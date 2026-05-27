"""
数据同步执行器 v2
================

基于 ddl_registry 的 DDL 定义，从 StarRocks 拉取数据写入本地 MySQL。
支持全量/增量模式，自动建表，分批读写。
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from risk_engine.toolkit.connectors import get_data
from risk_engine.toolkit.sync.ddl_registry import (
    ALL_TABLES,
    DDLEntry,
    get_starrocks_mapping,
    get_table,
    get_tables_by_schema,
)
from risk_engine.toolkit.sync.sync_tracker import finish_sync, start_sync


def run_sync(
    table_names: list | None = None,
    schema: str | None = None,
    mode: str = "full",
    sync_date: str = None,
    lookback_months: int = 24,
) -> dict:
    """
    执行数据同步。

    用法:
        # 同步全部表
        run_sync()

        # 只同步 ODS 层
        run_sync(schema="ods")

        # 只同步某几张表
        run_sync(table_names=["ods_ts_v3_order_store", "dws_credit_yzf_order_complete"])

        # 增量同步（只拉取上次同步以来的新数据）
        run_sync(mode="incremental")
    """
    sync_date = sync_date or datetime.now().strftime("%Y-%m-%d")
    results = {}

    if table_names:
        tables = [get_table(n) for n in table_names if get_table(n)]
    elif schema:
        tables = get_tables_by_schema(schema)
    else:
        tables = ALL_TABLES

    if not tables:
        print("⚠️ 没有找到匹配的表")
        return results

    print(f"{'='*50}")
    print(f"  数据同步  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  模式: {mode}  |  表数: {len(tables)}")
    print(f"{'='*50}")

    for tbl in tables:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {tbl.schema_name}.{tbl.table_name}")
        print(f"    {tbl.description} | 预估 {tbl.row_estimate:,} 行")

        # 检查是否已同步过
        if mode == "incremental" and not start_sync(tbl.table_name, sync_date):
            print("    ⏭️ 今日已同步，跳过")
            continue

        try:
            row_count = _sync_table(tbl, sync_date, mode, lookback_months)
            results[tbl.table_name] = row_count
            if mode == "incremental":
                finish_sync(tbl.table_name, sync_date, row_count, "success")
            print(f"    ✅ {row_count:,} 行")
        except Exception as e:
            print(f"    ❌ 失败: {e}")
            if mode == "incremental":
                finish_sync(tbl.table_name, sync_date, 0, "failed", str(e))
            results[tbl.table_name] = -1

    print(f"\n{'='*50}")
    print("  同步完成")
    for name, cnt in results.items():
        status = "✅" if cnt >= 0 else "❌"
        print(f"  {status} {name}: {cnt:,}" if cnt >= 0 else f"  {status} {name}: 失败")
    print(f"{'='*50}")

    return results


def _sync_table(tbl: DDLEntry, sync_date: str, mode: str, lookback_months: int) -> int:
    """同步单张表。"""

    # 1. 确保本地表存在
    _ensure_local_table(tbl)

    # 2. 构建查询 SQL
    starrocks_table = get_starrocks_mapping(tbl.table_name)
    filter_sql = _build_filter(tbl, sync_date, mode, lookback_months)

    sql = f"SELECT * FROM {starrocks_table} WHERE {filter_sql}"
    print(f"    SQL: {sql[:100]}...")

    # 3. 分批从 StarRocks 取数
    sr = get_data(data_type="risk")
    offset = 0
    total = 0
    batches = []

    while True:
        batch_sql = f"{sql} LIMIT {tbl.batch_size} OFFSET {offset}"
        df = sr.get_data(batch_sql)
        if df.empty:
            break
        batches.append(df)
        total += len(df)
        if len(batches) % 15 == 0:
            print(f"    已取 {total:,} 行...", end="\r")
        offset += tbl.batch_size

    sr.close()

    if not batches:
        return 0

    # 4. 合并
    df = pd.concat(batches, ignore_index=True)
    del batches
    print(f"    已取 {total:,} 行")

    # 5. 写入本地 MySQL
    _write_to_local(tbl, df)

    return total


def _build_filter(tbl: DDLEntry, sync_date: str, mode: str, lookback_months: int) -> str:
    """构建 WHERE 条件"""
    filters = []

    # 按业务类型筛选
    type_filters = {
        "ods_ts_order_white_list_control": "type = '淘顺实时授信'",
        "ods_ts_credit_yzf_order_grant_apply": "business_type = '02'",
        "dws_credit_yzf_order_complete": "source_business_type = '淘顺实时授信'",
    }
    f = type_filters.get(tbl.table_name)
    if f:
        filters.append(f)

    # 全量模式的时间回溯
    if mode == "full" and lookback_months:
        time_cols = {
            "ods_ts_credit_yzf_order_repayment": "due_date",
            "ods_ts_credit_yzf_order_info_complete": "complete_time",
            "ods.ods_ts_credit_yzf_order_grant_apply": "apply_time",
        }
        tc = time_cols.get(tbl.table_name)
        if tc:
            filters.append(f"{tc} >= DATE_SUB('{sync_date}', INTERVAL {lookback_months} MONTH)")

    # 增量模式
    if mode == "incremental":
        last_date = get_last_sync(tbl.table_name)
        if last_date:
            time_cols = {
                "ods_ts_credit_yzf_order_repayment": "repay_date",
                "ods_ts_order_white_list_control": "update_time",
            }
            tc = time_cols.get(tbl.table_name)
            if tc:
                filters.append(f"{tc} >= '{last_date}'")

    return " AND ".join(filters) if filters else "1=1"


def _ensure_local_table(tbl: DDLEntry):
    """确保本地表存在。先建库，再建表。"""
    conn = get_data(data_type="local")

    # 建 schema（如果不存在）
    conn.execute_sql(f"CREATE DATABASE IF NOT EXISTS `{tbl.schema_name}`")

    # 建表
    try:
        conn.get_data(f"SELECT 1 FROM {tbl.schema_name}.{tbl.table_name} LIMIT 1")
    except Exception:
        conn.execute_sql(tbl.ddl)
        print(f"    📦 已创建 {tbl.schema_name}.{tbl.table_name}")

    conn.close()


def _write_to_local(tbl: DDLEntry, df: pd.DataFrame):
    """分批写入本地 MySQL。"""
    conn = get_data(data_type="local")
    full_name = f"{tbl.schema_name}.{tbl.table_name}"

    # 清空旧数据
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
        values = []
        for _, row in batch.iterrows():
            vals = []
            for v in row:
                if pd.isna(v) or isinstance(v, (float, np.floating)) and (np.isnan(v) or np.isinf(v)):
                    vals.append(None)
                else:
                    vals.append(v.item() if hasattr(v, "item") else v)
            values.append(tuple(vals))

        try:
            cursor.executemany(sql, values)
            conn.conn.commit()
            written += len(batch)
        except Exception:
            conn.conn.rollback()
            # 逐行插入
            for vals in values:
                try:
                    cursor.execute(sql, vals)
                    conn.conn.commit()
                    written += 1
                except Exception:
                    conn.conn.rollback()

    cursor.close()
    conn.close()
    print(f"    💾 写入 {written:,}/{total:,} 行 → {full_name}")
