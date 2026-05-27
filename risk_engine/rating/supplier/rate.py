"""
代理商评级 - 评级分配
========================

按省份分别排名，每省独立分配 A/B/C 评级。
避免大省（如湖南）因总量大而挤占小省的评级名额。
"""

from __future__ import annotations

import pandas as pd

from risk_engine.rating.base import assign_rating_by_percentile
from risk_engine.rating.supplier.config import RATING_THRESHOLDS


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

    return result


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
