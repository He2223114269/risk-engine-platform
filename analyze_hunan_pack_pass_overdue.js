// 湖南 融合套餐 vs 单卡 通过率+逾期率分析
const mysql = require('mysql2/promise');

const SQL = `
  -- 近一年湖南各类套餐通过率+逾期率
  -- 步骤1: 湖南所有申请表 + DWS包名
  WITH apply_with_pack AS (
    SELECT
      a.ct_user_id,
      a.apply_status,
      a.apply_msg,
      a.store_addr_province,
      a.store_addr_city,
      a.add_time,
      COALESCE(d.pack_name, '未知') AS pack_name,
      d.lmd_step_num_repay_status,
      d.complete_time,
      d.order_no
    FROM ods.ods_ts_credit_yzf_order_grant_apply a
    LEFT JOIN dws.dws_credit_yzf_order_complete d
      ON a.ct_user_id = d.order_no
     AND d.source_business_type = '淘顺实时授信'
    WHERE a.store_addr_province = '湖南省'
      AND a.add_time >= '2025-05-19'
  )
  SELECT
    CASE WHEN pack_name LIKE '%融合%' THEN '融合套餐' ELSE '单卡' END AS 套餐类型,
    COUNT(*) AS 申请量,
    SUM(CASE WHEN apply_status = '授信成功' THEN 1 ELSE 0 END) AS 通过数,
    ROUND(SUM(CASE WHEN apply_status = '授信成功' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS 通过率,
    SUM(CASE WHEN apply_status != '授信成功' THEN 1 ELSE 0 END) AS 拒绝数,

    -- 逾期率（仅看竣工且已到还款期的）
    COUNT(order_no) AS 竣工数,
    SUM(CASE WHEN lmd_step_num_repay_status = 2 THEN 1 ELSE 0 END) AS 逾期数,
    ROUND(SUM(CASE WHEN lmd_step_num_repay_status = 2 THEN 1 ELSE 0 END) * 100.0 / NULLIF(SUM(CASE WHEN lmd_step_num_repay_status IN (1,2) THEN 1 ELSE 0 END), 0), 2) AS 逾期率
  FROM apply_with_pack
  GROUP BY 套餐类型
  ORDER BY 套餐类型
`;

const SQL_MONTHLY = `
  WITH apply_with_pack AS (
    SELECT
      a.ct_user_id,
      a.apply_status,
      a.add_time,
      COALESCE(d.pack_name, '未知') AS pack_name,
      d.lmd_step_num_repay_status,
      d.complete_time
    FROM ods.ods_ts_credit_yzf_order_grant_apply a
    LEFT JOIN dws.dws_credit_yzf_order_complete d
      ON a.ct_user_id = d.order_no
     AND d.source_business_type = '淘顺实时授信'
    WHERE a.store_addr_province = '湖南省'
      AND a.add_time >= '2025-05-19'
  )
  SELECT
    DATE_FORMAT(add_time, '%Y-%m') AS 月份,
    CASE WHEN pack_name LIKE '%融合%' THEN '融合套餐' ELSE '单卡' END AS 套餐类型,
    COUNT(*) AS 申请量,
    SUM(CASE WHEN apply_status = '授信成功' THEN 1 ELSE 0 END) AS 通过数,
    ROUND(SUM(CASE WHEN apply_status = '授信成功' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS 通过率,
    SUM(CASE WHEN lmd_step_num_repay_status = 2 THEN 1 ELSE 0 END) AS 逾期数,
    ROUND(SUM(CASE WHEN lmd_step_num_repay_status = 2 THEN 1 ELSE 0 END) * 100.0 / NULLIF(SUM(CASE WHEN lmd_step_num_repay_status IN (1,2) THEN 1 ELSE 0 END), 0), 2) AS 逾期率
  FROM apply_with_pack
  GROUP BY 月份, 套餐类型
  ORDER BY 月份, 套餐类型
`;

// 看看湖南有什么pack_name
const SQL_PACK_NAMES = `
  SELECT pack_name, COUNT(*) AS cnt
  FROM dws.dws_credit_yzf_order_complete
  WHERE source_business_type = '淘顺实时授信' AND province = '湖南省'
    AND complete_time >= '2025-05-19'
  GROUP BY pack_name
  ORDER BY cnt DESC
  LIMIT 30
`;

const SQL_DETAIL = `
  -- 5/19后湖南各pack_name通过率+逾期率
  WITH apply_with_pack AS (
    SELECT
      a.apply_status, a.add_time,
      COALESCE(d.pack_name, '无包名') AS pack_name,
      d.lmd_step_num_repay_status
    FROM ods.ods_ts_credit_yzf_order_grant_apply a
    LEFT JOIN dws.dws_credit_yzf_order_complete d
      ON a.ct_user_id = d.order_no
     AND d.source_business_type = '淘顺实时授信'
    WHERE a.store_addr_province = '湖南省'
      AND a.add_time >= '2025-05-19'
  )
  SELECT
    pack_name AS 套餐名称,
    COUNT(*) AS 申请量,
    SUM(CASE WHEN apply_status = '授信成功' THEN 1 ELSE 0 END) AS 通过数,
    ROUND(SUM(CASE WHEN apply_status = '授信成功' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS 通过率,
    SUM(CASE WHEN lmd_step_num_repay_status = 2 THEN 1 ELSE 0 END) AS 逾期数,
    ROUND(SUM(CASE WHEN lmd_step_num_repay_status = 2 THEN 1 ELSE 0 END) * 100.0 / NULLIF(SUM(CASE WHEN lmd_step_num_repay_status IN (1,2) THEN 1 ELSE 0 END), 0), 2) AS 逾期率
  FROM apply_with_pack
  GROUP BY pack_name
  ORDER BY 申请量 DESC
`;

async function main() {
  const conn = await mysql.createConnection({
    host: '47.119.181.195', port: 9030,
    user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)",
    database: 'ods',
  });

  console.log('=== 湖南各套餐名称分布（竣工订单）===');
  const [packs] = await conn.query({ sql: SQL_PACK_NAMES, rowsAsArray: false });
  console.table(packs);

  console.log('\n=== 湖南 融合套餐 vs 单卡 汇总 ===');
  const [rows] = await conn.query({ sql: SQL, rowsAsArray: false });
  console.table(rows);

  console.log('\n=== 湖南 月度趋势 ===');
  const [monthly] = await conn.query({ sql: SQL_MONTHLY, rowsAsArray: false });
  console.table(monthly);

  console.log('\n=== 湖南 详细套餐通过率/逾期率 ===');
  const [detail] = await conn.query({ sql: SQL_DETAIL, rowsAsArray: false });
  console.table(detail);

  await conn.end();
}

main().catch(e => { console.error(e); process.exit(1); });
