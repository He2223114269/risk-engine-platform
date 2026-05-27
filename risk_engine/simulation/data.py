"""
仿真数据准备 — 拉省份数据 + 特征工程

职责：
1. 从 StarRocks 拉取指定省份的申请数据 + DWS 数据 + 灵犀分
2. 特征工程（年龄区间、金额区间、在网时长、本异网等）
3. 不自己实现分箱/编码，调 core/feature_engineering

但当前 core/feature_engineering 还是骨架，这里先内嵌基础分箱逻辑，
后续迁移到 feature_engineering 后只保留取数。
"""

from __future__ import annotations

import os
import sys
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

# ── 项目路径 ──
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from risk_engine.simulation.config.presets import SimulationConfig  # noqa: E402
from risk_engine.toolkit.connectors import get_data  # noqa: E402

# ── 省份身份证前缀映射 ──
PROVINCE_CODE_MAP = {
    "11": "北京",
    "12": "天津",
    "13": "河北",
    "14": "山西",
    "15": "内蒙古",
    "21": "辽宁",
    "22": "吉林",
    "23": "黑龙江",
    "31": "上海市",
    "32": "江苏",
    "33": "浙江",
    "34": "安徽",
    "35": "福建",
    "36": "江西省",
    "37": "山东",
    "41": "河南",
    "42": "湖北",
    "43": "湖南省",
    "44": "广东",
    "45": "广西壮族自治区",
    "46": "海南省",
    "50": "重庆",
    "51": "四川",
    "52": "贵州省",
    "53": "云南",
    "54": "西藏",
    "61": "陕西",
    "62": "甘肃",
    "63": "青海",
    "64": "宁夏回族自治区",
    "65": "新疆",
}


def _extract_province_from_id(id_card: str) -> str:
    """从身份证前2位提取省份"""
    if not isinstance(id_card, str) or len(id_card) < 2:
        return "未知"
    return PROVINCE_CODE_MAP.get(id_card[:2], "未知")


def fetch(mode_config: SimulationConfig) -> pd.DataFrame:
    """
    拉取一个指定省份的仿真数据。

    流程：
    1. 星环取申请表 + DWS 宽表 + 灵犀分
    2. 合并、特征工程
    3. 返回带特征 + 标签 + LXF 的 DataFrame
    """
    province = mode_config.province
    data_date = mode_config.data_date
    data_start = mode_config.data_start

    conn = get_data(data_type="risk")

    # ── 1. 取申请表数据（子查询去重）──
    apply_sql = f"""
    SELECT * FROM (
        SELECT
            Decrypt(user_name_enc) AS user_name,
            Decrypt(id_number_enc) AS id_number,
            order_amt,
            store_addr_province,
            Decrypt(mobile_no_enc) AS mobile_no,
            pack_name,
            goods_type,
            case when mobile_no = bank_mobile_no then 1 else 0 end AS is_same_telelphon,
            round(return_red_envelope / pack_price, 4) AS subsidy_rate,
            case when nation = '汉' then '汉族' when nation is not null then '非汉族' else '未知' end AS nation,
            is_married,
            education,
            approval_time,
            apply_status,
            row_number() OVER (
                PARTITION BY user_name_enc, id_number_enc
                ORDER BY CASE WHEN apply_status = '授信成功' THEN 0 ELSE 1 END
            ) AS rt
        FROM ods.ods_ts_credit_yzf_order_grant_apply
        WHERE custtype = '00' AND store_addr_province = '{province}'
    ) t WHERE rt = 1
    """
    apply_data = conn.get_data(apply_sql)

    if apply_data.empty:
        print(f"  ⚠️ {province} 申请表无数据")
        conn.close()
        return pd.DataFrame()

    # 获取手机号列表
    mobile_list = apply_data["mobile_no"].dropna().unique().tolist()

    # ── 2. 取 DWS 宽表 ──
    dws_sql = f"""
    SELECT
        decrypt(id_card_no) AS id_card_no,
        decrypt(id_card_name) AS id_card_name,
        decrypt(grant_mobile) AS grant_mobile,
        order_amt_yuan,
        province,
        old_new_customer,
        pack_name,
        complete_time,
        contact_mobile,
        case when total_due_count - total_repaid_count >= 1 then 1 else 0 end AS is_over_due
    FROM dws.dws_credit_yzf_order_complete
    WHERE source_business_type = '淘顺实时授信'
      AND province = '{province}'
      AND custtype = '00'
      AND complete_time >= '{data_start}'
      AND complete_time < '{data_date}'
    """
    dws_data = conn.get_data(dws_sql)

    # ── 3. 取灵犀分（只拉目标省份）──
    lxf_sql = f"""
    WITH computed_lxf AS (
        SELECT
            Decrypt(user_name_enc) AS user_name,
            Decrypt(id_card_enc) AS id_card,
            Decrypt(service_telphone_enc) AS service_telphone,
            second_risk_result,
            lxf
        FROM ods.ods_ts_order_white_list_control
        WHERE type = '淘顺实时授信' AND province = '{province}'
    ),
    ranked_data AS (
        SELECT
            id_card, user_name, service_telphone, lxf,
            ROW_NUMBER() OVER (
                PARTITION BY user_name, id_card
                ORDER BY CASE WHEN second_risk_result = '通过' THEN 0 ELSE 1 END, lxf DESC
            ) AS rn
        FROM computed_lxf
    )
    SELECT user_name, id_card, service_telphone, lxf
    FROM ranked_data WHERE rn = 1
    """

    lxf_data = conn.get_data(lxf_sql)  # 先取全量，后面过滤也不会有太多

    # ── 4. 取在网时长 ──
    online_sql = """
    SELECT telephone,
           CASE WHEN operator_real = '3' THEN '1' ELSE '0' END AS is_bw,
           onlinetime,
           DATE(add_time) AS add_time
    FROM ods.ods_bl_wind_tel_onlinetime
    WHERE business_type = '淘顺翼支付实时授信'
      AND telephone
    """

    online_data = conn.injoin_data(mobile_list, online_sql)

    # ── 5. 合并数据 ──
    # 申请表 + DWS
    data = apply_data.merge(
        dws_data,
        left_on=["id_number", "user_name"],
        right_on=["id_card_no", "id_card_name"],
        how="left",
    )

    # 去重
    data = data.drop_duplicates(subset=["id_number"], keep="first")

    # 合并在网时长
    data = pd.merge(
        data,
        online_data,
        left_on="mobile_no",
        right_on="telephone",
        how="left",
    )

    # 合并灵犀分
    data = data.merge(
        lxf_data[["user_name", "id_card", "lxf"]],
        left_on=["user_name", "id_number"],
        right_on=["user_name", "id_card"],
        how="left",
    )
    # LXF 转 float
    data["lxf"] = pd.to_numeric(data["lxf"], errors="coerce")

    conn.close()

    # ── 6. 特征工程 ──
    # 关键列转数值
    data["is_over_due"] = pd.to_numeric(data["is_over_due"], errors="coerce").fillna(0).astype(int)
    data["lxf"] = pd.to_numeric(data["lxf"], errors="coerce")
    data = _engineering(data, mode_config)

    return data


def _engineering(data: pd.DataFrame, cfg: SimulationConfig) -> pd.DataFrame:
    """特征工程（后续迁移到 core/feature_engineering）"""

    # 身份证信息
    data["id_number"] = data["id_number"].astype(str)

    # 性别（从身份证第17位）
    data["gender"] = np.where(
        data["id_number"].str[16].astype(int, errors="ignore") % 2 == 1, 1, 0
    )  # 1=男, 0=女

    # 年龄 + 年龄区间
    def _calc_age(id_str):
        try:
            birth = datetime.strptime(id_str[6:14], "%Y%m%d")
            today = datetime.today()
            return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        except (ValueError, AttributeError):
            return None

    data["age"] = data["id_number"].apply(_calc_age)
    data["age_interval"] = pd.cut(
        data["age"],
        cfg.age_bins,
        labels=cfg.age_labels,
    )

    # 金额区间
    data["order_amt_yuan"] = pd.to_numeric(data["order_amt_yuan"], errors="coerce")
    data["order_amt"] = pd.to_numeric(data["order_amt"], errors="coerce")
    data["order_amt_yuan"] = np.where(
        data["order_amt_yuan"].isna(),
        data["order_amt"] / 100,
        data["order_amt_yuan"],
    )
    data["amt_interval"] = pd.cut(
        data["order_amt_yuan"].fillna(0),
        cfg.amt_bins,
        labels=cfg.amt_labels,
    )

    # 本异网
    data["is_bw"] = data["is_bw"].fillna(0).astype(float)

    # 在网时长
    data["onlinetime"] = pd.to_numeric(data["onlinetime"], errors="coerce").fillna(-1).astype(float)

    # 省份是否一致
    data["province_id"] = data["id_number"].apply(_extract_province_from_id)
    data["province_is_one"] = np.where(data["province_id"] == cfg.province, 1, 0)

    # 新老客
    data["old_new_customer"] = np.where(data["onlinetime"].isin([3, 4, 5]), "老客户", "新客户")

    # 业务场景字段（兼容新旧列名）
    if "province" in data.columns:
        pass  # DWS 的 province 列

    return data
