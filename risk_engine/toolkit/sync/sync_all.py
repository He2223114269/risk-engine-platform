"""
一键同步脚本 — 从 StarRocks 同步数据到本地 MySQL
用法: python sync_all.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from risk_engine.toolkit.connectors import get_data
import pandas as pd
import numpy as np
from datetime import datetime

# ── 配置 ──
LOCAL_HOST = '172.31.80.1'
LOCAL_PORT = 3306
LOCAL_USER = 'root'
LOCAL_PASS = '222311'
LOCAL_DB = 'risk_control'
BATCH_SIZE = 10000

# ── 表清单： (本地表名, StarRocks SQL 取数语句, 是否分页) ──
TABLES = [
    ("ods_ods_ts_v3_order_store",
     "SELECT * FROM ods.ods_ts_v3_order_store",
     15843, False),
    ("ods_ods_ts_order_white_list_control",
     "SELECT * FROM ods.ods_ts_order_white_list_control WHERE type = '淘顺实时授信'",
     928107, True),
    ("ods_ods_ts_credit_yzf_order_grant_apply",
     "SELECT * FROM ods.ods_ts_credit_yzf_order_grant_apply WHERE business_type = '02'",
     2310465, True),
    ("dws_dws_credit_yzf_order_complete",
     "SELECT * FROM dws.dws_credit_yzf_order_complete WHERE source_business_type = '淘顺实时授信'",
     1393089, True),
    ("ods_ods_ts_credit_yzf_order_info_complete",
     "SELECT * FROM ods.ods_ts_credit_yzf_order_info_complete",
     1515653, True),
    ("ods_ods_ts_credit_yzf_order_repayment",
     "SELECT * FROM ods.ods_ts_credit_yzf_order_repayment",
     50530527, True),
]

def sync():
    sr = get_data(data_type='risk')
    local_conn = __import__('pymysql').connect(host=LOCAL_HOST, port=LOCAL_PORT, user=LOCAL_USER, password=LOCAL_PASS, database=LOCAL_DB)
    cur = local_conn.cursor()

    for local_name, select_sql, est_rows, paginate in TABLES:
        print(f"\n{'='*50}")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {local_name} (~{est_rows:,} 行)")

        # 获取列名
        cols_df = sr.get_data(f"{select_sql} LIMIT 0")
        # Fallback: 用 DESCRIBE
        if cols_df.empty or len(cols_df.columns) == 0:
            cols_df = sr.get_data(f"DESCRIBE {select_sql.split('FROM ')[-1]}")
            cols = cols_df.iloc[:,0].tolist()
        else:
            cols = list(cols_df.columns)

        if not cols:
            print(f"  ❌ 无法获取字段列表")
            continue

        print(f"  字段数: {len(cols)}")

        # 建表（全 TEXT 简化）
        col_defs = ",\n    ".join([f"`{c}` TEXT" for c in cols])
        cur.execute(f"DROP TABLE IF EXISTS `{local_name}`")
        cur.execute(f"CREATE TABLE `{local_name}` ({col_defs}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")
        local_conn.commit()
        print(f"  ✅ 本地表已创建")

        # 分批取数+写入
        total = 0
        offset = 0

        while True:
            sql = f"{select_sql} LIMIT {BATCH_SIZE} OFFSET {offset}"
            batch = sr.get_data(sql)
            if batch.empty:
                break

            total += len(batch)
            # 打印进度（只打大的批次）
            if total % 50000 == 0 or not paginate:
                print(f"  {datetime.now().strftime('%H:%M:%S')} {total:,} 行...", end="\r")

            ph = ",".join(["%s"] * len(cols))
            cq = ",".join([f"`{c}`" for c in cols])
            ins = f"INSERT INTO `{local_name}` ({cq}) VALUES ({ph})"

            for _, row in batch.iterrows():
                vals = [str(v) if pd.notna(v) else None for v in row]
                try:
                    cur.execute(ins, tuple(vals))
                except:
                    pass
            local_conn.commit()

            if not paginate:
                break
            offset += BATCH_SIZE

        print(f"  ✅ {local_name}: {total:,} 行{' ' * 20}")

    cur.close()
    local_conn.close()
    sr.close()
    print(f"\n{'='*50}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 全部同步完成")

if __name__ == '__main__':
    sync()
