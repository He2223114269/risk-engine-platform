"""
仿真编排器 — 一次完整仿真的入口

流程:
  1. 加载配置
  2. 拉取数据
  3. 决策树分类
  4. cutoff 估计（各通过率下的 LXF 阈值 + 逾期率）
  5. 生成报告
  6. 保存快照
"""

from __future__ import annotations

import sys
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

from risk_engine.simulation.config.presets import SimulationConfig
from risk_engine.simulation import data as sim_data
from risk_engine.simulation import classifier
from risk_engine.simulation import estimator
from risk_engine.simulation import report as sim_report
from risk_engine.simulation import snapshot


def run(
    mode_config: SimulationConfig,
    *,
    label: str | None = None,
    save: bool = True,
    verbose: bool = True,
) -> dict:
    """
    运行一次完整仿真。

    参数:
        config:  SimulationConfig 对象（省份配置）
        label:   快照标签（默认时间戳）
        save:    是否保存结果快照
        verbose: 是否打印进度

    返回:
        {
            "config": dict,          # 完整配置快照
            "parameters": pd.DataFrame,  # cutoff 估计结果
            "summary": dict,         # 汇总
            "report": str,           # Markdown 报告
            "folder": Path | None,   # 快照文件夹
        }
    """
    province = mode_config.province

    if verbose:
        print(f"\n{'='*60}")
        print(f"  仿真运行 — {province} {mode_config.version}")
        print(f"{'='*60}")
        print(f"  数据范围: {mode_config.data_start} ~ {mode_config.data_date}")
        print(f"  决策树:   {mode_config.tree_version}")
        print(f"  测试通过率: {len(mode_config.pass_ratios)} 个级别")

    # ── 步骤 1: 拉取数据 ──
    if verbose:
        print(f"\n  [1/5] 拉取 {province} 数据...")

    data = sim_data.fetch(mode_config)

    if data.empty:
        raise ValueError(f"{province} 无可用数据")

    if verbose:
        print(f"        已获取 {len(data):,} 条记录")

    # ── 步骤 2: 决策树分类 ──
    if verbose:
        print(f"  [2/5] 决策树分类...")

    data = classifier.classify(data)

    branch_counts = data["strategy_type"].value_counts()
    if verbose:
        print(f"        分为 {len(branch_counts)} 个策略分支")

    # ── 步骤 3: cutoff 估计 ──
    if verbose:
        print(f"  [3/5] cutoff 估计（{len(mode_config.pass_ratios)} 个通过率级别）...")

    params = estimator.estimate_all(
        data,
        pass_ratios=mode_config.pass_ratios,
        score_col="lxf",
        label_col="is_over_due",
    )

    if verbose:
        combos = params.groupby("strategy_type").size().sum()
        print(f"        生成 {len(params):,} 条估算结果")

    # ── 步骤 4: 生成报告 ──
    if verbose:
        print(f"  [4/5] 生成报告...")

    full_config = mode_config.to_dict()
    summary = sim_report.create_summary(params)

    # 关注 50% 通过率下的各分支表现
    best_worst = sim_report.show_best_worst(params)
    if verbose:
        print(f"\n{best_worst}")

    report_md = sim_report.generate_markdown(params, full_config)

    # ── 步骤 5: 保存快照 ──
    folder = None
    if save:
        if verbose:
            print(f"\n  [5/5] 保存快照...")

        folder = snapshot.save_snapshot(
            config=full_config,
            province=mode_config.province.replace("省", "").replace("市", ""),
            version=mode_config.version,
            label=label,
        )

        snapshot.save_result(folder, params, summary, report_md)

        if verbose:
            print(f"        已保存至: {folder}")

    if verbose:
        print(f"\n  ✅ 仿真完成")

    return {
        "config": full_config,
        "parameters": params,
        "summary": summary,
        "report": report_md,
        "folder": folder,
        "data": data,
    }


def run_from_config_file(config_path: str, **overrides) -> dict:
    """
    从配置文件（Python 文件）加载配置并运行仿真。

    用法:
        run_from_config_file("risk_engine/simulation/config/zhejiang_v1.py")

    或覆盖参数:
        run_from_config_file("risk_engine/simulation/config/zhejiang_v1.py",
                             pass_ratios=[0.3, 0.5, 0.7])
    """
    # 动态导入配置文件
    import importlib.util
    config_path = Path(config_path)
    spec = importlib.util.spec_from_file_location(config_path.stem, config_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # 配置文件应该 export 一个 SimulationConfig 对象
    # 命名为 Zhejiang_v1 / Jiangxi_v1 等
    config_obj = None
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if isinstance(attr, SimulationConfig):
            config_obj = attr
            break

    if config_obj is None:
        raise ValueError(f"配置文件中未找到 SimulationConfig 对象: {config_path}")

    # 应用覆盖
    if overrides:
        config_obj = config_obj.clone(**overrides)

    return run(config_obj)
