#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : errors
功能描述 : 统一错误码体系 — 所有 API 错误通过此模块定义
          格式: E{模块号}{错误号}，如 E0101 = 决策超时
创建日期 : 2026-05-21
开发者   : Jingluo
版本     : v0.1.0
============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "AppError",
    "DecisionTimeoutError",
    "FeatureNotFoundError",
    "ModelNotFoundError",
]


@dataclass
class AppError(Exception):
    """应用级错误基类"""

    code: str  # 错误码
    message: str  # 错误描述
    status_code: int = 500  # HTTP 状态码


class DecisionTimeoutError(AppError):
    """决策超时 (E01)"""

    def __init__(self, request_id: str, timeout_ms: int):
        super().__init__(
            code="E0101",
            message=f"决策超时: request_id={request_id}, timeout={timeout_ms}ms",
            status_code=504,
        )


class FeatureNotFoundError(AppError):
    """特征未找到 (E02)"""

    def __init__(self, feature_name: str):
        super().__init__(
            code="E0201",
            message=f"特征未注册: {feature_name}",
            status_code=400,
        )


class ModelNotFoundError(AppError):
    """模型版本未找到 (E03)"""

    def __init__(self, model_version: str):
        super().__init__(
            code="E0301",
            message=f"模型版本不存在: {model_version}",
            status_code=404,
        )
