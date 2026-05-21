#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : output_schema
功能描述 : 决策输出标准化 — 统一风控决策的输出格式
          包含风险分、决策结果、拒绝原因码、特征快照等
创建日期 : 2026-05-21
开发者   : Jingluo
版本     : v0.1.0
更新历史 :
  2026-05-21, Jingluo, v0.1.0 — 初始创建
============================================================================
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime

__all__ = ["DecisionOutput"]


@dataclass
class DecisionOutput:
    """决策输出 — 标准化风控决策结果"""
    request_id: str                             # 请求唯一ID（链路追踪）
    risk_score: float                           # 风险分（0-1000）
    decision: str                               # accept / reject / manual_review
    reject_reason: str | None = None            # 拒绝原因码
    model_version: str = ""                     # 决策使用的模型版本
    rule_hit: list[str] = field(default_factory=list)  # 命中的规则列表
    feature_snapshot: dict = field(default_factory=dict)  # 决策时的特征快照
    decision_time_ms: int = 0                   # 决策耗时（毫秒）
    timestamp: datetime = field(default_factory=datetime.now)  # 决策时间
