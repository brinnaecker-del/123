# -*- coding: utf-8 -*-
"""按《高原科学研究》投稿须知第3条，为图名、图注、表名、表注补英文对照。

用法：python3 review/add-en-captions.py <输入.docx> <输出.docx>
（流程：apply-v10.py 生成 v10 → 本脚本就地补英文图表标题与注释）

做法：在每个中文图名／表名／注释段之后插入一段英文，段落格式与中文段相同，段前距设为 0。
"""
import sys, re, copy, zipfile
from lxml import etree

SRC, DST = sys.argv[1], sys.argv[2]
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
w = lambda t: '{%s}%s' % (W, t)
XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'

EN = [
    ('图1　', 'Fig. 1  Logical framework of the security–development–ecology triadic development model'),
    ('注：S表示安全', 'Note: S, D and E denote security, development and ecology; H1, H2 and H3 are the three analytical '
                   'propositions of this paper.'),
    ('图2　', 'Fig. 2  Mechanism chains and analytical propositions of the security–development–ecology system'),
    ('注：图中箭头表示结构性关联', 'Note: Arrows indicate structural linkages.'),
    ('表1　', 'Table 1  Security–development–ecology triadic evaluation index system for high-quality development in Xizang'),
    ('注：①S1、S3、D3、D4、D5五项',
     'Note: ① S1, S3, D3, D4 and D5 lack external policy or statistical targets; their upper bounds follow the convention '
     'of a lower bound of 0 and an upper bound equal to the maximum observed value plus a margin, rounded (1.23–2.20 times '
     'the observed maxima), and are not external empirical benchmarks. ② The benchmarks of E2 and E4 are taken from the '
     'indicator table of the Ecological and Environmental Protection Plan of the Xizang Autonomous Region for the 14th '
     'Five-Year Plan Period: forest coverage is 12.31% in the 2020 baseline and 12.51% as the 2025 target, and comprehensive '
     'grassland vegetation coverage is 47.14% and 50%, respectively. The lower bound is the observed value in the first '
     'sample year (2016) rather than the plan baseline year, to retain discrimination for 2016–2019; the upper bound is the '
     'plan target. ③ D5 is the electricity generation of industrial enterprises above designated size reported in the '
     'statistical communiqué; it differs from the clean-energy generation discussed in Section 4, but the two are close '
     'because clean energy accounts for over 99%. ④ Perturbation tests of the upper bounds and the ceiling effect of E2 '
     'are reported in the robustness section.'),
    ('表2　', 'Table 2  Comparison of the MPI and the traditional coupling degree in typical cases'),
    ('注：US、UD、UE为三子系统综合指数',
     'Note: US, UD and UE are the composite indices of the three subsystems; C is the traditional coupling degree.'),
    ('表3　', 'Table 3  Composite indices of the three subsystems and the MPI coordination index of Xizang, 2016–2025 '
             '(equal-weight baseline)'),
    ('注：样本期内MPI测算结果均落在',
     'Note: All MPI values in the sample period fall within 0–1, with higher values indicating better combined performance '
     'in level and balance. In theory the MPI is not always non-negative and may be negative under extreme imbalance, '
     'which does not occur in the sample period. No fixed ten-grade classification is used; values are described '
     'qualitatively.'),
    ('图3　', 'Fig. 3  Evolution of the composite indices of the security, development and ecology subsystems in Xizang, '
             '2016–2025'),
    ('注：数据来源于表3', 'Note: Data are from Table 3.'),
    ('表4　', 'Table 4  Decomposition of structural contribution gaps (computed annually and averaged over the sample period; '
             'top six)'),
    ('注：结构性贡献缺口为',
     'Note: The structural contribution gap of an indicator is the product of its combined CRITIC–entropy weight and its '
     'deviation, as a share of the sum of these products over all 13 indicators in that year, computed annually and '
     'averaged over the sample period. These weights are used only for indicator-level diagnosis and not for subsystem '
     'aggregation.'),
    ('表5　', 'Table 5  Local sensitivity of the MPI to the three subsystems, 2017–2025'),
    ('注：ε为MPI',
     'Note: ε is the local sensitivity (partial elasticity) of the MPI to a subsystem composite index, calculated annually '
     'by numerical differentiation with ±1% relative perturbations averaged on both sides.'),
    ('表6　', 'Table 6  Leave-one-out (LOO) results for the 13 indicators'),
    ('注：逐一剔除单项指标',
     'Note: Each indicator is removed in turn and the index is recalculated with all other settings unchanged. "Years with '
     'development weakest" is the number of years in the 10-year sample in which the development subsystem index is the '
     'lowest of the three.'),
]

zin = zipfile.ZipFile(SRC)
INFOS = zin.infolist()
FILES = {i.filename: zin.read(i.filename) for i in INFOS}   # 先全部读入，允许输入输出为同一文件
zin.close()
root = etree.fromstring(FILES['word/document.xml'])
body = root.find(w('body'))
text_of = lambda el: ''.join(t.text or '' for t in el.iter(w('t')))

def base_rpr(p):
    for r in p.iter(w('r')):
        if r.find(w('t')) is None:
            continue
        rpr = r.find(w('rPr'))
        rp = copy.deepcopy(rpr) if rpr is not None else etree.Element(w('rPr'))
        for va in rp.findall(w('vertAlign')):
            rp.remove(va)
        return rp
    return etree.Element(w('rPr'))

done = 0
for prefix, en in EN:
    hits = [p for p in body if p.tag == w('p') and text_of(p).startswith(prefix)]
    assert len(hits) == 1, (prefix, len(hits))
    zh = hits[0]
    nxt = zh.getnext()
    assert not (nxt is not None and nxt.tag == w('p') and text_of(nxt).startswith(en[:12])), '已补过：' + prefix
    p = etree.Element(w('p'))
    ppr = zh.find(w('pPr'))
    if ppr is not None:
        ppr = copy.deepcopy(ppr)
        sp = ppr.find(w('spacing'))
        if sp is not None:
            sp.set(w('before'), '0')          # 英文行紧接中文行：段前距 0，段后距沿用中文行
            zsp = zh.find(w('pPr')).find(w('spacing'))
            if zsp.get(w('after')) is not None:
                zsp.set(w('after'), '0')
        p.append(ppr)
    r = etree.SubElement(p, w('r'))
    r.append(base_rpr(zh))
    t = etree.SubElement(r, w('t')); t.text = en; t.set(XML_SPACE, 'preserve')
    zh.addnext(p)
    done += 1
print('补英文对照', done, '处')

data = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
zout = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED)
for it in INFOS:
    zout.writestr(it, data if it.filename == 'word/document.xml' else FILES[it.filename])
zout.close()
print('written', DST)
