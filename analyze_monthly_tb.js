const mysql = require('mysql2/promise');

async function main() {
  const conn = await mysql.createConnection({
    host: '47.119.181.195', port: 9030, user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)", database: 'ods',
  });
  const q = async (sql) => { const [r] = await conn.query(sql); return r; };

  const cond = "o.custtype='00' AND o.store_addr_province='湖南省' AND o.business_type='02'";
  const dws = "LEFT JOIN dws.dws_credit_yzf_order_complete c ON o.ct_user_id=c.ct_user_id AND c.source_business_type='淘顺实时授信'";

  // 逐月：特批 vs 正常 的逾期表现
  const months = ['2025-11','2025-12','2026-01','2026-02','2026-03'];
  console.log('=== 逐月 特批vs正常 逾期表现 ===');
  for (const m of months) {
    for (const type of ['特批','正常']) {
      const tbCond = type === '特批' ? "w.first_risk_result='特批白名单用户'" : "(w.first_risk_result IS NULL OR w.first_risk_result!='特批白名单用户')";
      const r = await q(`SELECT '${m}' AS month, '${type}' AS type,
        COUNT(*) AS approved,
        COUNT(c.ct_user_id) AS completed,
        SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS overdue,
        ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS ovr
        FROM ods_ts_credit_yzf_order_grant_apply o
        LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no
        ${dws}
        WHERE ${cond} AND date_format(o.add_time,'%Y-%m')='${m}'
          AND o.apply_status='授信成功' AND ${tbCond}`);
      if (r && r.length > 0) console.log(m, type, JSON.stringify(r[0]));
    }
  }

  // 加上各月特批占比
  console.log('\n=== 各月特批占比 ===');
  for (const m of months) {
    const r = await q(`SELECT '${m}' AS month,
      COUNT(*) AS approved,
      ROUND(SUM(CASE WHEN w.first_risk_result='特批白名单用户' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),1) AS tb_pct,
      SUM(CASE WHEN w.first_risk_result='特批白名单用户' THEN 1 ELSE 0 END) AS tb_cnt
      FROM ods_ts_credit_yzf_order_grant_apply o
      LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no
      WHERE ${cond} AND date_format(o.add_time,'%Y-%m')='${m}' AND o.apply_status='授信成功'`);
    if (r && r.length > 0) console.log(m, JSON.stringify(r[0]));
  }

  conn.end();
}
main().catch(e => { console.error(e); process.exit(1); });
