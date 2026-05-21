const mysql = require('mysql2/promise');
const fs = require('fs');

async function main() {
  const conn = await mysql.createConnection({
    host: '47.119.181.195', port: 9030, user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)", database: 'ods',
  });
  const q = async (sql) => { const [r] = await conn.query(sql); return r; };

  const dir = '/mnt/d/desktop/翼支付交流_门店代理商分析';

  // 飞鸿系列门店（逐店查询，避开StarRocks GROUP BY坑）
  const feihongPatterns = [
    '%飞鸿@%梅溪湖%',
    '%飞鸿电子%@%荷花园%',
    '%飞鸿@%万家丽%',
    '%飞鸿@%长青%',
    '嘉禾%飞鸿%',
  ];
  const feihongStores = [];

  for (const pat of feihongPatterns) {
    const rows = await q(`SELECT store_name, store_addr_city AS city,
      COUNT(*) AS apply,
      SUM(CASE WHEN apply_status='授信成功' THEN 1 ELSE 0 END) AS approve,
      ROUND(SUM(CASE WHEN apply_status='授信成功' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),2) AS approve_rate,
      MIN(add_time) AS first_app,
      MAX(add_time) AS last_app
      FROM ods_ts_credit_yzf_order_grant_apply
      WHERE custtype='00' AND store_addr_province='湖南省' AND business_type='02'
        AND store_name LIKE '${pat}' GROUP BY store_name, store_addr_city`);
    if (rows && rows.length > 0 && parseInt(rows[0].apply) > 0) {
      feihongStores.push(rows[0]);
    }
  }

  // 时祺+米琪
  const shiqiStores = [];
  const sqPatterns = ['%时祺%', '%米琪%'];
  for (const pat of sqPatterns) {
    const rows = await q(`SELECT store_name, store_addr_city AS city,
      COUNT(*) AS apply,
      SUM(CASE WHEN apply_status='授信成功' THEN 1 ELSE 0 END) AS approve,
      ROUND(SUM(CASE WHEN apply_status='授信成功' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),2) AS approve_rate,
      MIN(add_time) AS first_app,
      MAX(add_time) AS last_app
      FROM ods_ts_credit_yzf_order_grant_apply
      WHERE custtype='00' AND store_addr_province='湖南省' AND business_type='02'
        AND store_name LIKE '${pat}' GROUP BY store_name, store_addr_city`);
    if (rows && rows.length > 0 && parseInt(rows[0].apply) > 0) {
      shiqiStores.push(rows[0]);
    }
  }

  // 汇总
  const allStores = [...feihongStores, ...shiqiStores];
  console.log('=== 门店列表 ===');
  console.table(allStores);

  // ========== 质态分析（全量历史）==========
  const dws = "LEFT JOIN dws.dws_credit_yzf_order_complete c ON o.ct_user_id=c.ct_user_id AND c.source_business_type='淘顺实时授信'";
  const baseWhere = "o.custtype='00' AND o.store_addr_province='湖南省' AND o.business_type='02'";

  // 各家门店全量质态
  const storeQuality = [];
  for (const st of allStores) {
    const name = st.store_name;
    const rows = await q(`SELECT '${name}' AS store,
      COUNT(*) AS apply,
      SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS approve,
      ROUND(SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),2) AS approve_rate,
      COUNT(c.ct_user_id) AS completed,
      SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS overdue,
      ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS overdue_rate
      FROM ods_ts_credit_yzf_order_grant_apply o
      ${dws}
      WHERE ${baseWhere} AND o.store_name='${name}'`);
    if (rows && rows.length > 0) storeQuality.push(rows[0]);
  }
  console.log('\n=== 质态数据 ===');
  console.table(storeQuality);

  // ========== 特批情况 ==========
  const tbData = [];
  for (const st of allStores) {
    const name = st.store_name;
    const rows = await q(`SELECT '${name}' AS store,
      COUNT(*) AS apply,
      SUM(CASE WHEN w.first_risk_result='特批白名单用户' THEN 1 ELSE 0 END) AS tb_apply,
      ROUND(SUM(CASE WHEN w.first_risk_result='特批白名单用户' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),2) AS tb_pct
      FROM ods_ts_credit_yzf_order_grant_apply o
      LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no
      WHERE ${baseWhere} AND o.store_name='${name}'`);
    if (rows && rows.length > 0) tbData.push(rows[0]);
  }
  console.log('\n=== 特批情况 ===');
  console.table(tbData);

  // ========== 按月趋势 ==========
  // 飞鸿+时祺分别合计
  const feihongNames = feihongStores.map(s => s.store_name);
  const shiqiNames  = shiqiStores.map(s => s.store_name);

  for (const [groupName, names] of [['飞鸿', feihongNames], ['时祺+米琪', shiqiNames]]) {
    if (names.length === 0) continue;
    const nameList = names.map(n => "'" + n.replace(/'/g, "\\'") + "'").join(',');
    const rows = await q(`SELECT date_format(o.add_time,'%Y-%m') AS month, '${groupName}' AS grp,
      COUNT(*) AS apply,
      SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS approve,
      ROUND(SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),2) AS approve_rate,
      COUNT(c.ct_user_id) AS completed,
      SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS overdue,
      ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS overdue_rate
      FROM ods_ts_credit_yzf_order_grant_apply o ${dws}
      WHERE ${baseWhere} AND o.store_name IN (${nameList})
      GROUP BY month ORDER BY month`);
    console.log(`\n=== ${groupName} 按月走势 ===`);
    if (rows && rows.length > 0) console.table(rows);
  }

  // ========== 申请状态分布（拒绝原因）===========
  for (const [groupName, names] of [['飞鸿', feihongNames], ['时祺+米琪', shiqiNames]]) {
    if (names.length === 0) continue;
    const nameList = names.map(n => "'" + n.replace(/'/g, "\\'") + "'").join(',');
    const rows = await q(`SELECT o.apply_msg AS reason,
      COUNT(*) AS cnt,
      ROUND(COUNT(*)*100.0/SUM(COUNT(*)) OVER(),2) AS pct
      FROM ods_ts_credit_yzf_order_grant_apply o
      WHERE ${baseWhere} AND o.store_name IN (${nameList})
        AND o.apply_status != '授信成功'
      GROUP BY o.apply_msg ORDER BY cnt DESC LIMIT 10`);
    console.log(`\n=== ${groupName} 拒绝原因 ===`);
    if (rows && rows.length > 0) console.table(rows);
  }

  // ========== 生成报告 ==========
  const L = [];
  const p = s => L.push(s);
  const h1 = s => { L.push(''); L.push('---'); L.push('## ' + s); L.push(''); };
  const h2 = s => { L.push('### ' + s); L.push(''); };
  const tbl = (rows, hdrs, fmt) => {
    if (!rows||rows.length===0) { p('_无数据_'); L.push(''); return; }
    L.push('| '+hdrs.join(' | ')+' |');
    L.push('|'+hdrs.map(()=>':---:').join('|')+'|');
    rows.forEach(r => L.push('| '+(fmt?fmt(r):hdrs.map(h=>String(r[h]??'')).join(' | '))+' |'));
  };

  L.push('# 商户质态分析报告');
  L.push('## 湖南飞鸿电子信息有限公司 & 湖南时祺科技有限公司（含前身米琪）');
  L.push('> 全量历史数据 | 不去重 | 湖南全省 | ods_ts + dws');
  L.push('');

  // 商户概览
  L.push('---');
  L.push('## 一、商户与门店概览');
  L.push('');

  p('### 湖南飞鸿电子信息有限公司');
  tbl(feihongStores, ['门店', '地市', '申请量', '通过数', '通过率', '首单', '末单'],
    r => [r.store_name, r.city, String(r.apply||0), String(r.approve||0), (r.approve_rate||'0')+'%',
          r.first_app ? String(r.first_app).slice(0,10) : '-', r.last_app ? String(r.last_app).slice(0,10) : '-'].join(' | '));
  const fTotal = feihongStores.reduce((s,r) => ({a: s.a+parseInt(r.apply||0), p: s.p+parseInt(r.approve||0)}), {a:0,p:0});
  p(`**飞鸿合计**：${fTotal.a}单申请，${fTotal.p}单通过，综合通过率**${fTotal.a ? (fTotal.p*100/fTotal.a).toFixed(2) : 0}%**。`);
  L.push('');

  p('### 湖南时祺科技有限公司（含前身米琪）');
  tbl(shiqiStores, ['门店', '地市', '申请量', '通过数', '通过率', '首单', '末单'],
    r => [r.store_name, r.city, String(r.apply||0), String(r.approve||0), (r.approve_rate||'0')+'%',
          r.first_app ? String(r.first_app).slice(0,10) : '-', r.last_app ? String(r.last_app).slice(0,10) : '-'].join(' | '));
  const sTotal = shiqiStores.reduce((s,r) => ({a: s.a+parseInt(r.apply||0), p: s.p+parseInt(r.approve||0)}), {a:0,p:0});
  p(`**时祺+米琪合计**：${sTotal.a}单申请，${sTotal.p}单通过，综合通过率**${sTotal.a ? (sTotal.p*100/sTotal.a).toFixed(2) : 0}%**。`);
  if (shiqiStores.length === 0) p('⚠️ 未检索到含"时祺"或"米琪"的门店数据。');
  L.push('');

  // 质态
  h1('二、质态分析（全量历史）');
  tbl(storeQuality, ['门店', '申请', '通过数', '通过率', '竣工单', '逾期单', '逾期率'],
    r => [r.store, String(r.apply), String(r.approve), r.approve_rate+'%',
          String(r.completed||0), String(r.overdue||0), (r.overdue_rate||'0')+'%'].join(' | '));
  L.push('');

  // 特批
  h1('三、特批白名单情况');
  tbl(tbData, ['门店', '总申请', '特批申请', '特批占比'],
    r => [r.store, String(r.apply), String(r.tb_apply||0), (r.tb_pct||'0')+'%'].join(' | '));
  L.push('');

  // 拒绝原因
  h1('四、拒绝原因分析');
  // 飞鸿
  p('### 飞鸿 拒绝原因');
  const fhRej = await q(`SELECT o.apply_msg AS reason, COUNT(*) AS cnt
    FROM ods_ts_credit_yzf_order_grant_apply o
    WHERE ${baseWhere} AND o.store_name IN (${feihongNames.map(n=>"'"+n.replace(/'/g,"\\'")+"'").join(',')})
      AND o.apply_status != '授信成功'
    GROUP BY o.apply_msg ORDER BY cnt DESC`);
  if (fhRej && fhRej.length > 0) {
    const tot = fhRej.reduce((s,r)=>s+parseInt(r.cnt),0);
    tbl(fhRej, ['拒绝原因', '数量', '占比'],
      r => [r.reason||'(空)', String(r.cnt), (tot ? (parseInt(r.cnt)*100/tot).toFixed(1)+'%' : '0%')].join(' | '));
  }
  L.push('');

  p('### 时祺+米琪 拒绝原因');
  const sqRej = await q(`SELECT o.apply_msg AS reason, COUNT(*) AS cnt
    FROM ods_ts_credit_yzf_order_grant_apply o
    WHERE ${baseWhere} AND o.store_name IN (${shiqiNames.map(n=>"'"+n.replace(/'/g,"\\'")+"'").join(',')})
      AND o.apply_status != '授信成功'
    GROUP BY o.apply_msg ORDER BY cnt DESC`);
  if (sqRej && sqRej.length > 0) {
    const tot = sqRej.reduce((s,r)=>s+parseInt(r.cnt),0);
    tbl(sqRej, ['拒绝原因', '数量', '占比'],
      r => [r.reason||'(空)', String(r.cnt), (tot ? (parseInt(r.cnt)*100/tot).toFixed(1)+'%' : '0%')].join(' | '));
  }
  L.push('');

  // 按月
  h1('五、按月趋势');
  for (const [groupName, names] of [['飞鸿', feihongNames], ['时祺+米琪', shiqiNames]]) {
    if (names.length === 0) continue;
    const nameList = names.map(n => "'" + n.replace(/'/g, "\\'") + "'").join(',');
    const rows = await q(`SELECT date_format(o.add_time,'%Y-%m') AS month,
      COUNT(*) AS apply, SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS approve,
      ROUND(SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),2) AS approve_rate
      FROM ods_ts_credit_yzf_order_grant_apply o
      WHERE ${baseWhere} AND o.store_name IN (${nameList})
      GROUP BY month ORDER BY month`);
    h2(groupName);
    if (rows && rows.length > 0) {
      tbl(rows, ['月份', '申请', '通过', '通过率'],
        r => [r.month, String(r.apply), String(r.approve), r.approve_rate+'%'].join(' | '));
    } else { p('_无数据_'); }
  }

  // 结论
  h1('六、结论');
  p(`1. **飞鸿**：${feihongStores.length}家门店，合计${fTotal.a}单，通过率${fTotal.a?(fTotal.p*100/fTotal.a).toFixed(2):0}%。`);
  p(`2. **时祺+米琪**：${shiqiStores.length}家门店，合计${sTotal.a}单，通过率${sTotal.a?(sTotal.p*100/sTotal.a).toFixed(2):0}%。`);
  if (shiqiStores.length === 0) {
    p('3. ⚠️ **未检索到含"米琪"的门店数据**，可能前身米琪的门店名未保留原名称，建议确认门店全称后补充查询。');
  }
  p('3. 以上分析基于ods_ts表（淘顺自营）的全量历史数据，不包含ods_bl（供货商）数据。');
  L.push('');

  // CSV
  const csv = (rows, flds) => {
    if (!rows||rows.length===0) return '';
    const h = flds.join(','); const l = rows.map(r => flds.map(f => {const v=r[f]; if(v===null||v===undefined) return ''; const s=String(v); return s.includes(',')||s.includes('"')||s.includes('\n')?'"'+s.replace(/"/g,'""')+'"':s;}).join(','));
    return h+'\n'+l.join('\n');
  };
  fs.writeFileSync(dir+'/商户飞鸿时祺_门店明细.csv', csv(allStores, ['store_name','city','apply','approve','approve_rate','first_app','last_app']));
  fs.writeFileSync(dir+'/商户飞鸿时祺_质态.csv', csv(storeQuality, ['store','apply','approve','approve_rate','completed','overdue','overdue_rate']));
  fs.writeFileSync(dir+'/商户飞鸿时祺_特批.csv', csv(tbData, ['store','apply','tb_apply','tb_pct']));
  fs.writeFileSync(dir+'/商户飞鸿时祺_分析报告.md', L.join('\n'));

  console.log('\n✅ 商户分析完成');
  conn.end();
}
main().catch(e => { console.error(e); process.exit(1); });
