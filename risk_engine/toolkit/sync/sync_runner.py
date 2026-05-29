"""
数据同步执行器
==============

遍历 sync_config 配置的表清单，从 StarRocks 拉取数据写入本地 MySQL。
支持全量和增量两种模式。
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from risk_engine.toolkit.connectors import get_data
from risk_engine.toolkit.sync.sync_config import SYNC_TABLES, SyncTableConfig
from risk_engine.toolkit.sync.sync_tracker import finish_sync, start_sync


def run_sync(
    table_names: list | None = None,
    mode: str = "full",
    sync_date: str = None,
    lookback_months: int = 24,
    write_to_db: bool = True,
) -> dict:
    """
    执行数据同步。

    参数:
        table_names: 要同步的表名列表，None=全部
        mode: 'full'=全量, 'incremental'=增量
        sync_date: 同步日期 (yyyy-MM-dd)，默认今天
        lookback_months: 全量模式回溯月数
        write_to_db: 是否写入本地库（False=只打印不写入）

    返回:
        {table_name: row_count}
    """
    sync_date = sync_date or datetime.now().strftime("%Y-%m-%d")
    results = {}

    tables = [t for t in SYNC_TABLES if table_names is None or t.name in table_names]

    if mode == "full":
        print(f"=== 全量同步: {len(tables)} 张表 ===")
    else:
        print(f"=== 增量同步: {len(tables)} 张表 ===")

    for tbl in tables:
        print(f"\n{'='*50}")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始: {tbl.name}")
        print(f"    源: {tbl.starrocks_table}")
        print(f"    筛选: {tbl.filter_sql}")

        # 追踪记录
        if write_to_db and not start_sync(tbl.name, sync_date):
            print("    ⏭️ 今日已同步，跳过")
            continue

        try:
            row_count = _sync_table(tbl, sync_date, mode, lookback_months, write_to_db)
            results[tbl.name] = row_count

            if write_to_db:
                finish_sync(tbl.name, sync_date, row_count, "success")
            print(f"    ✅ {row_count:,} 行")

        except Exception as e:
            print(f"    ❌ 失败: {e}")
            if write_to_db:
                finish_sync(tbl.name, sync_date, 0, "failed", str(e))
            results[tbl.name] = -1

    print(f"\n=== 同步完成: {len(results)} 张表 ===")
    for name, cnt in results.items():
        status = "✅" if cnt >= 0 else "❌"
        print(f"  {status} {name}: {cnt:,}" if cnt >= 0 else f"  {status} {name}: 失败")

    return results


def _sync_table(
    tbl: SyncTableConfig, sync_date: str, mode: str, lookback_months: int, write_to_db: bool
) -> int:
    """同步单张表。"""
    from risk_engine.toolkit.sync.sync_tracker import get_last_sync

    # 构建 SQL
    if mode == "full":
        where = tbl.filter_sql
        if lookback_months and tbl.incremental_key:
            where += f"\n  AND {tbl.incremental_key} >= DATE_SUB('{sync_date}', INTERVAL {lookback_months} MONTH)"
    else:
        last_date = get_last_sync(tbl.name)
        if last_date:
            where = f"{tbl.filter_sql}\n  AND {tbl.incremental_key} >= '{last_date}'"
        else:
            print("     ⚠️ 无上次同步记录，回退全量模式")
            where = tbl.filter_sql

    cols = ", ".join(tbl.columns) if tbl.columns else "*"

    sql = f"SELECT {cols} FROM {tbl.starrocks_table} WHERE {where}"

    # 分批取数
    offset = 0
    total_rows = 0
    all_data = []

    print(f"    SQL: {sql[:120]}...")

    conn_starrocks = get_data(data_type="risk")

    while True:
        batch_sql = f"{sql} LIMIT {tbl.batch_size} OFFSET {offset}"
        df = conn_starrocks.get_data(batch_sql)

        if df.empty:
            break

        all_data.append(df)
        total_rows += len(df)

        # 进度的简单标记
        if len(all_data) % 10 == 0:
            print(f"    已取 {total_rows:,} 行...", end="\r")

        offset += tbl.batch_size

    conn_starrocks.close()

    if not all_data:
        return 0

    df = pd.concat(all_data, ignore_index=True)
    del all_data  # 释放内存

    print(f"    已取 {total_rows:,} 行", " " * 20)

    # 写入本地库
    if write_to_db:
        _write_to_mysql(tbl, df, sync_date)

    return total_rows


def _qualified(tbl: SyncTableConfig) -> str:
    """返回全限定表名 `db.table`"""
    return f"`{tbl.db_name}`.`{tbl.name}`"


def _write_to_mysql(tbl: SyncTableConfig, df: pd.DataFrame, sync_date: str):
    """分批写入本地 MySQL。"""
    conn = get_data(data_type="local")

    _ensure_local_table(conn, tbl)

    full_name = _qualified(tbl)
    conn.execute_sql(f"DELETE FROM {full_name}")

    cursor = conn.conn.cursor()
    cols = list(df.columns)
    ph = ",".join(["%s"] * len(cols))
    cq = ",".join([f"`{c}`" for c in cols])
    sql = f"INSERT INTO {full_name} ({cq}) VALUES ({ph})"

    total = len(df)
    written = 0

    for start in range(0, total, tbl.batch_size):
        batch = df.iloc[start : start + tbl.batch_size]
        values_list = []
        for _, row in batch.iterrows():
            vals = []
            for v in row:
                if (
                    pd.isna(v)
                    or isinstance(v, (float, np.floating))
                    and (np.isnan(v) or np.isinf(v))
                ):
                    vals.append(None)
                else:
                    vals.append(v.item() if hasattr(v, "item") else v)
            values_list.append(tuple(vals))

        try:
            cursor.executemany(sql, values_list)
            conn.conn.commit()
            written += len(batch)
        except Exception:
            conn.conn.rollback()
            for vals in values_list:
                try:
                    cursor.execute(sql, vals)
                    conn.conn.commit()
                    written += 1
                except Exception:
                    conn.conn.rollback()

        if written % 50000 == 0:
            print(f"    已写入 {written:,}/{total:,}")

    cursor.close()
    conn.close()
    print(f"    💾 写入 {written:,}/{total:,} 行到 {full_name}")


def _ensure_local_table(conn, tbl: SyncTableConfig):
    """检查本地表是否存在，不存在则从 StarRocks 获取建表信息创建。"""
    full_name = _qualified(tbl)
    try:
        conn.get_data(f"SELECT 1 FROM {full_name} LIMIT 1")
        return
    except Exception:
        pass

    sr = get_data(data_type="risk")
    try:
        sample = sr.get_data(f"SELECT * FROM {tbl.starrocks_table} WHERE {tbl.filter_sql} LIMIT 0")
        if sample.empty:
            sample = sr.get_data(f"SELECT * FROM {tbl.starrocks_table} LIMIT 0")

        cols = sample.columns
        col_defs = []
        for c in cols:
            dtype = sample[c].dtype
            if dtype == "object":
                col_defs.append(f"`{c}` TEXT")
            elif "int" in str(dtype):
                col_defs.append(f"`{c}` BIGINT")
            elif "float" in str(dtype) or "decimal" in str(dtype):
                col_defs.append(f"`{c}` DOUBLE")
            elif "datetime" in str(dtype):
                col_defs.append(f"`{c}` DATETIME")
            elif "date" in str(dtype):
                col_defs.append(f"`{c}` DATE")
            else:
                col_defs.append(f"`{c}` TEXT")

        cols_str = ",\n    ".join(col_defs)
        pk = ", ".join(tbl.index_cols) if tbl.index_cols else "`_row_id` INT AUTO_INCREMENT"
        create_sql = f"CREATE TABLE {full_name} (\n    {cols_str},"
        if tbl.index_cols:
            create_sql += f"\n    PRIMARY KEY ({pk})"
        else:
            create_sql += "\n    `_row_id` INT AUTO_INCREMENT,\n    PRIMARY KEY (`_row_id`)"
        create_sql += "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"

        conn.execute_sql(create_sql)
        print(f"    📦 本地表 {full_name} 已自动创建")

    finally:
        sr.close()
