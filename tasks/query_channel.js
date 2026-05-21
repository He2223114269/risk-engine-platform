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

  // ========== 渠道评级 vs 实际质态 ==========
  console.log('1. 渠道评级与实际质态交叉分析...');
  const [cross] = await conn.query(`
    select 
      s.channel_level,
      count(distinct s.id) as store_count,
      count(*) as total_orders,
      sum(case when o.step_num_repay_status = 2 then 1 else 0 end) as overdue,
      round(sum(case when o.step_num_repay_status = 2 then 1 else 0 end) * 100.0 / count(*), 2) as actual_overdue_rate,
      sum(case when o.old_new_customer = '新客户' then 1 else 0 end) as new_cust,
      round(avg(o.operator_real = 3) * 100, 2) as local_net_pct
    from ods.ods_ts_v3_order_store s
    inner join dws_credit_yzf_order_complete o
      on s.store_code = o.store_id
    where s.isv = '淘顺' and s.type = '翼支付实时授信'
      and o.source_business_type = '淘顺实时授信'
    group by s.channel_level
    order by actual_overdue_rate desc
  `);
  console.log('渠道级别 | 门店数 | 办单 | 实际逾期率 | 新客占比');
  cross.forEach(r => {
    console.log(r.channel_level, '|', r.store_count, '|', r.total_orders, '|', r.actual_overdue_rate + '%', '|', r.new_cust);
  });

  // ========== 错误分类门店：高逾期但评级好 ==========
  console.log('\n2. 错分门店（高逾期率但为优质/普通渠道）...');
  const [misclassified] = await conn.query(`
    select 
      s.province, s.city,
      o.store_id, o.store_name,
      s.channel_level, s.notes,
      count(*) as total_orders,
      sum(case when o.step_num_repay_status = 2 then 1 else 0 end) as overdue,
      round(sum(case when o.step_num_repay_status = 2 then 1 else 0 end) * 100.0 / count(*), 2) as actual_rate
    from ods.ods_ts_v3_order_store s
    inner join dws_credit_yzf_order_complete o
      on s.store_code = o.store_id
    where s.isv = '淘顺' and s.type = '翼支付实时授信'
      and s.channel_level in ('优质渠道', '普通渠道', '扶持渠道')
      and o.source_business_type = '淘顺实时授信'
    group by o.store_id, o.store_name, s.province, s.city, s.channel_level, s.notes
    having actual_rate >= 8 and total_orders >= 20
    order by actual_rate desc
  `);
  console.log(`${misclassified.length}家错分门店`);
  misclassified.slice(0, 15).forEach(r => {
    console.log(r.store_name, '|', r.province + '/' + r.city, '| 评级:', r.channel_level, '| 实际逾期:', r.actual_rate + '%', '| 备注:', r.notes || '-');
  });

  // ========== 拉黑/拉灰门店的实际质态 ==========
  console.log('\n3. 拉黑/拉灰门店的质态（验证评级的准确性）...');
  const [black] = await conn.query(`
    select 
      s.channel_level,
      count(*) as stores,
      round(avg(case when total >= 10 then overdue_rate else null end), 2) as avg_overdue_rate
    from (
      select s.channel_level, o.store_id,
        count(*) as total,
        sum(case when o.step_num_repay_status = 2 then 1 else 0 end) * 100.0 / count(*) as overdue_rate
      from ods.ods_ts_v3_order_store s
      inner join dws_credit_yzf_order_complete o
        on s.store_code = o.store_id
      where s.isv = '淘顺' and s.type = '翼支付实时授信'
        and o.source_business_type = '淘顺实时授信'
        and s.channel_level in ('拉黑渠道', '拉灰渠道')
      group by s.channel_level, o.store_id
    ) t
    group by channel_level
  `);
  black.forEach(r => console.log(r.channel_level, '|', r.stores, '家 | 平均逾期率', r.avg_overdue_rate + '%'));

  // ========== 写入CSV ==========
  function toCSV(rows, fields) {
    const h = fields.join(',');
    const l = rows.map(r => fields.map(f => {
      const v = r[f]; if (v===null||v===undefined) return '';
      const s = String(v); return s.includes(',')||s.includes('"')||s.includes('\n') ? '"'+s.replace(/"/g,'""')+'"' : s;
    }).join(','));
    return h+'\n'+l.join('\n');
  }

  if (misclassified.length > 0) {
    const mf = ['province','city','store_id','store_name','channel_level','notes','total_orders','overdue','actual_rate'];
    fs.writeFileSync(dir+'/门店_评级与实际偏差.csv', toCSV(misclassified, mf));
    console.log(`\n✅ 错分门店数据已写入: ${misclassified.length}家`);
  }

  console.log('\n✅ 渠道评级分析完成');
  conn.end();
}
main().catch(e => { console.error(e); process.exit(1); });
