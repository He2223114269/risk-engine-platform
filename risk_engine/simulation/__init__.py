"""
风控模型仿真模块 — Simulation

用于上线前的 what-if 模拟：
  - 决策树分类（各策略分支客群划分）
  - cutoff 估计（通过率 → LXF 阈值 → 预期逾期率）
  - 结构化报告 + 配置快照（可复现）

使用方式：

    # 配置驱动运行
    from risk_engine.simulation.pipeline import run
    from risk_engine.simulation.config.zhejiang_v1 import Zhejiang_v1

    result = run(Zhejiang_v1)

    # 继承历史快照重新跑
    from risk_engine.simulation.snapshot import import_previous
    from risk_engine.simulation.config.presets import Jiangxi_v1

    prev = import_previous("zhejiang", "v1", "2026-05-27_1500")
    new_config = Jiangxi_v1.clone(**{"province": "浙江省", ...})
    result = run(new_config)
"""

from risk_engine.simulation.pipeline import run, run_from_config_file
from risk_engine.simulation.snapshot import (
    save_snapshot, load_snapshot, list_snapshots, import_previous,
)
from risk_engine.simulation.config.presets import SimulationConfig, Jiangxi_v1
from risk_engine.simulation.classifier import classify, list_branches
from risk_engine.simulation.estimator import estimate_all, estimate_branch
