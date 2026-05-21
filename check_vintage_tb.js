const mysql = require('mysql2/promise');

async function main() {
  const conn = await mysql.createConnection({
    host: '47.119.181.195', port: 9030, user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)", database: 'ods',
  });
  const q = async (sql) => { const [r] = await conn.query(sql); return r; };

  const cond = "o.custtype='00' AND o.store_addr_province='湖南省' AND o.business_type='02'";
  const dws = "LEFT JOIN dws.dws_credit_yzf_order_complete c ON o.ct_user_id=c.ct_user_id AND c.source_business_type='淘顺实时授信'";

  // 含特批 vs 不含特批 金额逾期率
  console.log('=== 含特批 vs 不含特批 金额逾期率（对比你的vintage）===');
  for (const label of ['含特批(全部)', '不含特批(仅正常)']) {
    const tbCond = label === '含特批(全部)' 
      ? "1=1" 
      : "(w.first_risk_result IS NULL OR w.first_risk_result!='特批白名单用户')";
    for (const m of ['2025-11','2025-12','2026-01','2026-02','2026-03']) {
      const r = await q(`SELECT '${m}' AS month, '${label}' AS grp,
        COUNT(*) AS cnt,
        ROUND(SUM(o.order_amt/1000000),1) AS loan_amt_wan,
        ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN o.order_amt/1000000 ELSE 0 END),1) AS overdue_amt_wan,
        ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN o.order_amt/1000000 ELSE 0 END)*100.0/NULLIF(SUM(o.order_amt/1000000),0),2) AS ovr_pct
        FROM ods_ts_credit_yzf_order_grant_apply o
        LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no
        ${dws}
        WHERE ${cond} AND date_format(o.add_time,'%Y-%m')='${m}'
          AND o.apply_status='授信成功' AND ${tbCond}`);
      if (r && r.length > 0) console.log(m, label, JSON.stringify(r[0]));
    }
  }

  // 对比
  console.log('\n=== 对照表 ===');
  console.log('你的vintage:');
  console.log('2025-11 mob5=4.07% | 2025-12 mob4=5.45% | 2026-01 mob3=3.89% | 2026-02 mob2=1.48%');
  console.log('(mob5/4/3/2是累计逾期率)');

  conn.end();
}
main().catch(e => { console.error(e); process.exit(1); });
