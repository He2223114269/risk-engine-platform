"""
Cutoff 估计 — 通过率 ↔ LXF 阈值 ↔ 预期逾期率

核心逻辑：
  给定一个策略分支的客群 + 灵犀分 + is_overdue 标签，
  对每个 pass_ratio：
    1. 按 LXF 降序排列
    2. 取前 pass_ratio% 的人作为"通过"
    3. 记录通过的 LXF 最低分（cutoff 阈值）
    4. 计算通过人群的逾期率
"""

from __future__ import annotations

import pandas as pd


def estimate_branch(
    data: pd.DataFrame,
    pass_ratios: list[float],
    score_col: str = "lxf",
    label_col: str = "is_over_due",
) -> list[dict]:
    """
    对单个策略分支，计算不同通过率下的 cutoff 和逾期率。

    参数:
        data:       一个分支的客群数据（含 lxf 和 is_over_due）
        pass_ratios: 要测试的通过率列表（如 [0.1, 0.3, 0.5]）
        score_col:   评分列名
        label_col:   逾期标签列名

    返回:
        [{pass_ratio, cutoff_score, pass_count, total_count, overdue_rate, ...}, ...]
    """
    if data.empty or score_col not in data.columns:
        return []

    # 按灵犀分降序
    ranked = data.sort_values(score_col, ascending=False).reset_index(drop=True)
    total = len(ranked)

    results = []
    for ratio in pass_ratios:
        n_pass = max(1, int(total * ratio))
        passed = ranked.head(n_pass)
        cutoff_score = passed[score_col].min() if not passed.empty else None

        pass_count = len(passed)
        overdue_count = int(passed[label_col].sum()) if label_col in passed.columns else 0
        overdue_rate = overdue_count / pass_count if pass_count > 0 else None

        results.append(
            {
                "pass_ratio": ratio,
                "cutoff_score": float(cutoff_score) if cutoff_score is not None else None,
                "pass_count": pass_count,
                "total_count": total,
                "overdue_count": overdue_count,
                "overdue_rate": round(overdue_rate, 4) if overdue_rate is not None else None,
                "avg_score": (
                    round(float(passed[score_col].mean()), 1) if not passed.empty else None
                ),
            }
        )

    return results


def estimate_all(
    data: pd.DataFrame,
    pass_ratios: list[float],
    score_col: str = "lxf",
    label_col: str = "is_over_due",
    branch_col: str = "strategy_type",
) -> pd.DataFrame:
    """
    对所有策略分支，计算不同通过率下的 cutoff 和逾期率。

    参数:
        data:        全量数据（含 branch_col + score_col + label_col）
        pass_ratios:  通过率列表
        score_col:    评分列名
        label_col:    逾期标签
        branch_col:   分支列名

    返回:
        DataFrame: columns = [strategy_type, pass_ratio, cutoff_score,
                               pass_count, total_count, overdue_count, overdue_rate, avg_score]
    """
    all_results = []

    for branch in sorted(data[branch_col].unique()):
        branch_data = data[data[branch_col] == branch]
        results = estimate_branch(branch_data, pass_ratios, score_col, label_col)

        for r in results:
            r["strategy_type"] = branch

        all_results.extend(results)

    df = pd.DataFrame(all_results)

    # 排序
    if not df.empty:
        df = df.sort_values(["strategy_type", "pass_ratio"]).reset_index(drop=True)

    return df


def find_cutoff_at_ratio(
    data: pd.DataFrame,
    target_ratio: float,
    score_col: str = "lxf",
) -> float | None:
    """
    快捷方法：给定一个目标通过率，返回 LXF 阈值。

    参数:
        data:         一个分支的客群数据
        target_ratio: 目标通过率（如 0.5）
        score_col:    评分列

    返回:
        cutoff 分值 或 None
    """
    if data.empty or score_col not in data.columns:
        return None

    ranked = data.sort_values(score_col, ascending=False)
    n = max(1, int(len(ranked) * target_ratio))
    return float(ranked.head(n)[score_col].min())


def estimate_overdue_at_cutoff(
    data: pd.DataFrame,
    cutoff: float,
    score_col: str = "lxf",
    label_col: str = "is_over_due",
) -> float | None:
    """
    快捷方法：给定一个 cutoff 阈值，返回通过人群的逾期率。

    参数:
        data:      一个分支的客群数据
        cutoff:    LXF 阈值
        score_col: 评分列
        label_col: 逾期标签

    返回:
        逾期率 或 None
    """
    if data.empty or score_col not in data.columns:
        return None

    passed = data[data[score_col] >= cutoff]
    if len(passed) == 0:
        return None

    overdue = int(passed[label_col].sum()) if label_col in passed.columns else 0
    return round(overdue / len(passed), 4)
