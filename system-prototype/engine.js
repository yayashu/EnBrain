/* ============================================================
 * 谋全局 EnBrain · 核心诊断引擎（系统原型 · 纯函数层）
 * 本文件只做确定性计算，不依赖 DOM，可单独单测
 * ============================================================ */

/* ---------- 1. 行业基准参数（行业经验初值，可调） ---------- */
const INDUSTRY_PARAMS = {
  '零售电商': { hourlyRate: 75,  errorCost: 50,  errorVolume: 5000 },
  '离散制造': { hourlyRate: 80,  errorCost: 100, errorVolume: 3000 },
  '专业服务': { hourlyRate: 100, errorCost: 80,  errorVolume: 2000 },
};

/* ---------- 2. 机会卡（20 张，跨 6 手段域 + S0-S5 + 非技术） ---------- */
const OPPORTUNITY_CARDS = [
  // ===== 非技术 / S0 消除 =====
  { id:'OP-001', name:'低毛利 SKU 清理', bizDomain:'业务/产品', desc:'清理滞销低毛利 SKU，聚焦高价值产品线',
    triggerRule:{ industry:['零售电商'], employeeCount:[30,999999], systems:[], pains:['库存','毛利','SKU'] },
    meansDomain:'业务与商业模式域', meansTech:'S0',
    asIs:'SKU 数量庞大，大量低毛利 SKU 占用库存与运营资源', toBe:'清理低毛利 SKU，聚焦核心产品线',
    valueParams:{ headcountKey:'运营', laborRatio:0, errorDrop:0, cycleCut:0, revenueGain:0.08 },
    implParams:{ weeks:4, mandays:8, difficulty:1, buildCost:2, annualCost:0 }, riskLevel:1, orgSensitive:false, dataNeeds:[], crossSystems:0 },

  { id:'OP-002', name:'无价值审批环节下线', bizDomain:'流程', desc:'砍掉无人能说清价值的审批/报表环节',
    triggerRule:{ industry:[], employeeCount:[50,999999], systems:['OA'], pains:['审批','流程长'] },
    meansDomain:'流程域', meansTech:'S0',
    asIs:'审批链条长，存在多个无价值签字环节', toBe:'精简审批链，砍掉冗余节点',
    valueParams:{ headcountKey:'运营', laborRatio:0.15, errorDrop:0, cycleCut:0.4, revenueGain:0 },
    implParams:{ weeks:3, mandays:6, difficulty:1, buildCost:1, annualCost:0 }, riskLevel:1, orgSensitive:true, dataNeeds:['OA'], crossSystems:0 },

  // ===== 非技术（组织/供应链） =====
  { id:'OP-003', name:'财务/HR 共享中心建设', bizDomain:'职能', desc:'把分散的财务/HR 职能集中为共享中心，降本提效',
    triggerRule:{ industry:[], employeeCount:[200,999999], systems:[], pains:['人力','共享'] },
    meansDomain:'组织与人力域', meansTech:'非技术',
    asIs:'各部门独立配备财务/HR，人力冗余', toBe:'集中共享中心，统一服务',
    valueParams:{ headcountKey:'财务', laborRatio:0.25, errorDrop:0, cycleCut:0, revenueGain:0 },
    implParams:{ weeks:12, mandays:30, difficulty:4, buildCost:20, annualCost:5 }, riskLevel:4, orgSensitive:true, dataNeeds:[], crossSystems:1 },

  { id:'OP-004', name:'采购集中询比价', bizDomain:'供应链', desc:'集中采购、多方询比价，降低采购成本',
    triggerRule:{ industry:['离散制造'], employeeCount:[100,999999], systems:[], pains:['采购','成本'] },
    meansDomain:'供应链与运营域', meansTech:'非技术',
    asIs:'分散采购，议价能力弱', toBe:'集中采购 + 询比价机制',
    valueParams:{ headcountKey:'采购', laborRatio:0.1, errorDrop:0, cycleCut:0, revenueGain:0 },
    implParams:{ weeks:8, mandays:20, difficulty:3, buildCost:5, annualCost:2 }, riskLevel:2, orgSensitive:false, dataNeeds:[], crossSystems:0 },

  { id:'OP-005', name:'门店人力排班定岗定编', bizDomain:'人力', desc:'按客流/业务量优化排班与定编，减少人力冗余',
    triggerRule:{ industry:['零售电商'], employeeCount:[50,999999], systems:[], pains:['排班','人力'] },
    meansDomain:'组织与人力域', meansTech:'非技术',
    asIs:'门店排班粗放，忙闲不均', toBe:'数据驱动排班 + 定岗定编',
    valueParams:{ headcountKey:'门店', laborRatio:0.12, errorDrop:0, cycleCut:0, revenueGain:0 },
    implParams:{ weeks:6, mandays:15, difficulty:2, buildCost:3, annualCost:1 }, riskLevel:2, orgSensitive:true, dataNeeds:[], crossSystems:0 },

  // ===== S1 优化配置 =====
  { id:'OP-006', name:'ERP 主数据治理', bizDomain:'数据', desc:'统一物料/客户/供应商主数据，一数一源',
    triggerRule:{ industry:[], employeeCount:[50,999999], systems:['ERP'], pains:['主数据','数据乱'] },
    meansDomain:'系统与数据域', meansTech:'S1',
    asIs:'主数据多源头、不一致，导致对账困难', toBe:'统一主数据 + 治理规则',
    valueParams:{ headcountKey:'IT', laborRatio:0.2, errorDrop:0.3, cycleCut:0.2, revenueGain:0 },
    implParams:{ weeks:6, mandays:18, difficulty:3, buildCost:6, annualCost:2 }, riskLevel:2, orgSensitive:false, dataNeeds:['ERP'], crossSystems:2 },

  { id:'OP-007', name:'启用系统未用功能', bizDomain:'数字化', desc:'盘点已购系统但未启用的功能，直接启用',
    triggerRule:{ industry:[], employeeCount:[30,999999], systems:[], pains:['系统闲置'] },
    meansDomain:'系统与数据域', meansTech:'S1',
    asIs:'系统买了但大量功能未启用', toBe:'盘点并启用高价值闲置功能',
    valueParams:{ headcountKey:'运营', laborRatio:0.08, errorDrop:0, cycleCut:0.1, revenueGain:0 },
    implParams:{ weeks:4, mandays:10, difficulty:1, buildCost:1, annualCost:0 }, riskLevel:1, orgSensitive:false, dataNeeds:[], crossSystems:0 },

  // ===== S2 集成贯通 =====
  { id:'OP-008', name:'订单-库存-财务跨系统对账', bizDomain:'财务', desc:'打通订单/库存/财务系统，自动对账',
    triggerRule:{ industry:['零售电商'], employeeCount:[30,999999], systems:['ERP'], pains:['对账','孤岛'] },
    meansDomain:'系统与数据域', meansTech:'S2',
    asIs:'订单、库存、财务三套系统手工对账', toBe:'API 打通，自动对账',
    valueParams:{ headcountKey:'财务', laborRatio:0.5, errorDrop:0.4, cycleCut:0.5, revenueGain:0 },
    implParams:{ weeks:8, mandays:25, difficulty:3, buildCost:12, annualCost:3 }, riskLevel:2, orgSensitive:false, dataNeeds:['ERP'], crossSystems:3 },

  { id:'OP-009', name:'MES-ERP 数据打通', bizDomain:'制造', desc:'打通 MES 与 ERP，消除生产数据重复录入',
    triggerRule:{ industry:['离散制造'], employeeCount:[100,999999], systems:['MES'], pains:['重复录入','孤岛'] },
    meansDomain:'系统与数据域', meansTech:'S2',
    asIs:'MES 与 ERP 数据割裂，人工搬运', toBe:'集成贯通，自动同步',
    valueParams:{ headcountKey:'生产', laborRatio:0.35, errorDrop:0.35, cycleCut:0.3, revenueGain:0 },
    implParams:{ weeks:10, mandays:30, difficulty:4, buildCost:20, annualCost:4 }, riskLevel:3, orgSensitive:false, dataNeeds:['MES','ERP'], crossSystems:2 },

  // ===== S3 流程自动化 =====
  { id:'OP-010', name:'发票票据 OCR 录入', bizDomain:'财务', desc:'OCR 自动识别发票/票据，减少手工录入',
    triggerRule:{ industry:['专业服务'], employeeCount:[20,999999], systems:[], pains:['录入','票据'] },
    meansDomain:'系统与数据域', meansTech:'S3',
    asIs:'发票/票据人工录入，量大易错', toBe:'OCR 识别 + 自动录入',
    valueParams:{ headcountKey:'财务', laborRatio:0.55, errorDrop:0.5, cycleCut:0.6, revenueGain:0 },
    implParams:{ weeks:5, mandays:12, difficulty:2, buildCost:4, annualCost:2 }, riskLevel:2, orgSensitive:false, dataNeeds:[], crossSystems:1 },

  { id:'OP-011', name:'重复报表手工整理自动化', bizDomain:'运营', desc:'自动汇总生成重复性报表',
    triggerRule:{ industry:[], employeeCount:[30,999999], systems:[], pains:['报表','重复'] },
    meansDomain:'系统与数据域', meansTech:'S3',
    asIs:'多来源数据手工整理成报表', toBe:'自动化汇总 + 定时生成',
    valueParams:{ headcountKey:'运营', laborRatio:0.3, errorDrop:0.2, cycleCut:0.5, revenueGain:0 },
    implParams:{ weeks:4, mandays:10, difficulty:2, buildCost:3, annualCost:1 }, riskLevel:1, orgSensitive:false, dataNeeds:[], crossSystems:2 },

  { id:'OP-012', name:'渠道佣金稽核自动化', bizDomain:'财务', desc:'自动稽核渠道佣金，防止错发漏发',
    triggerRule:{ industry:['零售电商'], employeeCount:[50,999999], systems:[], pains:['佣金','稽核'] },
    meansDomain:'系统与数据域', meansTech:'S3',
    asIs:'佣金手工核对，错漏难防', toBe:'规则引擎自动稽核',
    valueParams:{ headcountKey:'财务', laborRatio:0.4, errorDrop:0.45, cycleCut:0.4, revenueGain:0 },
    implParams:{ weeks:6, mandays:14, difficulty:2, buildCost:6, annualCost:2 }, riskLevel:2, orgSensitive:false, dataNeeds:[], crossSystems:2 },

  // ===== S4 智能增强 =====
  { id:'OP-013', name:'合同审查风险标注', bizDomain:'法务', desc:'AI 辅助审查合同，标注风险点，人做决策',
    triggerRule:{ industry:['专业服务'], employeeCount:[20,999999], systems:[], pains:['合同','风险'] },
    meansDomain:'智能技术域', meansTech:'S4',
    asIs:'合同人工逐条审查，耗时', toBe:'AI 标注风险点 + 人审核',
    valueParams:{ headcountKey:'法务', laborRatio:0.4, errorDrop:0.35, cycleCut:0.45, revenueGain:0 },
    implParams:{ weeks:6, mandays:16, difficulty:3, buildCost:8, annualCost:3 }, riskLevel:3, orgSensitive:false, dataNeeds:[], crossSystems:1 },

  { id:'OP-014', name:'简历筛选匹配', bizDomain:'人力', desc:'AI 辅助筛选简历，人做最终决策',
    triggerRule:{ industry:[], employeeCount:[50,999999], systems:[], pains:['招聘','筛选'] },
    meansDomain:'智能技术域', meansTech:'S4',
    asIs:'HR 人工筛简历，量大', toBe:'AI 初筛 + 人复核',
    valueParams:{ headcountKey:'HR', laborRatio:0.35, errorDrop:0, cycleCut:0.4, revenueGain:0 },
    implParams:{ weeks:5, mandays:12, difficulty:3, buildCost:6, annualCost:2 }, riskLevel:3, orgSensitive:false, dataNeeds:[], crossSystems:1 },

  { id:'OP-015', name:'质检记录不良归因', bizDomain:'质量', desc:'AI 辅助分析质检数据，定位不良根因',
    triggerRule:{ industry:['离散制造'], employeeCount:[50,999999], systems:[], pains:['质检','不良'] },
    meansDomain:'智能技术域', meansTech:'S4',
    asIs:'不良原因靠经验判断', toBe:'AI 归因 + 人确认',
    valueParams:{ headcountKey:'质检', laborRatio:0.25, errorDrop:0.3, cycleCut:0.3, revenueGain:0 },
    implParams:{ weeks:8, mandays:20, difficulty:4, buildCost:10, annualCost:3 }, riskLevel:3, orgSensitive:false, dataNeeds:[], crossSystems:1 },

  { id:'OP-016', name:'营销素材批量生成', bizDomain:'营销', desc:'AI 批量生成/改写营销素材，人审核发布',
    triggerRule:{ industry:['零售电商'], employeeCount:[20,999999], systems:[], pains:['素材','内容'] },
    meansDomain:'智能技术域', meansTech:'S4',
    asIs:'营销素材人工制作，效率低', toBe:'AI 批量生成 + 人审',
    valueParams:{ headcountKey:'运营', laborRatio:0.3, errorDrop:0, cycleCut:0.5, revenueGain:0.05 },
    implParams:{ weeks:4, mandays:10, difficulty:2, buildCost:3, annualCost:2 }, riskLevel:2, orgSensitive:false, dataNeeds:[], crossSystems:1 },

  // ===== S5 智能自治 =====
  { id:'OP-017', name:'客服工单自动分派', bizDomain:'客服', desc:'AI 自动分类分派工单，低置信转人工',
    triggerRule:{ industry:['零售电商'], employeeCount:[20,999999], systems:[], pains:['客服','工单'] },
    meansDomain:'智能技术域', meansTech:'S5',
    asIs:'客服人工看工单分派，响应慢', toBe:'AI 分类分派 + 人审',
    valueParams:{ headcountKey:'客服', laborRatio:0.5, errorDrop:0.3, cycleCut:0.7, revenueGain:0 },
    implParams:{ weeks:6, mandays:15, difficulty:3, buildCost:8, annualCost:3 }, riskLevel:2, orgSensitive:true, dataNeeds:[], crossSystems:1 },

  { id:'OP-018', name:'智能客服问答', bizDomain:'客服', desc:'基于知识库的自动问答，降低人工客服量',
    triggerRule:{ industry:['零售电商'], employeeCount:[20,999999], systems:[], pains:['客服','问答'] },
    meansDomain:'智能技术域', meansTech:'S5',
    asIs:'大量重复问题人工回复', toBe:'知识库自动问答 + 转人工',
    valueParams:{ headcountKey:'客服', laborRatio:0.4, errorDrop:0, cycleCut:0.5, revenueGain:0 },
    implParams:{ weeks:5, mandays:12, difficulty:3, buildCost:6, annualCost:2 }, riskLevel:2, orgSensitive:true, dataNeeds:[], crossSystems:1 },

  { id:'OP-019', name:'订单交期智能答复', bizDomain:'销售', desc:'AI 基于生产/库存数据自动答复交期',
    triggerRule:{ industry:['离散制造'], employeeCount:[50,999999], systems:['MES'], pains:['交期'] },
    meansDomain:'智能技术域', meansTech:'S5',
    asIs:'交期需人工查数据后答复', toBe:'AI 自动查数据答复交期',
    valueParams:{ headcountKey:'销售', laborRatio:0.3, errorDrop:0.25, cycleCut:0.5, revenueGain:0 },
    implParams:{ weeks:7, mandays:18, difficulty:4, buildCost:10, annualCost:3 }, riskLevel:3, orgSensitive:false, dataNeeds:['MES'], crossSystems:2 },

  { id:'OP-020', name:'政策/制度知识问答', bizDomain:'通用', desc:'基于内部制度的知识问答，减少重复咨询',
    triggerRule:{ industry:[], employeeCount:[100,999999], systems:[], pains:['制度','咨询'] },
    meansDomain:'智能技术域', meansTech:'S5',
    asIs:'内部制度/流程反复人工解答', toBe:'知识库自动问答',
    valueParams:{ headcountKey:'运营', laborRatio:0.2, errorDrop:0, cycleCut:0.4, revenueGain:0 },
    implParams:{ weeks:5, mandays:12, difficulty:3, buildCost:5, annualCost:2 }, riskLevel:2, orgSensitive:false, dataNeeds:[], crossSystems:1 },
];

/* ---------- 3. 规则求值器（触发规则 DSL） ---------- */
function evaluateRule(rule, profile) {
  if (rule.industry && rule.industry.length && !rule.industry.includes(profile.industry)) return false;
  if (rule.employeeCount) {
    if (profile.employeeCount < rule.employeeCount[0] || profile.employeeCount > rule.employeeCount[1]) return false;
  }
  if (rule.systems && rule.systems.length) {
    const hit = rule.systems.some(s => profile.systems.some(ps => ps.includes(s)));
    if (!hit) return false;
  }
  if (rule.pains && rule.pains.length) {
    const hit = rule.pains.some(p => profile.pains.some(pp => pp.includes(p)));
    if (!hit) return false;
  }
  return true;
}

/* ---------- 4. 匹配引擎 ---------- */
function matchOpportunities(profile) {
  // L1 硬规则过滤
  const L1 = OPPORTUNITY_CARDS.filter(c => evaluateRule(c.triggerRule, profile));
  // L2 语义召回（关键词相似度模拟：痛点/流程 与 机会描述/业务域 的交集）
  const L2 = OPPORTUNITY_CARDS.filter(c => !L1.includes(c)).filter(c => {
    const profileText = (profile.pains.join(' ') + ' ' + profile.bizFlows.join(' '));
    const cardText = c.desc + ' ' + c.bizDomain + ' ' + c.name;
    const profileKeys = profileText.split(/\s+/).filter(k => k.length >= 2);
    return profileKeys.some(k => cardText.includes(k));
  });
  // 去重合并
  const map = new Map();
  [...L1, ...L2].forEach(c => map.set(c.id, c));
  return Array.from(map.values());
}

/* ---------- 5. 评分引擎（权重可调） ---------- */
function scoreOpportunity(opp, profile, w) {
  const p = INDUSTRY_PARAMS[profile.industry] || { hourlyRate: 75, errorCost: 50, errorVolume: 5000 };

  // V 价值度
  const hc = opp.valueParams.headcountKey ? (profile.departments[opp.valueParams.headcountKey] || 0) : 0;
  const laborRatio = opp.valueParams.laborRatio || 0;
  let laborScore = 20;
  if (hc > 0 && laborRatio > 0) {
    const ratio = (hc * laborRatio) / Math.max(profile.employeeCount, 1);
    laborScore = ratio >= 0.05 ? 100 : ratio >= 0.02 ? 75 : ratio >= 0.01 ? 55 : 35;
  }
  const ed = opp.valueParams.errorDrop || 0;
  const qualityScore = ed >= 0.5 ? 100 : ed >= 0.3 ? 80 : ed >= 0.1 ? 55 : 30;
  const cc = opp.valueParams.cycleCut || 0;
  const cycleScore = cc >= 0.6 ? 100 : cc >= 0.3 ? 70 : cc >= 0.1 ? 50 : 30;
  const rg = opp.valueParams.revenueGain || 0;
  const revenueScore = rg >= 0.05 ? 100 : rg >= 0.02 ? 70 : rg > 0 ? 45 : 0;
  const V = w.v.labor*laborScore + w.v.quality*qualityScore + w.v.cycle*cycleScore + w.v.revenue*revenueScore;

  // F 可行性
  const needs = opp.dataNeeds || [];
  let dataScore = 100;
  if (needs.length) {
    const has = needs.filter(n => profile.systems.some(s => s.includes(n))).length;
    dataScore = has === needs.length ? 100 : has > 0 ? 60 : 20;
  }
  const cross = opp.crossSystems || 0;
  const integScore = cross === 0 ? 100 : cross === 1 ? 70 : cross <= 3 ? 40 : 20;
  const diff = opp.implParams.difficulty || 1;
  const techScore = [90,80,65,45,30][diff-1] || 60;
  const stdMap = { '高':100, '中':70, '低':40 };
  const stdScore = stdMap[profile.stdLevel] || 50;
  const F = w.f.data*dataScore + w.f.integ*integScore + w.f.tech*techScore + w.f.std*stdScore;

  // R 风险度
  const compMap = { '高':80, '中':50, '低':20 };
  const compScore = compMap[profile.complianceLevel] || 50;
  const riskScore = (opp.riskLevel || 1) * 20;
  const orgScore = opp.orgSensitive ? 60 : 30;
  const R = w.r.compliance*compScore + w.r.tolerance*riskScore + w.r.org*orgScore;

  const ALI = w.top.V*V + w.top.F*F - w.top.R*R;
  return { V: round(V), F: round(F), R: round(R), ALI: round(ALI) };
}

/* ---------- 6. 手段选型（S0-S5 决策树） ---------- */
function selectMeans(opp) {
  return opp.meansTech; // 机会卡已按 2.9.4 决策树标注推荐手段
}

/* ---------- 7. ROI 测算（三档区间） ---------- */
function calcROI(opp, profile) {
  const p = INDUSTRY_PARAMS[profile.industry] || { hourlyRate: 75, errorCost: 50, errorVolume: 5000 };
  const hc = opp.valueParams.headcountKey ? (profile.departments[opp.valueParams.headcountKey] || 0) : 0;
  const laborRatio = opp.valueParams.laborRatio || 0;
  const laborSave = hc * 2 * 250 * laborRatio * p.hourlyRate * 0.8; // 日均2h
  const qualityGain = p.errorVolume * p.errorCost * (opp.valueParams.errorDrop || 0);
  const buildCost = (opp.implParams.buildCost || 0) * 10000; // 万→元
  const annualCost = (opp.implParams.annualCost || 0) * 10000;
  const totalBenefit = laborSave + qualityGain;
  const totalCost = buildCost + annualCost;
  const roi = totalCost > 0 ? (totalBenefit - totalCost) / totalCost : 0;
  const payback = totalBenefit > 0 ? totalCost / (totalBenefit / 12) : Infinity;

  // 三档区间（保守/中性/乐观）
  const conservative = { benefit: totalBenefit*0.7, roi: totalCost>0 ? (totalBenefit*0.7-totalCost)/totalCost : 0 };
  const optimistic = { benefit: totalBenefit*1.2, roi: totalCost>0 ? (totalBenefit*1.2-totalCost)/totalCost : 0 };

  return {
    laborSave: round(laborSave/10000), qualityGain: round(qualityGain/10000),
    totalBenefit: round(totalBenefit/10000), totalCost: round(totalCost/10000),
    roi: round(roi*100)/100, payback: payback === Infinity ? null : round(payback),
    conservative: round(conservative.roi*100)/100, optimistic: round(optimistic.roi*100)/100,
  };
}

/* ---------- 8. 交付方式决策（DFI） ---------- */
function decideDelivery(opp, profile) {
  const it = profile.itHeadcount || 0;
  const C = 0.35*Math.min(it*30,100) + 0.30*(profile.skillMatch||50) + 0.20*(profile.platformReady||30) + 0.15*(profile.aiExp||30);
  const cross = opp.crossSystems || 0;
  const X = 0.35*(cross>=3?90:cross===2?60:cross===1?35:15) + 0.25*(profile.dataQuality||50) + 0.25*(opp.implParams.difficulty*20) + 0.15*(profile.complianceLevel==='高'?80:profile.complianceLevel==='中'?50:20);
  const M = opp.implParams.difficulty <= 2; // 市场成熟度（简化：难度≤2 视为有成熟产品）
  const S = profile.dataOutbound === true; // 数据不出域

  let mode, reason;
  if (S) { mode = 'A/C 私有化'; reason = '数据不出域，仅自建或第三方私有化'; }
  else if (M && X < 45) { mode = 'B 采购'; reason = '市场有成熟产品，场景标准'; }
  else if (C >= 55 && X < 65) { mode = 'A 自建'; reason = '自建能力足，场景不复杂'; }
  else if (X >= 65 && C < 70) { mode = 'C 第三方'; reason = '场景复杂，需外部集成商'; }
  else if (X < 45 && C < 40) { mode = 'D AI 托管'; reason = '场景轻，企业无 IT 能力'; }
  else { mode = 'C 第三方'; reason = '综合评估，建议第三方实施'; }

  return { mode, reason, C: round(C), X: round(X) };
}

/* ---------- 9. 主流程 ---------- */
function runDiagnosis(profile, weights) {
  const matched = matchOpportunities(profile);
  const results = matched.map(opp => {
    const score = scoreOpportunity(opp, profile, weights);
    const roi = calcROI(opp, profile);
    const delivery = decideDelivery(opp, profile);
    return { opp, score, roi, delivery };
  });
  results.sort((a,b) => b.score.ALI - a.score.ALI);
  const aiList = results.filter(r => r.opp.meansTech === 'S4' || r.opp.meansTech === 'S5');
  const nonAiList = results.filter(r => !(r.opp.meansTech === 'S4' || r.opp.meansTech === 'S5'));
  return { profile, results, aiList, nonAiList, matchedCount: results.length };
}

function round(n) { return Math.round(n * 10) / 10; }

/* 默认权重 */
const DEFAULT_WEIGHTS = {
  top: { V: 0.45, F: 0.35, R: 0.20 },
  v: { labor:0.45, quality:0.25, cycle:0.20, revenue:0.10 },
  f: { data:0.35, integ:0.25, tech:0.25, std:0.15 },
  r: { compliance:0.40, tolerance:0.35, org:0.25 },
};
