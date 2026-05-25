"""
套餐评级分析报告生成器
"""

from __future__ import annotations
import pandas as pd
from datetime import datetime
from pathlib import Path
from risk_engine.toolkit.connectors import get_data


def generate_report(data_date: str, output_path: str = None) -> str:
    if output_path is None:
        output_path = Path(__file__).parent / f"套餐评级分析报告_{data_date}.md"

    conn = get_data(data_type="local")
    df = conn.get_data(f"SELECT * FROM package_evaluation WHERE data_date='{data_date}'")
    conn.close()
    total = len(df)

    lines = []
    def w(t=""): lines.append(t)

    w("# 套餐评级分析报告")
    w(f"\n> 数据截止: {data_date} | 总套餐: **{total}** 个\n")

    w("## 一、总体概览\n")
    cross = df.groupby("package_rating").agg(
        数量=("pack_name","count"),
        平均评分=("compliance_score","mean"),
        平均逾期率=("num_overdue_rate","mean"),
        平均退订率=("unsubscribe_rate","mean"),
        平均办单量=("total_transaction_count","mean"),
    ).round(4)
    w("| 评级 | 数量 | 占比 | 平均分 | 逾期率 | 退订率 | 办单量 |")
    w("|:---:|:----:|:---:|:-----:|:-----:|:-----:|:-----:|")
    for r in ["A","B","C"]:
        if r in cross.index:
            x = cross.loc[r]
            w(f"| {r} | {int(x['数量'])} | {int(x['数量'])/total*100:.1f}% | {x['平均评分']:.0f} | {x['平均逾期率']*100:.2f}% | {x['平均退订率']*100:.2f}% | {x['平均办单量']:.0f} |")

    w("\n## 二、热门套餐 TOP 10\n")
    top = df.sort_values("total_transaction_count", ascending=False).head(10)
    w("| 套餐名称 | 评级 | 评分 | 逾期率 | 办单量 |")
    w("|:--------|:---:|:----:|:-----:|:-----:|")
    for _, r in top.iterrows():
        w(f"| {r['pack_name'][:40]} | {r['package_rating']} | {r['compliance_score']:.0f} | {r['num_overdue_rate']*100:.2f}% | {int(r['total_transaction_count'])} |")

    w("\n## 三、逾期率分段\n")
    df["逾期段"] = pd.cut(df["num_overdue_rate"], bins=[-1,0,0.02,0.05,0.10,1], labels=["0%","0~2%","2~5%","5~10%",">10%"])
    od = df.groupby("逾期段", observed=True).agg(数量=("pack_name","count"), 平均评分=("compliance_score","mean"))
    w("| 逾期率 | 数量 | 平均评分 |")
    w("|:-----:|:----:|:-------:|")
    for idx, r in od.iterrows():
        w(f"| {idx} | {int(r['数量'])} | {r['平均评分']:.1f} |")

    report = "\n".join(lines)
    Path(output_path).write_text(report, encoding="utf-8")
    print(f"报告已生成: {output_path}")
    return report


if __name__ == "__main__":
    import sys
    generate_report(sys.argv[1] if len(sys.argv) > 1 else "2026-05-25")
