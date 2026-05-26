"""
代理商评级 - 维度权重配置
========================

各维度权重（总和 = 100%）：
  逾期质量    32%  ← 有翼支付评级时下调，无评级时上调
  客群结构    10%
  规模体量     9%
  翼支付评级  28%  ← 有评级时重点评估（外部强信号）
  展业稳定性   7%
  通过率异常   5%
  企业正规度   5%
  资本实力     4%

注：以上为"有翼支付评级 + 有企查查"时的基准权重。
  无翼支付评级 → 28% 翼支付权重按比例分给其他维度
  无企查查数据 → 9% 企查查权重按比例分给其他维度
"""

from dataclasses import dataclass
from typing import Dict, List, Set


@dataclass
class DimensionWeight:
    """单个维度的权重配置"""
    name: str
    weight: float
    fields: List[str]


# ── 基础权重（假设所有数据源都齐全） ──

BASE_WEIGHTS: Dict[str, float] = {
    "逾期质量": 0.32,
    "客群结构": 0.10,
    "规模体量": 0.09,
    "翼支付评级": 0.28,
    "展业稳定性": 0.07,
    "通过率异常": 0.05,
    "企业正规度": 0.05,
    "资本实力": 0.04,
}

# ── 根据数据有无动态调整的维度 ──
# 有数据时用完整权重，无数据时权重归零并重新分配
CONDITIONAL_DIMENSIONS: Dict[str, Set[str]] = {
    "yzf": {"翼支付评级"},      # 依赖翼支付评价表
    "qichacha": {"企业正规度", "资本实力"},  # 依赖企查查
}

# ── 评级阈值 ──

RATING_THRESHOLDS = {
    "A": 0.01,    # 每省前 1%
    "B": 0.10,    # 每省前 1% ~ 10%
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
    """校验基础权重总和是否为 1.0"""
    total = sum(BASE_WEIGHTS.values())
    if abs(total - 1.0) > 0.001:
        raise ValueError(f"权重总和不等于 1.0，当前为 {total}")
    return True


def get_effective_weights(
    has_yzf: bool = True,
    has_qichacha: bool = True,
) -> Dict[str, float]:
    """
    根据实际数据覆盖情况，返回动态调整后的权重。

    原理：
      没有 YZF/企查查数据的维度，其权重按比例分给其他有数据的维度。
      保证总分始终可比（总和 = 100%）。

    参数:
        has_yzf:      该代理商是否有翼支付评级
        has_qichacha: 该代理商是否有企查查数据

    返回:
        {维度名: 权重} 字典
    """
    # 确定哪些维度可用
    available = set(BASE_WEIGHTS.keys())

    if not has_yzf:
        available -= CONDITIONAL_DIMENSIONS["yzf"]
    if not has_qichacha:
        available -= CONDITIONAL_DIMENSIONS["qichacha"]

    # 获取可用维度的原始权重
    available_weights = {d: BASE_WEIGHTS[d] for d in available}
    missing_weight = sum(BASE_WEIGHTS[d] for d in BASE_WEIGHTS if d not in available)
    available_total = sum(available_weights.values())

    if available_total == 0:
        return available_weights

    # 缺失的权重按比例分配给可用维度
    return {
        d: w + w * missing_weight / available_total
        for d, w in available_weights.items()
    }


# 启动时校验
validate_weights()
