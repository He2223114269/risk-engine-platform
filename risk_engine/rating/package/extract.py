"""套餐评级 - 数据提取（简化版）"""
from __future__ import annotations
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
from risk_engine.toolkit.connectors import get_data

_DWS = "dws.dws_credit_yzf_order_complete"
_FILTER = "source_business_type = '淘顺实时授信'"
_RISK = "ods.ods_ts_order_white_list_control"


def extract_all(end_date=None, lookback_months=12, province=None):
    end_date = end_date or datetime.now().strftime("%Y-%m-%d")
    start = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=lookback_months * 30)).strftime("%Y-%m-%d")
    prov_f = f"AND a.province = '{province}'" if province else ""

    sql = f"""
    SELECT
        a.pack_name,
        a.province,
        MIN(a.complete_time) AS business_start_date,
        MAX(a.complete_time) AS last_active_date,
        COUNT(DISTINCT DATE_FORMAT(a.complete_time, '%Y-%m')) AS active_months,
        COUNT(*) AS total_transaction_count,
        COALESCE(SUM(a.order_amt_yuan), 0) AS total_transaction_amount,
        SUM(CASE WHEN a.custtype = '00' THEN 1 ELSE 0 END) AS new_customer_count,
        SUM(CASE WHEN a.custtype IN ('01','06') THEN 1 ELSE 0 END) AS old_customer_count,
        SUM(CASE WHEN a.operator_real IN ('1','电信') THEN 1 ELSE 0 END) AS local_network_count,
        SUM(CASE WHEN a.operator_real IN ('2','3','移动','联通') THEN 1 ELSE 0 END) AS external_network_count,
        SUM(CASE WHEN a.step_num_repay_status = 2 THEN 1 ELSE 0 END) AS overdue_order_count,
        COUNT(DISTINCT CASE WHEN a.step_num_repay_status IN (1,2) THEN a.order_no END) AS matured_order_count,
        SUM(CASE WHEN a.order_status IN ('违约退订','提前结清') THEN 1 ELSE 0 END) AS unsubscribe_count,
        SUM(CASE WHEN b.first_risk_result NOT IN ('保证金白名单通过','特批白名单用户') THEN 1 ELSE 0 END) AS risk_eligible,
        SUM(CASE WHEN b.first_risk_result NOT IN ('保证金白名单通过','特批白名单用户')
                      AND a.step_num_repay_status IN (0,1) THEN 1 ELSE 0 END) AS risk_passed
    FROM {_DWS} a
    LEFT JOIN {_RISK} b ON a.ct_user_id = b.order_no AND b.type = '淘顺实时授信'
    WHERE {_FILTER}
      AND a.complete_time >= '{start}'
      AND a.complete_time < DATE_ADD('{end_date}', INTERVAL 1 DAY)
      AND a.pack_name IS NOT NULL AND a.pack_name != ''
      {prov_f}
    GROUP BY a.pack_name, a.province
    """

    conn = get_data(data_type="risk")
    df = conn.get_data(sql)
    conn.close()
    if df.empty:
        return df

    ref = datetime.strptime(end_date, "%Y-%m-%d")
    df["num_overdue_rate"] = df.apply(
        lambda r: r["overdue_order_count"] / r["matured_order_count"] if r["matured_order_count"] > 0 else 0, axis=1
    )
    df["unsubscribe_rate"] = df.apply(
        lambda r: r["unsubscribe_count"] / r["total_transaction_count"] if r["total_transaction_count"] > 0 else 0, axis=1
    )
    df["risk_pass_rate"] = df.apply(
        lambda r: r["risk_passed"] / r["risk_eligible"] if r["risk_eligible"] > 0 else 0, axis=1
    )
    # Supplementary: monthly avg count
    conn2 = get_data(data_type="risk")
    avg_df = conn2.get_data(f"""
        SELECT pack_name, AVG(cnt) as monthly_avg_count
        FROM (
            SELECT pack_name, DATE_FORMAT(complete_time, '%Y-%m') as ym, COUNT(*) as cnt
            FROM {_DWS}
            WHERE {_FILTER} AND complete_time >= '{start}'
              AND pack_name IS NOT NULL AND pack_name != ''
            GROUP BY pack_name, ym
        ) t
        GROUP BY pack_name
    """)
    conn2.close()
    if not avg_df.empty:
        df = df.merge(avg_df, on="pack_name", how="left")
        df["monthly_avg_count"] = df["monthly_avg_count"].fillna(0)

    return df
