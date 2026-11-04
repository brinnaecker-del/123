// 市调大赛答辩 PPT。数字全部来自 output/numbers.json 与 output/*.csv（先运行 analysis.py）
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require(process.env.PPTX_SKILL + "/scripts/apply_theme.js");

const OUT = path.join(__dirname, "output");
const N = JSON.parse(fs.readFileSync(path.join(OUT, "numbers.json"), "utf8"));
const csv = (f) => {
  const L = fs.readFileSync(path.join(OUT, f), "utf8").replace(/^﻿/, "").trim().split(/\r?\n/);
  const h = L[0].split(",");
  return L.slice(1).map((l) => Object.fromEntries(l.split(",").map((v, i) => [h[i], v])));
};
const conc = (() => {
  const L = fs.readFileSync(path.join(__dirname, "..", "jea", "output", "T_concentration_74.csv"), "utf8").trim().split(/\r?\n/).slice(1);
  return L.map((l) => l.split(",").map(Number));
})();
const T = N.tiers, M = N.macro;
const pct = (x, d = 0) => (x * 100).toFixed(d) + "%";
const ct = csv("T6_pref_by_tier.csv");
const psu = csv("T7_sample_psu.csv");

const THEME = {
  name: "Highland Market", headFontFace: "Microsoft YaHei", bodyFontFace: "Microsoft YaHei",
  colors: { dk1: "231A1B", lt1: "FFFFFF", dk2: "5A4E4F", lt2: "F3EFEA",
    accent1: "8C2F39", accent2: "D08C3A", accent3: "3E7C6B", accent4: "4A5A78", accent5: "9AA0A6", accent6: "C9B79C",
    hlink: "4A5A78", folHlink: "8C2F39" },
};
const HEX = THEME.colors;
const TIERC = [HEX.accent1, HEX.accent2, HEX.accent3, HEX.accent4];

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "雪域县域，消费何往";
const C = pres.SchemeColor;

pres.defineSlideMaster({
  title: "DARK", background: { color: HEX.dk1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.3, w: 11.7, h: 1.4, fontSize: 44, bold: true, color: C.background1, valign: "bottom", align: "left" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 3.8, w: 11.7, h: 1.2, fontSize: 20, color: C.accent6, valign: "top" }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT", background: { color: HEX.lt1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 12.1, h: 0.85, fontSize: 30, bold: true, color: C.text1, valign: "middle", align: "left", margin: 0 }, text: "" } },
  ],
  slideNumber: { x: 12.4, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color: HEX.accent5 },
});

const chartBase = () => ({
  catAxisLabelColor: HEX.dk2, valAxisLabelColor: HEX.dk2, catAxisLabelFontSize: 12, valAxisLabelFontSize: 11,
  catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt",
  dataLabelFontSize: 11, dataLabelColor: HEX.dk1, valGridLine: { color: "E6E1DA", size: 0.5 }, catGridLine: { style: "none" },
  titleFontFace: "+mn-lt", titleFontSize: 14, titleColor: HEX.dk2, legendFontFace: "+mn-lt", legendFontSize: 12,
});
let secName = "";
function slide(title, sec) {
  if (sec && sec !== secName) { pres.addSection({ title: sec }); secName = sec; }
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: secName });
  s.addText(title, { placeholder: "title" });
  return s;
}
function txt(s, text, o) { s.addText(text, Object.assign({ isTextBox: true, fontSize: 16, color: C.text1, valign: "top", margin: 0 }, o)); }
function card(s, x, y, w, h, fill, name) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fill }, line: { color: fill }, objectName: name });
}
function stat(s, x, y, w, big, small, color) {
  txt(s, big, { x, y, w, h: 1.0, fontSize: 48, bold: true, color: color || C.accent1 });
  txt(s, small, { x, y: y + 1.05, w, h: 0.9, fontSize: 15, color: C.text2 });
}

// 1 封面
pres.addSection({ title: "开场" }); secName = "开场";
let s = pres.addSlide({ masterName: "DARK", sectionTitle: "开场" });
s.addText("雪域县域，消费何往", { placeholder: "title" });
s.addText("西藏73区县市场潜力分层与居民消费需求调查", { placeholder: "body" });
txt(s, "“正大杯”第十七届全国大学生市场调查与分析大赛 · 本科组", { x: 0.8, y: 6.3, w: 11, h: 0.5, fontSize: 14, color: C.accent5 });
s.addNotes("开场：一句话介绍——我们先用二手数据摸清73个区县的市场底数，再用这套分层去设计入户调查。");

// 2 背景：三个数字
s = slide("收入上台阶，县域消费正在打开", "背景与问题");
stat(s, 0.7, 1.7, 3.8, (M.gdp_2025 / M.gdp_2016).toFixed(1) + "倍", `地区生产总值\n${M.gdp_2016.toFixed(0)}→${M.gdp_2025.toFixed(0)}亿元（2016—2025）`);
stat(s, 4.75, 1.7, 3.8, pct(M.rural_rel_2025, 1), `农村居民收入相当于全国农村水平\n2016年为${pct(M.rural_rel_2016, 1)}`, C.accent2);
stat(s, 8.8, 1.7, 3.8, (M.tour_2025 / 1e4).toFixed(2) + "亿", `人次游客（2025）\n约为常住人口的${M.tour_per_res_2025.toFixed(0)}倍`, C.accent3);
s.addChart(pres.charts.LINE, [{ name: "农村居民人均可支配收入（元）", labels: ["2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025"],
  values: [9094, 10330, 11450, 12951, 14598, 16935, 18209, 19924, 21578, 23184] }],
  Object.assign(chartBase(), { x: 0.7, y: 4.1, w: 11.9, h: 2.7, chartColors: [HEX.accent2], lineSize: 3, lineDataSymbolSize: 7,
    showValue: true, dataLabelPosition: "t", showTitle: true, title: "农村居民人均可支配收入（元）", showLegend: false, valAxisHidden: true, valGridLine: { style: "none" } }));
s.addNotes("资料来源：历年西藏统计公报。收入接近全国平均，消费结构开始升级。");

// 3 问题
s = slide("但县域市场的“底数”和“需求”都不清楚", "背景与问题");
card(s, 0.7, 1.6, 5.8, 3.4, HEX.lt2, "card-left");
card(s, 6.85, 1.6, 5.8, 3.4, HEX.lt2, "card-right");
txt(s, "底数：哪里有市场？", { x: 1.0, y: 1.85, w: 5.2, h: 0.6, fontSize: 22, bold: true, color: C.accent1 });
txt(s, [{ text: "74个县级单位差异极大", options: { bullet: true, breakLine: true } },
  { text: "已有测度多停在全区、地市一级", options: { bullet: true, breakLine: true } },
  { text: "→ 用73区县面板数据回答", options: { bullet: false, bold: true } }],
  { x: 1.0, y: 2.6, w: 5.2, h: 3.0, fontSize: 18, paraSpaceAfter: 10 });
txt(s, "需求：市场要什么？", { x: 7.15, y: 1.85, w: 5.2, h: 0.6, fontSize: 22, bold: true, color: C.accent3 });
txt(s, [{ text: "居民买什么、在哪里买", options: { bullet: true, breakLine: true } },
  { text: "线上消费为什么用或不用", options: { bullet: true, breakLine: true } },
  { text: "→ 用入户问卷回答", options: { bullet: false, bold: true } }],
  { x: 7.15, y: 2.6, w: 5.2, h: 3.0, fontSize: 18, paraSpaceAfter: 10 });
card(s, 0.7, 5.4, 11.95, 1.2, HEX.dk1, "key");
txt(s, "关键设计：二手数据的分层结果，直接作为一手调查的抽样框", { x: 1.0, y: 5.4, w: 11.4, h: 1.2, fontSize: 22, bold: true, color: C.background1, valign: "middle" });

// 4 技术路线
s = slide("技术路线：四步走", "方案设计");
const steps = [["1", "市场底数", "73区县面板\n熵权指数 + K均值聚类"], ["2", "抽样设计", "四类市场为层\n二阶段分层PPS"],
  ["3", "需求调查", `8个样本县\n计划${N.n_issue_alloc}份问卷`], ["4", "分类建议", "按市场类型\n给出网点与物流方案"]];
steps.forEach(([n, h, b], i) => {
  const x = 0.7 + i * 3.1;
  card(s, x, 1.9, 2.75, 3.2, i < 2 ? HEX.lt2 : "F7F4F0", "step" + n);
  s.addShape(pres.shapes.OVAL, { x: x + 0.3, y: 2.15, w: 0.8, h: 0.8, fill: { color: TIERC[i] }, line: { color: TIERC[i] }, objectName: "num" + n });
  txt(s, n, { x: x + 0.3, y: 2.15, w: 0.8, h: 0.8, fontSize: 24, bold: true, color: C.background1, align: "center", valign: "middle" });
  txt(s, h, { x: x + 0.3, y: 3.15, w: 2.2, h: 0.6, fontSize: 22, bold: true });
  txt(s, b, { x: x + 0.3, y: 3.85, w: 2.3, h: 1.4, fontSize: 15, color: C.text2 });
});
txt(s, "已完成：第1、2步　｜　寒假实施：第3步　｜　3月完成：第4步", { x: 0.7, y: 6.0, w: 11.9, h: 0.5, fontSize: 16, color: C.text2 });

// 5 指标与熵权
s = slide("六项指标衡量市场潜力，权重由数据决定", "市场底数");
const wk = Object.keys(N.weights);
s.addChart(pres.charts.BAR, [{ name: "熵权", labels: wk, values: wk.map((k) => +N.weights[k].toFixed(3)) }],
  Object.assign(chartBase(), { x: 0.6, y: 1.5, w: 7.0, h: 5.3, barDir: "bar", chartColors: [HEX.accent1], showValue: true, dataLabelPosition: "outEnd",
    dataLabelFormatCode: "0.000", showLegend: false, valAxisHidden: true, valGridLine: { style: "none" }, catAxisLabelFontSize: 14, catAxisOrientation: "maxMin" }));
txt(s, [{ text: "熵权法", options: { bold: true, breakLine: true } },
  { text: "指标在各县间差异越大，权重越高，不依赖专家打分", options: { breakLine: true } },
  { text: " ", options: { breakLine: true } },
  { text: "经济规模、财政自给率权重最高", options: { bold: true, breakLine: true } },
  { text: "成长速度权重最低：各县增速普遍较快，区分力弱", options: { breakLine: true } },
  { text: " ", options: { breakLine: true } },
  { text: "数据缺口", options: { bold: true, breakLine: true } },
  { text: "区县无社零总额、居民收入——正是入户调查要补的", options: {} }],
  { x: 8.0, y: 1.7, w: 4.7, h: 5.0, fontSize: 16, paraSpaceAfter: 4 });

// 6 集中度
s = slide("市场“头重脚轻”，但正在向外扩散", "市场底数");
s.addChart(pres.charts.LINE, [
  { name: "城关区占74区县GDP", labels: conc.map((r) => String(r[0])), values: conc.map((r) => +(r[2] * 100).toFixed(1)) },
  { name: "GDP前五位区县合计", labels: conc.map((r) => String(r[0])), values: conc.map((r) => +(r[4] * 100).toFixed(1)) }],
  Object.assign(chartBase(), { x: 0.6, y: 1.5, w: 8.0, h: 5.3, chartColors: [HEX.accent1, HEX.accent4], lineSize: 3, lineDataSymbolSize: 7,
    showValue: true, dataLabelPosition: "t", dataLabelFormatCode: "0.0", showLegend: true, legendPos: "b", valAxisMinVal: 0, valAxisMaxVal: 50,
    valAxisTitle: "%", showValAxisTitle: true, valAxisTitleFontFace: "+mn-lt" }));
stat(s, 9.0, 1.9, 3.7, pct(N.chengguan_share_2024, 1), "2024年城关区一个区\n占74区县GDP");
stat(s, 9.0, 4.2, 3.7, "↓" + ((N.chengguan_share_2016 - N.chengguan_share_2024) * 100).toFixed(1), "个百分点（2016—2024年）\n增长向外围区县扩散", C.accent3);

// 7 排名
s = slide("潜力前十：拉萨近郊领跑，地市驻地紧随", "市场底数");
const top = N.top10.slice().reverse();
s.addChart(pres.charts.BAR, [{ name: "市场潜力指数", labels: top.map((r) => `${r[0]}（${r[1].replace("地区", "").replace("市", "")}）`), values: top.map((r) => +r[2].toFixed(1)) }],
  Object.assign(chartBase(), { x: 0.6, y: 1.4, w: 7.6, h: 5.5, barDir: "bar", chartColors: [HEX.accent2], showValue: true, dataLabelPosition: "outEnd",
    dataLabelFormatCode: "0.0", showLegend: false, valAxisHidden: true, valGridLine: { style: "none" }, catAxisLabelFontSize: 13, valAxisMaxVal: 115 }));
txt(s, [{ text: "第1—2位", options: { bold: true, color: C.accent1, breakLine: true } },
  { text: "堆龙德庆区、墨竹工卡县：拉萨近郊，园区与矿业带动", options: { breakLine: true } },
  { text: " ", options: { breakLine: true } },
  { text: "第3—8位", options: { bold: true, color: C.accent2, breakLine: true } },
  { text: "全部是地市（地区）政府驻地——拉萨以外的主要市场节点", options: { breakLine: true } },
  { text: " ", options: { breakLine: true } },
  { text: "末位", options: { bold: true, color: C.accent4, breakLine: true } },
  { text: N.bottom5.map((r) => r[0]).join("、") + "：高海拔牧区小县", options: {} }],
  { x: 8.6, y: 1.6, w: 4.2, h: 5.2, fontSize: 16, paraSpaceAfter: 4 });

// 8 四类市场
s = slide("K均值聚类：73个区县分为四类市场", "市场底数");
const desc = {
  1: ["人均产出最高", "品牌门店、中高端消费"], 2: ["地市驻地，靠本地经济", "区域仓储与配送节点"],
  3: ["人均公共支出最高", "单位团购、配送时效"], 4: ["人口最多，产出最低", "快递到村、双语电商"]};
[1, 2, 3, 4].forEach((t, i) => {
  const v = T[t], x = 0.6 + i * 3.1;
  card(s, x, 1.5, 2.85, 5.3, HEX.lt2, "tier" + t);
  s.addShape(pres.shapes.OVAL, { x: x + 0.25, y: 1.75, w: 0.45, h: 0.45, fill: { color: TIERC[i] }, line: { color: TIERC[i] }, objectName: "dot" + t });
  txt(s, v.name, { x: x + 0.8, y: 1.72, w: 2.0, h: 0.5, fontSize: 18, bold: true, valign: "middle" });
  txt(s, `${v.n.toFixed(0)}个县`, { x: x + 0.25, y: 2.4, w: 2.4, h: 0.8, fontSize: 36, bold: true, color: TIERC[i] });
  txt(s, [{ text: `人口占 ${pct(v.pop_share)}`, options: { breakLine: true } },
    { text: `产出占 ${pct(v.gdp_share)}`, options: { breakLine: true } },
    { text: `人均产出 ${(v.gdp_pc / 1e4).toFixed(1)}万元`, options: { breakLine: true } },
    { text: `财政自给率 ${pct(v.ssr, 1)}`, options: {} }],
    { x: x + 0.25, y: 3.3, w: 2.45, h: 1.6, fontSize: 15, color: C.text2, paraSpaceAfter: 2 });
  txt(s, desc[t][0], { x: x + 0.25, y: 5.05, w: 2.45, h: 0.45, fontSize: 15, bold: true });
  txt(s, desc[t][1], { x: x + 0.25, y: 5.5, w: 2.45, h: 0.9, fontSize: 14, color: C.text2 });
});
s.addNotes(`轮廓系数 k=3—6 为 ${Object.values(N.silhouette).map((v) => v.toFixed(3)).join("、")}，k=4 最高。`);

// 9 错位
s = slide("人口与产出错位：最大的升级空间在农牧区", "市场底数");
s.addChart(pres.charts.BAR, [
  { name: "人口占比", labels: [1, 2, 3, 4].map((t) => T[t].name), values: [1, 2, 3, 4].map((t) => +(T[t].pop_share * 100).toFixed(1)) },
  { name: "产出占比", labels: [1, 2, 3, 4].map((t) => T[t].name), values: [1, 2, 3, 4].map((t) => +(T[t].gdp_share * 100).toFixed(1)) }],
  Object.assign(chartBase(), { x: 0.6, y: 1.5, w: 8.0, h: 5.3, barDir: "col", barGrouping: "clustered", chartColors: [HEX.accent4, HEX.accent2],
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0", showLegend: true, legendPos: "b", valAxisHidden: true, valGridLine: { style: "none" } }));
stat(s, 9.0, 1.9, 3.7, pct(T[4].pop_share), "的人口在农牧基础型县", C.accent4);
stat(s, 9.0, 4.2, 3.7, pct(T[4].gdp_share), "的产出在这些县\n人均产出仅为核心型的" + pct(T[4].gdp_pc / T[1].gdp_pc), C.accent2);

// 10 地市内部差异
s = slide("同一地市内部差异大，不能“一刀切”", "市场底数");
s.addChart(pres.charts.BAR, [1, 2, 3, 4].map((t) => ({ name: T[t].name, labels: ct.map((r) => r.pref_cn), values: ct.map((r) => +(r[T[t].name] || 0)) })),
  Object.assign(chartBase(), { x: 0.6, y: 1.5, w: 8.4, h: 5.3, barDir: "bar", barGrouping: "stacked", chartColors: TIERC, showValue: true,
    dataLabelPosition: "ctr", dataLabelColor: "FFFFFF", dataLabelFormatCode: "0;;;", showLegend: true, legendPos: "b", valAxisHidden: true, valGridLine: { style: "none" } }));
txt(s, [{ text: "日喀则18个区县", options: { bold: true, breakLine: true } },
  { text: "农牧基础型9个、财政支撑型8个，地市中心型只有桑珠孜区", options: { breakLine: true } },
  { text: " ", options: { breakLine: true } },
  { text: "阿里7县", options: { bold: true, breakLine: true } },
  { text: "6个为财政支撑型：小而稳的“公职型”市场", options: {} }],
  { x: 9.3, y: 1.8, w: 3.5, h: 4.8, fontSize: 16, paraSpaceAfter: 4 });

// 11 稳健性
s = slide("分层结果稳健：三项检验一致性均在0.74以上", "市场底数");
const R = N.robust_ari;
[["更换20个随机种子", R["20个随机种子_最低"], "最低值"], ["删去成长速度指标", R["去掉成长速度"], "五项指标重新聚类"],
  ["修正口径跳变", R["跳变县改用2020-24增速"], "噶尔、色尼改用2020—2024年增速"]].forEach(([h, v, d], i) => {
  const x = 0.6 + i * 4.1;
  card(s, x, 1.7, 3.8, 3.4, HEX.lt2, "rob" + i);
  txt(s, h, { x: x + 0.3, y: 1.95, w: 3.2, h: 0.5, fontSize: 18, bold: true });
  txt(s, v.toFixed(2), { x: x + 0.3, y: 2.6, w: 3.2, h: 1.2, fontSize: 54, bold: true, color: C.accent3 });
  txt(s, d, { x: x + 0.3, y: 3.95, w: 3.2, h: 0.9, fontSize: 14, color: C.text2 });
});
txt(s, "调整兰德指数：1 = 与基准分层完全一致。修正口径跳变后噶尔县类型最不稳定，入户调查不以其作为核心型代表。",
  { x: 0.6, y: 5.5, w: 12.1, h: 0.9, fontSize: 15, color: C.text2 });

// 12 抽样
s = slide(`二阶段分层PPS：8个样本县，${N.n_total_alloc}户有效样本`, "调查设计");
const rows = [["层级", "样本县", "地市", "人口（万）", "入样概率", "样本量"].map((h) => ({ text: h, options: { bold: true, fill: { color: HEX.lt2 } } }))]
  .concat(psu.map((r) => [r["层级"], r["区县"], r["地市"], r["户籍人口(万人)"].replace(".0", ""), (+r["入样概率"]).toFixed(3), r["本县样本量"]]));
s.addTable(rows, { x: 0.6, y: 1.5, w: 7.6, colW: [1.7, 1.5, 1.3, 1.1, 1.0, 1.0], fontSize: 13, color: HEX.dk1, border: { type: "solid", pt: 0.5, color: "D9D3CB" }, rowH: 0.5, valign: "middle", fontFace: "Microsoft YaHei" });
txt(s, [{ text: "样本量", options: { bold: true, breakLine: true } },
  { text: `n₀ = 1.96²×0.5×0.5 / 0.04² ≈ ${N.sample.n0.toFixed(0)}`, options: { breakLine: true } },
  { text: `× 设计效应1.5 → ${N.sample.n_eff}户`, options: { breakLine: true } },
  { text: `每层不少于150户 → ${N.n_total_alloc}户`, options: { breakLine: true } },
  { text: `÷ 应答率85% → 发放${N.n_issue_alloc}份`, options: { breakLine: true } },
  { text: " ", options: { breakLine: true } },
  { text: "第二阶段", options: { bold: true, breakLine: true } },
  { text: "县城社区、乡镇、行政村各约1/3，按户籍名册等距抽户", options: {} }],
  { x: 8.6, y: 1.6, w: 4.2, h: 5.2, fontSize: 15, paraSpaceAfter: 4 });

// 13 问卷与模型
s = slide("问卷六模块，以计划行为理论解释线上消费意愿", "调查设计");
const mods = ["A 家庭基本信息", "B 收入与消费结构", "C 购物渠道", "D 物流与支付", "E 线上消费意愿量表", "F 痛点与需求"];
mods.forEach((m, i) => {
  card(s, 0.6, 1.5 + i * 0.85, 4.0, 0.7, i === 4 ? HEX.accent1 : HEX.lt2, "mod" + i);
  txt(s, m, { x: 0.85, y: 1.5 + i * 0.85, w: 3.6, h: 0.7, fontSize: 16, bold: i === 4, valign: "middle", color: i === 4 ? C.background1 : C.text1 });
});
const nodes = [["态度", 5.6, 1.7], ["主观规范", 5.6, 3.4], ["知觉行为控制\n物流·网络·语言·支付", 5.6, 5.1]];
nodes.forEach(([n, x, y], i) => {
  card(s, x, y, 3.3, 1.2, HEX.lt2, "tpb" + i);
  txt(s, n, { x, y, w: 3.3, h: 1.2, fontSize: 16, bold: true, align: "center", valign: "middle" });
  const y0 = y + 0.6, y1 = 4.0;
  s.addShape(pres.shapes.LINE, { x: x + 3.3, y: Math.min(y0, y1), w: 1.0, h: Math.abs(y1 - y0), line: { color: HEX.dk2, width: 1.5, endArrowType: "triangle" }, flipV: y0 > y1, objectName: "arrow" + i });
});
card(s, 9.9, 3.4, 2.8, 1.2, HEX.accent3, "intent");
txt(s, "线上消费意愿", { x: 9.9, y: 3.4, w: 2.8, h: 1.2, fontSize: 18, bold: true, align: "center", valign: "middle", color: C.background1 });
txt(s, "H3：知觉行为控制在农牧基础型中作用最强（多群组结构方程检验）", { x: 5.6, y: 6.5, w: 7.2, h: 0.5, fontSize: 14, color: C.text2 });

// 14 实施与质控
s = slide("实施计划与质量控制", "调查设计");
const tl = [["11月", "选题、二手数据、问卷初稿"], ["12月", "预调查约50份、培训双语调查员"], ["1—2月", "寒假入户，8个样本县"], ["2月下旬", "清理、加权、建模"], ["3月底前", "报告与PPT，校赛提交"]];
s.addShape(pres.shapes.LINE, { x: 0.9, y: 2.35, w: 11.6, h: 0, line: { color: HEX.accent5, width: 2 }, objectName: "timeline" });
tl.forEach(([d, t], i) => {
  const x = 0.6 + i * 2.45;
  s.addShape(pres.shapes.OVAL, { x: x + 0.15, y: 2.15, w: 0.4, h: 0.4, fill: { color: i === 2 ? HEX.accent1 : HEX.accent4 }, line: { color: HEX.lt1 }, objectName: "tl" + i });
  txt(s, d, { x, y: 1.5, w: 2.3, h: 0.5, fontSize: 18, bold: true });
  txt(s, t, { x, y: 2.8, w: 2.2, h: 1.0, fontSize: 14, color: C.text2 });
});
const qc = [["电子问卷", "记录定位与作答时长，<5分钟剔除"], ["10%回访", "每名调查员随机抽查电话回访"], ["逻辑校验", "分项支出之和不超过总支出"], ["知情同意", "不收集姓名、身份证号"]];
qc.forEach(([h, b], i) => {
  const x = 0.6 + i * 3.1;
  card(s, x, 4.4, 2.85, 2.2, HEX.lt2, "qc" + i);
  txt(s, h, { x: x + 0.25, y: 4.6, w: 2.4, h: 0.5, fontSize: 18, bold: true, color: C.accent1 });
  txt(s, b, { x: x + 0.25, y: 5.2, w: 2.4, h: 1.2, fontSize: 14, color: C.text2 });
});

// 15 建议
s = slide("初步建议：按市场类型分类施策", "结论");
const adv = [["高产出核心型", "品牌门店、中高端与服务消费"], ["地市中心型", "区域仓储配送中心，辐射周边县"], ["财政支撑型", "提升配送时效，发展单位团购平台"], ["农牧基础型", "乡镇快递站、双语电商、支付培训"]];
adv.forEach(([h, b], i) => {
  const y = 1.5 + i * 1.25;
  s.addShape(pres.shapes.OVAL, { x: 0.7, y: y + 0.2, w: 0.6, h: 0.6, fill: { color: TIERC[i] }, line: { color: TIERC[i] }, objectName: "adv" + i });
  txt(s, h, { x: 1.6, y: y + 0.15, w: 3.0, h: 0.7, fontSize: 20, bold: true, valign: "middle" });
  txt(s, b, { x: 4.7, y: y + 0.15, w: 8.0, h: 0.7, fontSize: 18, valign: "middle", color: C.text2 });
});
txt(s, "以上建议将根据入户调查结果修订，未被数据支持的部分删去。", { x: 0.7, y: 6.5, w: 12, h: 0.5, fontSize: 14, color: C.accent1 });

// 16 结尾
pres.addSection({ title: "结束" });
s = pres.addSlide({ masterName: "DARK", sectionTitle: "结束" });
s.addText("先摸底数，再问需求", { placeholder: "title" });
s.addText("恳请各位评委批评指正", { placeholder: "body" });
txt(s, "不足：区县缺社零总额与居民收入数据；户籍人口精确到万人；入户只覆盖8个县", { x: 0.8, y: 6.2, w: 11.7, h: 0.6, fontSize: 14, color: C.accent5 });

(async () => {
  const f = path.join(__dirname, "答辩PPT.pptx");
  await pres.writeFile({ fileName: f });
  await applyTheme(f, THEME);
  console.log("ok");
})();
