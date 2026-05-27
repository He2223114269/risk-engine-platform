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
    代理商评级全流程：提取 → 企查查 → 评分 → 评级 → 落库。
    """
    data_date = data_date or datetime.now().strftime("%Y-%m-%d")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始代理商评级流程")
    print(f"    数据截止: {data_date}, 省份: {province or '全国'}")

    # ── Step 1: 提取基础数据 ──
    print(f"    1/6 提取基础数据...")
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
    print(f"    2/6 提取门店质量数据...")
    supplier_codes = df["supplier_code"].tolist()
    store_df = extract_store_quality(supplier_codes)
    if not store_df.empty:
        df = df.merge(store_df, on="supplier_code", how="left")
        df["store_count_actual"] = df["store_count_actual"].fillna(df["store_count"])
        df["high_quality_store_count"] = df["high_quality_store_count"].fillna(0)
        df["regulated_store_count"] = df["regulated_store_count"].fillna(0)
        df["store_quality_rate"] = df.apply(
            lambda r: (
                r["high_quality_store_count"] / r["store_count_actual"]
                if r["store_count_actual"] > 0
                else 0
            ),
            axis=1,
        )
        df["regulated_store_rate"] = df.apply(
            lambda r: (
                r["regulated_store_count"] / r["store_count_actual"]
                if r["store_count_actual"] > 0
                else 0
            ),
            axis=1,
        )
    else:
        df["store_quality_rate"] = 0
        df["regulated_store_rate"] = 0
    print(f"        → 完成")

    # ── Step 3: 补充营业员人数 ──
    print(f"    3/6 补充营业员人数...")
    staff_df = extract_staff_count(supplier_codes)
    if not staff_df.empty:
        df = df.merge(staff_df, on="supplier_code", how="left")
        df["staff_count"] = df["staff_count"].fillna(0).astype(int)
    print(f"        → {'完成' if not staff_df.empty else '无数据'}")

    # ── Step 4: 导入企查查数据 ──
    print(f"    4/6 导入企查查数据...")
    _merge_qichacha(df, data_date)
    qcc_count = df["has_qichacha"].sum()
    print(f"        → 有企查查数据: {qcc_count}/{len(df)} ({qcc_count/len(df)*100:.1f}%)")

    # ── Step 5: 导入翼支付评级 ──
    print(f"    5/6 导入翼支付评级...")
    yzf_df = extract_yzf_rating()
    if not yzf_df.empty:
        df = df.merge(yzf_df, on="supplier_code", how="left")
    else:
        df["yzf_rating"] = None
    print(f"        → {'完成' if not yzf_df.empty else '无评级数据'}")

    # ── Step 6: 评分 + 评级 ──
    print(f"    6/6 评分 + 评级...")
    df = score_all(df)
    df = assign_ratings(df)

    # 统计
    rating_counts = df["supplier_rating"].value_counts()
    for r in ["A", "B", "C"]:
        count = rating_counts.get(r, 0)
        print(f"        {r}级: {count} 个 ({count/len(df)*100:.1f}%)")
    print(f"        综合评分范围: {df['compliance_score'].min()} ~ {df['compliance_score'].max()}")
    print(f"        综合评分均值: {df['compliance_score'].mean():.0f}")

    # ── 写入本地库 ──
    if write_to_db:
        _write_to_db(df, data_date)
        print(f"    ✅ 数据已写入本地库 risk_control.supplier_evaluation")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 代理商评级流程完成")
    return df


def _merge_qichacha(df: pd.DataFrame, data_date: str):
    """从本地 MySQL 的 supplier_qichacha 表合并企查查数据到评分 DataFrame。"""
    try:
        conn = get_data(data_type="local")
        qcc_df = conn.get_data("""
            SELECT supplier_name,
                   register_status, enterprise_type,
                   registered_capital, paid_capital,
                   credit_code, enterprise_scale, insured_count
            FROM supplier_qichacha
        """)
        conn.close()

        if qcc_df.empty:
            _set_qcc_fields(df, False)
            return

        # 标准化名称（处理全角/半角括号差异）
        df_name = df[["supplier_code", "supplier_name"]].copy()
        df_name["_name"] = df_name["supplier_name"].str.replace("（", "(").str.replace("）", ")")
        qcc_df["_name"] = qcc_df["supplier_name"].str.replace("（", "(").str.replace("）", ")")

        # 左连接企查查数据
        merged = df_name.merge(qcc_df, on="_name", how="left")

        # 把企查查字段合并回 df
        qcc_fields = [
            "register_status",
            "enterprise_type",
            "registered_capital",
            "paid_capital",
            "credit_code",
            "enterprise_scale",
            "insured_count",
        ]
        for col in qcc_fields:
            df[col] = merged[col].values

        df.drop(columns=["_name"], inplace=True, errors="ignore")

    except Exception as e:
        print(f"    ⚠️ 企查查数据加载失败: {e}")
        _set_qcc_fields(df, False)

    # 标记是否有企查查数据
    df["has_qichacha"] = df["register_status"].notna() & (df["register_status"] != "")


def _set_qcc_fields(df, has_data: bool):
    """设置企查查字段为 None"""
    df["has_qichacha"] = has_data
    for col in [
        "register_status",
        "enterprise_type",
        "registered_capital",
        "paid_capital",
        "credit_code",
        "enterprise_scale",
        "insured_count",
    ]:
        df[col] = None


def _write_to_db(df: pd.DataFrame, data_date: str):
    """将评分和评级结果写入本地 MySQL。"""
    COLUMNS = [
        "supplier_code",
        "supplier_name",
        "province",
        "business_start_date",
        "last_active_date",
        "business_duration_days",
        "active_months",
        "recent_inactive_days",
        "store_count",
        "staff_count",
        "high_quality_store_count",
        "regulated_store_count",
        "store_quality_rate",
        "regulated_store_rate",
        "yzf_rating",
        "total_transaction_amount",
        "total_transaction_count",
        "monthly_avg_amount",
        "last_month_amount",
        "amount_growth_rate",
        "num_overdue_rate",
        "overdue_order_count",
        "new_customer_count",
        "old_customer_count",
        "local_network_count",
        "external_network_count",
        "single_card_count",
        "fusion_count",
        "unsubscribe_rate",
        "risk_pass_rate",
        "risk_pass_rate_deviation",
        "compliance_score",
        "supplier_rating",
    ]

    GENERATED_COLUMNS = {
        "store_quality_rate",
        "regulated_store_rate",
        "avg_store_amount",
        "avg_staff_amount",
        "new_customer_rate",
        "old_customer_rate",
        "local_network_rate",
        "external_network_rate",
        "single_card_rate",
        "fusion_rate",
    }

    existing = [c for c in COLUMNS if c in df.columns and c not in GENERATED_COLUMNS]
    records = df[existing].copy()
    records.rename(columns={"supplier_code": "supplier_id"}, inplace=True)
    records["data_date"] = data_date

    conn = get_data(data_type="local")
    conn.execute_sql(f"DELETE FROM supplier_evaluation WHERE data_date = '{data_date}'")

    cursor = conn.conn.cursor()
    cols = list(records.columns)
    placeholders = ",".join(["%s"] * len(cols))
    cols_quoted = ",".join([f"`{c}`" for c in cols])
    sql = f"INSERT INTO supplier_evaluation ({cols_quoted}) VALUES ({placeholders})"

    success, failed = 0, 0
    for _, row in records.iterrows():
        # 跳过空 supplier_id
        sid = row.get("supplier_id") or row.get("supplier_code") or ""
        if not str(sid).strip():
            failed += 1
            continue
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
            success += 1
        except Exception as e:
            failed += 1

    conn.conn.commit()
    if failed > 0:
        print(f"    → 写入: {success} 成功, {failed} 失败（已跳过）")
    cursor.close()
    conn.close()
