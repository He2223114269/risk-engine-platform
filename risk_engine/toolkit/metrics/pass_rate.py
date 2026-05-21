#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : pass_rate
功能描述 : 通过率计算 — 淘顺实时授信业务的核心指标
          支持整体通过率、分省通过率、逐日通过率趋势、去重口径计算
          标准通过率从 risk_control.risk_parameter_pass_radio 动态读取

数据源: ods.ods_ts_credit_yzf_order_grant_apply（申请表）
筛选条件: source_business_type = '淘顺实时授信'
省份字段: store_addr_province / store_addr_city（非 province/city）

通过率口径:
  - 去重口径（默认）: 同身份证号去重，保留最新记录
  - 不去重口径: 全量明细

更新历史:
  2026-05-21, Jingluo, v0.1.0 — 初始创建
============================================================================
"""

from __future__ import annotations

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

from risk_engine.toolkit.connectors import get_data

__all__ = [
    "PassRateCalculator",
    "calc_pass_rate",
]


# ===== 核心SQL片段 =====

_SOURCE_FILTER = "business_type = '02'"

_DEDUP_SUB = f"""
  SELECT a1.*, a3.operator_real, a3.first_risk_result, a3.online_duration
  FROM ods.ods_ts_credit_yzf_order_grant_apply a1
  LEFT JOIN ods.ods_ts_credit_yzf_order_grant_apply a2
    ON a1.id_number_enc = a2.id_number_enc
    AND ( (a2.apply_status = '授信成功' AND a1.apply_status != '授信成功')
        OR (a1.apply_status = a2.apply_status AND a1.id < a2.id) )
  LEFT JOIN ods.ods_ts_order_white_list_control a3 ON a1.ct_user_id = a3.order_no
  WHERE a2.id IS NULL AND a1.{_SOURCE_FILTER}
"""

# ===== 主类 =====

class PassRateCalculator:
    """
    通过率计算器

    支持整体、分省、逐日维度计算通过率，
    去重/不去重两种口径。

    Usage:
        conn = get_data(data_type='risk')

        # 整体通过率（近7天）
        calc = PassRateCalculator(conn)
        result = calc.overall(days=7)
        print(f"整体通过率: {result['pass_rate']}%")

        # 分省通过率
        by_province = calc.by_province(days=30)
        print(by_province)

        # 逐日趋势
        daily = calc.daily_trend(start_date='2026-04-01')
        print(daily)
    """

    def __init__(self, conn: get_data):
        """
        Args:
            conn: 数据库连接器实例（data_type='risk' 连 StarRocks）
        """
        self.conn = conn

    # ───────────── 整体通过率 ─────────────

    def overall(
        self,
        days: int = 7,
        end_date: Optional[str] = None,
        dedup: bool = True,
        province: Optional[str] = None,
    ) -> dict:
        """
        计算整体通过率

        Args:
            days: 统计天数
            end_date: 结束日期（默认今天）
            dedup: 是否去重
            province: 省份筛选（可选）

        Returns:
            {'total': 申请量, 'pass': 通过量, 'reject': 拒绝量,
             'pass_rate': 通过率%, 'reject_reason': {原因: 数量}}
        """
        end = end_date or datetime.now().strftime("%Y-%m-%d")
        start = (datetime.strptime(end, "%Y-%m-%d") - timedelta(days=days - 1)).strftime("%Y-%m-%d")

        if dedup:
            source = f"({_DEDUP_SUB}) dedup"
            date_col = "a1.add_time"
            where_extra = f"AND {date_col} >= '{start}' AND {date_col} < date_add('{end}', interval 1 day)"
            if province:
                where_extra += f" AND a1.store_addr_province = '{province}'"
            sql = f"""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN apply_status='授信成功' THEN 1 ELSE 0 END) as pass,
                    SUM(CASE WHEN apply_status!='授信成功' THEN 1 ELSE 0 END) as reject
                FROM {source}
                WHERE {where_extra}
            """
        else:
            where = f"add_time >= '{start}' AND add_time < date_add('{end}', interval 1 day) AND {_SOURCE_FILTER}"
            if province:
                where += f" AND store_addr_province = '{province}'"
            sql = f"""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN apply_status='授信成功' THEN 1 ELSE 0 END) as pass,
                    SUM(CASE WHEN apply_status!='授信成功' THEN 1 ELSE 0 END) as reject
                FROM ods.ods_ts_credit_yzf_order_grant_apply
                WHERE {where}
            """

        df = self.conn.get_data(sql)
        if df.empty:
            return {"total": 0, "pass": 0, "reject": 0, "pass_rate": 0.0}

        row = df.iloc[0]
        total = int(row["total"])
        passed = int(row["pass"])
        reject = int(row["reject"])
        rate = round(passed / total * 100, 2) if total > 0 else 0.0

        # 拒绝原因分布
        reject_reason = self._reject_reasons(start, end, province, dedup)

        return {
            "total": total,
            "pass": passed,
            "reject": reject,
            "pass_rate": rate,
            "start_date": start,
            "end_date": end,
            "dedup": dedup,
            "reject_reason": reject_reason,
        }

    # ───────────── 分省通过率 ─────────────

    def by_province(
        self,
        days: int = 30,
        end_date: Optional[str] = None,
        dedup: bool = True,
        min_total: int = 50,
    ) -> pd.DataFrame:
        """
        分省通过率统计

        Args:
            days: 统计天数
            end_date: 结束日期
            dedup: 是否去重
            min_total: 最低申请量（低于此值的省份过滤掉）

        Returns:
            DataFrame: [省份, 申请量, 通过量, 拒绝量, 通过率%, 我司拒绝, 翼支付拒绝]
        """
        end = end_date or datetime.now().strftime("%Y-%m-%d")
        start = (datetime.strptime(end, "%Y-%m-%d") - timedelta(days=days - 1)).strftime("%Y-%m-%d")

        if dedup:
            source = f"({_DEDUP_SUB}) dedup"
            date_col = "a1.add_time"
            prov_col = "a1.store_addr_province"
            msg_col = "a1.apply_msg"
            sql = f"""
                SELECT
                    {prov_col} as province,
                    COUNT(*) as total,
                    SUM(CASE WHEN apply_status='授信成功' THEN 1 ELSE 0 END) as pass,
                    SUM(CASE WHEN apply_status!='授信成功' THEN 1 ELSE 0 END) as reject,
                    SUM(CASE WHEN {msg_col}='综合评分不通过' THEN 1 ELSE 0 END) as reject_our,
                    SUM(CASE WHEN {msg_col}!='综合评分不通过' AND apply_status!='授信成功' THEN 1 ELSE 0 END) as reject_their
                FROM {source}
                WHERE {prov_col} IS NOT NULL
                  AND {date_col} >= '{start}' AND {date_col} < date_add('{end}', interval 1 day)
                GROUP BY {prov_col}
                HAVING total >= {min_total}
                ORDER BY total DESC
            """
        else:
            sql = f"""
                SELECT
                    store_addr_province as province,
                    COUNT(*) as total,
                    SUM(CASE WHEN apply_status='授信成功' THEN 1 ELSE 0 END) as pass,
                    SUM(CASE WHEN apply_status!='授信成功' THEN 1 ELSE 0 END) as reject,
                    SUM(CASE WHEN apply_msg='综合评分不通过' THEN 1 ELSE 0 END) as reject_our,
                    SUM(CASE WHEN apply_msg!='综合评分不通过' AND apply_status!='授信成功' THEN 1 ELSE 0 END) as reject_their
                FROM ods.ods_ts_credit_yzf_order_grant_apply
                WHERE store_addr_province IS NOT NULL
                  AND add_time >= '{start}' AND add_time < date_add('{end}', interval 1 day)
                  AND {_SOURCE_FILTER}
                GROUP BY store_addr_province
                HAVING total >= {min_total}
                ORDER BY total DESC
            """

        df = self.conn.get_data(sql)
        if df.empty:
            return df

        df["pass_rate"] = (df["pass"] / df["total"] * 100).round(2)
        return df

    # ───────────── 逐日通过率趋势 ─────────────

    def daily_trend(
        self,
        start_date: str,
        end_date: Optional[str] = None,
        dedup: bool = True,
        province: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        逐日通过率趋势

        Args:
            start_date: 起始日期 (yyyy-MM-dd)
            end_date: 结束日期（默认今天）
            dedup: 是否去重
            province: 省份筛选（可选）

        Returns:
            DataFrame: [日期, 申请量, 通过量, 通过率%]
        """
        end = end_date or datetime.now().strftime("%Y-%m-%d")

        if dedup:
            source = f"({_DEDUP_SUB}) dedup"
            date_col = "a1.add_time"
            where_prov = f" AND a1.store_addr_province = '{province}'" if province else ""
            sql = f"""
                SELECT
                    date_format({date_col}, '%Y-%m-%d') as dt,
                    COUNT(*) as total,
                    SUM(CASE WHEN apply_status='授信成功' THEN 1 ELSE 0 END) as pass
                FROM {source}
                WHERE {date_col} >= '{start_date}' AND {date_col} < date_add('{end}', interval 1 day)
                  {where_prov}
                GROUP BY dt
                ORDER BY dt
            """
        else:
            where_prov = f" AND store_addr_province = '{province}'" if province else ""
            sql = f"""
                SELECT
                    date_format(add_time, '%Y-%m-%d') as dt,
                    COUNT(*) as total,
                    SUM(CASE WHEN apply_status='授信成功' THEN 1 ELSE 0 END) as pass
                FROM ods.ods_ts_credit_yzf_order_grant_apply
                WHERE add_time >= '{start_date}' AND add_time < date_add('{end}', interval 1 day)
                  AND {_SOURCE_FILTER}
                  {where_prov}
                GROUP BY dt
                ORDER BY dt
            """

        df = self.conn.get_data(sql)
        if df.empty:
            return df
        df["pass_rate"] = (df["pass"] / df["total"] * 100).round(2)
        return df

    # ───────────── 标准通过率对比 ─────────────

    def compare_with_standard(
        self,
        days: int = 7,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        各省实际通过率 vs 标准通过率对比
        标准通过率从 risk_control.risk_parameter_pass_radio 读取

        Returns:
            DataFrame: [省份, 实际通过率, 标准通过率, 差距, 评估]
              评估: '优秀'(≤3%), '达标'(≤5%), '不达标'(>5%)
        """
        # 1. 获取实际通过率
        actual = self.by_province(days=days, end_date=end_date)
        if actual.empty:
            return actual

        # 2. 获取标准通过率
        try:
            std_conn = get_data(data_type='local')
            std_df = std_conn.get_data("SELECT * FROM risk_parameter_pass_radio")
            std_conn.close()
            std_map = dict(zip(std_df["province"], std_df["pass_rate"]))
        except Exception:
            # 如果没有本地库或表，用预设默认值
            std_map = {
                "湖南省": 55.0,
                "贵州省": 70.0,
                "甘肃省": 70.0,
                "江苏省": 40.0,
                "安徽省": 55.0,
                "江西省": 50.0,
                "海南省": 60.0,
                "宁夏回族自治区": 50.0,
                "青海省": 50.0,
            }

        # 3. 对比
        actual["standard_rate"] = actual["province"].map(std_map)
        actual["gap"] = (actual["pass_rate"] - actual["standard_rate"]).round(2)
        actual["评估"] = actual["gap"].apply(
            lambda x: "✅ 优秀" if x >= -3 else ("🟡 达标" if x >= -5 else "🔴 不达标")
        )

        return actual[["province", "total", "pass_rate", "standard_rate", "gap", "评估"]]

    # ───────────── 内部方法 ─────────────

    def _reject_reasons(
        self,
        start_date: str,
        end_date: str,
        province: Optional[str] = None,
        dedup: bool = True,
    ) -> dict:
        """拒绝原因分布"""
        if dedup:
            where = f"a1.add_time >= '{start_date}' AND a1.add_time < date_add('{end_date}', interval 1 day) AND a1.apply_status != '授信成功'"
            if province:
                where += f" AND a1.store_addr_province = '{province}'"
            sql = f"""
                SELECT a1.apply_msg, COUNT(*) as cnt
                FROM ({_DEDUP_SUB}) dedup
                WHERE {where}
                GROUP BY a1.apply_msg
                ORDER BY cnt DESC
            """
        else:
            where = f"add_time >= '{start_date}' AND add_time < date_add('{end_date}', interval 1 day) AND {_SOURCE_FILTER} AND apply_status != '授信成功'"
            if province:
                where += f" AND store_addr_province = '{province}'"
            sql = f"""
                SELECT apply_msg, COUNT(*) as cnt
                FROM ods.ods_ts_credit_yzf_order_grant_apply
                WHERE {where}
                GROUP BY apply_msg
                ORDER BY cnt DESC
            """

        df = self.conn.get_data(sql)
        if df.empty:
            return {}
        return dict(zip(df["apply_msg"], df["cnt"]))

    def __repr__(self) -> str:
        return "PassRateCalculator(通过率计算器)"


# ===== 便捷函数 =====

def calc_pass_rate(
    conn: get_data,
    days: int = 7,
    dedup: bool = True,
    province: Optional[str] = None,
) -> dict:
    """
    便捷函数 — 一行计算通过率

    Usage:
        conn = get_data(data_type='risk')
        result = calc_pass_rate(conn, days=7)
        print(f"通过率: {result['pass_rate']}%")
    """
    calc = PassRateCalculator(conn)
    return calc.overall(days=days, dedup=dedup, province=province)
