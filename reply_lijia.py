#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
回复李嘉 — 贵州/广西/海南 通过率 + 逾期明细 + 门店逾期率
产出：4个Sheet的Excel → 邮件发送
"""

import sys
import os
from datetime import datetime

# 把项目路径加入 sys.path，复用 Email.py
PROJECT_ROOT = r"F:\OneDrive - 湖南工商大学\codeworksplce\Work_code\bfravel_risk_engine"
sys.path.insert(0, os.path.join(PROJECT_ROOT, "analysis_function"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "connect"))

from Email import EmailSender
from connect_db_offline import get_data

# ===== 配置 =====
PROVINCES = "'贵州省','广西壮族自治区','海南省'"
DATE_RANGE = '2026-04-16'          # 通过率近30天起始
WORK_DIR = r'F:\风控模型\数据文件'
os.makedirs(WORK_DIR, exist_ok=True)

# ===== 去重通过率子查询（用户已有逻辑） =====
DEDUP_SUB = f"""
  SELECT a1.*, a3.operator_real, a3.first_risk_result, a3.online_duration
  FROM ods.ods_ts_credit_yzf_order_grant_apply a1
  LEFT JOIN ods.ods_ts_credit_yzf_order_grant_apply a2
    ON a1.id_number_enc = a2.id_number_enc
    AND ( (a2.apply_status = '授信成功' AND a1.apply_status != '授信成功')
        OR (a1.apply_status = a2.apply_status AND a1.id < a2.id) )
  LEFT JOIN ods.ods_ts_order_white_list_control a3 ON a1.ct_user_id = a3.order_no
  WHERE a2.id IS NULL AND a1.business_type = '02'
"""

# ===== 1. 订单逾期明细（展业以来·三省·公众） =====
SQL_OVERDUE_DETAIL = f"""
  SELECT
    t1.order_no                    AS '订单号',
    t1.complete_time               AS '竣工时间',
    t1.province                    AS '省份',
    t1.city                        AS '地市',
    t1.order_amt_yuan              AS '放款金额',
    CASE WHEN t1.custtype = '00' THEN '公众' ELSE 'VIP' END AS '用户类型',
    ROUND(t1.remaining_principal / 100, 2) AS '贷余金额',
    ROUND(CASE WHEN t1.step_num_repay_status = 2 THEN t1.remaining_principal / 100 ELSE 0 END, 2) AS '逾期金额',
    t1.supplier_name               AS '代理商名称',
    t1.supplier_code               AS '代理商编码',
    t1.store_name                  AS '门店名称',
    t1.store_id                    AS '门店id',
    t2.seller_name                 AS '营业员姓名',
    t2.seller_mobile               AS '营业员手机号',
    CASE WHEN t1.step_num_repay_status = 2 THEN '逾期' ELSE '未逾期' END AS '是否逾期',
    t1.total_due_count             AS '应还次数',
    t1.total_repaid_count          AS '已还次数',
    t1.total_due_count - t1.total_repaid_count AS '未还次数'
  FROM dws.dws_credit_yzf_order_complete t1
  LEFT JOIN ods.ods_ts_credit_yzf_order_grant_apply t2
    ON t1.ct_user_id = t2.ct_user_id
  WHERE t1.source_business_type = '淘顺实时授信'
    AND t1.step_num_repay_status = 2
    AND t1.province IN ({PROVINCES})
    AND t1.custtype = '00'
  ORDER BY t1.complete_time DESC
"""

# ===== 2. 门店逾期率汇总（展业以来·三省） =====
SQL_STORE = f"""
  SELECT
    a.province                     AS '省份',
    a.city                         AS '地市',
    a.supplier_name                AS '代理商',
    a.supplier_code                AS '代理商编码',
    a.store_name                   AS '门店名称',
    a.store_id                     AS '门店编码',
    CASE WHEN b.channel_level IS NOT NULL THEN b.channel_level ELSE '普通渠道' END AS '门店状态',
    MIN(a.complete_time)           AS '最早办单时间',
    MAX(a.complete_time)           AS '最新办单时间',
    COUNT(*)                       AS '整体竣工数',
    SUM(CASE WHEN a.step_num_repay_status = 2 THEN 1 ELSE 0 END) AS '整体逾期数',
    ROUND(SUM(CASE WHEN a.step_num_repay_status = 2 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS '整体逾期率',
    SUM(CASE WHEN a.custtype = '00' THEN 1 ELSE 0 END) AS '公众竣工数',
    SUM(CASE WHEN a.custtype = '00' AND a.step_num_repay_status = 2 THEN 1 ELSE 0 END) AS '公众逾期数',
    ROUND(
      SUM(CASE WHEN a.custtype = '00' AND a.step_num_repay_status = 2 THEN 1 ELSE 0 END)
      / NULLIF(SUM(CASE WHEN a.custtype = '00' THEN 1 ELSE 0 END), 0), 4
    ) AS '公众逾期率',
    SUM(CASE WHEN a.custtype != '00' THEN 1 ELSE 0 END) AS 'vip竣工数',
    SUM(CASE WHEN a.custtype != '00' AND a.step_num_repay_status = 2 THEN 1 ELSE 0 END) AS 'vip逾期数',
    ROUND(
      SUM(CASE WHEN a.custtype != '00' AND a.step_num_repay_status = 2 THEN 1 ELSE 0 END)
      / NULLIF(SUM(CASE WHEN a.custtype != '00' THEN 1 ELSE 0 END), 0), 4
    ) AS 'vip逾期率'
  FROM dws.dws_credit_yzf_order_complete a
  LEFT JOIN (
    SELECT store_code, channel_level
    FROM (
      SELECT store_code, channel_level,
             ROW_NUMBER() OVER (PARTITION BY store_code ORDER BY add_time DESC) AS rn
      FROM ods.ods_ts_v3_order_store
      WHERE isv = '淘顺' AND type = '翼支付实时授信'
    ) t WHERE rn = 1
  ) b ON a.store_id = b.store_code
  WHERE a.source_business_type = '淘顺实时授信'
    AND a.province IN ({PROVINCES})
  GROUP BY a.province, a.city, a.supplier_name, a.supplier_code, a.store_name, a.store_id, b.channel_level
  ORDER BY a.province, a.city, 整体逾期率 DESC
"""

# ===== 3. 三省通过率（近30天·日维度·去重） =====
SQL_PASS_RATE = f"""
  SELECT
    DATE_FORMAT(add_time, '%Y-%m-%d') AS '日期',
    store_addr_province              AS '省份',
    COUNT(*)                         AS '申请数',
    SUM(CASE WHEN apply_status = '授信成功' THEN 1 ELSE 0 END) AS '通过数',
    ROUND(
      SUM(CASE WHEN apply_status = '授信成功' AND first_risk_result != '特批白名单用户' THEN 1 ELSE 0 END)
      / NULLIF(COUNT(*), 0), 4
    ) AS '通过率',
    ROUND(
      SUM(CASE WHEN apply_status = '授信成功' OR first_risk_result = '特批白名单用户' THEN 1 ELSE 0 END)
      / NULLIF(COUNT(*), 0), 4
    ) AS '含特批通过率',
    SUM(CASE WHEN first_risk_result = '特批白名单用户' THEN 1 ELSE 0 END) AS '特批用户数',
    ROUND(
      SUM(CASE WHEN operator_real IN ('移动', '联通') THEN 1 ELSE 0 END)
      / NULLIF(COUNT(*), 0), 4
    ) AS '异网占比',
    ROUND(
      SUM(CASE WHEN apply_status = '授信成功' AND operator_real IN ('移动', '联通') THEN 1 ELSE 0 END)
      / NULLIF(SUM(CASE WHEN operator_real IN ('移动', '联通') THEN 1 ELSE 0 END), 0), 2
    ) AS '异网通过率',
    ROUND(
      SUM(CASE WHEN apply_status = '授信成功' AND operator_real IN ('电信') THEN 1 ELSE 0 END)
      / NULLIF(SUM(CASE WHEN operator_real IN ('电信') THEN 1 ELSE 0 END), 0), 2
    ) AS '本网通过率',
    ROUND(
      SUM(CASE WHEN online_duration <= 3 THEN 1 ELSE 0 END)
      / NULLIF(COUNT(*), 0), 4
    ) AS '新客占比',
    ROUND(
      SUM(CASE WHEN apply_status = '授信成功' AND online_duration <= 3 THEN 1 ELSE 0 END)
      / NULLIF(SUM(CASE WHEN online_duration <= 3 THEN 1 ELSE 0 END), 0), 2
    ) AS '新客通过率'
  FROM ({DEDUP_SUB}) t
  WHERE add_time >= '{DATE_RANGE}'
    AND custtype = '00'
    AND store_addr_province IN ({PROVINCES})
  GROUP BY DATE_FORMAT(add_time, '%Y-%m-%d'), store_addr_province
  ORDER BY store_addr_province, 日期
"""

# ===== 4. 三省地市通过率汇总 =====
SQL_CITY = f"""
  SELECT
    store_addr_province              AS '省份',
    store_addr_city                  AS '地市',
    COUNT(*)                         AS '申请数',
    SUM(CASE WHEN apply_status = '授信成功' THEN 1 ELSE 0 END) AS '通过数',
    ROUND(
      SUM(CASE WHEN apply_status = '授信成功' AND first_risk_result != '特批白名单用户' THEN 1 ELSE 0 END)
      / NULLIF(COUNT(*), 0), 4
    ) AS '通过率',
    ROUND(
      SUM(CASE WHEN apply_status = '授信成功' OR first_risk_result = '特批白名单用户' THEN 1 ELSE 0 END)
      / NULLIF(COUNT(*), 0), 4
    ) AS '含特批通过率',
    ROUND(
      SUM(CASE WHEN operator_real IN ('移动', '联通') THEN 1 ELSE 0 END)
      / NULLIF(COUNT(*), 0), 4
    ) AS '异网占比',
    ROUND(
      SUM(CASE WHEN online_duration <= 3 THEN 1 ELSE 0 END)
      / NULLIF(COUNT(*), 0), 4
    ) AS '新客占比',
    COUNT(DISTINCT store_name)       AS '活跃门店数'
  FROM ({DEDUP_SUB}) t
  WHERE add_time >= '{DATE_RANGE}'
    AND custtype = '00'
    AND store_addr_province IN ({PROVINCES})
  GROUP BY store_addr_province, store_addr_city
  ORDER BY 省份, 通过率
"""


def run_sql(label, sql):
    """执行SQL并返回DataFrame"""
    print(f"  [SQL] {label}...", end=' ', flush=True)
    connector = get_data(data_type='risk')
    df = connector.get_data(sql)
    connector.close()
    print(f"→ {len(df)} 行")
    return df


def make_excel(overdue, stores, pass_rate, city_rate):
    """生成多Sheet Excel文件"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'三省通过率逾期数据_{timestamp}.xlsx'
    filepath = os.path.join(WORK_DIR, filename)

    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        sheets = [
            ('订单逾期明细', overdue),
            ('门店逾期率', stores),
            ('三省通过率', pass_rate),
            ('三省地市通过率', city_rate),
        ]
        for name, df in sheets:
            df.to_excel(writer, sheet_name=name, index=False)
            # 列宽自适应
            ws = writer.sheets[name]
            for i, col in enumerate(df.columns, 1):
                max_len = max(df[col].astype(str).map(len).max() if len(df) > 0 else 0,
                              len(str(col))) + 2
                from openpyxl.utils import get_column_letter
                ws.column_dimensions[get_column_letter(i)].width = min(max_len, 40)

    print(f"✅ Excel: {filepath}")
    return filepath


def send_email(filepath):
    """使用已有 Email 类发送邮件"""
    sender = EmailSender(
        smtp_server='smtp.163.com',
        smtp_port=465,
        sender_email='19376667428@163.com',
        sender_password='LMUmWTVeVQrV5F28',
        sender_name='风险建模分析助手',
        use_ssl=True
    )

    today = datetime.now().strftime('%Y-%m-%d')
    success = sender.send_report(
        to_emails=['lij@topshake.cn'],
        report_file=filepath,
        report_name=f'贵州/广西/海南 — 通过率与逾期数据（{today}）',
        cc_emails=['19376667428@163.com'],
    )
    if success:
        print(f"📬 收件人: lij@topshake.cn")
        print(f"📋 抄送: 19376667428@163.com")
    return success


def main():
    print("🚀 开始查询数据...\n")

    # 1. 执行4个SQL
    overdue_df = run_sql('逾期订单明细', SQL_OVERDUE_DETAIL)
    stores_df = run_sql('门店逾期率', SQL_STORE)
    pass_rate_df = run_sql('三省通过率', SQL_PASS_RATE)
    city_df = run_sql('三省地市通过率', SQL_CITY)

    # 2. 生成Excel
    print("\n📊 生成 Excel...")
    filepath = make_excel(overdue_df, stores_df, pass_rate_df, city_df)

    # 3. 发送邮件
    print("\n📧 发送邮件...")
    if send_email(filepath):
        print("\n✅ 全部完成！")
    else:
        print("\n❌ 邮件发送失败")


if __name__ == '__main__':
    # 延迟导入
    import pandas as pd
    main()
