# -*- coding: utf-8 -*-
"""按原图版式重绘图1、图2（SVG），措辞改为“弱补偿性”，图2 H1/H2 改指向发展子系统。"""
FONT = "'Noto Serif CJK SC','Noto Serif CJK','SimSun',serif"

def head(w, h):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs>
 <marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto-start-reverse">
  <path d="M0,0 L10,5 L0,10 z" fill="#111"/></marker>
</defs>
<rect width="{w}" height="{h}" fill="#fff"/>
<g font-family="{FONT}" fill="#111">
'''
TAIL = '</g></svg>\n'

def rect(x, y, w, h, dashed=False, sw=1.6, rx=0, dash='6 4'):
    da = f' stroke-dasharray="{dash}"' if dashed else ''
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="#fff" stroke="#111" stroke-width="{sw}"{da}/>\n'

def text(x, y, s, size=15, bold=False, anchor='middle'):
    fw = ' font-weight="700"' if bold else ''
    if s.startswith('• '):  # 圆点用无衬线字形，避免宋体下显示为“·”
        s = '<tspan font-family="Noto Sans CJK SC,sans-serif">•</tspan> ' + s[2:]
    return f'<text x="{x}" y="{y}" font-size="{size}"{fw} text-anchor="{anchor}">{s}</text>\n'

def arrow(d, dashed=False, sw=1.5, dash='6 4'):
    da = f' stroke-dasharray="{dash}"' if dashed else ''
    return f'<path d="{d}" fill="none" stroke="#111" stroke-width="{sw}"{da} marker-end="url(#ah)"/>\n'

def line(d, dashed=False, sw=1.5):
    da = ' stroke-dasharray="6 4"' if dashed else ''
    return f'<path d="{d}" fill="none" stroke="#111" stroke-width="{sw}"{da}/>\n'

# ---------------- 图1 ----------------
W, H = 1210, 696
s = head(W, H)
s += rect(231, 15, 740, 47, sw=2)
s += text(601, 46, '新时代党的治藏方略：稳定、发展、生态、强边（四件大事）', 22, True)
s += arrow('M601,62 L601,80')
s += rect(455, 82, 293, 40, dashed=True)
s += text(601.5, 109, '国家战略功能映射', 18, True)
s += arrow('M601,122 L601,131')
s += rect(122, 133, 956, 137, dashed=True)
for cx, x, w, t1, t2, l1, l2 in [
    (274, 124 + 23, 301, '安全功能（S）', '（稳定＋强边）', '边疆安全、社会稳定、民族团结、', '民生保障、治理效能'),
    (599, 462, 274, '发展功能（D）', '（发展）', '经济增长质量、结构升级、效率提升、', '开放合作、共同富裕'),
    (922, 781, 282, '生态屏障功能（E）', '（生态）', '生态安全、资源环境承载、生态保护修复、', '绿色低碳发展')]:
    s += rect(x, 148, w, 109)
    c = x + w / 2
    s += text(c, 173, t1, 17, True) + text(c, 196, t2, 15) + text(c, 222, l1, 14) + text(c, 244, l2, 14)
s += arrow('M274,257 L274,296') + arrow('M599,257 L599,288') + arrow('M922,257 L922,296')
s += rect(158, 298, 232, 99, dashed=True)
s += text(274, 326, '下界约束（底线）', 16, True) + text(274, 352, '不可从下击穿', 15) + text(274, 379, '为发展提供稳定与保障条件', 15)
s += rect(500, 290, 198, 121, sw=2.6)
s += text(599, 316, '发展（D）', 17, True) + text(599, 341, '约束条件下的响应变量', 16, True)
s += text(599, 368, '在底线与边界约束下', 15) + text(599, 391, '实现能力提升', 15)
s += rect(815, 298, 214, 99, dashed=True)
s += text(922, 326, '上界约束（边界）', 16, True) + text(922, 352, '不可从上突破', 15) + text(922, 379, '约束发展方式与规模', 15)
s += arrow('M390,350 L498,350') + text(444, 338, 'H1：降成本机制', 12.5)
s += arrow('M815,350 L700,350') + text(757, 338, 'H2：价值转化机制', 12.5)
s += line('M274,397 L274,435 L922,435 L922,397') + line('M599,411 L599,435')
s += '<path d="M599,428 L606,435 L599,442 L592,435 z" fill="#111"/>\n'
s += arrow('M599,442 L599,463')
s += rect(415, 465, 370, 62)
s += text(600, 491, '三元协调状态（S—D—E）', 17, True) + text(600, 517, '整体水平与结构失衡并存', 16)
s += arrow('M600,527 L600,546')
s += rect(415, 548, 370, 64)
s += text(600, 574, '弱补偿性聚合：失衡惩罚型协调指数（MPI）', 16.5, True) + text(600, 601, '降低高值维度对失衡的掩盖效应', 16)
s += arrow('M600,612 L600,630')
s += rect(415, 632, 370, 58)
s += text(600, 656, '相对短板识别与动态转移', 17, True) + text(600, 681, 'H3：短板动态转移预期（S ⇄ D ⇄ E）', 16)
s += rect(95, 498, 195, 172, dashed=True)
s += text(110, 526, '辅助诊断与稳健性支持', 15, True, 'start')
for i, b in enumerate(['结构性贡献缺口', '局部敏感性分析', '留一法检验', '滚动端点稳定性', '基准上/下浮动检验', '通用范式对照']):
    s += text(112, 552 + 22 * i, '• ' + b, 14, False, 'start')
s += line('M290,578 L345,578', dashed=True) + line('M345,492 L345,662', dashed=True)
for y in (492, 578, 662):
    s += arrow(f'M345,{y} L413,{y}', dashed=True)
s += TAIL
open('fig1.svg', 'w', encoding='utf8').write(s)

# ---------------- 图2 ----------------
W, H = 1210, 679
s = head(W, H)
# H3
s += rect(560, 30, 360, 78, dashed=True)
s += text(740, 60, 'H3：相对短板及其动态转移预期', 17, True) + text(740, 90, '→ 阶段间相对位置动态转换', 16)
s += arrow('M840,108 C 860,170 960,190 985,253', dashed=True, sw=1.8, dash='10 4 2 4')
def subsys(x, y, w, title, items):
    out = rect(x, y, w, 125, sw=2, rx=6)
    out += text(x + w / 2, y + 30, title, 19, True)
    for i, it in enumerate(items):
        out += text(x + 22, y + 58 + 24 * i, '• ' + it, 15, False, 'start')
    return out
s += subsys(60, 140, 290, '安全子系统', ['财政保障与治理能力', '边疆安全与社会稳定', '民生兜底与社会保障'])
s += subsys(415, 290, 265, '发展子系统', ['经济增长与结构升级', '开放合作与产业动能', '收入改善与共同富裕'])
s += subsys(60, 440, 290, '生态子系统', ['生态安全与资源环境承载', '生态修复与屏障功能', '绿色利用与可持续约束'])
# H1：安全 → 发展
s += arrow('M350,172 L500,172 C 535,172 547,200 547,288', sw=1.8)
s += text(362, 132, 'H1：降低制度风险与交易成本', 15, True, 'start') + text(362, 157, '→ 提升发展效率', 15, True, 'start')
# H2：生态 → 发展
s += arrow('M350,522 L500,522 C 535,522 547,494 547,417', sw=1.8)
s += text(362, 548, 'H2：约束发展规模与发展方式', 15, True, 'start') + text(362, 573, '（通过边界约束优化发展）', 15, False, 'start')
# 发展 → 三元协调状态
s += arrow('M680,352 L833,352', sw=1.8)
s += text(756, 340, '发展质量与能力提升', 14, True)
# 三元协调状态
s += rect(835, 255, 250, 200, sw=2.6, rx=10)
s += text(960, 294, '三元协调状态', 20, True) + text(960, 323, '（MPI协调指数）', 18, True)
for i, it in enumerate(['弱补偿性聚合', '失衡惩罚式测度', '整体水平 × 结构失衡程度']):
    s += text(855, 365 + 30 * i, '• ' + it, 16, False, 'start')
# 注
s += rect(250, 598, 710, 72, dashed=True, dash='3 3')
s += text(605, 627, '注：三子系统指数共同进入MPI协调指数，箭头表示子系统之间的结构性关联；', 15, True)
s += text(605, 654, 'MPI协调指数采用失衡惩罚型聚合方法，对子系统失衡施加连续惩罚（弱补偿）。', 15, True)
s += TAIL
open('fig2.svg', 'w', encoding='utf8').write(s)
print('svg written')
