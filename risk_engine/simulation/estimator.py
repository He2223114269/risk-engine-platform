"""
Cutoff 估计 — 通过率 ↔ LXF 阈值 ↔ 预期逾期率

核心逻辑：
  给定一个策略分支的客群 + 灵犀分 + is_overdue 标签，
  对每个 pass_ratio：
    1. 按 LXF 降序排列
    2. 取前 pass_ratio% 的人作为"通过"
    3. 记录通过的 LXF 最低分（cutoff 阈值）
    4. 计算通过人群的逾期率
    5. 计算拒绝人群的逾期率（验证模型区分度）
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
    对单个策略分支，计算不同通过率下的所有关键指标。

    参数:
        data:       一个分支的客群数据（含 lxf 和 is_over_due）
        pass_ratios: 要测试的通过率列表（如 [0.1, 0.3, 0.5]）
        score_col:   评分列名
        label_col:   逾期标签列名

    返回:
        [{pass_ratio, cutoff_score, pass_count, total_count,
          overdue_count, overdue_rate, avg_score,
          rejected_count, rejected_overdue_rate,           # 拒绝人群
          overdue_rate_ratio, discrimination_gap}, ...]     # 区分度指标
    """
    if data.empty or score_col not in data.columns:
        return []

    # 按灵犀分降序
    ranked = data.sort_values(score_col, ascending=False).reset_index(drop=True)
    total = len(ranked)
    overall_overdue_rate = int(data[label_col].sum()) / total if label_col in data.columns else None

    results = []
    for ratio in pass_ratios:
        n_pass = max(1, int(total * ratio))
        passed = ranked.head(n_pass)
        rejected = ranked.tail(total - n_pass) if total > n_pass else pd.DataFrame()

        cutoff_score = passed[score_col].min() if not passed.empty else None

        # ── 通过人群指标 ──
        pass_count = len(passed)
        overdue_count = int(passed[label_col].sum()) if label_col in passed.columns else 0
        overdue_rate = overdue_count / pass_count if pass_count > 0 else None

        # ── 拒绝人群指标 ──
        rejected_count = len(rejected)
        rejected_overdue_count = int(rejected[label_col].sum()) if label_col in rejected.columns else 0
        rejected_overdue_rate = (
            rejected_overdue_count / rejected_count if rejected_count > 0 else None
        )

        # ── 模型区分度指标 ──
        # 拒绝人群逾期率 - 通过人群逾期率（越大说明模型区分越好）
        if overdue_rate is not None and rejected_overdue_rate is not None:
            discrimination_gap = round(rejected_overdue_rate - overdue_rate, 4)
        else:
            discrimination_gap = None

        # 通过人群逾期率 / 整体逾期率（<1 说明筛选有效，越低越好）
        if overdue_rate is not None and overall_overdue_rate and overall_overdue_rate > 0:
            overdue_rate_ratio = round(overdue_rate / overall_overdue_rate, 4)
        else:
            overdue_rate_ratio = None

        # ── 业务影响指标 ──
        # 相比当前配置通过率，通过人数的变化比例
        #（由外层计算，这里先预留）

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
                # ── 拒绝人群指标（新增） ──
                "rejected_count": rejected_count,
                "rejected_overdue_rate": (
                    round(rejected_overdue_rate, 4) if rejected_overdue_rate is not None else None
                ),
                # ── 区分度指标（新增） ──
                "discrimination_gap": discrimination_gap,
                "overdue_rate_ratio": overdue_rate_ratio,
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
    对所有策略分支，计算不同通过率下的所有关键指标。

    参数:
        data:        全量数据（含 branch_col + score_col + label_col）
        pass_ratios:  通过率列表
        score_col:    评分列名
        label_col:    逾期标签
        branch_col:   分支列名

    返回:
        DataFrame: columns = [strategy_type, pass_ratio, cutoff_score,
                               pass_count, total_count, overdue_count, overdue_rate,
                               avg_score, rejected_count, rejected_overdue_rate,
                               discrimination_gap, overdue_rate_ratio]
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


def load_branch_pass_ratios(province: str, model=None) -> dict[str, float]:
    """
    从 sys_parameter.risk_score_control 表加载各分支的配置通过率。

    score_code 格式为 XXX_2511（如 001_2511），
    其中 XXX（001,002...）按顺序对应决策树的分支（第1个分支、第2个分支...）。

    参数:
        province: 省份名（如 "江西省"）
        model:    决策树模型实例（用于获取分支列表）

    返回:
        {branch_id: pass_ratio, ...}  如 {'bw_d1_td4_fm_1': 0.90}
        失败时返回 {}
    """
    try:
        from risk_engine.toolkit.connectors import get_data

        # 获取分支列表
        branches = model.list_branches() if model and hasattr(model, 'list_branches') else []
        if not branches:
            # 兜底：按顺序生成分支名
            branches = [str(i) for i in range(1, 24)]

        conn = get_data(data_type="local")

        # 优先取省份配置，没有则取"全国"
        sql = f"""
            SELECT score_code, pass_ratio
            FROM sys_parameter.risk_score_control
            WHERE isv='淘顺' AND bussiness='实时授信'
              AND status='生效'
              AND province IN ('{province}', '全国')
            ORDER BY FIELD(province, '{province}', '全国'), score_code
        """
        df = conn.get_data(sql)
        conn.close()

        if df.empty:
            print(f"    ⚠️ 未找到 {province} 的 score_code 配置")
            return {}

        # province 优先级：省份 > 全国
        # 从 df 中取每个 score_code 的第一条（省份优先级高因为 ORDER BY FIELD）
        df = df.drop_duplicates(subset="score_code", keep="first")

        result = {}
        for i, branch_id in enumerate(branches):
            if i >= len(df):
                break
            prefix = f"{i + 1:03d}"
            row = df[df["score_code"].str.startswith(prefix)]
            if not row.empty:
                result[branch_id] = float(row.iloc[0]["pass_ratio"])

        print(f"    📋 加载了 {len(result)} 个分支的配置通过率")
        for branch, ratio in list(result.items())[:5]:
            print(f"       {branch}: {ratio * 100:.0f}%")
        if len(result) > 5:
            print(f"       ... 还有 {len(result) - 5} 个分支")

        return result

    except Exception as e:
        print(f"    ⚠️ 读取分支通过率配置失败: {e}")
        return {}


def find_cutoff_at_ratio(
    data: pd.DataFrame,
    target_ratio: float,
    score_col: str = "lxf",
) -> float | None:
    """快捷方法：给定一个目标通过率，返回 LXF 阈值。"""
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
    """快捷方法：给定一个 cutoff 阈值，返回通过人群的逾期率。"""
    if data.empty or score_col not in data.columns:
        return None

    passed = data[data[score_col] >= cutoff]
    if len(passed) == 0:
        return None

    overdue = int(passed[label_col].sum()) if label_col in passed.columns else 0
    return round(overdue / len(passed), 4)
