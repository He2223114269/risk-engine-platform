#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : metrics
功能描述 : 风控指标库 — 通过率、逾期率、Vintage分析、门店质态评分
          所有指标函数为纯函数（输入 conn + 参数，输出 DataFrame/float）

已实现:
  - PassRateCalculator: 通过率计算（整体/分省/逐日/标准对比/去重口径）

规划中:
  - OverdueCalculator: 逾期率计算
  - VintageAnalyzer: Vintage 分析
  - StoreQualityScorer: 门店质态评分

更新历史:
  2026-05-21, Jingluo, v0.1.0 — 初始创建（pass_rate）
============================================================================
"""

from .pass_rate import PassRateCalculator, calc_pass_rate

__all__ = [
    "PassRateCalculator",
    "calc_pass_rate",
]
