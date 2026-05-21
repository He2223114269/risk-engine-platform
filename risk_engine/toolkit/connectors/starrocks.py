#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : starrocks
功能描述 : StarRocks 数据库连接器
          基于 pymysql 协议连接 StarRocks，封装查询执行与结果返回
          支持上下文管理器，自动管理连接生命周期
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

__all__ = ["StarRocksConnector"]


@dataclass
class StarRocksConfig:
    """StarRocks 连接配置"""
    host: str = "47.119.181.195"
    port: int = 9030
    user: str = "taoshun_fk_hc"
    password: str = ""
    database: str = ""
    charset: str = "utf8mb4"
    connect_timeout: int = 10
    read_timeout: int = 60


class StarRocksConnector:
    """
    StarRocks 连接器

    StarRocks 兼容 MySQL 协议，使用 pymysql 连接。
    支持直接执行 SQL 返回 DataFrame，也支持 fetch 逐条获取。

    Usage:
        conn = StarRocksConnector(config)
        df = conn.query("SELECT * FROM dws.dws_credit_yzf_order_complete LIMIT 10")
        print(df.head())

        # 上下文管理器
        with StarRocksConnector(config) as conn:
            df = conn.query("SELECT count(*) as cnt FROM ods.ods_ts_credit_yzf_order_grant_apply")
            print(df)
    """

    def __init__(self, config: Optional[StarRocksConfig] = None):
        self.config = config or StarRocksConfig()
        self._connection: Optional[pymysql.Connection] = None

    # ─── 连接管理 ───────────────────────────────────────────────

    def connect(self) -> pymysql.Connection:
        """建立数据库连接"""
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
        """关闭数据库连接"""
        if self._connection is not None:
            try:
                self._connection.close()
            except Exception:
                pass
            finally:
                self._connection = None

    @property
    def connection(self) -> pymysql.Connection:
        """获取连接，不存在时自动创建"""
        if self._connection is None:
            return self.connect()
        return self._connection

    # ─── 上下文管理器 ───────────────────────────────────────────

    def __enter__(self) -> StarRocksConnector:
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    # ─── 查询方法 ───────────────────────────────────────────────

    def query(self, sql: str, params: Optional[dict] = None) -> pd.DataFrame:
        """
        执行 SQL 查询，返回 DataFrame

        Args:
            sql: SQL 查询语句
            params: 查询参数（%s 占位符）
                     用法: query("SELECT * FROM t WHERE id = %(id)s", {"id": 123})

        Returns:
            查询结果的 DataFrame，空结果返回空 DataFrame
        """
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
        """
        执行 SQL 查询，返回第一条结果

        Returns:
            单行 dict，无结果返回 None
        """
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql, params)
            return cursor.fetchone()
        finally:
            cursor.close()

    def execute(self, sql: str, params: Optional[dict] = None) -> int:
        """
        执行 DDL/DML 语句（INSERT/UPDATE/DELETE/CREATE）

        Args:
            sql: SQL 语句
            params: 参数

        Returns:
            影响的行数
        """
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

    # ─── 便捷工具 ───────────────────────────────────────────────

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

    # ─── 信息 ───────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"StarRocksConnector({self.config.host}:{self.config.port})"
