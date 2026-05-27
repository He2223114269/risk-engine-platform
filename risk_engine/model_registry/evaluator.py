#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : evaluator
功能描述 : 模型评估器 — 离线评估模型效果
          计算 PSI/KS/AUC/混淆矩阵等核心指标，生成评估报告
创建日期 : 2026-05-21
开发者   : Jingluo
版本     : v0.1.0
更新历史 :
  2026-05-21, Jingluo, v0.1.0 — 初始创建
============================================================================
"""

from __future__ import annotations
from dataclasses import dataclass

__all__ = ["ModelEvaluator", "EvaluationReport"]


@dataclass
class EvaluationReport:
    """模型评估报告"""

    model_version: str
    psi: float  # 群体稳定性指标
    ks: float  # KS 值
    auc: float  # AUC
    gini: float  # Gini 系数
    confusion_matrix: dict  # 混淆矩阵
    score_distribution: dict  # 分数分布


class ModelEvaluator:
    """模型离线评估器"""

    def evaluate(self, model_path: str, test_data) -> EvaluationReport:
        """执行模型评估，返回完整评估报告"""
        raise NotImplementedError

    def calculate_psi(self, expected: list[float], actual: list[float], bins: int = 10) -> float:
        """计算 PSI — 监控模型分数的分布漂移"""
        raise NotImplementedError

    def calculate_ks(self, y_true: list[int], y_score: list[float]) -> float:
        """计算 KS 值 — 衡量模型区分好坏样本的能力"""
        raise NotImplementedError
