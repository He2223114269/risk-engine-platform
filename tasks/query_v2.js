const mysql = require('mysql2/promise');
const fs = require('fs');

async function main() {
  const conn = await mysql.createConnection({
    host: '47.119.181.195', port: 9030,
    user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)",
    database: 'dws',
  });

  const dir = '/mnt/d/desktop/翼支付交流_门店代理商分析';

  // Helper: run query and return rows
  async function q(sql) {
    const [rows] = await conn.query(sql);
    return rows;
  }

  console.log('1. 门店/代理商质态 — 公众 vs 特批白名单...');

  const pubStores = await q(`
    select province, city, store_id, store_name, supplier_code, supplier_name,
      count(*) as total_orders,
      sum(case when step_num_repay_status = 2 then 1 else 0 end) as overdue,
      round(sum(case when step_num_repay_status = 2 then 1 else 0 end)*100.0/count(*), 2) as overdue_rate,
      min(complete_time) as first_order, max(complete_time) as last_order,
      sum(case when old_new_customer = '新客户' then 1 else 0 end) as new_cust,
      round(sum(case when old_new_customer = '新客户' then 1 else 0 end)*100.0/count(*), 2) as new_cust_pct,
      sum(case when operator_real = 3 then 1 else 0 end) as local_net,
      round(sum(case when operator_real = 3 then 1 else 0 end)*100.0/count(*), 2) as local_net_pct
    from dws_credit_yzf_order_complete
    where source_business_type = '淘顺实时授信' and (order_channel_id is null or order_channel_id != '特批白名单')
    group by province, city, store_id, store_name, supplier_code, supplier_name
    having total_orders >= 10 order by total_orders desc
  `);
  console.log(`  公众门店: ${pubStores.length}家`);

  const vipStores = await q(`
    select province, city, store_id, store_name, supplier_code, supplier_name,
      count(*) as total_orders,
      sum(case when step_num_repay_status = 2 then 1 else 0 end) as overdue,
      round(sum(case when step_num_repay_status = 2 then 1 else 0 end)*100.0/count(*), 2) as overdue_rate,
      min(complete_time) as first_order, max(complete_time) as last_order,
      sum(case when old_new_customer = '新客户' then 1 else 0 end) as new_cust,
      round(sum(case when old_new_customer = '新客户' then 1 else 0 end)*100.0/count(*), 2) as new_cust_pct,
      sum(case when operator_real = 3 then 1 else 0 end) as local_net,
      round(sum(case when operator_real = 3 then 1 else 0 end)*100.0/count(*), 2) as local_net_pct
    from dws_credit_yzf_order_complete
    where source_business_type = '淘顺实时授信' and order_channel_id = '特批白名单'
    group by province, city, store_id, store_name, supplier_code, supplier_name
    having total_orders >= 5 order by total_orders desc
  `);
  console.log(`  特批白名单门店: ${vipStores.length}家`);

  const pubSupps = await q(`
    select coalesce(supplier_code,'未知') as supplier_id, coalesce(supplier_name,supplier_code,'未知') as supplier_name,
      count(distinct store_id) as store_count, count(*) as total_orders,
      sum(case when step_num_repay_status = 2 then 1 else 0 end) as overdue,
      round(sum(case when step_num_repay_status = 2 then 1 else 0 end)*100.0/count(*), 2) as overdue_rate,
      sum(case when old_new_customer = '新客户' then 1 else 0 end) as new_cust,
      round(sum(case when old_new_customer = '新客户' then 1 else 0 end)*100.0/count(*), 2) as new_cust_pct
    from dws_credit_yzf_order_complete
    where source_business_type = '淘顺实时授信' and (order_channel_id is null or order_channel_id != '特批白名单')
    group by supplier_code, supplier_name
    having total_orders >= 50 order by total_orders desc
  `);
  console.log(`  公众代理商: ${pubSupps.length}家`);

  const vipSupps = await q(`
    select coalesce(supplier_code,'未知') as supplier_id, coalesce(supplier_name,supplier_code,'未知') as supplier_name,
      count(distinct store_id) as store_count, count(*) as total_orders,
      sum(case when step_num_repay_status = 2 then 1 else 0 end) as overdue,
      round(sum(case when step_num_repay_status = 2 then 1 else 0 end)*100.0/count(*), 2) as overdue_rate,
      sum(case when old_new_customer = '新客户' then 1 else 0 end) as new_cust,
      round(sum(case when old_new_customer = '新客户' then 1 else 0 end)*100.0/count(*), 2) as new_cust_pct
    from dws_credit_yzf_order_complete
    where source_business_type = '淘顺实时授信' and order_channel_id = '特批白名单'
    group by supplier_code, supplier_name
    having total_orders >= 10 order by total_orders desc
  `);
  console.log(`  特批白名单代理商: ${vipSupps.length}家`);

  // 全国汇总
  const [t1] = await conn.query(`
    select count(*) as o, sum(case when step_num_repay_status=2 then 1 else 0 end) as d,
      count(distinct store_id) as sc, count(distinct coalesce(supplier_code,'x')) as ac
    from dws_credit_yzf_order_complete
    where source_business_type = '淘顺实时授信' and (order_channel_id is null or order_channel_id != '特批白名单')
  `);
  const [t2] = await conn.query(`
    select count(*) as o, sum(case when step_num_repay_status=2 then 1 else 0 end) as d,
      count(distinct store_id) as sc, count(distinct coalesce(supplier_code,'x')) as ac
    from dws_credit_yzf_order_complete
    where source_business_type = '淘顺实时授信' and order_channel_id = '特批白名单'
  `);
  console.log(`\n公众: ${(t1.o/10000).toFixed(1)}万单 逾期${(t1.d/t1.o*100).toFixed(2)}%  ${t1.sc}店 ${t1.ac}代理商`);
  console.log(`VIP: ${(t2.o/10000).toFixed(1)}万单 逾期${(t2.d/t2.o*100).toFixed(2)}%  ${t2.sc}店 ${t2.ac}代理商`);

  // 省份风险
  const provRisk = await q(`
    select province,
      case when order_channel_id='特批白名单' then '特批' else '公众' end as channel,
      count(distinct store_id) as store_cnt, count(*) as orders,
      sum(case when step_num_repay_status=2 then 1 else 0 end) as overdue
    from dws_credit_yzf_order_complete
    where source_business_type='淘顺实时授信'
    group by province, channel having orders>=100 order by province
  `);
  console.log('\n=== 省份风险（公众/特批） ===');
  provRisk.forEach(r => console.log(`${r.province} | ${r.channel} | ${r.store_cnt}店 | ${r.orders}单 | ${(r.overdue/r.orders*100).toFixed(2)}%`));

  // 输出CSV
  function toCSV(rows, fields) {
    const h = fields.join(',');
    const l = rows.map(r => fields.map(f => {
      const v = r[f]; if (v===null||v===undefined) return '';
      const s = String(v); return s.includes(',')||s.includes('"')||s.includes('\n') ? '"'+s.replace(/"/g,'""')+'"' : s;
    }).join(','));
    return h+'\n'+l.join('\n');
  }
  const sf = ['province','city','store_id','store_name','supplier_code','supplier_name',
    'total_orders','overdue','overdue_rate','first_order','last_order','new_cust','new_cust_pct','local_net','local_net_pct'];
  const af = ['supplier_id','supplier_name','store_count','total_orders','overdue','overdue_rate','new_cust','new_cust_pct'];
  
  fs.writeFileSync(dir+'/门店数据_公众.csv', toCSV(pubStores, sf));
  fs.writeFileSync(dir+'/门店数据_特批白名单.csv', toCSV(vipStores, sf));
  fs.writeFileSync(dir+'/代理商数据_公众.csv', toCSV(pubSupps, af));
  fs.writeFileSync(dir+'/代理商数据_特批白名单.csv', toCSV(vipSupps, af));

  console.log('\n✅ 数据已写入');
  conn.end();
}
main().catch(e => { console.error(e); process.exit(1); });
