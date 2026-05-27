#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : base
功能描述 : ORM 基类 — 所有数据库模型的基类
          通用字段：id, created_at, updated_at, version, deleted_at
创建日期 : 2026-05-21
开发者   : Jingluo
版本     : v0.1.0
更新历史 :
  2026-05-21, Jingluo, v0.1.0 — 初始创建
============================================================================
"""

from __future__ import annotations
from sqlalchemy import Column, DateTime, Integer, String, Boolean, func
from sqlalchemy.orm import DeclarativeBase

__all__ = ["Base", "TimestampMixin"]


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""

    pass


class TimestampMixin:
    """时间戳混入 — 所有表必备字段"""

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间"
    )
    version = Column(Integer, default=1, nullable=False, comment="数据版本号")
    deleted_at = Column(DateTime, nullable=True, comment="软删除时间")
