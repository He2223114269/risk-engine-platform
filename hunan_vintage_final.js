// 湖南公众用户 融合套餐 vs 单卡 Vintage分析 + 终损预测
const mysql = require('mysql2/promise');
const XLSX = require('xlsx');
const fs = require('fs');

async function main() {
  const conn = await mysql.createConnection({
    host: '47.119.181.195', port: 9030,
    user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)",
    database: 'dws',
  });
  const q = async (sql) => { const [r] = await conn.query(sql); return r; };
  const ODS = 'ods.ods_ts_credit_yzf_order_grant_apply';
  const DWS = 'dws.dws_credit_yzf_order_complete';
  const base = `source_business_type = '淘顺实时授信' AND province = '湖南省' AND custtype = '00' AND pack_name IS NOT NULL AND pack_name != ''`;
  const pkCond = (t) => t === '单卡' ? "pack_name NOT LIKE '%融合%'" : "pack_name LIKE '%融合%'";

  // =============================
  // 1. 总览
  // =============================
  const pass = await q(`
    SELECT CASE WHEN pack_name LIKE '%融合%' THEN '融合套餐' ELSE '单卡' END AS 套餐类型,
      COUNT(*) AS 申请量,
      SUM(IF(apply_status='授信成功',1,0)) AS 通过数,
      ROUND(SUM(IF(apply_status='授信成功',1,0))*100.0/COUNT(*),2) AS 通过率
    FROM ${ODS} WHERE store_addr_province='湖南省' AND custtype='00'
      AND add_time>='2025-05-19' AND pack_name IS NOT NULL AND pack_name != ''
    GROUP BY 1 ORDER BY 1
  `);
  const overdue = await q(`
    SELECT CASE WHEN pack_name LIKE '%融合%' THEN '融合套餐' ELSE '单卡' END AS 套餐类型,
      COUNT(*) AS 竣工数,
      SUM(IF(lmd_step_num_repay_status IN (1,2),1,0)) AS 已到还款,
      SUM(IF(lmd_step_num_repay_status=2,1,0)) AS 逾期数,
      ROUND(SUM(IF(lmd_step_num_repay_status=2,1,0))*100.0/NULLIF(SUM(IF(lmd_step_num_repay_status IN (1,2),1,0)),0),2) AS 逾期率,
      ROUND(SUM(order_amt)/1000000,2) AS 放款金额万
    FROM ${DWS} WHERE ${base} AND complete_time>='2025-05-19'
    GROUP BY 1 ORDER BY 1
  `);

  // =============================
  // 2. Vintage: 各月份竣工批次当前逾期情况
  // =============================
  const mobCalc = (ym) => {
    const [y, m] = ym.split('-').map(Number);
    return (2026 - y) * 12 + (5 - m);
  };
  const vintages = {};
  for (const ptype of ['单卡', '融合套餐']) {
    const raw = await q(`
      SELECT DATE_FORMAT(complete_time,'%Y-%m') AS 月份,
        COUNT(*) AS 竣工数,
        ROUND(SUM(order_amt)/1000000,2) AS 放款金额万,
        SUM(IF(lmd_step_num_repay_status=2,1,0)) AS 逾期数,
        SUM(IF(lmd_step_num_repay_status IN (1,2),1,0)) AS 应还数,
        ROUND(SUM(IF(lmd_step_num_repay_status=2,1,0))*100.0/NULLIF(SUM(IF(lmd_step_num_repay_status IN (1,2),1,0)),0),2) AS 逾期率
      FROM ${DWS} WHERE ${base} AND ${pkCond(ptype)}
        AND complete_time >= '2024-04-01' AND complete_time < '2026-06-01'
      GROUP BY 1 ORDER BY 1
    `);
    vintages[ptype] = raw.map(r => ({ ...r, MOB: mobCalc(r.月份) }));
    console.log(`${ptype} vintage rows: ${vintages[ptype].length}`);
  }

  // =============================
  // 3. 终损预测 — 方法二
  // =============================
  const predictions = {};
  for (const ptype of ['单卡', '融合套餐']) {
    const rows = vintages[ptype];
    // 成熟批次: MOB >= 6 且 竣工数 >= 30
    const mature = rows.filter(r => r.MOB >= 6 && parseInt(r.竣工数) >= 30);
    const totalAmtMature = mature.reduce((s, r) => s + parseFloat(r.放款金额万), 0);
    const weightedOvr = totalAmtMature > 0
      ? mature.reduce((s, r) => s + parseFloat(r.放款金额万) * parseFloat(r.逾期率), 0) / totalAmtMature
      : 0;

    // 近1年 (2025-05起) 所有批次的放款总额
    const recent = rows.filter(r => r.月份 >= '2025-05');
    const totalAmtRecent = recent.reduce((s, r) => s + parseFloat(r.放款金额万), 0);
    const predLoss = totalAmtRecent * weightedOvr / 100;

    predictions[ptype] = {
      matureBatches: mature,
      matureCount: mature.length,
      weightedOvr: weightedOvr,
      totalAmtMature: totalAmtMature,
      totalAmtRecent: totalAmtRecent,
      predLoss: predLoss
    };

    console.log(`\n${ptype}:`);
    console.log(`  成熟批次(MOB≥6): ${mature.length}`);
    mature.forEach(r => console.log(`    ${r.月份}: 竣工${r.竣工数} 放款${r.放款金额万}万 逾期率${r.逾期率}% MOB${r.MOB}`));
    console.log(`  加权平均终损率: ${weightedOvr.toFixed(2)}%`);
    console.log(`  近1年放款: ${totalAmtRecent.toFixed(2)}万`);
    console.log(`  预测终损: ${predLoss.toFixed(2)}万`);
  }

  const totalAmt = Object.values(predictions).reduce((s, p) => s + p.totalAmtRecent, 0);
  const totalLoss = Object.values(predictions).reduce((s, p) => s + p.predLoss, 0);

  // =============================
  // 4. 生成 Markdown
  // =============================
  let md = `# 湖南公众用户 融合套餐 vs 单卡 分析报告

**数据范围**: 近1年（2025-05-19 ~ 2026-05-19）| **客群**: 公众用户(custtype='00') | **地区**: 湖南省

---

## 一、总览

| 套餐类型 | 申请量 | 通过数 | 通过率 | 竣工数 | 逾期数 | 逾期率 | 放款金额(万元) |
|:--------:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-------------:|
| 单卡 | ${pass[0].申请量} | ${pass[0].通过数} | ${pass[0].通过率}% | ${overdue[0].竣工数} | ${overdue[0].逾期数} | ${overdue[0].逾期率}% | ${overdue[0].放款金额万} |
| 融合套餐 | ${pass[1].申请量} | ${pass[1].通过数} | ${pass[1].通过率}% | ${overdue[1].竣工数} | ${overdue[1].逾期数} | ${overdue[1].逾期率}% | ${overdue[1].放款金额万} |

**关键发现：**
- 融合套餐通过率 **${pass[1].通过率}%** vs 单卡 **${pass[0].通过率}%**（高 **${(parseFloat(pass[1].通过率)-parseFloat(pass[0].通过率)).toFixed(2)}pp**）
- 融合套餐逾期率 **${overdue[1].逾期率}%** vs 单卡 **${overdue[0].逾期率}%**（单卡是融合的 **${(parseFloat(overdue[0].逾期率)/parseFloat(overdue[1].逾期率)).toFixed(1)}倍**）

---

## 二、月度通过率趋势\n\n| 月份 | 单卡申请 | 单卡通过率 | 融合申请 | 融合通过率 | 差距 |\n|:----:|:-------:|:---------:|:-------:|:---------:|:----:|\n`;

  // 月度通过率 — 用单次查询
  const mp = await q(`
    SELECT DATE_FORMAT(add_time,'%Y-%m') AS 月份,
      CASE WHEN pack_name LIKE '%融合%' THEN '融合套餐' ELSE '单卡' END AS 套餐类型,
      COUNT(*) AS 申请量,
      SUM(IF(apply_status='授信成功',1,0)) AS 通过数,
      ROUND(SUM(IF(apply_status='授信成功',1,0))*100.0/COUNT(*),2) AS 通过率
    FROM ${ODS} WHERE store_addr_province='湖南省' AND custtype='00'
      AND add_time>='2025-05-01' AND pack_name IS NOT NULL AND pack_name != ''
    GROUP BY 1,2 ORDER BY 1,2
  `);

  const mpMap = {};
  for (const r of mp) {
    if (!mpMap[r.月份]) mpMap[r.月份] = {};
    mpMap[r.月份][r.套餐类型] = r;
  }
  for (const m of Object.keys(mpMap).sort()) {
    const d = mpMap[m]['单卡'], r = mpMap[m]['融合套餐'];
    if (!d || !r) continue;
    const diff = (parseFloat(r.通过率) - parseFloat(d.通过率)).toFixed(2);
    md += `| ${m} | ${d.申请量} | ${d.通过率}% | ${r.申请量} | ${r.通过率}% | ${diff}pp |\n`;
  }

  md += `\n## 三、月度逾期率趋势\n\n| 月份 | 单卡竣工 | 单卡逾期率 | 融合竣工 | 融合逾期率 | 单卡/融合 |\n|:----:|:-------:|:---------:|:-------:|:---------:|:---------:|\n`;

  const mo = await q(`
    SELECT DATE_FORMAT(complete_time,'%Y-%m') AS 月份,
      CASE WHEN pack_name LIKE '%融合%' THEN '融合套餐' ELSE '单卡' END AS 套餐类型,
      COUNT(*) AS 竣工数,
      SUM(IF(lmd_step_num_repay_status=2,1,0)) AS 逾期数,
      ROUND(SUM(IF(lmd_step_num_repay_status=2,1,0))*100.0/NULLIF(SUM(IF(lmd_step_num_repay_status IN (1,2),1,0)),0),2) AS 逾期率
    FROM ${DWS} WHERE ${base} AND complete_time>='2025-05-01'
    GROUP BY 1,2 ORDER BY 1,2
  `);
  const moMap = {};
  for (const r of mo) {
    if (!moMap[r.月份]) moMap[r.月份] = {};
    moMap[r.月份][r.套餐类型] = r;
  }
  for (const m of Object.keys(moMap).sort()) {
    const d = moMap[m]['单卡'], r = moMap[m]['融合套餐'];
    if (!d || !r) continue;
    const ratio = parseFloat(r.逾期率) > 0 ? `${(parseFloat(d.逾期率)/parseFloat(r.逾期率)).toFixed(1)}x` : '-';
    md += `| ${m} | ${d.竣工数} | ${d.逾期率}% | ${r.竣工数} | ${r.逾期率}% | ${ratio} |\n`;
  }

  md += `\n## 四、Vintage分析（各批次累计逾期率）\n\n`;
  for (const ptype of ['单卡', '融合套餐']) {
    md += `### ${ptype}\n\n`;
    const rows = vintages[ptype];
    if (rows.length === 0) { md += `（无数据）\n\n`; continue; }
    md += `| 批次 | 竣工数 | 放款(万) | MOB | 逾期率(%) |\n|:---:|:-----:|:-------:|:---:|:---------:|\n`;
    for (const r of rows) {
      md += `| ${r.月份} | ${r.竣工数} | ${r.放款金额万} | ${r.MOB} | ${r.逾期率} |\n`;
    }
    md += `\n`;
  }

  // 五、终损预测
  md += `## 五、终损预测（方法二：成熟批次加权均值法）\n\n`;
  md += `**方法说明：** 取MOB≥6的成熟批次，按放款金额加权计算逾期率均值作为"终损率"，应用于近1年（2025-05起）所有批次。\n\n`;

  for (const ptype of ['单卡', '融合套餐']) {
    const p = predictions[ptype];
    md += `### ${ptype}\n\n`;
    if (p.matureCount === 0) { md += `（无成熟批次）\n\n`; continue; }
    md += `**成熟批次明细：**\n\n`;
    md += `| 批次 | 竣工数 | 放款(万) | 逾期率(%) | MOB |\n|:---:|:-----:|:-------:|:---------:|:---:|\n`;
    for (const r of p.matureBatches) {
      md += `| ${r.月份} | ${r.竣工数} | ${r.放款金额万} | ${r.逾期率} | ${r.MOB} |\n`;
    }
    md += `\n加权平均终损率：**${p.weightedOvr.toFixed(2)}%**\n\n`;
  }

  md += `### 预测结果汇总\n\n`;
  md += `| 套餐类型 | 加权终损率 | 近1年放款(万) | 预测终损(万) |\n|:--------:|:---------:|:-------------:|:-------------:|\n`;
  md += `| 单卡 | ${predictions['单卡'].weightedOvr.toFixed(2)}% | ${predictions['单卡'].totalAmtRecent.toFixed(2)} | ${predictions['单卡'].predLoss.toFixed(2)} |\n`;
  md += `| 融合套餐 | ${predictions['融合套餐'].weightedOvr.toFixed(2)}% | ${predictions['融合套餐'].totalAmtRecent.toFixed(2)} | ${predictions['融合套餐'].predLoss.toFixed(2)} |\n`;
  md += `| **合计** | - | **${totalAmt.toFixed(2)}** | **${totalLoss.toFixed(2)}** |\n`;

  const mdPath = '/mnt/d/desktop/湖南公众用户_融合vs单卡分析报告.md';
  fs.writeFileSync(mdPath, md, 'utf-8');
  console.log(`\n✅ Markdown: ${mdPath}`);

  // =============================
  // 5. 生成 Excel
  // =============================
  const wb = XLSX.utils.book_new();

  // Sheet1: 总览
  const s1 = [
    ['套餐类型', '申请量', '通过数', '通过率(%)', '竣工数', '逾期数', '逾期率(%)', '放款金额(万元)'],
    ['单卡', pass[0].申请量, pass[0].通过数, pass[0].通过率, overdue[0].竣工数, overdue[0].逾期数, overdue[0].逾期率, overdue[0].放款金额万],
    ['融合套餐', pass[1].申请量, pass[1].通过数, pass[1].通过率, overdue[1].竣工数, overdue[1].逾期数, overdue[1].逾期率, overdue[1].放款金额万],
  ];
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(s1), '总览');

  // Sheet2: 月度通过率
  const s2 = [['月份', '单卡-申请', '单卡-通过', '单卡-通过率(%)', '融合-申请', '融合-通过', '融合-通过率(%)']];
  for (const m of Object.keys(mpMap).sort()) {
    const d = mpMap[m]['单卡'], r = mpMap[m]['融合套餐'];
    if (!d || !r) continue;
    s2.push([m, d.申请量, d.通过数, d.通过率, r.申请量, r.通过数, r.通过率]);
  }
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(s2), '月度通过率');

  // Sheet3: 月度逾期率
  const s3 = [['月份', '单卡-竣工', '单卡-逾期', '单卡-逾期率(%)', '融合-竣工', '融合-逾期', '融合-逾期率(%)']];
  for (const m of Object.keys(moMap).sort()) {
    const d = moMap[m]['单卡'], r = moMap[m]['融合套餐'];
    if (!d || !r) continue;
    s3.push([m, d.竣工数, d.逾期数, d.逾期率, r.竣工数, r.逾期数, r.逾期率]);
  }
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(s3), '月度逾期率');

  // Sheet4: Vintage
  const s4 = [['套餐类型', '批次月份', '竣工数', '放款金额(万)', '逾期数', '应还数', '逾期率(%)', 'MOB']];
  for (const ptype of ['单卡', '融合套餐']) {
    for (const r of vintages[ptype]) {
      s4.push([ptype, r.月份, r.竣工数, r.放款金额万, r.逾期数, r.应还数, r.逾期率, r.MOB]);
    }
  }
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(s4), 'Vintage');

  // Sheet5: 终损预测
  const s5 = [['套餐类型', '成熟批数', '加权终损率(%)', '成熟批放款(万)', '近1年放款(万)', '预测终损(万)']];
  for (const ptype of ['单卡', '融合套餐']) {
    const p = predictions[ptype];
    s5.push([ptype, p.matureCount, p.weightedOvr.toFixed(2), p.totalAmtMature.toFixed(2), p.totalAmtRecent.toFixed(2), p.predLoss.toFixed(2)]);
  }
  s5.push(['合计', '', '', '', totalAmt.toFixed(2), totalLoss.toFixed(2)]);
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(s5), '终损预测');

  // Sheet6: 成熟批次明细
  const s6 = [['套餐类型', '批次', '竣工数', '放款(万)', '逾期率(%)', 'MOB']];
  for (const ptype of ['单卡', '融合套餐']) {
    for (const r of predictions[ptype].matureBatches) {
      s6.push([ptype, r.月份, r.竣工数, r.放款金额万, r.逾期率, `${r.MOB}+`]);
    }
  }
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(s6), '成熟批次');

  const xlsxPath = '/mnt/d/desktop/湖南公众用户_融合vs单卡分析.xlsx';
  XLSX.writeFile(wb, xlsxPath);
  console.log(`✅ Excel: ${xlsxPath}`);

  await conn.end();
  console.log('\n===== DONE =====');
}
main().catch(e => { console.error(e); process.exit(1); });
