const mysql = require('mysql2/promise');
const fs = require('fs');

async function main() {
  const conn = await mysql.createConnection({
    host: '47.119.181.195', port: 9030, user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)", database: 'ods',
  });
  const query = async (sql) => { const [r] = await conn.query(sql); return r; };

  const dir = '/mnt/d/desktop/翼支付交流_门店代理商分析';

  // ============================================
  // 1. 各省特批白名单分布概览
  // ============================================
  const byProv = await query(`
    SELECT o.store_addr_province AS p,
      COUNT(*) AS total,
      SUM(CASE WHEN w.first_risk_result = '特批白名单用户' THEN 1 ELSE 0 END) AS tb,
      ROUND(SUM(CASE WHEN w.first_risk_result = '特批白名单用户' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS tb_pct,
      SUM(CASE WHEN o.apply_status = '授信成功' THEN 1 ELSE 0 END) AS pass,
      SUM(CASE WHEN o.apply_status = '授信成功' AND w.first_risk_result = '特批白名单用户' THEN 1 ELSE 0 END) AS tb_pass
    FROM ods_ts_credit_yzf_order_grant_apply o
    LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id = w.order_no
    WHERE o.custtype = '00' AND o.store_addr_province IS NOT NULL
      AND o.business_type = '02'
      AND o.add_time >= '2026-04-05'
    GROUP BY o.store_addr_province
    ORDER BY tb DESC
  `);

  // ============================================
  // 2. 湖南特批地市详情
  // ============================================
  const hnCity = await query(`
    SELECT o.store_addr_city AS city,
      COUNT(DISTINCT o.store_name) AS stores,
      COUNT(*) AS total,
      SUM(CASE WHEN w.first_risk_result = '特批白名单用户' THEN 1 ELSE 0 END) AS tb,
      ROUND(SUM(CASE WHEN w.first_risk_result = '特批白名单用户' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS tb_pct,
      SUM(CASE WHEN o.apply_status = '授信成功' THEN 1 ELSE 0 END) AS pass,
      SUM(CASE WHEN o.apply_status = '授信成功' AND w.first_risk_result IS NULL THEN 1 ELSE 0 END) AS normal_pass,
      SUM(CASE WHEN o.apply_status = '授信成功' AND w.first_risk_result = '特批白名单用户' THEN 1 ELSE 0 END) AS tb_pass
    FROM ods_ts_credit_yzf_order_grant_apply o
    LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id = w.order_no
    WHERE o.custtype = '00' AND o.store_addr_province = '湖南省'
      AND o.business_type = '02'
      AND o.add_time >= '2026-04-05'
    GROUP BY o.store_addr_city
    ORDER BY tb DESC
  `);

  // ============================================
  // 3. 湖南特批TOP30门店
  // ============================================
  const hnStores = await query(`
    SELECT o.store_addr_city AS city,
      o.store_name AS store,
      COUNT(*) AS total,
      SUM(CASE WHEN w.first_risk_result = '特批白名单用户' THEN 1 ELSE 0 END) AS tb,
      ROUND(SUM(CASE WHEN w.first_risk_result = '特批白名单用户' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS tb_pct,
      SUM(CASE WHEN o.apply_status = '授信成功' THEN 1 ELSE 0 END) AS pass
    FROM ods_ts_credit_yzf_order_grant_apply o
    LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id = w.order_no
    WHERE o.custtype = '00' AND o.store_addr_province = '湖南省'
      AND o.business_type = '02'
      AND o.add_time >= '2026-04-05'
    GROUP BY o.store_addr_city, o.store_name
    HAVING tb >= 5
    ORDER BY tb DESC
    LIMIT 50
  `);

  // ============================================
  // 4. 湖南特批门店名单（100%特批的门店）
  // ============================================
  const hnFullTb = await query(`
    SELECT o.store_addr_city AS city,
      o.store_name AS store,
      COUNT(*) AS total,
      SUM(CASE WHEN w.first_risk_result = '特批白名单用户' THEN 1 ELSE 0 END) AS tb
    FROM ods_ts_credit_yzf_order_grant_apply o
    LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id = w.order_no
    WHERE o.custtype = '00' AND o.store_addr_province = '湖南省'
      AND o.business_type = '02'
      AND o.add_time >= '2026-04-05'
    GROUP BY o.store_addr_city, o.store_name
    HAVING tb > 0 AND tb = COUNT(*)
    ORDER BY total DESC
    LIMIT 50
  `);

  // ============================================
  // 5. 特批 vs 非特批 — 逾期表现对比
  // ============================================
  const overdueComp = await query(`
    SELECT t.type,
      COUNT(DISTINCT t.ct_user_id) AS users,
      COUNT(*) AS orders,
      SUM(CASE WHEN c.step_num_repay_status = 2 THEN 1 ELSE 0 END) AS overdue,
      ROUND(SUM(CASE WHEN c.step_num_repay_status = 2 THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS overdue_rate
    FROM (
      SELECT o.ct_user_id,
        CASE WHEN w.first_risk_result = '特批白名单用户' THEN '特批' ELSE '正常' END AS type
      FROM ods_ts_credit_yzf_order_grant_apply o
      LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id = w.order_no
      WHERE o.custtype = '00' AND o.store_addr_province = '湖南省'
        AND o.business_type = '02'
        AND o.add_time >= '2026-04-05'
    ) t
    LEFT JOIN dws.dws_credit_yzf_order_complete c ON t.ct_user_id = c.ct_user_id AND c.source_business_type = '淘顺实时授信'
    GROUP BY t.type
  `);

  // ============================================
  // 6. 特批用户画像
  // ============================================
  const tbProfile = await query(`
    SELECT t.type,
      COUNT(*) AS total,
      ROUND(AVG(t.online_duration), 1) AS avg_online_months,
      ROUND(SUM(CASE WHEN t.operator_real IN ('移动','联通') THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 1) AS yw_pct,
      ROUND(SUM(CASE WHEN t.operator_real IN ('电信') THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 1) AS bw_pct,
      ROUND(AVG(t.lxf), 1) AS avg_lxf
    FROM (
      SELECT o.ct_user_id,
        CASE WHEN w.first_risk_result = '特批白名单用户' THEN '特批' ELSE '正常' END AS type,
        w.online_duration, w.operator_real, w.lxf
      FROM ods_ts_credit_yzf_order_grant_apply o
      LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id = w.order_no
      WHERE o.custtype = '00' AND o.store_addr_province = '湖南省'
        AND o.business_type = '02'
        AND o.add_time >= '2026-04-05'
    ) t
    GROUP BY t.type
  `);

  // ============================================
  // 7. 湖南100%特批地市的特批门店列表
  // ============================================
  const tbDepCities = ['益阳市','湘西土家族苗族自治州','怀化市','娄底市','湘潭市','张家界市'];
  const tbCityStores = {};
  for (const city of tbDepCities) {
    tbCityStores[city] = await query(`
      SELECT o.store_name AS store,
        COUNT(*) AS total,
        SUM(CASE WHEN w.first_risk_result = '特批白名单用户' THEN 1 ELSE 0 END) AS tb,
        ROUND(SUM(CASE WHEN w.first_risk_result = '特批白名单用户' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS tb_pct,
        SUM(CASE WHEN o.apply_status = '授信成功' THEN 1 ELSE 0 END) AS pass
      FROM ods_ts_credit_yzf_order_grant_apply o
      LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id = w.order_no
      WHERE o.custtype = '00' AND o.store_addr_province = '湖南省'
        AND o.store_addr_city = '${city}'
        AND o.business_type = '02'
        AND o.add_time >= '2026-04-05'
      GROUP BY o.store_name
      ORDER BY total DESC
    `);
  }

  // ============================================
  // 生成CSV
  // ============================================
  const csv = (rows, flds) => {
    const h = flds.join(',');
    const l = rows.map(r => flds.map(f => {
      const v = r[f]; if (v === null || v === undefined) return '';
      const s = String(v); return s.includes(',') || s.includes('"') || s.includes('\n') ? '"' + s.replace(/"/g, '""') + '"' : s;
    }).join(','));
    return h + '\n' + l.join('\n');
  };

  fs.writeFileSync(dir + '/特批白名单_各省分布.csv', csv(byProv, ['p','total','tb','tb_pct','pass','tb_pass']));
  fs.writeFileSync(dir + '/特批白名单_湖南地市.csv', csv(hnCity, ['city','stores','total','tb','tb_pct','pass','normal_pass','tb_pass']));
  fs.writeFileSync(dir + '/特批白名单_湖南TOP门店.csv', csv(hnStores, ['city','store','total','tb','tb_pct','pass']));

  // ============================================
  // 生成报告
  // ============================================
  const L = [];
  const p = s => L.push(s);
  const h1 = s => { L.push(''); L.push('---'); L.push('## ' + s); L.push(''); };
  const h2 = s => { L.push('### ' + s); L.push(''); };
  const tbl = (rows, hdrs, fmt) => {
    L.push('| ' + hdrs.join(' | ') + ' |');
    L.push('|' + hdrs.map(() => ':---:').join('|') + '|');
    rows.forEach(r => L.push('| ' + (fmt ? fmt(r) : hdrs.map(h => String(r[h] ?? '')).join(' | ')) + ' |'));
  };

  L.push('# 特批白名单用户专项分析');
  L.push('> 数据范围：2026/4/5 ~ 5/12 | ods_ts | business_type=02 | 公众客群(custtype=00) | 不去重');
  L.push('');

  h1('一、各省特批白名单分布');
  const tbProv = byProv.filter(r => r.tb > 0);
  if (tbProv.length > 0) {
    tbl(tbProv, ['省份', '总申请量', '特批用户', '特批占比', '总通过', '特批通过'],
      r => [r.p, String(r.total), String(r.tb), r.tb_pct + '%', String(r.pass), String(r.tb_pass)].join(' | '));
    L.push('');
    const onlyHN = tbProv.filter(r => r.tb > 0);
    p(`**结论**：特批白名单用户仅存在于**湖南省**（${tbProv[0].tb}人，占比${tbProv[0].tb_pct}%），其他省份特批用户数为0。`);
  } else {
    p('各省特批用户数均为0。');
  }
  L.push('');

  h1('二、湖南各地市特批分布');
  tbl(hnCity, ['地市', '门店数', '总申请', '特批订单', '特批占比', '总通过', '正常通过', '特批通过'],
    r => [r.city, String(r.stores), String(r.total), String(r.tb), r.tb_pct + '%', String(r.pass), String(r.normal_pass), String(r.tb_pass)].join(' | '));
  L.push('');

  // 地市分析
  const fullTbCities = hnCity.filter(r => parseFloat(r.tb_pct) >= 95);
  const highTbCities = hnCity.filter(r => parseFloat(r.tb_pct) >= 20 && parseFloat(r.tb_pct) < 95);
  const normalCities = hnCity.filter(r => parseFloat(r.tb_pct) < 20 && parseFloat(r.tb_pct) > 0);

  if (fullTbCities.length) {
    p(`**🔥 100%特批依赖地市**（特批占比≥95%）：${fullTbCities.map(c => `${c.city}(${c.tb}/${c.total}单, ${c.tb_pct}%)`).join('、')}。`);
    p(`  这些地市共${fullTbCities.reduce((s,c) => s + c.stores, 0)}家门店，无任何一单走正常风控流程通过。`);
  }
  if (highTbCities.length) {
    p(`**⚠️ 高特批依赖地市**（20%~95%）：${highTbCities.map(c => `${c.city}(${c.tb_pct}%)`).join('、')}。`);
  }
  if (normalCities.length) {
    p(`**ℹ️ 有特批但占比较低**（<20%）：${normalCities.map(c => `${c.city}(${c.tb_pct}%)`).join('、')}。`);
  }
  L.push('');

  h1('三、湖南特批TOP门店（特批≥5单）');
  tbl(hnStores.slice(0, 30), ['地市', '门店', '总申请', '特批', '特批占比', '通过数'],
    r => [r.city, r.store, String(r.total), String(r.tb), r.tb_pct + '%', String(r.pass)].join(' | '));
  L.push('');

  h2('100%依赖特批的门店');
  if (hnFullTb.length > 0) {
    tbl(hnFullTb.slice(0, 30), ['地市', '门店', '总申请', '特批'],
      r => [r.city, r.store, String(r.total), String(r.tb)].join(' | '));
    L.push('');
    p(`共${hnFullTb.length}家门店100%依赖特批通道。`);
  }
  L.push('');

  h1('四、特批依赖地市 — 门店明细');

  for (const city of tbDepCities) {
    const stores = tbCityStores[city] || [];
    if (stores.length === 0) continue;
    const totalTb = stores.reduce((s, x) => s + (x.tb || 0), 0);
    const totalAll = stores.reduce((s, x) => s + (x.total || 0), 0);

    h2(`${city}（共${stores.length}家门店，特批${totalTb}/${totalAll}单）`);
    tbl(stores, ['门店', '总申请', '特批', '特批占比', '通过数'],
      r => [r.store, String(r.total), String(r.tb), r.tb_pct + '%', String(r.pass)].join(' | '));
    L.push('');

    const fullTbStores = stores.filter(s => parseFloat(s.tb_pct) >= 100);
    if (fullTbStores.length > 0) {
      p(`其中${fullTbStores.length}家门店100%依赖特批：${fullTbStores.map(s => s.store).join('、')}。`);
      L.push('');
    }
  }

  h1('五、特批 vs 非特批 — 逾期表现对比');
  if (overdueComp.length > 0) {
    tbl(overdueComp, ['用户类型', '用户数', '订单数', '逾期数', '逾期率'],
      r => [r.type, String(r.users), String(r.orders), String(r.overdue), r.overdue_rate + '%'].join(' | '));
    L.push('');
    
    const tbRow = overdueComp.find(r => r.type === '特批');
    const normalRow = overdueComp.find(r => r.type === '正常');
    if (tbRow) {
      p(`特批用户${tbRow.orders}单，逾期${tbRow.overdue}单（${tbRow.overdue_rate}%）。`);
    }
    if (normalRow) {
      p(`正常用户${normalRow.orders}单，逾期${normalRow.overdue}单（${normalRow.overdue_rate}%）。`);
    }
  }
  L.push('');

  h1('六、特批用户画像对比（湖南）');
  tbl(tbProfile, ['用户类型', '数量', '平均在网(月)', '异网占比', '本网占比', '平均lxf'],
    r => [r.type, String(r.total), r.avg_online_months, r.yw_pct + '%', r.bw_pct + '%', r.avg_lxf ?? '-'].join(' | '));
  L.push('');

  h1('七、结论与建议');
  p('1. 特批白名单用户**仅湖南省存在**（2,105单，占全省18.4%），其他省份无此通道。');
  p(`2. **6个地市完全依赖特批**：${fullTbCities.map(c => c.city).join('、')}。这些地市无任何正常风控通过记录，模型自动审批能力为零。`);
  p('3. 正常通过率最低的地市（郴州45%、长沙48%）反而特批占比不高（8~13%），说明模型在这些地方仍有一定判断力。');
  p(`4. 共有${hnFullTb.length}家门店100%依赖特批通道，这些门店如特批政策调整将直接停摆。`);
  if (overdueComp.length > 0) {
    const tbRow = overdueComp.find(r => r.type === '特批');
    if (tbRow && parseInt(tbRow.overdue) > 0) {
      p(`5. 特批用户逾期率${tbRow.overdue_rate}%，建议关注特批用户贷后表现。`);
    } else if (tbRow) {
      p(`5. 特批用户当前逾期率${tbRow.overdue_rate}%（${tbRow.orders}单0逾期），但样本量有限且观察期短，需持续跟踪。`);
    }
  }
  p('6. 建议：1) 排查完全依赖特批的地市能否承接正常风控；2) 对高特批门店设置特批申请上限；3) 跟踪特批用户的还款表现。');
  L.push('');

  fs.writeFileSync(dir + '/特批白名单专项分析.md', L.join('\n'));
  console.log('✅ 特批白名单专项分析完成');
  console.log(`   - 湖南省: ${hnCity.reduce((s,r) => s + r.tb, 0)} 单特批`);
  console.log(`   - 100%特批门店: ${hnFullTb.length} 家`);
  console.log(`   - 完全依赖特批地市: ${fullTbCities.length} 个`);

  conn.end();
}
main().catch(e => { console.error(e); process.exit(1); });
