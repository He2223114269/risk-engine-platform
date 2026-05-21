const fs = require('fs');

// Parse stores CSV
const storeLines = fs.readFileSync('/mnt/d/desktop/门店分析_门店数据.csv','utf8').split('\n').slice(1).filter(Boolean);
const stores = storeLines.map(l => {
  const c = l.split(',').map(x => x.replace(/^"(.*)"$/, '$1'));
  return { province: c[0], city: c[1], store: c[3], total: parseInt(c[6])||0, overdue: parseInt(c[7])||0, rate: parseFloat(c[8])||0, new_pct: parseFloat(c[13])||0, local_pct: parseFloat(c[15])||0 };
});

// Parse suppliers CSV
const suppLines = fs.readFileSync('/mnt/d/desktop/门店分析_代理商数据.csv','utf8').split('\n').slice(1).filter(Boolean);
const supps = suppLines.map(l => {
  const c = l.split(',').map(x => x.replace(/^"(.*)"$/, '$1'));
  return { name: c[1], stores: parseInt(c[2])||0, total: parseInt(c[3])||0, overdue: parseInt(c[4])||0, rate: parseFloat(c[5])||0, new_pct: parseFloat(c[7])||0, local_pct: parseFloat(c[9])||0 };
});

// Parse pass rate CSV
const passLines = fs.readFileSync('/mnt/d/desktop/门店分析_通过率.csv','utf8').split('\n').slice(1).filter(Boolean);
const passRates = passLines.map(l => {
  const c = l.split(',').map(x => x.replace(/^"(.*)"$/, '$1'));
  return { city: c[0], store: c[1], apply: parseInt(c[2])||0, pass: parseInt(c[3])||0, rate: parseFloat(c[4])||0, riskReject: parseInt(c[5])||0, otherReject: parseInt(c[6])||0 };
});

// Parse recent CSV
const recentLines = fs.readFileSync('/mnt/d/desktop/门店分析_近30天活跃.csv','utf8').split('\n').slice(1).filter(Boolean);
const recents = recentLines.map(l => {
  const c = l.split(',').map(x => x.replace(/^"(.*)"$/, '$1'));
  return { store: c[1], total: parseInt(c[2])||0, rate: parseFloat(c[4])||0, recent: parseInt(c[5])||0, recentOverdue: parseInt(c[6])||0, recentRate: parseFloat(c[7])||0 };
});

// ===== ANALYSIS =====
const lines = [];

lines.push('='.repeat(60));
lines.push('  淘顺实时授信 - 门店与代理商分析报告');
lines.push('  数据截止日期: 2026-04月底');
lines.push('='.repeat(60));
lines.push('');

// 1. 整体概览
lines.push('一、整体数据概览');
lines.push('-'.repeat(40));
const totalOrders = stores.reduce((s, x) => s + x.total, 0);
const totalOverdue = stores.reduce((s, x) => s + x.overdue, 0);
lines.push(`统计门店数: ${stores.length} 家（办单≥10）`);
lines.push(`统计代理商: ${supps.length} 家（办单≥50）`);
lines.push(`总办单量: ${(totalOrders/10000).toFixed(1)} 万笔`);
lines.push(`总逾期率: ${(totalOverdue/totalOrders*100).toFixed(2)}%`);
lines.push('');

// 2. 办单量Top10门店
lines.push('二、办单量Top10门店');
lines.push('-'.repeat(40));
stores.slice(0, 10).forEach((s, i) => {
  lines.push(`${i+1}. ${s.store} (${s.province}/${s.city})`);
  lines.push(`   办单: ${s.total} | 逾期率: ${s.rate}% | 新客占比: ${s.new_pct}%`);
});
lines.push('');

// 3. 优秀标杆门店（案例）
lines.push('三、优秀门店案例（办单≥100，逾期率<1%）');
lines.push('-'.repeat(40));
const excellent = stores.filter(s => s.total >= 100 && s.rate < 1).sort((a,b) => b.total - a.total);
lines.push(`共 ${excellent.length} 家符合条件，以下为Top10:`);
excellent.slice(0, 10).forEach((s, i) => {
  lines.push(`${i+1}. ${s.store} (${s.province}/${s.city}) — 办单${s.total}单, 逾期率${s.rate}%, 新客${s.new_pct}%`);
});
lines.push('');

// 4. 高风险门店案例
lines.push('四、高风险门店案例（办单≥50，逾期率≥10%）');
lines.push('-'.repeat(40));
const highRisk = stores.filter(s => s.total >= 50 && s.rate >= 10).sort((a,b) => b.rate - a.rate);
lines.push(`共 ${highRisk.length} 家，以下为Top15:`);
highRisk.slice(0, 15).forEach((s, i) => {
  lines.push(`${i+1}. ${s.store} (${s.province}/${s.city})`);
  lines.push(`   办单${s.total}单, 逾期率${s.rate}%, 新客${s.new_pct}%`);
});
lines.push('');

// 5. 高风险省份门店分布
lines.push('五、高风险门店地域分布');
lines.push('-'.repeat(40));
const provRisk = {};
stores.filter(s => s.rate >= 5).forEach(s => {
  provRisk[s.province] = provRisk[s.province] || { storeCount: 0, total: 0, overdue: 0 };
  provRisk[s.province].storeCount++;
  provRisk[s.province].total += s.total;
  provRisk[s.province].overdue += s.overdue;
});
Object.entries(provRisk).sort((a,b) => b[1].storeCount - a[1].storeCount).slice(0, 10).forEach(([p, d]) => {
  lines.push(`${p}: ${d.storeCount}家高风险, 办单${d.total}单, 逾期率${(d.overdue/d.total*100).toFixed(2)}%`);
});
lines.push('');

// 6. 集中办单门店（近30天）
lines.push('六、近30天集中办单门店');
lines.push('-'.repeat(40));
const bursts = recents.filter(s => s.recent >= 15 && s.recent/s.total > 0.3).sort((a,b) => b.recent - a.recent);
lines.push(`共 ${bursts.length} 家（近30天≥15单且占总量>30%），以下为Top10:`);
bursts.slice(0, 10).forEach((s, i) => {
  const pct = (s.recent / s.total * 100).toFixed(0);
  lines.push(`${i+1}. ${s.store} — 总量${s.total}单, 近30天${s.recent}单(${pct}%), 总逾期率${s.rate}%, 近30天逾期率${s.recentRate}%`);
});
lines.push('');

// 7. Top10代理商
lines.push('七、Top10代理商');
lines.push('-'.repeat(40));
supps.slice(0, 10).forEach((s, i) => {
  lines.push(`${i+1}. ${s.name}`);
  lines.push(`   门店${s.stores}家, 办单${s.total}单, 逾期率${s.rate}%, 新客${s.new_pct}%`);
});
lines.push('');

// 8. 高风险代理商
lines.push('八、高风险代理商（办单≥500，逾期率≥8%）');
lines.push('-'.repeat(40));
const badSupps = supps.filter(s => s.total >= 500 && s.rate >= 8).sort((a,b) => b.rate - a.rate);
lines.push(`共 ${badSupps.length} 家，以下为Top10:`);
badSupps.slice(0, 10).forEach((s, i) => {
  lines.push(`${i+1}. ${s.name} — 门店${s.stores}家, 办单${s.total}单, 逾期率${s.rate}%, 新客${s.new_pct}%`);
});
lines.push('');

// 9. 具体案例
lines.push('');
lines.push('='.repeat(60));
lines.push('  重点案例');
lines.push('='.repeat(60));
lines.push('');

// 正面案例
lines.push('【正面案例】高办单+低逾期标杆门店');
const bestStore = excellent[0];
if (bestStore) {
  lines.push(`门店名称: ${bestStore.store}`);
  lines.push(`所在区域: ${bestStore.province}/${bestStore.city}`);
  lines.push(`办单量: ${bestStore.total}单`);
  lines.push(`逾期率: ${bestStore.rate}%（远低于全国平均）`);
  lines.push(`新客占比: ${bestStore.new_pct}%`);
  lines.push(`成功因素分析：`);
  lines.push(`  - 高办单量说明门店有稳定的客源和良好的市场口碑`);
  lines.push(`  - 极低逾期率说明门店严格筛选客户，只选择优质客户进件`);
  lines.push(`  - 可作为培训标杆，分享其客群筛选和门店管理的经验`);
}
lines.push('');

// 反面案例 - 高逾期
lines.push('【反面案例】高逾期门店分析');
const worstStore = highRisk[0];
if (worstStore) {
  lines.push(`门店名称: ${worstStore.store}`);
  lines.push(`所在区域: ${worstStore.province}/${worstStore.city}`);
  lines.push(`办单量: ${worstStore.total}单`);
  lines.push(`逾期率: ${worstStore.rate}%`);
  lines.push(`新客占比: ${worstStore.new_pct}%`);
}
lines.push('');

// 反面案例 - 集中办单
lines.push('【反面案例】集中办单门店（欺诈嫌疑）');
const burstStore = bursts[0];
if (burstStore) {
  const pct = (burstStore.recent / burstStore.total * 100).toFixed(0);
  lines.push(`门店名称: ${burstStore.store}`);
  lines.push(`总量: ${burstStore.total}单, 近30天: ${burstStore.recent}单(${pct}%)`);
  lines.push(`总逾期率: ${burstStore.rate}%, 近30天逾期率: ${burstStore.recentRate}%`);
  lines.push(`风险特征: 短时间内集中大量办单，需排查是否涉及欺诈或刷单`);
}
lines.push('');

// 10. 综合建议
lines.push('');
lines.push('='.repeat(60));
lines.push('  综合建议');
lines.push('='.repeat(60));
lines.push('');
lines.push('一、门店管理建议');
lines.push('1. 建立门店评级体系：按办单量、逾期率、通过率综合评分（ABCD四级）');
lines.push('2. 熔断机制：高逾期门店自动限制办单量，防止风险扩散');
lines.push('3. 培训赋能：优秀门店经验分享给其他门店');
lines.push('4. 高频监控：对集中办单门店加强监控和现场检查');
lines.push('');
lines.push('二、代理商管理建议');
lines.push('1. 代理商分级管理：按逾期率设置不同的保证金比例');
lines.push('2. 新客占比高的代理商需重点关注客群质量');
lines.push('3. 对高风险代理商名下门店进行逐一排查');
lines.push('');
lines.push('三、与翼支付协同建议');
lines.push('1. 共享门店黑名单，建立联合惩戒机制');
lines.push('2. 通过率数据互通，及时发现渠道问题');
lines.push('3. 共同制定门店管控标准和考核指标');

fs.writeFileSync('/mnt/d/desktop/门店代理商分析报告.txt', lines.join('\n'));
console.log('✅ 报告已生成: D:\\desktop\\门店代理商分析报告.txt');
