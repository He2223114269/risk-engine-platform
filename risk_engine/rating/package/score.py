"""套餐评级 - 评分逻辑"""
from __future__ import annotations
import pandas as pd
from risk_engine.rating.base import map_score_inverse, map_score_linear, map_score_by_percentile
from risk_engine.rating.package.config import DIMENSION_WEIGHTS


def score_all(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    # 数据充足
    result["data_sufficient"] = result.apply(
        lambda r: r["total_transaction_count"] >= 50 and r["active_months"] >= 3, axis=1
    )

    # 1. 逾期质量 35%
    result["score_overdue"] = result.apply(
        lambda r: (
            map_score_inverse(r["num_overdue_rate"], best=0.0, worst=0.10)
            if r["num_overdue_rate"] > 0 or r["data_sufficient"]
            else 50.0
        ), axis=1
    )

    # 2. 退订率 20%
    result["score_unsub"] = result["unsubscribe_rate"].apply(
        lambda x: map_score_inverse(x, best=0.0, worst=0.30)
    )

    # 3. 客群匹配度 15%
    result["old_customer_rate"] = result.apply(
        lambda r: r["old_customer_count"] / max(r["old_customer_count"] + r["new_customer_count"], 1), axis=1
    )
    result["score_customer"] = result["old_customer_rate"].apply(lambda x: 30 + x * 70)

    # 4. 规模体量 15%
    result["score_scale"] = map_score_by_percentile(result["total_transaction_count"])

    # 5. 风控通过率 10%
    pr_avg = result.groupby("province")["risk_pass_rate"].transform("mean")
    result["score_passrate"] = (result["risk_pass_rate"] - pr_avg).abs().apply(
        lambda x: map_score_inverse(x, best=0.0, worst=0.15)
    )

    # 6. 稳定性 5%
    result["score_stability"] = result["active_months"].apply(
        lambda x: map_score_linear(x, best=12.0, worst=0.0)
    )

    score_map = {
        "逾期质量": "score_overdue",
        "退订率": "score_unsub",
        "客群匹配度": "score_customer",
        "规模体量": "score_scale",
        "风控通过率": "score_passrate",
        "稳定性": "score_stability",
    }
    result["compliance_score"] = 0.0
    for dim, cfg in DIMENSION_WEIGHTS.items():
        col = score_map.get(dim)
        if col and col in result.columns:
            result["compliance_score"] += result[col] * cfg.weight
    result["compliance_score"] = result["compliance_score"].round(0).astype(int)
    return result
