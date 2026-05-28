#!/usr/bin/env python3
"""
仿真调试脚本 — v3 含拒绝推断
=====================================================

三步对比 + 灵敏度分析 + 报告持久化

用法：
  1. 在 PyCharm 里打开本文件，改配置区，Run
  2. 结果自动打印 + 保存到 data/simulations/ 下
"""

from __future__ import annotations
import os, sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # risk_engine 的上级
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
os.chdir(str(_PROJECT_ROOT))

# ── 配置区 ──────────────────────────────────────────────
# 默认使用浙江代理测试配置
# 可以在 config/zhejiang_proxy.py 中修改，或直接改这里
try:
    from risk_engine.simulation.config.zhejiang_proxy import CONFIG as _cfg
    PROVINCE = _cfg.get("province", "全国")          # 数据源省份
    CONFIG_PROVINCE = _cfg.get("config_province", "浙江省")  # 通过率配置省份
    DATA_DATE = _cfg.get("data_date", "2026-05-01")
    DATA_START = _cfg.get("data_start", "2026-01-01")
    TREE_VERSION = _cfg.get("tree_version", "jiangxi_v1")
    ENABLE_OPTIMIZE = True
    TARGET_PASS_RATE = _cfg.get("target_pass_rate", 0.40)
    print(f"  📋 加载配置: {_cfg.get('description', '')}")
except ImportError:
    PROVINCE = "全国"
    CONFIG_PROVINCE = "浙江省"
    DATA_DATE = "2026-05-01"
    DATA_START = "2026-01-01"
    TREE_VERSION = "jiangxi_v1"
    ENABLE_OPTIMIZE = True
    TARGET_PASS_RATE = 0.40
# ────────────────────────────────────────────────────────

# ── 省份过滤 SQL 条件 ──
if PROVINCE == "全国":
    _prov_where = ""
    _prov_where_dws = ""
    _prov_where_lxf = ""
    _province_label = "全国"
else:
    _prov_where = f" AND store_addr_province='{PROVINCE}'"
    _prov_where_dws = f" AND province='{PROVINCE}'"
    _prov_where_lxf = f" AND province='{PROVINCE}'"
    _province_label = PROVINCE
# ────────────────────────────────────────────────────────

CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "cache"  # project root/data/cache
CACHE_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "simulations"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

from risk_engine.toolkit.connectors import get_data
from risk_engine.simulation.estimator import load_branch_pass_ratios
from risk_engine.model_registry import load as load_model


# ═══════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════
def get_lxf_bin(s):
    if pd.isna(s): return "无分"
    if s <= 0: return "0-50"
    elif s <= 50: return "0-50"
    elif s <= 100: return "50-100"
    elif s <= 200: return "100-200"
    elif s <= 300: return "200-300"
    elif s <= 400: return "300-400"
    elif s <= 500: return "400-500"
    elif s <= 600: return "500-600"
    elif s <= 700: return "600-700"
    elif s <= 800: return "700-800"
    else: return "800+"


def save_report(content: str, name: str):
    """保存报告到 data/simulations/"""
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    fname = f"{name}_{ts}.md"
    path = REPORT_DIR / fname
    path.write_text(content, encoding="utf-8")
    print(f"\n  📝 报告已保存: {path}")
    return path


# ═══════════════════════════════════════
# 第一步：读取配置通过率
# ═══════════════════════════════════════
model = load_model(TREE_VERSION)
BRANCH_PASS_RATIOS = load_branch_pass_ratios(CONFIG_PROVINCE, model=model)
print(f"共 {len(BRANCH_PASS_RATIOS)} 个分支")

# ═══════════════════════════════════════
# 第二步：拉数据
# ═══════════════════════════════════════
cache_raw = CACHE_DIR / f"raw_{PROVINCE}_{DATA_DATE}_{DATA_START}.parquet"

if cache_raw.exists():
    print("  ✅ 使用缓存")
    data = pd.read_parquet(cache_raw)
else:
    print("  🚀 拉取数据...")
    conn = get_data(data_type="risk")

    # 1. 申请表
    apply_sql = f"""
    SELECT Decrypt(user_name_enc) AS user_name, Decrypt(id_number_enc) AS id_number,
           order_amt, store_addr_province AS province, Decrypt(mobile_no_enc) AS mobile_no,
           pack_name, goods_type, apply_status,
           row_number() OVER (PARTITION BY user_name_enc,id_number_enc
               ORDER BY CASE WHEN apply_status='授信成功' THEN 0 ELSE 1 END) AS rt
    FROM ods.ods_ts_credit_yzf_order_grant_apply
    WHERE custtype='00'{_prov_where}
      AND add_time>='{DATA_START}' AND add_time<'{DATA_DATE}'
    """
    apply_data = conn.get_data(apply_sql)
    apply_data = apply_data[apply_data["rt"]==1].copy()

    # 2. DWS 逾期
    dws_sql = f"""
    SELECT decrypt(id_card_no) AS id_no, decrypt(id_card_name) AS id_name,
           order_amt_yuan,
           CASE WHEN total_due_count-total_repaid_count>=1 THEN 1 ELSE 0 END AS is_over_due
    FROM dws.dws_credit_yzf_order_complete
    WHERE source_business_type='淘顺实时授信'{_prov_where_dws} AND custtype='00'
      AND complete_time>='{DATA_START}' AND complete_time<'{DATA_DATE}'
    """
    dws_data = conn.get_data(dws_sql)
    dws_data = dws_data.drop_duplicates(subset=["id_no"], keep="first")

    # 3. 灵犀分
    lxf_sql = f"""
    SELECT * FROM (
        SELECT Decrypt(user_name_enc) AS user_name, Decrypt(id_card_enc) AS id_card, lxf,
               ROW_NUMBER() OVER (PARTITION BY user_name_enc,id_card_enc
                   ORDER BY CASE WHEN second_risk_result='通过' THEN 0 ELSE 1 END, lxf DESC) AS rn
        FROM ods.ods_ts_order_white_list_control
        WHERE type='淘顺实时授信'{_prov_where_lxf}
    ) t WHERE rn=1
    """
    lxf_data = conn.get_data(lxf_sql)

    # 4. 在网数据（用 SQL LEFT JOIN 而不是 injoin_data，避免类型问题）
    mobile_list = apply_data["mobile_no"].dropna().unique().tolist()
    if mobile_list:
        onlines = []
        chunk_size = 500
        for i in range(0, len(mobile_list), chunk_size):
            chunk = mobile_list[i:i+chunk_size]
            quoted = "','".join(chunk)
            sql = f"""
            SELECT telephone, CASE WHEN operator_real='3' THEN 1 ELSE 0 END AS is_bw, onlinetime
            FROM ods.ods_bl_wind_tel_onlinetime
            WHERE business_type='淘顺翼支付实时授信' AND telephone IN ('{quoted}')
            """
            onlines.append(conn.get_data(sql))
        online_data = pd.concat(onlines).drop_duplicates(subset=["telephone"], keep="first")
    else:
        online_data = pd.DataFrame()

    conn.close()

    # 5. 合并
    data = apply_data.merge(dws_data, left_on=["id_number","user_name"],
                            right_on=["id_no","id_name"], how="left")
    data = data.merge(lxf_data, left_on=["id_number","user_name"],
                      right_on=["id_card","user_name"], how="left")
    data = data.merge(online_data, left_on="mobile_no", right_on="telephone", how="left")
    data = data.drop_duplicates(subset=["id_number"], keep="first")

    data["lxf"] = pd.to_numeric(data["lxf"], errors="coerce")
    data["is_over_due"] = pd.to_numeric(data["is_over_due"], errors="coerce").fillna(-1).astype(int)
    data.to_parquet(cache_raw)
    print(f"  ✅ 已缓存: {cache_raw}")

# ═══════════════════════════════════════
# 第三步：特征工程 + 决策树分类
# ═══════════════════════════════════════
amt_s = pd.to_numeric(data["order_amt"], errors="coerce").fillna(0)
data["amt_interval"] = pd.cut(amt_s/100, [0,1000,1500,2000,2500,3000,float("inf")], labels=[1,2,3,4,5,6])
def _age(s):
    try:
        b=datetime.strptime(str(s)[6:14],"%Y%m%d"); t=datetime.today()
        return t.year-b.year-((t.month,t.day)<(b.month,b.day))
    except: return None
data["age"]=data["id_number"].apply(_age)
data["age_interval"]=pd.cut(data["age"],[20,25,30,35,40,45,50,55,60,65],labels=[1,2,3,4,5,6,7,8,9])
data["is_bw"]=pd.to_numeric(data["is_bw"],errors="coerce").fillna(0).astype(float)
data["onlinetime"]=pd.to_numeric(data["onlinetime"],errors="coerce").fillna(-1).astype(float)
data["province_is_one"]=data["id_number"].apply(lambda x:1 if {"36":"江西省"}.get(str(x)[:2],"")==PROVINCE else 0)
data["gender"]=np.where(data["id_number"].astype(str).str[16].astype(float,errors="ignore")%2==1,1,0)

model = load_model(TREE_VERSION)
data = model.classify_batch(data)
data["class"] = data["strategy_type"]

data_with_lxf = data[data["lxf"].notna()].copy()
data_with_lxf["has_overdue_data"] = data_with_lxf["is_over_due"] >= 0
print(f"  有灵犀分样本: {len(data_with_lxf):,}")

# ═══════════════════════════════════════
# 第四步：实际现状
# ═══════════════════════════════════════
actual_stats = data_with_lxf.groupby("class").agg(
    apply_count=("apply_status","count"),
    pass_count=("apply_status",lambda x:(x=="授信成功").sum()),
).reset_index()
actual_stats["pass_rate"] = actual_stats["pass_count"]/actual_stats["apply_count"]

overdue_stats = data_with_lxf[data_with_lxf["has_overdue_data"]].groupby("class").agg(
    sample_count=("is_over_due","count"),
    over_count=("is_over_due","sum"),
).reset_index()
overdue_stats["overdue_rate"] = overdue_stats["over_count"]/overdue_stats["sample_count"]
actual_full = actual_stats.merge(overdue_stats, on="class", how="left")

# ═══════════════════════════════════════
# 第五步：拒绝推断 + 模拟
# ═══════════════════════════════════════
print("  建立 LXF-逾期率 映射表...")
lxf_bin_map = {}
for branch in data_with_lxf["class"].unique():
    bd = data_with_lxf[(data_with_lxf["class"]==branch)&data_with_lxf["has_overdue_data"]]
    if len(bd)<10:
        lxf_bin_map[branch] = {"_default_": bd["is_over_due"].mean() if len(bd)>0 else None}
        continue
    bd["lxf_bin"] = bd["lxf"].apply(get_lxf_bin)
    bin_rates = bd.groupby("lxf_bin")["is_over_due"].agg(["count","mean"]).to_dict("index")
    bin_rates = {k:v["mean"] for k,v in bin_rates.items() if v["count"]>=3}
    bin_rates["_default_"] = bd["is_over_due"].mean()
    lxf_bin_map[branch] = bin_rates

# 灵敏度分析的微调步长表
SENSITIVITY_STEPS = [0.05, 0.10, 0.15, 0.20]  # 在当前通过率基础上降低 5pp/10pp/15pp/20pp

sim_rows = []
sens_data = []  # 灵敏度分析数据
for strategy, pass_ratio in BRANCH_PASS_RATIOS.items():
    bd = data_with_lxf[data_with_lxf["class"]==strategy].copy()
    if len(bd)==0: continue
    bd = bd.sort_values("lxf", ascending=False)

    total = len(bd)
    n_pass = max(1, int(total * pass_ratio))
    sampled = bd.head(n_pass)
    pass_adjust = len(sampled)
    pass_rate_adjust = pass_adjust / total

    actual_passed = sampled[sampled["apply_status"]=="授信成功"]
    newly_passed = sampled[sampled["apply_status"]!="授信成功"]

    actual_with_data = actual_passed[actual_passed["has_overdue_data"]]
    actual_overdue_count = int(actual_with_data["is_over_due"].sum())
    actual_overdue_base = actual_with_data["is_over_due"].count()

    bin_map = lxf_bin_map.get(strategy, {"_default_":None})
    newly_overdue_estimated = sum(
        bin_map.get(get_lxf_bin(r["lxf"]), bin_map.get("_default_",0)) or 0
        for _,r in newly_passed.iterrows()
    )
    newly_total = len(newly_passed)
    newly_overdue_estimated_rate = newly_overdue_estimated/newly_total if newly_total>0 else 0

    total_overdue_est = actual_overdue_count + newly_overdue_estimated
    total_valid = actual_overdue_base + newly_total
    overdue_rate_combined = total_overdue_est/total_valid if total_valid>0 else 0
    actual_overdue = actual_overdue_count/actual_overdue_base if actual_overdue_base>0 else 0
    overdue_change = overdue_rate_combined - actual_overdue
    pass_change = pass_adjust - actual_stats.loc[actual_stats["class"]==strategy,"pass_count"].values[0]

    sim_rows.append({
        "strategy": strategy,
        "配置通过率": pass_ratio,
        "模拟通过率": pass_rate_adjust,
        "模拟通过数": pass_adjust,
        "实际通过数(对比)": actual_stats.loc[actual_stats["class"]==strategy,"pass_count"].values[0],
        "实际逾期数": actual_overdue_count,
        "实际逾期基数": actual_overdue_base,
        "实际逾期率": actual_overdue,
        "拒绝推断人数": newly_total,
        "拒绝推断逾期率": newly_overdue_estimated_rate,
        "拒绝推断逾期数(估计)": round(newly_overdue_estimated,1),
        "综合调整逾期率": overdue_rate_combined,
        "逾期率变化": overdue_change,
        "通过数变化": pass_change,
        "平均LXF": round(pd.to_numeric(sampled["lxf"],errors="coerce").mean(),1),
        "总样本": total,
    })

    # ── 灵敏度分析：降低通过率看效果 ──
    if actual_overdue > 0.05:
        steps = []
        for step in SENSITIVITY_STEPS:
            new_ratio = max(0.01, pass_ratio - step)
            if new_ratio >= pass_ratio: continue
            n2 = max(1, int(total * new_ratio))
            s2 = bd.head(n2)
            a2 = s2[s2["apply_status"]=="授信成功"]
            n2_new = s2[s2["apply_status"]!="授信成功"]
            a2_over = int(a2[a2["has_overdue_data"]]["is_over_due"].sum())
            a2_base = a2[a2["has_overdue_data"]]["is_over_due"].count()
            n2_est = sum(bin_map.get(get_lxf_bin(r["lxf"]),bin_map.get("_default_",0)) or 0 for _,r in n2_new.iterrows())
            c_rate = (a2_over+n2_est)/(a2_base+len(n2_new)) if (a2_base+len(n2_new))>0 else 0
            steps.append({"step_ratio": new_ratio, "overdue": c_rate, "pass_c": len(s2),
                          "overdue_change": c_rate-actual_overdue, "pass_change": len(s2)-pass_adjust})
        if steps:
            sens_data.append({"strategy": strategy, "pass_ratio": pass_ratio,
                              "actual_overdue": actual_overdue, "steps": steps})

sim_df = pd.DataFrame(sim_rows)

# ═══════════════════════════════════════
# 第六步：输出
# ═══════════════════════════════════════
t_apply = actual_full["apply_count"].sum()
t_pass = actual_full["pass_count"].sum()
t_sample = actual_full["sample_count"].sum()
t_over = actual_full["over_count"].sum()
total_actual_pass = actual_full["pass_count"].sum()
total_sim_pass = sim_df["模拟通过数"].sum()
total_newly = sim_df["拒绝推断人数"].sum()
total_newly_est = sim_df["拒绝推断逾期数(估计)"].sum()
total_actual_over_for_sim = sim_df["实际逾期数"].sum()
total_actual_base_for_sim = sim_df["实际逾期基数"].sum()
combined_overdue = (total_actual_over_for_sim+total_newly_est)/(total_actual_base_for_sim+total_newly)
total_pass_change = total_sim_pass - total_actual_pass
actual_overall_overdue = t_over/t_sample

lines = []
def pl(s=""):
    lines.append(s)
    print(s)

def _mark(v, tiers):
    """给数值打标记"""
    for threshold, mark in tiers:
        if v >= threshold: return mark
    return ""

def _fmt_row(branch, *cols, sep="  "):
    return f"  {branch:>28}{sep}{sep.join(cols)}"

# ── 一、实际现状 ──
pl("─"*90)
pl(f"  一、实际现状 ｜ {_province_label} {DATA_START}~{DATA_DATE} ｜ 总申请 {t_apply:,} ｜ 总逾期 {t_over:,}（{t_over/t_sample*100:.2f}%）")
pl("─"*90)
# 分本网/异网
for net_type in ["本网", "异网"]:
    prefix = "bw" if net_type == "本网" else "yw"
    subset = actual_full[actual_full["class"].str.startswith(prefix)].sort_values("overdue_rate", ascending=False)
    if subset.empty: continue
    pl(f"\n  ▼ {net_type}")
    for _, r in subset.iterrows():
        overdue = r["overdue_rate"] * 100
        mark = _mark(overdue, [(20,"🔴"),(15,"🟠"),(10,"🟡"),(0,"  ")])
        pass_txt = f"{int(r['pass_count']):,}/{int(r['apply_count']):,}（{r['pass_rate']*100:.0f}%）"
        overdue_txt = f"{int(r['over_count']):,}/{int(r['sample_count']):,}（{overdue:.1f}%）"
        pl(f"    {r['class']:>28} {mark} 通过: {pass_txt:<20} 逾期: {overdue_txt}")
pl(f"\n  {'─'*60}")
pl(f"    整体 ｜ 通过率 {t_pass/t_apply*100:.1f}%｜逾期率 {t_over/t_sample*100:.2f}%｜样本 {t_sample:,}")
# ── 二、模拟后 ──
pl("─"*90)
pl(f"  二、模拟后 ｜ 按配置通过率 + 拒绝推断｜ 模拟通过率 {total_sim_pass/t_apply*100:.1f}%｜综合逾期率 {combined_overdue*100:.2f}%")
pl("─"*90)
for net_type in ["本网", "异网"]:
    prefix = "bw" if net_type == "本网" else "yw"
    subset = sim_df[sim_df["strategy"].str.startswith(prefix)].sort_values("综合调整逾期率", ascending=False)
    if subset.empty: continue
    pl(f"\n  ▼ {net_type}")
    for _, r in subset.iterrows():
        rl = r["综合调整逾期率"] * 100
        mark = _mark(rl, [(20,"🔴"),(15,"🟠"),(10,"🟡"),(0,"  ")])
        cp = r["配置通过率"] * 100
        chg = r["逾期率变化"] * 100
        chg_str = f"{chg:+.1f}" if abs(chg) >= 0.05 else "≈0"
        pc = int(r["通过数变化"])
        ni = int(r["拒绝推断人数"])
        pl(f"    {r['strategy']:>28} {mark} 过率{cp:.0f}%→逾期{rl:.1f}%({chg_str}pp) 通过{pc:+d} 推断{ni}")

pl(f"\n  {'─'*60}")
pl(f"    整体 ｜ 通过率 {total_sim_pass/t_apply*100:.1f}%｜逾期率 {combined_overdue*100:.2f}%｜推断 {total_newly:,} 人｜变化 {total_pass_change:+d}")
pl()

# ── 三、灵敏度分析 ──
pl("─"*90)
pl("三、灵敏度 ｜ 高风险分支逐步收紧通过率的效果")
pl("─"*90)
found_sens = False
for sd in sens_data:
    if sd["steps"]:
        found_sens = True
        pl(f"\n  ▶ {sd['strategy']}（当前 {sd['pass_ratio']*100:.0f}%→逾期 {sd['actual_overdue']*100:.1f}%）")
        for st in sd["steps"]:
            chg = st['overdue_change'] * 100
            pl(f"    {st['step_ratio']*100:>5.0f}% → 逾期 {st['overdue']*100:.1f}%({chg:+.1f}pp) 通过 {st['pass_c']:,}({st['pass_change']:+d})")
        best = min(sd["steps"], key=lambda x: abs(x["overdue"]-0.05))
        if best["overdue"] < sd["actual_overdue"]:
            pl(f"    💡 建议 {best['step_ratio']*100:.0f}%（逾期 {best['overdue']*100:.1f}%，通过 {best['pass_change']:+d}）")
if not found_sens:
    pl("  所有逾期率均在 5% 以下，无需调整")
pl()

# ── 四、变化总结 ──
pl("─"*50)
pl("四、变化总结")
pl("─"*50)
pl(f"  {'':>20} │ {'实际':>8} │ {'模拟后':>8} │ {'变化':>8}")
pl(f"  {'─'*48}")
pl(f"  {'通过率':>20} │ {t_pass/t_apply*100:>7.1f}% │ {total_sim_pass/t_apply*100:>7.1f}% │ {(total_sim_pass-t_pass)/t_apply*100:+>7.1f}pp")
pl(f"  {'逾期率':>20} │ {actual_overall_overdue*100:>7.2f}% │ {combined_overdue*100:>7.2f}% │ {(combined_overdue-actual_overall_overdue)*100:+>7.2f}pp")
pl(f"  {'通过数':>20} │ {t_pass:>8,} │ {total_sim_pass:>8,} │ {total_pass_change:+>7,}")
pl(f"  {'拒绝推断(新通过无表现)':>20} │ {'':>8} │ {total_newly:>8,} │ {'':>8}")
pl()

# 预警
high_risk = sim_df[sim_df["综合调整逾期率"] > 0.15][["strategy","综合调整逾期率","通过数变化","拒绝推断人数"]]
if not high_risk.empty:
    pl(f"  ⚠️ 高风险分支（逾期率>15%）：")
    for _, r in high_risk.iterrows():
        pl(f"    {r['strategy']} 逾期{r['综合调整逾期率']*100:.1f}% 通过{int(r['通过数变化']):+d} 推断{int(r['拒绝推断人数'])}人")
    pl()

# ═══════════════════════════════════════
# 五、最优配置搜索
# ═══════════════════════════════════════
if ENABLE_OPTIMIZE and len(data_with_lxf) > 0:
    pl("\n" + "═"*90)
    pl("五、最优配置搜索 — 按风险排序分配通过率")
    pl(f"  策略：好客群多放，差客群收紧 → 目标整体通过率 {TARGET_PASS_RATE*100:.0f}%")
    pl("═"*90)

    # 1. 按分支逾期率排序（低→高 = 好→差）
    branch_risk = sim_df[["strategy","综合调整逾期率","总样本","配置通过率"]].copy()
    branch_risk = branch_risk.sort_values("综合调整逾期率").reset_index(drop=True)
    n_branches = len(branch_risk)

    # 2. 按风险分配通过率：最优95% → 最差5%，按排名线性插值
    #    然后再统一缩放至目标通过率
    best_ratio = 0.95  # 最优分支最高通过率
    worst_ratio = 0.05  # 最差分支最低通过率
    raw_ratios = np.linspace(best_ratio, worst_ratio, n_branches)
    for i, (_, r) in enumerate(branch_risk.iterrows()):
        branch_risk.at[r.name, "分配通过率"] = raw_ratios[i]

    # 3. 计算每条分支在分配通过率下的预期逾期率
    opt_rows = []
    for _, r in branch_risk.iterrows():
        strategy = r["strategy"]
        target_r = r["分配通过率"]
        bd = data_with_lxf[data_with_lxf["class"]==strategy].sort_values("lxf", ascending=False)
        if len(bd) == 0: continue

        n_p = max(1, int(len(bd) * target_r))
        sampled = bd.head(n_p)
        a_p = sampled[sampled["apply_status"]=="授信成功"]
        n_p_new = sampled[sampled["apply_status"]!="授信成功"]
        a_o = int(a_p[a_p["has_overdue_data"]]["is_over_due"].sum())
        a_b = a_p[a_p["has_overdue_data"]]["is_over_due"].count()
        bin_m = lxf_bin_map.get(strategy, {"_default_": None})
        n_e = sum(bin_m.get(get_lxf_bin(rr["lxf"]), bin_m.get("_default_",0)) or 0 for _, rr in n_p_new.iterrows())
        o_r = (a_o + n_e) / (a_b + len(n_p_new)) if (a_b + len(n_p_new)) > 0 else 0

        cur_r_row = sim_df[sim_df["strategy"]==strategy]
        cur_r = cur_r_row["配置通过率"].values[0] if not cur_r_row.empty else 0
        cur_o = cur_r_row["综合调整逾期率"].values[0] if not cur_r_row.empty else 0

        opt_rows.append({
            "strategy": strategy,
            "风险排名": len(opt_rows) + 1,
            "当前通过率": cur_r,
            "分配通过率": target_r,
            "当前逾期率": cur_o,
            "预期逾期率": o_r,
            "通过数": len(sampled),
            "拒绝推断": len(n_p_new),
        })

    opt_df = pd.DataFrame(opt_rows)

    # 4. 缩放至目标通过率
    current_total_pass = opt_df["通过数"].sum()
    target_total = int(TARGET_PASS_RATE * data_with_lxf["class"].count())
    if current_total_pass > 0 and current_total_pass != target_total:
        scale = target_total / current_total_pass
        opt_df["分配通过率"] = (opt_df["分配通过率"] * scale).clip(0.01, 0.99)
        opt_df["通过数"] = (opt_df["通过数"] * scale).astype(int)
        # 重新计算预期逾期率
        for idx, row in opt_df.iterrows():
            bd = data_with_lxf[data_with_lxf["class"]==row["strategy"]].sort_values("lxf", ascending=False)
            n_p = max(1, int(len(bd) * row["分配通过率"]))
            sampled = bd.head(n_p)
            a_p = sampled[sampled["apply_status"]=="授信成功"]
            n_p_new = sampled[sampled["apply_status"]!="授信成功"]
            a_o = int(a_p[a_p["has_overdue_data"]]["is_over_due"].sum())
            a_b = a_p[a_p["has_overdue_data"]]["is_over_due"].count()
            bin_m = lxf_bin_map.get(row["strategy"], {"_default_": None})
            n_e = sum(bin_m.get(get_lxf_bin(rr["lxf"]), bin_m.get("_default_",0)) or 0 for _, rr in n_p_new.iterrows())
            opt_df.at[idx, "预期逾期率"] = (a_o + n_e) / (a_b + len(n_p_new)) if (a_b + len(n_p_new)) > 0 else 0
            opt_df.at[idx, "拒绝推断"] = len(n_p_new)

    # 5. 输出
    opt_df = opt_df.sort_values("风险排名")

    pl(f"\n  分支排序｜逾期率越低=越优质→分配越高通过率")
    pl(f"  {'─'*90}")
    for net_type in ["本网", "异网"]:
        prefix = "bw" if net_type == "本网" else "yw"
        subset = opt_df[opt_df["strategy"].str.startswith(prefix)]
        if subset.empty: continue
        pl(f"\n  ▼ {net_type}")
        for _, r in subset.iterrows():
            cur_ov = r["当前逾期率"] * 100
            new_ov = r["预期逾期率"] * 100
            cur_r_val = r["当前通过率"] * 100
            new_r_val = r["分配通过率"] * 100
            dir_mark = "↑ 放量" if new_r_val > cur_r_val + 2 else ("↓ 收紧" if new_r_val < cur_r_val - 2 else "→ 微调")
            ov_flag = _mark(new_ov, [(15,"🔴"),(10,"🟠"),(5,"  "),(0,"✅")])
            pl(f"    #{r['风险排名']:>2} {r['strategy']:>26} {ov_flag} 排名{r['风险排名']} | "
               f"通过率 {cur_r_val:.0f}%→{new_r_val:.0f}% {dir_mark} | "
               f"逾期 {cur_ov:.1f}%→{new_ov:.1f}%")

    # 对比
    total_opt_pass = opt_df["通过数"].sum()
    total_opt_newly = opt_df["拒绝推断"].sum()
    opt_overall = sum(r["预期逾期率"]*r["通过数"] for _,r in opt_df.iterrows()) / total_opt_pass if total_opt_pass > 0 else 0
    current_rate = total_opt_pass / data_with_lxf["class"].count()

    pl(f"\n  {'─'*55}")
    pl(f"    {'':>20} │ {'当前(模拟后)':>12} │ {'风险分配':>10} │ {'变化':>8}")
    pl(f"    {'─'*55}")
    pl(f"    {'通过率':>20} │ {total_sim_pass/t_apply*100:>10.1f}% │ {current_rate*100:>8.1f}% │ {(current_rate-total_sim_pass/t_apply)*100:+>7.1f}pp")
    pl(f"    {'逾期率':>20} │ {combined_overdue*100:>10.2f}% │ {opt_overall*100:>8.2f}% │ {(opt_overall-combined_overdue)*100:+>7.2f}pp")
    pl(f"    {'通过数':>20} │ {total_sim_pass:>10,} │ {total_opt_pass:>8,} │ {total_opt_pass-total_sim_pass:+>7,}")
    pl(f"    {'─'*55}")
    verdict = "✅ 策略有效" if opt_overall < combined_overdue else "⚠️ 需权衡"
    pl(f"    结论: {verdict}，拒绝推断 {total_opt_newly:,} 人")
    pl()

pl(f"\n✅ 全部完成")

# ═══════════════════════════════════════
# 保存报告
# ═══════════════════════════════════════
report_content = "\n".join(lines)
report_path = save_report(report_content, f"sim_{_province_label}")
