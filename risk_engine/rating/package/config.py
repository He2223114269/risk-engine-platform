"""
套餐评级 - 维度权重配置
========================

套餐是用产品维度去评价的：
  逾期质量   35%  ← 买这个套餐的人还款表现如何
  退订率     20%  ← 办完就退 = 推销问题
  客群匹配度 15%  ← 老客多=稳定，新客多=风险
  规模体量   15%  ← 办单量
  风控通过率  10%  ← 风控端的态度
  稳定性      5%  ← 在售时长
"""

from dataclasses import dataclass


@dataclass
class DimensionWeight:
    name: str
    weight: float
    fields: list[str]


DIMENSION_WEIGHTS: dict[str, DimensionWeight] = {
    "逾期质量": DimensionWeight(name="逾期质量", weight=0.35, fields=["num_overdue_rate"]),
    "退订率": DimensionWeight(name="退订率", weight=0.20, fields=["unsubscribe_rate"]),
    "客群匹配度": DimensionWeight(name="客群匹配度", weight=0.15, fields=["old_customer_rate"]),
    "规模体量": DimensionWeight(name="规模体量", weight=0.15, fields=["total_transaction_count"]),
    "风控通过率": DimensionWeight(name="风控通过率", weight=0.10, fields=["risk_pass_rate"]),
    "稳定性": DimensionWeight(name="稳定性", weight=0.05, fields=["active_months"]),
}

RATING_THRESHOLDS = {"A": 0.01, "B": 0.20}


def validate_weights() -> bool:
    total = sum(dim.weight for dim in DIMENSION_WEIGHTS.values())
    if abs(total - 1.0) > 0.001:
        raise ValueError(f"权重总和不等于 1.0，当前为 {total}")
    return True
