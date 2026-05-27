"""
决策树分类器 — 江西 v1 模型

将用户根据特征映射到 15 个策略分支。
决策树结构来源于《江西省本异网模型.py》训练产出，
分支 ID 与 risk_strategy_id_info.strategy_type 对应。
"""

from __future__ import annotations

import pandas as pd


# ── 策略分支说明 ──
BRANCH_EXPLANATIONS = {
    "yw_fm_ad3_d1_9":   "异网-女-年龄≤3-金额≤2",
    "yw_fm_ad3_g1_10":  "异网-女-年龄≤3-金额>2",
    "yw_fm_ag3_11":     "异网-女-年龄>3",
    "yw_m_ad3_d1_12":   "异网-男-年龄≤4(细分≤2)",
    "yw_m_ad3_d1_13":   "异网-男-年龄≤4(细分>2)",
    "yw_m_ag3_d15_14":  "异网-男-年龄>4-金额≤3",
    "yw_m_ag3_g15_15":  "异网-男-年龄>4-金额>3",
    "bw_d1_td4_fm_1":   "本网-低金额-短在网-女",
    "bw_d1_td4_m_2":    "本网-低金额-短在网-男",
    "bw_d1_tg4_fm_3":   "本网-低金额-长在网-女",
    "bw_d1_tg4_m_pn_4": "本网-低金额-长在网-男-外省",
    "bw_d1_tg4_m_pi_5": "本网-低金额-长在网-男-本省",
    "bw_g1_fm_td4_6":   "本网-高金额-女-短在网",
    "bw_g1_fm_tg4_7":   "本网-高金额-女-长在网",
    "bw_g1_m_8":        "本网-高金额-男",
}


def _classify(row: pd.Series) -> str:
    """
    单行分类 → 返回策略分支 ID。

    决策树逻辑（从江西模型提取）：
        第一层: is_bw (本网/异网)
            异网:
                第二层: gender
                    女: 第三层: age_interval
                    男: 第三层: age_interval → 第四层: amt_interval
            本网:
                第二层: amt_interval
                    低金额: 第三层: onlinetime → 第四层: gender → 第五层: province_is_one
                    高金额: 第三层: gender → 第四层: onlinetime
    """
    # 第一层: is_bw
    if row.get("is_bw", 0) <= 0.5:
        # ── 异网 ──
        if row.get("gender", 0) <= 0.5:
            # 女
            if row.get("age_interval", 0) <= 3.5:
                if row.get("amt_interval", 0) <= 2.5:
                    return "yw_fm_ad3_d1_9"
                else:
                    return "yw_fm_ad3_g1_10"
            else:
                return "yw_fm_ag3_11"
        else:
            # 男
            if row.get("age_interval", 0) <= 4.5:
                if row.get("age_interval", 0) <= 2.5:
                    return "yw_m_ad3_d1_12"
                else:
                    return "yw_m_ad3_d1_13"
            else:
                if row.get("amt_interval", 0) <= 3.5:
                    return "yw_m_ag3_d15_14"
                else:
                    return "yw_m_ag3_g15_15"
    else:
        # ── 本网 ──
        if row.get("amt_interval", 0) <= 2.5:
            # 低金额
            if row.get("onlinetime", 0) <= 4.5:
                if row.get("gender", 0) <= 0.5:
                    return "bw_d1_td4_fm_1"
                else:
                    return "bw_d1_td4_m_2"
            else:
                if row.get("gender", 0) <= 0.5:
                    return "bw_d1_tg4_fm_3"
                else:
                    if row.get("province_is_one", 0) <= 0.5:
                        return "bw_d1_tg4_m_pn_4"
                    else:
                        return "bw_d1_tg4_m_pi_5"
        else:
            # 高金额
            if row.get("gender", 0) <= 0.5:
                if row.get("onlinetime", 0) <= 4.5:
                    return "bw_g1_fm_td4_6"
                else:
                    return "bw_g1_fm_tg4_7"
            else:
                return "bw_g1_m_8"


def classify(data: pd.DataFrame) -> pd.DataFrame:
    """
    对 DataFrame 进行分类，新增 strategy_type 列。

    参数:
        data: 包含决策树所需特征的 DataFrame
              (is_bw, gender, age_interval, amt_interval, onlinetime, province_is_one)

    返回:
        追加了 strategy_type 列的 DataFrame
    """
    data["strategy_type"] = data.apply(_classify, axis=1)
    return data


def list_branches() -> list[str]:
    """返回所有策略分支 ID"""
    return list(BRANCH_EXPLANATIONS.keys())


def get_branch_info(branch_id: str) -> str:
    """返回某个分支的中文说明"""
    return BRANCH_EXPLANATIONS.get(branch_id, "未知分支")
