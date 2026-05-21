#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : base
功能描述 : 模型基类 — 统一所有风控模型的接口规范
          所有具体模型（RF/GBDT/LR/评分卡）必须继承此基类
创建日期 : 2026-05-21
开发者   : Jingluo
版本     : v0.1.0
更新历史 :
  2026-05-21, Jingluo, v0.1.0 — 初始创建
============================================================================
"""

from __future__ import annotations
from abc import ABC, abstractmethod
import numpy as np

__all__ = ["BaseModel"]


class BaseModel(ABC):
    """风控模型基类"""

    @abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """训练模型"""
        ...

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测标签"""
        ...

    @abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """预测概率"""
        ...

    @abstractmethod
    def save(self, path: str) -> str:
        """保存模型到路径，返回保存路径"""
        ...

    @classmethod
    @abstractmethod
    def load(cls, path: str) -> BaseModel:
        """从路径加载模型"""
        ...
