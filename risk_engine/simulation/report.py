"""仿真报告 — 结构化输出"""
from __future__ import annotations
from datetime import datetime
import pandas as pd
from risk_engine.model_registry.models.base import DecisionTreeModel


def generate_markdown(
    parameters: pd.DataFrame,
    config: dict,
    *,
    title: str | None = None,
    model: DecisionTreeModel | None = None,
    config_pass_ratio: float | None = None,
    branch_pass_ratios: dict[str, float] | None = None,
) -> str:
    """生成 Markdown 格式的仿真报告。"""
    province = config.get("province", "未知")
    if title is None:
        title = f"仿真报告 — {province}"

    config_rate_str = ""
    if config_pass_ratio is not None:
        config_rate_str = f"（平均配置通过率: {config_pass_ratio * 100:.0f}%）"

    lines = [
        f"# {title}",
        "",
        f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> 省份: {province} {config_rate_str}",
        f"> 模型版本: {config.get('tree_version', '-')}",
        f"> 数据范围: {config.get('data_start', '-')} ~ {config.get('data_date', '-')}",
        f"> 测试通过率: {len(parameters['pass_ratio'].unique())} 个级别",
        "",
        "---",
        "",
        "## 一、总体概况",
        "",
    ]

    if not parameters.empty:
        total_samples = parameters.groupby("strategy_type")["total_count"].first().sum()
        total_overdue = parameters.groupby("strategy_type")["overdue_count"].first().sum()
        branches = parameters["strategy_type"].nunique()
        overall_overdue_rate = total_overdue / total_samples if total_samples > 0 else 0

        lines.extend([
            f"- 策略分支数: **{branches}**",
            f"- 总样本数: **{total_samples:,}**",
            f"- 总逾期数: **{total_overdue:,}**",
            f"- 整体逾期率: **{overall_overdue_rate * 100:.2f}%**",
            "",
        ])

        # ── 当前配置下的质态摘要 ──
        if config_pass_ratio is not None:
            # 找到最接近配置通过率的那行
            closest_idx = (parameters["pass_ratio"] - config_pass_ratio).abs().idxmin()
            row = parameters.loc[closest_idx]
            lines.extend([
                "### 📋 当前配置下的质态",
                "",
                f"- **配置通过率**: {config_pass_ratio * 100:.0f}%",
                f"- **LXF 阈值**: {row['cutoff_score'] if pd.notna(row['cutoff_score']) else '-'}",
                f"- **通过数/总数**: {int(row['pass_count']):,}/{int(row['total_count']):,}",
                f"- **逾期率**: **{row['overdue_rate'] * 100:.2f}%**"
                f"（{'✅ 可控' if (row['overdue_rate'] or 0) < 0.05 else '⚠️ 偏高' if (row['overdue_rate'] or 0) < 0.08 else '🔴 高风险'})",
                f"- **拒绝人群逾期率**: {row['rejected_overdue_rate'] * 100:.2f}%"
                if pd.notna(row.get('rejected_overdue_rate'))
                else "",
                f"- **区分度（拒绝-通过）**: {row['discrimination_gap'] * 100:.2f}%"
                if pd.notna(row.get('discrimination_gap'))
                else "",
                "",
            ])
            # 去空行
            lines = [l for l in lines if l.strip()]

    # ── 二、各通过率下的关键指标对比（全局汇总） ──
    lines.extend([
        "---",
        "",
        "## 二、各通过率下的质态对比（全局）",
        "",
        "| 通过率 | LXF阈值 | 通过数 | 逾期数 | 逾期率 | 平均分 | 拒绝人数 | 拒绝逾期率 | 区分度 | 风险比 |",
        "|:-----:|:------:|:-----:|:-----:|:-----:|:-----:|:-------:|:---------:|:-----:|:-----:|",
    ])

    # 按 pass_ratio 汇总所有分支
    summary = parameters.groupby("pass_ratio").agg({
        "cutoff_score": "min",
        "pass_count": "sum",
        "total_count": "first",
        "overdue_count": "sum",
        "overdue_rate": "mean",
        "avg_score": "mean",
        "rejected_count": "sum",
        "rejected_overdue_rate": "mean",
        "discrimination_gap": "mean",
        "overdue_rate_ratio": "mean",
    }).reset_index()

    for _, row in summary.iterrows():
        ratio = row["pass_ratio"]
        is_current = (config_pass_ratio is not None and abs(ratio - config_pass_ratio) < 0.005)
        marker = " ◀ 当前" if is_current else ""

        overdue = row["overdue_rate"] or 0
        rejected_rate = row.get("rejected_overdue_rate") or 0
        gap = row.get("discrimination_gap") or 0
        risk_ratio = row.get("overdue_rate_ratio") or 0

        lines.append(
            f"| {ratio * 100:.0f}%{marker} | "
            f"{row['cutoff_score'] if pd.notna(row['cutoff_score']) else '-'} | "
            f"{int(row['pass_count']):,} | "
            f"{int(row['overdue_count']):,} | "
            f"{overdue * 100:.2f}% | "
            f"{row['avg_score']:.0f} | "
            f"{int(row['rejected_count']):,} | "
            f"{rejected_rate * 100:.2f}% | "
            f"{gap * 100:.2f}% | "
            f"{risk_ratio:.2f} |"
        )

    lines.extend(["", "", "**指标说明**：", "",
        "- **逾期率**: 通过人群的逾期比例，越低越好",
        "- **拒绝逾期率**: 被拒绝人群中本应逾期的比例，越高说明模型拒绝得越准",
        "- **区分度**: 拒绝逾期率 − 通过逾期率，越大说明模型区分能力越强",
        "- **风险比**: 通过人群逾期率 / 整体逾期率，<1 说明筛选有效",
        "",
    ])

    # ── 三、各分支详细（只展示当前配置通过率） ──
    if config_pass_ratio is not None:
        lines.extend([
            "---",
            "",
            f"## 三、各分支在配置通过率 {config_pass_ratio * 100:.0f}% 下的质态",
            "",
            "| 策略分支 | 说明 | 通过率 | LXF阈值 | 通过/总数 | 逾期率 | 拒绝逾期率 | 区分度 |",
            "|:--------|:-----|:-----:|:------:|:---------:|:-----:|:---------:|:-----:|",
        ])

        for branch in sorted(parameters["strategy_type"].unique()):
            branch_data = parameters[
                (parameters["strategy_type"] == branch)
            ]
            if branch_data.empty:
                continue
            # 找最接近配置通过率的行
            idx = (branch_data["pass_ratio"] - config_pass_ratio).abs().idxmin()
            row = parameters.loc[idx]
            info = model.get_branch_info(branch) if model else ""

            overdue = row["overdue_rate"] or 0
            rejected_rate = row.get("rejected_overdue_rate") or 0
            gap = row.get("discrimination_gap") or 0

            lines.append(
                f"| {branch} | {info} | "
                f"{row['pass_ratio'] * 100:.0f}% | "
                f"{row['cutoff_score'] if pd.notna(row['cutoff_score']) else '-'} | "
                f"{int(row['pass_count'])}/{int(row['total_count'])} | "
                f"{overdue * 100:.2f}% | "
                f"{rejected_rate * 100:.2f}% | "
                f"{gap * 100:.2f}% |"
            )

        lines.append("")

    # ── 三.5 各分支按实际配置通过率（从 risk_score_control 读取） ──
    if branch_pass_ratios:
        lines.extend([
            "---",
            "",
            "## 四、各分支按实际配置通过率 vs 建议方案对比",
            "",
            "| 分支 | 说明 | 配置通过率 | 当前逾期率 | 建议通过率 | 调整后逾期率 | 逾期率变化 | 通过数变化 |",
            "|:----|:-----|:--------:|:---------:|:--------:|:----------:|:---------:|:--------:|",
        ])

        # 找一个安全通过率（逾期率<5%）
        summary_local = parameters.groupby("pass_ratio").agg({
            "overdue_rate": "mean",
            "pass_count": "sum",
        }).reset_index()
        safe = summary_local[summary_local["overdue_rate"] < 0.05]
        suggest_ratio = safe.iloc[-1]["pass_ratio"] if not safe.empty else None

        for branch in sorted(parameters["strategy_type"].unique()):
            config_ratio = branch_pass_ratios.get(branch)
            if config_ratio is None:
                continue
            branch_data = parameters[parameters["strategy_type"] == branch]
            if branch_data.empty:
                continue

            # 当前配置
            idx = (branch_data["pass_ratio"] - config_ratio).abs().idxmin()
            row = parameters.loc[idx]
            info = model.get_branch_info(branch) if model else ""
            overdue = row["overdue_rate"] or 0

            # 建议方案
            suggest_str = "-"
            suggest_overdue_str = "-"
            change_str = "-"
            pass_change_str = "-"
            if suggest_ratio is not None and suggest_ratio < config_ratio - 0.01:
                sidx = (branch_data["pass_ratio"] - suggest_ratio).abs().idxmin()
                srow = parameters.loc[sidx]
                s_overdue = srow["overdue_rate"] or 0
                suggest_str = f"{suggest_ratio * 100:.0f}%"
                suggest_overdue_str = f"{s_overdue * 100:.2f}%"
                diff = (s_overdue - overdue) * 100
                change_str = f"{diff:+.2f}%" if abs(diff) >= 0.01 else "≈0%"
                p_diff = int(srow["pass_count"]) - int(row["pass_count"])
                pass_change_str = f"{p_diff:+d}"

            lines.append(
                f"| {branch} | {info} | "
                f"{config_ratio * 100:.0f}% | "
                f"{overdue * 100:.2f}% | "
                f"{suggest_str} | "
                f"{suggest_overdue_str} | "
                f"{change_str} | "
                f"{pass_change_str} |"
            )

        if suggest_ratio:
            lines.append("")
            lines.append(f"> 💡 建议通过率 **{suggest_ratio * 100:.0f}%**（逾期率<5%的安全线）")
        lines.append("")

    # ── 五、配置建议 ──
    lines.extend([
        "---",
        "",
        "## 五、配置建议",
        "",
    ])

    warnings = []
    for _, row in summary.iterrows():
        overdue = row.get("overdue_rate", 0) or 0
        gap = row.get("discrimination_gap", 0) or 0
        ratio = row["pass_ratio"]

        if overdue > 0.10:
            warnings.append(
                f"- 🔴 **通过率 {ratio * 100:.0f}%**: 逾期率 {overdue * 100:.2f}%，超过10%红线，"
                f"建议降低通过率"
            )
        elif overdue > 0.05:
            warnings.append(
                f"- ⚠️ **通过率 {ratio * 100:.0f}%**: 逾期率 {overdue * 100:.2f}%，偏高需关注"
            )

        if gap < 0.02 and ratio < 0.8:
            warnings.append(
                f"- ⚠️ **通过率 {ratio * 100:.0f}%**: 区分度仅 {gap * 100:.2f}%，"
                f"模型筛选效果弱，建议复核"
            )

    if config_pass_ratio is not None:
        closest = (summary["pass_ratio"] - config_pass_ratio).abs().idxmin()
        current = summary.loc[closest]
        current_overdue = current["overdue_rate"] or 0
        current_gap = current["discrimination_gap"] or 0

        lines.append(f"**当前配置（{config_pass_ratio * 100:.0f}%）**:")
        lines.append(f"- 预期逾期率: **{current_overdue * 100:.2f}%**")
        lines.append(f"- 模型区分度: **{current_gap * 100:.2f}%**")
        if current_overdue < 0.05:
            lines.append("- ✅ 逾期率可控，当前配置合理")
        elif current_overdue < 0.08:
            lines.append("- ⚠️ 逾期率偏高，建议适度收紧通过率")
        else:
            lines.append("- 🔴 逾期率超限，强烈建议降低通过率")

        # 建议：找到比当前逾期率降低一个档位的通过率
        safe = summary[summary["overdue_rate"] < 0.05]
        if not safe.empty and current_overdue >= 0.05:
            best_safe = safe.iloc[-1]  # 最高的安全通过率
            lines.append(
                f"- 💡 建议通过率调整为 **{best_safe['pass_ratio'] * 100:.0f}%**"
                f"（预期逾期率 {best_safe['overdue_rate'] * 100:.2f}%，"
                f"通过数约 {int(best_safe['pass_count']):,}/{int(best_safe['total_count']):,}）"
            )
        lines.append("")

    if not warnings:
        lines.append("- ✅ 所有通过率级别逾期率在可控范围内")
    for w in warnings:
        lines.append(w)

    lines.extend(["", "---", "", "*报告由 risk_engine.simulation 自动生成*"])
    return "\n".join(lines)


def create_summary(parameters: pd.DataFrame, model: DecisionTreeModel | None = None) -> dict:
    """生成仿真汇总 JSON。"""
    if parameters.empty:
        return {"status": "empty"}

    by_branch = {}
    for branch in parameters["strategy_type"].unique():
        branch_data = parameters[parameters["strategy_type"] == branch]
        row = branch_data.iloc[0]
        by_branch[branch] = {
            "cutoff": row["cutoff_score"],
            "overdue_rate": row["overdue_rate"],
            "rejected_overdue_rate": row.get("rejected_overdue_rate"),
            "discrimination_gap": row.get("discrimination_gap"),
            "total": int(row["total_count"]),
            "pass": int(row["pass_count"]),
            "info": model.get_branch_info(branch) if model else "",
        }

    total_samples = parameters.groupby("strategy_type")["total_count"].first().sum()
    return {"branches": len(by_branch), "total_samples": int(total_samples), "by_branch": by_branch}


def show_best_worst(parameters: pd.DataFrame, pass_ratio: float = 0.5) -> str:
    """输出'最好和最差的分支'的文字总结。"""
    if parameters.empty:
        return "无数据"
    target = parameters[parameters["pass_ratio"] == pass_ratio]
    if target.empty:
        closest = (parameters["pass_ratio"] - pass_ratio).abs().min()
        target = parameters[(parameters["pass_ratio"] - pass_ratio).abs() == closest]
    sorted_target = target.sort_values("overdue_rate", ascending=True)
    best = sorted_target.iloc[0]
    worst = sorted_target.iloc[-1]
    return (
        f"通过率 {pass_ratio * 100:.0f}% 下：\n"
        f"  ✅ 最佳分支: {best['strategy_type']} — 逾期率 {best['overdue_rate'] * 100:.2f}%\n"
        f"  ❌ 最差分支: {worst['strategy_type']} — 逾期率 {worst['overdue_rate'] * 100:.2f}%"
    )
