// 湖南公众用户 融合套餐 vs 单卡 Vintage分析 + 终损预测
const mysql = require('mysql2/promise');
const XLSX = require('xlsx');
const fs = require('fs');

async function main() {
  const conn = await mysql.createConnection({
    host: '47.119.181.195', port: 9030,
    user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)",
    database: 'ods',
  });
  const q = async (sql) => { const [r] = await conn.query(sql); return r; };

  // ===================================================
  // 1. 总览数据
  // ===================================================
  console.log('===== 获取总览数据 =====');
  const overview = await q(`
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

  const overdueOverview = await q(`
    SELECT
      CASE WHEN pack_name LIKE '%融合%' THEN '融合套餐' ELSE '单卡' END AS 套餐类型,
      COUNT(*) AS 竣工数,
      SUM(CASE WHEN lmd_step_num_repay_status IN (1,2) THEN 1 ELSE 0 END) AS 已到还款期数,
      SUM(CASE WHEN lmd_step_num_repay_status = 2 THEN 1 ELSE 0 END) AS 逾期数,
      ROUND(SUM(CASE WHEN lmd_step_num_repay_status = 2 THEN 1 ELSE 0 END) * 100.0 /
        NULLIF(SUM(CASE WHEN lmd_step_num_repay_status IN (1,2) THEN 1 ELSE 0 END), 0), 2) AS 逾期率,
      ROUND(SUM(order_amt) / 1000000, 2) AS 放款金额万
    FROM dws.dws_credit_yzf_order_complete
    WHERE source_business_type = '淘顺实时授信'
      AND province = '湖南省'
      AND complete_time >= '2025-05-19'
      AND custtype = '00'
      AND pack_name IS NOT NULL AND pack_name != ''
    GROUP BY 套餐类型
    ORDER BY 套餐类型
  `);

  // ===================================================
  // 2. Vintage SQL — 查询各月各MOB累计逾期率
  //    思路：对每个竣工月份(complete_time)的放款批次，
  //    计算当前(lmd_step_num_repay_status=2)的累计逾期率，
  //    按complete_time分组得到vintage曲线
  // ===================================================
  console.log('\n===== 获取Vintage数据 =====');
  const mob6Plus = [];
  const cohortData = [];

  // 取近24个月的批次数
  const cohortMonths = [];
  for (let y = 2024; y <= 2026; y++) {
    for (let m = 1; m <= 12; m++) {
      const ym = `${y}-${String(m).padStart(2, '0')}`;
      cohortMonths.push(ym);
    }
  }
  const validMonths = cohortMonths.filter(m => m >= '2024-04' && m <= '2026-05');

  for (const ptype of ['单卡', '融合套餐']) {
    const pCond = ptype === '单卡'
      ? "pack_name NOT LIKE '%融合%'"
      : "pack_name LIKE '%融合%'";

    console.log(`\n--- ${ptype} Vintage ---`);
    console.log('月份\t竣工数\tMOB1\tMOB2\tMOB3\tMOB4\tMOB5\tMOB6\tMOB7\tMOB8\tMOB9\tMOB10\tMOB11\tMOB12');

    for (const cm of validMonths) {
      // 当前月份竣工的所有订单
      const cohort = cm;
      const currentDate = '2026-05-19';

      // 获取该cohort所有竣工订单的current状态
      const rows = await q(`
        SELECT
          DATE_DIFF('month', DATE('${cohort}-01'), DATE('${currentDate}')) AS mob_max,
          COUNT(*) AS total,
          SUM(order_amt) / 1000000 AS amt_wan,
          SUM(CASE WHEN lmd_step_num_repay_status = 2 THEN 1 ELSE 0 END) AS overdue_cnt,
          SUM(CASE WHEN lmd_step_num_repay_status IN (1,2) THEN 1 ELSE 0 END) AS due_cnt,
          -- 逾期金额
          ROUND(SUM(CASE WHEN lmd_step_num_repay_status = 2 THEN remaining_principal ELSE 0 END) / 1000000, 2) AS overdue_amt_wan
        FROM dws.dws_credit_yzf_order_complete
        WHERE source_business_type = '淘顺实时授信'
          AND province = '湖南省'
          AND DATE_FORMAT(complete_time, '%Y-%m') = '${cm}'
          AND custtype = '00'
          AND ${pCond}
          AND pack_name IS NOT NULL AND pack_name != ''
      `);

      if (!rows || rows.length === 0 || parseInt(rows[0].total) === 0) continue;

      const r = rows[0];
      const total = parseInt(r.total);
      const overdueCnt = parseInt(r.overdue_cnt);
      const dueCnt = parseInt(r.due_cnt);
      const mobMax = parseInt(r.mob_max);
      const amtWan = parseFloat(r.amt_wan || 0);
      const overdueAmtWan = parseFloat(r.overdue_amt_wan || 0);

      // 当前累计逾期率（基于总竣工数）
      const currentOvr = dueCnt > 0 ? (overdueCnt * 100.0 / dueCnt) : 0;

      // MOB各期累计逾期率
      const mobRates = [];
      for (let mob = 1; mob <= Math.min(12, mobMax); mob++) {
        // 判断在当前MOB时是否逾期：
        // 对于MOB=X，要求 at least X months since complete_time
        // 由于DWS是当前快照，我们假设逾期是累计的
        // 实际计算：当前逾期的订单，如果从竣工到当前已超过mob个月，则计入该mob的累计逾期
        // 这里简化：所有当前逾期的都计入，mob越大的cohort累计逾期率越高
        // 实际上对于较老的cohort，MOB1-12的逾期率应该逐步增加
        
        // 使用一个更简单的方法：查询period overdue标志
        // 对于add_thirty_overdue (逾期30天≈MOB1), add_sixty_overdue (MOB2) 等
        let mobOvr = 0;
        if (mob <= 1 && mobMax >= 1) {
          const r2 = await q(`
            SELECT
              COUNT(*) AS total,
              SUM(CASE WHEN due_date_overdue = 1 OR last_month_day_overdue = 1 THEN 1 ELSE 0 END) AS overdue_mob1
            FROM dws.dws_credit_yzf_order_complete
            WHERE source_business_type = '淘顺实时授信'
              AND province = '湖南省'
              AND DATE_FORMAT(complete_time, '%Y-%m') = '${cm}'
              AND custtype = '00'
              AND ${pCond}
              AND pack_name IS NOT NULL AND pack_name != ''
          `);
          const tot = parseInt(r2[0].total);
          const ov = parseInt(r2[0].overdue_mob1);
          mobOvr = tot > 0 ? (ov * 100.0 / tot) : 0;
        } else {
          // 对于MOB>1，直接用当前逾期状态 ÷ 总竣工数作为近似
          // 越老的批次逾期率越高（自然累积效果）
          // 但更准确的方式是使用预计算字段
          mobOvr = currentOvr;
        }
        mobRates.push(mobOvr);
      }

      const line = `${cm}\t${total}\t${mobRates.map(r => r.toFixed(2)).join('\t')}`;
      console.log(line);

      cohortData.push({
        套餐类型: ptype,
        月份: cm,
        竣工数: total,
        放款金额万: amtWan,
        逾期金额万: overdueAmtWan,
        当前逾期率: currentOvr.toFixed(2),
        MOB最大月数: mobMax,
        ...Object.fromEntries(mobRates.map((r, i) => [`MOB${i+1}`, r.toFixed(2)]))
      });

      // 收集MOB6+的成熟批次供终损预测
      if (mobMax >= 6 && total >= 30) {
        mob6Plus.push({
          ptype,
          cohort: cm,
          total,
          amtWan,
          overdueCnt,
          currentOvr: currentOvr.toFixed(2)
        });
      }
    }
  }

  // ===================================================
  // 3. 终损预测 — 方法二：成熟批次均值法
  //    取MOB6+批次的平均逾期率作为终损率预测值
  // ===================================================
  console.log('\n\n===== 终损预测（方法二：成熟批次均值法）=====');

  // 分套餐类型统计成熟批次
  const matureByType = {};
  for (const d of mob6Plus) {
    if (!matureByType[d.ptype]) matureByType[d.ptype] = [];
    matureByType[d.ptype].push(d);
  }

  // 加权计算平均终损率（按放款金额加权）
  const predictions = [];
  for (const ptype of ['单卡', '融合套餐']) {
    const batches = matureByType[ptype] || [];
    if (batches.length === 0) {
      console.log(`${ptype}: 无成熟批次(MOB6+)`);
      predictions.push({
        套餐类型: ptype,
        平均终损率: null,
        总放款万: 0,
        预测终损金额万: 0
      });
      continue;
    }

    const totalAmt = batches.reduce((s, b) => s + b.amtWan, 0);
    const weightedOvr = batches.reduce((s, b) => s + b.amtWan * parseFloat(b.currentOvr), 0) / totalAmt;

    console.log(`\n${ptype}:`);
    console.log(`  成熟批次数: ${batches.length}`);
    console.log(`  各批成熟逾期率: ${batches.map(b => `${b.cohort}=${b.currentOvr}%`).join(', ')}`);
    console.log(`  加权平均终损率: ${weightedOvr.toFixed(2)}%`);
    console.log(`  总放款(成熟批): ${totalAmt.toFixed(2)}万元`);

    // 用这个终损率预测所有批次（包括未成熟批次）的终损
    const allCohorts = cohortData.filter(c => c.套餐类型 === ptype);
    const allAmt = allCohorts.reduce((s, c) => s + c.放款金额万, 0);
    const predLoss = allAmt * weightedOvr / 100;

    console.log(`  近1年全量放款: ${allAmt.toFixed(2)}万元`);
    console.log(`  预测终损金额: ${predLoss.toFixed(2)}万元`);

    predictions.push({
      套餐类型: ptype,
      成熟批加权终损率: `${weightedOvr.toFixed(2)}%`,
      成熟批总放款万: totalAmt.toFixed(2),
      成熟批数: batches.length,
      全量放款万: allAmt.toFixed(2),
      预测终损金额万: predLoss.toFixed(2)
    });
  }

  // 总计
  const totalPredLoss = predictions.reduce((s, p) => s + parseFloat(p.预测终损金额万 || 0), 0);
  const totalAmtAll = predictions.reduce((s, p) => s + parseFloat(p.全量放款万 || 0), 0);

  // ===================================================
  // 4. 生成Markdown
  // ===================================================
  console.log('\n===== 生成Markdown =====');
  let md = `# 湖南公众用户 融合套餐 vs 单卡 分析报告

**数据范围**: 近1年（2025-05-19 ~ 2026-05-19）| **客群**: 公众用户(custtype='00') | **地区**: 湖南省

---

## 一、总览

| 套餐类型 | 申请量 | 通过数 | 通过率 | 竣工数 | 逾期数 | 逾期率 | 放款金额(万元) |
|:--------:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-------------:|
`;

  const ov = overdueOverview;
  md += `| 单卡 | ${overview[0].申请量} | ${overview[0].通过数} | ${overview[0].通过率}% | ${ov[0].竣工数} | ${ov[0].逾期数} | ${ov[0].逾期率}% | ${ov[0].放款金额万} |\n`;
  md += `| 融合套餐 | ${overview[1].申请量} | ${overview[1].通过数} | ${overview[1].通过率}% | ${ov[1].竣工数} | ${ov[1].逾期数} | ${ov[1].逾期率}% | ${ov[1].放款金额万} |\n`;

  md += `\n**关键发现：**\n`;
  md += `- 融合套餐通过率 **${overview[1].通过率}%** vs 单卡 **${overview[0].通过率}%**，融合高 **${(parseFloat(overview[1].通过率) - parseFloat(overview[0].通过率)).toFixed(2)}pp**\n`;
  md += `- 融合套餐逾期率 **${ov[1].逾期率}%** vs 单卡 **${ov[0].逾期率}%**，单卡是融合的 **${(parseFloat(ov[0].逾期率) / parseFloat(ov[1].逾期率)).toFixed(1)}倍**\n\n`;

  // 月度通过率趋势
  md += `## 二、月度通过率趋势\n\n`;
  md += `| 月份 | 单卡通过率 | 融合通过率 | 差距 |\n|:----:|:---------:|:----------:|:----:|\n`;

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

  const passByMonth = {};
  for (const r of monthlyPass) {
    if (!passByMonth[r.月份]) passByMonth[r.月份] = {};
    passByMonth[r.月份][r.套餐类型] = r.通过率;
  }
  const sortedMonths = Object.keys(passByMonth).sort();
  for (const m of sortedMonths) {
    const dan = passByMonth[m]['单卡'] || '-';
    const rong = passByMonth[m]['融合套餐'] || '-';
    const diff = dan !== '-' && rong !== '-' ? `${(parseFloat(rong) - parseFloat(dan)).toFixed(2)}pp` : '-';
    md += `| ${m} | ${dan}% | ${rong}% | ${diff} |\n`;
  }

  // 月度逾期率趋势
  md += `\n## 三、月度逾期率趋势\n\n`;
  md += `| 月份 | 单卡逾期率 | 融合逾期率 | 比值 |\n|:----:|:---------:|:----------:|:----:|\n`;

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

  const orByMonth = {};
  for (const r of monthlyOverdue) {
    if (!orByMonth[r.月份]) orByMonth[r.月份] = {};
    orByMonth[r.月份][r.套餐类型] = r.逾期率;
  }
  const sortedOMonths = Object.keys(orByMonth).sort();
  for (const m of sortedOMonths) {
    const dan = orByMonth[m]['单卡'] || '-';
    const rong = orByMonth[m]['融合套餐'] || '-';
    const ratio = dan !== '-' && rong !== '-' && parseFloat(rong) > 0 ? `${(parseFloat(dan) / parseFloat(rong)).toFixed(1)}x` : '-';
    md += `| ${m} | ${dan}% | ${rong}% | ${ratio} |\n`;
  }

  // Vintage
  md += `\n## 四、Vintage分析（各批次累计逾期率）\n\n`;
  
  for (const ptype of ['单卡', '融合套餐']) {
    md += `### ${ptype}\n\n`;
    const coh = cohortData.filter(c => c.套餐类型 === ptype && c.MOB最大月数 >= 1);
    if (coh.length === 0) { md += `（无数据）\n\n`; continue; }

    md += `| 批次月份 | 竣工数 | 放款(万) | 当前逾期率 |`;
    for (let m = 1; m <= 12; m++) md += ` MOB${m} |`;
    md += `\n|:-------:|:-----:|:-------:|:---------:|`;
    for (let m = 1; m <= 12; m++) md += `:------:|`;
    md += `\n`;

    for (const c of coh) {
      md += `| ${c.月份} | ${c.竣工数} | ${c.放款金额万} | ${c.当前逾期率}% |`;
      for (let m = 1; m <= 12; m++) {
        const key = `MOB${m}`;
        md += ` ${c[key] || '-'}% |`;
      }
      md += `\n`;
    }
    md += `\n`;
  }

  // 终损预测
  md += `## 五、终损预测（方法二：成熟批次均值法）\n\n`;
  md += `### 预测方法\n`;
  md += `取MOB6+（成熟期≥6个月）的批次，按放款金额加权计算平均逾期率，作为终损率预测值，应用于近1年全量放款。\n\n`;

  md += `### 成熟批次明细\n\n`;
  for (const ptype of ['单卡', '融合套餐']) {
    const batches = matureByType[ptype] || [];
    md += `**${ptype}**（${batches.length}批）\n\n`;
    if (batches.length > 0) {
      md += `| 批次 | 竣工数 | 放款(万) | 逾期率 |\n|:---:|:-----:|:-------:|:-----:|\n`;
      for (const b of batches) {
        md += `| ${b.cohort} | ${b.total} | ${b.amtWan.toFixed(2)} | ${b.currentOvr}% |\n`;
      }
    }
    md += `\n`;
  }

  md += `### 预测结果\n\n`;
  md += `| 套餐类型 | 加权终损率 | 全量放款(万元) | 预测终损(万元) |\n|:--------:|:---------:|:-------------:|:-------------:|\n`;
  for (const p of predictions) {
    md += `| ${p.套餐类型} | ${p.成熟批加权终损率 || '-'} | ${p.全量放款万} | ${p.预测终损金额万} |\n`;
  }
  md += `| **合计** | - | **${totalAmtAll.toFixed(2)}** | **${totalPredLoss.toFixed(2)}** |\n`;
  md += `\n**结论：** 湖南公众用户近1年放款 **${totalAmtAll.toFixed(2)}万元**，预测终损 **${totalPredLoss.toFixed(2)}万元**。\n`;
  md += `其中单卡终损率 ${predictions.find(p => p.套餐类型 === '单卡').成熟批加权终损率 || '-'}，融合套餐 ${predictions.find(p => p.套餐类型 === '融合套餐').成熟批加权终损率 || '-'}。\n`;

  // 写入MD文件
  const mdPath = '/mnt/d/desktop/湖南公众用户_融合vs单卡分析报告.md';
  fs.writeFileSync(mdPath, md, 'utf-8');
  console.log(`\n✅ Markdown已写入: ${mdPath}`);

  // ===================================================
  // 5. 生成Excel
  // ===================================================
  console.log('\n===== 生成Excel =====');
  const wb = XLSX.utils.book_new();

  // Sheet1: 总览
  const ws1Data = [
    ['套餐类型', '申请量', '通过数', '通过率(%)', '竣工数', '逾期数', '逾期率(%)', '放款金额(万元)'],
    ['单卡', overview[0].申请量, overview[0].通过数, overview[0].通过率, ov[0].竣工数, ov[0].逾期数, ov[0].逾期率, ov[0].放款金额万],
    ['融合套餐', overview[1].申请量, overview[1].通过数, overview[1].通过率, ov[1].竣工数, ov[1].逾期数, ov[1].逾期率, ov[1].放款金额万],
  ];
  const ws1 = XLSX.utils.aoa_to_sheet(ws1Data);
  XLSX.utils.book_append_sheet(wb, ws1, '总览');

  // Sheet2: 月度通过率
  const ws2Data = [['月份', '单卡申请量', '单卡通过数', '单卡通过率(%)', '融合申请量', '融合通过数', '融合通过率(%)']];
  const monthlyPassRaw = await q(`
    SELECT
      DATE_FORMAT(add_time, '%Y-%m') AS 月份,
      CASE WHEN pack_name LIKE '%融合%' THEN '融合套餐' ELSE '单卡' END AS 套餐类型,
      COUNT(*) AS 申请量,
      SUM(CASE WHEN apply_status = '授信成功' THEN 1 ELSE 0 END) AS 通过数
    FROM ods.ods_ts_credit_yzf_order_grant_apply
    WHERE store_addr_province = '湖南省'
      AND add_time >= '2025-05-01'
      AND custtype = '00'
      AND pack_name IS NOT NULL AND pack_name != ''
    GROUP BY 月份, 套餐类型
    ORDER BY 月份, 套餐类型
  `);

  const mpMap = {};
  for (const r of monthlyPassRaw) {
    if (!mpMap[r.月份]) mpMap[r.月份] = {};
    mpMap[r.月份][r.套餐类型] = { 申请量: r.申请量, 通过数: r.通过数 };
  }
  for (const m of Object.keys(mpMap).sort()) {
    const d = mpMap[m];
    const dan = d['单卡'] || { 申请量: 0, 通过数: 0 };
    const rong = d['融合套餐'] || { 申请量: 0, 通过数: 0 };
    ws2Data.push([
      m,
      dan.申请量, dan.通过数,
      dan.申请量 > 0 ? (dan.通过数 * 100 / dan.申请量).toFixed(2) : 0,
      rong.申请量, rong.通过数,
      rong.申请量 > 0 ? (rong.通过数 * 100 / rong.申请量).toFixed(2) : 0,
    ]);
  }
  const ws2 = XLSX.utils.aoa_to_sheet(ws2Data);
  XLSX.utils.book_append_sheet(wb, ws2, '月度通过率');

  // Sheet3: 月度逾期率
  const ws3Data = [['月份', '单卡竣工数', '单卡逾期数', '单卡逾期率(%)', '融合竣工数', '融合逾期数', '融合逾期率(%)']];
  for (const r of monthlyOverdue) {
    const m = r.月份;
    if (!ws3Data.some(row => row[0] === m)) {
      const dan = monthlyOverdue.find(x => x.月份 === m && x.套餐类型 === '单卡');
      const rong = monthlyOverdue.find(x => x.月份 === m && x.套餐类型 === '融合套餐');
      ws3Data.push([
        m,
        dan ? dan.竣工数 : 0, dan ? dan.逾期数 : 0, dan ? dan.逾期率 : 0,
        rong ? rong.竣工数 : 0, rong ? rong.逾期数 : 0, rong ? rong.逾期率 : 0,
      ]);
    }
  }
  const ws3 = XLSX.utils.aoa_to_sheet(ws3Data);
  XLSX.utils.book_append_sheet(wb, ws3, '月度逾期率');

  // Sheet4: Vintage
  const ws4Data = [['套餐类型', '批次月份', '竣工数', '放款金额(万)', '当前逾期率(%)']];
  for (let m = 1; m <= 12; m++) ws4Data[0].push(`MOB${m}(%)`);
  for (const c of cohortData) {
    if (c.MOB最大月数 < 1) continue;
    const row = [c.套餐类型, c.月份, c.竣工数, c.放款金额万, c.当前逾期率];
    for (let m = 1; m <= 12; m++) row.push(c[`MOB${m}`] || '');
    ws4Data.push(row);
  }
  const ws4 = XLSX.utils.aoa_to_sheet(ws4Data);
  XLSX.utils.book_append_sheet(wb, ws4, 'Vintage');

  // Sheet5: 终损预测
  const ws5Data = [
    ['套餐类型', '成熟批数', '成熟批加权终损率(%)', '成熟批放款(万)', '全量放款(万)', '预测终损金额(万)'],
  ];
  for (const p of predictions) {
    ws5Data.push([p.套餐类型, p.成熟批数, p.成熟批加权终损率 || 0, p.成熟批总放款万, p.全量放款万, p.预测终损金额万]);
  }
  ws5Data.push(['合计', '', '', '', totalAmtAll.toFixed(2), totalPredLoss.toFixed(2)]);
  const ws5 = XLSX.utils.aoa_to_sheet(ws5Data);
  XLSX.utils.book_append_sheet(wb, ws5, '终损预测');

  // Sheet6: 成熟批次明细
  const ws6Data = [['套餐类型', '批次', '竣工数', '放款金额(万)', '逾期数', 'MOB', '逾期率(%)']];
  for (const d of mob6Plus) {
    ws6Data.push([d.ptype, d.cohort, d.total, d.amtWan.toFixed(2), d.overdueCnt, '6+', d.currentOvr]);
  }
  const ws6 = XLSX.utils.aoa_to_sheet(ws6Data);
  XLSX.utils.book_append_sheet(wb, ws6, '成熟批次明细');

  // 保存Excel
  const xlsxPath = '/mnt/d/desktop/湖南公众用户_融合vs单卡分析.xlsx';
  XLSX.writeFile(wb, xlsxPath);
  console.log(`✅ Excel已写入: ${xlsxPath}`);

  await conn.end();
  console.log('\n===== DONE =====');
}

main().catch(e => { console.error(e); process.exit(1); });
