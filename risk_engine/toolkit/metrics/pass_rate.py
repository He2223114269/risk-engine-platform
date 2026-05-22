#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : pass_rate
功能描述 : 多维度通过率计算 — 淘顺实时授信业务核心指标

版本 v0.2.0 — 全面升级

=== 指标集 ===
  基础量      : 申请数, 通过数, 特批用户数
  通过率      : 通过率(裸), 特批通过率
  异网/本网   : 异网占比, 异网通过率, 本网通过率
  新客        : 新客占比, 新客通过率

  所有指标在同一 SQL 中一次计算完成，避免多次查询。

=== 分组维度 ===
  - date     : 日期 (DATE_FORMAT)
  - province  : 省份 (store_addr_province)
  - strategy  : 策略ID (strategy_id)
  - 任意组合  : 如 ["date", "province"], ["strategy", "province"] 等

=== 数据源 ===
  核心表: ods.ods_ts_credit_yzf_order_grant_apply（申请表）
  风控表: ods.ods_ts_order_white_list_control（风控结果）

=== 口径说明 ===
  - 去重口径（默认）: 同身份证去重，授信成功优先
  - 仅 business_type='02'（淘顺实时授信）
  - 仅 custtype='00'（普通用户，排除已结清再贷用户）

更新历史:
  2026-05-21, Jingluo, v0.1.0 — 初始创建 (简单通过率)
  2026-05-22, Jingluo, v0.2.0 — 完整指标集 + 灵活分组维度
============================================================================
"""

from __future__ import annotations

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List

from risk_engine.toolkit.connectors import get_data

__all__ = [
    "PassRateCalculator",
    "calc_pass_rate",
    "METRICS_REGISTRY",
    "DIMS_REGISTRY",
]


# ========================================================================
#  核心构建块
# ========================================================================

# ── 基础筛选（子查询内部） ──
_SOURCE_FILTER = "a1.business_type = '02'"

# ── 去重子查询 ──
# 同身份证号去重：
#   - 若有授信成功记录，优先保留授信成功的
#   - 同状态则保留 id 最大的（最新）
# 同时左联风控结果表（operator_real, first_risk_result, online_duration, strategy_id）
_DEDUP_SUB = f"""
  SELECT a1.*, a3.operator_real, a3.first_risk_result,
         a3.online_duration, a3.strategy_id
  FROM ods.ods_ts_credit_yzf_order_grant_apply a1
  LEFT JOIN ods.ods_ts_credit_yzf_order_grant_apply a2
    ON a1.id_number_enc = a2.id_number_enc
    AND ( (a2.apply_status = '授信成功' AND a1.apply_status != '授信成功')
        OR (a1.apply_status = a2.apply_status AND a1.id < a2.id) )
  LEFT JOIN ods.ods_ts_order_white_list_control a3
    ON a1.ct_user_id = a3.order_no AND a3.type = '淘顺实时授信'
  WHERE a2.id IS NULL AND {_SOURCE_FILTER}
"""


# ── 指标定义 ──
# 键 = 指标名，值 = SQL 表达式（在 GROUP BY 后计算）
# 用 NULLIF 防除零，ROUND 控制小数位
METRICS_REGISTRY = {
    # ─── 基础量 ───
    "申请数": "COUNT(*) AS 申请数",
    "通过数": (
        "SUM(CASE WHEN apply_status = '授信成功' THEN 1 ELSE 0 END) AS 通过数"
    ),
    "特批用户数": (
        "SUM(CASE WHEN first_risk_result = '特批白名单用户'"
        " THEN 1 ELSE 0 END) AS 特批用户数"
    ),

    # ─── 通过率 ───
    # 裸通过率：排除特批白名单用户
    "通过率": (
        "ROUND("
        "  SUM(CASE WHEN apply_status = '授信成功'"
        "           AND first_risk_result != '特批白名单用户'"
        "      THEN 1 ELSE 0 END)"
        "  / NULLIF(COUNT(*), 0), 4"
        ") AS 通过率"
    ),
    # 特批通过率：包含特批白名单用户
    "特批通过率": (
        "ROUND("
        "  SUM(CASE WHEN apply_status = '授信成功'"
        "           OR first_risk_result = '特批白名单用户'"
        "      THEN 1 ELSE 0 END)"
        "  / NULLIF(COUNT(*), 0), 4"
        ") AS 特批通过率"
    ),

    # ─── 异网/本网占比及通过率 ───
    "异网占比": (
        "ROUND("
        "  SUM(CASE WHEN operator_real IN ('移动', '联通')"
        "      THEN 1 ELSE 0 END)"
        "  / NULLIF(COUNT(*), 0), 4"
        ") AS 异网占比"
    ),
    "异网通过率": (
        "ROUND("
        "  SUM(CASE WHEN apply_status = '授信成功'"
        "           AND operator_real IN ('移动', '联通')"
        "      THEN 1 ELSE 0 END)"
        "  / NULLIF("
        "      SUM(CASE WHEN operator_real IN ('移动', '联通')"
        "          THEN 1 ELSE 0 END), 0"
        "  ), 2"
        ") AS 异网通过率"
    ),
    "本网通过率": (
        "ROUND("
        "  SUM(CASE WHEN apply_status = '授信成功'"
        "           AND operator_real = '电信'"
        "      THEN 1 ELSE 0 END)"
        "  / NULLIF("
        "      SUM(CASE WHEN operator_real = '电信'"
        "          THEN 1 ELSE 0 END), 0"
        "  ), 2"
        ") AS 本网通过率"
    ),

    # ─── 新客占比及通过率 ───
    # 新客定义: online_duration <= 3 个月
    "新客占比": (
        "ROUND("
        "  SUM(CASE WHEN online_duration <= 3 THEN 1 ELSE 0 END)"
        "  / NULLIF(COUNT(*), 0), 4"
        ") AS 新客占比"
    ),
    "新客通过率": (
        "ROUND("
        "  SUM(CASE WHEN apply_status = '授信成功'"
        "           AND online_duration <= 3"
        "      THEN 1 ELSE 0 END)"
        "  / NULLIF("
        "      SUM(CASE WHEN online_duration <= 3 THEN 1 ELSE 0 END), 0"
        "  ), 2"
        ") AS 新客通过率"
    ),
}

# ── 维度定义 ──
# 键 = 维度标识, 值 = (SQL 表达式, 输出列名)
DIMS_REGISTRY = {
    "date":     ("DATE_FORMAT(add_time, '%Y-%m-%d')", "日期"),
    "province": ("store_addr_province", "省份"),
    "strategy": ("strategy_id", "策略ID"),
}


def _build_select(
    dims: List[str],
    metrics: List[str],
) -> str:
    """构建 SELECT 子句（维度列 + 指标列）"""
    parts = []

    # 维度列
    for d in dims:
        if d in DIMS_REGISTRY:
            expr, label = DIMS_REGISTRY[d]
            parts.append(f"    {expr} AS {label}")
        else:
            parts.append(f"    {d}")  # 裸列名直接透传

    # 指标列
    for m in metrics:
        if m in METRICS_REGISTRY:
            parts.append(f"    {METRICS_REGISTRY[m]}")
        else:
            parts.append(f"    {m}")

    return ",\n".join(parts)


def _build_where(
    start_date: str,
    end_date: str,
    where_extra: Optional[str] = None,
    custtype: Optional[str] = "00",
) -> str:
    """构建 WHERE 子句"""
    clauses = [
        f"    add_time >= '{start_date}'",
        f"    AND add_time < DATE_ADD('{end_date}', INTERVAL 1 DAY)",
    ]
    if custtype is not None:
        clauses.append(f"    AND custtype = '{custtype}'")
    if where_extra:
        clauses.append(f"    AND {where_extra}")
    return "\n".join(clauses)


# ========================================================================
#  主类
# ========================================================================

class PassRateCalculator:
    """
    多维度通过率计算器 v0.2.0

    完整指标集 + 灵活分组维度 + 一次性查询。

    ── 快速上手 ──

    >>> calc = PassRateCalculator(get_data(data_type='risk'))

    # 每日+分省完整报告
    >>> df = calc.report(
    ...     dims=["date", "province"],
    ...     start_date="2026-05-01",
    ... )

    # 按策略 ID 汇总
    >>> df = calc.report(
    ...     dims=["strategy", "province"],
    ...     start_date="2026-05-05",
    ... )

    # 只看部分指标
    >>> df = calc.report(
    ...     dims=["province"],
    ...     days=30,
    ...     metrics=["申请数", "通过数", "异网占比", "新客占比"],
    ... )

    ── 向下兼容 ──
    >>> calc.overall(days=7)                    # 整体通过率
    >>> calc.by_province(days=30)               # 分省
    >>> calc.daily_trend(start_date="2026-05-01")  # 逐日趋势
    >>> calc.compare_with_standard()            # vs 标准通过率
    """

    def __init__(self, conn):
        self.conn = conn

    # ══════════════════════════════════════════════════════════════════
    #  核心报告方法
    # ══════════════════════════════════════════════════════════════════

    def report(
        self,
        dims: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: Optional[int] = None,
        metrics: Optional[List[str]] = None,
        where_extra: Optional[str] = None,
        custtype: Optional[str] = "00",
    ) -> pd.DataFrame:
        """
        多维度指标报告 — 单次查询完成所有指标。

        Args:
            dims: 分组维度，可选 ['date','province','strategy'] 任意组合
                  默认 ["date", "province"]
            start_date: 起始日期 (yyyy-MM-dd)
            end_date:   结束日期 (yyyy-MM-dd, 默认今天)
            days:       统计天数（与 start_date 二选一，优先 start_date）
            metrics:    指标列表（默认全部指标）
            where_extra: 额外筛选条件，如 "store_addr_province = '湖南省'"
            custtype:   custtype 过滤，None 表示不过滤

        Returns:
            DataFrame，列 = 维度列 + 指标列，行 = 每组一行
        """
        dims = dims or ["date", "province"]
        end_date = end_date or datetime.now().strftime("%Y-%m-%d")

        # 日期范围
        if start_date is None and days is not None:
            start_date = (
                datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=days - 1)
            ).strftime("%Y-%m-%d")
        elif start_date is None:
            start_date = (
                datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=6)
            ).strftime("%Y-%m-%d")

        # 构建 SQL
        metrics = metrics or list(METRICS_REGISTRY.keys())
        select_clause = _build_select(dims, metrics)
        where_clause = _build_where(start_date, end_date, where_extra, custtype)

        dim_labels = [
            DIMS_REGISTRY[d][1] if d in DIMS_REGISTRY else d
            for d in dims
        ]
        group_clause = ", ".join(dim_labels) if dim_labels else "1"
        order_clause = ", ".join(dim_labels) if dim_labels else "1"

        sql = f"""
SELECT
{select_clause}
FROM ({_DEDUP_SUB}) dedup
WHERE
{where_clause}
GROUP BY {group_clause}
ORDER BY {order_clause}
        """.strip()

        df = self.conn.get_data(sql)
        return df

    # ══════════════════════════════════════════════════════════════════
    #  语义化便捷方法
    # ══════════════════════════════════════════════════════════════════

    def by_date_province(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: Optional[int] = None,
        **kwargs,
    ) -> pd.DataFrame:
        """按日 + 分省报告（最常用的监控视图）"""
        return self.report(
            dims=["date", "province"],
            start_date=start_date,
            end_date=end_date,
            days=days,
            **kwargs,
        )

    def by_province(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: int = 30,
        min_total: int = 50,
        **kwargs,
    ) -> pd.DataFrame:
        """分省汇总"""
        end_date = end_date or datetime.now().strftime("%Y-%m-%d")
        if start_date is None and days is not None:
            start_date = (
                datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=days - 1)
            ).strftime("%Y-%m-%d")

        df = self.report(
            dims=["province"],
            start_date=start_date,
            end_date=end_date,
            **kwargs,
        )
        if df.empty:
            return df
        df = df[df["申请数"] >= min_total].sort_values("申请数", ascending=False)
        df["通过率%"] = (df["通过率"] * 100).round(2)
        return df

    def daily_trend(
        self,
        start_date: str,
        end_date: Optional[str] = None,
        province: Optional[str] = None,
    ) -> pd.DataFrame:
        """逐日通过率趋势"""
        df = self.report(
            dims=["date"],
            start_date=start_date,
            end_date=end_date,
            where_extra=f"store_addr_province = '{province}'" if province else None,
        )
        if not df.empty:
            df["通过率%"] = (df["通过率"] * 100).round(2)
        return df

    def by_strategy(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: int = 30,
        min_total: int = 30,
    ) -> pd.DataFrame:
        """按策略 ID 汇总（用户新增需求）"""
        df = self.report(
            dims=["strategy"],
            start_date=start_date,
            end_date=end_date,
            days=days,
        )
        if df.empty:
            return df
        df = df[df["申请数"] >= min_total].sort_values("申请数", ascending=False)
        df["通过率%"] = (df["通过率"] * 100).round(2)
        df["特批通过率%"] = (df["特批通过率"] * 100).round(2)
        return df

    def overall(
        self,
        days: int = 7,
        end_date: Optional[str] = None,
        province: Optional[str] = None,
    ) -> dict:
        """向下兼容 — 整体通过率

        Returns:
            dict: {total, pass, pass_rate, 异网占比, 新客占比, ...}
        """
        df = self.report(
            dims=[],
            start_date=(
                datetime.strptime(
                    end_date or datetime.now().strftime("%Y-%m-%d"), "%Y-%m-%d"
                ) - timedelta(days=days - 1)
            ).strftime("%Y-%m-%d"),
            end_date=end_date,
            metrics=list(METRICS_REGISTRY.keys()),
            where_extra=f"store_addr_province = '{province}'" if province else None,
        )
        if df.empty:
            return {
                "申请数": 0, "通过数": 0,
                "通过率": 0.0, "异网占比": 0.0, "新客占比": 0.0,
            }

        row = df.iloc[0]
        result = {}
        for col in df.columns:
            val = row[col]
            try:
                result[col] = int(val) if col in ("申请数", "通过数", "特批用户数") else float(val)
            except (ValueError, TypeError):
                result[col] = val
        result["通过率%"] = round(result.get("通过率", 0) * 100, 2)
        result["异网占比%"] = round(result.get("异网占比", 0) * 100, 2)
        result["新客占比%"] = round(result.get("新客占比", 0) * 100, 2)
        return result

    def compare_with_standard(
        self,
        days: int = 7,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """向下兼容 — 各省实际通过率 vs 标准通过率"""
        df = self.by_province(days=days, end_date=end_date, min_total=20)
        if df.empty:
            return df

        # 标准通过率配置（来自 risk_parameter_pass_radio 表）
        try:
            local_conn = get_data(data_type="local")
            std_df = local_conn.get_data(
                "SELECT province, pass_rate FROM risk_parameter_pass_radio"
            )
            local_conn.close()
            std_map = dict(zip(std_df["province"], std_df["pass_rate"]))
        except Exception:
            # 备用默认值
            std_map = {
                "湖南省": 55.0, "贵州省": 70.0,
                "甘肃省": 70.0, "江苏省": 40.0,
                "安徽省": 55.0, "江西省": 50.0,
                "海南省": 60.0, "宁夏回族自治区": 50.0,
                "青海省": 50.0,
            }

        df["标准通过率%"] = df["省份"].map(std_map)
        df["差距"] = (df["通过率%"] - df["标准通过率%"]).round(2)
        df["评估"] = df["差距"].apply(
            lambda x: "✅ 优秀" if x >= -3
            else ("🟡 达标" if x >= -5 else "🔴 不达标")
        )
        return df[["省份", "申请数", "通过率%", "标准通过率%", "差距", "评估"]]

    def __repr__(self):
        return "PassRateCalculator(v0.2.0, 多维度通过率计算器)"


# ========================================================================
#  便捷函数
# ========================================================================

def calc_pass_rate(
    conn,
    days: int = 7,
    province: Optional[str] = None,
) -> dict:
    """一行计算整体通过率（向下兼容）"""
    calc = PassRateCalculator(conn)
    return calc.overall(days=days, province=province)
