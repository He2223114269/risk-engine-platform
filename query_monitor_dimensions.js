const mysql = require('mysql2/promise');

async function main() {
  const conn = await mysql.createConnection({
    host: '47.119.181.195', port: 9030,
    user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)",
    database: 'dws',
  });
  const q = async (sql) => { const [r] = await conn.query(sql); return r; };

  // 1. 新老客分析（公众）
  console.log("=== 1. 新老客分析（各省合计）===");
  const newold = await q(`
    SELECT old_new_customer AS 新老客, '合计' AS 省份,
      COUNT(*) AS 竣工数,
      SUM(CASE WHEN lmd_step_num_repay_status = 2 THEN 1 ELSE 0 END) AS 逾期数,
      ROUND(SUM(CASE WHEN lmd_step_num_repay_status = 2 THEN 1 ELSE 0 END)*100.0/COUNT(*),2) AS 逾期率
    FROM dws.dws_credit_yzf_order_complete
    WHERE source_business_type = '淘顺实时授信' AND province != '上海市' AND custtype = '00'
    GROUP BY old_new_customer ORDER BY 新老客
  `);
  console.table(newold);

  console.log("=== 1b. 各省新老客逾期率 ===");
  const newoldProv = await q(`
    SELECT province, old_new_customer AS 新老客,
      COUNT(*) AS 竣工数,
      SUM(CASE WHEN lmd_step_num_repay_status = 2 THEN 1 ELSE 0 END) AS 逾期数,
      ROUND(SUM(CASE WHEN lmd_step_num_repay_status = 2 THEN 1 ELSE 0 END)*100.0/COUNT(*),2) AS 逾期率
    FROM dws.dws_credit_yzf_order_complete
    WHERE source_business_type = '淘顺实时授信' AND province != '上海市' AND custtype = '00'
    GROUP BY province, old_new_customer ORDER BY province, 新老客
  `);
  console.table(newoldProv);

  // 2. 本异网分析
  console.log("\n=== 2. 本异网分析（各省合计）===");
  const net = await q(`
    SELECT CASE WHEN operator_real IN ('1','电信','3') THEN '本网' ELSE '异网' END AS 本异网, '合计' AS 省份,
      COUNT(*) AS 竣工数,
      SUM(CASE WHEN lmd_step_num_repay_status = 2 THEN 1 ELSE 0 END) AS 逾期数,
      ROUND(SUM(CASE WHEN lmd_step_num_repay_status = 2 THEN 1 ELSE 0 END)*100.0/COUNT(*),2) AS 逾期率
    FROM dws.dws_credit_yzf_order_complete
    WHERE source_business_type = '淘顺实时授信' AND complete_time >= '2025-03-01'
      AND province != '上海市' AND custtype = '00'
    GROUP BY 本异网 ORDER BY 本异网
  `);
  console.table(net);

  console.log("=== 2b. 各省本异网逾期率 ===");
  const netProv = await q(`
    SELECT province, CASE WHEN operator_real IN ('1','电信','3') THEN '本网' ELSE '异网' END AS 本异网,
      COUNT(*) AS 竣工数,
      SUM(CASE WHEN lmd_step_num_repay_status = 2 THEN 1 ELSE 0 END) AS 逾期数,
      ROUND(SUM(CASE WHEN lmd_step_num_repay_status = 2 THEN 1 ELSE 0 END)*100.0/COUNT(*),2) AS 逾期率
    FROM dws.dws_credit_yzf_order_complete
    WHERE source_business_type = '淘顺实时授信' AND complete_time >= '2025-03-01'
      AND province != '上海市' AND custtype = '00'
    GROUP BY province, 本异网 ORDER BY province, 本异网
  `);
  console.table(netProv);

  // 3. 全国质态分省份（latest month = 2026-04, 沿用现有表口径）
  console.log("\n=== 3. 全国质态（2026-04 最新月份）===");
  const quality = await q(`
    SELECT province AS 省份,
      COUNT(*) AS 总办单,
      SUM(IF(lmd_step_num_repay_status = 2, 1, 0)) AS 逾期数,
      ROUND(SUM(IF(lmd_step_num_repay_status = 2, 1, 0))*100.0/COUNT(*),2) AS 逾期率,
      ROUND(SUM(IF(lmd_step_num_repay_status = 2, remaining_principal, 0))/1000000,2) AS 逾期剩余本金万,
      ROUND(SUM(order_amt)/1000000,2) AS 订单金额万
    FROM dws.dws_credit_yzf_order_complete
    WHERE source_business_type = '淘顺实时授信'
      AND DATE_FORMAT(complete_time, '%Y-%m') = DATE_FORMAT(DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH), '%Y-%m')
      AND custtype = '00'
    GROUP BY province ORDER BY 总办单 DESC
  `);
  console.table(quality);

  // 4. 地市逾期率 Top高逾期（2026-04）
  console.log("\n=== 4. 高逾期地市 Top20（2026-04）===");
  const cityRisk = await q(`
    SELECT province AS 省份, city AS 地市,
      COUNT(*) AS 总办单,
      SUM(IF(lmd_step_num_repay_status = 2, 1, 0)) AS 逾期数,
      ROUND(SUM(IF(lmd_step_num_repay_status = 2, 1, 0))*100.0/COUNT(*),2) AS 逾期率
    FROM dws.dws_credit_yzf_order_complete
    WHERE source_business_type = '淘顺实时授信'
      AND DATE_FORMAT(complete_time, '%Y-%m') = DATE_FORMAT(DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH), '%Y-%m')
      AND custtype = '00'
    GROUP BY province, city
    HAVING 总办单 >= 30
    ORDER BY 逾期率 DESC LIMIT 20
  `);
  console.table(cityRisk);

  // 5. 月度趋势 - 近6月各省逾期
  console.log("\n=== 5. 近6月各省逾期趋势 ===");
  const monthly = await q(`
    SELECT province AS 省份, DATE_FORMAT(complete_time, '%Y-%m') AS 月份,
      COUNT(*) AS 总办单,
      SUM(IF(lmd_step_num_repay_status = 2, 1, 0)) AS 逾期数,
      ROUND(SUM(IF(lmd_step_num_repay_status = 2, 1, 0))*100.0/COUNT(*),2) AS 逾期率
    FROM dws.dws_credit_yzf_order_complete
    WHERE source_business_type = '淘顺实时授信'
      AND complete_time >= '2025-11-01'
      AND custtype = '00'
    GROUP BY province, 月份 ORDER BY province, 月份
  `);
  console.table(monthly);

  // 6. 异网占比概况（近30天 vs 上月）
  console.log("\n=== 6. 异网占比月度变化 ===");
  const netRatio = await q(`
    SELECT province,
      DATE_FORMAT(complete_time, '%Y-%m') AS 月份,
      COUNT(*) AS 总办单,
      SUM(CASE WHEN operator_real NOT IN ('1','电信','3') OR operator_real IS NULL THEN 1 ELSE 0 END) AS 异网数,
      ROUND(SUM(CASE WHEN operator_real NOT IN ('1','电信','3') OR operator_real IS NULL THEN 1 ELSE 0 END)*100.0/COUNT(*),1) AS 异网占比
    FROM dws.dws_credit_yzf_order_complete
    WHERE source_business_type = '淘顺实时授信' AND complete_time >= '2026-03-01' AND custtype = '00'
    GROUP BY province, 月份 ORDER BY province, 月份
  `);
  console.table(netRatio);

  await conn.end();
}

main().catch(e => { console.error(e); process.exit(1); });
