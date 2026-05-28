"""
风控模型仿真模块 — Simulation

用于上线前的 what-if 模拟：
  - 决策树分类（各策略分支客群划分）
  - cutoff 估计（通过率 → LXF 阈值 → 预期逾期率）
  - 结构化报告 + 配置快照（可复现）

使用方式：
    from risk_engine.simulation.pipeline import run
    from risk_engine.simulation.config.zhejiang_v1 import Zhejiang_v1

    result = run(Zhejiang_v1)
"""

from risk_engine.simulation.pipeline import run, run_from_config_file, list_presets
from risk_engine.simulation.snapshot import (
    save_snapshot, load_snapshot, list_snapshots, import_previous,
)
from risk_engine.simulation.config.presets import Jiangxi_v1, SimulationConfig
from risk_engine.simulation.estimator import estimate_all, estimate_branch, load_branch_pass_ratios
from risk_engine.model_registry import list_models
