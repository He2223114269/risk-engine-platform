"""
门店评级 - 维度权重配置
========================

六维评分卡（权重总和 = 100%）：

  第一面：资产质量    30%  ← 最硬指标，逾期直接说明亏钱
  第二面：客群质量    20%  ← 带来什么客 = 什么质量
  第三面：渠道关联    15%  ← 门店在体系中的位置
  第四面：经营基础    15%  ← 干了多久、干了多少
  第五面：规模趋势    10%  ← 是在变好还是变差
  第六面：经营健康度  10%  ← 稳不稳、有没有异常

修改权重只改这个文件。
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class DimensionWeight:
    """单个维度的权重配置"""
    name: str
    weight: float
    fields: List[str]


DIMENSION_WEIGHTS: Dict[str, DimensionWeight] = {
    "资产质量": DimensionWeight(
        name="资产质量",
        weight=0.30,
        fields=["num_overdue_rate", "bad_debt_rate", "unsubscribe_rate"],
    ),
    "客群质量": DimensionWeight(
        name="客群质量",
        weight=0.20,
        fields=["new_customer_rate", "fusion_rate", "local_network_rate", "risk_pass_rate"],
    ),
    "渠道关联": DimensionWeight(
        name="渠道关联",
        weight=0.15,
        fields=["channel_level", "supplier_rating", "penalty_count"],
    ),
    "经营基础": DimensionWeight(
        name="经营基础",
        weight=0.15,
        fields=["business_duration_days", "total_transaction_count", "monthly_avg_amount"],
    ),
    "规模趋势": DimensionWeight(
        name="规模趋势",
        weight=0.10,
        fields=["amount_growth_rate", "overdue_trend", "new_customer_trend"],
    ),
    "经营健康度": DimensionWeight(
        name="经营健康度",
        weight=0.10,
        fields=["volume_cv", "month_end_ratio", "recent_inactive_days"],
    ),
}


# ── 评级阈值（按排名百分比） ──

RATING_THRESHOLDS = {
    "A": 0.01,    # 前 1%
    "B": 0.20,    # 1% ~ 20%
    # 其余为 C
}

# ── 门店渠道等级映射分数 ──

CHANNEL_LEVEL_SCORE = {
    "优质渠道": 100,
    "普通渠道": 70,
    "扶持渠道": 60,
    "拉灰渠道": 40,
    "管控渠道": 30,
    "监管渠道": 20,
    "拉黑渠道": 0,
}


def validate_weights() -> bool:
    total = sum(dim.weight for dim in DIMENSION_WEIGHTS.values())
    if abs(total - 1.0) > 0.001:
        raise ValueError(f"权重总和不等于 1.0，当前为 {total}")
    return True
