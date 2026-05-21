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

  const storeDefs = [
    { n: "飞鸿@长沙市商圈飞鸿梅溪湖店",            g: "飞鸿" },
    { n: "飞鸿电子@市社引商入店飞鸿电子信息公司荷花园厅", g: "飞鸿" },
    { n: "飞鸿@长沙市商圈飞鸿万家丽华为专营店",     g: "飞鸿" },
    { n: "湖南飞鸿@娄底市飞鸿长青旗舰店",           g: "飞鸿" },
    { n: "嘉禾普满@嘉禾县普满乡飞鸿电信营业厅",     g: "飞鸿" },
    { n: "时祺@长沙市岳麓时祺湘桥佳苑专营店",       g: "时祺" },
    { n: "米琪@湖南宇祺科技有限责任公司宁乡米琪店", g: "时祺" }
  ];
  const esc = s => "'" + s.replace(/'/g, "\\'") + "'";

  // ===== 1. 门店综合 =====
  const allData = [];
  for (const st of storeDefs) {
    const r = await q(`SELECT o.store_name AS s, o.store_addr_city AS c,
      COUNT(*) AS a, SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS ap,
      COUNT(cw.ct_user_id) AS co,
      SUM(CASE WHEN cw.step_num_repay_status=2 THEN 1 ELSE 0 END) AS ov,
      ROUND(AVG(o.order_amt/100),0) AS amt,
      SUM(CASE WHEN w.first_risk_result='特批白名单用户' THEN 1 ELSE 0 END) AS tb,
      MIN(o.add_time) AS f, MAX(o.add_time) AS l
      FROM ods_ts_credit_yzf_order_grant_apply o
      LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no
      LEFT JOIN dws.dws_credit_yzf_order_complete cw ON o.ct_user_id=cw.ct_user_id AND cw.source_business_type='淘顺实时授信'
      WHERE ${cond} AND o.store_name=${esc(st.n)} GROUP BY o.store_name, o.store_addr_city`);
    if (r && r.length > 0 && parseInt(r[0].a) > 0) allData.push({ ...r[0], g: st.g });
  }

  // 计算派生指标
  for (const d of allData) {
    d.apr = d.a > 0 ? (parseInt(d.ap)*100/parseInt(d.a)).toFixed(1) : '0.0';
    d.ovr = parseInt(d.co) > 0 ? (parseInt(d.ov)*100/parseInt(d.co)).toFixed(2) : '0.00';
    d.tb_pct = parseInt(d.a) > 0 && parseInt(d.tb) > 0 ? (parseInt(d.tb)*100/parseInt(d.a)).toFixed(0)+'%' : '无';
  }

  // 按商户汇总
  const fhData = allData.filter(d => d.g === '飞鸿');
  const sqData = allData.filter(d => d.g === '时祺');
  const sum = (arr) => arr.reduce((s, d) => ({ a: s.a+parseInt(d.a), ap: s.ap+parseInt(d.ap), co: s.co+parseInt(d.co||0), ov: s.ov+parseInt(d.ov||0), amt: s.amt+parseInt(d.amt||0)*(parseInt(d.ap)) }), {a:0,ap:0,co:0,ov:0,amt:0});
  const fhSum = sum(fhData);
  const sqSum = sum(sqData);

  console.log('=== 门店综合质态+单价 ===');
  console.table(allData);

  // ===== 2. 单价分布 =====
  for (const [gName, stores] of [['飞鸿', fhData], ['时祺+米琪', sqData]]) {
    const names = stores.map(s => esc(s.s));
    if (names.length === 0) continue;
    const namesList = names.join(',');
    const priceRanges = await q(`SELECT 
      CASE WHEN o.order_amt/100<1000 THEN '<1000'
           WHEN o.order_amt/100<2000 THEN '1000~2000'
           WHEN o.order_amt/100<3000 THEN '2000~3000'
           WHEN o.order_amt/100<5000 THEN '3000~5000'
           ELSE '5000+' END AS rng,
      COUNT(*) AS a, SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS ap
      FROM ods_ts_credit_yzf_order_grant_apply o
      WHERE ${cond} AND o.store_name IN (${namesList}) AND o.order_amt IS NOT NULL
      GROUP BY rng ORDER BY rng`);
    console.log(`\n=== ${gName} 单价分布 ===`);
    if (priceRanges && priceRanges.length > 0) {
      console.table(priceRanges);
    }
  }

  // ===== 3. 月趋势（飞鸿合计） =====
  const fhNames = fhData.map(s => esc(s.s)).join(',');
  const fhM = await q(`SELECT date_format(o.add_time,'%Y-%m') AS m, o.store_name AS s,
    COUNT(*) AS a, SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS ap,
    ROUND(AVG(o.order_amt/100),0) AS amt,
    COUNT(cw.ct_user_id) AS co,
    SUM(CASE WHEN cw.step_num_repay_status=2 THEN 1 ELSE 0 END) AS ov
    FROM ods_ts_credit_yzf_order_grant_apply o
    LEFT JOIN dws.dws_credit_yzf_order_complete cw ON o.ct_user_id=cw.ct_user_id AND cw.source_business_type='淘顺实时授信'
    WHERE ${cond} AND o.store_name IN (${fhNames})
    GROUP BY m, s ORDER BY m, s`);
  console.log(`\n=== 飞鸿各门店月趋势 ===`);
  console.table(fhM);

  // ===== 4. 生成报告 =====
  const L = [];
  const p = s => L.push(s);
  const h1 = s => { L.push(''); L.push('---'); L.push('## ' + s); L.push(''); };
  const h2 = s => { L.push('### ' + s); L.push(''); };
  const tbl = (rows, hdrs, fmt) => {
    if (!rows||rows.length===0) { p('_无数据_'); L.push(''); return; }
    L.push('| ' + hdrs.join(' | ') + ' |');
    L.push('|' + hdrs.map(() => ':---:').join('|') + '|');
    rows.forEach(r => L.push('| ' + (fmt(r)) + ' |'));
  };

  L.push('# 商户质态综合分析');
  L.push('## 湖南飞鸿电子信息有限公司 & 湖南时祺科技有限公司（含前身米琪）');
  L.push('> 全量历史 | ods_ts + dws | 通过率/逾期率/竣工/均价/特批');
  L.push('');

  h1('一、商户汇总');

  // 飞鸿汇总
  p(`**湖南飞鸿电子信息有限公司**`);
  p(`- ${fhData.length}家门店，合计申请${fhSum.a}单，通过${fhSum.ap}单（**${(fhSum.ap*100/fhSum.a).toFixed(1)}%**），竣工${fhSum.co}单，逾期${fhSum.ov}单（**${fhSum.co ? (fhSum.ov*100/fhSum.co).toFixed(2) : 0}%**），加权均价**${fhSum.ap ? Math.round(fhSum.amt/fhSum.ap) : 0}元**。`);
  L.push('');

  p(`**湖南时祺科技有限公司（含米琪）**`);
  p(`- ${sqData.length}家门店，合计申请${sqSum.a}单，通过${sqSum.ap}单（**${sqSum.a ? (sqSum.ap*100/sqSum.a).toFixed(1) : 0}%**），竣工${sqSum.co}单，逾期${sqSum.ov}单（**${sqSum.co ? (sqSum.ov*100/sqSum.co).toFixed(2) : 0}%**）。`);
  L.push('');

  h1('二、门店质态全览');
  tbl(allData, ['门店', '地市', '申请', '通过', '通过率', '竣工', '逾期', '逾期率', '均价(元)', '特批', '运营期'],
    r => [r.s, r.c, String(r.a), String(r.ap), r.apr+'%', String(r.co||0), String(r.ov||0), r.ovr+'%',
          r.amt ? String(r.amt) : '-', r.tb_pct,
          String(r.f).substring(0,10)+'~'+String(r.l).substring(0,10)].join(' | '));
  L.push('');

  h1('三、门店质态评级');
  tbl(allData, ['门店', '评级'],
    r => {
      const ovr = parseFloat(r.ovr||0);
      const tbPct = parseInt(r.tb||0) * 100 / parseInt(r.a);
      let rate;
      if (tbPct >= 90) rate = '⚠️ 特批依赖（100%通过特批，0逾期）';
      else if (ovr >= 20) rate = '🔴 高危（逾期率'+r.ovr+'%）';
      else if (ovr >= 10) rate = '🟡 关注（逾期率'+r.ovr+'%）';
      else if (ovr >= 5) rate = '🔵 一般（逾期率'+r.ovr+'%）';
      else rate = '🟢 健康（逾期率'+r.ovr+'%）';
      return [r.s, rate].join(' | ');
    });
  L.push('');

  h1('四、单价分布');
  for (const [gName, stores] of [['飞鸿', fhData], ['时祺+米琪', sqData]]) {
    if (stores.length === 0) continue;
    h2(gName);
    const names = stores.map(s => esc(s.s)).join(',');
    const pr = await q(`SELECT CASE WHEN o.order_amt/100<1000 THEN '<1000元' WHEN o.order_amt/100<2000 THEN '1000~2000' WHEN o.order_amt/100<3000 THEN '2000~3000' WHEN o.order_amt/100<5000 THEN '3000~5000' ELSE '5000+' END AS rng,
      COUNT(*) AS a, SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS ap,
      ROUND(SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),1) AS apr
      FROM ods_ts_credit_yzf_order_grant_apply o WHERE ${cond} AND o.store_name IN (${names}) AND o.order_amt IS NOT NULL
      GROUP BY rng ORDER BY rng`);
    if (pr && pr.length > 0) {
      tbl(pr, ['价格区间', '申请', '通过', '通过率'], r => [r.rng, String(r.a), String(r.ap), r.apr+'%'].join(' | '));
      // 主力区间
      const max = pr.reduce((a,b) => parseInt(a.a) > parseInt(b.a) ? a : b);
      p(`**主力区间**：${max.rng}（${max.a}单，占${(parseInt(max.a)*100/pr.reduce((s,r)=>s+parseInt(r.a),0)).toFixed(0)}%），通过率${max.apr}%。`);
      L.push('');
    }
  }

  h1('五、飞鸿各门店月趋势（含逾期率+均价）');
  if (fhM && fhM.length > 0) {
    tbl(fhM, ['月份', '门店', '申请', '通过', '均价(元)', '竣工', '逾期', '逾期率'],
      r => [r.m, r.s, String(r.a), String(r.ap), String(r.amt||'-'), String(r.co||0), String(r.ov||0),
            parseInt(r.co) > 0 ? (parseInt(r.ov)*100/parseInt(r.co)).toFixed(2)+'%' : '-'].join(' | '));
  }
  L.push('');

  h1('六、结论与建议');
  // 红黑榜
  const sorted = [...allData].sort((a,b) => parseFloat(b.ovr) - parseFloat(a.ovr));
  p(`**🔴 最差门店**：${sorted[0].s} — 逾期率${sorted[0].ovr}%，通过率${sorted[0].apr}%，均价${sorted[0].amt||'-'}元。`);
  const best = [...allData].filter(d => parseInt(d.co||0) > 0).sort((a,b) => parseFloat(a.ovr) - parseFloat(b.ovr));
  if (best.length > 0) p(`**🟢 最佳门店**：${best[0].s} — 逾期率${best[0].ovr}%，通过率${best[0].apr}%。`);

  // 关键对比
  const meixihu = allData.find(d => d.s.includes('梅溪湖'));
  const hehuating = allData.find(d => d.s.includes('荷花园'));
  if (meixihu && hehuating) {
    L.push('');
    p(`**同商户极端分化**：飞鸿名下两店`);
    p(`- 梅溪湖店：通过率${meixihu.apr}%，逾期率**${meixihu.ovr}%**，均价${meixihu.amt}元`);
    p(`- 荷花园厅：通过率${hehuating.apr}%，逾期率**${hehuating.ovr}%**，均价${hehuating.amt}元`);
    p(`  → 建议了解两店客群差异（进件渠道、客户来源、导购操作模式）。`);
  }

  const loudi = allData.find(d => d.s.includes('娄底'));
  if (loudi) {
    L.push('');
    p(`**⚠️ 娄底飞鸿长青旗舰店**：30单全部100%特批通过，逾期率0%。典型特批依赖门店，需持续关注。`);
  }

  L.push('');
  L.push('---');
  p(`*报告生成时间：${new Date().toLocaleString('zh-CN', {timeZone:'Asia/Shanghai'})}*`);

  // CSV
  const csv = (rows, flds) => {
    if (!rows||rows.length===0) return '';
    const h = flds.join(','); const l = rows.map(r => flds.map(f => {const v=r[f]; if(v===null||v===undefined) return ''; const s=String(v); return s.includes(',')||s.includes('"')||s.includes('\n')?'"'+s.replace(/"/g,'""')+'"':s;}).join(','));
    return h+'\n'+l.join('\n');
  };

  fs.writeFileSync(dir+'/商户飞鸿时祺_综合分析.csv', csv(allData, ['s','c','a','ap','apr','co','ov','ovr','amt','tb','tb_pct']));
  fs.writeFileSync(dir+'/商户飞鸿时祺_综合分析.md', L.join('\n'));

  console.log('\n✅ 综合分析完成');
  conn.end();
}
main().catch(e => { console.error(e); process.exit(1); });
