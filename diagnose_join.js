// 诊断：看看湖南申请表和DWS的关联情况
const mysql = require('mysql2/promise');

async function main() {
  const conn = await mysql.createConnection({
    host: '47.119.181.195', port: 9030,
    user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)",
    database: 'ods',
  });

  // 1. 湖南申请表抽样
  console.log('=== 湖南申请表order_no样例 ===');
  const [apps] = await conn.query(`
    SELECT ct_user_id, apply_status, add_time
    FROM ods_ts_credit_yzf_order_grant_apply
    WHERE store_addr_province = '湖南省'
    LIMIT 5
  `);
  console.table(apps);

  // 2. 湖南DWS订单号样例
  console.log('\n=== 湖南DWS order_no样例 ===');
  const [dws] = await conn.query(`
    SELECT order_no, complete_time, pack_name
    FROM dws.dws_credit_yzf_order_complete
    WHERE source_business_type = '淘顺实时授信' AND province = '湖南省'
    LIMIT 5
  `);
  console.table(dws);

  // 3. 直接join看看匹配数
  console.log('\n=== 匹配数 ===');
  const [match] = await conn.query(`
    SELECT
      (SELECT COUNT(*) FROM ods_ts_credit_yzf_order_grant_apply WHERE store_addr_province = '湖南省') AS 申请数,
      (SELECT COUNT(*) FROM dws.dws_credit_yzf_order_complete WHERE source_business_type = '淘顺实时授信' AND province = '湖南省') AS 竣工数,
      (SELECT COUNT(*) FROM ods_ts_credit_yzf_order_grant_apply a
       INNER JOIN dws.dws_credit_yzf_order_complete d ON a.ct_user_id = d.order_no
       WHERE a.store_addr_province = '湖南省' AND d.source_business_type = '淘顺实时授信') AS 匹配数
  `);
  console.table(match);

  // 4. 看看ct_user_id和order_no的格式是否相同
  console.log('\n=== 湖南申请表ct_user_id前5个 ===');
  const [ids] = await conn.query(`
    SELECT ct_user_id, LENGTH(ct_user_id) AS len, LEFT(ct_user_id, 3) AS prefix
    FROM ods_ts_credit_yzf_order_grant_apply
    WHERE store_addr_province = '湖南省'
    LIMIT 10
  `);
  console.table(ids);

  console.log('\n=== 湖南DWS order_no前5个 ===');
  const [oids] = await conn.query(`
    SELECT order_no, LENGTH(order_no) AS len, LEFT(order_no, 3) AS prefix
    FROM dws.dws_credit_yzf_order_complete
    WHERE source_business_type = '淘顺实时授信' AND province = '湖南省'
    LIMIT 10
  `);
  console.table(oids);

  // 5. 试试左连接看是否有配上的
  console.log('\n=== 左连接部分数据 ===');
  const [lj] = await conn.query(`
    SELECT a.ct_user_id, d.order_no, d.pack_name
    FROM ods_ts_credit_yzf_order_grant_apply a
    LEFT JOIN dws.dws_credit_yzf_order_complete d ON a.ct_user_id = d.order_no AND d.source_business_type = '淘顺实时授信'
    WHERE a.store_addr_province = '湖南省'
    LIMIT 15
  `);
  console.table(lj);

  await conn.end();
}

main().catch(e => { console.error(e); process.exit(1); });
