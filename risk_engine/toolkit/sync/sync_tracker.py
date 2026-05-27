"""
同步追踪表
==========

记录每次同步的状态，支持后续增量同步。
"""

from __future__ import annotations

import contextlib

from risk_engine.toolkit.connectors import get_data

TRACKER_TABLE = "sync_journal"


def ensure_tracker_table():
    """在本地库创建同步追踪表。"""
    conn = get_data(data_type="local")
    try:
        conn.get_data(f"SELECT 1 FROM {TRACKER_TABLE} LIMIT 1")
    except Exception:
        conn.execute_sql(f"""
            CREATE TABLE {TRACKER_TABLE} (
                table_name  VARCHAR(64) NOT NULL,
                sync_date   DATE NOT NULL,
                start_time  DATETIME NOT NULL,
                end_time    DATETIME,
                row_count   INT DEFAULT 0,
                status      VARCHAR(16) DEFAULT 'running',
                remark      TEXT,
                PRIMARY KEY (table_name, sync_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
    conn.close()


def start_sync(table_name: str, sync_date: str) -> bool:
    """记录同步开始。返回 False 表示该表今天已同步过（跳过）。"""
    ensure_tracker_table()
    conn = get_data(data_type="local")

    try:
        existing = conn.get_data(f"""
            SELECT status FROM {TRACKER_TABLE}
            WHERE table_name = '{table_name}' AND sync_date = '{sync_date}'
        """)
        if not existing.empty and existing.iloc[0, 0] == "success":
            conn.close()
            return False  # 已同步成功，跳过

        # 清除旧记录（如果有失败的）
        conn.execute_sql(f"""
            DELETE FROM {TRACKER_TABLE}
            WHERE table_name = '{table_name}' AND sync_date = '{sync_date}'
        """)

        conn.execute_sql(f"""
            INSERT INTO {TRACKER_TABLE} (table_name, sync_date, start_time, status)
            VALUES ('{table_name}', '{sync_date}', NOW(), 'running')
        """)
    except Exception:
        conn.close()
        return False

    conn.close()
    return True


def finish_sync(
    table_name: str, sync_date: str, row_count: int, status: str = "success", remark: str = ""
):
    """记录同步完成。"""
    conn = get_data(data_type="local")
    with contextlib.suppress(Exception):
        conn.execute_sql(f"""
            UPDATE {TRACKER_TABLE}
            SET end_time = NOW(), row_count = {row_count},
                status = '{status}', remark = '{remark}'
            WHERE table_name = '{table_name}' AND sync_date = '{sync_date}'
        """)
    conn.close()


def get_last_sync(table_name: str) -> str | None:
    """获取最近一次成功同步的日期。"""
    conn = get_data(data_type="local")
    try:
        df = conn.get_data(f"""
            SELECT MAX(sync_date) as last_date FROM {TRACKER_TABLE}
            WHERE table_name = '{table_name}' AND status = 'success'
        """)
        conn.close()
        if not df.empty and df.iloc[0, 0]:
            return str(df.iloc[0, 0])
    except Exception:
        pass
    conn.close()
    return None
