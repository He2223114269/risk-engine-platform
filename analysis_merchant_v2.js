const mysql = require('mysql2/promise');
const fs = require('fs');

async function main() {
  const conn = await mysql.createConnection({
    host: '47.119.181.195', port: 9030, user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)", database: 'ods',
  });
  const q = async (sql) => { const [r] = await conn.query(sql); return r; };

  const dir = '/mnt/d/desktop/翼支付交流_门店代理商分析';
  const cond = "o.custtype='00' AND o.store_addr_province='湖南省' AND o.business_type='02'";
  const dws  = "LEFT JOIN dws.dws_credit_yzf_order_complete c ON o.ct_user_id=c.ct_user_id AND c.source_business_type='淘顺实时授信'";

  // 门店列表
  const storeList = [
    { name: "飞鸿@长沙市商圈飞鸿梅溪湖店",            group: "飞鸿" },
    { name: "飞鸿电子@市社引商入店飞鸿电子信息公司荷花园厅", group: "飞鸿" },
    { name: "飞鸿@长沙市商圈飞鸿万家丽华为专营店",     group: "飞鸿" },
    { name: "湖南飞鸿@娄底市飞鸿长青旗舰店",           group: "飞鸿" },
    { name: "嘉禾普满@嘉禾县普满乡飞鸿电信营业厅",     group: "飞鸿" },
    { name: "时祺@长沙市岳麓时祺湘桥佳苑专营店",       group: "时祺" },
    { name: "米琪@湖南宇祺科技有限责任公司宁乡米琪店", group: "时祺" }
  ];

  const storeNames = storeList.map(s => "'" + s.name.replace(/'/g, "\\'") + "'");

  // ==================== 1. 门店综合质态 + 单价 ====================
  const allData = [];
  for (const st of storeList) {
    const name = st.name;
    const rows = await q(`SELECT o.store_name AS store, o.store_addr_city AS city,
      COUNT(*) AS apply,
      SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS approve,
      ROUND(SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),2) AS approve_rate,
      COUNT(c.ct_user_id) AS completed,
      SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS overdue,
      ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS overdue_rate,
      ROUND(AVG(o.order_amt/100), 0) AS avg_order_amt_yuan,
      ROUND(AVG(c.service_fee_yuan), 2) AS avg_fee_yuan,
      SUM(CASE WHEN w.first_risk_result='特批白名单用户' THEN 1 ELSE 0 END) AS tb_apply,
      MIN(o.add_time) AS first_app,
      MAX(o.add_time) AS last_app
      FROM ods_ts_credit_yzf_order_grant_apply o
      LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no
      ${dws}
      WHERE ${cond} AND o.store_name='${name}'
      GROUP BY o.store_name, o.store_addr_city`);
    if (rows && rows.length > 0) allData.push(rows[0]);
  }

  console.log('=== 综合质态+单价 ===');
  console.table(allData);

  // ==================== 2. 飞鸿vs时祺 商户总计 ====================
  const nameListAll = storeNames.join(',');
  const [merchantSummary] = await q(`
    SELECT CASE WHEN o.store_name IN (${storeNames.slice(0,5).join(',')}) THEN '飞鸿' ELSE '时祺+米琪' END AS merchant,
      COUNT(*) AS apply,
      SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS approve,
      ROUND(SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),2) AS approve_rate,
      COUNT(c.ct_user_id) AS completed,
      SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS overdue,
      ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS overdue_rate,
      ROUND(AVG(o.order_amt/100), 0) AS avg_order_amt,
      ROUND(AVG(c.service_fee_yuan), 2) AS avg_fee
    FROM ods_ts_credit_yzf_order_grant_apply o
    LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no
    ${dws}
    WHERE ${cond} AND o.store_name IN (${nameListAll})
    GROUP BY merchant
  `);
  console.log('\n=== 商户汇总 ===');
  console.table(merchantSummary);

  // ==================== 3. 单价分布（各价格带申请量）====================
  const [priceDist] = await q(`
    SELECT CASE WHEN o.store_name IN (${storeNames.slice(0,5).join(',')}) THEN '飞鸿' ELSE '时祺+米琪' END AS merchant,
      CASE 
        WHEN o.order_amt/100 < 1000 THEN '<1000元'
        WHEN o.order_amt/100 < 2000 THEN '1000~2000'
        WHEN o.order_amt/100 < 3000 THEN '2000~3000'
        WHEN o.order_amt/100 < 5000 THEN '3000~5000'
        ELSE '5000+'
      END AS price_range,
      COUNT(*) AS apply,
      SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS approve,
      ROUND(SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),2) AS approve_rate
    FROM ods_ts_credit_yzf_order_grant_apply o
    WHERE ${cond} AND o.store_name IN (${nameListAll}) AND o.order_amt IS NOT NULL
    GROUP BY merchant, price_range
    ORDER BY merchant, price_range
  `);
  console.log('\n=== 单价分布 ===');
  console.table(priceDist);

  // ==================== 4. 飞鸿各门店月趋势（含单价）====================
  const monthlyFeihong = [];
  const fhNames = storeNames.slice(0,5).join(',');
  const fhMonths = await q(`SELECT date_format(o.add_time,'%Y-%m') AS month, o.store_name AS store,
    COUNT(*) AS apply,
    SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS approve,
    ROUND(AVG(o.order_amt/100), 0) AS avg_amt,
    COUNT(c.ct_user_id) AS completed,
    SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS overdue,
    ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS overdue_rate
    FROM ods_ts_credit_yzf_order_grant_apply o
    LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no
    ${dws}
    WHERE ${cond} AND o.store_name IN (${fhNames})
    GROUP BY month, store
    ORDER BY month, store`);
  console.log('\n=== 飞鸿各门店月趋势 ===');
  console.table(fhMonths);

  // ==================== 5. 生成报告 ====================
  const L = [];
  const p = s => L.push(s);
  const h1 = s => { L.push(''); L.push('---'); L.push('## ' + s); L.push(''); };
  const h2 = s => { L.push('### ' + s); L.push(''); };
  const tbl = (rows, hdrs, fmt) => {
    if (!rows||rows.length===0) { p('_无数据_'); L.push(''); return; }
    L.push('| ' + hdrs.join(' | ') + ' |');
    L.push('|' + hdrs.map(() => ':---:').join('|') + '|');
    rows.forEach(r => L.push('| ' + (fmt ? fmt(r) : hdrs.map(h => String(r[h] ?? '')).join(' | ')) + ' |'));
  };

  L.push('# 商户质态综合分析');
  L.push('## 湖南飞鸿电子信息有限公司 & 湖南时祺科技有限公司（含前身米琪）');
  L.push('> 全量历史 | ods_ts + dws | 已含 通过率/逾期率/竣工/单价/特批');
  L.push('');

  h1('一、商户汇总');
  if (merchantSummary && merchantSummary.length > 0) {
    tbl(merchantSummary, ['商户', '申请', '通过数', '通过率', '竣工', '逾期', '逾期率', '均价(元)', '均服务费(元)'],
      r => [r.merchant, String(r.apply), String(r.approve), r.approve_rate+'%', String(r.completed||0),
            String(r.overdue||0), (r.overdue_rate||'0')+'%',
            r.avg_order_amt ? String(r.avg_order_amt) : '-', r.avg_fee ? String(r.avg_fee) : '-'].join(' | '));
    L.push('');
    const fh = merchantSummary.find(r => r.merchant === '飞鸿');
    const sq = merchantSummary.find(r => r.merchant === '时祺+米琪');
    if (fh) p(`**飞鸿**：${fh.apply}单，通过率${fh.approve_rate}%，逾期率${fh.overdue_rate||'0'}%，均价${fh.avg_order_amt||'-'}元。`);
    if (sq) p(`**时祺+米琪**：${sq.apply}单，通过率${sq.approve_rate}%，逾期率${sq.overdue_rate||'0'}%，均价${sq.avg_order_amt||'-'}元。`);
  }
  L.push('');

  h1('二、门店质态全览（含逾期率+单价+特批）');
  tbl(allData, ['门店', '地市', '申请', '通过', '通过率', '竣工', '逾期', '逾期率', '均价(元)', '均服务费', '特批', '运营期'],
    r => [r.store, r.city, String(r.apply), String(r.approve), r.approve_rate+'%', String(r.completed||0),
          String(r.overdue||0), (r.overdue_rate||'0')+'%',
          r.avg_order_amt_yuan ? String(r.avg_order_amt_yuan) : '-',
          r.avg_fee_yuan ? String(r.avg_fee_yuan) : '-',
          (r.tb_apply||0) > 0 ? r.tb_apply+'单('+((r.tb_apply*100/r.apply).toFixed(0))+'%)' : '无',
          String(r.first_app).substring(0,10)+'~'+String(r.last_app).substring(0,10)].join(' | '));
  L.push('');

  h1('三、单价分布');
  if (priceDist && priceDist.length > 0) {
    tbl(priceDist, ['商户', '价格区间', '申请', '通过', '通过率'],
      r => [r.merchant, r.price_range, String(r.apply), String(r.approve), r.approve_rate+'%'].join(' | '));
    L.push('');
  }

  // 单价区间分析
  for (const merchant of ['飞鸿', '时祺+米琪']) {
    const rows = (priceDist||[]).filter(r => r.merchant === merchant);
    if (rows.length === 0) continue;
    const max = rows.reduce((a, b) => parseInt(a.apply) > parseInt(b.apply) ? a : b);
    p(`**${merchant}**：主力价格区间为**${max.price_range}**（${max.apply}单，通过率${max.approve_rate}%）。`);
    const highest = rows.reduce((a, b) => parseFloat(a.approve_rate) > parseFloat(b.approve_rate) ? a : b);
    p(`  通过率最高的价格区间：**${highest.price_range}**（${highest.approve_rate}%）。`);
  }
  L.push('');

  h1('四、门店质态评级');
  // 按逾期率+通过率分级
  const ratings = [];
  for (const d of allData) {
    const or = parseFloat(d.overdue_rate||0);
    const ar = parseFloat(d.approve_rate||0);
    const tbPct = d.tb_apply > 0 ? d.tb_apply * 100 / d.apply : 0;
    let rating, color;
    if (tbPct >= 90) { rating = '⚠️ 特批依赖'; color = 'yellow'; }
    else if (or >= 20) { rating = '🔴 高危'; color = 'red'; }
    else if (or >= 10) { rating = '🟡 关注'; color = 'yellow'; }
    else if (or >= 5) { rating = '🔵 一般'; color = 'blue'; }
    else { rating = '🟢 健康'; color = 'green'; }
    ratings.push({ store: d.store, rating, overdue_rate: d.overdue_rate, approve_rate: d.approve_rate });
  }
  tbl(ratings, ['门店', '评级', '逾期率', '通过率'],
    r => [r.store, r.rating, r.overdue_rate+'%', r.approve_rate+'%'].join(' | '));
  L.push('');

  h1('五、结论与建议');
  // 按商户
  p('### 湖南飞鸿电子信息有限公司');
  const fhData = allData.filter(d => d.store.includes('飞鸿') || d.store.includes('嘉禾'));
  const fhTotal = { a:0, p:0, c:0, o:0 };
  for (const d of fhData) { fhTotal.a += parseInt(d.apply); fhTotal.p += parseInt(d.approve); fhTotal.c += parseInt(d.completed||0); fhTotal.o += parseInt(d.overdue||0); }
  p(`共${fhData.length}家门店，合计${fhTotal.a}单，通过${fhTotal.p}单（${(fhTotal.p*100/fhTotal.a).toFixed(1)}%），竣工${fhTotal.c}单，逾期${fhTotal.o}单（${fhTotal.c ? (fhTotal.o*100/fhTotal.c).toFixed(2) : 0}%）。`);

  // 红黑榜
  const worst = [...allData].filter(d => d.store.includes('飞鸿')||d.store.includes('嘉禾')).sort((a,b) => parseFloat(b.overdue_rate||0) - parseFloat(a.overdue_rate||0));
  if (worst.length > 0) {
    const w = worst[0], b = worst[worst.length-1];
    p(`🔴 **最差门店**：${w.store} — 逾期率${w.overdue_rate}%，通过率${w.approve_rate}%，均价${w.avg_order_amt_yuan||'-'}元。`);
    p(`🟢 **最佳门店**：${b.store} — 逾期率${b.overdue_rate}%，通过率${b.approve_rate}%，均价${b.avg_order_amt_yuan||'-'}元。`);
  }
  L.push('');

  p('### 湖南时祺科技有限公司（含米琪）');
  const sqData = allData.filter(d => d.store.includes('时祺') || d.store.includes('米琪'));
  const sqTotal = { a:0, p:0, c:0, o:0 };
  for (const d of sqData) { sqTotal.a += parseInt(d.apply); sqTotal.p += parseInt(d.approve); sqTotal.c += parseInt(d.completed||0); sqTotal.o += parseInt(d.overdue||0); }
  p(`共${sqData.length}家门店，合计${sqTotal.a}单，通过${sqTotal.p}单（${sqTotal.a?(sqTotal.p*100/sqTotal.a).toFixed(1):0}%），竣工${sqTotal.c}单，逾期${sqTotal.o}单（${sqTotal.c?(sqTotal.o*100/sqTotal.c).toFixed(2):0}%）。`);
  const sqWorst = sqData.filter(d => parseFloat(d.overdue_rate||0) > 0);
  if (sqWorst.length > 0) p(`🔴 逾期门店：${sqWorst.map(d => d.store+'('+d.overdue_rate+'%)').join('、')}。`);
  else p('🟢 所有门店当前逾期率为0，但观察期较短（时祺仅运营1个月）。');
  L.push('');

  p('### 综合建议');
  p('1. **飞鸿梅溪湖店**逾期率44.53%为最高风险门店，虽然近期改善但历史包袱重，建议：1) 降额控制；2) 加强进件审核；3) 贷后跟踪频率提高。');
  p('2. **娄底飞鸿长青旗舰店**100%特批，虽然当前无逾期，但特批依赖风险需持续关注。');
  p('3. **时祺**运营时间短（1个月），通过率27%偏低，建议观察3个月后再做评估。');
  p('4. 飞鸿梅溪湖店（26.9%通过率+44.5%逾期率）vs 飞鸿荷花园厅（45.7%通过率+3.2%逾期率）同为飞鸿名下门店，质量差异巨大，建议了解两店客群差异。');
  L.push('');

  // CSV
  const csv = (rows, flds) => {
    if (!rows||rows.length===0) return '';
    const h = flds.join(','); const l = rows.map(r => flds.map(f => {const v=r[f]; if(v===null||v===undefined) return ''; const s=String(v); return s.includes(',')||s.includes('"')||s.includes('\n')?'"'+s.replace(/"/g,'""')+'"':s;}).join(','));
    return h+'\n'+l.join('\n');
  };
  fs.writeFileSync(dir+'/商户飞鸿时祺_综合质态.csv', csv(allData, ['store','city','apply','approve','approve_rate','completed','overdue','overdue_rate','avg_order_amt_yuan','avg_fee_yuan','tb_apply','first_app','last_app']));
  fs.writeFileSync(dir+'/商户飞鸿时祺_单价分布.csv', csv(priceDist, ['merchant','price_range','apply','approve','approve_rate']));
  fs.writeFileSync(dir+'/商户飞鸿时祺_综合分析.md', L.join('\n'));

  console.log('\n✅ 综合分析完成');
  conn.end();
}
main().catch(e => { console.error(e); process.exit(1); });
