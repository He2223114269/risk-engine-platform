"""
代理商评级 - 评级分配
========================

根据综合评分排名，为每个代理商分配 A/B/C 评级。
"""

from __future__ import annotations

import pandas as pd
from typing import Optional

from risk_engine.rating.base import assign_rating_by_percentile
from risk_engine.rating.supplier.config import RATING_THRESHOLDS


def assign_ratings(df: pd.DataFrame) -> pd.DataFrame:
    """
    根据 compliance_score 分配 A/B/C 评级。

    参数:
        df: score_all() 输出的 DataFrame，需含 compliance_score 列

    返回:
        新增 supplier_rating 列的 DataFrame
    """
    result = df.copy()

    result["supplier_rating"] = assign_rating_by_percentile(
        result["compliance_score"],
        top_pct=RATING_THRESHOLDS["A"],
        good_pct=RATING_THRESHOLDS["B"],
    )

    return result


def get_benefit_by_rating(rating: str) -> dict:
    """
    根据评级返回保障金缴纳比例和每月可办单数。

    参数:
        rating: A/B/C

    返回:
        {"deposit_ratio": 0.6, "max_orders": 50}
    """
    BENEFITS = {
        "A": {"deposit_ratio": 0.60, "max_orders": 50},
        "B": {"deposit_ratio": 0.70, "max_orders": 40},
        "C": {"deposit_ratio": 0.80, "max_orders": 30},
    }
    return BENEFITS.get(rating, BENEFITS["C"])
