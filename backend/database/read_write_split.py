#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : read_write_split
功能描述 : 读写分离 — 根据 SQL 类型自动路由到主库或从库
创建日期 : 2026-05-21
开发者   : Jingluo
版本     : v0.1.0
============================================================================
"""

from __future__ import annotations

__all__ = ["ReadWriteRouter"]


class ReadWriteRouter:
    """数据库读写分离路由器"""

    def route_to_master(self) -> str:
        """路由到主库（写操作）"""
        raise NotImplementedError

    def route_to_slave(self) -> str:
        """路由到从库（读操作）"""
        raise NotImplementedError

    def should_use_master(self, sql: str) -> bool:
        """判断 SQL 是否需要在主库执行"""
        raise NotImplementedError
