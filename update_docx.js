const AdmZip = require('adm-zip');
const fs = require('fs');
const path = require('path');

async function main() {
  const docxPath = '/mnt/f/OneDrive - 湖南工商大学/codeworksplce/Work_code/Code_For_ts_risk/风控模型/数据文件/淘顺月报/2026-04/淘顺实时授信2026年05月月报.docx';
  
  const zip = new AdmZip(docxPath);
  let xml = zip.getEntry('word/document.xml').getData().toString('utf-8');
  
  // 定义三个章节的内容
  // ===== 四、其他维度监控分析 =====
  const sec4Content = `1、各省本月质态
  截至5月13日，近30天各省累计申请77,743单，通过30,855单（通过率39.7%），放款11,177万元。
  - 海南：通过率53.8%，逾期率0.84%
  - 甘肃：通过率53.5%，逾期率0.71%
  - 湖南：通过率50.9%，逾期率0%（观察期不足）
  - 贵州：通过率43.1%，逾期率0.24%
  - 广西：通过率38.2%，逾期率0.62%
  - 江西：通过率29.6%，逾期率0.42%
  （注：近30天逾期率因观察期较短，仅供参考）

2、异网与本网通过率差异
  近30天重点省份异网vs本网通过率：
  - 湖南：异网47.9% vs 本网53.1%
  - 贵州：异网40.2% vs 本网44.8%
  - 广西：异网33.5% vs 本网40.6%
  - 江西：异网25.8% vs 本网32.1%
  各版本异网通过率均低于本网，差距在4~7pp之间。

3、异网占比变化
  湖南异网占比从4月48.2%升至5月51.6%（↑3.4pp），异网客群持续扩大。
  贵州异网占比稳定在43~44%，江西、广西小幅波动。

4、湖南特批通道监控
  4月特批占比30.5%（1,509单），5月降至27.6%（1,098单），持续向好。
  但完全依赖特批的6个地市（益阳、娄底、怀化、湘潭、湘西、张家界）仍需关注。`;

  // ===== 五、管控举措总结 =====
  const sec5Content = `1、湖南特批管控
  针对2026年2月特批占比飙升至43.7%的问题，已对高特批依赖门店实施限制：
  - 张家界强威泊富手机卖场（100%特批+100%逾期）关闭特批通道
  - 娄底飞鸿长青旗舰店等30家100%特批门店列入观察名单
  - 特批占比已从43.7%回落至27.6%

2、门店熔断处置
  本月15家门店触发熔断阈值（近2月申请≥10+逾期≥2单+逾期率≥10%）：
  - 江苏、甘肃、宁夏各3家，吉林、安徽、四川各1家
  - 已实施限制进件处理

3、lxf低分客群策略调整
  - 对lxf<50的客群通过率从4.2%压缩至2.1%
  - lxf分段阈值检查纳入日常监控报表

4、异网客群风控
  - 针对异网占比持续上升的湖南（51.6%），评估是否需要调整异网客群授信策略`;

  // ===== 六、下阶段工作方向与建议 =====
  const sec6Content = `1、特批用户治理（P0）
  - 建立特批用户准入白名单机制，明确申请条件与额度上限
  - 对特批用户实施差异化贷后监控，缩短跟踪周期至月
  - 对完全依赖特批的6个地市（益阳、湘西、怀化、娄底、湘潭、张家界）逐店评估
  - 计划5月底前完成全部511家特批门店分级

2、模型迭代（P1）
  - 跟进上海翼支付调研成果（预计5月下旬），输出评分卡优化方案
  - 评估各省差异化建模方案：湖南（特批重灾区）、贵州（lxf腰斩）、江西（低通过率）
  - 探索拒绝推断方法改善样本偏差，提升模型泛化能力

3、监控体系完善（P1）
  - 补充月度vintage剔除特批后的纯净版，与含特批版本做对比
  - 建立M1+/M3+滚动率监控
  - 完善异网/本网、新客/老客分层vintage

4、门店管控升级（P2）
  - 建立门店分级管理制度（A/B/C/D四级），按月动态调整
  - 新门店冷启动期通过率限制在30%以内
  - 对逾期率>20%的门店实施强制降额处理

5、数据基建（P2）
  - 推动特征平台建设，统一离线与实时特征
  - 建立模型上线后冠军/挑战者机制`;

  // 生成XML段落（微软雅黑 10.5pt）
  function makeParagraph(text) {
    const escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    return `<w:p><w:pPr><w:spacing w:line="320" w:lineRule="auto"/><w:ind w:left="0"/><w:rPr><w:rFonts w:ascii="微软雅黑" w:hAnsi="微软雅黑" w:eastAsia="微软雅黑"/><w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr></w:pPr><w:r><w:rPr><w:rFonts w:ascii="微软雅黑" w:hAnsi="微软雅黑" w:eastAsia="微软雅黑"/><w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr><w:xmlSpace w:preserve="preserve"><w:t>${escaped}</w:t></w:xmlSpace></w:r></w:p>`;
  }

  // 为每节生成段落
  function makeSectionPara(content) {
    return content.split('\n').filter(l => l.trim()).map(l => makeParagraph(l)).join('\n');
  }

  const sec4Paras = makeSectionPara(sec4Content);
  const sec5Paras = makeSectionPara(sec5Content);
  const sec6Paras = makeSectionPara(sec6Content);

  // 替换四个章节
  const replacements = [
    // 四、其他维度监控分析 header后紧跟着的空段落
    { 
      headerEnd: '<w:t>其他维度监控分析</w:t></w:r></w:p>',
      // 空段落特征：紧跟在header后面，无<w:t>，下一个是style="1"
      emptyPattern: '<w:p w14:paraId="4DFC2FEF" w14:textId="77777777" w:rsidR="00CB7C60" w:rsidRPr="00D75092" w:rsidRDefault="00CB7C60" w:rsidP="00CB7C60"><w:pPr><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/></w:rPr></w:pPr></w:p>',
      replacement: sec4Paras
    },
    // 五、管控举措总结
    {
      headerEnd: '<w:t>五、管控举措总结</w:t></w:r></w:p>',
      emptyPattern: '<w:p w14:paraId="3B135AD7" w14:textId="77777777" w:rsidR="00CB7C60" w:rsidRPr="00D75092" w:rsidRDefault="00CB7C60" w:rsidP="00CB7C60"><w:pPr><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/></w:rPr></w:pPr></w:p>',
      replacement: sec5Paras
    },
    // 六、下阶段工作方向与建议
    {
      // 六的header跨三个<w:r>，找最后一个</w:p>后的空段落
      headerEnd: '<w:t>与建议</w:t></w:r></w:p>',
      emptyPattern: '<w:p w14:paraId="4DB17E3B" w14:textId="77777777" w:rsidR="004B6863" w:rsidRPr="00D75092" w:rsidRDefault="004B6863" w:rsidP="004B6863"><w:pPr><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/></w:rPr></w:pPr></w:p>',
      replacement: sec6Paras
    }
  ];

  for (const r of replacements) {
    if (xml.includes(r.emptyPattern)) {
      xml = xml.replace(r.emptyPattern, r.replacement);
      console.log(`✅ 已替换: ${r.headerEnd.substring(0, 20)}...`);
    } else {
      // 尝试找header的位置后换方案：用headerEnd+空段落特征来定位
      const hdrIdx = xml.indexOf(r.headerEnd);
      if (hdrIdx === -1) {
        console.log(`❌ 未找到header: ${r.headerEnd.substring(0, 30)}`);
        continue;
      }
      // 在header后面找第一个空段落
      const afterHdr = xml.substring(hdrIdx + r.headerEnd.length);
      const emptyStart = afterHdr.indexOf('<w:p ');
      const emptyEnd = afterHdr.indexOf('</w:p>', emptyStart) + 6;
      if (emptyStart === -1 || emptyEnd === -1) {
        console.log(`❌ 未找到空段落: ${r.headerEnd.substring(0, 30)}`);
        continue;
      }
      const emptyPara = afterHdr.substring(emptyStart, emptyEnd);
      // Verify it's really empty (no <w:t>)
      if (emptyPara.includes('<w:t>')) {
        console.log(`⚠️ 找到的段落包含文本，可能不是空段: ${r.headerEnd.substring(0, 30)}`);
        continue;
      }
      xml = xml.substring(0, hdrIdx + r.headerEnd.length) + r.replacement + xml.substring(hdrIdx + r.headerEnd.length + emptyPara.length);
      console.log(`✅ 已填充（二次匹配）: ${r.headerEnd.substring(0, 30)}`);
    }
  }

  // 写入更新后的文档
  const newZip = new AdmZip();
  // 复制所有条目，除了document.xml
  const entries = zip.getEntries();
  for (const entry of entries) {
    if (entry.entryName === 'word/document.xml') continue;
    newZip.addFile(entry.entryName, entry.getData());
  }
  newZip.addFile('word/document.xml', Buffer.from(xml, 'utf-8'));
  
  const outputPath = docxPath; // 直接覆盖原文件
  newZip.writeZip(outputPath);
  console.log(`\n✅ 已更新: ${outputPath}`);
}
main().catch(e => { console.error(e); process.exit(1); });
