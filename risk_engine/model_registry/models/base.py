"""决策树模型基类 — 所有决策树模型的统一接口"""
from __future__ import annotations
from abc import ABC, abstractmethod

import pandas as pd


class DecisionTreeModel(ABC):
    """决策树模型基类

    子类必须实现:
      - model_id     : 模型唯一标识
      - features     : 输入特征列表
      - classify()   : 单行分类逻辑
      - get_branch_info() : 分支中文说明
    """

    model_id: str = ""
    features: list[str] = []
    version: str = ""
    description: str = ""

    @abstractmethod
    def classify(self, row: pd.Series) -> str:
        """对单行数据分类，返回策略分支ID"""
        ...

    def classify_batch(self, data: pd.DataFrame) -> pd.DataFrame:
        """批量分类，追加 strategy_type 列"""
        data = data.copy()
        data["strategy_type"] = data.apply(self.classify, axis=1)
        return data

    def get_branch_info(self, branch_id: str) -> str:
        """返回分支的中文说明（可选覆盖）"""
        return ""

    def list_branches(self) -> list[str]:
        """返回全部分支ID（可选覆盖）"""
        return []
