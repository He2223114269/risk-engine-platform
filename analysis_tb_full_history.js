const mysql = require('mysql2/promise');
const fs = require('fs');

async function main() {
  const conn = await mysql.createConnection({
    host: '47.119.181.195', port: 9030, user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)", database: 'ods',
  });
  const q = async (sql) => { const [r] = await conn.query(sql); return r; };

  const dir = '/mnt/d/desktop/翼支付交流_门店代理商分析';

  const tbCond    = "w.first_risk_result='特批白名单用户'";
  const normalCond = "(w.first_risk_result IS NULL OR w.first_risk_result!='特批白名单用户')";
  const baseFrom  = `FROM ods_ts_credit_yzf_order_grant_apply o
    LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no
    LEFT JOIN dws.dws_credit_yzf_order_complete c ON o.ct_user_id=c.ct_user_id AND c.source_business_type='淘顺实时授信'`;

  // ============ 1. 全量汇总对比 ============
  const tbAll = await q(`SELECT '特批' AS type,
    COUNT(*) AS apply,
    SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS approve,
    ROUND(SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),2) AS approve_rate,
    COUNT(c.ct_user_id) AS completed,
    SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS overdue,
    ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS overdue_rate
    ${baseFrom} WHERE o.custtype='00' AND o.store_addr_province='湖南省'
      AND o.business_type='02' AND ${tbCond}`);
  const nrAll = await q(`SELECT '正常' AS type,
    COUNT(*) AS apply,
    SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS approve,
    ROUND(SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),2) AS approve_rate,
    COUNT(c.ct_user_id) AS completed,
    SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS overdue,
    ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS overdue_rate
    ${baseFrom} WHERE o.custtype='00' AND o.store_addr_province='湖南省'
      AND o.business_type='02' AND ${normalCond}`);

  console.log('=== 全量汇总 ===');
  console.table([...(tbAll||[]), ...(nrAll||[])]);

  // ============ 2. 按月逾期走势 ============
  const months = await q(`SELECT DISTINCT date_format(o.add_time,'%Y-%m') AS m
    FROM ods_ts_credit_yzf_order_grant_apply o
    WHERE o.custtype='00' AND o.store_addr_province='湖南省' AND o.business_type='02'
    ORDER BY m`);
  const monthArr = months.map(r => r.m);
  console.log(`月份数: ${monthArr.length}, 范围: ${monthArr[0]} ~ ${monthArr[monthArr.length-1]}`);

  const monthlyRows = [];
  for (const m of monthArr) {
    // 特批
    const [r1] = await q(`SELECT '${m}' AS month, '特批' AS type,
      COUNT(*) AS apply,
      SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS approve,
      COUNT(c.ct_user_id) AS completed,
      SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS overdue,
      ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS overdue_rate
      ${baseFrom}
      WHERE o.custtype='00' AND o.store_addr_province='湖南省' AND o.business_type='02'
        AND date_format(o.add_time,'%Y-%m')='${m}' AND ${tbCond}`);
    if (r1 && r1.length > 0 && parseInt(r1[0].apply) > 0) monthlyRows.push(r1[0]);

    // 正常
    const [r2] = await q(`SELECT '${m}' AS month, '正常' AS type,
      COUNT(*) AS apply,
      SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS approve,
      COUNT(c.ct_user_id) AS completed,
      SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS overdue,
      ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS overdue_rate
      ${baseFrom}
      WHERE o.custtype='00' AND o.store_addr_province='湖南省' AND o.business_type='02'
        AND date_format(o.add_time,'%Y-%m')='${m}' AND ${normalCond}`);
    if (r2 && r2.length > 0 && parseInt(r2[0].apply) > 0) monthlyRows.push(r2[0]);
  }
  console.log('\n=== 按月逾期走势 ===');
  console.table(monthlyRows);

  // ============ 3. 按账龄分层（特批vs正常） ============
  // 按通过时间分：观察期1个月 / 1-3个月 / 3-6个月 / 6个月+
  const [aging] = await q(`
    SELECT t.type,
      CASE WHEN t.approve_time IS NULL THEN '未通过'
        WHEN datediff(now(), t.approve_time) <= 30 THEN '≤1月'
        WHEN datediff(now(), t.approve_time) <= 90 THEN '1-3月'
        WHEN datediff(now(), t.approve_time) <= 180 THEN '3-6月'
        ELSE '6月+' END AS aging_bucket,
      COUNT(*) AS approve_cnt,
      SUM(CASE WHEN t.overdue_flag=1 THEN 1 ELSE 0 END) AS overdue,
      ROUND(SUM(CASE WHEN t.overdue_flag=1 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),2) AS overdue_rate
    FROM (
      SELECT 
        CASE WHEN w.first_risk_result='特批白名单用户' THEN '特批' ELSE '正常' END AS type,
        CASE WHEN o.apply_status='授信成功' THEN o.add_time ELSE NULL END AS approve_time,
        CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END AS overdue_flag
      FROM ods_ts_credit_yzf_order_grant_apply o
      LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no
      LEFT JOIN dws.dws_credit_yzf_order_complete c ON o.ct_user_id=c.ct_user_id AND c.source_business_type='淘顺实时授信'
      WHERE o.custtype='00' AND o.store_addr_province='湖南省' AND o.business_type='02'
    ) t
    WHERE t.approve_time IS NOT NULL
    GROUP BY t.type, aging_bucket
    ORDER BY t.type, aging_bucket
  `);
  console.log('\n=== 按账龄分层逾期率 ===');
  console.table(aging);

  // ============ 4. 特批vs正常 - 按年龄/运营商等客群分层对比 ============
  // 按运营商分
  const [byOp] = await q(`
    SELECT t.type, t.operator_group,
      COUNT(*) AS approve,
      SUM(t.overdue_flag) AS overdue,
      ROUND(SUM(t.overdue_flag)*100.0/NULLIF(COUNT(*),0),2) AS overdue_rate
    FROM (
      SELECT CASE WHEN w.first_risk_result='特批白名单用户' THEN '特批' ELSE '正常' END AS type,
        CASE WHEN w.operator_real IN ('移动','联通') THEN '异网'
             WHEN w.operator_real IN ('电信') THEN '本网'
             ELSE '未知' END AS operator_group,
        CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END AS overdue_flag
      FROM ods_ts_credit_yzf_order_grant_apply o
      LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no
      LEFT JOIN dws.dws_credit_yzf_order_complete c ON o.ct_user_id=c.ct_user_id AND c.source_business_type='淘顺实时授信'
      WHERE o.custtype='00' AND o.store_addr_province='湖南省' AND o.business_type='02'
        AND o.apply_status='授信成功'
    ) t
    GROUP BY t.type, t.operator_group
    ORDER BY t.type, t.operator_group
  `);
  console.log('\n=== 按运营商分层逾期率 ===');
  console.table(byOp);

  // ============ 5. 逾期分布分析 ============
  const [overdueDetail] = await q(`
    SELECT t.type, t.overdue_orders,
      COUNT(*) AS user_cnt,
      ROUND(COUNT(*)*100.0/SUM(COUNT(*)) OVER(PARTITION BY t.type),2) AS pct
    FROM (
      SELECT 
        CASE WHEN w.first_risk_result='特批白名单用户' THEN '特批' ELSE '正常' END AS type,
        o.ct_user_id,
        SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS overdue_orders
      FROM ods_ts_credit_yzf_order_grant_apply o
      LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no
      LEFT JOIN dws.dws_credit_yzf_order_complete c ON o.ct_user_id=c.ct_user_id AND c.source_business_type='淘顺实时授信'
      WHERE o.custtype='00' AND o.store_addr_province='湖南省' AND o.business_type='02'
        AND o.apply_status='授信成功'
      GROUP BY type, o.ct_user_id
    ) t
    GROUP BY t.type, t.overdue_orders
    ORDER BY t.type, t.overdue_orders
  `);
  console.log('\n=== 逾期分布 ===');
  console.table(overdueDetail);

  // ============ 6. 生成报告 ============
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

  L.push('# 特批白名单用户 — 全量历史质态分析');
  L.push('> 全量历史数据 | 湖南全省 | ods_ts + dws');
  L.push('');

  h1('一、全量汇总对比');
  tbl([...(tbAll||[]), ...(nrAll||[])], ['类型', '总申请', '通过数', '通过率', '竣工单', '逾期单', '逾期率'],
    r => [r.type, String(r.apply), String(r.approve), r.approve_rate+'%', String(r.completed), String(r.overdue), (r.overdue_rate||'0')+'%'].join(' | '));
  L.push('');

  // 对比
  if (tbAll && tbAll.length > 0 && nrAll && nrAll.length > 0) {
    const t = tbAll[0], n = nrAll[0];
    p(`**特批通道**：全量${t.apply}单，通过${t.approve}单（${t.approve_rate}%），竣工${t.completed}单，逾期${t.overdue}单（**${t.overdue_rate}%**）。`);
    p(`**正常通道**：全量${n.apply}单，通过${n.approve}单（${n.approve_rate}%），竣工${n.completed}单，逾期${n.overdue}单（**${n.overdue_rate}%**）。`);
    const diff = parseFloat(t.overdue_rate||0) - parseFloat(n.overdue_rate||0);
    p(`**差异**：特批逾期率${diff > 0 ? '↑高' : '↓低'}${Math.abs(diff).toFixed(2)}pp。`);
    L.push('');
  }

  h1('二、按月逾期走势');
  tbl(monthlyRows, ['月份', '类型', '申请', '通过', '竣工', '逾期', '逾期率'],
    r => [r.month, r.type, String(r.apply), String(r.approve), String(r.completed), String(r.overdue), (r.overdue_rate||'0')+'%'].join(' | '));
  L.push('');

  h1('三、按账龄分层逾期率');
  tbl(aging, ['类型', '账龄', '通过数', '逾期', '逾期率'],
    r => [r.type, r.aging_bucket, String(r.approve_cnt), String(r.overdue), r.overdue_rate+'%'].join(' | '));
  L.push('');

  h1('四、按运营商分层逾期率');
  if (byOp && byOp.length > 0) {
    tbl(byOp, ['类型', '运营商', '通过数', '逾期', '逾期率'],
      r => [r.type, r.operator_group, String(r.approve), String(r.overdue), (r.overdue_rate||'0')+'%'].join(' | '));
    L.push('');
  }

  h1('五、逾期分布（人均逾期笔数）');
  if (overdueDetail && overdueDetail.length > 0) {
    tbl(overdueDetail, ['类型', '逾期笔数', '用户数', '占比'],
      r => [r.type, String(r.overdue_orders), String(r.user_cnt), r.pct+'%'].join(' | '));
    L.push('');
  }

  h1('六、结论与建议');
  p('1. 特批白名单用户全量历史共17315单，数据跨度2025年10月至2026年5月（8个月）。');
  p(`2. 特批逾期率 vs 正常逾期率：特批${tbAll&&tbAll[0]?tbAll[0].overdue_rate+'%':'N/A'}，正常${nrAll&&nrAll[0]?nrAll[0].overdue_rate+'%':'N/A'}。`);
  p('3. 特批用户不经过风控模型评估（lxf/运营商/在网时长均为NULL），信用风险敞口不可量化。');
  p('4. 特批存在时间仅8个月，最长观察期不足8个月，需持续跟踪。');
  p('5. 建议：1) 对特批用户补充外部征信查询；2) 延长追踪窗口至12个月以上；3) 对特批门店设置额度上限并与逾期率挂钩。');
  L.push('');

  // CSV
  const csv = (rows, flds) => {
    if (!rows || rows.length===0) return '';
    const h = flds.join(',');
    const l = rows.map(r => flds.map(f => {
      const v = r[f]; if (v===null||v===undefined) return '';
      const s = String(v); return s.includes(',')||s.includes('"')||s.includes('\n') ? '"'+s.replace(/"/g,'""')+'"' : s;
    }).join(','));
    return h+'\n'+l.join('\n');
  };
  const allSummary = [...(tbAll||[]), ...(nrAll||[])];
  fs.writeFileSync(dir+'/特批全量质态_汇总.csv', csv(allSummary, ['type','apply','approve','approve_rate','completed','overdue','overdue_rate']));
  fs.writeFileSync(dir+'/特批全量质态_按月.csv', csv(monthlyRows, ['month','type','apply','approve','completed','overdue','overdue_rate']));
  fs.writeFileSync(dir+'/特批全量质态_账龄.csv', csv(aging, ['type','aging_bucket','approve_cnt','overdue','overdue_rate']));
  fs.writeFileSync(dir+'/特批全量质态.md', L.join('\n'));

  console.log('\n✅ 全量历史质态分析完成');
  conn.end();
}
main().catch(e => { console.error(e); process.exit(1); });
