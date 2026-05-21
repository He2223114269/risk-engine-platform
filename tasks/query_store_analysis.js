const mysql = require('mysql2/promise');
const fs = require('fs');

async function main() {
  // Connect with default database=dws, but use full qualified names for ods tables
  const conn = await mysql.createConnection({
    host: '47.119.181.195', port: 9030,
    user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)",
    database: 'dws',
  });

  // ========== 1. Store basic stats from DWS ==========
  console.log('1. 门店基础质态...');
  const stores = await conn.query(`
    select 
      province, city,
      store_id, store_name,
      supplier_code, supplier_name,
      count(*) as total_orders,
      sum(case when step_num_repay_status = 2 then 1 else 0 end) as overdue,
      round(sum(case when step_num_repay_status = 2 then 1 else 0 end) * 100.0 / count(*), 2) as overdue_rate,
      min(complete_time) as first_order,
      max(complete_time) as last_order,
      timestampdiff(day, min(complete_time), max(complete_time)) as active_days,
      sum(case when old_new_customer = '新客户' then 1 else 0 end) as new_cust,
      round(sum(case when old_new_customer = '新客户' then 1 else 0 end) * 100.0 / count(*), 2) as new_cust_pct,
      sum(case when operator_real = 3 then 1 else 0 end) as local_net,
      round(sum(case when operator_real = 3 then 1 else 0 end) * 100.0 / count(*), 2) as local_net_pct
    from dws_credit_yzf_order_complete
    where source_business_type = '淘顺实时授信'
    group by province, city, store_id, store_name, supplier_code, supplier_name
    having total_orders >= 10
    order by total_orders desc
  `);
  console.log(`  共 ${stores[0].length} 家门店`);

  // ========== 2. Supplier aggregation ==========
  console.log('2. 代理商汇总...');
  const suppliers = await conn.query(`
    select 
      coalesce(supplier_code, supplier_name, '未知') as supplier_id,
      coalesce(supplier_name, supplier_code, '未知') as supplier_name,
      count(distinct store_id) as store_count,
      count(*) as total_orders,
      sum(case when step_num_repay_status = 2 then 1 else 0 end) as overdue,
      round(sum(case when step_num_repay_status = 2 then 1 else 0 end) * 100.0 / count(*), 2) as overdue_rate,
      sum(case when old_new_customer = '新客户' then 1 else 0 end) as new_cust,
      round(sum(case when old_new_customer = '新客户' then 1 else 0 end) * 100.0 / count(*), 2) as new_cust_pct,
      sum(case when operator_real = 3 then 1 else 0 end) as local_net,
      round(sum(case when operator_real = 3 then 1 else 0 end) * 100.0 / count(*), 2) as local_net_pct
    from dws_credit_yzf_order_complete
    where source_business_type = '淘顺实时授信'
    group by supplier_code, supplier_name
    having total_orders >= 50
    order by total_orders desc
  `);
  console.log(`  共 ${suppliers[0].length} 家代理商`);

  // ========== 3. Recent 30 days active + high risk stores ==========
  console.log('3. 近30天活跃门店...');
  const recent = await conn.query(`
    select s.*, r.recent_orders, r.recent_overdue,
           round(r.recent_overdue * 100.0 / r.recent_orders, 2) as recent_overdue_rate
    from (
      select store_id, store_name,
        count(*) as recent_orders,
        sum(case when step_num_repay_status = 2 then 1 else 0 end) as recent_overdue
      from dws_credit_yzf_order_complete
      where source_business_type = '淘顺实时授信'
        and complete_time >= date_sub(now(), interval 30 day)
      group by store_id, store_name
      having recent_orders >= 5
    ) r
    left join (
      select store_id, store_name,
        count(*) as total_orders,
        sum(case when step_num_repay_status = 2 then 1 else 0 end) as overdue,
        round(sum(case when step_num_repay_status = 2 then 1 else 0 end) * 100.0 / count(*), 2) as overdue_rate
      from dws_credit_yzf_order_complete
      where source_business_type = '淘顺实时授信'
      group by store_id, store_name
    ) s on r.store_id = s.store_id
    order by r.recent_orders desc
  `);
  console.log(`  共 ${recent[0].length} 家`);

  // ========== 4. Pass rate from ods table ==========
  console.log('4. 门店通过率...');
  const passRate = await conn.query({
    sql: `
      select 
        store_addr_city as city,
        store_name,
        count(*) as apply_total,
        sum(case when apply_status = '授信成功' then 1 else 0 end) as pass,
        round(sum(case when apply_status = '授信成功' then 1 else 0 end) * 100.0 / count(*), 2) as pass_rate,
        sum(case when apply_msg = '综合评分不通过' then 1 else 0 end) as risk_reject,
        sum(case when apply_msg is not null and apply_msg != '综合评分不通过' and apply_status = '授信失败' then 1 else 0 end) as other_reject
      from ods.ods_ts_credit_yzf_order_grant_apply
      where store_addr_province is not null and store_addr_province != ''
      group by store_addr_city, store_name
      having apply_total >= 20
      order by apply_total desc
    `,
  });
  console.log(`  共 ${passRate[0].length} 家`);

  // ========== 5. Output ==========
  const output = {
    stores: stores[0].slice(0, 5000),  // top 5000 by volume
    suppliers: suppliers[0].slice(0, 500),
    recentStores: recent[0].slice(0, 500),
    passRate: passRate[0].slice(0, 2000),
    meta: {
      total_stores: stores[0].length,
      total_suppliers: suppliers[0].length,
      recent_active: recent[0].length,
      pass_rate_stores: passRate[0].length,
    }
  };

  // Save as CSV files for Excel import
  function toCSV(rows, fields) {
    const header = fields.join(',');
    const lines = rows.map(r => fields.map(f => {
      const v = r[f];
      if (v === null || v === undefined) return '';
      const s = String(v);
      return s.includes(',') || s.includes('"') || s.includes('\n') ? `"${s.replace(/"/g, '""')}"` : s;
    }).join(','));
    return header + '\n' + lines.join('\n');
  }

  const storeFields = ['province','city','store_id','store_name','supplier_code','supplier_name',
    'total_orders','overdue','overdue_rate','first_order','last_order','active_days',
    'new_cust','new_cust_pct','local_net','local_net_pct'];
  const suppFields = ['supplier_id','supplier_name','store_count','total_orders','overdue',
    'overdue_rate','new_cust','new_cust_pct','local_net','local_net_pct'];
  const recentFields = ['store_id','store_name','total_orders','overdue','overdue_rate',
    'recent_orders','recent_overdue','recent_overdue_rate'];
  const passFields = ['city','store_name','apply_total','pass','pass_rate','risk_reject','other_reject'];

  fs.writeFileSync('/mnt/d/desktop/门店分析_门店数据.csv', toCSV(output.stores, storeFields));
  fs.writeFileSync('/mnt/d/desktop/门店分析_代理商数据.csv', toCSV(output.suppliers, suppFields));
  fs.writeFileSync('/mnt/d/desktop/门店分析_近30天活跃.csv', toCSV(output.recentStores, recentFields));
  fs.writeFileSync('/mnt/d/desktop/门店分析_通过率.csv', toCSV(output.passRate, passFields));

  // Also output summary JSON
  fs.writeFileSync('/mnt/d/desktop/门店分析_汇总.json', JSON.stringify(output.meta, null, 2));

  console.log('\n✅ 数据已导出到 D:\\desktop');
  console.log(`  - 门店分析_门店数据.csv (${output.stores.length}行)`);
  console.log(`  - 门店分析_代理商数据.csv (${output.suppliers.length}行)`);
  console.log(`  - 门店分析_近30天活跃.csv (${output.recentStores.length}行)`);
  console.log(`  - 门店分析_通过率.csv (${output.passRate.length}行)`);

  conn.end();
}

main().catch(e => { console.error(e); process.exit(1); });
