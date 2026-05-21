const mysql = require('mysql2/promise');
const fs = require('fs');

async function main() {
  const conn = await mysql.createConnection({
    host: '47.119.181.195', port: 9030, user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)", database: 'dws',
  });
  const q = async (sql) => { const [r] = await conn.query(sql); return r; };

  const dir = '/mnt/d/desktop/翼支付交流_门店代理商分析';

  // ========== Base SQL snippets ==========
  // 公众(普通): custtype='00' AND 非特批
  const PUB_NORM = "source_business_type='淘顺实时授信' and custtype='00' and (order_channel_id is null or order_channel_id != '特批白名单')";
  // 公众(含特批): custtype='00'
  const PUB_ALL = "source_business_type='淘顺实时授信' and custtype='00'";
  // 特批白名单: subset of 公众
  const VIP = "source_business_type='淘顺实时授信' and custtype='00' and order_channel_id = '特批白名单'";

  // ========== 1. 全国对比概览 ==========
  console.log('1. 全国对比概览...');
  const [pubNormTotal] = await conn.query(`select count(*) as o, sum(case when step_num_repay_status=2 then 1 else 0 end) as d, count(distinct store_id) as sc from dws_credit_yzf_order_complete where ${PUB_NORM}`);
  const [vipTotal] = await conn.query(`select count(*) as o, sum(case when step_num_repay_status=2 then 1 else 0 end) as d, count(distinct store_id) as sc from dws_credit_yzf_order_complete where ${VIP}`);
  const [pubAllTotal] = await conn.query(`select count(*) as o, sum(case when step_num_repay_status=2 then 1 else 0 end) as d from dws_credit_yzf_order_complete where ${PUB_ALL}`);

  console.log(`普通公众: ${pubNormTotal[0].o}单 逾期${(pubNormTotal[0].d/pubNormTotal[0].o*100).toFixed(2)}% ${pubNormTotal[0].sc}店`);
  console.log(`特批白名单: ${vipTotal[0].o}单 逾期${(vipTotal[0].d/vipTotal[0].o*100).toFixed(2)}% ${vipTotal[0].sc}店`);
  console.log(`公众合计: ${pubAllTotal[0].o}单 逾期${(pubAllTotal[0].d/pubAllTotal[0].o*100).toFixed(2)}%`);

  // ========== 2. 公众(普通)省份概况 ==========
  console.log('\n2. 公众(普通)省份概况...');
  const provNorm = await q(`
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
    from dws_credit_yzf_order_complete
    where ${PUB_NORM}
    group by province having orders>=200
    order by orders desc
  `);
  provNorm.forEach(p => console.log(p.province, p.orders, p.rate+'%'));

  // ========== 3. 特批省份概况 ==========
  console.log('\n3. 特批省份概况...');
  const provVip = await q(`
    select province,
      count(distinct store_id) as stores,
      count(*) as orders,
      sum(case when step_num_repay_status=2 then 1 else 0 end) as overdue,
      round(sum(case when step_num_repay_status=2 then 1 else 0 end)*100.0/count(*),2) as rate
    from dws_credit_yzf_order_complete
    where ${VIP}
    group by province having orders>=50
    order by orders desc
  `);
  provVip.forEach(p => console.log(p.province, p.orders, p.rate+'%'));

  // ========== 4. 公众(普通)各省门店明细 ==========
  console.log('\n4. 公众(普通)各省门店明细...');
  const normStores = await q(`
    select province, city, store_name, store_id,
      count(*) as orders,
      sum(case when step_num_repay_status=2 then 1 else 0 end) as overdue,
      round(sum(case when step_num_repay_status=2 then 1 else 0 end)*100.0/count(*),2) as rate,
      sum(case when old_new_customer='新客户' then 1 else 0 end) as new_cust,
      round(sum(case when old_new_customer='新客户' then 1 else 0 end)*100.0/count(*),2) as new_pct,
      coalesce(supplier_name,'') as supplier_name
    from dws_credit_yzf_order_complete
    where ${PUB_NORM}
    group by province, city, store_name, store_id, supplier_name
    having orders>=20
  `);

  // ========== 5. 特批各省门店明细 ==========
  console.log('5. 特批各省门店明细...');
  const vipStores = await q(`
    select province, city, store_name, store_id,
      count(*) as orders,
      sum(case when step_num_repay_status=2 then 1 else 0 end) as overdue,
      round(sum(case when step_num_repay_status=2 then 1 else 0 end)*100.0/count(*),2) as rate,
      coalesce(supplier_name,'') as supplier_name
    from dws_credit_yzf_order_complete
    where ${VIP}
    group by province, city, store_name, store_id, supplier_name
    having orders>=5
  `);

  // ========== 6. Group by province ==========
  const byProv = {};
  normStores.forEach(s => {
    if (!byProv[s.province]) byProv[s.province] = [];
    byProv[s.province].push(s);
  });
  const byProvVip = {};
  vipStores.forEach(s => {
    if (!byProvVip[s.province]) byProvVip[s.province] = [];
    byProvVip[s.province].push(s);
  });

  // ========== 7. Output CSVs ==========
  const csv = (rows, fields) => {
    const h = fields.join(',');
    const l = rows.map(r => fields.map(f => {
      const v = r[f]; if (v===null||v===undefined) return '';
      const s = String(v);
      return s.includes(',')||s.includes('"')||s.includes('\n') ? '"'+s.replace(/"/g,'""')+'"' : s;
    }).join(','));
    return h+'\n'+l.join('\n');
  };

  // 公众(普通)全国数据
  const nf = ['province','city','store_name','store_id','orders','overdue','rate','new_cust','new_pct','supplier_name'];
  fs.writeFileSync(dir+'/公众普通_门店.csv', csv(normStores, nf));
  fs.writeFileSync(dir+'/特批白名单_门店.csv', csv(vipStores, ['province','city','store_name','store_id','orders','overdue','rate','supplier_name']));
  fs.writeFileSync(dir+'/公众普通_各省概况.csv', csv(provNorm, ['province','stores','agents','orders','overdue','rate','new_cust','new_pct','local_net','local_pct']));
  fs.writeFileSync(dir+'/特批白名单_各省概况.csv', csv(provVip, ['province','stores','orders','overdue','rate']));

  // Per-province CSVs - 普通公众
  for (const p of provNorm) {
    const st = byProv[p.province] || [];
    fs.writeFileSync(`${dir}/省份_${p.province}_普通公众_门店.csv`, csv(st, nf));
  }

  // ========== 8. Markdown Report ==========
  const lines = [];
  lines.push('# 淘顺实时授信 — 公众客群深度分析');
  lines.push('');
  lines.push(`**公众定义**：\`custtype='00'\``);
  lines.push('');
  lines.push('## 一、全国概览');
  lines.push('');
  lines.push('| 客群 | 办单 | 逾期率 | 门店数 |');
  lines.push('|:----:|:----:|:------:|:-----:|');
  lines.push(`| 🟦 **普通公众** | ${pubNormTotal[0].o} | **${(pubNormTotal[0].d/pubNormTotal[0].o*100).toFixed(2)}%** | ${pubNormTotal[0].sc} |`);
  lines.push(`| 🟪 **特批白名单**（公众子集）| ${vipTotal[0].o} | **${(vipTotal[0].d/vipTotal[0].o*100).toFixed(2)}%** | ${vipTotal[0].sc} |`);
  lines.push(`| 📊 **公众合计** | ${pubAllTotal[0].o} | **${(pubAllTotal[0].d/pubAllTotal[0].o*100).toFixed(2)}%** | — |`);
  lines.push('');
  lines.push(`> 💡 **特批白名单逾期率(${(vipTotal[0].d/vipTotal[0].o*100).toFixed(2)}%) 明显低于普通公众(${(pubNormTotal[0].d/pubNormTotal[0].o*100).toFixed(2)}%)**，说明特批策略有效筛选出了更优质的客群`);
  lines.push('');

  // Province compare table
  lines.push('## 二、省份对比（仅普通公众）');
  lines.push('');
  lines.push('| 排名 | 省份 | 办单 | 逾期率 | 门店 | 代理商 | 新客占比 | 本网占比 |');
  lines.push('|:---:|:----:|:----:|:------:|:----:|:------:|:--------:|:--------:|');
  provNorm.forEach((p, i) => {
    lines.push(`| ${i+1} | ${p.province} | ${p.orders} | ${p.rate}% | ${p.stores} | ${p.agents} | ${p.new_pct}% | ${p.local_pct}% |`);
  });
  lines.push('');

  // Risk tiers
  const high = provNorm.filter(p => p.rate >= 8).sort((a,b) => b.rate - a.rate);
  const mid = provNorm.filter(p => p.rate >= 4 && p.rate < 8).sort((a,b) => b.rate - a.rate);
  const low = provNorm.filter(p => p.rate < 4).sort((a,b) => b.rate - a.rate);
  lines.push('### 风险分层');
  if (high.length) lines.push(`🔴 **高风险**（≥8%）：${high.map(p => p.province+'('+p.rate+'%)').join('、')}`);
  if (mid.length) lines.push(`🟡 **中风险**（4%~8%）：${mid.map(p => p.province+'('+p.rate+'%)').join('、')}`);
  if (low.length) lines.push(`🟢 **低风险**（<4%）：${low.map(p => p.province+'('+p.rate+'%)').join('、')}`);
  lines.push('');

  // Province compare: 普通公众 vs 特批
  lines.push('## 三、省份对比（普通 vs 特批）');
  lines.push('');
  lines.push('| 省份 | 普通公众办单 | 普通逾期率 | 特批办单 | 特批逾期率 |');
  lines.push('|:----:|:-----------:|:---------:|:--------:|:----------:|');
  for (const pn of provNorm) {
    const pv = provVip.find(v => v.province === pn.province);
    lines.push(`| ${pn.province} | ${pn.orders} | ${pn.rate}% | ${pv ? pv.orders : '-'} | ${pv ? pv.rate+'%' : '-'} |`);
  }
  lines.push('');

  // ========== Per province deep analysis ==========
  lines.push('---');
  lines.push('# 四、各省深度分析');
  lines.push('');

  for (const pv of provNorm.map(p => p.province)) {
    const info = provNorm.find(p => p.province === pv);
    const pvInfo = provVip.find(v => v.province === pv);
    const st = (byProv[pv] || []).sort((a,b) => b.orders - a.orders);
    const vpSt = (byProvVip[pv] || []).sort((a,b) => b.orders - a.orders);
    if (!info) continue;

    const good = st.filter(s => s.rate < 3 && s.orders >= 30);
    const bad = st.filter(s => s.rate >= 8 && s.orders >= 20);

    lines.push(`## ${pv}`);
    lines.push('');
    lines.push(`**普通公众**：${info.orders}单 | 逾期率 **${info.rate}%** | ${info.stores}家门店 | ${info.agents}家代理商`);
    if (pvInfo) {
      lines.push(`**特批白名单**：${pvInfo.orders}单 | 逾期率 **${pvInfo.rate}%** | ${pvInfo.stores}家门店`);
    }
    lines.push(`新客${info.new_pct}% | 本网${info.local_pct}%`);
    lines.push('');

    // Top stores - 普通公众
    lines.push('### 普通公众 — Top 大店（按办单）');
    lines.push('');
    lines.push('| # | 门店 | 地市 | 办单 | 逾期率 | 新客 |');
    lines.push('|:-:|------|:----:|:----:|:------:|:----:|');
    st.slice(0, 10).forEach((s, i) => {
      lines.push(`| ${i+1} | ${s.store_name} | ${s.city||'-'} | ${s.orders} | ${s.rate}% | ${s.new_pct}% |`);
    });
    lines.push('');

    // Good stores
    if (good.length > 0) {
      lines.push(`### 普通公众 — 优质门店（逾期<3%）— ${good.length}家`);
      lines.push('');
      lines.push('| # | 门店 | 地市 | 办单 | 逾期率 | 新客 |');
      lines.push('|:-:|------|:----:|:----:|:------:|:----:|');
      good.sort((a,b) => b.orders - a.orders).slice(0, 5).forEach((s, i) => {
        lines.push(`| ${i+1} | ${s.store_name} | ${s.city||'-'} | ${s.orders} | ${s.rate}% | ${s.new_pct}% |`);
      });
      lines.push('');
    }

    // Bad stores
    if (bad.length > 0) {
      lines.push(`### ⚠️ 普通公众 — 高风险门店（逾期≥8%）— ${bad.length}家`);
      lines.push('');
      lines.push('| # | 门店 | 地市 | 办单 | 逾期率 | 新客 | 代理商 |');
      lines.push('|:-:|------|:----:|:----:|:------:|:----:|:------:|');
      bad.sort((a,b) => b.rate - a.rate).slice(0, 10).forEach((s, i) => {
        lines.push(`| ${i+1} | ${s.store_name} | ${s.city||'-'} | ${s.orders} | ${s.rate}% | ${s.new_pct}% | ${s.supplier_name||'-'} |`);
      });
      lines.push('');
    }

    // VIP stores
    if (vpSt.length > 0) {
      lines.push(`### 特批白名单门店（${vpSt.length}家）`);
      lines.push('');
      lines.push('| # | 门店 | 地市 | 办单 | 逾期率 |');
      lines.push('|:-:|------|:----:|:----:|:------:|');
      vpSt.slice(0, 10).forEach((s, i) => {
        lines.push(`| ${i+1} | ${s.store_name} | ${s.city||'-'} | ${s.orders} | ${s.rate}% |`);
      });
      lines.push('');
      const badVip = vpSt.filter(s => s.rate >= 10);
      if (badVip.length > 0) {
        lines.push(`##### 特批高风险（逾期≥10%）`);
        badVip.sort((a,b) => b.rate - a.rate).slice(0, 5).forEach(s => {
          lines.push(`- 🔴 ${s.store_name} | ${s.orders}单 | ${s.rate}%`);
        });
        lines.push('');
      }
    }
  }

  fs.writeFileSync(dir+'/公众客群深度分析.md', lines.join('\n'));
  console.log('\n✅ 公众客群深度分析.md 生成完成');
  console.log('✅ 全部CSV已重新输出');

  conn.end();
}
main().catch(e => { console.error(e); process.exit(1); });
