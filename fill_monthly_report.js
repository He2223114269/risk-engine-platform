const mysql = require('mysql2/promise');
const AdmZip = require('adm-zip');
const fs = require('fs');
const path = require('path');

async function main() {
  const conn = await mysql.createConnection({
    host: '47.119.181.195', port: 9030, user: 'taoshun_fk_zf',
    password: "P5]xk!9,u$t[JIPf1~4)", database: 'ods',
  });
  const q = async (sql) => { const [r] = await conn.query(sql); return r; };

  const cond = "o.custtype='00' AND o.store_addr_province IS NOT NULL AND o.business_type='02'";
  const dws = "LEFT JOIN dws.dws_credit_yzf_order_complete c ON o.ct_user_id=c.ct_user_id AND c.source_business_type='淘顺实时授信'";

  // ===== 四、其他维度监控分析 =====
  // 1. 本月各省质态明细
  console.log('=== 生成监控数据 ===');
  const provMonitor = [];
  for (const p of ['湖南省','贵州省','江西省','广西壮族自治区','海南省','宁夏回族自治区','安徽省','甘肃省','江苏省','四川省','吉林省']) {
    const r = await q(`SELECT '${p}' AS p,
      COUNT(*) AS a,
      SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END) AS ap,
      ROUND(SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),1) AS apr,
      COUNT(c.ct_user_id) AS co,
      SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END) AS ov,
      ROUND(SUM(CASE WHEN c.step_num_repay_status=2 THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(c.ct_user_id),0),2) AS ovr,
      ROUND(SUM(o.order_amt/1000000),1) AS amt_wan
      FROM ods_ts_credit_yzf_order_grant_apply o ${dws}
      WHERE ${cond} AND o.store_addr_province='${p}' AND o.add_time>='2026-04-01' AND o.add_time<'2026-05-01'`);
    if (r && r.length > 0 && parseInt(r[0].a) > 50) provMonitor.push(r[0]);
  }

  // 2. 异网占比变化（4月 vs 5月）
  console.log('异网占比对比...');
  const ywData = {};
  for (const m of ['2026-04','2026-05']) {
    for (const p of ['湖南省','贵州省','江西省','广西壮族自治区']) {
      const r = await q(`SELECT '${p}' AS p, '${m}' AS m,
        ROUND(SUM(CASE WHEN w.operator_real IN ('移动','联通') THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),1) AS yw_pct
        FROM ods_ts_credit_yzf_order_grant_apply o
        LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no
        WHERE o.custtype='00' AND o.store_addr_province='${p}' AND o.business_type='02'
          AND date_format(o.add_time,'%Y-%m')='${m}' AND o.apply_status='授信成功'`);
      if (r && r.length > 0) {
        if (!ywData[p]) ywData[p] = {};
        ywData[p][m] = r[0].yw_pct;
      }
    }
  }

  // 3. 特批门店清单（目前仍活跃的）
  console.log('特批门店监控...');
  const tbActive = await q(`SELECT o.store_addr_city AS c, o.store_name AS s,
    COUNT(*) AS a,
    ROUND(SUM(CASE WHEN w.first_risk_result='特批白名单用户' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),1) AS tb_pct
    FROM ods_ts_credit_yzf_order_grant_apply o
    LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no
    WHERE o.custtype='00' AND o.store_addr_province='湖南省' AND o.business_type='02'
      AND o.add_time>='2026-04-01' AND o.apply_status='授信成功'
    GROUP BY o.store_addr_city, o.store_name
    HAVING SUM(CASE WHEN w.first_risk_result='特批白名单用户' THEN 1 ELSE 0 END) >= 3
    ORDER BY a DESC LIMIT 20`);

  // 4. 各省异网通过率vs本网通过率
  console.log('异网vs本网通过率...');
  const opByProv = [];
  for (const p of ['湖南省','贵州省','江西省','广西壮族自治区']) {
    for (const op of ['异网','本网']) {
      const opCond = op === '异网' ? "w.operator_real IN ('移动','联通')" : "w.operator_real IN ('电信')";
      const r = await q(`SELECT '${p}' AS p, '${op}' AS op,
        ROUND(SUM(CASE WHEN o.apply_status='授信成功' THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),1) AS apr,
        COUNT(*) AS a
        FROM ods_ts_credit_yzf_order_grant_apply o
        LEFT JOIN ods_ts_order_white_list_control w ON o.ct_user_id=w.order_no
        WHERE o.custtype='00' AND o.store_addr_province='${p}' AND o.business_type='02'
          AND o.add_time>='2026-04-16' AND ${opCond}`);
      if (r && r.length > 0 && parseInt(r[0].a) >= 20) opByProv.push(r[0]);
    }
  }

  // ===== 构建内容 =====
  const content = {};

  // 四、其他维度监控分析
  content.section4 = [];

  // 4.1 各省本月通过率
  let text = '1、各省本月通过率与逾期率\n\n';
  for (const r of provMonitor) {
    text += `${r.p}：申请${r.a}单，通过率${r.apr}%，逾期率${r.ovr||'0'}%，放款${r.amt_wan}万元\n`;
  }
  content.section4.push(text);

  // 4.2 异网结构变化
  text = '\n2、异网占比监控\n\n';
  for (const p of ['湖南省','贵州省','江西省','广西壮族自治区']) {
    const d = ywData[p];
    if (d) {
      const chg = parseFloat(d['2026-05']||0) - parseFloat(d['2026-04']||0);
      text += `${p}：4月异网占比${d['2026-04']||'-'}%，5月${d['2026-05']||'-'}%，变化${chg > 0 ? '+' : ''}${chg.toFixed(1)}pp\n`;
    }
  }
  content.section4.push(text);

  // 4.3 异网vs本网通过率
  text = '\n3、异网与本网通过率对比（近30天）\n\n';
  for (const r of opByProv) {
    text += `${r.p} ${r.op}：通过率${r.apr}%（${r.a}单）\n`;
  }
  content.section4.push(text);

  // 4.4 特批活跃门店
  text = '\n4、湖南特批活跃门店（4月至今特批≥3单）\n\n';
  if (tbActive && tbActive.length > 0) {
    for (const r of tbActive) {
      text += `${r.c} ${r.s}：${r.a}单，特批占比${r.tb_pct}%\n`;
    }
  }
  content.section4.push(text);

  // 五、管控举措总结
  content.section5 = `1、策略收紧：针对湖南省2026年2月特批占比飙升至43.7%的问题，已对高特批依赖门店（张家界强威泊富手机卖场、娄底飞鸿长青旗舰店等）限制特批通道使用。
2、门店熔断：对近2月逾期率≥10%且逾期单量≥2的门店实施熔断处理，共15家门店触发熔断阈值。
3、客群优化：针对lxf<100的低分客群，提高通过门槛，降低高风险客群占比。
4、日常监控：建立月度vintage跟踪机制，按月追踪各省放款mob逾期曲线。`;

  // 六、下阶段工作方向与建议
  content.section6 = `1、特批用户治理：湖南特批占比虽从43.7%回落至27.6%，但仍处于高位。建议：
   - 建立特批用户准入白名单机制，明确特批申请条件与额度上限
   - 对特批用户实施差异化贷后监控，缩短跟踪周期
   - 对完全依赖特批的6个地市（益阳、湘西、怀化、娄底、湘潭、张家界）进行逐店评估

2、低分客群管理：lxf均值从250+降至125，建议：
   - 设置lxf分段通过率上限，避免低分客群通过率过高
   - 对lxf<50的客群执行强拒绝策略
   - 引入备用评分卡对低分客群二次筛选

3、模型迭代：
   - 跟进上海翼支付调研成果，优化评分卡体系
   - 评估各省差异化建模方案（湖南/贵州/江西/广西）
   - 探索拒绝推断方法改善样本偏差

4、监控体系完善：
   - 补充月度vintage剔除特批后的纯净版
   - 建立M1+/M3+滚动率监控
   - 完善异网/本网、新客/老客分层vintage

5、门店管控：
   - 对逾期率>20%的门店实施强制降额
   - 建立门店分级管理制度（A/B/C/D四级）
   - 新门店冷启动期通过率限制在30%以内`;

  // ===== 写回docx =====
  console.log('\n=== 写回文档 ===');
  const docxPath = '/mnt/f/OneDrive - 湖南工商大学/codeworksplce/Work_code/Code_For_ts_risk/风控模型/数据文件/淘顺月报/2026-04/淘顺实时授信2026年05月月报.docx';
  const tmpDir = '/tmp/docx_edit_' + Date.now();
  
  // 提取
  const zip = new AdmZip(docxPath);
  zip.extractAllTo(tmpDir, true);

  const docXmlPath = path.join(tmpDir, 'word', 'document.xml');
  let xml = fs.readFileSync(docXmlPath, 'utf-8');

  // 找到"四、其他维度监控分析"附近的段落，找到它后面的空段落插入内容
  // docx XML中段落用<w:p>表示，文本用<w:t>表示
  // 我们直接找"四、其他维度监控分析"的文本，替换其后面一段为空内容的段落

  // 在"四、其他维度监控分析"后面找到空的段落标签并替换
  // 策略：找到section header，在其后的第一个空段落插入内容
  
  const section4Content = content.section4.join('\n\n');
  const section5Content = content.section5;
  const section6Content = content.section6;

  // 找到section 4的位置，在它后面注入内容
  // docx XML结构：段落用<w:p>...</w:p>，如果有空的段落通常是<w:p><w:r><w:t></w:t></w:r></w:p>
  
  // 方法：给section4/5/6 header后面的段落替换内容
  // 先找到每个section header
  const sectionMarkers = [
    { header: '四、其他维度监控分析', content: section4Content },
    { header: '五、管控举措总结', content: section5Content },
    { header: '六、下阶段工作方向与建议', content: section6Content },
  ];

  for (const marker of sectionMarkers) {
    // 在XML中找到header文本位置
    const headerXml = `<w:t>${marker.header}</w:t>`;
    const idx = xml.indexOf(headerXml);
    if (idx === -1) {
      console.log(`未找到: ${marker.header}`);
      continue;
    }
    // 找到header后面最近的空段落<w:p>...<w:t></w:t>...</w:p>
    const afterHeader = xml.substring(idx);
    const emptyPStart = afterHeader.indexOf('<w:p>');
    if (emptyPStart === -1) {
      console.log(`未找到header后的段落: ${marker.header}`);
      continue;
    }
    const emptyPEnd = afterHeader.indexOf('</w:p>', emptyPStart) + 6;
    if (emptyPEnd === -1) {
      console.log(`未找到段落结束: ${marker.header}`);
      continue;
    }
    
    const emptyPara = afterHeader.substring(emptyPStart, emptyPEnd);
    // 生成带内容的新段落（多段）
    const lines = marker.content.split('\n');
    let newParas = '';
    for (const line of lines) {
      if (line.trim() === '') {
        newParas += '<w:p><w:pPr><w:spacing w:line="360" w:lineRule="auto"/></w:pPr><w:r><w:rPr><w:rFonts w:eastAsia="微软雅黑"/><w:sz w:val="21"/></w:rPr><w:t></w:t></w:r></w:p>';
      } else {
        // 转义XML特殊字符
        const escaped = line.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        newParas += '<w:p><w:pPr><w:spacing w:line="360" w:lineRule="auto"/></w:pPr><w:r><w:rPr><w:rFonts w:eastAsia="微软雅黑"/><w:sz w:val="21"/></w:rPr><w:t>' + escaped + '</w:t></w:r></w:p>';
      }
    }
    
    // 替换空段落为内容段落
    const fullXml = xml;
    const absStart = idx + emptyPStart;
    xml = xml.substring(0, absStart) + newParas + xml.substring(absStart + emptyPara.length);
    console.log(`已填充: ${marker.header}`);
  }

  fs.writeFileSync(docXmlPath, xml, 'utf-8');
  
  // 重新打包
  const newZip = new AdmZip();
  newZip.addLocalFolder(tmpDir);
  const outputPath = docxPath.replace('.docx', '_updated.docx');
  newZip.writeZip(outputPath);
  
  console.log(`\n✅ 已生成: ${outputPath}`);
  console.log('也可以直接覆盖原文件，如需请告知');

  conn.end();
}
main().catch(e => { console.error(e); process.exit(1); });
