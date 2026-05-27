"""
门店评级 - 评分逻辑
========================

六维评分卡：
1. 资产质量 30%
2. 客群质量 20%
3. 渠道关联 15%
4. 经营基础 15%
5. 规模趋势 10%
6. 经营健康度 10%
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from risk_engine.rating.base import (
    map_score_by_percentile,
    map_score_inverse,
    map_score_linear,
)
from risk_engine.rating.store.config import CHANNEL_LEVEL_SCORE, DIMENSION_WEIGHTS


def score_all(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    # ── 数据充足标记 ──
    result["data_sufficient"] = result.apply(
        lambda r: r["total_transaction_count"] >= 20
        and r["active_months"] >= 2
        and r.get("matured_order_count", 0) > 0,
        axis=1,
    )

    # ══════════════════════════════════════════════════════════
    #  1. 资产质量 (30%)
    # ══════════════════════════════════════════════════════════

    # 逾期率
    result["score_overdue"] = result.apply(
        lambda r: (
            map_score_inverse(float(r["num_overdue_rate"]), best=0.0, worst=0.10)
            if float(float(r["num_overdue_rate"])) > 0 or r["data_sufficient"]
            else 50.0  # 数据不足且逾期为0 → 不信任
        ),
        axis=1,
    )
    # 退订率（反向）
    result["score_unsub"] = result["unsubscribe_rate"].apply(
        lambda x: map_score_inverse(x, best=0.0, worst=0.30)
    )
    result["score_asset_quality"] = result["score_overdue"] * 0.7 + result["score_unsub"] * 0.3

    # ══════════════════════════════════════════════════════════
    #  2. 客群质量 (20%)
    # ══════════════════════════════════════════════════════════

    result["new_customer_rate"] = result.apply(
        lambda r: r["new_customer_count"]
        / max(r["new_customer_count"] + r["old_customer_count"], 1),
        axis=1,
    )
    result["fusion_rate"] = result.apply(
        lambda r: r["fusion_count"] / max(r["fusion_count"] + r["single_card_count"], 1),
        axis=1,
    )
    result["local_network_rate"] = result.apply(
        lambda r: r["local_network_count"]
        / max(r["local_network_count"] + r["external_network_count"], 1),
        axis=1,
    )

    # 新客率高 = 风险高，反向映射
    result["score_new_customer"] = result["new_customer_rate"].apply(
        lambda x: map_score_inverse(x, best=0.0, worst=1.0)
    )
    result["score_fusion"] = result["fusion_rate"].apply(lambda x: 30 + x * 70)
    result["score_local"] = result["local_network_rate"].apply(lambda x: 30 + x * 70)
    # 通过率异常（偏离省均值越远越差——过高或过低都扣分）
    prov_avg = result.groupby("province")["risk_pass_rate"].transform("mean")
    result["risk_pass_rate_deviation"] = (result["risk_pass_rate"] - prov_avg).abs()
    result["score_pass_rate"] = result["risk_pass_rate_deviation"].apply(
        lambda x: map_score_inverse(x, best=0.0, worst=0.15)
    )

    # 客群质量 = 四维度等权
    result["score_customer_quality"] = (
        result["score_new_customer"] * 0.25
        + result["score_fusion"] * 0.25
        + result["score_local"] * 0.25
        + result["score_pass_rate"] * 0.25
    )

    # ══════════════════════════════════════════════════════════
    #  3. 渠道关联 (15%)
    # ══════════════════════════════════════════════════════════

    result["score_channel"] = result["channel_level"].apply(
        lambda x: CHANNEL_LEVEL_SCORE.get(x, 50) if pd.notna(x) else 50
    )
    result["score_supplier"] = result["supplier_rating"].apply(
        lambda x: {"A": 100, "B": 70, "C": 40}.get(x, 50) if pd.notna(x) else 50
    )
    result["score_channel_relation"] = (
        result["score_channel"] * 0.6 + result["score_supplier"] * 0.4
    )

    # ══════════════════════════════════════════════════════════
    #  4. 经营基础 (15%)
    # ══════════════════════════════════════════════════════════

    result["score_active"] = result["active_months"].apply(
        lambda x: map_score_linear(x, best=6.0, worst=0.0)
    )
    result["score_scale"] = map_score_by_percentile(result["total_transaction_count"])
    result["score_operation"] = result["score_active"] * 0.4 + result["score_scale"] * 0.6

    # ══════════════════════════════════════════════════════════
    #  5. 规模趋势 (10%)
    # ══════════════════════════════════════════════════════════

    # 交易额增速：适中为好（太高可能冲量，太低可能萎缩）
    result["score_growth"] = result["amount_growth_rate"].apply(
        lambda x: map_score_inverse(abs(float(x) - 0.2), best=0.0, worst=0.5)
    )
    # 逾期趋势（暂用整体逾期率代替，后续可用分月对比）
    result["score_overdue_trend"] = result["score_overdue"]  # placeholder
    result["score_trend"] = result["score_growth"] * 0.5 + result["score_overdue_trend"] * 0.5

    # ══════════════════════════════════════════════════════════
    #  6. 经营健康度 (10%)
    # ══════════════════════════════════════════════════════════

    result["score_recency"] = result["recent_inactive_days"].apply(
        lambda x: map_score_inverse(x, best=0.0, worst=60.0)
    )
    result["score_health"] = result["score_recency"]  # 额外维度后续可加

    # ══════════════════════════════════════════════════════════
    #  综合评分（加权汇总）
    # ══════════════════════════════════════════════════════════

    score_mapping = {
        "资产质量": "score_asset_quality",
        "客群质量": "score_customer_quality",
        "渠道关联": "score_channel_relation",
        "经营基础": "score_operation",
        "规模趋势": "score_trend",
        "经营健康度": "score_health",
    }

    result["compliance_score"] = 0.0
    for dim_name, cfg in DIMENSION_WEIGHTS.items():
        col = score_mapping.get(dim_name)
        if col and col in result.columns:
            result["compliance_score"] += result[col] * cfg.weight

    result["compliance_score"] = result["compliance_score"].round(0).astype(int)
    return result
