#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : orm
功能描述 : ORM 模型 — SQLAlchemy 2.0 声明式模型定义
          所有表继承 base.py 基类（id, created_at, updated_at, version, deleted_at）

模型清单:
    supplier_rating.SupplierEvaluation — 代理商综合评价表
    store_rating.StoreEvaluation       — 门店综合评价表
    package_rating.PackageEvaluation   — 套餐综合评价表

创建日期 : 2026-05-21
开发者   : Jingluo
版本     : v0.2.0
更新历史 :
  2026-05-26, Jingluo, v0.2.0 — 统一模型导出入口
============================================================================
"""

from __future__ import annotations

from backend.database.orm.package_rating import PackageEvaluation
from backend.database.orm.store_rating import StoreEvaluation

# 统一导出所有 ORM 模型，方便外部引用
from backend.database.orm.supplier_rating import SupplierEvaluation

__all__ = [
    "SupplierEvaluation",
    "StoreEvaluation",
    "PackageEvaluation",
]
