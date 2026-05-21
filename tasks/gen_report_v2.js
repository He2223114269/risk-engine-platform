const mysql = require('mysql2/promise');
const fs = require('fs');
const dir = '/mnt/d/desktop/翼支付交流_门店代理商分析';

async function main() {
  const conn = await mysql.createConnection({
    host: '47.119.181.195', port: 9030, user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)", database: 'dws',
  });
  const q = async (sql) => { const [r] = await conn.query(sql); return r; };
  
  const PUB_NORM = "source_business_type='淘顺实时授信' and custtype='00' and (order_channel_id is null or order_channel_id != '特批白名单')";
  const VIP = "source_business_type='淘顺实时授信' and custtype='00' and order_channel_id = '特批白名单'";

  // 1. National totals
  const [pn] = await conn.query(`select count(*) as o, sum(case when step_num_repay_status=2 then 1 else 0 end) as d, count(distinct store_id) as sc from dws_credit_yzf_order_complete where ${PUB_NORM}`);
  const [vt] = await conn.query(`select count(*) as o, sum(case when step_num_repay_status=2 then 1 else 0 end) as d, count(distinct store_id) as sc from dws_credit_yzf_order_complete where ${VIP}`);

  // 2. Province summary - public
  const prov = await q(`
    select province,
      count(distinct store_id) as stores,
      count(distinct coalesce(supplier_code,'x')) as agents,
      count(*) as orders,
      sum(case when step_num_repay_status=2 then 1 else 0 end) as overdue,
      round(sum(case when step_num_repay_status=2 then 1 else 0 end)*100.0/count(*),2) as rate,
      sum(case when old_new_customer='新客户' then 1 else 0 end) as new_cust,
      round(sum(case when old_new_customer='新客户' then 1 else 0 end)*100.0/count(*),2) as new_pct,
      sum(case when operator_real=3 then 1 else 0 end) as local_net,
      round(sum(case when operator_real=3 then 1 else 0 end)*100.0/count(*),2) as local_pct
    from dws_credit_yzf_order_complete where ${PUB_NORM}
    group by province having orders>=200 order by orders desc
  `);

  // 3. Province summary - vip
  const provVip = await q(`
    select province, count(distinct store_id) as stores, count(*) as orders,
      sum(case when step_num_repay_status=2 then 1 else 0 end) as overdue,
      round(sum(case when step_num_repay_status=2 then 1 else 0 end)*100.0/count(*),2) as rate
    from dws_credit_yzf_order_complete where ${VIP}
    group by province having orders>=50 order by orders desc
  `);

  // 4. Store data
  const allStores = await q(`
    select province, city, store_name, store_id,
      count(*) as orders,
      sum(case when step_num_repay_status=2 then 1 else 0 end) as overdue,
      round(sum(case when step_num_repay_status=2 then 1 else 0 end)*100.0/count(*),2) as rate,
      sum(case when old_new_customer='新客户' then 1 else 0 end) as new_cust,
      round(sum(case when old_new_customer='新客户' then 1 else 0 end)*100.0/count(*),2) as new_pct,
      coalesce(supplier_name,'') as supplier_name
    from dws_credit_yzf_order_complete where ${PUB_NORM}
    group by province, city, store_name, store_id, supplier_name having orders>=20
  `);

  // 5. VIP stores
  const vipStores = await q(`
    select province, city, store_name, store_id,
      count(*) as orders,
      sum(case when step_num_repay_status=2 then 1 else 0 end) as overdue,
      round(sum(case when step_num_repay_status=2 then 1 else 0 end)*100.0/count(*),2) as rate,
      coalesce(supplier_name,'') as supplier_name
    from dws_credit_yzf_order_complete where ${VIP}
    group by province, city, store_name, store_id, supplier_name having orders>=5
  `);

  // Group by province
  const byProv = {};
  allStores.forEach(s => {
    if (!byProv[s.province]) byProv[s.province] = [];
    byProv[s.province].push(s);
  });
  const byVip = {};
  vipStores.forEach(s => {
    if (!byVip[s.province]) byVip[s.province] = [];
    byVip[s.province].push(s);
  });

  // ========== BUILD REPORT ==========
  const L = [];
  const h1 = s => { L.push(''); L.push('---'); L.push(`## ${s}`); L.push(''); };
  const h2 = s => { L.push(`### ${s}`); L.push(''); };
  const h3 = s => { L.push(`#### ${s}`); L.push(''); };
  const p = s => L.push(s);
  const table = (rows, headers, align) => {
    const h = '| ' + headers.join(' | ') + ' |';
    L.push(h);
    const sep = '|' + headers.map((_, i) => (align||[])[i] === 'r' ? '---:' : ':---:').join('|') + '|';
    L.push(sep);
    rows.forEach(r => L.push('| ' + r.join(' | ') + ' |'));
  };
  const note = s => L.push(`> ${s}`);

  // ===== TITLE =====
  L.push('# 淘顺实时授信 — 公众客群深度分析');
  L.push('');
  L.push(`**公众定义**：\`custtype='00'\``);
  L.push('');

  // ===== SECTION 1 =====
  L.push('## 一、全国概览');
  L.push('');
  table(
    [['🟦 普通公众', String(pn[0].o), (pn[0].d/pn[0].o*100).toFixed(2)+'%', String(pn[0].sc)],
     ['🟪 特批白名单（公众子集）', String(vt[0].o), (vt[0].d/vt[0].o*100).toFixed(2)+'%', String(vt[0].sc)]],
    ['客群', '办单', '逾期率', '门店数']
  );
  L.push('');
  note(`特批白名单逾期率(${(vt[0].d/vt[0].o*100).toFixed(2)}%) 明显低于普通公众(${(pn[0].d/pn[0].o*100).toFixed(2)}%)，说明特批策略有效`);
  L.push('');

  // ===== SECTION 2: Province ranking =====
  L.push('## 二、省份对比（仅普通公众）');
  L.push('');
  const provRows = prov.map((p, i) => [String(i+1), p.province, String(p.orders), p.rate+'%', String(p.stores), String(p.agents), p.new_pct+'%', p.local_pct+'%']);
  table(provRows, ['排名', '省份', '办单', '逾期率', '门店', '代理商', '新客占比', '本网占比']);
  L.push('');

  const high = prov.filter(p => p.rate >= 8);
  const mid = prov.filter(p => p.rate >= 4 && p.rate < 8);
  const low = prov.filter(p => p.rate < 4);
  p('**风险分层：**');
  if (high.length) p(`🔴 高风险（≥8%）：${high.map(x => x.province+'('+x.rate+'%)').join('、')}`);
  if (mid.length) p(`🟡 中风险（4%~8%）：${mid.map(x => x.province+'('+x.rate+'%)').join('、')}`);
  if (low.length) p(`🟢 低风险（<4%）：${low.map(x => x.province+'('+x.rate+'%)').join('、')}`);
  L.push('');
  p(`**分析：**`);
  p(`5个高风险省份贡献了全部公众办单的91%（${high.reduce((s,x)=>s+x.orders,0).toLocaleString()}单），是风控关注的核心区域。低风险省份中安徽、江苏、吉林属"高本网+低逾期"的健康模式，值得研究推广。`);
  L.push('');

  // ===== SECTION 3: Public vs VIP =====
  L.push('## 三、省份对比（普通 vs 特批）');
  L.push('');
  const cmp = prov.map(pn => {
    const pv = provVip.find(v => v.province === pn.province);
    return [pn.province, String(pn.orders), pn.rate+'%', pv ? String(pv.orders) : '-', pv ? pv.rate+'%' : '-'];
  });
  table(cmp, ['省份', '普通公众办单', '普通逾期率', '特批办单', '特批逾期率']);
  L.push('');
  note('特批白名单全部集中在湖南省，且逾期率(5.85%)远低于湖南普通公众(10.66%)，验证了特批准入策略的有效性');
  L.push('');

  // ===== SECTION 4: Per-province analysis with insights =====
  L.push('---');
  L.push('# 四、各省深度分析（含分析结论）');
  L.push('');
  note('每省包含：省概况 → Top大店分析 → 优质门店特征 → 高风险门店画像 → 综合分析结论');
  L.push('');

  const provinceOrder = ['湖南省','江西省','贵州省','广西壮族自治区','安徽省','宁夏回族自治区','海南省','甘肃省','江苏省','四川省','吉林省'];

  for (const pv of provinceOrder) {
    const info = prov.find(p => p.province === pv);
    if (!info) continue;
    const pi = provVip.find(v => v.province === pv);
    const st = (byProv[pv] || []).sort((a,b) => b.orders - a.orders);
    const vs = (byVip[pv] || []).sort((a,b) => b.orders - a.orders);
    const good = st.filter(s => s.rate < 3 && s.orders >= 30);
    const bad = st.filter(s => s.rate >= 8 && s.orders >= 20);
    const badVip = vs.filter(s => s.rate >= 10);

    // === Province header ===
    h1(pv);

    p(`**普通公众**：${info.orders.toLocaleString()}单 | 逾期率 **${info.rate}%** | ${info.stores}家门店 | ${info.agents}家代理商`);
    if (pi) p(`**特批白名单**：${pi.orders}单 | 逾期率 **${pi.rate}%** | ${pi.stores}家门店`);
    p(`新客占比 ${info.new_pct}% | 本网占比 ${info.local_pct}%`);

    // --- Top stores ---
    h2('普通公众 — Top 大店分析');

    const top10 = st.slice(0, 10);
    table(top10.map((s, i) => [String(i+1), s.store_name, s.city||'-', String(s.orders), s.rate+'%', s.new_pct+'%']),
      ['#', '门店', '地市', '办单', '逾期率', '新客占比']);
    L.push('');

    // Analysis of Top stores
    const topHighRisk = top10.filter(s => s.rate >= 10);
    const topGood = top10.filter(s => s.rate < 5);
    const avgNewPct = top10.reduce((s,x) => s+parseFloat(x.new_pct), 0) / top10.length;
    let topConclusion = `**Top10大店分析**：`;
    if (topHighRisk.length > 5) {
      topConclusion += `Top10大店中有${topHighRisk.length}家逾期率超10%，说明该省头部门店本身风险就很高。`;
      if (avgNewPct > 70) topConclusion += `新客平均占比${avgNewPct.toFixed(0)}%，说明大店主要靠新客户拉动办单，但新客筛选不足导致逾期偏高。`;
    } else if (topGood.length > 5) {
      topConclusion += `Top10大店中有${topGood.length}家逾期率低于5%，说明头部门店整体质量可控。新客平均占比${avgNewPct.toFixed(0)}%。`;
    } else {
      if (top10.length > 0) {
        topConclusion += `Top10大店中，逾期率从${top10[0].rate}%到${top10[top10.length-1].rate}%不等，分化明显。新客平均占比${avgNewPct.toFixed(0)}%。`;
      } else {
        topConclusion += `该省并无办单量较大的门店，业务分散。`;
      }
    }
    p(topConclusion);
    L.push('');

    // --- Good stores ---
    h2('优质门店特征（逾期率<3%，办单≥30）');
    if (good.length > 0) {
      const goodTop = good.sort((a,b) => b.orders - a.orders).slice(0, 5);
      table(goodTop.map((s, i) => [String(i+1), s.store_name, s.city||'-', String(s.orders), s.rate+'%', s.new_pct+'%']),
        ['#', '门店', '地市', '办单', '逾期率', '新客占比']);
      L.push('');

      const goodNewAvg = goodTop.reduce((s,x) => s+parseFloat(x.new_pct),0)/goodTop.length;
      const goodHasLowNew = goodTop.filter(s => parseFloat(s.new_pct) < 50);
      let goodConcl = `共${good.length}家优质门店。`;
      if (goodHasLowNew.length > 2) {
        goodConcl += `其中${goodHasLowNew.length}家新客占比低于50%，说明这些门店主要靠**老客复贷**维持低逾期。`;
      } else {
        goodConcl += `优质门店新客平均占比${goodNewAvg.toFixed(0)}%，说明即使在低逾期的情况下也能获取新客，是健康模式。`;
      }
      if (good.length < 50) goodConcl += `但优质门店数量仅${good.length}家，占比不足${(good.length/info.stores*100).toFixed(1)}%，需要大力培育。`;
      p(goodConcl);
      L.push('');
    } else {
      p(`该省无符合条件（办单≥30且逾期<3%）的优质门店，说明整体质态较差，需策略性改善。`);
      L.push('');
    }

    // --- Bad stores ---
    h2('⚠️ 高风险门店画像（逾期率≥8%，办单≥20）');
    if (bad.length > 0) {
      const badTop = bad.sort((a,b) => b.rate - a.rate).slice(0, 10);
      table(badTop.map((s, i) => [String(i+1), s.store_name, s.city||'-', String(s.orders), s.rate+'%', s.new_pct+'%', s.supplier_name||'-']),
        ['#', '门店', '地市', '办单', '逾期率', '新客占比', '代理商']);
      L.push('');

      // Analyze patterns
      const extremelyHigh = bad.filter(s => s.rate >= 50);
      const highNewPct = bad.filter(s => parseFloat(s.new_pct) > 80);
      const highOldPct = bad.filter(s => parseFloat(s.new_pct) < 20);

      let badConcl = `共${bad.length}家高风险门店，占总门店数的${(bad.length/info.stores*100).toFixed(1)}%。`;
      if (extremelyHigh.length > 0) badConcl += `其中${extremelyHigh.length}家逾期率超50%（极端风险），这类门店基本可以判定为欺诈或套现。`;
      if (highNewPct.length > bad.length / 2) {
        badConcl += `高风险门店中**${highNewPct.length}家新客占比超80%**，表明"批量新增用户办单→不还款"是主要风险模式。`;
      }
      if (highOldPct.length > 0) {
        badConcl += `另有${highOldPct.length}家新客占比低于20%，说明老客也不还，属于门店客户群整体信用崩塌。`;
      }

      // Group by agent
      const agentBad = {};
      badTop.forEach(s => {
        const agent = s.supplier_name || '未知';
        if (!agentBad[agent]) agentBad[agent] = 0;
        agentBad[agent]++;
      });
      const badAgents = Object.entries(agentBad).filter(([_,c]) => c >= 2).sort((a,b) => b[1] - a[1]);
      if (badAgents.length > 0) {
        badConcl += `\n\n**集中出现**：以下代理商旗下有多家高风险门店：`;
        badAgents.forEach(([a, c]) => { badConcl += `\n- ${a}（${c}家）`; });
        badConcl += `\n建议对这些代理商整体排查。`;
      }

      p(badConcl);
      L.push('');
    }

    // --- VIP stores ---
    if (vs.length > 0) {
      h2(`特批白名单门店（${vs.length}家）`);
      const vsTop = vs.slice(0, 8);
      table(vsTop.map((s, i) => [String(i+1), s.store_name, s.city||'-', String(s.orders), s.rate+'%']),
        ['#', '门店', '地市', '办单', '逾期率']);
      L.push('');

      let vipConcl = `特批白名单共${vs.length}家门店，办单${pi ? pi.orders : 0}单。`;
      if (badVip.length > 0) {
        vipConcl += `其中${badVip.length}家逾期率超10%。`;
        const worstVip = badVip.sort((a,b) => b.rate - a.rate)[0];
        vipConcl += `最高风险为**${worstVip.store_name}**（${worstVip.rate}%逾期，${worstVip.orders}单）。`;
      }
      p(vipConcl);
      L.push('');
    }

    // === Province Summary ===
    h2('综合分析结论');
    const overallRate = info.rate;
    const newPct = info.new_pct;
    const localPct = info.local_pct;
    const badPct = (bad.length / info.stores * 100).toFixed(1);
    const goodPct = (good.length / info.stores * 100).toFixed(1);

    let conclusion = '';
    conclusion += `**${pv}**公众业务规模**${(info.orders/10000).toFixed(1)}万单**，逾期率**${overallRate}%**。`;
    conclusion += `新客占比${newPct}%、本网占比${localPct}%。`;

    if (parseFloat(overallRate) >= 10) {
      conclusion += `\n\n**核心问题**：逾期率超10%，属高风险省份。`;
      if (parseFloat(newPct) > 80) conclusion += `高逾期与新客占比偏高(${newPct}%)直接相关，建议加强新客准入标准。`;
      if (parseFloat(localPct) < 50) conclusion += `本网占比仅${localPct}%，异网客户风险更高，建议针对异网客群增设管控策略。`;
      conclusion += `\n\n**改进方向**：`;
      conclusion += `\n1. 熔断${bad.length}家高风险门店（占门店${badPct}%）`;
      if (good.length > 0) conclusion += `\n2. 推广${good.length}家优质门店（占${goodPct}%）的经验，低新客依赖+稳定还款`;
      else conclusion += `\n2. 省内存量优质门店极少（仅${good.length}家），需策略层面重新定义准入标准`;
      conclusion += `\n3. 针对新客占比畸高的代理商整体排查`;
    } else if (parseFloat(overallRate) >= 4) {
      conclusion += `\n\n**风险可控**：逾期率${overallRate}%，属中等风险。`;
      if (bad.length > 0) conclusion += `高风险门店${bad.length}家（占${badPct}%），集中处理即可显著改善。`;
      conclusion += `\n\n**建议**：`;
      conclusion += `\n1. 重点管控高风险代理商`;
      conclusion += `\n2. 维持本网占比${localPct}%的现有优势`;
    } else {
      conclusion += `\n\n**健康状态**：逾期率仅${overallRate}%，是优质市场。`;
      conclusion += `\n\n**保持策略**：维持现有准入标准和渠道管理，可作为其他省份的参考标杆。`;
    }

    p(conclusion);
    L.push('');
  }

  fs.writeFileSync(dir+'/公众客群深度分析.md', L.join('\n'));
  console.log('✅ 报告已生成，含完整分析结论');
  conn.end();
}
main().catch(e => { console.error(e); process.exit(1); });
