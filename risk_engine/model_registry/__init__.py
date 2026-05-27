#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : model_registry
功能描述 : 模型注册表 — 管理模型全生命周期
          支持版本管理、灰度发布、AB测试、回滚、产物存储
创建日期 : 2026-05-21
开发者   : Jingluo
版本     : v0.1.0
更新历史 :
  2026-05-21, Jingluo, v0.1.0 — 初始创建
============================================================================
"""

from .evaluator import ModelEvaluator

# ── 决策树模型注册 ──
from risk_engine.model_registry.models.jiangxi_v1 import JiangxiV1

# 模型注册表
_MODELS: dict[str, type] = {
    "jiangxi_v1": JiangxiV1,
}


def load(model_id: str):
    """按 model_id 加载决策树模型实例"""
    cls = _MODELS.get(model_id)
    if cls is None:
        raise ValueError(f"未知模型: {model_id}，可用: {list(_MODELS.keys())}")
    return cls()


def list_models() -> list[str]:
    """列出所有已注册模型"""
    return list(_MODELS.keys())
