"""
门店评级 - 一键运行
========================

串联 extract → score → rate → 落库。

用法:
    from risk_engine.rating.store.run import run_store_rating
    run_store_rating(data_date="2026-05-25")
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

import numpy as np
import pandas as pd

from risk_engine.rating.store.extract import (
    extract_all,
    extract_channel_level,
    extract_supplier_rating,
)
from risk_engine.rating.store.rate import assign_ratings
from risk_engine.rating.store.score import score_all
from risk_engine.toolkit.connectors import get_data


def run_store_rating(
    data_date: Optional[str] = None,
    province: Optional[str] = None,
    lookback_months: int = 12,
    write_to_db: bool = True,
) -> pd.DataFrame:
    data_date = data_date or datetime.now().strftime("%Y-%m-%d")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始门店评级")
    print(f"    截止: {data_date}, 省份: {province or '全国'}")

    # ── 1. 提取基础数据 ──
    print(f"    1/5 提取基础数据...")
    df = extract_all(end_date=data_date, lookback_months=lookback_months, province=province)
    print(f"        → {len(df)} 家门店")
    if df.empty:
        return df
    store_ids = df["store_id"].tolist()

    # ── 2. 渠道等级 ──
    print(f"    2/5 提取渠道等级...")
    cl_df = extract_channel_level(store_ids)
    if not cl_df.empty:
        df = df.merge(cl_df[["store_id", "channel_level"]], on="store_id", how="left")
    else:
        df["channel_level"] = None
    matched = df["channel_level"].notna().sum()
    print(f"        → 有渠道等级: {matched}/{len(df)}")

    # ── 3. 代理商评级 ──
    print(f"    3/5 提取代理商评级...")
    sr_df = extract_supplier_rating()
    if not sr_df.empty:
        df = df.merge(sr_df, on="supplier_code", how="left")
    else:
        df["supplier_rating"] = None
    print(f"        → 完成")

    # ── 4. 评分 ──
    print(f"    4/5 评分 + 评级...")
    df = score_all(df)
    df = assign_ratings(df)

    cnts = df["store_rating"].value_counts()
    for r in ["A", "B", "C"]:
        c = cnts.get(r, 0)
        print(f"        {r}级: {c} 个 ({c/len(df)*100:.1f}%)" if c else f"        {r}级: 0")
    print(f"        评分范围: {df['compliance_score'].min()} ~ {df['compliance_score'].max()}")

    # ── 5. 落库 ──
    if write_to_db:
        _write_to_db(df, data_date)
        print(f"    ✅ 数据已写入本地库 risk_control.store_evaluation")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 完成")
    return df


def _write_to_db(df: pd.DataFrame, data_date: str):
    COLUMNS = [
        "store_id",
        "store_name",
        "province",
        "city",
        "supplier_code",
        "supplier_name",
        "business_start_date",
        "last_active_date",
        "business_duration_days",
        "active_months",
        "recent_inactive_days",
        "total_transaction_count",
        "total_transaction_amount",
        "monthly_avg_amount",
        "last_month_amount",
        "amount_growth_rate",
        "new_customer_count",
        "old_customer_count",
        "local_network_count",
        "external_network_count",
        "single_card_count",
        "fusion_count",
        "num_overdue_rate",
        "overdue_order_count",
        "matured_order_count",
        "unsubscribe_rate",
        "risk_pass_rate",
        "risk_pass_rate_deviation",
        "channel_level",
        "supplier_rating",
        "penalty_count",
        "compliance_score",
        "store_rating",
    ]
    existing = [c for c in COLUMNS if c in df.columns]
    records = df[existing].copy()
    records["data_date"] = data_date

    conn = get_data(data_type="local")
    conn.execute_sql(f"DELETE FROM store_evaluation WHERE data_date = '{data_date}'")

    cursor = conn.conn.cursor()
    cols = list(records.columns)
    ph = ",".join(["%s"] * len(cols))
    cq = ",".join([f"`{c}`" for c in cols])
    sql = f"INSERT INTO store_evaluation ({cq}) VALUES ({ph})"

    success = 0
    errors = 0
    for _, row in records.iterrows():
        vals = []
        for v in row:
            if pd.isna(v):
                vals.append(None)
            elif isinstance(v, (float, np.floating)) and (np.isnan(v) or np.isinf(v)):
                vals.append(None)
            else:
                try:
                    vals.append(v.item() if hasattr(v, "item") else v)
                except:
                    vals.append(v)
        try:
            cursor.execute(sql, tuple(vals))
            success += 1
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"    ⚠️ 写入失败 [{row.iloc[0]}]: {e}")
    conn.conn.commit()
    cursor.close()
    conn.close()
    print(f"    → 写入: {success} 成功, {errors} 失败")
