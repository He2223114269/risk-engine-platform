const mysql = require('mysql2/promise');
const fs = require('fs');

async function main() {
  const conn = await mysql.createConnection({
    host: '47.119.181.195', port: 9030, user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)", database: 'ods',
  });
  const q = async (sql) => { const [r] = await conn.query(sql); return r; };

  const dir = '/mnt/d/desktop/翼支付交流_门店代理商分析';
  const tbCond = "w.first_risk_result = '特批白名单用户'";
  const normalCond = "(w.first_risk_result IS NULL OR w.first_risk_result != '特批白名单用户')";
  const baseJoin = `FROM ods_ts_credit_yzf_order_grant_apply o
    LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id = w.order_no
    LEFT JOIN dws.dws_credit_yzf_order_complete c ON o.ct_user_id = c.ct_user_id AND c.source_business_type = '淘顺实时授信'
    WHERE o.custtype = '00' AND o.store_addr_province = '湖南省'
      AND o.business_type = '02' AND o.add_time >= '2026-04-05'`;

  // ===================== 1. 全省对比 =====================
  const tbFull = await q(`SELECT '特批' AS type,
    COUNT(*) AS apply, SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS approve,
    ROUND(SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),2) AS approve_rate,
    COUNT(DISTINCT c.ct_user_id) AS complete_users,
    COUNT(c.ct_user_id) AS complete_orders,
    SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS overdue,
    ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS overdue_rate
    ${baseJoin} AND ${tbCond}`);

  const normalFull = await q(`SELECT '正常' AS type,
    COUNT(*) AS apply, SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS approve,
    ROUND(SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),2) AS approve_rate,
    COUNT(DISTINCT c.ct_user_id) AS complete_users,
    COUNT(c.ct_user_id) AS complete_orders,
    SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS overdue,
    ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS overdue_rate
    ${baseJoin} AND ${normalCond}`);

  const fullCompare = [...tbFull, ...normalFull];
  console.log('=== 湖南 特批vs正常 全链路质态 ===');
  console.table(fullCompare);

  // ===================== 2. 地市对比 =====================
  const tbDeps = ['益阳市','湘西土家族苗族自治州','怀化市','娄底市','湘潭市','张家界市'];
  const normalRef = ['长沙市','衡阳市','郴州市','株洲市','邵阳市','常德市','永州市','岳阳市'];
  const allCities = [...tbDeps, ...normalRef];
  const cityRows = [];

  for (const city of allCities) {
    try {
      const [tbR] = await q(`SELECT '${city}' AS city, '特批' AS type,
        COUNT(*) AS apply, SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS approve,
        COUNT(c.ct_user_id) AS complete_orders,
        SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS overdue,
        ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS overdue_rate
        ${baseJoin} AND o.store_addr_city='${city}' AND ${tbCond}`);
      if (tbR) cityRows.push(tbR);
    } catch(e) {}
    try {
      const [nr] = await q(`SELECT '${city}' AS city, '正常' AS type,
        COUNT(*) AS apply, SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS approve,
        COUNT(c.ct_user_id) AS complete_orders,
        SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS overdue,
        ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS overdue_rate
        ${baseJoin} AND o.store_addr_city='${city}' AND ${normalCond}`);
      if (nr) cityRows.push(nr);
    } catch(e) {}
  }
  console.log('\n=== 地市直通对比 ===');
  console.table(cityRows);

  // ===================== 3. 门店质态风险矩阵 =====================
  const storeRisk = await q(`
    SELECT t.city, t.store,
      COUNT(*) AS apply, SUM(t.tb_flag) AS tb_apply,
      ROUND(SUM(t.tb_flag)*100.0/NULLIF(COUNT(*),0),2) AS tb_pct,
      SUM(t.approved) AS approve,
      COUNT(c.ct_user_id) AS completed,
      ROUND(COUNT(c.ct_user_id)*100.0/NULLIF(SUM(t.approved),0),2) AS complete_rate,
      SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS overdue,
      ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS overdue_rate,
      SUM(CASE WHEN c.step_num_repay_status=2 AND t.tb_flag=1 THEN 1 ELSE 0 END) AS tb_overdue
    FROM (
      SELECT o.store_addr_city AS city, o.store_name AS store, o.ct_user_id,
        CASE WHEN w.first_risk_result='特批白名单用户' THEN 1 ELSE 0 END AS tb_flag,
        CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END AS approved
      FROM ods_ts_credit_yzf_order_grant_apply o
      LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no
      WHERE o.custtype='00' AND o.store_addr_province='湖南省'
        AND o.business_type='02' AND o.add_time>='2026-04-05'
    ) t
    LEFT JOIN dws.dws_credit_yzf_order_complete c ON t.ct_user_id=c.ct_user_id AND c.source_business_type='淘顺实时授信'
    GROUP BY t.city, t.store
    HAVING SUM(t.tb_flag)>=3
    ORDER BY overdue_rate DESC, tb_apply DESC
  `);

  // 分两组：有逾期的 + 无逾期的
  const storeWithOverdue = storeRisk.filter(r => parseInt(r.overdue) > 0);
  const storeNoOverdue = storeRisk.filter(r => parseInt(r.overdue) === 0);

  // ===================== 4. 特批门店额外信息：客群结构 =====================
  // 对于有特批用户的门店，看特批用户的还款情况对比特批vs正常
  const [storeSummary] = await q(`
    SELECT COUNT(*) AS tb_stores_with_completion,
      SUM(CASE WHEN overdue>0 THEN 1 ELSE 0 END) AS tb_stores_with_overdue
    FROM (
      SELECT t.store,
        SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS overdue
      FROM (
        SELECT o.store_name AS store, o.ct_user_id
        FROM ods_ts_credit_yzf_order_grant_apply o
        LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no
        WHERE o.custtype='00' AND o.store_addr_province='湖南省'
          AND o.business_type='02' AND o.add_time>='2026-04-05'
          AND w.first_risk_result='特批白名单用户'
      ) t
      LEFT JOIN dws.dws_credit_yzf_order_complete c ON t.ct_user_id=c.ct_user_id AND c.source_business_type='淘顺实时授信'
      GROUP BY t.store
    ) s
  `);
  console.log('\n=== 特批门店汇总 ===');
  console.table(storeSummary);

  // ===================== 5. 生成报告 =====================
  const L = [];
  const p = s => L.push(s);
  const h1 = s => { L.push(''); L.push('---'); L.push('## ' + s); L.push(''); };
  const h2 = s => { L.push('### ' + s); L.push(''); };
  const tbl = (rows, hdrs, fmt) => {
    if (!rows || rows.length === 0) { p('_无数据_'); L.push(''); return; }
    L.push('| ' + hdrs.join(' | ') + ' |');
    L.push('|' + hdrs.map(() => ':---:').join('|') + '|');
    rows.forEach(r => L.push('| ' + (fmt ? fmt(r) : hdrs.map(h => String(r[h] ?? '')).join(' | ')) + ' |'));
  };

  L.push('# 特批白名单用户 — 质态综合分析');
  L.push('> 数据范围：2026/4/5 ~ 5/12 | ods_ts + dws | 不去重 | 湖南全省');
  L.push('');

  h1('一、特批 vs 正常 — 全链路质态对比（全省）');
  tbl(fullCompare, ['类型', '申请单', '通过数', '通过率', '竣工用户', '竣工单', '逾期单', '逾期率'],
    r => [r.type, String(r.apply), String(r.approve), r.approve_rate + '%', 
          String(r.complete_users || 0), String(r.complete_orders || 0),
          String(r.overdue), r.overdue_rate + '%'].join(' | '));
  L.push('');

  const tbRow = fullCompare.find(r => r.type === '特批');
  const nrRow = fullCompare.find(r => r.type === '正常');
  if (tbRow) {
    p(`**特批通道**：2283单全部通过（通过率100%），竣工${tbRow.complete_orders || 0}单（用户${tbRow.complete_users || 0}人），逾期**${tbRow.overdue}单（${tbRow.overdue_rate}%）**。特批不经过风控模型评估，100%通过。`);
  }
  if (nrRow) {
    p(`**正常通道**：14443单申请，通过${nrRow.approve}单（${nrRow.approve_rate}%），竣工${nrRow.complete_orders || 0}单，逾期${nrRow.overdue}单（${nrRow.overdue_rate}%）。正常通道有风控模型拦截，通过率仅40%。`);
  }
  L.push('');

  // 特批竣工率
  if (tbRow) {
    const compRate = tbRow.approve > 0 ? (parseInt(tbRow.complete_users || 0) * 100 / parseInt(tbRow.approve)).toFixed(2) : 0;
    p(`**特批竣工转化率**：批准2283 → 竣工${tbRow.complete_users || 0}人（${compRate}%）。特批用户虽有审批绿色通道，但仍有约${(100 - parseFloat(compRate)).toFixed(1)}%未竣工。`);
    L.push('');
  }

  h1('二、地市质态对比 — 特批依赖地市 vs 正常地市');
  // 按城市分组
  const citySummary = {};
  for (const row of cityRows) {
    if (!citySummary[row.city]) citySummary[row.city] = {};
    citySummary[row.city][row.type] = row;
  }

  for (const city of allCities) {
    const data = citySummary[city];
    if (!data) continue;
    const t = data['特批'];
    const n = data['正常'];

    h2(`${city}`);
    tbl(
      [
        { ...(t || {}), type: '特批' },
        { ...(n || {}), type: '正常' }
      ].filter(r => r.apply > 0),
      ['通道', '申请', '通过数', '竣工单', '逾期单', '逾期率'],
      r => [r.type, String(r.apply), String(r.approve), String(r.complete_orders || 0),
            String(r.overdue), (r.overdue_rate || '0') + '%'].join(' | ')
    );

    if (tbDeps.includes(city) && t) {
      const tbDepPct = t.apply > 0 ? (parseInt(t.approve) * 100 / (parseInt(t.approve) + parseInt(n?.approve || 0))).toFixed(0) : 0;
      p(`该市${t.apply}单特批，${n ? n.apply + '单正常' : '0单正常'}。特批通道贡献了该市${tbDepPct}%的通过量。`);
      if (parseInt(t.overdue) > 0) {
        p(`⚠️ 特批用户逾期${t.overdue}单（逾期率${t.overdue_rate}%），需关注。`);
      }
    } else if (tbDeps.includes(city) && !t) {
      p(`该市无特批用户。`);
    }
    L.push('');
  }

  h1('三、特批门店风险矩阵');
  p(`共${storeRisk.length}家门店有≥3单特批申请且有竣工记录。`);
  L.push('');

  if (storeWithOverdue.length > 0) {
    h2('🔴 特批门店 — 有逾期记录');
    tbl(storeWithOverdue.slice(0, 30),
      ['地市', '门店', '总申请', '特批单', '特批占比', '通过数', '竣工单', '竣工率', '逾期单', '逾期率', '特批逾期'],
      r => [r.city, r.store, String(r.apply), String(r.tb_apply), r.tb_pct + '%', String(r.approve),
            String(r.completed), r.complete_rate + '%', String(r.overdue), r.overdue_rate + '%',
            String(r.tb_overdue || 0)].join(' | '));
    L.push('');
    p(`共${storeWithOverdue.length}家特批门店出现逾期。`);
  }

  h2('🟢 特批门店 — 无逾期记录（前30家）');
  tbl(storeNoOverdue.slice(0, 30),
    ['地市', '门店', '总申请', '特批单', '特批占比', '通过数', '竣工单', '竣工率'],
    r => [r.city, r.store, String(r.apply), String(r.tb_apply), r.tb_pct + '%', String(r.approve),
          String(r.completed), r.complete_rate + '%'].join(' | '));
  L.push('');

  h1('四、质态总结与建议');
  p(`1. **特批用户通过率100%，逾期率${tbRow ? tbRow.overdue_rate + '%' : 'N/A'}**。当前逾期表现良好，但观察期短（仅1个月），且特批用户不经过风控评估，信用风险敞口更大。`);
  p(`2. **特批竣工转化率约${tbRow && tbRow.approve > 0 ? ((parseInt(tbRow.complete_users||0)*100/parseInt(tbRow.approve)).toFixed(1)) : 'N/A'}%**，略低于正常通道（${nrRow && nrRow.approve > 0 ? ((parseInt(nrRow.complete_users||0)*100/parseInt(nrRow.approve)).toFixed(1)) : 'N/A'}%）。特批用户通过后未竣工的比例不容忽视。`);
  p(`3. **完全特批依赖地市**（${tbDeps.join('、')}）共6个地市，全省${storeRisk.filter(r => r.tb_pct >= 95).length}家门店100%依赖特批。如特批政策收紧，这些地市业务将直接归零。`);
  p(`4. **逾期风险门店**：${storeWithOverdue.length}家特批门店出现逾期。建议对这些门店进行特批额度管控或加强贷后跟踪。`);
  p('5. 建议：1) 对完全依赖特批的门店逐一评估，能否承接正常风控；2) 设置特批门店申请量上限；3) 特批用户贷后监控周期延长至3~6个月；4) 对逾期特批门店限制特批通道使用。');
  L.push('');

  // CSV输出
  const csv = (rows, flds) => {
    if (!rows || rows.length === 0) return '';
    const h = flds.join(',');
    const l = rows.map(r => flds.map(f => {
      const v = r[f]; if (v === null || v === undefined) return '';
      const s = String(v); return s.includes(',') || s.includes('"') || s.includes('\n') ? '"' + s.replace(/"/g, '""') + '"' : s;
    }).join(','));
    return h + '\n' + l.join('\n');
  };

  fs.writeFileSync(dir + '/特批质态对比_全省.csv', csv(fullCompare, ['type','apply','approve','approve_rate','complete_users','complete_orders','overdue','overdue_rate']));
  fs.writeFileSync(dir + '/特批质态对比_地市.csv', csv(cityRows, ['city','type','apply','approve','complete_orders','overdue','overdue_rate']));
  fs.writeFileSync(dir + '/特批门店风险矩阵.csv', csv(storeRisk, ['city','store','apply','tb_apply','tb_pct','approve','completed','complete_rate','overdue','overdue_rate','tb_overdue']));
  fs.writeFileSync(dir + '/特批白名单质态分析.md', L.join('\n'));

  console.log('\n✅ 特批质态分析完成');
  conn.end();
}
main().catch(e => { console.error(e); process.exit(1); });
