const mysql = require('mysql2/promise');
const fs = require('fs');

async function main() {
  const conn = await mysql.createConnection({
    host: '47.119.181.195', port: 9030, user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)", database: 'ods',
  });
  const q = async (sql) => { const [r] = await conn.query(sql); return r; };

  const dir = '/mnt/d/desktop/翼支付交流_门店代理商分析';
  const cond = "o.custtype='00' AND o.business_type='02'";
  const dws = "LEFT JOIN dws.dws_credit_yzf_order_complete c ON o.ct_user_id=c.ct_user_id AND c.source_business_type='淘顺实时授信'";
  const wlc = "LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no";
  const curMonth = '2026-05';
  const prevMonth = '2026-04';
  const range30d = '2026-04-16';
  const range7d = '2026-05-06';

  // ========== 1. 全国月度趋势（近13个月） ==========
  const months = [];
  for (let i = 0; i < 13; i++) {
    const d = new Date(2025, 4 + i, 1); // Start from 2025-05
    months.push(d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0'));
  }

  const natTrend = [];
  for (const m of months) {
    const r = await q(`SELECT '${m}' AS m,
      COUNT(*) AS a,
      SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS ap,
      ROUND(SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),1) AS apr,
      COUNT(c.ct_user_id) AS co,
      SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS ov,
      ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS ovr,
      ROUND(SUM(o.order_amt/1000000),1) AS amt_wan
      FROM ods_ts_credit_yzf_order_grant_apply o ${dws}
      WHERE ${cond} AND o.store_addr_province IS NOT NULL AND date_format(o.add_time,'%Y-%m')='${m}'`);
    if (r && r.length > 0 && parseInt(r[0].a) > 0) natTrend.push(r[0]);
  }

  // ========== 2. 各省近30天通过率排名 ==========
  const prov30 = [];
  const provs = await q(`SELECT DISTINCT store_addr_province AS p FROM ods_ts_credit_yzf_order_grant_apply o
    WHERE ${cond} AND o.store_addr_province IS NOT NULL`);
  const pList = (provs && provs.length > 0) ? provs.map(r => r.p) : 
    ['湖南省','贵州省','江西省','广西壮族自治区','广东省','四川省','安徽省','甘肃省','海南省','吉林省','江苏省','宁夏回族自治区'];
  
  for (const p of ['湖南省','贵州省','江西省','广西壮族自治区','广东省','四川省','安徽省','甘肃省','海南省','吉林省','江苏省','宁夏回族自治区','云南省','福建省']) {
    const r = await q(`SELECT '${p}' AS p,
      COUNT(*) AS a, SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS ap,
      ROUND(SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),1) AS apr,
      COUNT(c.ct_user_id) AS co,
      SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS ov,
      ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS ovr
      FROM ods_ts_credit_yzf_order_grant_apply o ${dws}
      WHERE ${cond} AND o.store_addr_province='${p}' AND o.add_time>='2026-04-16'`);
    if (r && r.length > 0 && parseInt(r[0].a) >= 50) prov30.push(r[0]);
  }
  prov30.sort((a,b) => b.apr - a.apr);

  // ========== 3. 重点省份（湖南/贵州/广西/江西）地市 ==========
  const keyProvs = ['湖南省','贵州省','广西壮族自治区','江西省'];
  const cityData = {};
  for (const pv of keyProvs) {
    const rows = [];
    const cities = ['长沙市','衡阳市','岳阳市','郴州市','株洲市','邵阳市','常德市','永州市','娄底市','益阳市','怀化市','湘潭市','湘西土家族苗族自治州','张家界市',
                    '贵阳市','遵义市','毕节地区','黔南布依族苗族自治州','六盘水市','铜仁地区','黔东南苗族侗族自治州','黔西南布依族苗族自治州','安顺市',
                    '南宁市','柳州市','桂林市','玉林市','河池市','崇左市','百色市','北海市','贵港市','贺州市','梧州市','钦州市','来宾市','防城港市',
                    '赣州市','南昌市','九江市','上饶市','宜春市','吉安市','抚州市','景德镇市','萍乡市','新余市','鹰潭市'];
    for (const c of cities) {
      const r = await q(`SELECT '${c}' AS c,
        COUNT(*) AS a, SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS ap,
        ROUND(SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),1) AS apr,
        COUNT(c.ct_user_id) AS co,
        SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS ov,
        ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS ovr
        FROM ods_ts_credit_yzf_order_grant_apply o ${dws}
        WHERE ${cond} AND o.store_addr_province='${pv}' AND o.store_addr_city='${c}' AND o.add_time>='2026-04-16'`);
      if (r && r.length > 0 && parseInt(r[0].a) >= 20) rows.push(r[0]);
    }
    cityData[pv] = rows.sort((a,b) => a.apr - b.apr);
  }

  // ========== 4. 特批通道监控（湖南逐月） ==========
  const tbMonths = ['2025-11','2025-12','2026-01','2026-02','2026-03','2026-04','2026-05'];
  const tbTrend = [];
  for (const m of tbMonths) {
    const r = await q(`SELECT '${m}' AS m,
      COUNT(*) AS approved,
      ROUND(SUM(CASE WHEN w.first_risk_result='特批白名单用户' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),1) AS tb_pct,
      SUM(CASE WHEN w.first_risk_result='特批白名单用户' THEN 1 ELSE 0 END) AS tb_cnt,
      ROUND(SUM(CASE WHEN w.first_risk_result='特批白名单用户' AND c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(SUM(CASE WHEN w.first_risk_result='特批白名单用户' AND c.ct_user_id IS NOT NULL THEN 1 ELSE 0 END),0),2) AS tb_ovr,
      ROUND(SUM(CASE WHEN (w.first_risk_result IS NULL OR w.first_risk_result!='特批白名单用户') AND c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(SUM(CASE WHEN (w.first_risk_result IS NULL OR w.first_risk_result!='特批白名单用户') AND c.ct_user_id IS NOT NULL THEN 1 ELSE 0 END),0),2) AS normal_ovr
      FROM ods_ts_credit_yzf_order_grant_apply o ${wlc} ${dws}
      WHERE ${cond} AND o.store_addr_province='湖南省' AND date_format(o.add_time,'%Y-%m')='${m}' AND o.apply_status='授信成功'`);
    if (r && r.length > 0 && parseInt(r[0].approved) > 0) tbTrend.push(r[0]);
  }

  // ========== 5. 异常门店预警 ==========
  const alarmStores = [];
  const mList = "'2026-04','2026-05'";
  // 条件：近2月申请>=10且逾期率>=10%
  const alarmRows = await q(`SELECT o.store_addr_province AS p, o.store_addr_city AS c, o.store_name AS s,
    COUNT(*) AS a, SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS ap,
    ROUND(SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),1) AS apr,
    COUNT(c.ct_user_id) AS co,
    SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS ov,
    ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS ovr
    FROM ods_ts_credit_yzf_order_grant_apply o ${dws}
    WHERE ${cond} AND date_format(o.add_time,'%Y-%m') IN (${mList})
    GROUP BY o.store_addr_province, o.store_addr_city, o.store_name
    HAVING COUNT(*) >= 10 AND SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) >= 2
      AND SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0) >= 10
    ORDER BY ovr DESC LIMIT 20`);
  if (alarmRows && alarmRows.length > 0) {
    for (const r of alarmRows) alarmStores.push(r);
  }

  // ========== 6. 打印报告 ==========
  const L = [];
  const p = s => L.push(s);
  const h1 = s => { L.push(''); L.push('## ' + s); L.push(''); };
  const h2 = s => { L.push('### ' + s); L.push(''); };
  const tbl = (rows, hdrs, fmt) => {
    if (!rows||rows.length===0) { p('_无数据_'); L.push(''); return; }
    L.push('| ' + hdrs.join(' | ') + ' |');
    L.push('|' + hdrs.map(() => ':---:').join('|') + '|');
    rows.forEach(r => L.push('| ' + (fmt?fmt(r):hdrs.map(h=>String(r[h]??'')).join(' | ')) + ' |'));
  };

  L.push('# 淘顺实时授信 — 常规监控月报');
  L.push(`> 数据截止：2026-05-13 | 范围：近13个月 + 近30天`);
  L.push('');

  h1('一、全国月度趋势');
  tbl(natTrend, ['月份', '申请', '通过', '通过率', '竣工', '逾期', '逾期率', '放款(万)'],
    r => [r.m, String(r.a), String(r.ap), r.apr+'%', String(r.co||0), String(r.ov||0), (r.ovr||'0')+'%', String(r.amt_wan||'-')].join(' | '));
  L.push('');

  h1('二、各省近30天通过率排名');
  tbl(prov30, ['排名', '省份', '申请', '通过率', '竣工', '逾期', '逾期率'],
    (r,i) => [String(i+1), r.p, String(r.a), r.apr+'%', String(r.co||0), String(r.ov||0), (r.ovr||'0')+'%'].join(' | '));
  L.push('');

  h1('三、重点省份地市明细');
  const provCities = {
    '湖南省': '湖南', '贵州省': '贵州', '广西壮族自治区': '广西', '江西省': '江西'
  };
  for (const pv of keyProvs) {
    const rows = cityData[pv] || [];
    if (rows.length === 0) continue;
    h2(provCities[pv] || pv);
    tbl(rows, ['地市', '申请', '通过率', '竣工', '逾期', '逾期率'],
      r => [r.c, String(r.a), r.apr+'%', String(r.co||0), String(r.ov||0), (r.ovr||'0')+'%'].join(' | '));
    const bad = rows.filter(r => parseFloat(r.ovr||0) >= 10);
    if (bad.length > 0) p(`⚠️ 逾期率≥10%地市：${bad.map(r=>r.c+'('+r.ovr+'%)').join('、')}。`);
    L.push('');
  }

  h1('四、特批通道监控（湖南）');
  tbl(tbTrend, ['月份', '批准量', '特批占比', '特批用户', '特批逾期率', '正常逾期率'],
    r => [r.m, String(r.approved), r.tb_pct+'%', String(r.tb_cnt), (r.tb_ovr||'0')+'%', (r.normal_ovr||'0')+'%'].join(' | '));
  L.push('');
  if (tbTrend.length > 0) {
    const latest = tbTrend[tbTrend.length-1];
    p(`本月特批占比${latest.tb_pct}%，特批逾期率${latest.tb_ovr||'0'}%，正常逾期率${latest.normal_ovr||'0'}%。`);
  }

  h1('五、异常门店预警');
  if (alarmStores.length > 0) {
    tbl(alarmStores, ['省份', '地市', '门店', '申请', '通过率', '竣工', '逾期', '逾期率'],
      r => [r.p, r.c, r.s, String(r.a), r.apr+'%', String(r.co||0), String(r.ov||0), r.ovr+'%'].join(' | '));
    p(`共${alarmStores.length}家门店触发预警（近2月申请≥10+逾期≥2单+逾期率≥10%）。`);
  } else {
    p('本月无门店触发预警阈值。');
  }
  L.push('');

  // 写文件
  fs.writeFileSync(dir + '/常规监控月报_202605.md', L.join('\n'));

  // 同时输出到对话框
  console.log(L.join('\n'));

  console.log('\n✅ 常规监控月报已生成');
  conn.end();
}
main().catch(e => { console.error(e); process.exit(1); });
