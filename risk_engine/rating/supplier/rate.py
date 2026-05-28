"""
代理商评级 - 评级分配
========================

按省份分别排名，每省独立分配 A/B/C 评级。
避免大省（如湖南）因总量大而挤占小省的评级名额。
"""

from __future__ import annotations

import pandas as pd

from risk_engine.rating.base import assign_rating_by_percentile
from risk_engine.rating.supplier.config import (
    A_MIN_ORDERS,
    B_MIN_ORDERS,
    RATING_THRESHOLDS,
)


def assign_ratings(df: pd.DataFrame) -> pd.DataFrame:
    """
    按省份分组，各省独立分配 A/B/C 评级。

    各省评级标准（各省单独排名）：
      A 级: 每省前 1%
      B 级: 每省前 1% ~ 10%
      C 级: 其余

    参数:
        df: score_all() 输出的 DataFrame，需含 compliance_score 和 province 列

    返回:
        新增 supplier_rating 列的 DataFrame
    """
    result = df.copy()
    result["supplier_rating"] = "C"  # 默认值

    # 按省份分组，各省独立评级
    for province, group in result.groupby("province"):
        if len(group) == 0:
            continue

        idx = group.index
        scores = result.loc[idx, "compliance_score"]

        ratings = assign_rating_by_percentile(
            scores,
            top_pct=RATING_THRESHOLDS["A"],
            good_pct=RATING_THRESHOLDS["B"],
        )
        result.loc[idx, "supplier_rating"] = ratings

    # ── 执行办单量硬门槛 ──
    result = apply_min_order_thresholds(result)

    return result


def apply_min_order_thresholds(df: pd.DataFrame) -> pd.DataFrame:
    """
    对评级结果应用办单量硬门槛。

    如果 A 级代理商的近12个月办单数 < A_MIN_ORDERS，降到 B。
    如果 B 级代理商的近12个月办单数 < B_MIN_ORDERS，降到 C。

    参数:
        df: 需含 supplier_rating 和 total_transaction_count 列
    """
    df = df.copy()

    # A → B（之前是 A 但办单不够）
    a_downgrade = (df["supplier_rating"] == "A") & (
        df["total_transaction_count"] < A_MIN_ORDERS
    )
    df.loc[a_downgrade, "supplier_rating"] = "B"
    n_a_downgraded = a_downgrade.sum()
    if n_a_downgraded:
        print(f"    ⚠️ 办单量不足 {A_MIN_ORDERS} 单: {n_a_downgraded} 个 A 级降为 B 级")

    # B → C（包括原本是 B + 刚从 A 降下来的）
    b_downgrade = (df["supplier_rating"] == "B") & (
        df["total_transaction_count"] < B_MIN_ORDERS
    )
    df.loc[b_downgrade, "supplier_rating"] = "C"
    n_b_downgraded = b_downgrade.sum()
    if n_b_downgraded:
        print(f"    ⚠️ 办单量不足 {B_MIN_ORDERS} 单: {n_b_downgraded} 个 B 级降为 C 级")

    return df


def get_benefit_by_rating(rating: str) -> dict:
    """
    根据评级返回保障金缴纳比例和每月可办单数。
    """
    BENEFITS = {
        "A": {"deposit_ratio": 0.60, "max_orders": 50},
        "B": {"deposit_ratio": 0.70, "max_orders": 40},
        "C": {"deposit_ratio": 0.80, "max_orders": 30},
    }
    return BENEFITS.get(rating, BENEFITS["C"])
