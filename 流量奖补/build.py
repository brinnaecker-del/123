# -*- coding: utf-8 -*-
"""由 原稿.docx + content.py 生成 修订稿.docx。

直接改写 word/document.xml 的 <w:body>：原稿中的图片段落、未改动的表格按块原样保留，
其余段落按 content.py 重写；参考文献按首次引用顺序重新编号（顺序编码制）。
用法：python3 build.py   （需先 unzip 原稿.docx 到 unpacked/）
"""
import io, re, sys, shutil, os
from xml.sax.saxutils import escape
from content import SPEC, NEW_REFS, DROPPED

SRC = 'unpacked/word/document.xml'
OUT_DIR = 'build'

d = io.open(SRC, encoding='utf8').read()
head, rest = d.split('<w:body>', 1)
body, tail = rest.rsplit('</w:body>', 1)


# ---------- 拆分原稿 body 的顶层块 ----------
def split_blocks(body):
    blocks, i = [], 0
    pat = re.compile(r'<w:(p|tbl|sectPr)[ >]')
    while True:
        m = pat.search(body, i)
        if not m:
            break
        tag, s = m.group(1), m.start()
        depth = 0
        rx = re.compile(r'<w:%s[ >]|</w:%s>' % (tag, tag))
        for mm in rx.finditer(body, s):
            depth += -1 if mm.group(0).startswith('</') else 1
            if depth == 0:
                j = mm.end()
                break
        blocks.append(body[s:j])
        i = j
    return blocks


B = split_blocks(body)
assert len(B) == 139, len(B)
txt = lambda x: ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', x))

# 原稿参考文献 o1..o33
OLD_REFS = {}
for k in range(101, 134):
    t = txt(B[k])
    m = re.match(r'\[(\d+)\]\s*(.*)', t)
    OLD_REFS['o' + m.group(1)] = m.group(2)
assert len(OLD_REFS) == 33
REFS = dict(OLD_REFS)
REFS.update(NEW_REFS)

# ---------- 引文编号 ----------
CITE = re.compile(r'〔([^〕]+)〕')
order = []


def scan(s):
    for m in CITE.finditer(s):
        for k in m.group(1).split(','):
            k = k.strip()
            assert k in REFS, k
            assert k not in DROPPED, k
            if k not in order:
                order.append(k)


for item in SPEC:
    for x in item[1:]:
        if isinstance(x, str):
            scan(x)
        elif isinstance(x, list):
            for y in x:
                if isinstance(y, list):
                    for z in y:
                        scan(z)
                elif isinstance(y, str):
                    scan(y)
NUM = {k: i + 1 for i, k in enumerate(order)}


def cite_label(keys):
    ns = sorted(NUM[k.strip()] for k in keys.split(','))
    parts, i = [], 0
    while i < len(ns):
        j = i
        while j + 1 < len(ns) and ns[j + 1] == ns[j] + 1:
            j += 1
        parts.append(str(ns[i]) if i == j else '%d-%d' % (ns[i], ns[j]))
        i = j + 1
    return '[' + ','.join(parts) + ']'


# ---------- run 生成 ----------
TOK = re.compile(r'(〔[^〕]+〕|【【.*?】】|⟦[^⟧]+⟧|_\{[^}]+\}|\^\{[^}]+\})')


def rpr(sz, bold=False, hei=False, sup=False, sub=False, hl=False, ital=False):
    f = '<w:rFonts w:eastAsia="黑体"/>' if hei else (
        '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>' if ital else '<w:rFonts w:hint="eastAsia"/>')
    s = f
    if bold:
        s += '<w:b/><w:bCs/>'
    if ital:
        s += '<w:i/><w:iCs/>'
    if hl:
        s += '<w:highlight w:val="yellow"/>'
    if sz:
        s += '<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (sz, sz)
    if sup:
        s += '<w:vertAlign w:val="superscript"/>'
    if sub:
        s += '<w:vertAlign w:val="subscript"/>'
    return '<w:rPr>' + s + '</w:rPr>'


def r(text, **kw):
    sp = ' xml:space="preserve"' if (text[:1] == ' ' or text[-1:] == ' ') else ''
    return '<w:r>%s<w:t%s>%s</w:t></w:r>' % (rpr(**kw), sp, escape(text))


def runs(text, sz=21, bold=False, hei=False, hl=False, cites=True):
    out = []
    for seg in TOK.split(text):
        if not seg:
            continue
        if seg.startswith('〔') and cites:
            out.append(r(cite_label(seg[1:-1]), sz=sz, sup=True, hl=hl))
        elif seg.startswith('【【'):
            out.append(runs(seg[2:-2], sz=sz, bold=bold, hei=hei, hl=True, cites=cites))
        elif seg.startswith('⟦'):
            out.append(r(seg[1:-1], sz=sz, ital=True, hl=hl))
        elif seg.startswith('_{'):
            out.append(r(seg[2:-1], sz=sz, sub=True, hl=hl))
        elif seg.startswith('^{'):
            out.append(r(seg[2:-1], sz=sz, sup=True, hl=hl))
        else:
            out.append(r(seg, sz=sz, bold=bold, hei=hei, hl=hl))
    return ''.join(out)


def P(ppr, content):
    return '<w:p><w:pPr>%s</w:pPr>%s</w:p>' % (ppr, content)


PPR_BODY = '<w:ind w:firstLine="420"/><w:jc w:val="both"/>'
PPR_H1 = '<w:keepNext/><w:spacing w:before="260" w:after="120"/>'
PPR_H2 = '<w:keepNext/><w:spacing w:before="160" w:after="80"/>'
PPR_TITLE = '<w:spacing w:before="120" w:after="200"/><w:jc w:val="center"/>'
PPR_TBLCAP = '<w:keepNext/><w:spacing w:before="140" w:after="40"/><w:jc w:val="center"/>'
PPR_TBLNOTE = '<w:spacing w:before="30" w:after="140"/>'
PPR_FORMULA = '<w:spacing w:before="60" w:after="60"/><w:jc w:val="center"/>'
PPR_REF = '<w:spacing w:after="20" w:line="300" w:lineRule="auto"/><w:ind w:left="360" w:hanging="360"/>'

# ---------- 三线表 ----------
TBL_BORDERS = ('<w:tblBorders><w:top w:val="single" w:color="000000" w:sz="12" w:space="0"/>'
               '<w:left w:val="none" w:color="FFFFFF" w:sz="0" w:space="0"/>'
               '<w:bottom w:val="single" w:color="000000" w:sz="12" w:space="0"/>'
               '<w:right w:val="none" w:color="FFFFFF" w:sz="0" w:space="0"/>'
               '<w:insideH w:val="none" w:color="FFFFFF" w:sz="0" w:space="0"/>'
               '<w:insideV w:val="none" w:color="FFFFFF" w:sz="0" w:space="0"/></w:tblBorders>')
CELL_MAR = ('<w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="10" w:type="dxa"/>'
            '<w:bottom w:w="0" w:type="dxa"/><w:right w:w="10" w:type="dxa"/></w:tblCellMar>')
TC_MAR = ('<w:tcMar><w:top w:w="30" w:type="dxa"/><w:left w:w="60" w:type="dxa"/>'
          '<w:bottom w:w="30" w:type="dxa"/><w:right w:w="60" w:type="dxa"/></w:tcMar>')


def table(widths, header, rows, aligns):
    W = sum(widths)
    x = ['<w:tbl><w:tblPr><w:tblStyle w:val="15"/><w:tblW w:w="%d" w:type="dxa"/><w:jc w:val="center"/>%s'
         '<w:tblLayout w:type="fixed"/>%s</w:tblPr><w:tblGrid>%s</w:tblGrid>'
         % (W, TBL_BORDERS, CELL_MAR, ''.join('<w:gridCol w:w="%d"/>' % w for w in widths))]

    def row(cells, kind):
        trpr = '<w:cantSplit/>' + ('<w:tblHeader/>' if kind == 'head' else '') + '<w:jc w:val="center"/>'
        out = ['<w:tr><w:tblPrEx>%s%s</w:tblPrEx><w:trPr>%s</w:trPr>' % (TBL_BORDERS, CELL_MAR, trpr)]
        for i, c in enumerate(cells):
            if kind == 'head':
                bd = ('<w:top w:val="single" w:color="000000" w:sz="12" w:space="0"/><w:left w:val="nil"/>'
                      '<w:bottom w:val="single" w:color="000000" w:sz="6" w:space="0"/><w:right w:val="nil"/>')
                jc = 'center'
            elif kind == 'last':
                bd = '<w:left w:val="nil"/><w:bottom w:val="single" w:color="000000" w:sz="12" w:space="0"/><w:right w:val="nil"/>'
                jc = aligns[i]
            else:
                bd = '<w:left w:val="nil"/><w:right w:val="nil"/>'
                jc = aligns[i]
            out.append('<w:tc><w:tcPr><w:tcW w:w="%d" w:type="dxa"/><w:tcBorders>%s</w:tcBorders>%s'
                       '<w:vAlign w:val="center"/></w:tcPr>' % (widths[i], bd, TC_MAR))
            out.append(P('<w:spacing w:line="240" w:lineRule="auto"/><w:jc w:val="%s"/>' % jc,
                         runs(c, sz=18, bold=(kind == 'head'))))
            out.append('</w:tc>')
        out.append('</w:tr>')
        return ''.join(out)

    x.append(row(header, 'head'))
    for i, rw in enumerate(rows):
        x.append(row(rw, 'last' if i == len(rows) - 1 else 'body'))
    x.append('</w:tbl>')
    return ''.join(x)


# ---------- 组装 ----------
out = []
for item in SPEC:
    t = item[0]
    if t == 'keep':
        blk = B[item[1]]
        if item[1] == 75:  # 表5：与正文新提法保持一致
            for a, b in [('基础热度奖励+产业实效附加奖励；落地成效专项奖', '基础热度奖励+转化实效附加奖励；增设中间档；递延兑付'),
                         ('总额与封顶约束；真实性核验；多元评审；动态优化', '总额与封顶约束；转化数据台账；真实性核验；多元评审')]:
                assert blk.count('>' + a + '<') == 1, a
                blk = blk.replace('>' + a + '<', '>' + b + '<')
        out.append(blk)
    elif t == 'title':
        out.append(P(PPR_TITLE, runs(item[1], sz=30, bold=True, hei=True)))
    elif t == 'abs':
        out.append(P('<w:spacing w:after="60"/>' + PPR_BODY,
                     '<w:r>%s<w:t>摘要　</w:t></w:r>' % rpr(None, bold=True, hei=True) + runs(item[1], sz=18)))
    elif t == 'kw':
        out.append(P('<w:spacing w:after="160"/>' + PPR_BODY,
                     '<w:r>%s<w:t>关键词　</w:t></w:r>' % rpr(None, bold=True, hei=True) + runs(item[1], sz=18)))
    elif t == 'h1':
        out.append(P(PPR_H1, runs(item[1], sz=28, bold=True, hei=True)))
    elif t == 'h2':
        out.append(P(PPR_H2, runs(item[1], sz=21, bold=True, hei=True)))
    elif t == 'p':
        out.append(P(PPR_BODY, runs(item[1])))
    elif t == 'tblcap':
        out.append(P(PPR_TBLCAP, runs(item[1], sz=21, bold=True, hei=True)))
    elif t == 'tblnote':
        out.append(P(PPR_TBLNOTE, runs(item[1], sz=18)))
    elif t == 'formula':
        out.append(P(PPR_FORMULA, runs(item[1], sz=21) + r('　　　　' + item[2], sz=21)))
    elif t == 'table':
        out.append(table(*item[1:]))
    elif t == 'refs':
        for k in order:
            out.append(P(PPR_REF, runs('[%d] %s' % (NUM[k], REFS[k]), sz=20, cites=False)))
    elif t == 'en_title':
        out.append(P('<w:spacing w:before="240" w:after="60"/><w:jc w:val="center"/>', r(item[1], sz=22, bold=True)))
    elif t == 'en_abs':
        out.append(P('<w:spacing w:after="100" w:line="300" w:lineRule="auto"/><w:jc w:val="both"/>',
                     r('Abstract:', sz=None, bold=True) + r(' ' + item[1], sz=None)))
    elif t == 'en_kw':
        out.append(P('<w:spacing w:after="100"/><w:jc w:val="both"/>',
                     r('Keywords:', sz=None, bold=True) + r(' ' + item[1], sz=None)))
    else:
        raise ValueError(t)
out.append(B[138])  # sectPr

new = head + '<w:body>' + ''.join(out) + '</w:body>' + tail
if os.path.exists(OUT_DIR):
    shutil.rmtree(OUT_DIR)
shutil.copytree('unpacked', OUT_DIR)
io.open(OUT_DIR + '/word/document.xml', 'w', encoding='utf8').write(new)
if os.path.exists('fig1-修订.png'):
    shutil.copy('fig1-修订.png', OUT_DIR + '/word/media/image1.png')

# 输出引文顺序，供修改说明使用
with io.open('refs-order.txt', 'w', encoding='utf8') as f:
    for k in order:
        f.write('%d\t%s\t%s\n' % (NUM[k], k, re.sub(r'【【|】】', '', REFS[k])))
unused = [k for k in REFS if k not in order and k not in DROPPED]
print('refs:', len(order), 'unused (not dropped):', unused)
