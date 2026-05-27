# -*- coding: utf-8 -*-
"""同步三张基础表到本地 MySQL"""

import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from risk_engine.toolkit.connectors import get_data
import pandas as pd
import numpy as np
import pymysql
from datetime import datetime

sr = get_data(data_type="risk")
lc = pymysql.connect(
    host="172.31.80.1", port=3306, user="root", password="222311", database="risk_control"
)
cur = lc.cursor()
B = 10000


def create_table(cursor, table_name, columns):
    col_defs = []
    for c in columns:
        col_defs.append("`" + c + "` TEXT")
    sql = (
        "CREATE TABLE `"
        + table_name
        + "` ("
        + ",".join(col_defs)
        + ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
    )
    cursor.execute("DROP TABLE IF EXISTS `" + table_name + "`")
    cursor.execute(sql)


def sync_table(local_name, select_sql):
    total = 0
    offset = 0
    print("[" + datetime.now().strftime("%H:%M") + "] " + local_name)

    # 取一行获取字段
    batch = sr.get_data(select_sql + " LIMIT 1")
    if batch.empty:
        print("  无数据")
        return 0
    cols = list(batch.columns)
    create_table(cur, local_name, cols)
    lc.commit()

    cq = ",".join(["`" + c + "`" for c in cols])
    ph = ",".join(["%s"] * len(cols))
    ins = "INSERT INTO `" + local_name + "` (" + cq + ") VALUES (" + ph + ")"

    while True:
        batch = sr.get_data(select_sql + " LIMIT " + str(B) + " OFFSET " + str(offset))
        if batch.empty:
            break
        total += len(batch)
        for _, row in batch.iterrows():
            vals = [str(v) if pd.notna(v) else None for v in row]
            try:
                cur.execute(ins, tuple(vals))
            except:
                pass
        lc.commit()
        offset += B
        if offset % 50000 == 0:
            print("  " + str(total) + " 行...")

    print("  " + local_name + ": " + str(total) + " 行")
    return total


# 1. v3_store（全量）
sync_table("ods_ods_ts_v3_order_store", "SELECT * FROM ods.ods_ts_v3_order_store")

# 2. 风控结果表
sync_table(
    "ods_ods_ts_order_white_list_control",
    "SELECT * FROM ods.ods_ts_order_white_list_control WHERE type = '淘顺实时授信'",
)

# 3. 申请表
sync_table(
    "ods_ods_ts_credit_yzf_order_grant_apply",
    "SELECT * FROM ods.ods_ts_credit_yzf_order_grant_apply WHERE business_type = '02'",
)

cur.close()
lc.close()
sr.close()
print("\n✅ 三张表同步完成")
