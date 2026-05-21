#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : connectors
功能描述 : 数据库连接器 — 单类通吃所有数据源

核心类: get_data(data_type)
  - data_type='risk'  → 风险 StarRocks (47.119.181.195:9030)
  - data_type='ts'    → 淘顺分期 MySQL
  - data_type='local' → 本地库
  - data_type='dws'   → 风险 StarRocks 的 dws 库
  - data_type='dwd'   → 风险 StarRocks 的 dwd 库

用法:
    from risk_engine.toolkit.connectors import get_data

    conn = get_data(data_type='risk')
    df = conn.get_data("SELECT * FROM ods.some_table LIMIT 10")
    conn.close()

    # 或上下文管理器（自动关闭）
    with get_data(data_type='dws') as conn:
        df = conn.get_data("SELECT * FROM dws_credit_yzf_order_complete LIMIT 5")

设计说明:
    继承原 connect_db_offline.py 的 get_data 类设计思想：
    一个类通过 data_type 参数切换不同数据库，避免为每个库写重复代码。
    密码优先从环境变量读取，未设置时使用内置默认值。

更新历史:
  2026-05-21, Jingluo, v1.0.0 — 基于原 connect_db_offline 重构
============================================================================
"""

from .db_connector import get_data

__all__ = ["get_data"]
