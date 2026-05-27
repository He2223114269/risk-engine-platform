"""
门店评级 - 评级分配
========================

按综合评分排名分配 A/B/C。
有渠道等级的门店：渠道等级 = 拉黑 → 直接 C，优质 → 保底 B。
"""

from __future__ import annotations

import pandas as pd

from risk_engine.rating.base import assign_rating_by_percentile
from risk_engine.rating.store.config import RATING_THRESHOLDS


def assign_ratings(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    # 硬约束：拉黑渠道直接 C
    result["store_rating"] = assign_rating_by_percentile(
        result["compliance_score"],
        top_pct=RATING_THRESHOLDS["A"],
        good_pct=RATING_THRESHOLDS["B"],
    )

    # 渠道等级的硬约束
    blacklist = result["channel_level"].isin(["拉黑渠道"])
    result.loc[blacklist, "store_rating"] = "C"

    return result
