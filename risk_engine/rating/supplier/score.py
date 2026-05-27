"""
代理商评级 - 评分逻辑
========================

将 extract.py 提取的各维度原始值，映射为 0-100 分，加权汇总。

v3 变更：
  1. 新增企查查维度：企业正规度、资本实力
  2. 无企查查数据的代理商自动调整权重，保证总分可比
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from risk_engine.rating.base import (
    map_score_by_percentile,
    map_score_inverse,
    map_score_linear,
    map_yzf_rating,
)
from risk_engine.rating.supplier.config import (
    YZF_RATING_SCORE,
    get_effective_weights,
)


def score_all(df: pd.DataFrame) -> pd.DataFrame:
    """
    对所有代理商计算各维度评分 + 综合评分。
    df 需要包含企查查字段（由 run.py 在调用前合并）。
    """
    result = df.copy()

    # ── 标记数据充足度 ──
    result["data_sufficient"] = result.apply(
        lambda r: (
            r["total_transaction_count"] >= 20
            and r["active_months"] >= 2
            and r.get("matured_order_count", 0) > 0
        ),
        axis=1,
    )
    result["overdue_seen"] = result["num_overdue_rate"] > 0

    # ── 标记是否有企查查数据 ──
    result["has_qichacha"] = result.get("register_status").notna() & (
        result.get("register_status") != ""
    )

    # ══════════════════════════════════════════════════════════
    #  1. 逾期质量评分（权重 40%）
    # ══════════════════════════════════════════════════════════

    result["score_overdue_num"] = result.apply(
        lambda r: (
            map_score_inverse(r["num_overdue_rate"], best=0.0, worst=0.10)
            if r["overdue_seen"]
            else (50.0 if not r["data_sufficient"] else 100.0)
        ),
        axis=1,
    )
    result["score_overdue_quality"] = result["score_overdue_num"]

    # ══════════════════════════════════════════════════════════
    #  2. 客群结构评分（权重 13%）
    # ══════════════════════════════════════════════════════════

    result["old_customer_rate"] = result.apply(
        lambda r: r["old_customer_count"]
        / max(r["old_customer_count"] + r["new_customer_count"], 1),
        axis=1,
    )
    result["fusion_rate"] = result.apply(
        lambda r: (
            r["fusion_count"] / max(r["fusion_count"] + r["single_card_count"], 1)
            if (r["fusion_count"] + r["single_card_count"]) > 0
            else 0.5
        ),
        axis=1,
    )
    result["local_network_rate"] = result.apply(
        lambda r: (
            r["local_network_count"]
            / max(r["local_network_count"] + r["external_network_count"], 1)
            if (r["local_network_count"] + r["external_network_count"]) > 0
            else 0.5
        ),
        axis=1,
    )

    result["score_old_customer"] = result["old_customer_rate"].apply(lambda x: 30 + x * 70)
    result["score_fusion"] = result["fusion_rate"].apply(lambda x: 30 + x * 70)
    result["score_local_network"] = result["local_network_rate"].apply(lambda x: 30 + x * 70)

    result["score_customer_structure"] = (
        result[["score_old_customer", "score_fusion", "score_local_network"]].max(axis=1) * 0.5
        + result[["score_old_customer", "score_fusion", "score_local_network"]].mean(axis=1) * 0.5
    ).clip(30, 100)

    # ══════════════════════════════════════════════════════════
    #  3. 规模体量评分（权重 11%）
    # ══════════════════════════════════════════════════════════

    result["score_scale"] = map_score_by_percentile(result["total_transaction_count"])

    # ══════════════════════════════════════════════════════════
    #  4. 翼支付评级评分（权重 11%）
    # ══════════════════════════════════════════════════════════

    def _estimate_yzf(row):
        if pd.notna(row.get("yzf_rating")) and str(row["yzf_rating"]).strip():
            return map_yzf_rating(str(row["yzf_rating"]), YZF_RATING_SCORE)
        overdue_score = row.get("score_overdue_quality", 50)
        if overdue_score >= 85:
            return 70
        elif overdue_score >= 60:
            return 55
        else:
            return 40

    result["score_yzf"] = result.apply(_estimate_yzf, axis=1)

    # ══════════════════════════════════════════════════════════
    #  5. 展业稳定性评分（权重 9%）
    # ══════════════════════════════════════════════════════════

    result["score_active_months"] = result["active_months"].apply(
        lambda x: map_score_linear(x, best=6.0, worst=0.0)
    )
    result["score_recency"] = result["recent_inactive_days"].apply(
        lambda x: map_score_inverse(x, best=0.0, worst=60.0)
    )
    result["score_stability"] = result["score_active_months"] * 0.6 + result["score_recency"] * 0.4

    # ══════════════════════════════════════════════════════════
    #  6. 通过率异常评分（权重 5%）
    # ══════════════════════════════════════════════════════════

    province_avg = result.groupby("province")["risk_pass_rate"].transform("mean")
    result["risk_pass_rate_deviation"] = result["risk_pass_rate"] - province_avg

    result["score_pass_rate"] = result["risk_pass_rate_deviation"].apply(
        lambda x: 100.0 if x >= 0 else map_score_inverse(abs(x), best=0.0, worst=0.20)
    )

    # ══════════════════════════════════════════════════════════
    #  7. 企业正规度评分（权重 6%）
    # ══════════════════════════════════════════════════════════

    def _score_enterprise_regularity(row):
        if not row["has_qichacha"]:
            return 50.0  # 无数据→中性分，权重会被重分配
        score = 60.0  # 基础分

        # 登记状态：存续→加分，注销/吊销→扣分
        status = str(row.get("register_status", "")).strip()
        if "存续" in status:
            score += 20
        elif "注销" in status or "吊销" in status:
            score -= 30

        # 企业类型：有限公司比个体户正规
        etype = str(row.get("enterprise_type", "")).strip()
        if "有限责任" in etype:
            score += 15
        elif "股份" in etype:
            score += 10
        elif "个人独资" in etype:
            score -= 5
        # 个体户不扣分（大部分是个体户，一视同仁）

        return max(10, min(100, score))

    result["score_enterprise_regularity"] = result.apply(_score_enterprise_regularity, axis=1)

    # ══════════════════════════════════════════════════════════
    #  8. 资本实力评分（权重 5%）
    # ══════════════════════════════════════════════════════════

    def _score_capital(row):
        if not row["has_qichacha"]:
            return 50.0  # 无数据→中性分，权重被重分配

        capital_str = str(row.get("registered_capital", "")).strip()
        if capital_str in ["-", "—", "", "nan", "None"]:
            return 50.0  # 未公示→中性

        # 提取数字（"999万元" → 999, "2万元" → 2, "999万美元" → 999*7）
        import re

        match = re.search(r"([\d.]+)\s*万元", capital_str)
        try:
            capital = float(match.group(1)) if match else 0
        except Exception:
            return 50.0

        # 映射：0万→20分, 10万→40分, 50万→60分, 200万→80分, 1000万+→100分
        # 用对数映射更合理
        if capital <= 0:
            return 20
        elif capital > 1000:
            return 100
        else:
            return min(100, 20 + 80 * (np.log10(max(capital, 0.1)) / np.log10(1000)))

    result["score_capital"] = result.apply(_score_capital, axis=1)

    # ══════════════════════════════════════════════════════════
    #  综合评分（动态权重）
    # ══════════════════════════════════════════════════════════

    score_mapping = {
        "逾期质量": "score_overdue_quality",
        "客群结构": "score_customer_structure",
        "规模体量": "score_scale",
        "翼支付评级": "score_yzf",
        "展业稳定性": "score_stability",
        "通过率异常": "score_pass_rate",
        "企业正规度": "score_enterprise_regularity",
        "资本实力": "score_capital",
    }

    def _calc_composite(row):
        """每个代理商独立计算加权总分，动态处理翼支付评级和企查查权重"""
        has_yzf = row.get("yzf_rating") is not None and str(row.get("yzf_rating", "")).strip() != ""
        has_qcc = row.get("has_qichacha", False)
        weights = get_effective_weights(has_yzf=has_yzf, has_qichacha=has_qcc)

        total_score = 0.0
        for dim_name, dim_weight in weights.items():
            score_col = score_mapping.get(dim_name)
            if score_col and score_col in row.index:
                total_score += row[score_col] * dim_weight

        return int(round(total_score))

    result["compliance_score"] = result.apply(_calc_composite, axis=1)

    return result
