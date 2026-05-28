#!/usr/bin/env python3
"""
仿真模块 CLI 入口 — python -m risk_engine.simulation run <preset> [options]

用法:
    # 使用预设配置（推荐）
    python -m risk_engine.simulation run jiangxi_v1
    python -m risk_engine.simulation run jiangxi_v1 --data-date 2026-06-10 --pass-ratios 0.3 0.5 0.7
    python -m risk_engine.simulation run jiangxi_v1 --no-save --label "test-run-1"

    # 从 YAML 文件加载
    python -m risk_engine.simulation run --config configs/jiangxi_v1.yaml
    python -m risk_engine.simulation run --config configs/jiangxi_v1.yaml --data-date 2026-06-10

    # 列出可用预设
    python -m risk_engine.simulation list-presets

    # 列出历史快照
    python -m risk_engine.simulation list-snapshots jiangxi v1
"""

from __future__ import annotations

import argparse
import sys


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="risk_engine.simulation",
        description="风控模型仿真模拟 — cutoff 估计与策略验证",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── run ──
    run_parser = sub.add_parser("run", help="运行一次仿真")
    run_parser.add_argument("preset", nargs="?", default=None, help="预设名称（如 jiangxi_v1）")
    run_parser.add_argument(
        "--config", "-c", default=None, help="YAML 配置文件路径（与 preset 二选一）"
    )
    run_parser.add_argument("--data-date", default=None, help="数据截止日期")
    run_parser.add_argument("--data-start", default=None, help="数据起始日期")
    run_parser.add_argument("--tree-version", default=None, help="决策树版本")
    run_parser.add_argument(
        "--pass-ratios", nargs="*", type=float, default=None, help="测试通过率列表"
    )
    run_parser.add_argument("--label", default=None, help="运行标签（默认识别为时间戳）")
    run_parser.add_argument(
        "--no-save", action="store_true", help="不保存快照（仅预览）"
    )
    run_parser.add_argument("--quiet", "-q", action="store_true", help="静默模式")

    # ── list-presets ──
    sub.add_parser("list-presets", help="列出所有可用预设")

    # ── list-snapshots ──
    snap_parser = sub.add_parser("list-snapshots", help="列出历史仿真快照")
    snap_parser.add_argument("province", help="省份")
    snap_parser.add_argument("version", default="v1", nargs="?", help="版本号")

    return parser


def _cmd_run(args: argparse.Namespace):
    from risk_engine.simulation.pipeline import get_preset, list_presets, run, run_from_config_file

    presets = list_presets()

    if args.config:
        # 从 YAML 文件加载
        overrides = {}
        for key in ("data_date", "data_start", "tree_version"):
            val = getattr(args, key, None)
            if val is not None:
                overrides[key] = val
        if args.pass_ratios is not None:
            overrides["pass_ratios"] = args.pass_ratios

        result = run_from_config_file(args.config, **overrides)

    elif args.preset:
        # 从预设加载
        if args.preset not in presets:
            print(f"❌ 未知预设: {args.preset}")
            print(f"   可用: {', '.join(presets)}")
            sys.exit(1)

        cfg = get_preset(args.preset)

        if args.data_date:
            cfg.data_date = args.data_date
        if args.data_start:
            cfg.data_start = args.data_start
        if args.tree_version:
            cfg.tree_version = args.tree_version
        if args.pass_ratios is not None:
            cfg.pass_ratios = args.pass_ratios

        result = run(
            cfg,
            label=args.label,
            save=not args.no_save,
            verbose=not args.quiet,
        )

    else:
        print("❌ 请指定预设名称或 --config 配置文件")
        print(f"   可用预设: {', '.join(presets)}")
        sys.exit(1)

    # 静默模式只打印报告路径
    if args.quiet and result.get("folder"):
        print(result["folder"])


def _cmd_list_presets():
    from risk_engine.simulation.pipeline import list_presets

    presets = list_presets()
    print("可用仿真预设:")
    for name in presets:
        print(f"  • {name}")


def _cmd_list_snapshots(args: argparse.Namespace):
    from risk_engine.simulation.snapshot import list_snapshots

    snapshots = list_snapshots(args.province, args.version)
    if not snapshots:
        print(f"  无快照: {args.province}/{args.version}")
        return

    print(f"仿真快照 — {args.province}/{args.version}:")
    for snap in snapshots:
        print(f"  [{snap['label']}] {snap.get('saved_at', '?')}")
        if snap.get("path"):
            print(f"    路径: {snap['path']}")


def main():
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "run":
        _cmd_run(args)
    elif args.command == "list-presets":
        _cmd_list_presets()
    elif args.command == "list-snapshots":
        _cmd_list_snapshots(args)


if __name__ == "__main__":
    main()
