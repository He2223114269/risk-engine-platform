const mysql = require('mysql2/promise');
const fs = require('fs');

async function main() {
  const conn = await mysql.createConnection({
    host: '47.119.181.195', port: 9030, user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)", database: 'dws',
  });
  const q = async (sql) => { const [r] = await conn.query(sql); return r; };

  const dir = '/mnt/d/desktop/翼支付交流_门店代理商分析';
  const csv = (rows, fields) => {
    const h = fields.join(',');
    const l = rows.map(r => fields.map(f => {
      const v = r[f]; if (v===null||v===undefined) return '';
      const s = String(v);
      return s.includes(',')||s.includes('"')||s.includes('\n') ? '"'+s.replace(/"/g,'""')+'"' : s;
    }).join(','));
    return h+'\n'+l.join('\n');
  };

  // 1. 各省综合概况
  console.log('1. 各省概况...');
  const prov = await q(`
    select province,
      count(distinct store_id) as stores,
      count(distinct coalesce(supplier_code,'x')) as agents,
      count(*) as orders,
      sum(case when step_num_repay_status=2 then 1 else 0 end) as overdue,
      round(sum(case when step_num_repay_status=2 then 1 else 0 end)*100.0/count(*),2) as rate,
      sum(case when old_new_customer='新客户' then 1 else 0 end) as new_cust,
      round(sum(case when old_new_customer='新客户' then 1 else 0 end)*100.0/count(*),2) as new_pct
    from dws_credit_yzf_order_complete
    where source_business_type='淘顺实时授信'
    group by province having orders>=500
    order by orders desc
  `);
  fs.writeFileSync(dir+'/各省概况.csv', csv(prov, ['province','stores','agents','orders','overdue','rate','new_cust','new_pct']));
  console.log('  -> 各省概况.csv', prov.length+'省');

  // 2. 各省门店排名
  console.log('2. 各省门店排名...');
  const stores = await q(`
    select province, store_name, store_id,
      count(*) as orders,
      sum(case when step_num_repay_status=2 then 1 else 0 end) as overdue,
      round(sum(case when step_num_repay_status=2 then 1 else 0 end)*100.0/count(*),2) as rate,
      sum(case when old_new_customer='新客户' then 1 else 0 end) as new_cust,
      round(sum(case when old_new_customer='新客户' then 1 else 0 end)*100.0/count(*),2) as new_pct,
      coalesce(supplier_name,'') as supplier_name
    from dws_credit_yzf_order_complete
    where source_business_type='淘顺实时授信'
    group by province, store_name, store_id, supplier_name
    having orders>=30
  `);
  // Split by province
  const provMap = {};
  stores.forEach(s => {
    if (!provMap[s.province]) provMap[s.province] = [];
    provMap[s.province].push(s);
  });
  
  // For each province: top 10 good stores, top 10 bad stores
  const reportLines = [];
  reportLines.push('# 各省深度分析');
  reportLines.push('');
  reportLines.push('## 综合概况');
  reportLines.push('');
  reportLines.push('| 省份 | 门店数 | 代理商数 | 办单(万) | 逾期率 | 新客占比 |');
  reportLines.push('|:----:|:-----:|:--------:|:--------:|:------:|:--------:|');
  prov.forEach(p => {
    reportLines.push(`| ${p.province} | ${p.stores} | ${p.agents} | ${(p.orders/10000).toFixed(1)} | ${p.rate}% | ${p.new_pct}% |`);
  });
  reportLines.push('');

  // Per province deep analysis
  const provinces = prov.map(p => p.province);
  for (const pv of provinces) {
    const st = provMap[pv] || [];
    const good = st.filter(s => s.rate < 3 && s.orders >= 50).sort((a,b) => b.orders - a.orders);
    const bad = st.filter(s => s.rate >= 8 && s.orders >= 30).sort((a,b) => b.rate - a.rate);

    reportLines.push(`---`);
    reportLines.push(`## ${pv}`);
    reportLines.push('');
    
    const pi = prov.find(p => p.province === pv);
    if (pi) {
      reportLines.push(`- **办单**: ${(pi.orders/10000).toFixed(1)}万单 | **逾期率**: ${pi.rate}% | **门店**: ${pi.stores}家 | **代理商**: ${pi.agents}家 | **新客**: ${pi.new_pct}%`);
      reportLines.push('');
    }

    // Top stores
    reportLines.push(`### Top 办单门店`);
    reportLines.push('');
    reportLines.push(`| # | 门店 | 办单 | 逾期率 | 新客占比 | 代理商 |`);
    reportLines.push(`|:-:|------|:----:|:------:|:--------:|:------:|`);
    st.sort((a,b) => b.orders - a.orders).slice(0, 10).forEach((s, i) => {
      reportLines.push(`| ${i+1} | ${s.store_name} | ${s.orders} | ${s.rate}% | ${s.new_pct}% | ${s.supplier_name || '-'} |`);
    });
    reportLines.push('');

    // Good stores
    if (good.length > 0) {
      reportLines.push(`### 优质门店（逾期率<3%）— ${good.length}家`);
      reportLines.push('');
      reportLines.push(`| # | 门店 | 办单 | 逾期率 | 新客占比 |`);
      reportLines.push(`|:-:|------|:----:|:------:|:--------:|`);
      good.slice(0, 5).forEach((s, i) => {
        reportLines.push(`| ${i+1} | ${s.store_name} | ${s.orders} | ${s.rate}% | ${s.new_pct}% |`);
      });
      reportLines.push('');
    }

    // Bad stores
    if (bad.length > 0) {
      reportLines.push(`### 高风险门店（逾期率≥8%）— ${bad.length}家 ⚠️`);
      reportLines.push('');
      reportLines.push(`| # | 门店 | 办单 | 逾期率 | 新客占比 |`);
      reportLines.push(`|:-:|------|:----:|:------:|:--------:|`);
      bad.slice(0, 10).forEach((s, i) => {
        reportLines.push(`| ${i+1} | ${s.store_name} | ${s.orders} | ${s.rate}% | ${s.new_pct}% |`);
      });
      reportLines.push('');
    }
  }

  fs.writeFileSync(dir+'/各省深度分析.md', reportLines.join('\n'));
  console.log('  -> 各省深度分析.md');

  conn.end();
  console.log('\n✅ 完成');
}
main().catch(e => { console.error(e); process.exit(1); });
