#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : mysql
功能描述 : MySQL 数据库连接器
          用于连接淘顺分期 MySQL RDS 实例
          与 StarRocksConnector 接口一致，方便工厂模式统一调用
创建日期 : 2026-05-21
开发者   : Jingluo
版本     : v0.1.0
更新历史 :
  2026-05-21, Jingluo, v0.1.0 — 初始创建
============================================================================
"""

from __future__ import annotations

import pymysql
import pandas as pd
from typing import Optional
from dataclasses import dataclass

__all__ = ["MySQLConnector"]


@dataclass
class MySQLConfig:
    """MySQL 连接配置"""
    host: str = "taoshunfq.rwlb.rds.aliyuncs.com"
    port: int = 3306
    user: str = "taoshunfenqi_fk_hc"
    password: str = ""
    database: str = ""
    charset: str = "utf8mb4"
    connect_timeout: int = 10
    read_timeout: int = 60


class MySQLConnector:
    """
    MySQL 连接器

    与 StarRocksConnector 保持相同接口，
    可通过 ConnectorFactory 统一创建。

    Usage:
        conn = MySQLConnector(config)
        df = conn.query("SELECT * FROM some_table LIMIT 10")
    """

    def __init__(self, config: Optional[MySQLConfig] = None):
        self.config = config or MySQLConfig()
        self._connection: Optional[pymysql.Connection] = None

    # ─── 连接管理 ───────────────────────────────────────────────

    def connect(self) -> pymysql.Connection:
        if self._connection is None:
            self._connection = pymysql.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                charset=self.config.charset,
                connect_timeout=self.config.connect_timeout,
                read_timeout=self.config.read_timeout,
                cursorclass=pymysql.cursors.DictCursor,
            )
        return self._connection

    def close(self) -> None:
        if self._connection is not None:
            try:
                self._connection.close()
            except Exception:
                pass
            finally:
                self._connection = None

    @property
    def connection(self) -> pymysql.Connection:
        if self._connection is None:
            return self.connect()
        return self._connection

    # ─── 上下文管理器 ───────────────────────────────────────────

    def __enter__(self) -> MySQLConnector:
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    # ─── 查询方法 ───────────────────────────────────────────────

    def query(self, sql: str, params: Optional[dict] = None) -> pd.DataFrame:
        """执行 SQL 查询，返回 DataFrame"""
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            if not rows:
                return pd.DataFrame()
            return pd.DataFrame(rows)
        finally:
            cursor.close()

    def query_one(self, sql: str, params: Optional[dict] = None) -> Optional[dict]:
        """执行 SQL 查询，返回第一条结果"""
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql, params)
            return cursor.fetchone()
        finally:
            cursor.close()

    def execute(self, sql: str, params: Optional[dict] = None) -> int:
        """执行 DDL/DML 语句"""
        cursor = self.connection.cursor()
        try:
            affected = cursor.execute(sql, params)
            self.connection.commit()
            return affected
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        full_name = table_name.replace("`", "")
        sql = f"SELECT COUNT(*) as cnt FROM information_schema.tables WHERE table_name = %(table)s"
        result = self.query_one(sql, {"table": full_name.split(".")[-1]})
        return result is not None and result["cnt"] > 0

    def get_columns(self, table_name: str) -> list[dict]:
        """获取表字段信息"""
        sql = f"SHOW COLUMNS FROM `{table_name.replace('.', '`.`')}`"
        df = self.query(sql)
        return df.to_dict("records") if not df.empty else []

    def __repr__(self) -> str:
        return f"MySQLConnector({self.config.host}:{self.config.port})"
