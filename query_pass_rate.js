const mysql = require('mysql2/promise');

async function main() {
  const conn = await mysql.createConnection({
    host: '47.119.181.195',
    port: 9030,
    user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)",
    database: 'ods',
  });

  // 5/10 那8单的申请详情（有无初审/复审区别等）
  const detailSql = `
    select 
      g.store_addr_city as 地市,
      g.store_name as 门店,
      g.apply_status as 申请状态,
      g.apply_msg as 拒绝原因,
      g.add_time as 申请时间,
      w.order_no,
      w.first_risk_result as 初审结果,
      w.second_risk_result as 复审结果,
      w.recall_strategy as 捞回策略,
      w.operator_real as 运营商,
      w.online_duration as 在网时长,
      w.lxf as lxf分值
    from ods_ts_credit_yzf_order_grant_apply g
    left join ods_ts_order_white_list_control w on g.ct_user_id = w.order_no
    where g.store_addr_province = '海南省' and g.store_addr_city = '儋州市'
      and g.store_name like '%解放路%金鹏%'
      and date_format(g.add_time, '%Y-%m-%d') = '2026-05-10'
    order by g.add_time
  `;

  const [detail] = await conn.query(detailSql);
  console.log('=== 5/10 解放路金鹏 申请风控详情 ===');
  console.table(detail);

  // 再看这款店的集中申请模式：每天申请量vs通过率散点
  const patternSql = `
    select 
      date_format(add_time, '%Y-%m-%d') as 日期,
      count(*) as 申请量,
      sum(case when apply_status = '授信成功' then 1 else 0 end) as 通过数,
      concat(round(sum(case when apply_status = '授信成功' then 1 else 0 end) * 100.0 / count(*), 2), '%') as 通过率
    from (
      select apply_status, add_time from ods_ts_credit_yzf_order_grant_apply
      where store_addr_province = '海南省' and store_addr_city = '儋州市'
        and store_name like '%解放路%金鹏%'
      union all
      select apply_status, add_time from ods_bl_credit_yzf_order_grant_apply
      where store_addr_province = '海南省' and store_addr_city = '儋州市'
        and store_name like '%解放路%金鹏%'
    ) t
    group by 日期
    having 申请量 >= 5
    order by 申请量 desc, 日期 desc
  `;

  const [pattern] = await conn.query(patternSql);
  console.log('\n=== 解放路金鹏 高峰日（>=5单）通过率 ===');
  console.table(pattern);

  conn.end();
}

main().catch(err => { console.error(err); process.exit(1); });
