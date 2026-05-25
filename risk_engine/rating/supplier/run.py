"""
代理商评级 - 一键运行
========================

串联 extract → score → rate → 落库 完整流程。

用法:
    # 全量跑一次
    from risk_engine.rating.supplier.run import run_supplier_rating
    run_supplier_rating(data_date="2026-05-25")

    # 仅湖南
    run_supplier_rating(province="湖南省", data_date="2026-05-25")
"""

from __future__ import annotations

import pandas as pd
import numpy as np
import pymysql
from datetime import date, datetime
from typing import Optional

from risk_engine.toolkit.connectors import get_data
from risk_engine.rating.supplier.extract import (
    extract_all,
    extract_store_quality,
    extract_yzf_rating,
    extract_staff_count,
)
from risk_engine.rating.supplier.score import score_all
from risk_engine.rating.supplier.rate import assign_ratings


def run_supplier_rating(
    data_date: Optional[str] = None,
    province: Optional[str] = None,
    lookback_months: int = 12,
    write_to_db: bool = True,
) -> pd.DataFrame:
    """
    代理商评级全流程：提取 → 评分 → 评级 → 落库。

    参数:
        data_date: 数据截止日期 (yyyy-MM-dd)，默认今天
        province:  省份筛选（None=全国）
        lookback_months: 回溯月数
        write_to_db: 是否写入本地库（默认写入）

    返回:
        最终评级结果 DataFrame
    """
    data_date = data_date or datetime.now().strftime("%Y-%m-%d")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始代理商评级流程")
    print(f"    数据截止: {data_date}, 省份: {province or '全国'}")

    # ── Step 1: 提取基础数据 ──
    print(f"    1/5 提取基础数据...")
    df = extract_all(
        end_date=data_date,
        lookback_months=lookback_months,
        province=province,
    )
    print(f"        → {len(df)} 个代理商")

    if df.empty:
        print("    ⚠️ 无数据，流程终止")
        return df

    # ── Step 2: 提取门店质量 ──
    print(f"    2/5 提取门店质量数据...")
    supplier_codes = df["supplier_code"].tolist()
    store_df = extract_store_quality(supplier_codes)

    if not store_df.empty:
        df = df.merge(store_df, on="supplier_code", how="left")
        # 填充缺失值
        df["store_count_actual"] = df["store_count_actual"].fillna(df["store_count"])
        df["high_quality_store_count"] = df["high_quality_store_count"].fillna(0)
        df["regulated_store_count"] = df["regulated_store_count"].fillna(0)
        df["store_quality_rate"] = df.apply(
            lambda r: r["high_quality_store_count"] / r["store_count_actual"]
            if r["store_count_actual"] > 0 else 0,
            axis=1,
        )
        df["regulated_store_rate"] = df.apply(
            lambda r: r["regulated_store_count"] / r["store_count_actual"]
            if r["store_count_actual"] > 0 else 0,
            axis=1,
        )
    else:
        df["store_quality_rate"] = 0
        df["regulated_store_rate"] = 0
    print(f"        → 完成")

    # ── Step 3: 补充营业员人数 ──
    print(f"    3/5 补充营业员人数...")
    staff_df = extract_staff_count(supplier_codes)
    if not staff_df.empty:
        df = df.merge(staff_df, on="supplier_code", how="left")
        df["staff_count"] = df["staff_count"].fillna(0).astype(int)
    print(f"        → {'完成' if not staff_df.empty else '无数据'}")

    # ── Step 4: 导入翼支付评级 ──
    print(f"    4/5 导入翼支付评级...")
    yzf_df = extract_yzf_rating()
    if not yzf_df.empty:
        df = df.merge(yzf_df, on="supplier_code", how="left")
    else:
        df["yzf_rating"] = None
    print(f"        → {'完成' if not yzf_df.empty else '无评级数据'}")

    # ── Step 5: 评分 ──
    print(f"    5/5 评分 + 评级...")
    df = score_all(df)
    df = assign_ratings(df)

    # 统计
    rating_counts = df["supplier_rating"].value_counts()
    for r in ["A", "B", "C"]:
        count = rating_counts.get(r, 0)
        print(f"        {r}级: {count} 个 ({count/len(df)*100:.1f}%)")
    print(f"        综合评分范围: {df['compliance_score'].min()} ~ {df['compliance_score'].max()}")
    print(f"        综合评分均值: {df['compliance_score'].mean():.0f}")

    # ── Step 5: 写入本地库 ──
    if write_to_db:
        _write_to_db(df, data_date)
        print(f"    ✅ 数据已写入本地库 risk_control.supplier_evaluation")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 代理商评级流程完成")
    return df


def _write_to_db(df: pd.DataFrame, data_date: str):
    """将评分和评级结果写入本地 MySQL。"""
    # 只取表中存在的列
    COLUMNS = [
        "supplier_code", "province",
        "business_start_date", "last_active_date",
        "business_duration_days", "active_months", "recent_inactive_days",
        "store_count", "staff_count",
        "high_quality_store_count", "regulated_store_count",
        "store_quality_rate", "regulated_store_rate",
        "yzf_rating",
        "total_transaction_amount", "total_transaction_count",
        "monthly_avg_amount", "last_month_amount", "amount_growth_rate",
        "num_overdue_rate",
        "overdue_order_count",
        "new_customer_count", "old_customer_count",
        "local_network_count", "external_network_count",
        "single_card_count", "fusion_count",
        "unsubscribe_rate",
        "risk_pass_rate", "risk_pass_rate_deviation",
        "compliance_score", "supplier_rating",
    ]

    # 排除 generated 列（MySQL 不允许插入 generated 列）
    GENERATED_COLUMNS = {
        "store_quality_rate", "regulated_store_rate",
        "avg_store_amount", "avg_staff_amount",
        "new_customer_rate", "old_customer_rate",
        "local_network_rate", "external_network_rate",
        "single_card_rate", "fusion_rate",
    }

    existing = [c for c in COLUMNS if c in df.columns and c not in GENERATED_COLUMNS]
    records = df[existing].copy()
    # 列名映射：风控引擎的 supplier_code → 数据库的 supplier_id
    records.rename(columns={"supplier_code": "supplier_id"}, inplace=True)
    records["data_date"] = data_date

    # 构建 INSERT 语句（逐行写入，避免 NaN 问题）
    conn = get_data(data_type="local")

    # 先清除旧数据
    conn.execute_sql(f"DELETE FROM supplier_evaluation WHERE data_date = '{data_date}'")

    # 逐行写入
    cursor = conn.conn.cursor()
    cols = list(records.columns)
    placeholders = ",".join(["%s"] * len(cols))
    cols_quoted = ",".join([f"`{c}`" for c in cols])
    sql = f"INSERT INTO supplier_evaluation ({cols_quoted}) VALUES ({placeholders})"

    for _, row in records.iterrows():
        values = []
        for val in row:
            if pd.isna(val):
                values.append(None)
            elif isinstance(val, (float,)) and (np.isinf(val) or np.isnan(val)):
                values.append(None)
            else:
                values.append(val)
        try:
            cursor.execute(sql, tuple(values))
        except Exception as e:
            print(f'    ⚠️ 写入失败 [{row.iloc[0]}]: {e}')
            conn.conn.rollback()

    conn.conn.commit()
    cursor.close()
    conn.close()
