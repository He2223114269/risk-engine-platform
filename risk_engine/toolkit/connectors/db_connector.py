#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : db_connector
功能描述 : 数据库连接器 — get_data 类，通过 data_type 切换不同数据源
          设计继承自原 connect_db_offline.py，保留全部 data_type 和方法

支持的数据源:
    risk      风险 StarRocks      47.119.181.195:9030    ods
    ts        淘顺分期 MySQL      taoshunfq...:3306     taoshun_fenqi
    bl        百旅分期             bailv...:3306         bailv_np
    bl_risk   百旅风控             bailv...:3306         bailv_np
    tr_risk   通融分期             腾讯云CLB:3306        bailv_np
    tr_fusing 通融分期(同)         腾讯云CLB:3306        bailv_np
    ts_risk   淘顺风控(旧)         taoshunfq...:3306     taoshun_fenqi
    ts_fusing 淘顺风控(旧/同)      taoshunfq...:3306     taoshun_fenqi
    tsck      淘顺全库             阿里云RDS:3306        taoshun_all
    hive      Hive大数据           47.107.182.51:10000   ods
    local     本地库               localhost:3306        risk_control

密码来源（优先级）:
  1. risk_engine/config/db_config_secret.py（含明文密码，已 gitignore）
  2. risk_engine/config/db_config.py（模板，密码为空则走环境变量）
  3. 环境变量（如 RISK_DB_PASSWORD、TS_DB_PASSWORD 等）

用法:
    from risk_engine.toolkit.connectors import get_data

    conn = get_data(data_type='risk')
    df = conn.get_data("SELECT * FROM ods.some_table LIMIT 10")
    conn.close()

    with get_data(data_type='ts') as conn:
        df = conn.get_data("SELECT * FROM taoshun_fenqi.some_table LIMIT 5")

更新历史:
  2026-05-21, Jingluo, v2.0.0 — 配置分离到 db_config[_secret].py
============================================================================
"""

from __future__ import annotations

import os
import pymysql
import pandas as pd
from typing import Optional

__all__ = ["get_data"]


# ===== 加载配置（优先明文文件，其次模板文件+环境变量） =====

def _load_config(data_type: str) -> dict:
    """
    加载指定 data_type 的数据库配置

    优先级:
      1. db_config_secret.py（含明文密码，已 gitignore）
      2. db_config.py（模板，密码为空则读环境变量）
    """
    config = None

    # 1. 尝试加载明文配置
    try:
        from risk_engine.config import db_config_secret
        config = db_config_secret.DB_CONFIG.get(data_type)
        if config:
            return dict(config)
    except (ImportError, AttributeError):
        pass

    # 2. 尝试加载模板配置
    try:
        from risk_engine.config import db_config
        config = db_config.DB_CONFIG.get(data_type)
    except (ImportError, AttributeError):
        pass

    if config is None:
        raise ValueError(
            f"不支持的 data_type: '{data_type}'。"
            f"请检查 risk_engine/config/db_config[_secret].py 中是否包含此类型"
        )

    config = dict(config)

    # 3. 如果密码为空，尝试环境变量
    if not config.get("password"):
        env_var = config.get("env_var", "")
        env_pwd = os.environ.get(env_var) if env_var else None
        if env_pwd:
            config["password"] = env_pwd
        else:
            raise ConnectionError(
                f"{data_type} 密码未配置。请:\n"
                f"  1. 创建 risk_engine/config/db_config_secret.py（推荐）\n"
                f"  2. 或设置环境变量 {env_var}"
            )

    return config


# ===== 主类 =====

class get_data:
    """
    数据库连接操作类

    通过 data_type 选择数据库，统一方法集。

    Usage:
        conn = get_data(data_type='risk')
        df = conn.get_data("SELECT * FROM ods.some_table LIMIT 10")
        conn.close()

        with get_data(data_type='dws') as conn:
            df = conn.get_data("SELECT * FROM dws_credit_yzf_order_complete LIMIT 5")
    """

    def __init__(self, data_type: str = "risk", db: Optional[str] = None):
        """
        Args:
            data_type: 数据库类型，见模块文档
            db: 覆盖默认数据库名（主要用于 risk 类型切换 schema）
        """
        config = _load_config(data_type)

        self.mysql_host = config["host"]
        self.mysql_port = config["port"]
        self.mysql_user = config["user"]
        self.mysql_password = config["password"]
        self.mysql_db = db if db else config["database"]
        self.data_type = data_type

        self.conn: Optional[pymysql.Connection] = None
        self.connect_to_database()

    # ─── 连接管理 ───────────────────────────────────────────────

    def connect_to_database(self) -> None:
        """连接数据库"""
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
                f"连接失败: {self.mysql_user}@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}\n  {e}"
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
        """检查连接是否可用"""
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
        cursor = self.conn.cursor()
        try:
            cursor.execute(sql_content)
            rows = cursor.fetchall()
            if not rows:
                return pd.DataFrame()
            columns = [desc[0] for desc in cursor.description]
            df = pd.DataFrame(rows, columns=columns)
            return df
        finally:
            cursor.close()

    def get_newest_data(self, sheet_name: str, columns: str = "*") -> pd.DataFrame:
        """获取整表数据（便捷方法）"""
        sql = f"SELECT {columns} FROM {self.mysql_db}.{sheet_name}"
        return self.get_data(sql)

    # ─── 分批查询（用于 StarRocks 大 IN 查询） ───────────────

    def injoin_data(self, id_list: list, sql_content: str) -> pd.DataFrame:
        """
        每次 10000 条分批查询

        Args:
            id_list: ID 列表
            sql_content: SQL 前缀，如 "SELECT * FROM table WHERE id"

        Returns:
            合并后的 DataFrame
        """
        result = pd.DataFrame()
        for i in range(0, len(id_list), 10000):
            chunk = id_list[i : i + 10000]
            if len(chunk) == 1:
                chunk = chunk + [chunk[0]]
            sql = f"{sql_content} IN {tuple(chunk)}"
            chunk_df = pd.read_sql_query(sql, self.conn)
            result = pd.concat([result, chunk_df], ignore_index=True)
        return result

    # ─── 数据写入 ───────────────────────────────────────────────

    def to_sql(self, table_name: str, data: pd.DataFrame) -> None:
        """将 DataFrame 写入数据库表（INSERT）"""
        if not self.is_connection_open():
            self.connect_to_database()

        columns_list = list(data.columns)
        columns_str = ",".join([f"`{c}`" for c in columns_list])
        fill_str = ",".join(["%s"] * len(columns_list))
        sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({fill_str})"
        write_in = [tuple(row) for row in data[columns_list].to_numpy()]

        cursor = self.conn.cursor()
        try:
            cursor.executemany(sql, write_in)
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
        插入数据，记录成功/失败明细

        Args:
            data: 要插入的数据
            table_name: 目标表名
            insert_type: insert / replace / upsert / replace_all

        Returns:
            (success_df, failed_df)
        """
        if not self.is_connection_open():
            self.connect_to_database()

        cursor = self.conn.cursor()
        cols = ",".join([f"`{col}`" for col in data.columns])
        values = "(" + ",".join(["%s"] * len(data.columns)) + ")"

        if insert_type == "insert":
            prefix = f"INSERT INTO `{table_name}` ({cols}) VALUES "
            suffix = ""
        elif insert_type == "replace":
            prefix = f"REPLACE INTO `{table_name}` ({cols}) VALUES "
            suffix = ""
        elif insert_type == "upsert":
            update = ", ".join([f"`{c}`=VALUES(`{c}`)" for c in data.columns])
            prefix = f"INSERT INTO `{table_name}` ({cols}) VALUES "
            suffix = f" ON DUPLICATE KEY UPDATE {update}"
        elif insert_type == "replace_all":
            cursor.execute(f"DELETE FROM `{table_name}`")
            self.conn.commit()
            prefix = f"INSERT INTO `{table_name}` ({cols}) VALUES "
            suffix = ""
        else:
            raise ValueError("insert_type: insert / replace / upsert / replace_all")

        success, failed = [], []
        for idx, row in enumerate(data.itertuples(index=False, name=None)):
            try:
                cursor.execute(prefix + values + suffix, row)
                success.append(data.iloc[idx])
            except Exception:
                failed.append(data.iloc[idx])
        self.conn.commit()
        cursor.close()

        cols_list = list(data.columns)
        return (
            pd.DataFrame(success, columns=cols_list) if success else pd.DataFrame(columns=cols_list),
            pd.DataFrame(failed, columns=cols_list) if failed else pd.DataFrame(columns=cols_list),
        )

    # ─── 更新 / 删除 ────────────────────────────────────────────

    def update_sql(self, table_name: str, condition_data: pd.DataFrame, value_data: pd.DataFrame) -> None:
        """批量更新数据"""
        if condition_data.shape[0] != value_data.shape[0]:
            raise ValueError("condition_data 和 value_data 行数不一致")

        set_str = ",".join([f"{c}=%s" for c in value_data.columns])
        where_str = " AND ".join([f"{c}=%s" for c in condition_data.columns])
        sql = f"UPDATE {table_name} SET {set_str} WHERE {where_str}"
        rows = [tuple(r) for r in pd.concat([value_data, condition_data], axis=1).to_numpy()]

        cursor = self.conn.cursor()
        try:
            cursor.executemany(sql, rows)
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cursor.close()

    def for_update_sql(self, table_name: str, condition_data: pd.DataFrame, value_data: pd.DataFrame) -> None:
        """逐条更新（慢但可控）"""
        total = pd.concat([condition_data, value_data], axis=1)
        cursor = self.conn.cursor()
        try:
            for _, row in total.iterrows():
                set_clause = ",".join([f'{c}="{row[c]}"' for c in value_data.columns])
                where_clause = " AND ".join([
                    f'{c}={int(row[c]) if c == "id" else chr(34) + str(row[c]) + chr(34)}'
                    for c in condition_data.columns
                ])
                cursor.execute(f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}")
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cursor.close()

    def clear_table(self, table_name: str) -> None:
        """清空表"""
        self.execute_sql(f"TRUNCATE TABLE {table_name}")

    def execute_sql(self, sql_sentence: str) -> None:
        """执行任意 SQL"""
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
        tbl = table_name.split(".")[-1]
        df = self.get_data(
            f"SELECT COUNT(*) as cnt FROM information_schema.tables WHERE table_name='{tbl}'"
        )
        return not df.empty and df.iloc[0]["cnt"] > 0

    def get_columns(self, table_name: str) -> pd.DataFrame:
        """获取表字段信息"""
        name = table_name.replace(".", "`.`")
        return self.get_data(f"SHOW COLUMNS FROM `{name}`")

    # ─── 信息 ───────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"get_data({self.data_type}) → {self.mysql_user}@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
