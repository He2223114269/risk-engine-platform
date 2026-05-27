"""模型注册 — 所有决策树模型在此注册"""
from risk_engine.model_registry.models.base import DecisionTreeModel
from risk_engine.model_registry.models.jiangxi_v1 import JiangxiV1

__all__ = ["DecisionTreeModel", "JiangxiV1"]
