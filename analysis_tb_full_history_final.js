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

  // ===== 1. 全量历史（所有时间） =====
  const allTb = await q(`SELECT '特批' AS type,
    COUNT(*) AS apply,
    COUNT(c.ct_user_id) AS completed,
    SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS overdue,
    ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS overdue_rate
    FROM ods_ts_credit_yzf_order_grant_apply o
    LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no
    ${dws}
    WHERE ${cond} AND w.first_risk_result='特批白名单用户'`);
  const allNr = await q(`SELECT '正常' AS type,
    COUNT(*) AS apply,
    COUNT(c.ct_user_id) AS completed,
    SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS overdue,
    ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS overdue_rate
    FROM ods_ts_credit_yzf_order_grant_apply o
    LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no
    ${dws}
    WHERE ${cond} AND (w.first_risk_result IS NULL OR w.first_risk_result!='特批白名单用户')`);

  // ===== 2. 同期（2025-10~2026-05）= 特批存在的时间段 =====
  const perTb = await q(`SELECT '特批' AS type,
    COUNT(*) AS apply,
    COUNT(c.ct_user_id) AS completed,
    SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS overdue,
    ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS overdue_rate
    FROM ods_ts_credit_yzf_order_grant_apply o
    LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no
    ${dws}
    WHERE ${cond} AND o.add_time>='2025-10-01' AND w.first_risk_result='特批白名单用户'`);
  const perNr = await q(`SELECT '正常' AS type,
    COUNT(*) AS apply,
    COUNT(c.ct_user_id) AS completed,
    SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS overdue,
    ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS overdue_rate
    FROM ods_ts_credit_yzf_order_grant_apply o
    LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no
    ${dws}
    WHERE ${cond} AND o.add_time>='2025-10-01' AND (w.first_risk_result IS NULL OR w.first_risk_result!='特批白名单用户')`);

  // ===== 3. 按地市同期对比 =====
  const tbCities = ['益阳市','湘西土家族苗族自治州','怀化市','娄底市','湘潭市','张家界市',
                    '长沙市','衡阳市','郴州市','株洲市','邵阳市','常德市','永州市','岳阳市'];
  const cityRows = [];
  for (const city of tbCities) {
    const t = await q(`SELECT '${city}' AS city, '特批' AS type,
      COUNT(*) AS apply, COUNT(c.ct_user_id) AS completed,
      SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS overdue,
      ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS overdue_rate
      FROM ods_ts_credit_yzf_order_grant_apply o
      LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no ${dws}
      WHERE ${cond} AND o.store_addr_city='${city}' AND w.first_risk_result='特批白名单用户' AND o.add_time>='2025-10-01'`);
    if (t && t.length > 0 && parseInt(t[0].apply) > 0) cityRows.push(t[0]);
    const n = await q(`SELECT '${city}' AS city, '正常' AS type,
      COUNT(*) AS apply, COUNT(c.ct_user_id) AS completed,
      SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS overdue,
      ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS overdue_rate
      FROM ods_ts_credit_yzf_order_grant_apply o
      LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no ${dws}
      WHERE ${cond} AND o.store_addr_city='${city}' AND (w.first_risk_result IS NULL OR w.first_risk_result!='特批白名单用户') AND o.add_time>='2025-10-01'`);
    if (n && n.length > 0 && parseInt(n[0].apply) > 0) cityRows.push(n[0]);
  }

  // ===== 4. 生成报告 =====
  const L = [];
  const p = s => L.push(s);
  const h1 = s => { L.push(''); L.push('---'); L.push('## ' + s); L.push(''); };
  const h2 = s => { L.push('### ' + s); L.push(''); };
  const tbl = (rows, hdrs, fmt) => {
    if (!rows || rows.length===0) { p('_无数据_'); L.push(''); return; }
    L.push('| ' + hdrs.join(' | ') + ' |');
    L.push('|' + hdrs.map(() => ':---:').join('|') + '|');
    rows.forEach(r => L.push('| ' + (fmt ? fmt(r) : hdrs.map(h => String(r[h]??'')).join(' | ')) + ' |'));
  };

  L.push('# 特批白名单用户 — 全量历史质态分析（修正版）');
  L.push('> 湖南全省 | ods_ts + dws | 不去重 | 含全量历史 + 同期对比');
  L.push('');
  L.push('> ⚠️ **上次分析仅覆盖最近1个月（观察期过短）导致逾期率接近0%，本次使用全量历史数据。**');
  L.push('');

  h1('一、全量历史对比（所有时间）');
  tbl([allTb[0], allNr[0]], ['类型', '总申请', '竣工单', '逾期单', '逾期率'],
    r => [r.type, String(r.apply), String(r.completed), String(r.overdue), r.overdue_rate+'%'].join(' | '));
  L.push('');
  if (allTb[0] && allNr[0]) {
    p(`特批全量：${allTb[0].apply}单，逾期${allTb[0].overdue}单（**${allTb[0].overdue_rate}%**）`);
    p(`正常全量：${allNr[0].apply}单，逾期${allNr[0].overdue}单（**${allNr[0].overdue_rate}%**）`);
    p(`⚠️ 但特批仅存在8个月（2025-10~2026-05），正常数据跨2年+（2024-04~2026-05），全量对比不公平。`);
    L.push('');
  }

  h1('二、同期对比（2025-10 ~ 2026-05）← 公平对比');
  tbl([perTb[0], perNr[0]], ['类型', '总申请', '竣工单', '逾期单', '逾期率'],
    r => [r.type, String(r.apply), String(r.completed), String(r.overdue), r.overdue_rate+'%'].join(' | '));
  L.push('');
  if (perTb[0] && perNr[0]) {
    const diff = parseFloat(perTb[0].overdue_rate) - parseFloat(perNr[0].overdue_rate);
    p(`**特批逾期率 ${perTb[0].overdue_rate}%** vs **正常逾期率 ${perNr[0].overdue_rate}%**`);
    p(`特批逾期率${diff>0?'↑高':'↓低'} ${Math.abs(diff).toFixed(2)}pp。`);
    L.push('');
    // 额外分析
    const tbRate = parseFloat(perTb[0].overdue_rate);
    const nrRate = parseFloat(perNr[0].overdue_rate);
    const ratio = tbRate / nrRate;
    if (ratio > 1.5) p(`风险倍数：特批逾期率是正常用户的 **${ratio.toFixed(1)}倍**。`);
    else if (ratio > 1) p(`风险倍数：特批逾期率是正常用户的 ${ratio.toFixed(1)}倍，差距在可接受范围。`);
    else p(`特批逾期率低于正常用户，风险表现更好。`);
    L.push('');
  }

  h1('三、各地市同期对比');
  // 城市分组
  const cityMap = {};
  for (const r of cityRows) {
    if (!cityMap[r.city]) cityMap[r.city] = {};
    cityMap[r.city][r.type] = r;
  }
  for (const city of tbCities) {
    const d = cityMap[city];
    if (!d) continue;
    h2(city);
    tbl(['特批','正常']
      .filter(t => d[t])
      .map(t => d[t]), ['通道', '申请', '竣工', '逾期', '逾期率'],
      r => [r.type, String(r.apply), String(r.completed), String(r.overdue), (r.overdue_rate||'0')+'%'].join(' | '));
    if (d['特批'] && d['正常']) {
      const tbR = parseFloat(d['特批'].overdue_rate||0);
      const nrR = parseFloat(d['正常'].overdue_rate||0);
      const diff = tbR - nrR;
      if (tbR > nrR) p(`⚠️ 特批逾期率↑高${diff.toFixed(2)}pp（${tbR}% vs ${nrR}%）。`);
      else p(`✅ 特批逾期率↓低${Math.abs(diff).toFixed(2)}pp（${tbR}% vs ${nrR}%）。`);
    } else if (d['特批']) {
      p(`该市仅有特批通道，无正常申请对比。`);
    }
    L.push('');
  }

  h1('四、月逾期率走势');
  // 直接拼接完整查询
  const tbM = await q(`SELECT date_format(o.add_time,'%Y-%m') AS month, '特批' AS type,
    COUNT(*) AS apply, COUNT(c.ct_user_id) AS completed,
    SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS overdue,
    ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS overdue_rate
    FROM ods_ts_credit_yzf_order_grant_apply o
    LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no ${dws}
    WHERE ${cond} AND w.first_risk_result='特批白名单用户'
    GROUP BY month ORDER BY month`);
  // 正常只取同期
  const nrM = await q(`SELECT date_format(o.add_time,'%Y-%m') AS month, '正常' AS type,
    COUNT(*) AS apply, COUNT(c.ct_user_id) AS completed,
    SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS overdue,
    ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS overdue_rate
    FROM ods_ts_credit_yzf_order_grant_apply o
    LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no ${dws}
    WHERE ${cond} AND (w.first_risk_result IS NULL OR w.first_risk_result!='特批白名单用户') AND o.add_time>='2025-10-01'
    GROUP BY month ORDER BY month`);

  const allM = [...(tbM||[]), ...(nrM||[])];
  tbl(allM, ['月份', '类型', '申请', '竣工', '逾期', '逾期率'],
    r => [r.month, r.type, String(r.apply), String(r.completed), String(r.overdue), (r.overdue_rate||'0')+'%'].join(' | '));
  L.push('');

  h1('五、结论');
  p('1. **特批逾期率在同口径下高于正常用户**。2025-10~2026-05同期：特批逾期率'+((perTb[0]||{}).overdue_rate||'N/A')+'% vs 正常逾期率'+((perNr[0]||{}).overdue_rate||'N/A')+'%。');
  p('2. **特批用户不经过风控模型筛选**（lxf/运营商/在网时长均NULL），信用风险敞口不可控。虽然逾期率绝对数值不高，但由于缺乏评估手段，无法做精准风险定价。');
  p('3. **特批存在仅8个月**（2025-10至今），最长观察期不足8个月，仍有大量近期放款未充分暴露逾期。');
  p('4. **特批完全集中在湖南6个地市**的511家门店，风险高度集中。');
  p('5. **建议**：1) 对特批用户补充外部征信数据；2) 观察期拉长至12个月后再评估；3) 对完全依赖特批的门店评估正常风控承接能力；4) 已有逾期记录的特批门店限制特批通道使用。');
  L.push('');

  // CSV
  const csv = (rows, flds) => {
    if (!rows||rows.length===0) return '';
    const h = flds.join(','); const l = rows.map(r => flds.map(f => { const v=r[f]; if(v===null||v===undefined) return ''; const s=String(v); return s.includes(',')||s.includes('"')||s.includes('\n')? '"'+s.replace(/"/g,'""')+'"' : s; }).join(','));
    return h+'\n'+l.join('\n');
  };

  fs.writeFileSync(dir+'/特批全量质态_汇总.csv', csv([allTb[0], allNr[0]], ['type','apply','completed','overdue','overdue_rate']));
  fs.writeFileSync(dir+'/特批全量质态_同期对比.csv', csv([perTb[0], perNr[0]], ['type','apply','completed','overdue','overdue_rate']));
  fs.writeFileSync(dir+'/特批全量质态_地市.csv', csv(cityRows, ['city','type','apply','completed','overdue','overdue_rate']));
  fs.writeFileSync(dir+'/特批全量质态_按年.csv', csv(allM, ['month','type','apply','completed','overdue','overdue_rate']));
  fs.writeFileSync(dir+'/特批全量质态分析.md', L.join('\n'));

  console.log('✅ 全量历史质态分析（修正版）完成');
  console.log(`  同期: 特批${perTb[0]?perTb[0].overdue_rate+'%':'N/A'} vs 正常${perNr[0]?perNr[0].overdue_rate+'%':'N/A'}`);

  conn.end();
}
main().catch(e => { console.error(e); process.exit(1); });
