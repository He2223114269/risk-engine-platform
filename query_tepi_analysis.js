const mysql = require('mysql2/promise');

async function main() {
  const conn = await mysql.createConnection({
    host: '47.119.181.195', port: 9030,
    user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)",
    database: 'dws',
  });
  const q = async (sql) => { const [r] = await conn.query(sql); return r; };

  // 1. 特批白名单 vs 正常公众 整体对比
  console.log("=== 1. 特批白名单 vs 正常公众 整体对比 ===");
  const overview = await q(`
    SELECT 
      CASE WHEN order_channel_id = '特批白名单' THEN '特批白名单' ELSE '正常公众' END AS 客群,
      COUNT(*) AS 办单数,
      SUM(CASE WHEN step_num_repay_status = 2 THEN 1 ELSE 0 END) AS 逾期数,
      ROUND(SUM(CASE WHEN step_num_repay_status = 2 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS 逾期率,
      ROUND(AVG(order_amt_yuan), 2) AS 平均金额
    FROM dws.dws_credit_yzf_order_complete
    WHERE source_business_type = '淘顺实时授信'
      AND custtype = '00'
      AND complete_time >= '2025-01-01'
    GROUP BY 客群
    ORDER BY 逾期率 DESC
  `);
  console.table(overview);

  // 2. 特批门店逾期率>20%且办单>=5
  console.log("\n=== 2. 特批高风险门店（逾期率>20% 且 办单>=5） ===");
  const highRisk = await q(`
    SELECT 
      province, store_name,
      COUNT(*) AS 办单数,
      SUM(CASE WHEN step_num_repay_status = 2 THEN 1 ELSE 0 END) AS 逾期数,
      ROUND(SUM(CASE WHEN step_num_repay_status = 2 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS 逾期率
    FROM dws.dws_credit_yzf_order_complete
    WHERE source_business_type = '淘顺实时授信'
      AND custtype = '00'
      AND order_channel_id = '特批白名单'
      AND complete_time >= '2025-01-01'
    GROUP BY province, store_name
    HAVING 办单数 >= 5 AND 逾期率 > 20
    ORDER BY 逾期率 DESC
  `);
  console.table(highRisk);
  console.log(`高风险门店数: ${highRisk.length}`);

  // 3. 特批门店省份分布
  console.log("\n=== 3. 特批门店省份分布 ===");
  const provDist = await q(`
    SELECT 
      province,
      COUNT(DISTINCT store_name) AS 门店数,
      COUNT(*) AS 办单数,
      SUM(CASE WHEN step_num_repay_status = 2 THEN 1 ELSE 0 END) AS 逾期数,
      ROUND(SUM(CASE WHEN step_num_repay_status = 2 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS 逾期率
    FROM dws.dws_credit_yzf_order_complete
    WHERE source_business_type = '淘顺实时授信'
      AND custtype = '00'
      AND order_channel_id = '特批白名单'
      AND complete_time >= '2025-01-01'
    GROUP BY province
    ORDER BY 办单数 DESC
  `);
  console.table(provDist);

  // 4. 特批月度趋势
  console.log("\n=== 4. 特批月度趋势 ===");
  const monthly = await q(`
    SELECT 
      DATE_FORMAT(complete_time, '%Y-%m') AS 月份,
      COUNT(*) AS 办单数,
      SUM(CASE WHEN step_num_repay_status = 2 THEN 1 ELSE 0 END) AS 逾期数,
      ROUND(SUM(CASE WHEN step_num_repay_status = 2 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS 逾期率,
      ROUND(AVG(order_amt_yuan), 2) AS 平均金额
    FROM dws.dws_credit_yzf_order_complete
    WHERE source_business_type = '淘顺实时授信'
      AND custtype = '00'
      AND order_channel_id = '特批白名单'
      AND complete_time >= '2025-01-01'
    GROUP BY 月份
    ORDER BY 月份 ASC
  `);
  console.table(monthly);

  // 5. 正常公众月度趋势（对照）
  console.log("\n=== 5. 正常公众月度趋势 ===");
  const normalMonthly = await q(`
    SELECT 
      DATE_FORMAT(complete_time, '%Y-%m') AS 月份,
      COUNT(*) AS 办单数,
      SUM(CASE WHEN step_num_repay_status = 2 THEN 1 ELSE 0 END) AS 逾期数,
      ROUND(SUM(CASE WHEN step_num_repay_status = 2 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS 逾期率
    FROM dws.dws_credit_yzf_order_complete
    WHERE source_business_type = '淘顺实时授信'
      AND custtype = '00'
      AND (order_channel_id != '特批白名单' OR order_channel_id IS NULL)
      AND complete_time >= '2025-01-01'
    GROUP BY 月份
    ORDER BY 月份 ASC
  `);
  console.table(normalMonthly);

  // 6. 特批门店TOP高风险明细（全部字段用于月报）
  console.log("\n=== 6. 特批高风险门店 TOP20 ===");
  const top20 = await q(`
    SELECT 
      province, store_name,
      COUNT(*) AS 办单数,
      SUM(CASE WHEN step_num_repay_status = 2 THEN 1 ELSE 0 END) AS 逾期数,
      ROUND(SUM(CASE WHEN step_num_repay_status = 2 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS 逾期率,
      ROUND(AVG(order_amt_yuan), 2) AS 平均金额,
      ROUND(SUM(CASE WHEN old_new_customer = '新客户' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS 新客占比,
      ROUND(SUM(CASE WHEN operator_real IN ('1','电信','3') THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS 本网占比
    FROM dws.dws_credit_yzf_order_complete
    WHERE source_business_type = '淘顺实时授信'
      AND custtype = '00'
      AND order_channel_id = '特批白名单'
      AND complete_time >= '2025-01-01'
    GROUP BY province, store_name
    HAVING 办单数 >= 5 AND 逾期率 > 20
    ORDER BY 逾期率 DESC
    LIMIT 20
  `);
  console.table(top20);

  await conn.end();
}

main().catch(e => { console.error(e); process.exit(1); });
