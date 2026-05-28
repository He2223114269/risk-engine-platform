"""仿真编排器 — 一次完整仿真的入口

流程:
  1. 加载配置
  2. 拉取数据
  3. 决策树分类（通过 model_registry 加载模型）
  4. cutoff 估计（各通过率下的 LXF 阈值 + 逾期率）
  5. 生成报告
  6. 保存快照
"""

from __future__ import annotations

from risk_engine.simulation import data as sim_data
from risk_engine.simulation import estimator
from risk_engine.simulation import report as sim_report
from risk_engine.simulation import snapshot
from risk_engine.model_registry import load as load_model
from pathlib import Path
from typing import Any

import yaml

from risk_engine.simulation.config.presets import SimulationConfig


# ── 预设配置映射 ──
_CONFIG_PRESETS: dict[str, SimulationConfig] = {}


def _init_presets():
    """懒加载预设配置，避免 import 循环。"""
    if _CONFIG_PRESETS:
        return
    from risk_engine.simulation.config.presets import Jiangxi_v1

    _CONFIG_PRESETS["jiangxi_v1"] = Jiangxi_v1
    try:
        from risk_engine.simulation.config.zhejiang_v1 import Zhejiang_v1

        _CONFIG_PRESETS["zhejiang_v1"] = Zhejiang_v1
    except ImportError:
        pass


def list_presets() -> list[str]:
    """列出所有可用的预设配置名。"""
    _init_presets()
    return sorted(_CONFIG_PRESETS.keys())


def get_preset(name: str) -> SimulationConfig:
    """按名称获取预设配置。"""
    _init_presets()
    if name not in _CONFIG_PRESETS:
        raise ValueError(
            f"未知预设: {name}，可用: {list(_CONFIG_PRESETS.keys())}"
        )
    return _CONFIG_PRESETS[name]


def run_from_config_file(config_path: str | Path, **overrides: Any) -> dict:
    """
    从 YAML 配置文件加载配置并运行仿真。

    参数:
        config_path: YAML 配置文件路径
        overrides:   覆盖字段（优先级高于文件）
                     支持 preset 名称引用

    YAML 文件格式:
        preset: jiangxi_v1              # 可选：继承预设
        province: 江西省
        data_start: 2025-01-01
        data_date: 2025-06-10
        tree_version: jiangxi_v1
        pass_ratios: [0.1, 0.5, 0.9]
        # ... 其余 SimulationConfig 字段

    返回:
        与 run() 相同的结果字典
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ValueError(f"配置文件格式错误: 预期 dict，得到 {type(raw)}")

    # 如果有 preset，先加载预设再覆盖
    preset_name = raw.pop("preset", None)
    if preset_name:
        cfg = get_preset(preset_name).clone()
    else:
        cfg = SimulationConfig()

    # 从 YAML 覆盖字段
    for key, value in raw.items():
        if hasattr(cfg, key):
            setattr(cfg, key, value)
        else:
            import warnings

            warnings.warn(f"未知配置字段: {key}，已忽略")

    # overrides 优先级最高
    for key, value in overrides.items():
        if hasattr(cfg, key):
            setattr(cfg, key, value)

    return run(cfg)


def run(
    mode_config: SimulationConfig,
    *,
    label: str | None = None,
    save: bool = True,
    verbose: bool = True,
) -> dict:
    """运行一次完整仿真。"""
    province = mode_config.province
    model_id = mode_config.tree_version

    if verbose:
        print(f"\n{'=' * 60}")
        print(f"  仿真运行 — {province} {mode_config.version}")
        print(f"{'=' * 60}")
        print(f"  数据范围: {mode_config.data_start} ~ {mode_config.data_date}")
        print(f"  决策树:   {model_id}")
        print(f"  测试通过率: {len(mode_config.pass_ratios)} 个级别")

    # ── 步骤 1: 加载模型 ──
    if verbose:
        print(f"\n  [1/6] 加载模型 ({model_id})...")
    model = load_model(model_id)

    # ── 步骤 2: 拉取数据 ──
    if verbose:
        print(f"  [2/6] 拉取 {province} 数据...")

    data = sim_data.fetch(mode_config)
    if data.empty:
        raise ValueError(f"{province} 无可用数据")
    if verbose:
        print(f"        已获取 {len(data):,} 条记录")

    # ── 步骤 3: 决策树分类 ──
    if verbose:
        print("  [3/6] 决策树分类...")
    data = model.classify_batch(data)
    branch_counts = data["strategy_type"].value_counts()
    if verbose:
        print(f"        分为 {len(branch_counts)} 个策略分支")

    # ── 步骤 4: cutoff 估计 ──
    if verbose:
        print(f"  [4/6] cutoff 估计（{len(mode_config.pass_ratios)} 个通过率级别）...")
    params = estimator.estimate_all(
        data, pass_ratios=mode_config.pass_ratios,
        score_col="lxf", label_col="is_over_due",
    )
    if verbose:
        print(f"        生成 {len(params):,} 条估算结果")

    # ── 步骤 5: 生成报告 ──
    if verbose:
        print("  [5/6] 生成报告...")
    best_worst = sim_report.show_best_worst(params)
    if verbose:
        print(f"\n{best_worst}")
    report_md = sim_report.generate_markdown(params, mode_config.to_dict(), model=model)

    # ── 步骤 6: 保存快照 ──
    folder = None
    if save:
        if verbose:
            print("\n  [6/6] 保存快照...")
        folder = snapshot.save_snapshot(
            config=mode_config.to_dict(),
            province=province.replace("省", "").replace("市", ""),
            version=mode_config.version,
            label=label,
        )
        snapshot.save_result(folder, params, None, report_md)
        if verbose:
            print(f"        已保存至: {folder}")

    if verbose:
        print("\n  ✅ 仿真完成")

    return {
        "config": mode_config.to_dict(),
        "parameters": params,
        "report": report_md,
        "folder": folder,
        "data": data,
        "model": model,
    }
