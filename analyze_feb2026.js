const mysql = require('mysql2/promise');

async function main() {
  const conn = await mysql.createConnection({
    host: '47.119.181.195', port: 9030, user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)", database: 'ods',
  });
  const q = async (sql) => { const [r] = await conn.query(sql); return r; };

  const cond = "o.custtype='00' AND o.store_addr_province='湖南省' AND o.business_type='02'";
  const dws = "LEFT JOIN dws.dws_credit_yzf_order_complete c ON o.ct_user_id=c.ct_user_id AND c.source_business_type='淘顺实时授信'";

  // 1. 各月放款后逾期暴露速度（vintage模拟）：只看放款当月+次月已逾期的比例
  console.log('=== 放款后首月即逾期（首期不还率）=== ');
  for (const m of ['2025-11','2025-12','2026-01','2026-02','2026-03']) {
    const r = await q(`SELECT '${m}' AS cohort,
      COUNT(*) AS approved,
      SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS overdue,
      COUNT(c.ct_user_id) AS completed,
      ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS ovr
      FROM ods_ts_credit_yzf_order_grant_apply o LEFT JOIN dws.dws_credit_yzf_order_complete c ON o.ct_user_id=c.ct_user_id AND c.source_business_type='淘顺实时授信'
      WHERE ${cond} AND date_format(o.add_time,'%Y-%m')='${m}' AND o.apply_status='授信成功'`);
    if (r && r.length > 0) console.log(m, JSON.stringify(r[0]));
  }

  // 2. 2026-02 已逾期门店全量
  console.log('\n=== 2026-02放款且已逾期门店 ===');
  const feb = await q(`SELECT o.store_addr_city AS c, o.store_name AS s, o.ct_user_id AS uid,
    w.lxf, w.online_duration, w.operator_real, w.first_risk_result,
    c.step_num_repay_status
    FROM ods_ts_credit_yzf_order_grant_apply o
    LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no
    LEFT JOIN dws.dws_credit_yzf_order_complete c ON o.ct_user_id=c.ct_user_id AND c.source_business_type='淘顺实时授信'
    WHERE ${cond} AND date_format(o.add_time,'%Y-%m')='2026-02'
      AND o.apply_status='授信成功' AND c.step_num_repay_status=2
    ORDER BY o.store_addr_city, o.store_name`);
  console.log('逾期明细行数:', feb ? feb.length : 0);

  // 按门店汇总
  const storeMap = {};
  if (feb) for (const r of feb) {
    const key = r.c + '@' + r.s;
    if (!storeMap[key]) storeMap[key] = { city: r.c, store: r.s, cnt: 0, tb_cnt: 0, low_lxf: 0, low_online: 0, yw_cnt: 0 };
    storeMap[key].cnt++;
    if (r.first_risk_result === '特批白名单用户') storeMap[key].tb_cnt++;
    if (r.lxf !== null && r.lxf < 100) storeMap[key].low_lxf++;
    if (r.online_duration !== null && r.online_duration <= 3) storeMap[key].low_online++;
    if (r.operator_real === '移动' || r.operator_real === '联通') storeMap[key].yw_cnt++;
  }
  const sorted = Object.values(storeMap).sort((a,b) => b.cnt - a.cnt);
  console.log('\n=== 2026-02 逾期门店汇总 ===');
  console.table(sorted);

  // 3. 2026-02 逾期客群画像
  console.log('\n=== 2026-02 逾期 vs 非逾期 客群画像 ===');
  for (const status of ['逾期(已逾期)', '正常(未逾期)']) {
    const condition = status === '逾期(已逾期)' 
      ? "c.step_num_repay_status=2"
      : "(c.step_num_repay_status IS NULL OR c.step_num_repay_status!=2)";
    const r = await q(`SELECT '${status}' AS grp,
      COUNT(*) AS cnt,
      ROUND(AVG(w.lxf),1) AS avg_lxf,
      ROUND(AVG(w.online_duration),1) AS avg_online,
      ROUND(SUM(CASE WHEN w.operator_real IN ('移动','联通') THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),1) AS yw_pct,
      ROUND(SUM(CASE WHEN w.online_duration<=3 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),1) AS new_pct,
      ROUND(SUM(CASE WHEN w.first_risk_result='特批白名单用户' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),1) AS tb_pct,
      ROUND(SUM(CASE WHEN w.lxf IS NULL THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),1) AS null_lxf_pct
      FROM ods_ts_credit_yzf_order_grant_apply o
      LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no
      LEFT JOIN dws.dws_credit_yzf_order_complete c ON o.ct_user_id=c.ct_user_id AND c.source_business_type='淘顺实时授信'
      WHERE ${cond} AND date_format(o.add_time,'%Y-%m')='2026-02'
        AND o.apply_status='授信成功' AND ${condition}`);
    if (r && r.length > 0) console.log(status, JSON.stringify(r[0]));
  }

  // 4. 2026-02 逾期门店聚合（哪些门店贡献了最多逾期）
  // 用前面已经有的 storeMap 数据降序并只取逾期>=3的门店
  console.log('\n=== 2026-02 逾期门店排名（逾期>=3） ===');
  const topStores = sorted.filter(s => s.cnt >= 3);
  console.table(topStores);

  // 5. 特批 vs 非特批在2026-02的表现
  console.log('\n=== 2026-02 特批vs非特批 逾期表现 ===');
  for (const type of ['特批', '正常']) {
    const tbCond = type === '特批' ? "w.first_risk_result='特批白名单用户'" : "(w.first_risk_result IS NULL OR w.first_risk_result!='特批白名单用户')";
    const r = await q(`SELECT '${type}' AS type,
      COUNT(*) AS approved,
      SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS ov,
      ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),2) AS ovr
      FROM ods_ts_credit_yzf_order_grant_apply o
      LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no
      LEFT JOIN dws.dws_credit_yzf_order_complete c ON o.ct_user_id=c.ct_user_id AND c.source_business_type='淘顺实时授信'
      WHERE ${cond} AND date_format(o.add_time,'%Y-%m')='2026-02'
        AND o.apply_status='授信成功' AND ${tbCond}`);
    if (r && r.length > 0) console.log(type, JSON.stringify(r[0]));
  }

  // 6. 2026-02 非特批但lxf<100的逾期贡献
  console.log('\n=== 2026-02 各lxf段逾期率 ===');
  const lxfRanges = ['<50','50-100','100-200','200-300','300+','NULL'];
  for (const range of lxfRanges) {
    let lxfCond;
    if (range === 'NULL') lxfCond = "w.lxf IS NULL";
    else {
      const parts = range.split('-');
      if (parts.length === 1 && parts[0] === '<50') lxfCond = "w.lxf < 50";
      else if (parts.length === 1) lxfCond = "w.lxf >= 300";
      else lxfCond = `w.lxf >= ${parts[0]} AND w.lxf < ${parts[1]}`;
    }
    const r = await q(`SELECT '${range}' AS lxf_range,
      COUNT(*) AS approved,
      SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS ov,
      ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),2) AS ovr
      FROM ods_ts_credit_yzf_order_grant_apply o
      LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no
      LEFT JOIN dws.dws_credit_yzf_order_complete c ON o.ct_user_id=c.ct_user_id AND c.source_business_type='淘顺实时授信'
      WHERE ${cond} AND date_format(o.add_time,'%Y-%m')='2026-02'
        AND o.apply_status='授信成功' AND ${lxfCond}`);
    if (r && r.length > 0 && parseInt(r[0].approved) > 0) console.log(range, JSON.stringify(r[0]));
  }

  conn.end();
}
main().catch(e => { console.error(e); process.exit(1); });
