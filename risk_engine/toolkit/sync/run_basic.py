"""同步基础表到本地 MySQL（按层分库）

ODS 层表 → ods 库
DWS 层表 → dws 库
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import contextlib
from datetime import datetime

import pandas as pd
import pymysql

from risk_engine.toolkit.connectors import get_data

sr = get_data(data_type="risk")
# 不指定 database，后续用 db.table 全限定名
lc = pymysql.connect(
    host="172.31.80.1", port=3306, user="root", password="222311", charset="utf8mb4"
)
cur = lc.cursor()
B = 10000


def create_table(cursor, db_name, table_name, columns):
    col_defs = []
    for c in columns:
        col_defs.append("`" + c + "` TEXT")
    full_name = "`" + db_name + "`.`" + table_name + "`"
    sql = (
        "CREATE TABLE " + full_name + " ("
        + ",".join(col_defs)
        + ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
    )
    cursor.execute("DROP TABLE IF EXISTS " + full_name)
    cursor.execute(sql)


def sync_table(db_name, local_name, select_sql):
    total = 0
    offset = 0
    full_name = "`" + db_name + "`.`" + local_name + "`"
    print("[" + datetime.now().strftime("%H:%M") + "] " + db_name + "." + local_name)

    batch = sr.get_data(select_sql + " LIMIT 1")
    if batch.empty:
        print("  无数据")
        return 0
    cols = list(batch.columns)
    create_table(cur, db_name, local_name, cols)
    lc.commit()

    cq = ",".join(["`" + c + "`" for c in cols])
    ph = ",".join(["%s"] * len(cols))
    ins = "INSERT INTO " + full_name + " (" + cq + ") VALUES (" + ph + ")"

    while True:
        batch = sr.get_data(select_sql + " LIMIT " + str(B) + " OFFSET " + str(offset))
        if batch.empty:
            break
        total += len(batch)
        for _, row in batch.iterrows():
            vals = [str(v) if pd.notna(v) else None for v in row]
            with contextlib.suppress(BaseException):
                cur.execute(ins, tuple(vals))
        lc.commit()
        offset += B
        if offset % 50000 == 0:
            print("  " + str(total) + " 行...")

    print("  " + db_name + "." + local_name + ": " + str(total) + " 行")
    return total


# ── ODS 层 → ods 库 ──
sync_table("ods", "ods_ts_v3_order_store", "SELECT * FROM ods.ods_ts_v3_order_store")
sync_table(
    "ods",
    "ods_ts_order_white_list_control",
    "SELECT * FROM ods.ods_ts_order_white_list_control WHERE type = '淘顺实时授信'",
)
sync_table(
    "ods",
    "ods_ts_credit_yzf_order_grant_apply",
    "SELECT * FROM ods.ods_ts_credit_yzf_order_grant_apply WHERE business_type = '02'",
)

# ── DWS 层 → dws 库 ──
sync_table(
    "dws",
    "dws_credit_yzf_order_complete",
    "SELECT * FROM dws.dws_credit_yzf_order_complete WHERE source_business_type = '淘顺实时授信'",
)

cur.close()
lc.close()
sr.close()
print("\n✅ 同步完成")
