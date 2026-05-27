"""
门店评级 - StarRocks 数据提取
========================

从 DWS 按 store_id 聚合各维度原始数据。
加上 v3_store 的渠道等级关联。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd

from risk_engine.toolkit.connectors import get_data

_DWS_TABLE = "dws.dws_credit_yzf_order_complete"
_SOURCE_FILTER = "source_business_type = '淘顺实时授信'"
_APPLY_TABLE = "ods.ods_ts_credit_yzf_order_grant_apply"
_RISK_TABLE = "ods.ods_ts_order_white_list_control"
_STORE_TABLE = "ods.ods_ts_v3_order_store"


def extract_all(
    end_date: Optional[str] = None,
    lookback_months: int = 12,
    province: Optional[str] = None,
) -> pd.DataFrame:
    """
    一次查询提取所有门店的聚合数据。
    """
    end_date = end_date or datetime.now().strftime("%Y-%m-%d")
    start_date = (
        datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=lookback_months * 30)
    ).strftime("%Y-%m-%d")

    province_filter = f"AND a.province = '{province}'" if province else ""

    sql = f"""
    WITH store_base AS (
        SELECT
            a.store_id, a.store_name, a.province, a.city,
            a.supplier_code, a.supplier_name,
            a.order_no, a.complete_time, a.order_amt_yuan,
            a.custtype,
            CASE WHEN a.custtype IN ('01', '06') THEN '老' ELSE '新' END AS old_new_flag,
            a.operator_real,
            CASE WHEN a.province = '湖南省' AND a.pack_name LIKE '%融合%' THEN '融合'
                 WHEN a.province = '湖南省' THEN '单卡' ELSE NULL END AS package_type,
            a.step_num_repay_status, a.order_status,
            CASE WHEN b.first_risk_result IS NOT NULL THEN b.first_risk_result ELSE '正常' END AS first_risk_result
        FROM {_DWS_TABLE} a
        LEFT JOIN {_RISK_TABLE} b ON a.ct_user_id = b.order_no AND b.type = '淘顺实时授信'
        WHERE {_SOURCE_FILTER}
          AND a.complete_time >= '{start_date}'
          AND a.complete_time < DATE_ADD('{end_date}', INTERVAL 1 DAY)
          AND a.store_id IS NOT NULL
          {province_filter}
    )
    SELECT
        -- 基本信息
        store_id, store_name, province, city, supplier_code, supplier_name,

        -- 经营基础
        MIN(complete_time) AS business_start_date,
        MAX(complete_time) AS last_active_date,
        COUNT(DISTINCT DATE_FORMAT(complete_time, '%Y-%m')) AS active_months,
        COUNT(*) AS total_transaction_count,
        COALESCE(SUM(order_amt_yuan), 0) AS total_transaction_amount,

        -- 近半年月均
        COALESCE(SUM(CASE WHEN complete_time >= DATE_SUB('{end_date}', INTERVAL 6 MONTH)
                     THEN order_amt_yuan ELSE 0 END) / 6, 0) AS monthly_avg_amount,
        COALESCE(SUM(CASE WHEN DATE_FORMAT(complete_time, '%Y-%m') = DATE_FORMAT('{end_date}', '%Y-%m')
                     THEN order_amt_yuan ELSE 0 END), 0) AS last_month_amount,

        -- 资产质量
        SUM(CASE WHEN step_num_repay_status = 2 THEN 1 ELSE 0 END) AS overdue_order_count,
        COUNT(DISTINCT CASE WHEN step_num_repay_status IN (1, 2) THEN order_no END) AS matured_order_count,
        SUM(CASE WHEN order_status IN ('违约退订', '提前结清') THEN 1 ELSE 0 END) AS unsubscribe_count,

        -- 客群
        SUM(CASE WHEN custtype = '00' THEN 1 ELSE 0 END) AS new_customer_count,
        SUM(CASE WHEN custtype IN ('01', '06') THEN 1 ELSE 0 END) AS old_customer_count,
        SUM(CASE WHEN operator_real IN ('1', '电信') THEN 1 ELSE 0 END) AS local_network_count,
        SUM(CASE WHEN operator_real IN ('2', '3', '移动', '联通') THEN 1 ELSE 0 END) AS external_network_count,
        SUM(CASE WHEN package_type = '单卡' THEN 1 ELSE 0 END) AS single_card_count,
        SUM(CASE WHEN package_type = '融合' THEN 1 ELSE 0 END) AS fusion_count,

        -- 风控通过率
        SUM(CASE WHEN first_risk_result NOT IN ('保证金白名单通过', '特批白名单用户') THEN 1 ELSE 0 END) AS risk_eligible_count,
        SUM(CASE WHEN first_risk_result NOT IN ('保证金白名单通过', '特批白名单用户')
                      AND step_num_repay_status IN (0, 1) THEN 1 ELSE 0 END) AS risk_passed_count

    FROM store_base
    GROUP BY store_id, store_name, province, city, supplier_code, supplier_name
    """

    conn = get_data(data_type="risk")
    df = conn.get_data(sql)
    conn.close()

    if df.empty:
        return df

    # 衍生计算
    ref_date = datetime.strptime(end_date, "%Y-%m-%d")
    df["business_duration_days"] = (ref_date - pd.to_datetime(df["business_start_date"])).dt.days
    df["recent_inactive_days"] = (ref_date - pd.to_datetime(df["last_active_date"])).dt.days
    df["amount_growth_rate"] = df.apply(
        lambda r: (
            (r["last_month_amount"] / r["monthly_avg_amount"] - 1)
            if r["monthly_avg_amount"] > 0
            else 0
        ),
        axis=1,
    )
    # 足额率
    df["num_overdue_rate"] = df.apply(
        lambda r: (
            r["overdue_order_count"] / r["matured_order_count"]
            if r["matured_order_count"] > 0
            else 0
        ),
        axis=1,
    )
    # 退订率
    df["unsubscribe_rate"] = df.apply(
        lambda r: (
            r["unsubscribe_count"] / r["total_transaction_count"]
            if r["total_transaction_count"] > 0
            else 0
        ),
        axis=1,
    )
    # 风控通过率
    df["risk_pass_rate"] = df.apply(
        lambda r: (
            r["risk_passed_count"] / r["risk_eligible_count"] if r["risk_eligible_count"] > 0 else 0
        ),
        axis=1,
    )

    return df


def extract_channel_level(
    store_ids: list,
) -> pd.DataFrame:
    """从 v3_store 取门店的渠道等级。"""
    if not store_ids:
        return pd.DataFrame()

    conn = get_data(data_type="risk")
    batch_size = 500
    results = []
    for i in range(0, len(store_ids), batch_size):
        batch = store_ids[i : i + batch_size]
        ids_str = ",".join([f"'{s}'" for s in batch])
        df = conn.get_data(f"""
            SELECT store_code, channel_level, update_time
            FROM {_STORE_TABLE}
            WHERE isv = '淘顺' AND type = '翼支付实时授信'
              AND store_code IN ({ids_str})
        """)
        if not df.empty:
            df = df.sort_values("update_time", ascending=False)
            df = df.drop_duplicates(subset=["store_code"], keep="first")
            df.rename(columns={"store_code": "store_id"}, inplace=True)
            results.append(df)
    conn.close()
    return pd.concat(results, ignore_index=True) if results else pd.DataFrame()


def extract_supplier_rating(conn=None) -> pd.DataFrame:
    """从本地库取代理商评级。"""
    if conn is None:
        conn = get_data(data_type="local")
    try:
        df = conn.get_data("""
            SELECT supplier_id, supplier_rating
            FROM supplier_evaluation
            WHERE data_date = '2026-05-25'
        """)
        df.rename(columns={"supplier_id": "supplier_code"}, inplace=True)
        return df
    except Exception:
        return pd.DataFrame(columns=["supplier_code", "supplier_rating"])
