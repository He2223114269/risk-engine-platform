const mysql = require('mysql2/promise');
const fs = require('fs');

async function main() {
  const conn = await mysql.createConnection({
    host: '47.119.181.195', port: 9030,
    user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)",
    database: 'dws',
  });
  const q = async (sql) => { const [r] = await conn.query(sql); return r; };

  const dir = '/mnt/d/desktop/翼支付交流_门店代理商分析';
  const PUBLIC = "source_business_type='淘顺实时授信' and (order_channel_id is null or order_channel_id != '特批白名单')";
  const VIP = "source_business_type='淘顺实时授信' and order_channel_id = '特批白名单'";

  // ========== 公众省份概况 ==========
  console.log('1. 公众各省概况...');
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
    from dws_credit_yzf_order_complete
    where ${PUBLIC}
    group by province having orders>=500
    order by orders desc
  `);

  // ========== 公众各省门店明细 ==========
  console.log('2. 公众各省门店明细...');
  const stores = await q(`
    select province, store_name, store_id,
      count(*) as orders,
      sum(case when step_num_repay_status=2 then 1 else 0 end) as overdue,
      round(sum(case when step_num_repay_status=2 then 1 else 0 end)*100.0/count(*),2) as rate,
      sum(case when old_new_customer='新客户' then 1 else 0 end) as new_cust,
      round(sum(case when old_new_customer='新客户' then 1 else 0 end)*100.0/count(*),2) as new_pct,
      coalesce(supplier_name,'') as supplier_name,
      city
    from dws_credit_yzf_order_complete
    where ${PUBLIC}
    group by province, store_name, store_id, city, supplier_name
    having orders>=30
  `);

  // ========== 公众各省代理商 ==========
  console.log('3. 公众各省代理商...');
  const agents = await q(`
    select province, coalesce(supplier_name, supplier_code, '未知') as supplier_name,
      count(distinct store_id) as stores,
      count(*) as orders,
      sum(case when step_num_repay_status=2 then 1 else 0 end) as overdue,
      round(sum(case when step_num_repay_status=2 then 1 else 0 end)*100.0/count(*),2) as rate,
      sum(case when old_new_customer='新客户' then 1 else 0 end) as new_cust,
      round(sum(case when old_new_customer='新客户' then 1 else 0 end)*100.0/count(*),2) as new_pct
    from dws_credit_yzf_order_complete
    where ${PUBLIC} and supplier_name is not null and supplier_name!=''
    group by province, supplier_code, supplier_name
    having orders>=100
  `);

  // ========== Group by province ==========
  const byProvStore = {};
  stores.forEach(s => {
    if (!byProvStore[s.province]) byProvStore[s.province] = [];
    byProvStore[s.province].push(s);
  });
  const byProvAgent = {};
  agents.forEach(a => {
    if (!byProvAgent[a.province]) byProvAgent[a.province] = [];
    byProvAgent[a.province].push(a);
  });

  // ========== 省CSV (分渠道) ==========
  console.log('4. 输出省份CSV...');
  // For each province, output store CSV and agent CSV
  for (const p of prov) {
    const st = byProvStore[p.province] || [];
    const ag = byProvAgent[p.province] || [];
    // Store CSV
    const sf = ['store_name','store_id','city','orders','overdue','rate','new_cust','new_pct','supplier_name'];
    const h = sf.join(',');
    const lines = st.map(s => sf.map(f => {
      const v = s[f];
      if (v===null||v===undefined) return '';
      const str = String(v);
      return str.includes(',')||str.includes('"')||str.includes('\n') ? '"'+str.replace(/"/g,'""')+'"' : str;
    }).join(','));
    fs.writeFileSync(`${dir}/省份_${p.province}_门店.csv`, h+'\n'+lines.join('\n'));

    // Agent CSV
    const af = ['supplier_name','stores','orders','overdue','rate','new_cust','new_pct'];
    const ah = af.join(',');
    const al = ag.map(a => af.map(f => String(a[f]||'')).join(','));
    fs.writeFileSync(`${dir}/省份_${p.province}_代理商.csv`, ah+'\n'+al.join('\n'));
  }
  console.log('  -> 各省CSV已输出');

  // ========== 报告 ==========
  console.log('5. 生成报告...');
  const lines = [];
  lines.push('# 公众渠道 — 各省深度分析');
  lines.push('');
  lines.push(`> 数据截止：2026年4月底 | 仅统计公众渠道（已排除特批白名单）`);
  lines.push('');
  lines.push('## 一、省综合排名');
  lines.push('');
  lines.push('| 排名 | 省份 | 办单(万) | 逾期率 | 门店数 | 代理商数 | 新客占比 | 本网占比 |');
  lines.push('|:---:|:----:|:--------:|:------:|:-----:|:--------:|:--------:|:--------:|');
  prov.sort((a,b) => b.orders - a.orders).forEach((p, i) => {
    lines.push(`| ${i+1} | ${p.province} | ${(p.orders/10000).toFixed(1)} | ${p.rate}% | ${p.stores} | ${p.agents} | ${p.new_pct}% | ${p.local_pct}% |`);
  });
  lines.push('');

  // Risk tier
  const high = prov.filter(p => p.rate >= 8).sort((a,b) => b.rate - a.rate);
  const mid = prov.filter(p => p.rate >= 4 && p.rate < 8).sort((a,b) => b.rate - a.rate);
  const low = prov.filter(p => p.rate < 4).sort((a,b) => b.rate - a.rate);

  lines.push('### 风险分层');
  lines.push('');
  if (high.length) {
    lines.push(`🔴 **高风险**（逾期率≥8%）：${high.map(p => p.province+'('+p.rate+'%)').join('、')}`);
  }
  if (mid.length) {
    lines.push(`🟡 **中风险**（4%~8%）：${mid.map(p => p.province+'('+p.rate+'%)').join('、')}`);
  }
  if (low.length) {
    lines.push(`🟢 **低风险**（<4%）：${low.map(p => p.province+'('+p.rate+'%)').join('、')}`);
  }
  lines.push('');

  // ========== Per province ==========
  for (const pv of prov.map(p => p.province)) {
    const st = (byProvStore[pv] || []).sort((a,b) => b.orders - a.orders);
    const ag = (byProvAgent[pv] || []).sort((a,b) => b.orders - a.orders);
    const info = prov.find(p => p.province === pv);
    if (!info) continue;

    const good = st.filter(s => s.rate < 3 && s.orders >= 50);
    const bad = st.filter(s => s.rate >= 8 && s.orders >= 30);
    const badAg = ag.filter(a => a.rate >= 8 && a.orders >= 200);

    lines.push(`---`);
    lines.push(`## ${pv}`);
    lines.push('');
    lines.push(`**${(info.orders/10000).toFixed(1)}万单** | 逾期率 **${info.rate}%** | ${info.stores}家门店 | ${info.agents}家代理商`);
    lines.push(`新客占比 ${info.new_pct}% | 本网占比 ${info.local_pct}%`);
    lines.push('');

    // Top 10 stores
    lines.push('### Top10 大店（按办单）');
    lines.push('');
    lines.push('| # | 门店 | 地市 | 办单 | 逾期率 | 新客占比 | 代理商 |');
    lines.push('|:-:|------|:----:|:----:|:------:|:--------:|:------:|');
    st.slice(0, 10).forEach((s, i) => {
      lines.push(`| ${i+1} | ${s.store_name} | ${s.city||'-'} | ${s.orders} | ${s.rate}% | ${s.new_pct}% | ${s.supplier_name||'-'} |`);
    });
    lines.push('');

    // Good stores
    if (good.length > 0) {
      lines.push(`### 优质标杆（逾期率<3%，>50单）— ${good.length}家`);
      lines.push('');
      lines.push('| # | 门店 | 地市 | 办单 | 逾期率 | 新客占比 |');
      lines.push('|:-:|------|:----:|:----:|:------:|:--------:|');
      good.sort((a,b) => b.orders - a.orders).slice(0, 5).forEach((s, i) => {
        lines.push(`| ${i+1} | ${s.store_name} | ${s.city||'-'} | ${s.orders} | ${s.rate}% | ${s.new_pct}% |`);
      });
      lines.push('');
    }

    // Bad stores
    if (bad.length > 0) {
      lines.push(`### ⚠️ 高风险门店（逾期率≥8%，办单≥30）— ${bad.length}家`);
      lines.push('');
      lines.push('| # | 门店 | 地市 | 办单 | 逾期率 | 新客占比 | 代理商 |');
      lines.push('|:-:|------|:----:|:----:|:------:|:--------:|:------:|');
      bad.sort((a,b) => b.rate - a.rate).slice(0, 10).forEach((s, i) => {
        lines.push(`| ${i+1} | ${s.store_name} | ${s.city||'-'} | ${s.orders} | ${s.rate}% | ${s.new_pct}% | ${s.supplier_name||'-'} |`);
      });
      lines.push('');
    }

    // Top agents
    if (ag.length > 0) {
      lines.push(`### Top代理商`);
      lines.push('');
      lines.push('| # | 代理商 | 门店数 | 办单 | 逾期率 | 新客占比 |');
      lines.push('|:-:|--------|:-----:|:----:|:------:|:--------:|');
      ag.slice(0, 5).forEach((a, i) => {
        lines.push(`| ${i+1} | ${a.supplier_name} | ${a.stores} | ${a.orders} | ${a.rate}% | ${a.new_pct}% |`);
      });
      lines.push('');
    }

    // Bad agents
    if (badAg.length > 0) {
      lines.push(`### ⚠️ 高风险代理商（逾期率≥8%，办单≥200）— ${badAg.length}家`);
      lines.push('');
      lines.push('| # | 代理商 | 门店数 | 办单 | 逾期率 | 新客占比 |');
      lines.push('|:-:|--------|:-----:|:----:|:------:|:--------:|');
      badAg.forEach((a, i) => {
        lines.push(`| ${i+1} | ${a.supplier_name} | ${a.stores} | ${a.orders} | ${a.rate}% | ${a.new_pct}% |`);
      });
      lines.push('');
    }
  }

  fs.writeFileSync(dir+'/公众渠道_各省深度分析.md', lines.join('\n'));
  console.log('  -> 公众渠道_各省深度分析.md');

  // Also update main report overview table
  const csvProv = prov.map(p => ({
    province: p.province, stores: p.stores, agents: p.agents,
    orders: p.orders, rate: p.rate+'%', new_pct: p.new_pct+'%', local_pct: p.local_pct+'%'
  }));
  const cf = ['province','stores','agents','orders','rate','new_pct','local_pct'];
  fs.writeFileSync(dir+'/公众渠道_各省概况.csv', csvProv.map(r => cf.map(f => r[f]).join(',')).join('\n'));

  // Clean up old mixed province files
  try {
    const oldFiles = ['省份_湖南_门店.csv','省份_湖南_代理商.csv','省份_江西_门店.csv','省份_江西_代理商.csv'];
    // Actually the new ones just got created properly... let's check
  } catch(e) {}

  conn.end();
  console.log('\n✅ 全部完成');
}
main().catch(e => { console.error(e); process.exit(1); });
