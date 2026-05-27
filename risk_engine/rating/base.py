"""
评级共享函数库
==============
通用的评分映射和评级分配工具。

所有具体评级任务（代理商/门店/套餐）共用的基础函数，
放在这里避免每个模块重复写相同的映射逻辑。

用法:
    from risk_engine.rating.base import map_score_inverse, assign_rating_by_percentile

    # 逾期率 2% → 80 分
    score = map_score_inverse(0.02, best=0.0, worst=0.10)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Optional

# ════════════════════════════════════════════════════════════════
#  评分映射
# ════════════════════════════════════════════════════════════════


def map_score_inverse(
    value: float,
    best: float = 0.0,
    worst: float = 0.10,
    score_max: float = 100.0,
    score_min: float = 0.0,
    clip: bool = True,
) -> float:
    """
    反向线性映射：值越低分越高。

    用于逾期率、退订率、新客占比等"越小越好"的指标。

    参数:
        value:  原始值（如 0.02 = 2%）
        best:   最高分对应的原始值（默认 0%）
        worst:  最低分对应的原始值（默认 10%）
        score_max:  最高分（默认 100）
        score_min:  最低分（默认 0）
        clip:      是否截断到 [score_min, score_max]

    示例:
        >>> map_score_inverse(0.02)       # 逾期率 2%
        80.0

        >>> map_score_inverse(0.12)       # 逾期率 12%，超过 worst
        0.0
    """
    if worst == best:
        return score_max

    score = score_max - (value - best) / (worst - best) * (score_max - score_min)

    if clip:
        score = max(score_min, min(score_max, score))

    return score


def map_score_linear(
    value: float,
    best: float = 1.0,
    worst: float = 0.0,
    score_max: float = 100.0,
    score_min: float = 0.0,
    clip: bool = True,
) -> float:
    """
    正向线性映射：值越高分越高。

    用于老客占比、融合占比、本网占比等"越高越好"的指标。

    参数:
        value:  原始值（如 0.80 = 80%）
        best:   最高分对应的原始值
        worst:  最低分对应的原始值
    """
    if best == worst:
        return score_max

    score = (value - worst) / (best - worst) * (score_max - score_min) + score_min

    if clip:
        score = max(score_min, min(score_max, score))

    return score


def map_score_by_percentile(
    series: pd.Series,
    reverse: bool = False,
) -> pd.Series:
    """
    按百分位排名给分。

    适用于没有绝对标准、全靠相对位置的指标，如"规模体量"。

    参数:
        series:  原始值列
        reverse: True=值越低分越高（如逾期率用百分位）

    返回:
        0-100 的分数
    """
    ranks = series.rank(method="average", ascending=not reverse)
    scores = (ranks - 1) / (len(ranks) - 1) * 100 if len(ranks) > 1 else pd.Series([50.0])
    return scores


def map_yzf_rating(rating: str, rating_score_map: dict) -> float:
    """
    翼支付评级映射分数。

    参数:
        rating: 评级字符串（A/B/C/D/E）
        rating_score_map: 评级→分数映射表

    返回:
        0-100 分数
    """
    return float(rating_score_map.get(rating, 0))


# ════════════════════════════════════════════════════════════════
#  评级分配
# ════════════════════════════════════════════════════════════════


def assign_rating_by_percentile(
    scores: pd.Series,
    top_pct: float = 0.01,
    good_pct: float = 0.20,
) -> pd.Series:
    """
    按综合分数排名分配 A/B/C 评级。

    参数:
        scores:    综合分数列（0-100）
        top_pct:   A 级占比（默认前 1%）
        good_pct:  A+B 级占比（默认前 20%）

    返回:
        ["A", "B", "C", ...] 的 Series
    """
    n = len(scores)
    ranks = scores.rank(method="min", ascending=False)

    def _rating(rank):
        if rank <= n * top_pct:
            return "A"
        elif rank <= n * good_pct:
            return "B"
        else:
            return "C"

    return ranks.apply(_rating)
