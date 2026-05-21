#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : connectors
功能描述 : 数据连接器 — 连接器工厂模式
          支持 StarRocks / MySQL / Kafka 等数据源
          用法: ConnectorFactory.create('starrocks', password='xxx')
创建日期 : 2026-05-21
开发者   : Jingluo
版本     : v0.1.0
更新历史 :
  2026-05-21, Jingluo, v0.1.0 — 初始创建（factory / starrocks / mysql）
============================================================================
"""

from .factory import ConnectorFactory
from .starrocks import StarRocksConnector, StarRocksConfig
from .mysql import MySQLConnector, MySQLConfig

__all__ = [
    "ConnectorFactory",
    "StarRocksConnector",
    "StarRocksConfig",
    "MySQLConnector",
    "MySQLConfig",
]
