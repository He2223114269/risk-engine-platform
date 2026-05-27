"""套餐评级 - 一键运行"""

from __future__ import annotations
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional
from risk_engine.toolkit.connectors import get_data
from risk_engine.rating.package.extract import extract_all
from risk_engine.rating.package.score import score_all
from risk_engine.rating.package.rate import assign_ratings


def run_package_rating(
    data_date: Optional[str] = None,
    province: Optional[str] = None,
    lookback_months: int = 12,
    write_to_db: bool = True,
) -> pd.DataFrame:
    data_date = data_date or datetime.now().strftime("%Y-%m-%d")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始套餐评级")

    print(f"    1/3 提取基础数据...")
    df = extract_all(end_date=data_date, lookback_months=lookback_months, province=province)
    print(f"        → {len(df)} 个套餐")
    if df.empty:
        return df

    print(f"    2/3 评分 + 评级...")
    df = score_all(df)
    df = assign_ratings(df)
    cnts = df["package_rating"].value_counts()
    for r in ["A", "B", "C"]:
        c = cnts.get(r, 0)
        print(f"        {r}级: {c} 个 ({c/len(df)*100:.1f}%)")
    print(f"        评分: {df['compliance_score'].min()} ~ {df['compliance_score'].max()}")

    if write_to_db:
        _write(df, data_date)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 完成")
    return df


def _write(df: pd.DataFrame, data_date: str):
    cols = [
        "pack_name",
        "province",
        "total_transaction_count",
        "num_overdue_rate",
        "unsubscribe_rate",
        "risk_pass_rate",
        "active_months",
        "old_customer_count",
        "new_customer_count",
        "compliance_score",
        "package_rating",
    ]
    existing = [c for c in cols if c in df.columns]
    rec = df[existing].copy()
    rec["data_date"] = data_date

    conn = get_data(data_type="local")
    conn.execute_sql(f"DELETE FROM package_evaluation WHERE data_date = '{data_date}'")

    cursor = conn.conn.cursor()
    cs = list(rec.columns)
    ph = ",".join(["%s"] * len(cs))
    cq = ",".join([f"`{c}`" for c in cs])
    sql = f"INSERT INTO package_evaluation ({cq}) VALUES ({ph})"

    ok, err = 0, 0
    for _, row in rec.iterrows():
        vals = [
            None if pd.isna(v) or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))) else v
            for v in row
        ]
        try:
            cursor.execute(sql, tuple(vals))
            ok += 1
        except Exception as e:
            err += 1
            if err <= 3:
                print(f"    ⚠️ 失败 [{row.iloc[0]}]: {e}")
    conn.conn.commit()
    cursor.close()
    conn.close()
    print(f"    → 写入: {ok} 成功, {err} 失败")
