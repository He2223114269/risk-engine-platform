#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : connectors
功能描述 : 数据连接器 — 连接器工厂模式
          支持 StarRocks / MySQL / Kafka 等数据源
          用法: ConnectorFactory.create('starrocks')
创建日期 : 2026-05-21
开发者   : Jingluo
版本     : v0.1.0
============================================================================
"""

from .factory import ConnectorFactory
