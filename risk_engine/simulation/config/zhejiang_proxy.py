"""
浙江代理测试 — 用全国数据模拟浙江上线
======================================

背景：
  浙江新省份上线，无实际浙江数据。
  用全国数据（2026年1-4月）作为代理，使用江西决策树，
  寻找整体通过率 40% 下的最优分支配置。

用法：
  python -m risk_engine.simulation dev
  或直接运行 risk_engine/simulation/dev_simulation.py
"""

from __future__ import annotations

# ── 浙江代理测试专用配置 ──
CONFIG = {
    "province": "全国",           # 数据源：用全国数据代替浙江
    "config_province": "浙江省",  # 通过率配置：从 risk_score_control 读浙江的配置
    "data_start": "2026-01-01",
    "data_date": "2026-05-01",
    "tree_version": "jiangxi_v1",
    "target_pass_rate": 0.40,    # 目标整体通过率 40%
    "description": "浙江代理测试 — 全国数据 + 江西决策树 + 浙江通过率配置",
}
