const mysql = require('mysql2/promise');
const fs = require('fs');

async function main() {
  const conn = await mysql.createConnection({
    host: '47.119.181.195', port: 9030, user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)", database: 'ods',
  });
  const q = async (sql) => { const [r] = await conn.query(sql); return r; };
  const dir = '/mnt/d/desktop/翼支付交流_门店代理商分析';

  // 1. National trends
  const national = await q(`
    select date_format(add_time, '%Y-%m-%d') as dt,
      count(*) as total,
      sum(case when apply_status='授信成功' then 1 else 0 end) as pass,
      round(sum(case when apply_status='授信成功' then 1 else 0 end)*100.0/count(*),2) as rate
    from ods_ts_credit_yzf_order_grant_apply
    where custtype='00' and store_addr_province is not null
      and add_time >= '2026-04-13'
    group by dt order by dt
  `);

  const sum7 = national.filter(r => r.dt >= '2026-05-06').reduce((s,x)=>({t:s.t+x.total,p:s.p+x.pass}),{t:0,p:0});
  const sum30 = national.reduce((s,x)=>({t:s.t+x.total,p:s.p+x.pass}),{t:0,p:0});
  const r7 = sum7.t ? (sum7.p/sum7.t*100).toFixed(2) : 0;
  const r30 = sum30.t ? (sum30.p/sum30.t*100).toFixed(2) : 0;

  const prevMRows = await q(`
    select count(*) as cnt, sum(case when apply_status='授信成功' then 1 else 0 end) as pass_cnt
    from ods_ts_credit_yzf_order_grant_apply
    where custtype='00' and store_addr_province is not null
      and add_time>='2026-03-13' and add_time<'2026-04-13'
  `);
  const prevM = prevMRows[0] || {cnt:0,pass_cnt:0};
  const rPrev = prevM.cnt ? (prevM.pass_cnt/prevM.cnt*100).toFixed(2) : 0;
  console.log(`7天:${sum7.t}单 ${r7}% | 30天:${sum30.t}单 ${r30}% | 上月:${prevM.t}单 ${rPrev}%`);

  // 2. By province - 30 days + 7 days + prev month
  const bp30 = await q(`
    select store_addr_province as p,
      count(*) as t, sum(case when apply_status='授信成功' then 1 else 0 end) as pa,
      round(sum(case when apply_status='授信成功' then 1 else 0 end)*100.0/count(*),2) as r,
      sum(case when apply_msg='综合评分不通过' then 1 else 0 end) as rr
    from ods_ts_credit_yzf_order_grant_apply
    where custtype='00' and store_addr_province is not null
      and add_time>='2026-04-13'
    group by store_addr_province having t>=50 order by t desc
  `);
  const bp7 = await q(`
    select store_addr_province as p, count(*) as t,
      sum(case when apply_status='授信成功' then 1 else 0 end) as pa,
      round(sum(case when apply_status='授信成功' then 1 else 0 end)*100.0/count(*),2) as r
    from ods_ts_credit_yzf_order_grant_apply
    where custtype='00' and store_addr_province is not null
      and add_time>='2026-05-06'
    group by store_addr_province having t>=10
  `);
  const bpPrev = await q(`
    select store_addr_province as p, count(*) as t,
      sum(case when apply_status='授信成功' then 1 else 0 end) as pa,
      round(sum(case when apply_status='授信成功' then 1 else 0 end)*100.0/count(*),2) as r
    from ods_ts_credit_yzf_order_grant_apply
    where custtype='00' and store_addr_province is not null
      and add_time>='2026-03-13' and add_time<'2026-04-13'
    group by store_addr_province having t>=50
  `);

  // City-level for key provinces
  const cityData = {};
  for (const pv of ['贵州省','江西省','湖南省','广西壮族自治区']) {
    const rows = await q(`
      select store_addr_city as c,
        count(*) as t, sum(case when apply_status='授信成功' then 1 else 0 end) as pa,
        round(sum(case when apply_status='授信成功' then 1 else 0 end)*100.0/count(*),2) as r,
        sum(case when apply_msg='综合评分不通过' then 1 else 0 end) as rr
      from ods_ts_credit_yzf_order_grant_apply
      where custtype='00' and store_addr_province='${pv}' and store_addr_city is not null and store_addr_city!=''
        and add_time>='2026-04-13'
      group by store_addr_city having t>=20
    `);
    cityData[pv] = rows;
    console.log(`  ${pv}: ${rows.length}个地市`);
  }

  // 3. Build combined data + CSVs
  const csv = (rows, fields) => {
    const h = fields.join(',');
    const l = rows.map(r => fields.map(f => {
      const v = r[f]; if (v===null||v===undefined) return '';
      const s = String(v); return s.includes(',')||s.includes('"')||s.includes('\n') ? '"'+s.replace(/"/g,'""')+'"' : s;
    }).join(','));
    return h+'\n'+l.join('\n');
  };

  const combined = bp30.map(bp => {
    const b7 = bp7.find(x => x.p === bp.p);
    const bpv = bpPrev.find(x => x.p === bp.p);
    return {
      province: bp.p, total_30d: bp.t, rate_30d: bp.r,
      total_7d: b7 ? b7.t : 0, rate_7d: b7 ? b7.r : null,
      total_prev: bpv ? bpv.t : 0, rate_prev: bpv ? bpv.r : null,
      change: bpv ? (bp.r - bpv.r).toFixed(2) : null,
      risk_reject_30d: bp.rr
    };
  });

  const cf = ['province','total_30d','rate_30d','total_7d','rate_7d','total_prev','rate_prev','change'];
  fs.writeFileSync(dir+'/通过率分析_淘顺各省.csv', csv(combined, cf));

  for (const pv of ['贵州省','江西省','湖南省','广西壮族自治区']) {
    const cd = cityData[pv] || [];
    if (cd.length > 0) {
      fs.writeFileSync(dir+`/通过率_${pv}_地市.csv`, csv(cd, ['c','t','pa','r','rr']));
    }
  }

  // 4. Build MD
  const drops = combined.filter(d => d.change !== null && parseFloat(d.change) < -2).sort((a,b) => parseFloat(a.change) - parseFloat(b.change));
  const rises = combined.filter(d => d.change !== null && parseFloat(d.change) > 2).sort((a,b) => parseFloat(b.change) - parseFloat(a.change));
  const sorted30 = [...combined].sort((a,b) => b.rate_30d - a.rate_30d);
  const sorted7 = [...combined].sort((a,b) => (b.rate_7d||0) - (a.rate_7d||0));

  const chgIcon = parseFloat(r30) > parseFloat(rPrev) ? '↑' : '↓';
  const chgVal = Math.abs(parseFloat(r30) - parseFloat(rPrev)).toFixed(2);

  const L = [];
  const p = s => L.push(s);
  const h1 = s => { L.push(''); L.push('---'); L.push('## '+s); L.push(''); };
  const h2 = s => { L.push('### '+s); L.push(''); };
  const tbl = (rows, hdrs) => {
    L.push('| '+hdrs.join(' | ')+' |');
    L.push('|'+hdrs.map(()=>':---:').join('|')+'|');
    rows.forEach(r => L.push('| '+r.join(' | ')+' |'));
  };

  L.push('# 淘顺实时授信 — 通过率分析');
  L.push('> 公众客群(custtype=00) | ods_ts_credit_yzf_order_grant_apply');
  L.push('');

  h1('一、全国通过率趋势');
  p(`近7天（5/6-5/12）：${sum7.t}单，通过率 **${r7}%**`);
  p(`近30天（4/13-5/12）：${sum30.t}单，通过率 **${r30}%**`);
  p(`上月同期（3/13-4/12）：${prevM.t}单，通过率 **${rPrev}%**`);
  p(`环比变化：${chgIcon} **${chgVal}pp**（上月 ${rPrev}% → 本月 ${r30}%）`);
  L.push('');

  h1('二、各省通过率排名（近30天）');
  const r30Rows = sorted30.map((d,i)=>[String(i+1),d.province,String(d.total_30d),d.rate_30d+'%',
    d.change!==null ? (parseFloat(d.change)>0?'↑':parseFloat(d.change)<0?'↓':'→')+Math.abs(parseFloat(d.change)).toFixed(1) : '-']);
  tbl(r30Rows, ['排名','省份','申请量','通过率','环比(pp)']);
  L.push('');

  h1('三、通过率异常变化');
  if (drops.length > 0) {
    h2('🔴 通过率骤降（环比下降>2pp）');
    tbl(drops.map(d=>[d.province,d.rate_prev+'%',d.rate_30d+'%',d.change+'pp']),
      ['省份','上月通过率','本月通过率','变化']);
    L.push('');
    
    // Detailed analysis for each dropped province
    for (const d of drops) {
      const provInfo = combined.find(x => x.province === d.province);
      const nowRate = parseFloat(d.rate_30d);
      const prevRate = parseFloat(d.rate_prev);
      const changeVal = parseFloat(d.change);
      
      // Get 7-day rate to see if it's continuing to drop
      const prov7 = provInfo ? provInfo.rate_7d : null;
      
      let analysis = `**${d.province}**：通过率从${d.rate_prev}%降至${d.rate_30d}%`;
      
      // Check if 7-day rate is even lower (continuing drop) or recovering
      if (prov7 !== null && prov7 !== undefined) {
        const p7 = parseFloat(prov7);
        if (p7 < nowRate) analysis += `，近7天通过率${p7.toFixed(2)}%仍在下降，趋势未止。`;
        else if (p7 > nowRate) analysis += `，但近7天通过率${p7.toFixed(2)}%已有所回升。`;
        else analysis += `，近7天通过率${p7.toFixed(2)}%与30天均值持平。`;
      }
      
      // Now try to analyze the reason by looking at reject patterns
      // High risk_reject_30d share = strategy tightening
      // Low share but still low pass = external rejection
      const riskPct = provInfo ? (provInfo.risk_reject_30d/d.total_30d*100) : 0;
      const otherPct = 100 - nowRate - riskPct;
      
      if (riskPct > 60) {
        analysis += ` 风控拒绝占比${riskPct.toFixed(1)}%（占比较高），说明我方规则收紧或客群质量整体下降，是导致通过率下滑的主因。`;
      } else if (otherPct > 10) {
        analysis += ` 其他拒绝（含翼支付、外部规则）占比${otherPct.toFixed(1)}%，说明外部数据源或合作方策略变化影响较大。`;
      } else {
        analysis += ` 风控拒绝占比${riskPct.toFixed(1)}%，其他拒绝占比${otherPct.toFixed(1)}%，下降主要由我方风控规则导致。`;
      }
      
      p(analysis);
    }
    L.push('');
  }
  if (rises.length > 0) {
    h2('🟢 通过率回升（环比上升>2pp）');
    tbl(rises.map(d=>[d.province,d.rate_prev+'%',d.rate_30d+'%',d.change+'pp']),
      ['省份','上月通过率','本月通过率','变化']);
    L.push('');
    
    for (const d of rises) {
      const provInfo = combined.find(x => x.province === d.province);
      const nowRate = parseFloat(d.rate_30d);
      const prov7 = provInfo ? provInfo.rate_7d : null;
      
      let analysis = `**${d.province}**：通过率从${d.rate_prev}%升至${d.rate_30d}%`;
      if (prov7 !== null && prov7 !== undefined) {
        const p7 = parseFloat(prov7);
        if (p7 > nowRate) analysis += `，近7天通过率${p7.toFixed(2)}%仍在上升，趋势持续。`;
        else if (p7 < nowRate) analysis += `，但近7天通过率${p7.toFixed(2)}%已有所回落。`;
      }
      
      const riskPct = provInfo ? (provInfo.risk_reject_30d/d.total_30d*100) : 0;
      if (riskPct < 50) {
        analysis += ` 风控拒绝仅占${riskPct.toFixed(1)}%，说明通过率回升主要来自客户质量改善而非策略放宽，风险相对可控。`;
      } else {
        analysis += ` 风控拒绝仍占${riskPct.toFixed(1)}%，回升幅度有限，策略仍有收紧空间。`;
      }
      p(analysis);
    }
    L.push('');
  }

  h1('四、拒绝原因拆解（近30天）');
  const rejRows = combined.map(d => {
    const other = d.total_30d - (d.rate_30d/100*d.total_30d) - d.risk_reject_30d;
    return [d.province, String(d.total_30d), d.rate_30d+'%',
      (d.risk_reject_30d/d.total_30d*100).toFixed(1)+'%',
      (other/d.total_30d*100).toFixed(1)+'%'];
  });
  tbl(rejRows, ['省份','申请量','通过率','风控拒绝','其他拒绝']);
  L.push('');

  h1('五、重点省份地市通过率');

  for (const pv of ['贵州省','江西省','湖南省','广西壮族自治区']) {
    const cd = cityData[pv] || [];
    if (cd.length === 0) continue;
    const sorted = cd.sort((a,b) => a.r - b.r);

    h2(`${pv} — 各地市通过率`);
    tbl(sorted.map(c=>[c.c,String(c.t),c.r+'%']), ['地市','申请量','通过率']);
    L.push('');

    const low = sorted.filter(c => c.r < 30);
    const highPass = sorted.filter(c => c.r >= 60);
    const avg = sorted.reduce((s,c) => s+parseFloat(c.r), 0)/sorted.length;
    let conc = `省均通过率${avg.toFixed(1)}%。`;
    if (low.length) conc += `**低通过率地市**（<$30%）：${low.map(c=>c.c+'('+c.r+'%)').join('、')}。`;
    if (highPass.length) conc += `**高通过率地市**（≥60%）：${highPass.map(c=>c.c+'('+c.r+'%)').join('、')}。`;
    const minC = sorted[0], maxC = sorted[sorted.length-1];
    conc += `极差${(maxC.r-minC.r).toFixed(1)}pp（${minC.c}:${minC.r}% ~ ${maxC.c}:${maxC.r}%）。`;
    p(conc);
    L.push('');
  }

  h1('六、近7天各省通过率');
  tbl(sorted7.map((d,i)=>[String(i+1),d.province,String(d.total_7d),(d.rate_7d||0)+'%']), ['排名','省份','申请量','通过率']);
  L.push('');

  h1('七、结论与建议');
  p(`1. 全国通过率近30天${r30}%，环比${chgIcon}${chgVal}pp${parseFloat(r30)>parseFloat(rPrev)?'（上升）':'（下降）'}。`);
  if (drops.length) p(`2. 通过率骤降省份：${drops.map(d=>d.province+'('+d.change+'pp)').join('、')}，建议排查策略变化。`);
  p('3. 贵州、江西、湖南、广西四省逾期率最高（10%+），需结合通过率综合评估策略松紧度。');
  L.push('');

  fs.writeFileSync(dir+'/通过率分析.md', L.join('\n'));
  console.log('\n✅ 通过率分析完成');
  conn.end();
}
main().catch(e => { console.error(e); process.exit(1); });
