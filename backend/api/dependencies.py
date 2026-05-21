#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : dependencies
功能描述 : FastAPI 依赖注入 — 统一管理数据库会话、Redis 连接、配置等依赖
          所有路由通过依赖注入获取服务实例，便于测试时 mock
创建日期 : 2026-05-21
开发者   : Jingluo
版本     : v0.1.0
============================================================================
"""

from __future__ import annotations

__all__ = [
    "get_db_session",
    "get_redis_client",
    "get_current_user",
]


def get_db_session():
    """获取数据库会话（FastAPI Depends）"""
    raise NotImplementedError


def get_redis_client():
    """获取 Redis 客户端"""
    raise NotImplementedError


def get_current_user(token: str) -> dict:
    """解析当前用户信息（JWT）"""
    raise NotImplementedError
