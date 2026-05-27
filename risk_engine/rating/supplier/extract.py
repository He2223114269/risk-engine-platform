"""
代理商评级 - 数据提取
========================

从 StarRocks 拉取各维度的原始数据，聚合到代理商粒度。
输出 DataFrame，字段对应 supplier_evaluation 表。
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from risk_engine.toolkit.connectors import get_data

# ════════════════════════════════════════════════════════════════
#  配置
# ════════════════════════════════════════════════════════════════

# DWS 宽表（订单 + 逾期 + 客群字段）
_DWS_TABLE = "dws.dws_credit_yzf_order_complete"
_SOURCE_FILTER = "source_business_type = '淘顺实时授信'"

# 风控申请表（关联风控结果）
_APPLY_TABLE = "ods.ods_ts_credit_yzf_order_grant_apply"
_RISK_TABLE = "ods.ods_ts_order_white_list_control"

# 门店等级表
_STORE_TABLE = "ods.ods_ts_v3_order_store"


# ════════════════════════════════════════════════════════════════
#  核心提取逻辑
# ════════════════════════════════════════════════════════════════


def extract_all(
    end_date: str | None = None,
    lookback_months: int = 12,
    province: str | None = None,
) -> pd.DataFrame:
    """
    一次查询提取所有维度的代理商汇总数据。

    参数:
        end_date: 截止日期 (yyyy-MM-dd)，默认今天
        lookback_months: 回溯月数（用于近6月月均等计算）
        province: 省份筛选（None = 全国）

    返回:
        DataFrame, 每行一个代理商
    """
    end_date = end_date or datetime.now().strftime("%Y-%m-%d")
    start_date = (
        datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=lookback_months * 30)
    ).strftime("%Y-%m-%d")

    province_filter = f"AND a.province = '{province}'" if province else ""

    sql = f"""
    WITH supplier_base AS (
        SELECT
            a.supplier_code,
            a.supplier_name,
            a.province,
            a.store_id,
            a.order_no,
            a.complete_time,
            a.order_amt_yuan,
            a.custtype,
            CASE WHEN a.custtype IN ('01', '06') THEN '老客户' ELSE '新客户' END AS old_new_flag,
            a.operator_real,
            -- 湖南单卡/融合判断
            CASE
                WHEN a.province = '湖南省' AND a.pack_name LIKE '%融合%' THEN '融合'
                WHEN a.province = '湖南省' THEN '单卡'
                ELSE NULL
            END AS package_type,
            a.step_num_repay_status,
            a.order_status,
            -- 风控通过判断：排除保证金白名单和特批白名单
            CASE
                WHEN b.first_risk_result IS NOT NULL THEN b.first_risk_result
                ELSE '正常'
            END AS first_risk_result
        FROM {_DWS_TABLE} a
        LEFT JOIN {_RISK_TABLE} b
            ON a.ct_user_id = b.order_no AND b.type = '淘顺实时授信'
        WHERE {_SOURCE_FILTER}
          AND a.complete_time >= '{start_date}'
          AND a.complete_time < DATE_ADD('{end_date}', INTERVAL 1 DAY)
          AND a.supplier_code IS NOT NULL
          AND a.supplier_code != ''
          {province_filter}
    )
    SELECT
        -- 展业时间
        supplier_code,
        -- 取最常用的代理商名称（一个 code 偶尔有多个 name，取频次最高的）
        MAX(supplier_name) AS supplier_name,
        province,
        MIN(complete_time) AS business_start_date,
        MAX(complete_time) AS last_active_date,
        COUNT(DISTINCT DATE_FORMAT(complete_time, '%Y-%m')) AS active_months,

        -- 规模
        COUNT(DISTINCT store_id) AS store_count,
        COUNT(*) AS total_transaction_count,
        COALESCE(SUM(order_amt_yuan), 0) AS total_transaction_amount,

        -- 近6月月均
        COALESCE(
            SUM(CASE
                WHEN complete_time >= DATE_SUB('{end_date}', INTERVAL 6 MONTH)
                THEN order_amt_yuan ELSE 0
            END) / 6, 0
        ) AS monthly_avg_amount,

        -- 最近一月交易额
        COALESCE(
            SUM(CASE
                WHEN DATE_FORMAT(complete_time, '%Y-%m') = DATE_FORMAT('{end_date}', '%Y-%m')
                THEN order_amt_yuan ELSE 0
            END), 0
        ) AS last_month_amount,

        -- 逾期统计
        SUM(CASE
            WHEN step_num_repay_status = 2 THEN 1 ELSE 0
        END) AS overdue_order_count,

        COUNT(DISTINCT CASE
            WHEN step_num_repay_status IN (1, 2) THEN order_no
        END) AS matured_order_count,

        -- 新老客
        SUM(CASE WHEN custtype = '00' THEN 1 ELSE 0 END) AS new_customer_count,
        SUM(CASE WHEN custtype IN ('01', '06') THEN 1 ELSE 0 END) AS old_customer_count,

        -- 本异网
        SUM(CASE WHEN operator_real IN ('1', '电信') THEN 1 ELSE 0 END) AS local_network_count,
        SUM(CASE WHEN operator_real IN ('2', '3', '移动', '联通') THEN 1 ELSE 0 END) AS external_network_count,

        -- 单卡/融合（仅湖南有效）
        SUM(CASE WHEN package_type = '单卡' THEN 1 ELSE 0 END) AS single_card_count,
        SUM(CASE WHEN package_type = '融合' THEN 1 ELSE 0 END) AS fusion_count,

        -- 退订
        SUM(CASE WHEN order_status IN ('违约退订', '提前结清') THEN 1 ELSE 0 END) AS unsubscribe_count,

        -- 风控通过率（剔除保证金和特批白名单）
        SUM(CASE
            WHEN first_risk_result NOT IN ('保证金白名单通过', '特批白名单用户')
            THEN 1 ELSE 0
        END) AS risk_eligible_count,

        SUM(CASE
            WHEN first_risk_result NOT IN ('保证金白名单通过', '特批白名单用户')
                 AND step_num_repay_status IN (0, 1)  -- 只要有还款记录就算通过（有分期）
            THEN 1 ELSE 0
        END) AS risk_passed_count

    FROM supplier_base
    GROUP BY supplier_code, province
    """

    conn = get_data(data_type="risk")
    df = conn.get_data(sql)
    conn.close()

    if df.empty:
        return df

    # 计算衍生指标
    df["business_duration_days"] = (
        datetime.strptime(end_date, "%Y-%m-%d") - pd.to_datetime(df["business_start_date"])
    ).dt.days

    df["recent_inactive_days"] = (
        datetime.strptime(end_date, "%Y-%m-%d") - pd.to_datetime(df["last_active_date"])
    ).dt.days

    df["amount_growth_rate"] = df.apply(
        lambda r: (
            (r["last_month_amount"] / r["monthly_avg_amount"] - 1)
            if r["monthly_avg_amount"] > 0
            else 0
        ),
        axis=1,
    )

    # 逾期率 = 逾期订单数 / 已到还款期的订单数
    df["num_overdue_rate"] = df.apply(
        lambda r: (
            r["overdue_order_count"] / r["matured_order_count"]
            if r["matured_order_count"] > 0
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

    # 退订率
    df["unsubscribe_rate"] = df.apply(
        lambda r: (
            r["unsubscribe_count"] / r["total_transaction_count"]
            if r["total_transaction_count"] > 0
            else 0
        ),
        axis=1,
    )

    return df


def extract_store_quality(
    supplier_codes: list,
    end_date: str | None = None,
) -> pd.DataFrame:
    """
    提取门店质量数据。
    从 ods_ts_v3_order_store 查每个代理商旗下门店的渠道等级。
    """
    if not supplier_codes:
        return pd.DataFrame()

    # 先用 DWS 获取 supplier_code → store_id 映射
    conn = get_data(data_type="risk")

    # 分批查（避免 IN 子句太长）
    batch_size = 500
    results = []
    for i in range(0, len(supplier_codes), batch_size):
        batch = supplier_codes[i : i + batch_size]
        codes_str = ",".join([f"'{c}'" for c in batch])

        sql = f"""
        SELECT DISTINCT supplier_code, store_id
        FROM {_DWS_TABLE}
        WHERE {_SOURCE_FILTER}
          AND supplier_code IN ({codes_str})
        """
        df = conn.get_data(sql)
        results.append(df)

    conn.close()

    if not results:
        return pd.DataFrame()

    mapping = pd.concat(results, ignore_index=True)
    store_ids = mapping["store_id"].unique().tolist()

    if not store_ids:
        return pd.DataFrame()

    # 查门店等级表（取最新一条，按 store_code 匹配）
    conn = get_data(data_type="risk")
    all_store_data = []
    for i in range(0, len(store_ids), batch_size):
        batch = store_ids[i : i + batch_size]
        ids_str = ",".join([f"'{s}'" for s in batch])

        sql = f"""
        SELECT store_code, channel_level, update_time
        FROM {_STORE_TABLE}
        WHERE isv = '淘顺'
          AND type = '翼支付实时授信'
          AND store_code IN ({ids_str})
        """
        df = conn.get_data(sql)
        if not df.empty:
            # 取最新一条（按 update_time 降序）
            df = df.sort_values("update_time", ascending=False)
            df = df.drop_duplicates(subset=["store_code"], keep="first")
            all_store_data.append(df)

    conn.close()

    if not all_store_data:
        return pd.DataFrame()

    store_levels = pd.concat(all_store_data, ignore_index=True)
    store_levels = store_levels[["store_code", "channel_level"]].drop_duplicates(
        subset=["store_code"], keep="first"
    )
    store_levels.rename(columns={"store_code": "store_id"}, inplace=True)

    # 关联到代理商
    merged = mapping.merge(store_levels, on="store_id", how="left")

    # 汇总每个代理商的门店质量
    result = (
        merged.groupby("supplier_code")
        .agg(
            store_count_actual=("store_id", "nunique"),
            high_quality_store_count=(
                "channel_level",
                lambda x: (x == "优质渠道").sum() if x.notna().any() else 0,
            ),
            regulated_store_count=(
                "channel_level",
                lambda x: x.isin(["监控渠道", "拉黑渠道"]).sum() if x.notna().any() else 0,
            ),
        )
        .reset_index()
    )

    return result


def extract_staff_count(
    supplier_codes: list,
    end_date: str | None = None,
) -> pd.DataFrame:
    """
    从申请表提取每个代理商的营业员人数。
    """
    if not supplier_codes:
        return pd.DataFrame()

    conn = get_data(data_type="risk")

    batch_size = 500
    results = []
    for i in range(0, len(supplier_codes), batch_size):
        batch = supplier_codes[i : i + batch_size]
        codes_str = ",".join([f"'{c}'" for c in batch])

        sql = f"""
        SELECT a.supplier_code, COUNT(DISTINCT b.seller_name) AS staff_count
        FROM (
            SELECT DISTINCT ct_user_id, supplier_code
            FROM {_DWS_TABLE}
            WHERE {_SOURCE_FILTER}
              AND supplier_code IN ({codes_str})
        ) a
        LEFT JOIN {_APPLY_TABLE} b
            ON a.ct_user_id = b.ct_user_id
            AND b.business_type = '02'
        GROUP BY a.supplier_code
        """
        df = conn.get_data(sql)
        results.append(df)

    conn.close()

    if results:
        return pd.concat(results, ignore_index=True)
    return pd.DataFrame()


def extract_yzf_rating(
    excel_path: str = None,
    conn=None,
) -> pd.DataFrame:
    """
    导入翼支付评级。
    默认从本地库的已导入数据读取，也可从 Excel 重新导入。
    """
    if conn is None:
        conn = get_data(data_type="local")

    try:
        df = conn.get_data(
            "SELECT supplier_id AS supplier_code, level AS yzf_rating " "FROM yzf_supplier_rating"
        )
    except Exception:
        # 如果本地库没有该表，返回空
        df = pd.DataFrame(columns=["supplier_code", "yzf_rating"])

    if conn is not None:
        conn.close()

    return df
