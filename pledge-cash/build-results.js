// 生成《第五章（续）》含实际估计结果的版本。所有数值从 results/*.json 读取，不手工录入。
// 无法估计的单元格写“—”，并在表注中写明所缺数据。
const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ImageRun,
  AlignmentType, BorderStyle, HeadingLevel, TabStopType, VerticalAlign,
} = require('docx');

const R = (f) => JSON.parse(fs.readFileSync(path.join(__dirname, 'results', f), 'utf8'));
const BL = R('res_baseline.json'), CH = R('res_channels.json'), BD = R('res_boundary.json');
const DD = R('res_did.json'), RB = R('res_robust.json');

const TEXT_W = 8306, CN = '宋体', CN_H = '黑体', EN = 'Times New Roman';
function runs(text, base = {}) {
  const out = [];
  const push = (t, extra = {}) => {
    if (!t) return;
    out.push(new TextRun({ text: t, font: { ascii: EN, hAnsi: EN, eastAsia: base.cn || CN }, size: base.size || 24, bold: base.bold, ...extra }));
  };
  for (const seg of text.split(/(【[^】]*】)/)) {
    if (!seg) continue;
    const hl = seg.startsWith('【') ? { highlight: 'yellow' } : {};
    const re = /(_\{[^}]*\}|\^\{[^}]*\})/g;
    let last = 0, m;
    while ((m = re.exec(seg))) {
      push(seg.slice(last, m.index), hl);
      push(m[0].slice(2, -1), { ...hl, [m[0][0] === '_' ? 'subScript' : 'superScript']: true });
      last = m.index + m[0].length;
    }
    push(seg.slice(last), hl);
  }
  return out;
}
const body = [];
const P = (t) => body.push(new Paragraph({ children: runs(t), indent: { firstLine: 480 }, spacing: { line: 360 }, alignment: AlignmentType.JUSTIFIED }));
const H = (t, level) => body.push(new Paragraph({
  heading: level, children: runs(t, { cn: CN_H, bold: true, size: level === HeadingLevel.HEADING_1 ? 32 : level === HeadingLevel.HEADING_2 ? 28 : 24 }),
  spacing: { before: 240, after: 120, line: 360 }, keepNext: true,
  alignment: level === HeadingLevel.HEADING_1 ? AlignmentType.CENTER : AlignmentType.LEFT,
}));
const EQ = (t, no) => {
  const lines = Array.isArray(t) ? t : [t];
  lines.forEach((ln, i) => {
    const last = i === lines.length - 1;
    body.push(new Paragraph({
      children: [new TextRun({ text: '\t' }), ...runs(ln), ...(last ? [new TextRun({ text: `\t(${no})`, font: EN, size: 24 })] : [])],
      tabStops: [{ type: TabStopType.CENTER, position: TEXT_W / 2 }, { type: TabStopType.RIGHT, position: TEXT_W }],
      spacing: { before: i === 0 ? 60 : 0, after: last ? 60 : 0, line: 360 }, keepNext: !last,
    }));
  });
};
const NOTE = (t) => body.push(new Paragraph({ children: runs(t, { size: 18 }), spacing: { after: 160, line: 300 }, alignment: AlignmentType.JUSTIFIED }));
const CAP = (t) => body.push(new Paragraph({ children: runs(t, { cn: CN_H, size: 21, bold: true }), alignment: AlignmentType.CENTER, spacing: { before: 200, after: 80 }, keepNext: true }));
const IMG = (file, cap, w = 560, h = 302) => {
  body.push(new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, children: [new ImageRun({ type: 'png', data: fs.readFileSync(path.join(__dirname, 'figures', file)), transformation: { width: w, height: h } })] }));
  body.push(new Paragraph({ children: runs(cap, { cn: CN_H, size: 21, bold: true }), alignment: AlignmentType.CENTER, spacing: { before: 60, after: 160 } }));
};

const THICK = { style: BorderStyle.SINGLE, size: 12, color: '000000' };
const THIN = { style: BorderStyle.SINGLE, size: 6, color: '000000' };
const NONE = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };
function TABLE(caption, rows, opts = {}) {
  CAP(caption);
  const ncol = rows[0].length;
  const first = opts.first || Math.round(TEXT_W * (ncol > 5 ? 0.24 : 0.28));
  const rest = Math.floor((TEXT_W - first) / (ncol - 1));
  const widths = opts.widths ? [...opts.widths] : [first, ...Array(ncol - 1).fill(rest)];
  widths[ncol - 1] += TEXT_W - widths.reduce((a, b) => a + b, 0);
  const hdr = opts.header || 1;
  const trs = rows.map((r, ri) => new TableRow({
    cantSplit: true,
    children: r.map((c, ci) => new TableCell({
      width: { size: widths[ci], type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
      borders: { top: ri === 0 ? THICK : NONE, bottom: ri === rows.length - 1 ? THICK : ri === hdr - 1 ? THIN : NONE, left: NONE, right: NONE },
      margins: { top: 30, bottom: 30, left: 60, right: 60 },
      children: [new Paragraph({ keepNext: ri < rows.length - 1, children: runs(String(c), { size: 20 }), alignment: ci === 0 ? AlignmentType.LEFT : AlignmentType.CENTER })],
    })),
  }));
  body.push(new Table({ width: { size: TEXT_W, type: WidthType.DXA }, columnWidths: widths, rows: trs }));
  if (opts.note) NOTE(opts.note);
}
const NA = '—';
// 系数两行：v 为 [系数, (标准误)] 或 null（未进入该列模型→空白）或 NA（无法估计）
const coef = (name, vals) => [[name, ...vals.map((v) => (v === NA ? NA : v ? v[0] : ''))], ['', ...vals.map((v) => (v && v !== NA ? v[1] : ''))]];
const row = (name, ...v) => [name, ...v];
const f3 = (x) => Number(x).toFixed(3), f4 = (x) => Number(x).toFixed(4), pct = (x) => (100 * x).toFixed(1) + '%';
const STD = '括号内为公司层面聚类稳健标准误；***、**、*分别表示1%、5%、10%显著水平；连续变量经上下1%缩尾。';
const CTRLNOTE = '控制变量同表5-3。';

// ============ 正文 ============
H('第五章（续）　渠道检验、边界条件与政策评估', HeadingLevel.HEADING_1);
body.push(new Paragraph({
  children: runs(`【编写说明（定稿前删除）：本稿接开题报告第四部分（三）之后，按论文第五章编排。所有数值由作者提供的CSMAR数据重新构造样本后估计所得，脚本与结果文件见 pledge-cash/scripts 与 pledge-cash/results。重构样本为${BL.N.toLocaleString('en-US')}个公司—年度观测、${BL.firms.toLocaleString('en-US')}家公司，开题报告为50,961个、5,161家；基准系数复现为${BL.t6[1].coef[0]}，开题报告为-0.0165***（对照见附表一）。正文前后各表须来自同一样本，定稿时应统一采用一套样本与代码。表中“—”表示所需数据未提供、未能估计，表注写明所缺数据；黄色标注处为待补内容。】`, { size: 21 }),
  spacing: { after: 200, line: 320 }, alignment: AlignmentType.JUSTIFIED,
}));

// ---------- 5.3 ----------
const t6 = BL.t6;
H('5.3　渠道检验：区分风险规避与掏空', HeadingLevel.HEADING_2);
P(`表5-3的基准回归显示，大股东股权质押比例的系数显著为负（列(2)为${t6[1].coef[0]}），说明在样本平均意义上，质押比例上升伴随现金持有水平下降。但净效应只是两种力量的合力，系数为负并不能排除风险规避渠道同时存在，也不能直接证明掏空渠道成立。本节依据第三章提出的H2a与H2b，从平仓压力、控股股东资金占用与现金边际价值三个方面开展检验。`);

H('5.3.1　平仓压力', HeadingLevel.HEADING_3);
P('平仓压力指标Pressure按如下方式构造。对第一大股东在t年末仍未解押的每一笔质押k，以质押起始日收盘价为基期，用考虑现金红利再投资的月个股回报率推算此后各月末的复权价格I_{k}(m)。CSMAR质押明细表未提供预警线与平仓线字段，本文按质押率40%、年利率10%与预警线160%设定预警条件：');
EQ('I_{k}(m) / I_{k}(0) ＜ 0.40 × 1.60 × (1 + 0.10τ) = 0.64(1 + 0.10τ)', '5-1');
P('其中τ为质押起始日至m月末的年数。若t年内任一月末满足式(5-1)，则记该笔质押触及预警线；Pressure_{i,t}为触及预警线的质押股数占第一大股东全部未解押质押股数的比例，当年无质押的公司取0。质押明细表中存在只有新增记录而无解押记录的情况，为避免已实际解押的质押被计入，本文剔除合同结束日早于t年末的记录，以及无结束日期且起始日早于t年末3年以上的记录。');
P('平仓压力由股价下跌驱动，而股价下跌本身可能反映公司经营恶化，因此模型中控制当年股票回报率Ret；同时构造市场驱动的平仓压力Pressure_Mkt，即在式(5-1)中以沪深A股按上月总市值加权的月回报构造的市场指数替代个股价格路径，其变动主要来自质押时点与市场整体下跌的相对位置。检验模型为：');
EQ(['Cash_{i,t} = β_{0} + β_{1}Pledge_{i,t} + β_{2}Pledge_{i,t}×Pressure_{i,t} + β_{3}Pressure_{i,t}', ' + β_{4}Ret_{i,t} + β_{5}Controls_{i,t} + λ_{t} + μ_{i} + ε_{i,t}'], '5-2');
P('判定规则：β_{2}显著为正，支持H2a；β_{2}不显著或显著为负，则不支持风险规避渠道的存在。以Pressure_Mkt的结果为主要依据。');
const pd5 = CH.pressure_diag;
const vif = (r) => (1 / (1 - r * r)).toFixed(2);
const c5 = CH.t5_5;
P(`在有质押的公司—年度中，Pressure大于0的占${pct(pd5.Pressure.share_pos_among_pledgers)}，Pressure_Mkt大于0的占${pct(pd5.Pressure_Mkt.share_pos_among_pledgers)}。Pledge×Pressure与Pressure的相关系数为${f3(pd5.Pressure.corr_PxP_P_all)}（方差膨胀因子${vif(pd5.Pressure.corr_PxP_P_all)}），市场口径为${f3(pd5.Pressure_Mkt.corr_PxP_P_all)}（${vif(pd5.Pressure_Mkt.corr_PxP_P_all)}），共线性处于可接受范围。表5-5显示，四列中交乘项均不显著：个股口径下β_{2}为${c5[0].PxP[0]}与${c5[1].PxP[0]}（滞后一期），市场驱动口径下为${c5[2].PxP[0]}，加入行业×年度固定效应后为${c5[3].PxP[0]}。按判定规则，本文未发现平仓压力上升时质押公司增持现金的证据，H2a未获支持。加入平仓压力后，Pledge的系数仍显著为负。`);
TABLE('表5-5　平仓压力与现金持有', [
  ['变量', '(1)', '(2)', '(3)', '(4)'],
  ['压力口径', 'Pressure', 'Pressure_{t−1}', 'Pressure_Mkt', 'Pressure_Mkt'],
  ...coef('Pledge', c5.map((c) => c.Pledge)), ...coef('Pledge×压力', c5.map((c) => c.PxP)),
  ...coef('压力', c5.map((c) => c.P)), ...coef('Ret', c5.map((c) => c.Ret)),
  row('控制变量', '是', '是', '是', '是'), row('公司固定效应', '是', '是', '是', '是'),
  row('年度固定效应', '是', '是', '是', '否'), row('行业×年度固定效应', '否', '否', '否', '是'),
  row('调整R²', ...c5.map((c) => c.r2)), row('观测值', ...c5.map((c) => c.N)),
], { header: 2, note: '注：被解释变量为Cash。' + CTRLNOTE + STD });

H('5.3.2　控股股东资金占用', HeadingLevel.HEADING_3);
P('参照Jiang等（2010），以经行业年度均值调整的其他应收款与其他应付款之差OREC衡量资金净占用：');
EQ('OREC_{i,t} = α_{0} + α_{1}Pledge_{i,t} + α_{2}Controls_{i,t} + λ_{t} + μ_{i} + ε_{i,t}', '5-3');
const c6 = CH.t5_6;
P(`判定规则：α_{1}显著为正，支持H2b中“质押伴随资金占用上升”的部分；不显著则不支持。表5-6显示，α_{1}为${c6[0].Pledge[0]}${c6[0].Pledge[1]}，未经行业调整的口径为${c6[1].Pledge[0]}${c6[1].Pledge[1]}，加入行业×年度固定效应后为${c6[2].Pledge[0]}${c6[2].Pledge[1]}，均接近于零且不显著。即在公司固定效应设定下，质押比例上升并未伴随以其他应收款衡量的资金占用增加，H2b的这一部分未获支持。其他应收款是资金占用的含噪代理变量，这一结论有待以年报披露的非经营性资金占用数据进一步检验。【待补：控股股东及其关联方非经营性资金占用金额，用于列(3)。】`);
TABLE('表5-6　股权质押与控股股东资金占用', [
  ['变量', '(1)', '(2)', '(3)', '(4)'],
  ['被解释变量', 'OREC', 'OREC（未调整）', '非经营性占用', 'OREC'],
  ...coef('Pledge', [c6[0].Pledge, c6[1].Pledge, NA, c6[2].Pledge]),
  row('控制变量', '是', '是', '是', '是'), row('公司固定效应', '是', '是', '是', '是'),
  row('年度固定效应', '是', '是', '是', '否'), row('行业×年度固定效应', '否', '否', '否', '是'),
  row('调整R²', c6[0].r2, c6[1].r2, NA, c6[2].r2), row('观测值', c6[0].N, c6[1].N, NA, c6[2].N),
], { header: 2, note: '注：列(3)缺控股股东及其关联方非经营性资金占用数据，未能估计。' + CTRLNOTE + STD });

H('5.3.3　现金边际价值', HeadingLevel.HEADING_3);
P('参照Faulkender和Wang（2006），将模型(4)展开为：');
EQ(['r_{i,t} − R^{B}_{i,t} = γ_{0} + γ_{1}ΔC_{i,t} + γ_{2}ΔC_{i,t}×Pledge_{i,t} + γ_{3}Pledge_{i,t} + γ_{4}ΔE_{i,t}', ' + γ_{5}ΔNA_{i,t} + γ_{6}ΔRD_{i,t} + γ_{7}ΔI_{i,t} + γ_{8}ΔD_{i,t} + γ_{9}C_{i,t−1} + γ_{10}L_{i,t}', ' + γ_{11}NF_{i,t} + γ_{12}C_{i,t−1}×ΔC_{i,t} + γ_{13}L_{i,t}×ΔC_{i,t} + λ_{t} + μ_{i} + ε_{i,t}'], '5-4');
P('变量定义同第四章。判定规则：γ_{2}显著为负支持H2b；不显著或为正与H2a一致，并报告γ_{2}的95%置信区间。【待补：本项检验所需的非经常性损益、利息费用、研发支出、普通股现金股利及筹资活动现金流（吸收投资、取得借款、偿还债务）数据尚未提供，表5-7暂未估计。】');
TABLE('表5-7　股权质押与现金边际价值', [
  ['变量', '(1)', '(2)', '(3)'],
  ['基准收益/质押口径', '25组合/Pledge', '三因子/Pledge', '25组合/Pledge_Dum'],
  ...coef('ΔC', [NA, NA, NA]), ...coef('ΔC×质押', [NA, NA, NA]), ...coef('质押', [NA, NA, NA]),
  row('γ_{2}的95%置信区间', NA, NA, NA), row('Faulkender-Wang控制变量', '是', '是', '是'),
  row('公司与年度固定效应', '是', '是', '是'), row('调整R²', NA, NA, NA), row('观测值', NA, NA, NA),
], { header: 2, note: '注：所需数据未提供，未能估计。' });

H('5.3.4　渠道检验小结', HeadingLevel.HEADING_3);
P('按第三章写定的组合规则，三项检验中已完成的两项均不显著：平仓压力的交乘项不显著（H2a未获支持），质押对资金占用的影响不显著（H2b的资金占用部分未获支持），现金边际价值检验因数据不足尚未完成。因此，基准回归中质押与现金持有的负向关系，目前既不能归因于风险规避渠道，也不能归因于以资金占用为表现的掏空渠道。初步结果“与H1b（掏空说）一致”的表述只在净效应的符号层面成立，不宜进一步解读为掏空机制得到验证。5.8.3将从上市后募集资金消耗的角度考察这一负向关系的来源。');

// ---------- 5.4 ----------
const b8 = BD.t5_8;
H('5.4　边界条件检验', HeadingLevel.HEADING_2);
H('5.4.1　融资约束（H3）', HeadingLevel.HEADING_3);
P('按模型(2)，以滞后一期SA指数高于当年中位数定义HighFC。SA指数由企业规模与上市年限构成，在本文样本中HighFC与上市年限对数Age的相关系数为' + f3(BD.corr_HighFC_Age) + '，因此在模型(2)基础上加入质押与中心化的上市年限、企业规模的交乘项：');
EQ(['Cash_{i,t} = β_{0} + β_{1}Pledge_{i,t} + β_{2}Pledge_{i,t}×HighFC_{i,t−1} + β_{3}HighFC_{i,t−1}', ' + β_{4}Pledge_{i,t}×Age^{c}_{i,t} + β_{5}Pledge_{i,t}×Size^{c}_{i,t} + β_{6}Controls_{i,t} + λ_{t} + μ_{i} + ε_{i,t}'], '5-5');
P(`判定规则：β_{2}与β_{1}同号且显著，支持H3；若β_{2}在加入Pledge×Age^{c}与Pledge×Size^{c}后不再显著，则H3不成立。表5-8列(1)中β_{2}为${b8[0].PxH[0]}，单看似乎支持H3；但列(2)加入两个交乘项后，β_{2}变为${b8[1].PxH[0]}，不再显著，而Pledge×Age^{c}为${b8[1].PxAge[0]}，Pledge×Size^{c}为${b8[1].PxSize[0]}。这说明列(1)中的调节作用实际来自上市年限：上市年限越短，质押与现金持有的负向关系越强。按判定规则，H3不成立。KZ指数与WW指数口径因缺现金股利与长期负债数据，尚未估计。【待补：现金股利、长期借款、应付债券数据，用于列(3)、(4)。】`);
TABLE('表5-8　融资约束的边界作用', [
  ['变量', '(1)', '(2)', '(3)', '(4)'],
  ['融资约束口径', 'SA', 'SA', 'KZ', 'WW'],
  ...coef('Pledge', [b8[0].Pledge, b8[1].Pledge, NA, NA]), ...coef('Pledge×HighFC', [b8[0].PxH, b8[1].PxH, NA, NA]),
  ...coef('HighFC', [b8[0].HighFC, b8[1].HighFC, NA, NA]), ...coef('Pledge×Age^{c}', [null, b8[1].PxAge, NA, NA]),
  ...coef('Pledge×Size^{c}', [null, b8[1].PxSize, NA, NA]),
  row('控制变量', '是', '是', '是', '是'), row('公司与年度固定效应', '是', '是', '是', '是'),
  row('调整R²', b8[0].r2, b8[1].r2, NA, NA), row('观测值', b8[0].N, b8[1].N, NA, NA),
], { header: 2, note: '注：被解释变量为Cash；HighFC为滞后一期SA指数高于当年中位数的虚拟变量；Age^{c}、Size^{c}为中心化后的上市年限与企业规模。列(3)、(4)缺现金股利与长期负债数据，未能估计。' + STD });

const d9 = BD.t5_9, b10 = BD.t5_10;
H('5.4.2　产权性质（H4）', HeadingLevel.HEADING_3);
P(`表5-9报告两组的质押分布。国有企业中存在质押的观测仅占${d9[0].dum}，质押比例均值为${d9[0].mean}，75分位数为${d9[0].p75}；非国有企业分别为${d9[1].dum}、${d9[1].mean}与${d9[1].p75}。国有企业组质押比例的组内标准差为${d9[0].within_sd}，低于非国有企业的${d9[1].within_sd}，固定效应模型在该组可利用的变异较少。`);
P(`判定规则：Pledge×SOE的系数显著且与β_{1}符号相反，支持H4。表5-10列(1)中Pledge×SOE为${b10[0].PxSOE[0]}${b10[0].PxSOE[1]}，不显著，H4未获支持。分组回归中，非国有企业组系数为${b10[1].Pledge[0]}，国有企业组为${b10[2].Pledge[0]}，均不显著；而全样本中非国有企业的效应（列(1)的Pledge）为${b10[0].Pledge[0]}。二者的差异来自分组回归允许控制变量系数与年度效应在组间不同，说明非国有企业组的负向关系对模型设定较为敏感。鉴于国有企业组组内变异较小，其系数不显著不应解读为效应不存在。`);
TABLE('表5-9　按产权性质分组的质押分布', [
  ['组别', '观测值', '存在质押的比例', 'Pledge均值', 'Pledge组内标准差', 'P75', 'P90'],
  ...d9.map((r, i) => [i === 0 ? '国有企业' : '非国有企业', r.N, r.dum, r.mean, r.within_sd, r.p75, r.p90]),
], { note: '注：“组内标准差”为各公司Pledge减去其公司均值后的标准差。非国有企业包括股权性质为民营、外资与其他的公司。' });
TABLE('表5-10　产权性质的边界作用', [
  ['变量', '(1) 全样本', '(2) 非国有企业', '(3) 国有企业'],
  ...coef('Pledge', b10.map((c) => c.Pledge)), ...coef('Pledge×SOE', [b10[0].PxSOE, null, null]),
  row('控制变量', '是', '是', '是'), row('公司与年度固定效应', '是', '是', '是'),
  row('调整R²', ...b10.map((c) => c.r2)), row('观测值', ...b10.map((c) => c.N)),
], { note: '注：被解释变量为Cash；列(1)同时控制SOE（由股权性质变更的公司识别）。' + STD });

// ---------- 5.5 ----------
const ds = DD.did_sample, f11 = DD.t5_11, m12 = DD.t5_12, pp = DD.placebo_perm, tr = DD.trend_adj;
H('5.5　政策评估：2018年股票质押新规', HeadingLevel.HEADING_2);
H('5.5.1　样本与处理强度', HeadingLevel.HEADING_3);
P(`双重差分样本限定为2016年之前上市、且2016年与2017年至少有一年质押数据的公司，共${ds.firms.toLocaleString('en-US')}家、${ds.N.toLocaleString('en-US')}个观测。处理强度PledgePre_{i}为公司2016年与2017年年末大股东质押比例的均值，其均值为${f3(ds.PledgePre_mean)}、中位数为${f3(ds.PledgePre_median)}，${pct(ds.share_pos)}的公司PledgePre大于0。Post_{t}在2018年及以后取1。`);

H('5.5.2　第一阶段：新规是否降低了高质押公司的质押风险', HeadingLevel.HEADING_3);
EQ('Y_{i,t} = δ_{0} + δ_{1}PledgePre_{i}×Post_{t} + δ_{2}Controls_{i,t} + λ_{t} + μ_{i} + ε_{i,t}', '5-6');
P('其中Y分别取Pledge、Pressure与OREC。以Pledge为被解释变量时存在均值回归问题，本文构造安慰剂队列：以2012—2013年平均质押比例为处理强度、以2014年为虚拟政策时点，仅使用2012—2017年样本重复估计。');
P(`表5-11显示，新规实施后高质押公司的质押比例相对下降，δ_{1}为${f11[0].DID[0]}；但安慰剂队列中的对应系数为${f11[1].DID[0]}，绝对值更大。这说明高质押公司质押比例的回落并未超过均值回归的幅度，不能归因于新规。平仓压力的δ_{1}为${f11[2].DID[0]}，即新规实施后高质押公司的平仓压力相对上升，这与2018年股价普遍下跌、续作与补充质押空间收紧相一致；资金占用的δ_{1}为${f11[3].DID[0]}，不显著。安慰剂队列的窗口包含2015年股市异常波动，其估计值可能同时受该次冲击影响。`);
TABLE('表5-11　2018年新规的第一阶段检验', [
  ['变量', '(1)', '(2)', '(3)', '(4)'],
  ['被解释变量', 'Pledge', 'Pledge（安慰剂队列）', 'Pressure', 'OREC'],
  ...coef('PledgePre×Post', f11.map((c) => c.DID)),
  row('控制变量', '是', '是', '是', '是'), row('公司与年度固定效应', '是', '是', '是', '是'),
  row('样本期间', '2007—2025', '2012—2017', '2007—2025', '2007—2025'),
  row('调整R²', ...f11.map((c) => c.r2)), row('观测值', ...f11.map((c) => c.N)),
], { header: 2, note: '注：列(2)以2012—2013年平均质押比例为处理强度、2014年为虚拟政策时点，样本限于2012年前上市的公司。' + STD });

H('5.5.3　新规对现金持有的影响', HeadingLevel.HEADING_3);
P('判定规则（与第一阶段联合解读）：（1）若高质押公司的质押风险与资金占用相对下降且β_{1}显著为正，说明新规抑制了掏空；（2）若平仓压力相对上升且β_{1}显著为正，更符合风险规避渠道下的预防性储备；（3）若第一阶段不显著，β_{1}只作描述性报告。');
P(`表5-12显示，PledgePre×Post的系数在各列中均为负：仅控制公司与年度固定效应时为${m12[0].coef[0]}，加入行业×年度与省份×年度固定效应后为${m12[2].coef[0]}，剔除2018年后为${m12[3].coef[0]}，以二值处理变量估计为${m12[4].coef[0]}；不加入时变控制变量时为${DD.main_nocontrols[0]}。即新规实施后，处理强度越高的公司现金持有相对越低。这一结果不属于事先设定的任何一种情形：第一阶段显示平仓压力上升，而风险规避渠道预测现金应相对增加，实际观测到的是相对下降；资金占用未见变化，也不符合情形（1）。因此本文不将β_{1}解读为新规通过某一渠道改变现金政策的因果证据，只作描述性报告。结合2018年民营企业融资收紧的背景，高质押公司现金相对下降的一种可能解释是外部融资收紧下的现金消耗，但现有数据不足以检验这一解释。`);
TABLE('表5-12　2018年股票质押新规与现金持有', [
  ['变量', '(1)', '(2)', '(3)', '(4)', '(5)'],
  ...coef('PledgePre×Post', [m12[0].coef, m12[1].coef, m12[2].coef, m12[3].coef, null]),
  ...coef('Treat×Post', [null, null, null, null, m12[4].coef]),
  row('控制变量', '是', '是', '是', '是', '是'), row('公司固定效应', '是', '是', '是', '是', '是'),
  row('年度固定效应', '是', '否', '否', '否', '否'),
  row('行业×年度固定效应', '否', '是', '是', '是', '是'), row('省份×年度固定效应', '否', '否', '是', '是', '是'),
  row('剔除2018年', '否', '否', '否', '是', '否'),
  row('调整R²', ...m12.map((c) => c.r2)), row('观测值', ...m12.map((c) => c.N)),
], { note: '注：被解释变量为Cash；列(5)以PledgePre是否高于样本中位数定义Treat。' + STD });

H('5.5.4　动态效应与平行趋势', HeadingLevel.HEADING_3);
EQ('Cash_{i,t} = Σ_{k≠2017} θ_{k}PledgePre_{i}×1(t=k) + Controls_{i,t} + λ_{t} + μ_{i} + ε_{i,t}', '5-7');
const wald = DD.event_pre_wald;
P(`图5-1报告θ_{k}及其95%置信区间。2007—2015年的系数在5%水平上均不显著，联合检验的Wald统计量为${Number(wald.statistic).toFixed(2)}（p=${f3(wald.pvalue)}），未能拒绝政策前系数全部为零的原假设。但需要如实指出，2007—2011年的系数多在0.02—0.03之间，此后逐步下降至基期附近，政策前存在一定的下行趋势，新规后的负向系数可能部分反映这一趋势的延续。按开题报告的预案，本文加入PledgePre与线性时间趋势的交乘项重新估计：仅控制公司与年度固定效应时，PledgePre×Post变为${tr[0].DID[0]}${tr[0].DID[1]}，不再显著；同时加入行业×年度与省份×年度固定效应时为${tr[1].DID[0]}${tr[1].DID[1]}。新规效应的估计对趋势设定较为敏感，这进一步支持仅对其作描述性解读。`);
IMG('fig5-1_event.png', '图5-1　2018年新规的动态效应', 560, 302);
NOTE('注：圆点为θ_{k}的点估计，竖线为95%置信区间（公司层面聚类）；2017年为基期；控制变量与公司、年度固定效应同表5-12列(1)。');

H('5.5.5　安慰剂检验', HeadingLevel.HEADING_3);
const pf_ = DD.placebo_fake;
P(`一是虚构政策时点：仅使用2018年以前的样本，以2014年、2015年为虚拟政策时点，处理强度相应取前两年均值，估计系数分别为${pf_[0].coef[0]}${pf_[0].coef[1]}与${pf_[1].coef[0]}${pf_[1].coef[1]}，均不显著。二是随机置换处理强度：将PledgePre在公司间随机重新分配${pp.n}次并重新估计（图5-2），置换系数均值为${f4(pp.mean)}、标准差为${f4(pp.sd)}；真实估计值${f4(pp.true)}位于置换分布的${pct(pp.pctile_true)}分位，绝对值不小于真实值的置换结果占${pct(pp.share_abs_ge_true)}。这说明表5-12列(1)的系数不太可能由处理强度的随机分配产生，但这一检验不能排除前述政策前趋势的影响。`);
IMG('fig5-2_placebo.png', '图5-2　随机置换处理强度的安慰剂检验', 560, 284);

H('5.5.6　补充检验：省级纾困计划', HeadingLevel.HEADING_3);
P('以公司注册地省份的地方政府纾困基金设立时点构造交错处理变量，采用Callaway和Sant’Anna（2021）的估计量，并以省份层面聚类与野自助法推断。【待补：各省（区、市）地方政府纾困基金设立时间须按毛捷和管星华（2022）原文提供，本文不作推断或补全；表5-13暂未估计。】');
TABLE('表5-13　省级纾困计划与现金持有', [
  ['', '(1) 全样本', '(2) 高PledgePre', '(3) 低PledgePre', '(4) ReliefInt'],
  ...coef('ATT／系数', [NA, NA, NA, NA]),
  row('估计方法', 'CS(2021)', 'CS(2021)', 'CS(2021)', '双向固定效应'),
  row('推断方法', '省份聚类＋野自助', '省份聚类＋野自助', '省份聚类＋野自助', '省份聚类＋野自助'),
  row('处理省份数／对照省份数', NA, NA, NA, NA), row('观测值', NA, NA, NA, NA),
], { note: '注：纾困时点数据未提供，未能估计。' });

// ---------- 5.6 ----------
H('5.6　被解释变量的计量可靠性', HeadingLevel.HEADING_2);
P('杨国超等（2025）发现账面现金可能被虚增。若虚增现金集中发生在高质押公司，β_{1}偏向正值；初步结果为负，现金操纵更可能削弱而非制造负向结论，但仍需检验。拟采用的做法包括：以非受限现金Cash3替代Cash；剔除“存贷双高”样本；剔除因货币资金相关会计违规被处罚的公司；控制受限资金占比RestCash；以资金收益率CashRet为被解释变量。【待补：使用受限的货币资金、利息收入、有息负债与“存贷双高”的判定口径（杨国超等，2025原文）、货币资金相关违规处罚记录均未提供，表5-14暂未估计。】');
TABLE('表5-14　被解释变量计量可靠性检验', [
  ['变量', '(1)', '(2)', '(3)', '(4)', '(5)'],
  ['被解释变量', 'Cash3', 'Cash', 'Cash', 'Cash', 'CashRet'],
  ['样本／设定', '全样本', '剔除存贷双高', '剔除违规公司', '控制RestCash', '全样本'],
  ...coef('Pledge', [NA, NA, NA, NA, NA]),
  row('控制变量', '是', '是', '是', '是', '是'), row('公司与年度固定效应', '是', '是', '是', '是', '是'),
  row('调整R²', NA, NA, NA, NA, NA), row('观测值', NA, NA, NA, NA, NA),
], { header: 3, note: '注：所需数据未提供，未能估计。' });

// ---------- 5.7 ----------
const cx = RB.t5_15_capex;
H('5.7　拓展分析：股权质押与企业投资', HeadingLevel.HEADING_2);
P('开题报告原设想检验质押是否“通过提高现金储备”挤出投资，而本文结果显示质押与现金持有负相关，这一前提不成立，因此本节直接检验质押对企业投资的影响。');
P(`表5-15列(1)显示，Pledge对资本支出Capex的系数为${cx.coef[0]}${cx.coef[1]}，不显著，未发现质押伴随资本支出变化的证据。研发投入与Richardson（2006）投资效率模型所需数据尚未提供。【待补：研发支出、折旧与摊销、处置长期资产收回的现金、取得子公司支付的现金，用于列(2)—(4)。】`);
TABLE('表5-15　股权质押与企业投资', [
  ['变量', '(1) Capex', '(2) RD', '(3) 过度投资', '(4) 投资不足'],
  ...coef('Pledge', [cx.coef, NA, NA, NA]),
  row('控制变量', '是', '是', '是', '是'), row('公司与年度固定效应', '是', '是', '是', '是'),
  row('调整R²', cx.r2, NA, NA, NA), row('观测值', cx.N, NA, NA, NA),
], { note: '注：列(2)—(4)所需数据未提供，未能估计。' + CTRLNOTE + STD });

// ---------- 5.8 ----------
const r16 = RB.t5_16, r17 = RB.t5_17, r18 = RB.t5_18;
H('5.8　稳健性检验与内生性处理', HeadingLevel.HEADING_2);
H('5.8.1　替换核心变量', HeadingLevel.HEADING_3);
P(`以是否存在质押Pledge_Dum、占总股本口径的质押比例Pledge_Ratio2与明细表口径的质押比例替换解释变量，系数分别为${r16.Pledge_Dum.coef[0]}、${r16.Pledge_Ratio2.coef[0]}与${r16.Pledge_det.coef[0]}，均显著为负。以Cash2替换被解释变量所需的交易性金融资产数据尚未提供。`);
TABLE('表5-16　稳健性检验：替换核心变量', [
  ['变量', '(1)', '(2)', '(3)', '(4)'],
  ['替换内容', 'Cash2', 'Pledge_Dum', 'Pledge_Ratio2', '明细表口径'],
  ...coef('质押变量', [NA, r16.Pledge_Dum.coef, r16.Pledge_Ratio2.coef, r16.Pledge_det.coef]),
  row('控制变量', '是', '是', '是', '是'), row('公司与年度固定效应', '是', '是', '是', '是'),
  row('调整R²', NA, r16.Pledge_Dum.r2, r16.Pledge_Ratio2.r2, r16.Pledge_det.r2),
  row('观测值', NA, r16.Pledge_Dum.N, r16.Pledge_Ratio2.N, r16.Pledge_det.N),
], { header: 2, note: '注：列(1)缺交易性金融资产数据，未能估计。质押比例按统计表逐笔变动累加推算，累加结果大于1（漏记解押）或小于0（残差）的截取至[0,1]；明细表口径同样处理。' + STD });

H('5.8.2　调整样本与设定', HeadingLevel.HEADING_3);
P(`剔除2008年、2015年与2020年后系数为${r17.drop_crisis.coef[0]}；剔除上市当年及其后两年的观测后为${r17.drop_first3.coef[0]}；改为公司与行业×年度双向聚类后为${r17.twoway.coef[0]}${r17.twoway.coef[1]}，结论不变。加入现金股利所需数据尚未提供。`);
TABLE('表5-17　稳健性检验：调整样本与设定', [
  ['变量', '(1)', '(2)', '(3)', '(4)'],
  ['调整内容', '加入Div', '剔除2008、2015、2020年', '剔除上市前三年', '双向聚类'],
  ...coef('Pledge', [NA, r17.drop_crisis.coef, r17.drop_first3.coef, r17.twoway.coef]),
  row('控制变量', '是', '是', '是', '是'), row('公司与年度固定效应', '是', '是', '是', '是'),
  row('调整R²', NA, r17.drop_crisis.r2, r17.drop_first3.r2, r17.twoway.r2),
  row('观测值', NA, r17.drop_crisis.N, r17.drop_first3.N, r17.twoway.N),
], { header: 2, note: '注：列(1)缺现金股利数据，未能估计；列(4)括号内为公司与行业×年度双向聚类标准误。' + STD });

H('5.8.3　公司生命周期与上市募集资金', HeadingLevel.HEADING_3);
P('需要排除的替代解释是：公司上市时募集大量现金，此后随投资逐年消耗，同时大股东质押比例往往随上市时间推移而上升，两者在同一公司内部同时变化，即使没有因果联系也会形成负相关。');
P(`表5-18按上市年限分组估计。上市第4—6年与第7年及以后两组的系数分别为${r18['4-6'].coef[0]}与${r18['7+'].coef[0]}，均不显著；上市第1—3年组为${r18['1-3'].coef[0]}，显著为正，但该组在公司固定效应下仅有${r18['1-3'].N}个有效观测，估计不够稳定。值得注意的是，全样本系数显著为负，而各生命周期阶段内部均未发现负向关系，说明基准回归的负向关系主要来自公司跨越不同上市阶段时质押与现金的同步变化。这与上市募集资金逐年消耗的解释相符，但并不能证明这一解释。需要指出，5.4.1中Pledge×Age^{c}显著为正，意味着上市年限越短、负向关系越强，而本节上市第1—3年组的系数为正，二者方向并不一致：前者利用全样本的公司内变化，后者仅利用各阶段内部的变化，且该组样本量较小。上市初期的关系究竟如何，须结合募集资金数据进一步检验。直接检验需要IPO募集资金数据。【待补：IPO募集资金净额，用于列(4)；该项结果将决定基准结论的解读方式。】`);
TABLE('表5-18　公司生命周期与上市募集资金', [
  ['变量', '(1) 上市1—3年', '(2) 上市4—6年', '(3) 上市7年及以上', '(4) 全样本'],
  ...coef('Pledge', [r18['1-3'].coef, r18['4-6'].coef, r18['7+'].coef, NA]),
  row('IPO募资比例×上市年数', '否', '否', '否', '是'),
  row('控制变量', '是', '是', '是', '是'), row('公司与年度固定效应', '是', '是', '是', '是'),
  row('调整R²', r18['1-3'].r2, r18['4-6'].r2, r18['7+'].r2, NA),
  row('观测值', r18['1-3'].N, r18['4-6'].N, r18['7+'].N, NA),
], { note: '注：上市当年记为第1年；观测值为剔除单例固定效应后的有效样本。列(4)缺IPO募集资金数据，未能估计。' + STD });

const lg = RB.t5_19_lag, ps = RB.t5_19_psm, iv = RB.t5_19_iv, ivf = RB.iv_first, pn = RB.psm_n;
const maxAfter = Math.max(...RB.psm_balance.map((b) => Math.abs(b.after)));
H('5.8.4　内生性处理', HeadingLevel.HEADING_3);
P(`一是将Pledge滞后一期，系数为${lg.coef[0]}${lg.coef[1]}。二是以Pledge_Dum为处理变量、以控制变量为协变量逐年估计logit倾向得分，进行1:1有放回近邻匹配（卡尺0.05）：${pn.treated_total.toLocaleString('en-US')}个处理组观测中有${pn.treated_matched.toLocaleString('en-US')}个匹配成功，对应${pn.controls_unique.toLocaleString('en-US')}个不重复的对照观测；匹配后各协变量标准化偏差的绝对值均低于${Math.ceil(maxAfter)}%，在匹配样本中系数为${ps.coef[0]}${ps.coef[1]}。三是以同行业同年度（剔除本公司）平均质押比例为工具变量进行两阶段最小二乘估计，第一阶段系数为${ivf.coef[0]}，Kleibergen-Paap rk Wald F统计量为${Number(ivf.cluster_robust_F).toFixed(2)}；第二阶段系数为${iv.coef[0]}${iv.coef[1]}，约为OLS估计（表5-3列(2)）的${Math.round(parseFloat(iv.coef[0]) / parseFloat(t6[1].coef[0]))}倍。如开题报告所述，该工具变量的排他性约束较弱，行业层面的共同冲击可能同时影响质押与现金，这一量级差异也提示其结果不宜作为因果推断依据，仅作辅助参考。`);
TABLE('表5-19　内生性处理', [
  ['变量', '(1) 滞后一期', '(2) PSM样本', '(3) 2SLS'],
  ...coef('Pledge／L.Pledge', [lg.coef, ps.coef, iv.coef]),
  row('Kleibergen-Paap F统计量', '', '', Number(ivf.cluster_robust_F).toFixed(2)),
  row('控制变量', '是', '是', '是'), row('公司与年度固定效应', '是', '是', '是'),
  row('观测值', lg.N, ps.N, iv.N),
], { note: '注：列(3)报告第二阶段结果；单一内生变量、单一工具变量时，Kleibergen-Paap rk Wald F等于第一阶段工具变量聚类稳健t统计量的平方。' + STD });

// ---------- 附表一：复现对照 ----------
H('附表一　开题报告表6、表7的复现对照（不入正文）', HeadingLevel.HEADING_2);
const p6 = [['-0.0335***', '0.505', '50,737'], ['-0.0165***', '0.613', '50,737'], ['-0.0125**', '0.617', '50,730'], ['-0.0136**', '0.615', '50,737']];
TABLE('附表1-1　表6复现', [
  ['列', '开题报告：系数', '复现：系数', '开题报告：调整R²', '复现：调整R²', '开题报告：观测值', '复现：观测值'],
  ...t6.map((c, i) => [`(${i + 1})`, p6[i][0], c.coef[0], p6[i][1], c.r2, p6[i][2], c.N]),
], { first: 700 });
const p7 = [['-0.1808***', '0.1699***', '0.53', '6,912'], ['-0.1683***', '0.1356***', '0.62', '50,954'], ['-0.0262', '0.0268', '—', '6,839'], ['-0.0456***', '0.0327**', '—', '50,730']];
TABLE('附表1-2　表7复现', [
  ['列', '开题：Pledge', '复现：Pledge', '开题：Pledge²', '复现：Pledge²', '复现：拐点', '复现：U型', '复现：观测值'],
  ...BL.t7.map((c, i) => [`(${i + 1})`, p7[i][0], c.b1[0], p7[i][1], c.b2[0], c.holds ? c.tp.toFixed(2) : '—', c.holds ? '成立' : '不成立', c.N]),
], { first: 600, note: `注：复现样本${BL.N.toLocaleString('en-US')}个观测、${BL.firms.toLocaleString('en-US')}家公司。描述性统计中Pledge均值${f3(BL.t4.Pledge.mean)}（开题0.216）、Pledge_Dum均值${f3(BL.t4.Pledge_Dum.mean)}（开题0.388）、Cash均值${f3(BL.t4.Cash.mean)}（开题0.244）。差异来源包括：样本筛选细节、缩尾范围，以及统计表累加结果超出[0,1]时的处理方式。` });

const doc = new Document({
  styles: {
    default: { document: { run: { font: { ascii: EN, hAnsi: EN, eastAsia: CN }, size: 24 } } },
    paragraphStyles: [1, 2, 3].map((n) => ({
      id: `Heading${n}`, name: `Heading ${n}`, basedOn: 'Normal', next: 'Normal', quickFormat: true,
      run: { color: '000000', bold: true, font: { ascii: EN, hAnsi: EN, eastAsia: CN_H } }, paragraph: { outlineLevel: n - 1 },
    })),
  },
  sections: [{ properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1800, right: 1800 } } }, children: body }],
});
const out = path.join(__dirname, '第五章续-实证检验结果稿.docx');
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(out, b); console.log('written', out); });
