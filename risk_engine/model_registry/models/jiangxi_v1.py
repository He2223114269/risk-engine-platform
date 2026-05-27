"""江西 v1 决策树模型 — 训练自 江西省本异网模型.py"""
from __future__ import annotations

import pandas as pd

from risk_engine.model_registry.models.base import DecisionTreeModel


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


class JiangxiV1(DecisionTreeModel):
    """江西 v1 决策树 — 15 分支分类"""

    model_id = "jiangxi_v1"
    version = "1.0.0"
    description = "江西决策树，15分支，基于本网/异网→性别→年龄→金额→在网时长"
    features = ["is_bw", "gender", "age_interval", "amt_interval", "onlinetime", "province_is_one"]

    def classify(self, row: pd.Series) -> str:
        """单行分类 → 策略分支ID"""
        if row.get("is_bw", 0) <= 0.5:
            # ── 异网 ──
            if row.get("gender", 0) <= 0.5:
                if row.get("age_interval", 0) <= 3.5:
                    if row.get("amt_interval", 0) <= 2.5:
                        return "yw_fm_ad3_d1_9"
                    else:
                        return "yw_fm_ad3_g1_10"
                else:
                    return "yw_fm_ag3_11"
            else:
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
                if row.get("gender", 0) <= 0.5:
                    if row.get("onlinetime", 0) <= 4.5:
                        return "bw_g1_fm_td4_6"
                    else:
                        return "bw_g1_fm_tg4_7"
                else:
                    return "bw_g1_m_8"

    def get_branch_info(self, branch_id: str) -> str:
        return BRANCH_EXPLANATIONS.get(branch_id, "未知分支")

    def list_branches(self) -> list[str]:
        return list(BRANCH_EXPLANATIONS.keys())
