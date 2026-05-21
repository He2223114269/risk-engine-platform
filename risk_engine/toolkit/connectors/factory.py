#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : factory
功能描述 : 数据库连接器工厂
          统一创建和管理不同类型数据库的连接器实例
          支持 StarRocks / MySQL / Local (SQLite) 三种数据源
          用法: ConnectorFactory.create('starrocks', password='xxx')
创建日期 : 2026-05-21
开发者   : Jingluo
版本     : v0.1.0
更新历史 :
  2026-05-21, Jingluo, v0.1.0 — 初始创建
============================================================================
"""

from __future__ import annotations

from typing import Optional

from .starrocks import StarRocksConnector, StarRocksConfig
from .mysql import MySQLConnector, MySQLConfig

__all__ = ["ConnectorFactory"]
_registry = {}

# ===== 连接器类型注册 =====

_REGISTERED_TYPES = {
    "starrocks": (StarRocksConnector, StarRocksConfig),
    "mysql": (MySQLConnector, MySQLConfig),
    "local": None,  # TODO: SQLite 连接器
}


class ConnectorFactory:
    """
    连接器工厂

    负责创建和管理数据库连接器。
    所有连接器对外暴露统一接口：query() / query_one() / execute()

    Usage:
        # 1. 创建连接器（每次返回新实例）
        conn = ConnectorFactory.create('starrocks', password='xxx')

        # 2. 查询数据
        df = conn.query("SELECT * FROM dws.dws_credit_yzf_order_complete LIMIT 10")

        # 3. 使用上下文管理器（自动关闭）
        with ConnectorFactory.create('starrocks', password='xxx') as conn:
            df = conn.query("SELECT count(*) as cnt FROM ods.ods_ts_credit_yzf_order_grant_apply")
            print(df)

        # 4. 创建 MySQL 连接器
        conn = ConnectorFactory.create('mysql', password='yyy')
    """

    @staticmethod
    def create(db_type: str, **kwargs) -> object:
        """
        创建数据库连接器

        Args:
            db_type: 数据库类型，支持 'starrocks' / 'mysql' / 'local'
            **kwargs: 连接参数，会覆盖默认配置
                      常用参数: host, port, user, password, database

        Returns:
            连接器实例（StarRocksConnector / MySQLConnector）

        Raises:
            ValueError: 不支持的数据库类型

        Usage:
            conn = ConnectorFactory.create(
                'starrocks',
                password='your_password',
                database='dws'
            )
        """
        if db_type not in _REGISTERED_TYPES:
            raise ValueError(
                f"不支持的数据库类型: '{db_type}'。"
                f"可用类型: {list(_REGISTERED_TYPES.keys())}"
            )

        connector_cls, config_cls = _REGISTERED_TYPES[db_type]

        # 用传入参数更新默认配置
        config = config_cls(**{k: v for k, v in kwargs.items() if hasattr(config_cls, k)})
        return connector_cls(config)

    @staticmethod
    def register(db_type: str, connector_cls, config_cls) -> None:
        """
        注册新的数据库类型（扩展用）

        Args:
            db_type: 数据库类型名称
            connector_cls: 连接器类
            config_cls: 配置类
        """
        _REGISTERED_TYPES[db_type] = (connector_cls, config_cls)

    @staticmethod
    def list_types() -> list[str]:
        """列出所有已注册的数据库类型"""
        return list(_REGISTERED_TYPES.keys())
