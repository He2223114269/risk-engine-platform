#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : db_connector
功能描述 : 数据库连接器 — 单类通吃所有数据源
          通过 data_type 参数自动选择对应的库、账号、主机
          支持 StarRocks(风险库) / MySQL(淘顺分期) / 本地库
          统一方法: get_data / to_sql / insert_data / close

设计思路:
  get_data 类封装了所有数据库连接配置和操作，
  只需在初始化时传入 data_type 即可切换数据源:
    conn = get_data(data_type='risk')  → 连风险 StarRocks
    conn = get_data(data_type='ts')    → 连淘顺分期 MySQL
    conn = get_data(data_type='local') → 连本地库

更新历史:
  2026-05-21, Jingluo, v1.0.0 — 基于原 connect_db_offline.py 重构
  2026-05-21, Jingluo, v1.0.0 — 密码改环境变量读取，新增上下文管理器
============================================================================
"""

from __future__ import annotations

import os
import pymysql
import pandas as pd
from typing import Optional

__all__ = ["get_data"]


# ===== 数据库配置 =====
# 密码优先从环境变量读取，未设置时使用默认值（本地库可用）
# 生产库密码请在 .env 或系统环境变量中配置

DB_CONFIG = {
    "starrocks": {
        "host": "47.119.181.195",
        "port": 9030,
        "user": "taoshun_fk_zf",
        "password_env": "RISK_DB_PASSWORD",
        "password_default": "P5]xk!9,u$t[JIPf1~4)",
        "database_default": "ods",
    },
    "risk": {
        "host": "47.119.181.195",
        "port": 9030,
        "user": "taoshun_fk_zf",
        "password_env": "RISK_DB_PASSWORD",
        "password_default": "P5]xk!9,u$t[JIPf1~4)",
        "database_default": "ods",
    },
    "ts": {
        "host": "taoshunfq.rwlb.rds.aliyuncs.com",
        "port": 3306,
        "user": "taoshunfenqi_fk_ZF",
        "password_env": "TS_DB_PASSWORD",
        "password_default": "taoshunfenqi_fk_zfa@csts1314*",
        "database_default": "taoshun_fenqi",
    },
    "local": {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password_env": "LOCAL_DB_PASSWORD",
        "password_default": "222311",
        "database_default": "risk_control",
    },
    "dws": {
        "host": "47.119.181.195",
        "port": 9030,
        "user": "taoshun_fk_zf",
        "password_env": "RISK_DB_PASSWORD",
        "password_default": "P5]xk!9,u$t[JIPf1~4)",
        "database_default": "dws",
    },
    "dwd": {
        "host": "47.119.181.195",
        "port": 9030,
        "user": "taoshun_fk_zf",
        "password_env": "RISK_DB_PASSWORD",
        "password_default": "P5]xk!9,u$t[JIPf1~4)",
        "database_default": "dwd",
    },
}


def _get_password(config: dict) -> str:
    """优先从环境变量读取密码，否则用默认值"""
    env_var = config.get("password_env")
    if env_var:
        env_pwd = os.environ.get(env_var)
        if env_pwd:
            return env_pwd
    return config.get("password_default", "")


class get_data:
    """
    数据库连接操作类 — 兼容原 connect_db_offline 用法

    通过 data_type 选择数据库，所有方法统一调用。

    Usage:
        # 基础用法
        conn = get_data(data_type='risk')
        df = conn.get_data("SELECT * FROM ods.some_table LIMIT 10")

        # 切换库
        conn = get_data(data_type='ts')        # 淘顺分期
        conn = get_data(data_type='local')     # 本地库
        conn = get_data(data_type='dws')       # 风险库 dws 库

        # 上下文管理器（自动关闭）
        with get_data(data_type='risk') as conn:
            df = conn.get_data("SELECT count(*) as cnt FROM ods.some_table")

        # 写入数据
        conn.to_sql("my_table", df)

        # 带日志的插入
        succ, fail = conn.insert_data(df, "my_table", insert_type='upsert')
    """

    def __init__(self, data_type: str = "risk", db: Optional[str] = None):
        """
        Args:
            data_type: 数据库类型
                'starrocks' / 'risk' — 风险 StarRocks（默认 ods 库）
                'dws' — 风险 StarRocks 的 dws 库
                'dwd' — 风险 StarRocks 的 dwd 库
                'ts'  — 淘顺分期 MySQL
                'local' — 本地 MySQL
            db: 指定数据库名（覆盖默认），主要用于 risk 类型切换 schema
        """
        config = DB_CONFIG.get(data_type)
        if config is None:
            raise ValueError(f"不支持的 data_type: '{data_type}'。可选: {list(DB_CONFIG.keys())}")

        self.mysql_host = config["host"]
        self.mysql_port = config["port"]
        self.mysql_user = config["user"]
        self.mysql_password = _get_password(config)
        self.mysql_db = db if db else config["database_default"]
        self.data_type = data_type

        self.conn: Optional[pymysql.Connection] = None
        self.connect_to_database()

    # ─── 连接管理 ───────────────────────────────────────────────

    def connect_to_database(self) -> None:
        """连接数据库（初始化时自动调用，也可手动重连）"""
        try:
            self.conn = pymysql.connect(
                host=self.mysql_host,
                port=self.mysql_port,
                user=self.mysql_user,
                password=self.mysql_password,
                database=self.mysql_db,
                charset="utf8mb4",
                connect_timeout=10,
                cursorclass=pymysql.cursors.DictCursor,
            )
        except Exception as e:
            raise ConnectionError(
                f"连接失败: {self.mysql_user}@{self.mysql_host}:{self.mysql_port}/{self.mysql_db} — {e}"
            )

    def close(self) -> None:
        """关闭数据库连接"""
        if self.conn:
            try:
                self.conn.cursor().close()
                self.conn.close()
            except Exception:
                pass
            finally:
                self.conn = None

    def is_connection_open(self) -> bool:
        """检查连接是否可用，断开时自动尝试重连"""
        try:
            if self.conn:
                self.conn.ping(reconnect=True)
                return True
            return False
        except Exception:
            return False

    # ─── 上下文管理器 ───────────────────────────────────────────

    def __enter__(self) -> get_data:
        if not self.is_connection_open():
            self.connect_to_database()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    # ─── 数据查询 ───────────────────────────────────────────────

    def get_data(self, sql_content: str) -> pd.DataFrame:
        """
        执行 SQL 查询，返回 DataFrame

        Args:
            sql_content: SQL 查询语句

        Returns:
            查询结果 DataFrame
        """
        if not self.is_connection_open():
            self.connect_to_database()
        return pd.read_sql_query(sql_content, self.conn)

    def get_newest_data(self, sheet_name: str, columns: str = "*") -> pd.DataFrame:
        """获取整表数据（便捷方法）"""
        sql = f"SELECT {columns} FROM {self.mysql_db}.{sheet_name}"
        return self.get_data(sql)

    # ─── 批量查询（按 ID 分批，用于 StarRocks 大表） ─────────

    def injoin_data(self, id_list: list, sql_content: str) -> pd.DataFrame:
        """
        每次 10000 条分批查询，适用于 StarRocks 大 IN 查询

        Args:
            id_list: ID 列表
            sql_content: SQL 前缀，如 "SELECT * FROM table WHERE id IN"

        Returns:
            合并后的 DataFrame
        """
        import numpy as np

        result = pd.DataFrame()
        for i in range(0, len(id_list), 10000):
            chunk_ids = id_list[i : i + 10000]
            if len(chunk_ids) == 1:
                chunk_ids = chunk_ids + [chunk_ids[0]]
            sql = f"{sql_content} IN {tuple(chunk_ids)}"
            chunk = pd.read_sql_query(sql, self.conn)
            result = pd.concat([result, chunk], ignore_index=True)
        return result

    # ─── 数据写入 ───────────────────────────────────────────────

    def to_sql(self, table_name: str, data: pd.DataFrame) -> None:
        """
        将 DataFrame 写入数据库表（INSERT）

        Args:
            table_name: 目标表名
            data: 要写入的数据
        """
        if not self.is_connection_open():
            self.connect_to_database()

        columns_list = list(data.columns)
        columns_str = "`,`".join(columns_list)
        columns_str = f"`{columns_str}`"
        fill_str = ",".join(["%s"] * len(columns_list))

        sql_insert = f"INSERT INTO {table_name} ({columns_str}) VALUES ({fill_str})"
        write_in = [tuple(row) for row in data[columns_list].to_numpy()]

        cursor = self.conn.cursor()
        try:
            cursor.executemany(sql_insert, write_in)
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cursor.close()

    def insert_data(
        self,
        data: pd.DataFrame,
        table_name: str,
        insert_type: str = "insert",
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        将 DataFrame 插入数据库，记录成功/失败明细

        Args:
            data: 要插入的数据
            table_name: 目标表名
            insert_type: 插入模式
                'insert'      — 普通 INSERT
                'replace'     — REPLACE INTO
                'upsert'      — INSERT ... ON DUPLICATE KEY UPDATE
                'replace_all' — 先清空表再 INSERT

        Returns:
            (success_df, failed_df) — 成功和失败的数据
        """
        if not self.is_connection_open():
            self.connect_to_database()

        cursor = self.conn.cursor()
        cols = ",".join([f"`{col}`" for col in data.columns])
        values_template = "(" + ",".join(["%s"] * len(data.columns)) + ")"

        if insert_type == "insert":
            sql_prefix = f"INSERT INTO `{table_name}` ({cols}) VALUES "
            sql_suffix = ""
        elif insert_type == "replace":
            sql_prefix = f"REPLACE INTO `{table_name}` ({cols}) VALUES "
            sql_suffix = ""
        elif insert_type == "upsert":
            update_clause = ", ".join([f"`{col}`=VALUES(`{col}`)" for col in data.columns])
            sql_prefix = f"INSERT INTO `{table_name}` ({cols}) VALUES "
            sql_suffix = f" ON DUPLICATE KEY UPDATE {update_clause}"
        elif insert_type == "replace_all":
            try:
                cursor.execute(f"DELETE FROM `{table_name}`")
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                return pd.DataFrame(), data
            sql_prefix = f"INSERT INTO `{table_name}` ({cols}) VALUES "
            sql_suffix = ""
        else:
            raise ValueError("insert_type 仅支持: insert / replace / upsert / replace_all")

        success_rows = []
        failed_rows = []
        for idx, row in enumerate(data.itertuples(index=False, name=None)):
            try:
                sql = sql_prefix + values_template + sql_suffix
                cursor.execute(sql, row)
                success_rows.append(data.iloc[idx])
            except Exception:
                failed_rows.append(data.iloc[idx])

        self.conn.commit()
        cursor.close()

        success_df = pd.DataFrame(success_rows) if success_rows else pd.DataFrame(columns=data.columns)
        failed_df = pd.DataFrame(failed_rows) if failed_rows else pd.DataFrame(columns=data.columns)
        return success_df, failed_df

    # ─── 更新 / 删除 ────────────────────────────────────────────

    def update_sql(self, table_name: str, condition_data: pd.DataFrame, value_data: pd.DataFrame) -> None:
        """
        批量更新数据

        Args:
            table_name: 目标表名
            condition_data: WHERE 条件列
            value_data: SET 值的列
        """
        if condition_data.shape[0] != value_data.shape[0]:
            raise ValueError("condition_data 和 value_data 行数不一致")

        values_columns = list(value_data.columns)
        condition_columns = list(condition_data.columns)

        values_str = ",".join([f"{c}=%s" for c in values_columns])
        condition_str = " AND ".join([f"{c}=%s" for c in condition_columns])

        sql_update = f"UPDATE {table_name} SET {values_str} WHERE {condition_str}"
        write_in = [
            tuple(row)
            for row in pd.concat([value_data, condition_data], axis=1).to_numpy()
        ]

        cursor = self.conn.cursor()
        try:
            cursor.executemany(sql_update, write_in)
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cursor.close()

    def for_update_sql(self, table_name: str, condition_data: pd.DataFrame, value_data: pd.DataFrame) -> None:
        """逐条更新（慢但可控，适合小批量）"""
        total_data = pd.concat([condition_data, value_data], axis=1)
        cursor = self.conn.cursor()
        try:
            for _, row in total_data.iterrows():
                set_parts = [f'{col}="{row[col]}"' for col in value_data.columns]
                set_value = ",".join(set_parts)

                where_parts = []
                for col in condition_data.columns:
                    val = int(row[col]) if col == "id" else f'"{row[col]}"'
                    where_parts.append(f'{col}={val}')
                where_value = " AND ".join(where_parts)

                sql = f"UPDATE {table_name} SET {set_value} WHERE {where_value}"
                cursor.execute(sql)
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cursor.close()

    def clear_table(self, table_name: str) -> None:
        """清空表数据"""
        cursor = self.conn.cursor()
        try:
            cursor.execute(f"TRUNCATE TABLE {table_name}")
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cursor.close()

    def execute_sql(self, sql_sentence: str) -> None:
        """执行任意 SQL（DDL/DML）"""
        cursor = self.conn.cursor()
        try:
            cursor.execute(sql_sentence)
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cursor.close()

    # ─── 工具方法 ───────────────────────────────────────────────

    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        sql = f"SELECT COUNT(*) as cnt FROM information_schema.tables WHERE table_name='{table_name.split('.')[-1]}'"
        df = self.get_data(sql)
        return not df.empty and df.iloc[0]["cnt"] > 0

    def get_columns(self, table_name: str) -> pd.DataFrame:
        """获取表字段信息"""
        sql = f"SHOW COLUMNS FROM `{table_name.replace('.', '`.`')}`"
        return self.get_data(sql)

    # ─── 信息 ───────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"get_data({self.data_type}) → {self.mysql_user}@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
