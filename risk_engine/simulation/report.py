"""
仿真报告 — 结构化输出

职责：
- 生成 Markdown 格式的人类可读报告
- 按分支输出 cutoff 对比表
- 质量检查清单
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from risk_engine.simulation.classifier import get_branch_info


def generate_markdown(
    parameters: pd.DataFrame,
    config: dict,
    *,
    title: str | None = None,
) -> str:
    """
    生成 Markdown 格式的仿真报告。

    参数:
        parameters:  estimator.estimate_all 的输出
        config:      完整配置快照
        title:       报告标题（默认自动生成）

    返回:
        Markdown 字符串
    """
    province = config.get("province", "未知")

    if title is None:
        title = f"仿真报告 — {province}"

    lines = [
        f"# {title}",
        "",
        f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> 省份: {province}",
        f"> 模型版本: {config.get('tree_version', '-')}",
        f"> 数据范围: {config.get('data_start', '-')} ~ {config.get('data_date', '-')}",
        "",
        "---",
        "",
        "## 一、总体概况",
        "",
    ]

    # 整体统计
    if not parameters.empty:
        total_samples = parameters.groupby("strategy_type")["total_count"].first().sum()
        total_overdue = parameters.groupby("strategy_type")["overdue_count"].first().sum()
        branches = parameters["strategy_type"].nunique()
        lines.extend(
            [
                f"- 策略分支数: **{branches}**",
                f"- 总样本数: **{total_samples:,}**",
                f"- 总逾期数: **{total_overdue:,}**",
                (
                    f"- 整体逾期率: **{total_overdue/total_samples*100:.2f}%**"
                    if total_samples > 0
                    else ""
                ),
                "",
            ]
        )

    # ── 各分支详情 ──
    lines.extend(
        [
            "## 二、各分支 Cutoff 估计",
            "",
            "| 策略分支 | 说明 | 通过率 | LXF阈值 | 通过数/总数 | 逾期率 | 平均分 |",
            "|:--------|:-----|:-----:|:------:|:----------:|:-----:|:-----:|",
        ]
    )

    for branch in sorted(parameters["strategy_type"].unique()):
        branch_data = parameters[parameters["strategy_type"] == branch]
        info = get_branch_info(branch)

        # 取第一行作为基准
        row = branch_data.iloc[0]
        lines.append(
            f"| {branch} | {info} | "
            f"{row['pass_ratio']*100:.0f}% | "
            f"{row['cutoff_score'] if row['cutoff_score'] is not None else '-'} | "
            f"{int(row['pass_count'])}/{int(row['total_count'])} | "
            f"{row['overdue_rate']*100:.2f}% | "
            f"{row['avg_score']} |"
        )

    lines.append("")

    # ── 建议项 ──
    lines.extend(
        [
            "## 三、配置建议",
            "",
        ]
    )

    # 逾期率偏高的分支
    if not parameters.empty:
        for _, row in parameters.iterrows():
            overdue = row.get("overdue_rate", 0) or 0
            if overdue > 0.10:
                lines.append(
                    f"- ⚠️ **{row['strategy_type']}** 在通过率 {row['pass_ratio']*100:.0f}% 时"
                    f"逾期率 {overdue*100:.2f}%，建议降低通过率或加大审核力度"
                )

    if not any((row.get("overdue_rate", 0) or 0) > 0.10 for _, row in parameters.iterrows()):
        lines.append("- ✅ 所有分支逾期率在可控范围内")

    lines.extend(
        [
            "",
            "---",
            "",
            "*报告由 risk_engine.simulation 自动生成*",
        ]
    )

    return "\n".join(lines)


def create_summary(parameters: pd.DataFrame) -> dict:
    """
    生成仿真汇总 JSON（供程序读取）。
    """
    if parameters.empty:
        return {"status": "empty"}

    # 各分支基准通过率下的逾期率
    by_branch = {}
    for branch in parameters["strategy_type"].unique():
        branch_data = parameters[parameters["strategy_type"] == branch]
        row = branch_data.iloc[0]  # 第一行=最小通过率
        by_branch[branch] = {
            "cutoff": row["cutoff_score"],
            "overdue_rate": row["overdue_rate"],
            "total": int(row["total_count"]),
            "pass": int(row["pass_count"]),
            "info": get_branch_info(branch),
        }

    total_samples = parameters.groupby("strategy_type")["total_count"].first().sum()

    return {
        "branches": len(by_branch),
        "total_samples": int(total_samples),
        "by_branch": by_branch,
    }


def show_best_worst(parameters: pd.DataFrame, pass_ratio: float = 0.5) -> str:
    """
    输出"最好和最差的分支"的文字总结。

    参数:
        parameters: 估计结果
        pass_ratio:  关注的通过率
    """
    if parameters.empty:
        return "无数据"

    target = parameters[parameters["pass_ratio"] == pass_ratio]
    if target.empty:
        # 取最近的通过率
        closest = (parameters["pass_ratio"] - pass_ratio).abs().min()
        target = parameters[(parameters["pass_ratio"] - pass_ratio).abs() == closest]

    # 按逾期率排序
    sorted_target = target.sort_values("overdue_rate", ascending=True)

    best = sorted_target.iloc[0]
    worst = sorted_target.iloc[-1]

    return (
        f"通过率 {pass_ratio*100:.0f}% 下：\n"
        f"  ✅ 最佳分支: {best['strategy_type']} — 逾期率 {best['overdue_rate']*100:.2f}%\n"
        f"  ❌ 最差分支: {worst['strategy_type']} — 逾期率 {worst['overdue_rate']*100:.2f}%"
    )
