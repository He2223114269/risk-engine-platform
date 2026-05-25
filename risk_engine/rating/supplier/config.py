"""
代理商评级 - 维度权重配置
========================

各维度权重（总和 = 100%）：
  逾期质量    40%  ← 最硬的指标
  客群结构    15%  ← 老客/融合/本网占比
  规模体量    12%  ← 交易量和门店数
  翼支付评级  10%  ← 外部参考
  展业稳定性  10%  ← 活跃时长和持续性
  门店质量    8%   ← 优质/监管门店占比
  通过率异常  5%   ← 风控通过率偏离度

修改权重只改这个文件。
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class DimensionWeight:
    """单个维度的权重配置"""
    name: str          # 维度名称
    weight: float      # 权重（0~1 之间）
    fields: List[str]  # 该维度包含的原始字段


# ── 维度权重定义（总和 = 1.0） ──

DIMENSION_WEIGHTS: Dict[str, DimensionWeight] = {
    "逾期质量": DimensionWeight(
        name="逾期质量",
        weight=0.45,
        fields=["amt_overdue_rate", "num_overdue_rate", "bad_debt_rate"],
    ),
    "客群结构": DimensionWeight(
        name="客群结构",
        weight=0.15,
        fields=["old_customer_rate", "fusion_rate", "local_network_rate"],
    ),
    "规模体量": DimensionWeight(
        name="规模体量",
        weight=0.12,
        fields=["total_transaction_count", "monthly_avg_amount", "store_count"],
    ),
    "翼支付评级": DimensionWeight(
        name="翼支付评级",
        weight=0.13,
        fields=["yzf_rating"],
    ),
    "展业稳定性": DimensionWeight(
        name="展业稳定性",
        weight=0.10,
        fields=["active_months", "business_duration_days", "recent_inactive_days"],
    ),
    "通过率异常": DimensionWeight(
        name="通过率异常",
        weight=0.05,
        fields=["risk_pass_rate_deviation"],
    ),
}

# ── 评级阈值（百分比排名，并非分数绝对值） ──

RATING_THRESHOLDS = {
    "A": 0.01,    # 前 1%
    "B": 0.20,    # 1% ~ 20%
    # 其余为 C
}


# ── 翼支付评级映射分数 ──

YZF_RATING_SCORE = {
    "A": 100,
    "B": 80,
    "C": 60,
    "D": 40,
    "E": 20,
}


def validate_weights() -> bool:
    """校验权重总和是否为 1.0"""
    total = sum(dim.weight for dim in DIMENSION_WEIGHTS.values())
    if abs(total - 1.0) > 0.001:
        raise ValueError(f"权重总和不等于 1.0，当前为 {total}")
    return True
