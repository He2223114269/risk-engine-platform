#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : registry
功能描述 : 特征注册中心 — 统一管理所有风控特征的元数据
          包括特征名称、数据类型、来源表、计算逻辑、版本号
          所有特征的增删改查必须通过注册中心，严禁硬编码特征名
创建日期 : 2026-05-21
开发者   : Jingluo
版本     : v0.1.0
更新历史 :
  2026-05-21, Jingluo, v0.1.0 — 初始创建
============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

__all__ = [
    "FeatureDefinition",
    "FeatureRegistry",
]


@dataclass(frozen=True)
class FeatureDefinition:
    """特征定义 — 不可变对象，注册后禁止修改"""

    name: str  # 特征名称（全局唯一）
    feature_type: str  # numeric / categorical / text
    source_table: str  # 来源表
    compute_logic: str  # 计算逻辑描述
    version: str = "v1"  # 特征版本
    description: str = ""  # 特征说明
    tags: list[str] = field(default_factory=list)  # 标签


class FeatureRegistry:
    """特征注册中心"""

    _instance: Optional[FeatureRegistry] = None

    def __new__(cls) -> FeatureRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._features: dict[str, FeatureDefinition] = {}
        return cls._instance

    def register(self, definition: FeatureDefinition) -> None:
        """注册一个新特征"""
        raise NotImplementedError

    def get(self, name: str) -> Optional[FeatureDefinition]:
        """查询特征定义"""
        raise NotImplementedError

    def list_by_tag(self, tag: str) -> list[FeatureDefinition]:
        """按标签筛选特征"""
        raise NotImplementedError

    def validate(self, feature_names: list[str]) -> list[str]:
        """批量校验特征名是否已注册，返回未注册的特征名列表"""
        raise NotImplementedError
