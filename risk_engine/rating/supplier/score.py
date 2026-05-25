"""
代理商评级 - 评分逻辑
========================

将 extract.py 提取的各维度原始值，映射为 0-100 分，加权汇总。

v2 变更：
  1. 数据不足的代理商逾期率不给满分（从严）
  2. 客群结构改用 Sigmoid/Floor 映射（避免中位=0时一律低分）
  3. 空值按实际情况估算，不默认 0
  4. 剔除门店质量维度（数据覆盖不足）
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Optional

from risk_engine.rating.base import (
    map_score_inverse,
    map_score_linear,
    map_score_by_percentile,
    map_yzf_rating,
)
from risk_engine.rating.supplier.config import (
    DIMENSION_WEIGHTS,
    YZF_RATING_SCORE,
)


def score_all(df: pd.DataFrame) -> pd.DataFrame:
    """
    对所有代理商计算各维度评分 + 综合评分。
    """
    result = df.copy()

    # ── 标记数据充足度 ──
    # 数据不足：交易<20笔 或 活跃<2月 或 无到期订单
    # 这样的代理商逾期率看起来=0，但只是因为还没到还款期，不是真的表现好
    result["data_sufficient"] = result.apply(
        lambda r: (
            r["total_transaction_count"] >= 20
            and r["active_months"] >= 2
            and r.get("matured_order_count", 0) > 0
        ),
        axis=1,
    )
    # 有逾期记录的不管数据足不足都正常评分
    result["overdue_seen"] = result["num_overdue_rate"] > 0

    # ══════════════════════════════════════════════════════════
    #  1. 逾期质量评分（权重 45%）
    # ══════════════════════════════════════════════════════════

    result["score_overdue_num"] = result.apply(
        lambda r: (
            map_score_inverse(r["num_overdue_rate"], best=0.0, worst=0.10)
            if r["overdue_seen"]
            else (
                50.0 if not r["data_sufficient"]  # 数据不足+未逾期 → 不信任，给50
                else 100.0  # 数据充足+真逾期=0 → 真实优秀
            )
        ),
        axis=1,
    )
    result["score_overdue_quality"] = result["score_overdue_num"]

    # ══════════════════════════════════════════════════════════
    #  2. 客群结构评分（权重 15%）
    # ══════════════════════════════════════════════════════════

    # 老客占比
    result["old_customer_rate"] = result.apply(
        lambda r: r["old_customer_count"] / max(r["old_customer_count"] + r["new_customer_count"], 1),
        axis=1,
    )
    # 融合占比（仅湖南有效）
    result["fusion_rate"] = result.apply(
        lambda r: r["fusion_count"] / max(r["fusion_count"] + r["single_card_count"], 1)
        if (r["fusion_count"] + r["single_card_count"]) > 0 else 0.5,
        axis=1,
    )
    # 本网占比
    result["local_network_rate"] = result.apply(
        lambda r: r["local_network_count"] / max(r["local_network_count"] + r["external_network_count"], 1)
        if (r["local_network_count"] + r["external_network_count"]) > 0 else 0.5,
        axis=1,
    )

    # 客群结构：用带 Floor 的线性映射，0 值也有基础分
    # 老客占比 0%→30分, 50%→65分, 100%→100分
    result["score_old_customer"] = result["old_customer_rate"].apply(
        lambda x: 30 + x * 70
    )
    # 融合占比 0%→30分, 50%→65分, 100%→100分
    result["score_fusion"] = result["fusion_rate"].apply(
        lambda x: 30 + x * 70
    )
    # 本网占比 0%→30分, 50%→65分, 100%→100分
    result["score_local_network"] = result["local_network_rate"].apply(
        lambda x: 30 + x * 70
    )

    # 取三项的最高分和平均分的加权（鼓励特长，不惩罚短板）
    result["score_customer_structure"] = (
        result[["score_old_customer", "score_fusion", "score_local_network"]]
        .max(axis=1) * 0.5  # 最强项占50%
        + result[["score_old_customer", "score_fusion", "score_local_network"]]
        .mean(axis=1) * 0.5  # 平均水平占50%
    )
    # 最低保障：如果三项数据都凑不齐（全空），补50分
    result["score_customer_structure"] = result["score_customer_structure"].clip(30, 100)

    # ══════════════════════════════════════════════════════════
    #  3. 规模体量评分（权重 12%）
    # ══════════════════════════════════════════════════════════

    result["score_scale"] = map_score_by_percentile(result["total_transaction_count"])

    # ══════════════════════════════════════════════════════════
    #  4. 翼支付评级评分（权重 13%）
    # ══════════════════════════════════════════════════════════

    # 有评级 → 映射分数
    # 无评级 → 用逾期质量估算（逾期好→默认C+, 逾期差→默认D+）
    def _estimate_yzf(row):
        if pd.notna(row.get("yzf_rating")) and str(row["yzf_rating"]).strip():
            return map_yzf_rating(str(row["yzf_rating"]), YZF_RATING_SCORE)
        # 无评级时，用逾期质量估算
        overdue_score = row.get("score_overdue_quality", 50)
        if overdue_score >= 85:
            return 70  # 逾期优秀→默认B-
        elif overdue_score >= 60:
            return 55  # 逾期一般→默认C
        else:
            return 40  # 逾期差→默认D+

    result["score_yzf"] = result.apply(_estimate_yzf, axis=1)

    # ══════════════════════════════════════════════════════════
    #  5. 展业稳定性评分（权重 10%）
    # ══════════════════════════════════════════════════════════

    result["score_active_months"] = result["active_months"].apply(
        lambda x: map_score_linear(x, best=6.0, worst=0.0)
    )
    result["score_recency"] = result["recent_inactive_days"].apply(
        lambda x: map_score_inverse(x, best=0.0, worst=60.0)
    )
    result["score_stability"] = (
        result["score_active_months"] * 0.6 + result["score_recency"] * 0.4
    )

    # ══════════════════════════════════════════════════════════
    #  6. 通过率异常评分（权重 5%）
    # ══════════════════════════════════════════════════════════

    province_avg = result.groupby("province")["risk_pass_rate"].transform("mean")
    result["risk_pass_rate_deviation"] = result["risk_pass_rate"] - province_avg

    result["score_pass_rate"] = result["risk_pass_rate_deviation"].apply(
        lambda x: 100.0 if x >= 0
        else map_score_inverse(abs(x), best=0.0, worst=0.20)
    )

    # ══════════════════════════════════════════════════════════
    #  综合评分（加权汇总）
    # ══════════════════════════════════════════════════════════

    score_mapping = {
        "逾期质量": "score_overdue_quality",
        "客群结构": "score_customer_structure",
        "规模体量": "score_scale",
        "翼支付评级": "score_yzf",
        "展业稳定性": "score_stability",
        "通过率异常": "score_pass_rate",
    }

    result["compliance_score"] = 0.0
    for dim_name, weight_config in DIMENSION_WEIGHTS.items():
        score_col = score_mapping.get(dim_name)
        if score_col and score_col in result.columns:
            result["compliance_score"] += (
                result[score_col] * weight_config.weight
            )

    result["compliance_score"] = result["compliance_score"].round(0).astype(int)

    return result
