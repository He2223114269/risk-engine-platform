"""
仿真配置文件 — 江西 v1（baseline 模板）

所有省份都可以从这个模板继承，只覆盖差异字段。
"""

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SimulationConfig:
    """单次仿真的完整配置"""

    # ── 基础信息 ──
    province: str = ""  # 省份（如 "江西省"）
    version: str = "v1"  # 本配置版本
    description: str = ""  # 说明
    base: str | None = None  # 继承自哪个预设

    # ── 数据 ──
    data_date: str = "2025-06-10"  # 训练数据截止日期（不包括此日期）
    data_start: str = "2025-01-01"  # 训练数据起始日期
    exclude_industry_advance: bool = True  # 是否排除行业先享

    # ── 策略 ──
    strategy_source: str = "sys_parameter"  # 策略配置来源
    strategy_business: str = "淘顺实时授信"  # 业务类型
    result_filter: str = "2511"  # 生效策略过滤

    # ── 评分 ──
    score_table: str = "risk_score_control"  # 通过率配置表
    cutoff_table: str = "risk_cutoff"  # cutoff 映射表

    # ── 决策树 ──
    tree_version: str = "jiangxi_v1"  # 决策树版本
    tree_features: list = field(
        default_factory=lambda: [
            "is_bw",  # 本网/异网
            "gender",  # 性别
            "age_interval",  # 年龄区间
            "amt_interval",  # 金额区间
            "onlinetime",  # 在网时长
            "province_is_one",  # 身份证省份=业务省份
        ]
    )

    # ── 特征分箱 ──
    age_bins: list = field(default_factory=lambda: [20, 25, 30, 35, 40, 45, 50, 55, 60, 65])
    age_labels: list = field(default_factory=lambda: list(range(1, 10)))
    amt_bins: list = field(default_factory=lambda: [0, 1000, 1500, 2000, 2500, 3000, float("inf")])
    amt_labels: list = field(default_factory=lambda: list(range(1, 7)))

    # ── 仿真参数 ──
    pass_ratios: list = field(
        default_factory=lambda: [  # 测试哪些通过率
            0.05,
            0.10,
            0.15,
            0.20,
            0.25,
            0.30,
            0.35,
            0.40,
            0.45,
            0.50,
            0.55,
            0.60,
            0.65,
            0.70,
            0.75,
            0.80,
            0.85,
            0.90,
            0.95,
        ]
    )
    lxf_table: str = "ods.ods_ts_order_white_list_control"  # 灵犀分所在表

    # ── 输出 ──
    output_format: str = "all"  # report / table / all

    def clone(self, **overrides: Any) -> "SimulationConfig":
        """返回一份深拷贝，并覆盖指定字段（用于省份继承）"""
        new = deepcopy(self)
        for k, v in overrides.items():
            setattr(new, k, v)
        return new

    def to_dict(self) -> dict:
        """转为纯字典（用于序列化）"""
        from dataclasses import asdict

        return asdict(self)


# ── 江西 v1 模板（baseline） ──

Jiangxi_v1 = SimulationConfig(
    province="江西省",
    version="v1",
    description="江西决策树模型 v1 — baseline",
    data_date="2025-06-10",
    data_start="2025-01-01",
)
