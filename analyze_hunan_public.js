// 湖南 融合套餐 vs 单卡 — 仅公众用户(custtype='00')
const mysql = require('mysql2/promise');

async function main() {
  const conn = await mysql.createConnection({
    host: '47.119.181.195', port: 9030,
    user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)",
    database: 'ods',
  });
  const q = async (sql) => { const [r] = await conn.query(sql); return r; };

  console.log('===== 1. 通过率 — 公众用户 =====');
  const pass = await q(`
    SELECT
      CASE WHEN pack_name LIKE '%融合%' THEN '融合套餐' ELSE '单卡' END AS 套餐类型,
      COUNT(*) AS 申请量,
      SUM(CASE WHEN apply_status = '授信成功' THEN 1 ELSE 0 END) AS 通过数,
      ROUND(SUM(CASE WHEN apply_status = '授信成功' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS 通过率
    FROM ods.ods_ts_credit_yzf_order_grant_apply
    WHERE store_addr_province = '湖南省'
      AND add_time >= '2025-05-19'
      AND custtype = '00'
      AND pack_name IS NOT NULL AND pack_name != ''
    GROUP BY 套餐类型
    ORDER BY 套餐类型
  `);
  console.table(pass);

  console.log('\n===== 2. 逾期率（质态）— 公众用户 =====');
  const overdue = await q(`
    SELECT
      CASE WHEN pack_name LIKE '%融合%' THEN '融合套餐' ELSE '单卡' END AS 套餐类型,
      COUNT(*) AS 竣工数,
      SUM(CASE WHEN lmd_step_num_repay_status IN (1,2) THEN 1 ELSE 0 END) AS 已到还款期数,
      SUM(CASE WHEN lmd_step_num_repay_status = 2 THEN 1 ELSE 0 END) AS 逾期数,
      ROUND(SUM(CASE WHEN lmd_step_num_repay_status = 2 THEN 1 ELSE 0 END) * 100.0 /
        NULLIF(SUM(CASE WHEN lmd_step_num_repay_status IN (1,2) THEN 1 ELSE 0 END), 0), 2) AS 逾期率
    FROM dws.dws_credit_yzf_order_complete
    WHERE source_business_type = '淘顺实时授信'
      AND province = '湖南省'
      AND complete_time >= '2025-05-19'
      AND custtype = '00'
      AND pack_name IS NOT NULL AND pack_name != ''
    GROUP BY 套餐类型
    ORDER BY 套餐类型
  `);
  console.table(overdue);

  console.log('\n===== 3. 月度通过率趋势 — 公众 =====');
  const monthlyPass = await q(`
    SELECT
      DATE_FORMAT(add_time, '%Y-%m') AS 月份,
      CASE WHEN pack_name LIKE '%融合%' THEN '融合套餐' ELSE '单卡' END AS 套餐类型,
      COUNT(*) AS 申请量,
      SUM(CASE WHEN apply_status = '授信成功' THEN 1 ELSE 0 END) AS 通过数,
      ROUND(SUM(CASE WHEN apply_status = '授信成功' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS 通过率
    FROM ods.ods_ts_credit_yzf_order_grant_apply
    WHERE store_addr_province = '湖南省'
      AND add_time >= '2025-05-01'
      AND custtype = '00'
      AND pack_name IS NOT NULL AND pack_name != ''
    GROUP BY 月份, 套餐类型
    ORDER BY 月份, 套餐类型
  `);
  console.table(monthlyPass);

  console.log('\n===== 4. 月度逾期率趋势 — 公众 =====');
  const monthlyOverdue = await q(`
    SELECT
      DATE_FORMAT(complete_time, '%Y-%m') AS 月份,
      CASE WHEN pack_name LIKE '%融合%' THEN '融合套餐' ELSE '单卡' END AS 套餐类型,
      COUNT(*) AS 竣工数,
      SUM(CASE WHEN lmd_step_num_repay_status IN (1,2) THEN 1 ELSE 0 END) AS 已到还款期数,
      SUM(CASE WHEN lmd_step_num_repay_status = 2 THEN 1 ELSE 0 END) AS 逾期数,
      ROUND(SUM(CASE WHEN lmd_step_num_repay_status = 2 THEN 1 ELSE 0 END) * 100.0 /
        NULLIF(SUM(CASE WHEN lmd_step_num_repay_status IN (1,2) THEN 1 ELSE 0 END), 0), 2) AS 逾期率
    FROM dws.dws_credit_yzf_order_complete
    WHERE source_business_type = '淘顺实时授信'
      AND province = '湖南省'
      AND complete_time >= '2025-05-01'
      AND custtype = '00'
      AND pack_name IS NOT NULL AND pack_name != ''
    GROUP BY 月份, 套餐类型
    ORDER BY 月份, 套餐类型
  `);
  console.table(monthlyOverdue);

  await conn.end();
}

main().catch(e => { console.error(e); process.exit(1); });
