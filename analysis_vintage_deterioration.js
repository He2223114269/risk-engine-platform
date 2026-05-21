const mysql = require('mysql2/promise');
const fs = require('fs');

async function main() {
  const conn = await mysql.createConnection({
    host: '47.119.181.195', port: 9030, user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)", database: 'ods',
  });
  const q = async (sql) => { const [r] = await conn.query(sql); return r; };

  const cond = "o.custtype='00' AND o.business_type='02'";
  const dws = "LEFT JOIN dws.dws_credit_yzf_order_complete c ON o.ct_user_id=c.ct_user_id AND c.source_business_type='淘顺实时授信'";

  // ========= 1. 湖南+贵州 逐月趋势（2024-10起）=========
  const months = ['2024-10','2024-11','2024-12','2025-01','2025-02','2025-03','2025-04','2025-05','2025-06',
                  '2025-07','2025-08','2025-09','2025-10','2025-11','2025-12','2026-01','2026-02','2026-03','2026-04','2026-05'];
  const allTrends = [];

  for (const prov of ['湖南省','贵州省']) {
    for (const m of months) {
      const r = await q(`SELECT '${prov}' AS p, '${m}' AS m,
        COUNT(*) AS a,
        SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS ap,
        COUNT(c.ct_user_id) AS co,
        SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS ov
        FROM ods_ts_credit_yzf_order_grant_apply o ${dws}
        WHERE ${cond} AND o.store_addr_province='${prov}' AND date_format(o.add_time,'%Y-%m')='${m}'`);
      if (r && r.length > 0 && parseInt(r[0].a) > 0) allTrends.push(r[0]);
    }
  }
  console.log('=== 月度趋势 ===');
  console.table(allTrends);
  console.log('\n');

  // ========= 2. 拆分：2025年11月前后对比 =========
  const before = ['2025-09','2025-10'];
  const after  = ['2025-11','2025-12','2026-01','2026-02','2026-03','2026-04','2026-05'];

  console.log('=== 2025.11前后对比 ===');
  for (const prov of ['湖南省','贵州省']) {
    for (const [periodName, periodMonths] of [['2025-09~10(前)', before], ['2025-11~2026-05(后)', after]]) {
      if (periodMonths.length === 0) continue;
      const mlist = periodMonths.map(m => `'${m}'`).join(',');
      const r = await q(`SELECT '${prov}' AS p, '${periodName}' AS period,
        COUNT(*) AS a,
        SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS ap,
        ROUND(SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),1) AS apr,
        COUNT(c.ct_user_id) AS co,
        SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS ov,
        ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS ovr
        FROM ods_ts_credit_yzf_order_grant_apply o ${dws}
        WHERE ${cond} AND o.store_addr_province='${prov}' AND date_format(o.add_time,'%Y-%m') IN (${mlist})`);
      if (r && r.length > 0) console.log(prov, periodName, JSON.stringify(r[0]));
    }
  }
  console.log('\n');

  // ========= 3. 湖南+贵州 11月后各城市分拆 =========
  console.log('=== 2025.11后各地市逾期率 ===');
  for (const prov of ['湖南省','贵州省']) {
    const afterList = after.map(m => `'${m}'`).join(',');
    const cityR = await q(`SELECT o.store_addr_city AS c,
      COUNT(*) AS a,
      SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS ap,
      COUNT(c.ct_user_id) AS co,
      SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS ov,
      ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS ovr
      FROM ods_ts_credit_yzf_order_grant_apply o ${dws}
      WHERE ${cond} AND o.store_addr_province='${prov}' AND date_format(o.add_time,'%Y-%m') IN (${afterList})
      GROUP BY o.store_addr_city ORDER BY ovr DESC`);
    console.log(prov);
    if (cityR && cityR.length > 0) console.table(cityR);
  }
  console.log('\n');

  // ========= 4. 湖南+贵州 客群结构变化 =========
  console.log('=== 湖南 前后客群结构 ===');
  for (const prov of ['湖南省','贵州省']) {
    for (const [periodName, periodMonths] of [['前', before], ['后', after]]) {
      const mlist = periodMonths.map(m => `'${m}'`).join(',');
      const r = await q(`SELECT '${prov}' AS p, '${periodName}' AS period,
        COUNT(*) AS a,
        ROUND(SUM(CASE WHEN w.online_duration<=3 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),1) AS new_pct,
        ROUND(SUM(CASE WHEN w.operator_real IN ('移动','联通') THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),1) AS yw_pct,
        ROUND(SUM(CASE WHEN w.first_risk_result='特批白名单用户' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),1) AS tb_pct,
        ROUND(AVG(w.lxf),1) AS avg_lxf,
        ROUND(AVG(w.online_duration),1) AS avg_online
        FROM ods_ts_credit_yzf_order_grant_apply o
        LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no
        WHERE ${cond} AND o.store_addr_province='${prov}' AND date_format(o.add_time,'%Y-%m') IN (${mlist})`);
      if (r && r.length > 0) console.log(prov, periodName, JSON.stringify(r[0]));
    }
  }
  console.log('\n');

  // ========= 5. 湖南+贵州 2025.11后逾期最严重的门店TOP20 =========
  console.log('=== 2025.11后 逾期率最高门店TOP20 ===');
  for (const prov of ['湖南省','贵州省']) {
    const afterList = after.map(m => `'${m}'`).join(',');
    const storeR = await q(`SELECT o.store_addr_city AS c, o.store_name AS s,
      COUNT(*) AS a,
      SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS ap,
      COUNT(c.ct_user_id) AS co,
      SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS ov,
      ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS ovr
      FROM ods_ts_credit_yzf_order_grant_apply o ${dws}
      WHERE ${cond} AND o.store_addr_province='${prov}' AND date_format(o.add_time,'%Y-%m') IN (${afterList})
        AND c.ct_user_id IS NOT NULL
      GROUP BY o.store_addr_city, o.store_name
      HAVING COUNT(*) >= 5 AND SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) > 0
      ORDER BY ovr DESC LIMIT 15`);
    console.log(`${prov} TOP15`);
    if (storeR && storeR.length > 0) console.table(storeR);
  }

  conn.end();
}
main().catch(e => { console.error(e); process.exit(1); });
