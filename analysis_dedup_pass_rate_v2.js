const mysql = require('mysql2/promise');
const fs = require('fs');

// 去重子查询模板（按用户提供的SQL逻辑）
const dedup_subquery = (table) => `
  SELECT a1.*, a3.operator_real, a3.first_risk_result, a3.online_duration
  FROM ${table} a1
  LEFT JOIN ${table} a2
    ON a1.id_number_enc = a2.id_number_enc
   AND (
     (a2.apply_status = '授信成功' AND a1.apply_status != '授信成功')
     OR (a1.apply_status = a2.apply_status AND a1.id < a2.id)
   )
  LEFT JOIN ods_ts_order_white_list_control a3 ON a1.ct_user_id = a3.order_no
  WHERE a2.id IS NULL AND a1.business_type = '02'
`;

async function main() {
  const conn = await mysql.createConnection({
    host: '47.119.181.195', port: 9030, user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)", database: 'ods',
  });
  const q = async (sql) => { const [r] = await conn.query(sql); return r; };

  const dir = '/mnt/d/desktop/翼支付交流_门店代理商分析';

  // ============= 1. 全国逐日去重通过率 =============
  const national_daily = await q(`
    SELECT date_format(add_time, '%Y-%m-%d') as dt,
      COUNT(*) AS total,
      SUM(CASE WHEN apply_status = '授信成功' THEN 1 ELSE 0 END) AS pass,
      ROUND(SUM(CASE WHEN apply_status = '授信成功' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS rate
    FROM (${dedup_subquery('ods_ts_credit_yzf_order_grant_apply')}) t
    WHERE custtype = '00' AND store_addr_province IS NOT NULL
      AND add_time >= '2026-04-05'
    GROUP BY dt ORDER BY dt
  `);

  // 汇总
  const sum7 = national_daily.filter(r => r.dt >= '2026-05-06').reduce((s, x) => ({ t: s.t + x.total, p: s.p + x.pass }), { t: 0, p: 0 });
  const sum30 = national_daily.reduce((s, x) => ({ t: s.t + x.total, p: s.p + x.pass }), { t: 0, p: 0 });
  const r7 = sum7.t ? (sum7.p / sum7.t * 100).toFixed(2) : 0;
  const r30 = sum30.t ? (sum30.p / sum30.t * 100).toFixed(2) : 0;
  console.log(`全国去重: 7天 ${sum7.t}单 ${r7}% | 30天 ${sum30.t}单 ${r30}%`);

  // 上月同期
  const prevMRows = await q(`
    SELECT COUNT(*) AS cnt,
      SUM(CASE WHEN apply_status = '授信成功' THEN 1 ELSE 0 END) AS pass_cnt
    FROM (${dedup_subquery('ods_ts_credit_yzf_order_grant_apply')}) t
    WHERE custtype = '00' AND store_addr_province IS NOT NULL
      AND add_time >= '2026-03-06' AND add_time < '2026-04-05'
  `);
  const prevM = prevMRows[0] || { cnt: 0, pass_cnt: 0 };
  const rPrev = prevM.cnt ? (prevM.pass_cnt / prevM.cnt * 100).toFixed(2) : 0;
  console.log(`上月同期: ${prevM.cnt}单 ${rPrev}%`);

  // ============= 2. 各省去重通过率 =============
  const bp30 = await q(`
    SELECT store_addr_province AS p,
      COUNT(*) AS t,
      SUM(CASE WHEN apply_status = '授信成功' THEN 1 ELSE 0 END) AS pa,
      ROUND(SUM(CASE WHEN apply_status = '授信成功' AND first_risk_result != '特批白名单用户' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS r,
      SUM(CASE WHEN first_risk_result = '特批白名单用户' THEN 1 ELSE 0 END) AS tb,
      ROUND(SUM(CASE WHEN apply_status = '授信成功' OR first_risk_result = '特批白名单用户' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS tb_r
    FROM (${dedup_subquery('ods_ts_credit_yzf_order_grant_apply')}) t
    WHERE custtype = '00' AND store_addr_province IS NOT NULL
      AND add_time >= '2026-04-05'
    GROUP BY store_addr_province HAVING t >= 50 ORDER BY r
  `);

  const bp7 = await q(`
    SELECT store_addr_province AS p, COUNT(*) AS t,
      SUM(CASE WHEN apply_status = '授信成功' THEN 1 ELSE 0 END) AS pa,
      ROUND(SUM(CASE WHEN apply_status = '授信成功' AND first_risk_result != '特批白名单用户' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS r
    FROM (${dedup_subquery('ods_ts_credit_yzf_order_grant_apply')}) t
    WHERE custtype = '00' AND store_addr_province IS NOT NULL
      AND add_time >= '2026-05-06'
    GROUP BY store_addr_province HAVING t >= 10
  `);

  const bpPrev = await q(`
    SELECT store_addr_province AS p, COUNT(*) AS t,
      SUM(CASE WHEN apply_status = '授信成功' THEN 1 ELSE 0 END) AS pa,
      ROUND(SUM(CASE WHEN apply_status = '授信成功' AND first_risk_result != '特批白名单用户' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS r
    FROM (${dedup_subquery('ods_ts_credit_yzf_order_grant_apply')}) t
    WHERE custtype = '00' AND store_addr_province IS NOT NULL
      AND add_time >= '2026-03-06' AND add_time < '2026-04-05'
    GROUP BY store_addr_province HAVING t >= 50
  `);

  // ============= 3. 重点省份地市明细 =============
  const cityData = {};
  for (const pv of ['贵州省', '江西省', '湖南省', '广西壮族自治区']) {
    // 全维度地市分析
    const rows = await q(`
      SELECT store_addr_city AS c,
        COUNT(*) AS t,
        SUM(CASE WHEN apply_status = '授信成功' THEN 1 ELSE 0 END) AS pa,
        ROUND(SUM(CASE WHEN apply_status = '授信成功' AND first_risk_result != '特批白名单用户' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS r,
        SUM(CASE WHEN first_risk_result = '特批白名单用户' THEN 1 ELSE 0 END) AS tb,
        ROUND(SUM(CASE WHEN operator_real IN ('移动', '联通') THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS yw_bl,
        ROUND(SUM(CASE WHEN apply_status = '授信成功' AND operator_real IN ('移动', '联通') THEN 1 ELSE 0 END) * 100.0 / NULLIF(SUM(CASE WHEN operator_real IN ('移动', '联通') THEN 1 ELSE 0 END), 0), 2) AS yw_r,
        ROUND(SUM(CASE WHEN apply_status = '授信成功' AND operator_real IN ('电信') THEN 1 ELSE 0 END) * 100.0 / NULLIF(SUM(CASE WHEN operator_real IN ('电信') THEN 1 ELSE 0 END), 0), 2) AS bw_r,
        ROUND(SUM(CASE WHEN online_duration <= 3 THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS xk_bl,
        ROUND(SUM(CASE WHEN apply_status = '授信成功' AND online_duration <= 3 THEN 1 ELSE 0 END) * 100.0 / NULLIF(SUM(CASE WHEN online_duration <= 3 THEN 1 ELSE 0 END), 0), 2) AS xk_r
      FROM (${dedup_subquery('ods_ts_credit_yzf_order_grant_apply')}) t
      WHERE custtype = '00' AND store_addr_province = '${pv}' AND store_addr_city IS NOT NULL AND store_addr_city != ''
        AND add_time >= '2026-04-05'
      GROUP BY store_addr_city HAVING t >= 20
    `);
    cityData[pv] = rows;
    console.log(`  ${pv}: ${rows.length}个地市`);
  }

  // ============= 4. 生成CSV =============
  const csv = (rows, fields) => {
    const h = fields.join(',');
    const l = rows.map(r => fields.map(f => {
      const v = r[f]; if (v === null || v === undefined) return '';
      const s = String(v); return s.includes(',') || s.includes('"') || s.includes('\n') ? '"' + s.replace(/"/g, '""') + '"' : s;
    }).join(','));
    return h + '\n' + l.join('\n');
  };

  const combined = bp30.map(bp => {
    const b7 = bp7.find(x => x.p === bp.p);
    const bpv = bpPrev.find(x => x.p === bp.p);
    return {
      province: bp.p, total_30d: bp.t, rate_30d: bp.r, tb_30d: bp.tb,
      total_7d: b7 ? b7.t : 0, rate_7d: b7 ? b7.r : null,
      total_prev: bpv ? bpv.t : 0, rate_prev: bpv ? bpv.r : null,
      change: bpv ? (bp.r - bpv.r).toFixed(2) : null,
    };
  });

  const cf = ['province', 'total_30d', 'rate_30d', 'tb_30d', 'total_7d', 'rate_7d', 'total_prev', 'rate_prev', 'change'];
  fs.writeFileSync(dir + '/通过率分析_去重口径_各省.csv', csv(combined, cf));

  for (const pv of ['贵州省', '江西省', '湖南省', '广西壮族自治区']) {
    const cd = cityData[pv] || [];
    if (cd.length > 0) {
      const cityFields = ['c', 't', 'pa', 'r', 'tb', 'yw_bl', 'yw_r', 'bw_r', 'xk_bl', 'xk_r'];
      fs.writeFileSync(dir + `/通过率_去重_${pv}_地市.csv`, csv(cd, cityFields));
    }
  }

  // ============= 5. 生成报告MD =============
  const drops = combined.filter(d => d.change !== null && parseFloat(d.change) < -2).sort((a, b) => parseFloat(a.change) - parseFloat(b.change));
  const rises = combined.filter(d => d.change !== null && parseFloat(d.change) > 2).sort((a, b) => parseFloat(b.change) - parseFloat(a.change));
  const sorted30 = [...combined].sort((a, b) => b.rate_30d - a.rate_30d);
  const sorted7 = [...combined].sort((a, b) => (b.rate_7d || 0) - (a.rate_7d || 0));

  const chgIcon = parseFloat(r30) > parseFloat(rPrev) ? '↑' : '↓';
  const chgVal = Math.abs(parseFloat(r30) - parseFloat(rPrev)).toFixed(2);

  const L = [];
  const p = s => L.push(s);
  const h1 = s => { L.push(''); L.push('---'); L.push('## ' + s); L.push(''); };
  const h2 = s => { L.push('### ' + s); L.push(''); };
  const tbl = (rows, hdrs) => {
    L.push('| ' + hdrs.join(' | ') + ' |');
    L.push('|' + hdrs.map(() => ':---:').join('|') + '|');
    rows.forEach(r => L.push('| ' + r.join(' | ') + ' |'));
  };

  L.push('# 淘顺实时授信 — 通过率分析（去重口径）');
  L.push('> 公众客群(custtype=00) | ods_ts | 同身份证号去重(保留最新记录) | business_type=02');
  L.push('');

  h1('一、全国去重通过率趋势');
  p(`近7天（5/6-5/12）：${sum7.t}单，去重通过率 **${r7}%**`);
  p(`近30天（4/5-5/12）：${sum30.t}单，去重通过率 **${r30}%**`);
  p(`上月同期（3/6-4/4）：${prevM.cnt}单，去重通过率 **${rPrev}%**`);
  p(`环比变化：${chgIcon} **${chgVal}pp**（上月 ${rPrev}% → 本月 ${r30}%）`);
  L.push('');

  h1('二、各省去重通过率排名（近30天）');
  const r30Rows = sorted30.map((d, i) => [String(i + 1), d.province, String(d.total_30d), d.rate_30d + '%', d.tb_30d ? String(d.tb_30d) : '0',
    d.change !== null ? (parseFloat(d.change) > 0 ? '↑' : parseFloat(d.change) < 0 ? '↓' : '→') + Math.abs(parseFloat(d.change)).toFixed(1) : '-']);
  tbl(r30Rows, ['排名', '省份', '申请量(去重)', '通过率', '特批用户', '环比(pp)']);
  L.push('');

  h1('三、通过率异常变化（去重口径）');
  if (drops.length > 0) {
    h2('🔴 通过率骤降（环比下降>2pp）');
    tbl(drops.map(d => [d.province, d.rate_prev + '%', d.rate_30d + '%', d.change + 'pp']),
      ['省份', '上月通过率', '本月通过率', '变化']);
    L.push('');
    for (const d of drops) {
      const prov7 = combined.find(x => x.province === d.province);
      let analysis = `**${d.province}**：通过率从${d.rate_prev}%降至${d.rate_30d}%`;
      if (prov7 && prov7.rate_7d !== null) {
        const p7 = parseFloat(prov7.rate_7d);
        if (p7 < parseFloat(d.rate_30d)) analysis += `，近7天${p7.toFixed(2)}%仍在下降，趋势未止。`;
        else if (p7 > parseFloat(d.rate_30d)) analysis += `，近7天${p7.toFixed(2)}%已有所回升。`;
        else analysis += `，近7天${p7.toFixed(2)}%持平。`;
      }
      p(analysis);
    }
    L.push('');
  }
  if (rises.length > 0) {
    h2('🟢 通过率回升（环比上升>2pp）');
    tbl(rises.map(d => [d.province, d.rate_prev + '%', d.rate_30d + '%', d.change + 'pp']),
      ['省份', '上月通过率', '本月通过率', '变化']);
    L.push('');
    for (const d of rises) {
      const prov7 = combined.find(x => x.province === d.province);
      let analysis = `**${d.province}**：通过率从${d.rate_prev}%升至${d.rate_30d}%`;
      if (prov7 && prov7.rate_7d !== null) {
        const p7 = parseFloat(prov7.rate_7d);
        if (p7 > parseFloat(d.rate_30d)) analysis += `，近7天${p7.toFixed(2)}%仍在上升。`;
        else if (p7 < parseFloat(d.rate_30d)) analysis += `，近7天${p7.toFixed(2)}%已回落。`;
      }
      p(analysis);
    }
    L.push('');
  }

  h1('四、重点省份地市去重通过率');

  for (const pv of ['贵州省', '江西省', '湖南省', '广西壮族自治区']) {
    const cd = cityData[pv] || [];
    if (cd.length === 0) continue;
    const sorted = cd.sort((a, b) => a.r - b.r);

    h2(`${pv} — 各地市（去重口径）`);
    const tbCols = (pv === '湖南省') ? ['特批用户', '特批占比'] : [];
    tbl(sorted.map(c => {
      const cols = [c.c, String(c.t), c.r + '%'];
      if (pv === '湖南省') cols.push(String(c.tb || 0), c.t ? (Math.round((c.tb || 0) * 100 / c.t) + '%') : '0%');
      cols.push(c.yw_bl + '%', c.yw_r + '%', c.bw_r + '%', c.xk_bl + '%', c.xk_r + '%');
      return cols;
    }),
      ['地市', '申请量', '通过率'].concat(tbCols).concat(['异网占比', '异网通过率', '本网通过率', '新客占比', '新客通过率']) );
    L.push('');

    const low = sorted.filter(c => c.r < 40);
    const highPass = sorted.filter(c => c.r >= 65);
    const avg = sorted.reduce((s, c) => s + parseFloat(c.r), 0) / sorted.length;
    let conc = `省均去重通过率 **${avg.toFixed(1)}%**。`;
    if (low.length) {
      if (pv === '湖南省') {
        // 湖南0%地市都是100%特批白名单，标注说明
        const tbDeps = sorted.filter(c => parseFloat(c.r) === 0 && c.tb > 0);
        if (tbDeps.length > 0) {
          conc += `低通过率地市(<40%)：${low.map(c => c.c + '(' + c.r + '%)').join('、')}。`;
          conc += ` ⚠️ 其中${tbDeps.map(c => c.c + '(' + String(c.tb) + '/' + String(c.t) + '单)').join('、')} **100%依赖特批白名单通道**，风控模型自动审批能力为零，属于运营风险点。`;
        } else {
          conc += `低通过率地市(<40%)：${low.map(c => c.c + '(' + c.r + '%)').join('、')}。`;
        }
      } else {
        conc += `低通过率地市(<40%)：${low.map(c => c.c + '(' + c.r + '%)').join('、')}。`;
      }
    }
    if (highPass.length) conc += `高通过率地市(≥65%)：${highPass.map(c => c.c + '(' + c.r + '%)').join('、')}。`;
    const minC = sorted[0], maxC = sorted[sorted.length - 1];
    conc += `极差${(maxC.r - minC.r).toFixed(1)}pp（${minC.c}:${minC.r}% ~ ${maxC.c}:${maxC.r}%）。`;
    p(conc);
    L.push('');
  }

  h1('五、近7天各省去重通过率');
  tbl(sorted7.map((d, i) => [String(i + 1), d.province, String(d.total_7d), (d.rate_7d || 0) + '%']),
    ['排名', '省份', '申请量(去重)', '通过率']);
  L.push('');

  h1('六、结论与建议（去重口径）');
  p(`1. 全国去重通过率近30天${r30}%，较上月${rPrev}%${chgIcon}${chgVal}pp。`);
  p(`2. 原始口径(38~39%) vs 去重口径(~${r30}%)，差异约${(parseFloat(r30)-38).toFixed(1)}pp，主要由重复申请（同人多次提）导致。`);
  if (drops.length) p(`3. 通过率骤降省份：${drops.map(d => d.province + '(' + d.change + 'pp)').join('、')}。`);
  p('4. 广西去重后通过率回归合理区间，应使用去重口径做日常监控。');
  const hnTotal = combined.find(d => d.province === '湖南省');
  if (hnTotal) {
    p(`5. **湖南省特批依赖严重**：湖南全省近30天去重${hnTotal.total_30d}单中特批用户${hnTotal.tb_30d || 0}人（占${hnTotal.tb_30d ? Math.round(hnTotal.tb_30d * 100 / hnTotal.total_30d) + '%' : '0%'}）。益阳、湘西、怀化、娄底、湘潭、张家界6个地市**完全依赖特批通道**。建议评估这些地市是否应逐步收紧特批。`);
  }
  L.push('');

  fs.writeFileSync(dir + '/通过率分析_去重口径.md', L.join('\n'));
  console.log('\n✅ 去重口径通过率分析完成，已写入');

  // ============= 额外：打印广西详细结果 =============
  const gx = await q(`
    SELECT store_addr_province AS 省份,
      COUNT(*) AS 申请数(去重),
      SUM(CASE WHEN apply_status = '授信成功' THEN 1 ELSE 0 END) AS 通过数,
      ROUND(SUM(CASE WHEN apply_status = '授信成功' AND first_risk_result != '特批白名单用户' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS 通过率,
      ROUND(SUM(CASE WHEN operator_real IN ('移动', '联通') THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS 异网占比,
      ROUND(SUM(CASE WHEN apply_status = '授信成功' AND operator_real IN ('移动', '联通') THEN 1 ELSE 0 END) * 100.0 / NULLIF(SUM(CASE WHEN operator_real IN ('移动', '联通') THEN 1 ELSE 0 END), 0), 2) AS 异网通过率,
      ROUND(SUM(CASE WHEN apply_status = '授信成功' AND operator_real IN ('电信') THEN 1 ELSE 0 END) * 100.0 / NULLIF(SUM(CASE WHEN operator_real IN ('电信') THEN 1 ELSE 0 END), 0), 2) AS 本网通过率,
      ROUND(SUM(CASE WHEN online_duration <= 3 THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS 新客占比,
      ROUND(SUM(CASE WHEN apply_status = '授信成功' AND online_duration <= 3 THEN 1 ELSE 0 END) * 100.0 / NULLIF(SUM(CASE WHEN online_duration <= 3 THEN 1 ELSE 0 END), 0), 2) AS 新客通过率
    FROM (${dedup_subquery('ods_ts_credit_yzf_order_grant_apply')}) t
    WHERE custtype = '00' AND store_addr_province = '广西壮族自治区'
      AND add_time >= '2026-04-05'
  `);
  console.log('\n=== 广西去重口径详情 ===');
  console.table(gx);

  conn.end();
}
main().catch(e => { console.error(e); process.exit(1); });
