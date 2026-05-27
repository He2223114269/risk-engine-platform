"""套餐评级 - 评级分配"""

import pandas as pd

from risk_engine.rating.base import assign_rating_by_percentile
from risk_engine.rating.package.config import RATING_THRESHOLDS


def assign_ratings(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["package_rating"] = assign_rating_by_percentile(
        result["compliance_score"],
        top_pct=RATING_THRESHOLDS["A"],
        good_pct=RATING_THRESHOLDS["B"],
    )
    return result
