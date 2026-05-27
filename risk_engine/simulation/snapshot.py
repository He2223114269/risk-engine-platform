"""
配置快照管理 — 保存/加载/导入仿真配置

设计：
- 每次仿真结束时，完整展开的配置自动保存到结果文件夹
- 后续可加载历史快照，继承或修改后重新仿真
- 目标是：每次仿真都可完全复现
"""

from __future__ import annotations

import dataclasses
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

# ── 项目根目录 ──
ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = ROOT / "data" / "simulations"


def _ensure_serializable(obj: Any) -> Any:
    """将配置对象转为纯字典，确保 JSON 可序列化"""
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    if isinstance(obj, dict):
        return {str(k): _ensure_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_ensure_serializable(v) for v in obj]
    if isinstance(obj, (tuple, set)):
        return list(obj)
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def save_snapshot(
    config: dict,
    province: str,
    version: str,
    *,
    label: str | None = None,
) -> Path:
    """
    保存配置快照到仿真结果文件夹。

    参数:
        config:   已展开的完整配置字典
        province: 省份名（如 "zhejiang"）
        version:  版本号（如 "v1"）
        label:    可选标签，默认用时间戳

    返回:
        Path: 保存的文件夹路径
    """
    if label is None:
        label = datetime.now().strftime("%Y-%m-%d_%H%M")

    folder = DATA_DIR / province / version / label
    folder.mkdir(parents=True, exist_ok=True)

    snapshot = _ensure_serializable(config)
    snapshot["_meta"] = {
        "province": province,
        "version": version,
        "label": label,
        "saved_at": datetime.now().isoformat(),
    }

    snapshot_path = folder / "config_snapshot.json"
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False, default=str)

    return folder


def load_snapshot(province: str, version: str, label: str) -> dict:
    """
    加载历史快照配置。

    参数:
        province: 省份名
        version:  版本号
        label:    标签（时间戳）

    返回:
        dict: 完整配置
    """
    snapshot_path = DATA_DIR / province / version / label / "config_snapshot.json"
    if not snapshot_path.exists():
        raise FileNotFoundError(f"快照不存在: {snapshot_path}")

    with open(snapshot_path, encoding="utf-8") as f:
        return json.load(f)


def list_snapshots(province: str, version: str) -> list[dict]:
    """
    列出某省份某版本的所有历史快照。

    返回:
        [{"label": "2026-05-27_1530", "saved_at": "...", "province": "..."}, ...]
    """
    base = DATA_DIR / province / version
    if not base.exists():
        return []

    results = []
    for folder in sorted(base.iterdir(), reverse=True):
        snapshot_file = folder / "config_snapshot.json"
        if snapshot_file.exists():
            try:
                with open(snapshot_file, encoding="utf-8") as f:
                    config = json.load(f)
                meta = config.get("_meta", {})
                results.append(
                    {
                        "label": folder.name,
                        "province": meta.get("province", province),
                        "version": meta.get("version", version),
                        "saved_at": meta.get("saved_at", ""),
                        "path": str(folder),
                    }
                )
            except Exception:
                continue

    return results


def import_previous(province: str, version: str, label: str) -> dict:
    """
    导入历史仿真的一整套结果（配置 + 参数 + 报告）。

    这是一个便利函数——返回一个包含 all 路径和内容的字典，
    方便在 notebook 或分析脚本中直接使用。

    返回:
        {
            "config": {...},          # 配置快照
            "parameters": pd.DataFrame,  # 仿真参数（如果存了）
            "folder": Path,           # 快照文件夹
            "province": str,
            "version": str,
            "label": str,
        }
    """
    folder = DATA_DIR / province / version / label
    return {
        "config": load_snapshot(province, version, label),
        "folder": folder,
        "province": province,
        "version": version,
        "label": label,
    }


def save_result(
    folder: Path,
    parameters: pd.DataFrame,
    summary: dict | None = None,
    report: str | None = None,
) -> None:
    """
    保存仿真结果到快照文件夹。

    参数:
        folder:     snapshot.save_snapshot 返回的文件夹
        parameters: 各策略分支的参数 DataFrame
        summary:    可选汇总数据
        report:     可选 Markdown 报告文本
    """
    parameters.to_excel(folder / "parameters.xlsx", index=False)

    if report:
        (folder / "report.md").write_text(report, encoding="utf-8")

    if summary:
        with open(folder / "summary.json", "w", encoding="utf-8") as f:
            json.dump(_ensure_serializable(summary), f, indent=2, ensure_ascii=False, default=str)
