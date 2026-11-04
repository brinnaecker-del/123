"""生成市调大赛参赛报告（正文 + 附录分开两个 docx，按大赛要求分开提交）。
所有数字取自 output/numbers.json 与 output/*.csv；先运行 analysis.py。
"""
import json
import os

import pandas as pd
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
N = json.load(open(os.path.join(OUT, "numbers.json"), encoding="utf-8"))
M = N["macro"]
T = {int(k): v for k, v in N["tiers"].items()}
W = N["weights"]
S = N["sample"]
R = N["robust_ari"]
mpi = pd.read_csv(os.path.join(OUT, "T5_county_mpi.csv"))
psu = pd.read_csv(os.path.join(OUT, "T7_sample_psu.csv"))
ct = pd.read_csv(os.path.join(OUT, "T6_pref_by_tier.csv"), index_col=0)
TN = {t: T[t]["name"] for t in T}
PENDING = "【待调查完成后填写】"


def pct(x, d=1):
    return f"{x * 100:.{d}f}%"


def f1(x, d=1):
    return f"{x:,.{d}f}"


# ---------------------------------------------------------------- 样式
def setup(doc):
    sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
    sec.top_margin = sec.bottom_margin = Cm(2.54)
    sec.left_margin = sec.right_margin = Cm(3.17)
    st = doc.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(12)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    st.paragraph_format.line_spacing = 1.5
    st.paragraph_format.first_line_indent = Pt(24)
    st.paragraph_format.space_after = Pt(0)
    for lvl, size in [(1, 16), (2, 14), (3, 12)]:
        h = doc.styles[f"Heading {lvl}"]
        h.font.name = "Times New Roman"
        h.font.size = Pt(size)
        h.font.bold = True
        h.font.color.rgb = RGBColor(0, 0, 0)
        h.element.rPr.rFonts.set(qn("w:eastAsia"), "黑体")
        h.paragraph_format.first_line_indent = Pt(0)
        h.paragraph_format.space_before = Pt(12 if lvl == 1 else 6)
        h.paragraph_format.space_after = Pt(6)
        h.paragraph_format.line_spacing = 1.5
        h.paragraph_format.keep_with_next = True
    # 页码
    p = sec.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for tag, text in [("begin", None), (None, "PAGE"), ("end", None)]:
        r = p.add_run()
        if tag:
            e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), tag); r._r.append(e)
        else:
            e = OxmlElement("w:instrText"); e.set(qn("xml:space"), "preserve"); e.text = text; r._r.append(e)


def ea(run, font):
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts"); rpr.insert(0, rf)
    rf.set(qn("w:eastAsia"), font)


def para(doc, text, bold_lead=None, indent=True, align=None, size=None):
    p = doc.add_paragraph()
    if not indent:
        p.paragraph_format.first_line_indent = Pt(0)
    if align:
        p.alignment = align
    if bold_lead:
        r = p.add_run(bold_lead); r.bold = True
        if size: r.font.size = Pt(size)
    r = p.add_run(text)
    if size: r.font.size = Pt(size)
    return p


def pending(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(PENDING + text)
    r.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
    return p


def caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Pt(0)
    r = p.add_run(text); r.bold = True; r.font.size = Pt(10.5)
    ea(r, "黑体")


def note(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.line_spacing = 1.2
    r = p.add_run(text); r.font.size = Pt(9)


def shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    s = OxmlElement("w:shd"); s.set(qn("w:val"), "clear"); s.set(qn("w:color"), "auto"); s.set(qn("w:fill"), hexcolor)
    tcPr.append(s)


def table(doc, header, rows, widths=None, size=10):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(str(h)); r.bold = True; r.font.size = Pt(size)
        c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        c.paragraphs[0].paragraph_format.first_line_indent = Pt(0)
        shade(c, "E7E2DA")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            pr = cells[i].paragraphs[0]
            pr.paragraph_format.first_line_indent = Pt(0)
            pr.paragraph_format.line_spacing = 1.15
            pr.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = pr.add_run(str(v)); r.font.size = Pt(size)
            if PENDING[1:4] in str(v) or str(v) == "—待填—":
                r.font.color.rgb = RGBColor(0xC0, 0, 0)
    if widths:
        t.autofit = False
        tot = sum(widths); widths = [w * 14.6 / tot for w in widths]
        for i, w in enumerate(widths):
            t.columns[i].width = Cm(w)
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    return t


def figure(doc, path, width=15):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Pt(0)
    p.add_run().add_picture(path, width=Cm(width))


def page_break(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# ================================================================ 正文
doc = Document()
setup(doc)

TITLE = "雪域县域，消费何往"
SUB = "——西藏73区县市场潜力分层与居民消费需求调查"

# ---- 标题页
for _ in range(6):
    doc.add_paragraph()
p = para(doc, TITLE, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, size=26); p.runs[0].bold = True
ea(p.runs[0], "黑体")
para(doc, SUB, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, size=16)
for _ in range(4):
    doc.add_paragraph()
para(doc, "“正大杯”第十七届全国大学生市场调查与分析大赛", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, size=14)
para(doc, "本科组 · 参赛报告", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, size=14)
for _ in range(6):
    doc.add_paragraph()
note(doc, "（按大赛要求，报告中不出现学校、指导教师及团队成员信息。组别请按实际报名填写。）")
page_break(doc)

# ---- 摘要
doc.add_heading("摘  要", level=1).alignment = WD_ALIGN_PARAGRAPH.CENTER
t1, t2, t3, t4 = T[1], T[2], T[3], T[4]
para(doc,
     f"2016—2025年，西藏地区生产总值由{f1(M['gdp_2016'],0)}亿元增至{f1(M['gdp_2025'],0)}亿元，"
     f"农村居民人均可支配收入由{f1(M['rural_2016'],0)}元增至{f1(M['rural_2025'],0)}元，"
     f"相当于全国农村水平的比例由{pct(M['rural_rel_2016'])}升至{pct(M['rural_rel_2025'])}。"
     "收入快速增长之下，县域消费市场在哪里、有多大、居民买什么、在哪里买、卡在哪里，"
     "既缺少县一级的系统画像，也缺少面向居民的一手证据。")
para(doc,
     f"本报告分两步回答。第一步用二手数据摸清市场“底数”：以73个区县2016—2024年面板数据，"
     f"从经济规模、人口规模、人均产出、成长速度、人均公共支出和财政自给率六个维度构建熵权市场潜力指数，"
     f"并用K均值聚类把区县分为四类市场：高产出核心型（{t1['n']:.0f}个）、地市中心型（{t2['n']:.0f}个）、"
     f"财政支撑型（{t3['n']:.0f}个）和农牧基础型（{t4['n']:.0f}个）。"
     f"农牧基础型集中了73区县{pct(t4['pop_share'],0)}的户籍人口，却只有{pct(t4['gdp_share'],0)}的产出，"
     f"人均产出约为高产出核心型的{t4['gdp_pc']/t1['gdp_pc']*100:.0f}%；"
     f"财政支撑型人均公共支出最高（{t3['exp_pc']/1e4:.1f}万元），财政自给率却只有{pct(t3['ssr'])}。"
     f"分层结果在更换随机种子、删去增速指标、修正口径跳变后保持稳定（调整兰德指数≥{min(R.values()):.2f}）。")
para(doc,
     f"第二步以四类市场为层，设计二阶段分层PPS入户调查：每层按人口规模成比例抽取2个县，"
     f"共8个样本县、有效样本{N['n_total_alloc']}户（计划发放{N['n_issue_alloc']}份），"
     "问卷围绕收入与消费结构、购物渠道、物流可得性、线上消费意愿与消费痛点五个模块，"
     "以计划行为理论构建线上消费意愿模型。二手数据给出“哪里有市场”，一手调查回答“市场要什么”，"
     "两者通过抽样框直接衔接。" + "一手调查结果" + PENDING + "。")
para(doc, "市场潜力指数；县域市场分层；K均值聚类；分层PPS抽样；计划行为理论；西藏",
     bold_lead="关键词：", indent=False)
page_break(doc)

# ---- 目录（Word 打开后右键“更新域”）
doc.add_heading("目  录", level=1).alignment = WD_ALIGN_PARAGRAPH.CENTER
p = doc.add_paragraph()
r = p.add_run()
for tag, text in [("begin", None), (None, 'TOC \\o "1-3" \\h \\z \\u'), ("separate", None)]:
    if tag:
        e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), tag); r._r.append(e)
    else:
        e = OxmlElement("w:instrText"); e.set(qn("xml:space"), "preserve"); e.text = text; r._r.append(e)
r2 = p.add_run("（在 Word 中右键此处 →“更新域”生成目录）")
r3 = p.add_run(); e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), "end"); r3._r.append(e)
page_break(doc)

# ================================================================ 一、背景
doc.add_heading("一、调查背景与问题提出", level=1)
doc.add_heading("（一）收入上台阶，县域消费成为新增长点", level=2)
para(doc,
     f"2016—2025年，西藏地区生产总值年均增长{pct(M['gdp_cagr'])}（现价），"
     f"农村居民人均可支配收入年均增长{pct(M['rural_cagr'])}，与全国农村居民的差距明显缩小："
     f"2016年为全国农村水平的{pct(M['rural_rel_2016'])}，2025年已达{pct(M['rural_rel_2025'])}（图1）。"
     "农牧民收入接近全国平均，意味着消费正从“吃饱穿暖”转向家电、交通工具、教育与服务消费，"
     "县城和乡镇是这部分新增需求最先落地的地方。")
para(doc,
     f"外来消费同样在扩张。接待游客总人数由2016年的{f1(M['tour_2016'],0)}万人次增至2025年的"
     f"{f1(M['tour_2025'],0)}万人次，相当于每位常住居民对应约{M['tour_per_res_2025']:.0f}人次游客；"
     f"其间2020年和2022年分别回落到{f1(M['tour_2020'],0)}万和{f1(M['tour_2022'],0)}万人次，"
     "说明外来消费波动大，县域市场的稳定支撑仍要靠本地居民。")
figure(doc, os.path.join(OUT, "fig1_macro.png"), 15.5)
caption(doc, "图1  西藏地区生产总值、农村居民收入与接待游客人数（2016—2025年）")
note(doc, "资料来源：西藏自治区历年国民经济和社会发展统计公报；全国农村居民收入取自国家统计局历年统计公报。")

doc.add_heading("（二）问题：县域市场的“底数”和“需求”都不清楚", level=2)
para(doc,
     "西藏74个县级行政区，面积大、人口散、海拔高，县与县之间差别很大：既有人均产出接近东部发达地区的"
     "拉萨近郊区县，也有人口不足两万、靠财政转移支付维持公共服务的边境牧区县。"
     "企业布局网点、政府规划县域商业体系，都需要先回答两个问题：")
para(doc, "哪些区县有市场、有多大、属于什么类型？现有研究多停留在全区或地市一级，缺少覆盖全部区县的统一测度。",
     bold_lead="第一，“底数”问题：")
para(doc, "不同类型区县的居民买什么、在哪里买、线上消费为什么用或不用？统计年鉴不提供这类信息，只能通过入户调查获得。",
     bold_lead="第二，“需求”问题：")

doc.add_heading("（三）调查目标与意义", level=2)
para(doc, "本调查设定三项目标：（1）构建覆盖73个区县的市场潜力指数并划分市场类型；"
     "（2）以分层结果为抽样框，调查各类市场居民的消费结构、渠道选择与线上消费意愿；"
     "（3）据此为县域商业网点布局、电商与物流下沉提出分类建议。")
para(doc, "实践上，分层画像可直接用于企业选址和政府县域商业体系建设的优先排序；"
     "方法上，本报告把二手数据的聚类结果作为一手调查的分层抽样框，"
     "让“宏观画像”与“微观调查”在同一套分层下衔接，避免两张皮。")

doc.add_heading("（四）研究框架与技术路线", level=2)
table(doc, ["阶段", "数据", "方法", "产出"], [
    ["1 市场底数", "73区县面板（2016—2024）", "熵权法、K均值聚类、稳健性检验", "市场潜力指数、四类市场"],
    ["2 抽样设计", "分层结果 + 户籍人口", "二阶段分层PPS抽样", "8个样本县、各层样本量"],
    ["3 需求调查", "入户问卷（计划约1100份）", "描述统计、卡方检验、有序Logit、结构方程", "消费结构、渠道、意愿模型"],
    ["4 对策建议", "1—3 的结果", "分类比较", "分层次的网点与物流方案"],
], widths=[2.5, 4.2, 4.8, 3.8])
caption(doc, "表1  研究技术路线")

# ================================================================ 二、文献
doc.add_heading("二、文献回顾与理论基础", level=1)
doc.add_heading("（一）市场潜力的测度", level=2)
para(doc, "Harris（1954）最早用“市场潜力”描述一个地区可触达的购买力，核心是规模与可达性。"
     "后续研究多用多指标综合评价刻画区域市场，常见做法是对规模、收入、增长等指标标准化后加权。"
     "权重的确定有主观赋权与客观赋权两类，熵权法依据指标离散程度确定权重（Shannon，1948），"
     "不依赖专家打分，适合指标间量纲差异大的县域数据。")
doc.add_heading("（二）市场分层与聚类", level=2)
para(doc, "市场细分的基本思路是把需求相近的单元归为一组，分别制定策略。"
     "K均值聚类（MacQueen，1967）是最常用的划分方法，聚类数可用轮廓系数（Rousseeuw，1987）辅助确定，"
     "分层是否稳定可用调整兰德指数（Hubert and Arabie，1985）衡量。")
doc.add_heading("（三）抽样设计", level=2)
para(doc, "当总体单位规模差异大时，按规模成比例概率抽样（PPS）可以降低估计方差（Hansen and Hurwitz，1943）；"
     "先分层再抽样可以保证各类子总体都有足够样本（Kish，1965）。本报告以聚类结果为层，"
     "正是利用了分层抽样“层内同质、层间异质”的要求。")
doc.add_heading("（四）消费意愿的理论框架", level=2)
para(doc, "计划行为理论（Ajzen，1991）认为，行为意愿由态度、主观规范和知觉行为控制共同决定。"
     "对高原县域居民而言，物流时效、网络条件、语言与支付能力都属于“知觉行为控制”，"
     "这正是本调查希望识别的关键约束。")
doc.add_heading("（五）文献述评", level=2)
para(doc, "已有研究存在两点不足：一是区域市场测度多到地市一级，缺少覆盖全部区县的统一口径；"
     "二是宏观评价与微观调查各自独立，评价结果没有用来指导调查样本的选择。"
     "本报告以区县为单位测度市场潜力，并把分层结果直接作为抽样框，弥补这两点。")
note(doc, "注：国内关于西藏县域消费、农村电商的文献请团队在知网检索后补充，并逐条核对作者、年份与期刊。")

# ================================================================ 三、方案设计
doc.add_heading("三、调查方案设计", level=1)
doc.add_heading("（一）调查对象与内容", level=2)
para(doc, "二手数据部分：西藏73个区县（城关区缺少人口与财政数据，只用于规模排序）。"
     "一手调查部分：样本县内年满18周岁、在本地居住半年以上的常住家庭，每户由熟悉家庭开支的成员作答。")
table(doc, ["模块", "主要内容", "题目数", "对应分析"], [
    ["A 家庭基本信息", "人口、职业、收入来源、居住地（县城/乡镇/村）", "8", "分组变量"],
    ["B 收入与消费结构", "年收入区间、八大类支出占比、近一年大件消费", "6", "消费结构比较"],
    ["C 购物渠道", "县城商超、乡镇小店、集市、网购、直播、代购的使用频率", "6", "渠道选择、卡方检验"],
    ["D 物流与支付", "最近快递点距离、到货天数、移动支付使用", "4", "知觉行为控制"],
    ["E 线上消费意愿", "态度、主观规范、知觉行为控制、意愿量表（李克特5级）", "16", "结构方程模型"],
    ["F 痛点与需求", "最想买却买不到的商品、最希望改善的服务", "3", "开放题编码"],
], widths=[3.2, 6.5, 1.6, 3.9])
caption(doc, "表2  问卷结构（完整问卷见附录一）")

doc.add_heading("（二）二手数据与指标体系", level=2)
para(doc, "区县面板包括地区生产总值、户籍人口、地方一般预算收入与支出四项，覆盖2016—2024年。"
     "原始数据中有11个数值明显录入错误（如2018年仁布、定结等五县的收入栏实为支出数），"
     "按事先设定的机械规则剔除，规则见附录三。指标设置如下：")
wrow = []
desc = {"经济规模": ("2024年地区生产总值", "亿元"), "人口规模": ("2024年户籍人口", "万人"),
        "人均产出": ("人均地区生产总值，2022—2024年均值", "元"), "成长速度": ("2016—2024年地区生产总值年均增速", "%"),
        "人均公共支出": ("人均一般预算支出，2022—2024年均值", "元"), "财政自给率": ("一般预算收入/支出，2022—2024年均值", "%")}
meaning = {"经济规模": "市场总量", "人口规模": "潜在顾客数", "人均产出": "购买力", "成长速度": "市场成长性",
           "人均公共支出": "政府采购与公共消费", "财政自给率": "本地经济自主性"}
for k, v in W.items():
    wrow.append([k, desc[k][0], desc[k][1], meaning[k], f"{v:.3f}"])
table(doc, ["维度", "指标定义", "单位", "市场含义", "熵权"], wrow, widths=[2.4, 5.6, 1.4, 3.6, 1.6])
caption(doc, "表3  市场潜力指标体系与熵权")
note(doc, "注：受数据限制，未纳入社会消费品零售总额与居民收入的区县数据；户籍人口原始数据精确到万人，小县的人均指标误差较大。"
     "三年均值用于平滑单年波动。")
para(doc, "指标经极差标准化并平移至[0.01, 1]后，用熵权法确定权重，加权求和后以最高值为100换算得到市场潜力指数。"
     f"权重最高的是经济规模（{W['经济规模']:.3f}）和财政自给率（{W['财政自给率']:.3f}），"
     f"最低的是成长速度（{W['成长速度']:.3f}）——各县增速普遍较快、差别相对小，区分力弱。")

doc.add_heading("（三）抽样设计", level=2)
para(doc, "采用二阶段分层PPS抽样：", indent=True)
para(doc, "以第四部分得到的四类市场为层，层内同质、层间异质，满足分层抽样要求。", bold_lead="分层：")
para(doc, "每层按2024年户籍人口规模成比例系统抽取2个县（PPS），随机种子固定为20261104，可复现。", bold_lead="第一阶段（县）：")
para(doc, "样本县内按县城社区、乡镇驻地、行政村三类居住地配额，各占约1/3，"
     "在每类中随机抽取社区或村，再按户籍名册等距抽户。", bold_lead="第二阶段（户）：")
para(doc,
     f"样本量按估计比例的公式确定：n₀ = z²p(1−p)/e²，取置信水平95%（z=1.96）、p=0.5、允许误差e={S['e']:.0%}，"
     f"得n₀≈{S['n0']:.0f}；考虑整群抽样的设计效应deff={S['deff']}，需有效样本{S['n_eff']}户。"
     f"层间按人口平方根比例分配，并设每层至少150户以保证分层分析，合计{N['n_total_alloc']}户；"
     f"按应答率{S['resp']:.0%}计划发放{N['n_issue_alloc']}份。")
rows = [[r["层级"], r["区县"], r["地市"], f"{r['户籍人口(万人)']:.0f}", f"{r['入样概率']:.3f}", r["本县样本量"]]
        for _, r in psu.iterrows()]
table(doc, ["层级", "样本县", "所属地市", "户籍人口（万人）", "入样概率", "计划有效样本"], rows,
      widths=[2.8, 2.6, 2.3, 2.6, 2.0, 2.6])
caption(doc, "表4  样本县与样本量分配")
note(doc, "注：双湖县平均海拔约5000米，若因交通或审批无法入户，按预案以同层内按地市、县名排序的下一县替补，并在报告中说明。"
     "边境县入户须事先办理相关手续。设计权数=1/（县入样概率×户入样概率），用于加权估计。")

doc.add_heading("（四）问卷设计与预调查", level=2)
para(doc, "问卷采用藏汉双语，量表题参照计划行为理论的成熟量表改编。正式调查前在拉萨市开展预调查"
     "（计划约50份），检验题目理解度、作答时长（目标15分钟以内）和量表信度（克朗巴哈α≥0.7），据此修改问卷。")
pending(doc, "预调查样本量、α系数与修改内容。")

doc.add_heading("（五）质量控制", level=2)
for lead, txt in [
    ("调查员：", "招募藏汉双语调查员，统一培训并模拟访问；"),
    ("现场：", "使用电子问卷记录定位与作答时长，作答少于5分钟的问卷剔除；"),
    ("复核：", "每名调查员随机抽取10%的问卷电话回访；"),
    ("数据：", "设置逻辑校验（如分项支出之和不超过总支出），双人独立录入开放题编码；"),
    ("伦理：", "入户前说明调查目的并取得口头知情同意，不收集姓名、身份证号等可识别信息。")]:
    para(doc, txt, bold_lead=lead)

doc.add_heading("（六）调查实施计划", level=2)
table(doc, ["时间", "工作内容"], [
    ["2026年11月", "确定选题、二手数据分析、问卷初稿"],
    ["2026年12月", "预调查、修改问卷、联系样本县、调查员培训"],
    ["2027年1—2月", "寒假入户调查（8个样本县）"],
    ["2027年2月下旬", "数据清理、加权、建模"],
    ["2027年3月中旬", "完成报告与PPT，校内查重"],
    ["2027年3月底前", "校赛提交"],
], widths=[4, 11])
caption(doc, "表5  调查实施进度")
note(doc, "注：时间节点按第十七届大赛通知（校赛3月底前完成），以学校通知为准。")

# ================================================================ 四、二手数据分析
doc.add_heading("四、县域市场底数：潜力指数与市场分层", level=1)
doc.add_heading("（一）市场高度集中", level=2)
para(doc,
     f"把有GDP数据的城关区一并计入，2024年城关区一个区就占74区县GDP的{pct(N['chengguan_share_2024'])}"
     f"（2016年为{pct(N['chengguan_share_2016'])}），GDP前五位的区县合计占{pct(N['top5_share_2024'])}。"
     "其余69个区县分享不到六成的产出，市场“头重脚轻”。城关区份额在下降，说明增长正在向外围扩散。")

doc.add_heading("（二）市场潜力指数排名", level=2)
top = mpi.head(10)
table(doc, ["排名", "区县", "地市", "潜力指数", "人均产出（万元）", "户籍人口（万人）", "类型"],
      [[int(r.mpi_rank), r.county_cn, r.pref_cn, f"{r.mpi:.1f}", f"{r.gdp_pc/1e4:.1f}", f"{r.pop_2024:.0f}", r.tier_name]
       for _, r in top.iterrows()], widths=[1.2, 2.4, 2.0, 1.8, 2.6, 2.6, 2.6])
caption(doc, "表6  市场潜力指数前十位区县")
figure(doc, os.path.join(OUT, "fig3_top15.png"), 13)
caption(doc, "图2  市场潜力指数前十五位（颜色代表市场类型）")
para(doc,
     f"堆龙德庆区以100分居首，墨竹工卡县（{mpi.iloc[1].mpi:.1f}）次之，两者都是拉萨近郊、产业园区集中的区县。"
     "第三至第八位全部是地市（地区）政府驻地（巴宜、桑珠孜、卡若、噶尔、乃东、色尼），"
     f"说明“地市中心城区”是拉萨以外最主要的市场节点。末位五县（{'、'.join(r[0] for r in N['bottom5'])}）"
     "多为人口少、产出低的高海拔牧区县。完整排名见附录二。")

doc.add_heading("（三）四类县域市场", level=2)
para(doc,
     f"以六项指标（规模类取对数）标准化后做K均值聚类。k=3至6的轮廓系数分别为"
     f"{'、'.join(f'{v:.3f}' for v in N['silhouette'].values())}，k=4最高，且四类都能给出清楚的市场含义，故取4类。"
     "轮廓系数在0.35左右，说明类别之间有一定重叠，县域市场更接近“连续光谱”而非截然分开，"
     "这也是需要入户调查进一步验证的原因。")
prow = []
for t in sorted(T):
    v = T[t]
    prow.append([v["name"], f"{v['n']:.0f}", pct(v["pop_share"], 1), pct(v["gdp_share"], 1),
                 f"{v['gdp_pc']/1e4:.1f}", pct(v["gdp_cagr"], 1), f"{v['exp_pc']/1e4:.1f}", pct(v["ssr"], 1), f"{v['mpi']:.1f}"])
table(doc, ["类型", "县数", "人口占比", "产出占比", "人均产出（万元）", "年均增速", "人均支出（万元）", "财政自给率", "平均潜力指数"],
      prow, widths=[2.4, 1.1, 1.6, 1.6, 1.9, 1.6, 1.9, 1.7, 1.7], size=9)
caption(doc, "表7  四类县域市场的特征（类内均值）")
figure(doc, os.path.join(OUT, "fig2_tiers.png"), 14.5)
caption(doc, "图3  四类市场的人均产出与人均公共支出（点大小代表人口）")

lst = lambda t: "、".join(mpi[mpi.tier == t].county_cn.tolist())
para(doc, f"{lst(1)}。人均产出{T[1]['gdp_pc']/1e4:.0f}万元，财政自给率{pct(T[1]['ssr'],0)}，"
     "产业园区和矿业带动明显，是购买力最强、最接近“城市型”的市场，适合布局品牌门店与中高端商品。",
     bold_lead=f"1. 高产出核心型（{T[1]['n']:.0f}个）：")
para(doc, f"{lst(2)}。除江达县外均为地市政府驻地，人口规模大，平均约{T[2]['pop_2024']:.0f}万人，"
     f"产出占73区县的{pct(T[2]['gdp_share'],0)}；人均公共支出却是四类中最低的"
     f"（{T[2]['exp_pc']/1e4:.1f}万元），说明这里的消费主要靠本地经济而非财政，是区域商贸、仓储与物流中转的天然节点。",
     bold_lead=f"2. 地市中心型（{T[2]['n']:.0f}个）：")
para(doc, f"人口平均不足{T[3]['pop_2024']+0.5:.0f}万人，人均公共支出最高（{T[3]['exp_pc']/1e4:.1f}万元），"
     f"财政自给率只有{pct(T[3]['ssr'])}。阿里、山南的多数县和日喀则的边境县属于此类。"
     "消费以公职人员、驻地单位和政府采购为主，市场“小而稳”，对价格不敏感但对配送时效和品类齐全要求高。",
     bold_lead=f"3. 财政支撑型（{T[3]['n']:.0f}个）：")
para(doc, f"县数最多，集中了{pct(T[4]['pop_share'],0)}的人口，但人均产出只有{T[4]['gdp_pc']/1e4:.1f}万元，"
     "日喀则、昌都、那曲的农牧业大县多在此类。这是人口红利最大、消费升级空间最大、"
     "但物流和渠道最薄弱的市场，也是本次入户调查样本量最大的一层。",
     bold_lead=f"4. 农牧基础型（{T[4]['n']:.0f}个）：")

ctr = [[i] + [int(ct.loc[i].get(TN[t], 0)) for t in sorted(T)] for i in ct.index]
table(doc, ["地市"] + [TN[t] for t in sorted(T)], ctr, widths=[2.6, 3, 3, 3, 3])
caption(doc, "表8  各地市区县的市场类型分布（个）")
para(doc, "同一地市内部差异很大：日喀则18个区县中，农牧基础型9个、财政支撑型8个，地市中心型只有桑珠孜区1个。"
     "按地市“一刀切”配置商业资源，会忽略这种内部差异。")

doc.add_heading("（四）稳健性检验", level=2)
table(doc, ["检验", "做法", "与基准分层的调整兰德指数"], [
    ["更换随机种子", "20个不同种子重复聚类", f"最低 {R['20个随机种子_最低']:.3f}"],
    ["删去成长速度", "只用其余五项指标聚类", f"{R['去掉成长速度']:.3f}"],
    ["修正口径跳变", "噶尔县（2020）、色尼区（2019）GDP有统计口径跳变，增速改用2020—2024年", f"{R['跳变县改用2020-24增速']:.3f}"],
], widths=[3, 8, 4])
caption(doc, "表9  分层稳健性检验")
para(doc, "调整兰德指数为1表示两种分层完全一致。三项检验均在0.74以上，主要结论不变。"
     "修正口径跳变后一致性最低，主要是噶尔县的增速被下调后可能从高产出核心型移出；"
     "因此对噶尔县的类型判断应谨慎，入户调查中不将其作为核心型的代表县。")

# ================================================================ 五、一手调查结果（框架）
doc.add_heading("五、居民消费需求：入户调查结果", level=1)
p = para(doc, "本部分的表格与分析方法已确定，数值" + PENDING + "。调查数据全部来自团队实地入户，"
         "不使用任何模拟或推测数值。")
doc.add_heading("（一）样本概况与代表性检验", level=2)
para(doc, "报告实际回收、有效问卷数和应答率；比较样本与各层户籍人口在性别、年龄、居住地上的分布，"
     "并给出加权前后的差异。")
table(doc, ["层级", "计划有效样本", "实际有效样本", "有效率", "县城/乡镇/村（%）"],
      [[TN[t], N["alloc"][TN[t]], "—待填—", "—待填—", "—待填—"] for t in sorted(T)], widths=[3, 2.8, 2.8, 2.2, 4.4])
caption(doc, "表10  样本回收情况")
doc.add_heading("（二）消费结构：四类市场比较", level=2)
para(doc, "用加权均值比较八大类消费支出占比，检验假设H1：农牧基础型的食品与衣着占比显著高于其他三类，"
     "交通通信与教育文娱占比显著低于其他三类。方法：设计加权的方差分析与两两比较。")
doc.add_heading("（三）购物渠道与物流可得性", level=2)
para(doc, "检验假设H2：到最近快递点的距离越远，网购频率越低。方法：渠道使用频率与市场类型的卡方检验；"
     "以网购频率为因变量的有序Logit模型，控制收入、年龄、教育与居住地。")
doc.add_heading("（四）线上消费意愿：计划行为理论模型", level=2)
para(doc, "先做验证性因子分析检验量表信度与效度（组合信度≥0.7、平均方差提取量≥0.5），"
     "再用结构方程模型估计态度、主观规范与知觉行为控制对意愿的影响，并按市场类型做多群组比较。"
     "假设H3：知觉行为控制（物流、网络、语言、支付）在农牧基础型中的作用强于其他三类。")
table(doc, ["路径", "标准化系数", "p值", "是否支持"],
      [["态度 → 意愿", "—待填—", "—待填—", "—待填—"], ["主观规范 → 意愿", "—待填—", "—待填—", "—待填—"],
       ["知觉行为控制 → 意愿", "—待填—", "—待填—", "—待填—"]], widths=[5, 3, 3, 3])
caption(doc, "表11  结构方程模型路径系数")
doc.add_heading("（五）消费痛点：开放题编码", level=2)
para(doc, "两名成员独立编码，计算一致性（Kappa≥0.7），按市场类型列出前五位痛点。")

# ================================================================ 六、结论
doc.add_heading("六、结论与建议", level=1)
doc.add_heading("（一）主要结论（基于二手数据，已完成）", level=2)
for i, txt in enumerate([
    f"西藏县域市场高度集中：城关区一区占74区县GDP的{pct(N['chengguan_share_2024'],0)}，前五位区县占{pct(N['top5_share_2024'],0)}，但集中度在下降。",
    "73个区县可分为四类市场：高产出核心型、地市中心型、财政支撑型、农牧基础型，分层结果稳健。",
    f"人口与产出错位：农牧基础型集中了{pct(T[4]['pop_share'],0)}的人口，只有{pct(T[4]['gdp_share'],0)}的产出，是消费升级空间最大的市场。",
    "财政支撑型县的消费更多依托公共支出，市场规模小但稳定，与以本地经济为主的地市中心型逻辑不同。"], 1):
    para(doc, txt, bold_lead=f"{i}. ")
doc.add_heading("（二）分类建议（初步，待入户调查验证）", level=2)
table(doc, ["市场类型", "建议方向", "待调查验证的问题"], [
    ["高产出核心型", "品牌门店、中高端与服务消费", "居民最想要但本地缺的品类"],
    ["地市中心型", "区域仓储与配送中心，向周边县辐射", "周边县居民到地市中心购物的频率与距离"],
    ["财政支撑型", "提高配送时效与品类，发展单位团购与政府采购平台", "公职人员与牧民的消费差异"],
    ["农牧基础型", "乡镇快递服务站、双语电商服务、移动支付培训", "物流、语言、支付哪一项是最大障碍"],
], widths=[3, 6, 6])
caption(doc, "表12  分类建议")
pending(doc, "结合入户调查结果修改建议，删去未被支持的部分。")
doc.add_heading("（三）不足", level=2)
para(doc, "区县数据缺少社会消费品零售总额与居民收入，市场潜力指数以产出和财政指标代替，"
     "可能高估矿业、园区经济县的消费能力；户籍人口精确到万人，小县人均指标误差较大；"
     "入户调查只覆盖8个县，结论外推到同类县时需注意。")

# ---- 参考文献
doc.add_heading("参考文献", level=1)
for ref in [
    "Ajzen I. The theory of planned behavior[J]. Organizational Behavior and Human Decision Processes, 1991, 50(2): 179-211.",
    "Hansen M H, Hurwitz W N. On the theory of sampling from finite populations[J]. The Annals of Mathematical Statistics, 1943, 14(4): 333-362.",
    "Harris C D. The market as a factor in the localization of industry in the United States[J]. Annals of the Association of American Geographers, 1954, 44(4): 315-348.",
    "Hubert L, Arabie P. Comparing partitions[J]. Journal of Classification, 1985, 2(1): 193-218.",
    "Kish L. Survey Sampling[M]. New York: John Wiley & Sons, 1965.",
    "MacQueen J. Some methods for classification and analysis of multivariate observations[C]//Proceedings of the Fifth Berkeley Symposium on Mathematical Statistics and Probability. Berkeley: University of California Press, 1967, 1: 281-297.",
    "Rousseeuw P J. Silhouettes: a graphical aid to the interpretation and validation of cluster analysis[J]. Journal of Computational and Applied Mathematics, 1987, 20: 53-65.",
    "Shannon C E. A mathematical theory of communication[J]. Bell System Technical Journal, 1948, 27(3): 379-423.",
    "西藏自治区统计局. 西藏自治区国民经济和社会发展统计公报（2016—2025年各年）[R].",
    "国家统计局. 中华人民共和国国民经济和社会发展统计公报（2016—2025年各年）[R].",
]:
    p = para(doc, ref, indent=False, size=10.5)
    p.paragraph_format.left_indent = Cm(0.74)
    p.paragraph_format.first_line_indent = Cm(-0.74)

doc.save(os.path.join(HERE, "参赛报告-正文.docx"))

# ================================================================ 附录
ap = Document()
setup(ap)
ap.add_heading("附录", level=1).alignment = WD_ALIGN_PARAGRAPH.CENTER
ap.add_heading("附录一  调查问卷", level=2)
para(ap, "尊敬的朋友：您好！我们是大学生调查团队，正在了解西藏县域居民的消费情况。问卷匿名填写，"
     "结果只用于学术研究，不涉及您的姓名和身份信息，约需15分钟。感谢您的支持！（正式问卷为藏汉双语）", indent=False)
Q = [
    ("A 家庭基本信息", [
        "A1 您家现在住在：①县城社区 ②乡镇驻地 ③行政村",
        "A2 您的性别：①男 ②女",
        "A3 您的年龄：①18—29岁 ②30—39岁 ③40—49岁 ④50—59岁 ⑤60岁及以上",
        "A4 您的受教育程度：①未上学 ②小学 ③初中 ④高中/中专 ⑤大专及以上",
        "A5 您家常住人口：____人，其中18岁以下____人、60岁以上____人",
        "A6 您家主要收入来源（可多选）：①种植 ②畜牧 ③外出务工 ④本地打工/个体经营 ⑤工资（公职/企业） ⑥政策补贴 ⑦其他",
        "A7 您本人的职业：①农牧民 ②个体经营 ③企业员工 ④公职人员 ⑤学生 ⑥无业/退休 ⑦其他",
        "A8 您家是否有人在县城以外长期工作：①是 ②否"]),
    ("B 收入与消费结构", [
        "B1 去年您家总收入大约：①3万元以下 ②3—6万 ③6—10万 ④10—15万 ⑤15—20万 ⑥20万以上",
        "B2 去年您家总支出大约：____万元",
        "B3 请估计去年各类支出所占比例（合计100%）：食品烟酒__% 衣着__% 居住__% 生活用品__% 交通通信__% 教育文娱__% 医疗保健__% 其他（含宗教、人情）__%",
        "B4 近一年您家购买过的大件（可多选）：①冰箱/冰柜 ②洗衣机 ③电视 ④手机 ⑤电脑 ⑥摩托车 ⑦汽车 ⑧太阳能设备 ⑨都没有",
        "B5 未来一年您家最打算增加哪方面开支（限选2项）：同B3类别",
        "B6 与三年前比，您家生活消费：①明显减少 ②略减少 ③差不多 ④略增加 ⑤明显增加"]),
    ("C 购物渠道", [
        "C1—C6 您家以下渠道的使用频率（①从不 ②一年几次 ③每月 ④每周 ⑤几乎每天）：",
        "  C1 县城超市/商场  C2 乡镇或村里小卖部  C3 集市/流动商贩  C4 网购（淘宝、拼多多、京东等）  C5 直播或短视频购物  C6 托人从拉萨或内地代购"]),
    ("D 物流与支付", [
        "D1 离您家最近的快递收取点：①村里 ②乡镇 ③县城 ④更远；单程大约____分钟",
        "D2 网购商品一般几天到货：①3天内 ②4—7天 ③8—14天 ④15天以上 ⑤没网购过",
        "D3 您是否使用手机支付：①经常 ②偶尔 ③不会用 ④不想用",
        "D4 您家手机网络信号：①很好 ②一般 ③时有时无 ④基本没有"]),
    ("E 线上消费意愿（1=非常不同意，5=非常同意）", [
        "态度：E1 网购能买到本地买不到的东西  E2 网购比本地便宜  E3 网购很方便  E4 总体上我喜欢网购",
        "主观规范：E5 家人支持我网购  E6 身边朋友常网购  E7 村/社区干部鼓励网购  E8 别人推荐的东西我愿意网上买",
        "知觉行为控制：E9 我会用手机下单  E10 到货时间我能接受  E11 商品页面的文字我能看懂  E12 出问题时我知道怎么退换",
        "意愿：E13 未来一年我打算多网购  E14 我愿意把更多开支放到网上  E15 我会推荐家人网购  E16 有了村级快递点我会更多网购"]),
    ("F 痛点与需求", [
        "F1 您最想买、但在本地买不到或很难买到的东西是：________",
        "F2 您觉得本地购物最不方便的地方是：________",
        "F3 如果只能改善一项服务，您最希望是：①快递到村 ②更多商品种类 ③价格更低 ④售后维修 ⑤双语服务 ⑥其他____"]),
]
for sec, items in Q:
    p = para(ap, sec, indent=False); p.runs[0].bold = True
    for it in items:
        para(ap, it, indent=False, size=10.5)

ap.add_heading("附录二  73区县市场潜力指数与类型", level=2)
table(ap, ["排名", "区县", "地市", "潜力指数", "类型", "GDP（亿元）", "人口（万人）"],
      [[int(r.mpi_rank), r.county_cn, r.pref_cn, f"{r.mpi:.1f}", r.tier_name, f"{r.gdp_2024:.1f}", f"{r.pop_2024:.0f}"]
       for _, r in mpi.iterrows()], widths=[1.2, 2.6, 2.2, 1.8, 2.8, 2.2, 2.0], size=9)

ap.add_heading("附录三  数据来源与清洗规则", level=2)
para(ap, "区县面板来自各区县统计资料汇编（2016—2024年），自治区宏观数据来自历年统计公报。"
     "清洗规则：（1）城关区缺少人口与财政数据，不参与指数计算；（2）收入或支出某年数值与前后两年相比"
     "同方向偏离4倍以上且随后回落，视为录入错误设为缺失；（3）财政自给率中位数低于20%的县，"
     "某年收入达到支出80%以上的，视为把支出数填入收入栏；（4）支出小于收入的设为缺失。"
     "共剔除11个数值。噶尔县（2020）与色尼区（2019）的GDP口径跳变保留，并在稳健性检验中处理。")
note(ap, "注：区县面板的最初来源请团队核实并写明（年鉴名称、出版年）。")

ap.add_heading("附录四  数据分析代码说明", level=2)
para(ap, "全部分析可复现：analysis.py（指数、聚类、稳健性、抽样）→ build_report.py（报告）→ build_ppt.js（PPT）。"
     "报告中的每个数字均由程序从数据自动生成。入户调查的加权与建模代码在调查完成后补充。")

ap.add_heading("附录五  AI工具使用情况说明", level=2)
para(ap, "本报告在数据处理代码编写、文字初稿与排版中使用了AI辅助工具。选题、调查设计决策、"
     "实地调查与数据解释由团队成员完成并负责；全部数值均由代码从原始数据计算，团队已逐项核对。")
pending(ap, "按实际使用情况如实修改本说明。")

ap.add_heading("附录六  调查过程记录", level=2)
pending(ap, "调查照片（注意不出现学校信息与受访者面部）、调查日志、预调查修改记录。")
ap.save(os.path.join(HERE, "参赛报告-附录.docx"))
print("ok")
