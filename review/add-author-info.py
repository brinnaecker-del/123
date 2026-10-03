# -*- coding: utf-8 -*-
"""按《高原科学研究》投稿须知第4、6、7条补作者简介、稿件联系人与项目信息。

用法：python3 review/add-author-info.py <输入.docx> <输出.docx>
（流程：apply-v10.py → add-en-captions.py → 本脚本，均就地写回 v10）

- 首页脚注（原有基金项目）后接：作者简介（第一作者即通讯作者）、通讯作者。
- 文末（英文关键词之后）加：项目名称（须知第7条）、稿件联系人（须知第6条）。
信息由作者 2026-10-03 提供，存于 author-info.local.json（不入库）。
输出文件请用 *-含作者信息.docx 命名（已被 .gitignore 忽略）。
"""
import sys, copy, zipfile
from lxml import etree

SRC, DST = sys.argv[1], sys.argv[2]
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
w = lambda t: '{%s}%s' % (W, t)
XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'

# 个人信息（出生年份、电话、邮箱等）不入公开仓库：从同目录下被 .gitignore 忽略的 author-info.local.json 读取
import json, os
_info = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'author-info.local.json'), encoding='utf8'))
BIO, CORR, FUND, CONTACT = _info['BIO'], _info['CORR'], _info['FUND'], _info['CONTACT']

zin = zipfile.ZipFile(SRC)
INFOS = zin.infolist()
FILES = {i.filename: zin.read(i.filename) for i in INFOS}
zin.close()
text_of = lambda el: ''.join(t.text or '' for t in el.iter(w('t')))

def para_like(tpl_p, rpr, text):
    p = etree.Element(w('p'))
    ppr = tpl_p.find(w('pPr'))
    if ppr is not None:
        p.append(copy.deepcopy(ppr))
    r = etree.SubElement(p, w('r'))
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    t = etree.SubElement(r, w('t')); t.text = text; t.set(XML_SPACE, 'preserve')
    return p

# ---------- 首页脚注 ----------
fr = etree.fromstring(FILES['word/footnotes.xml'])
fund_fn = [fn for fn in fr if '基金项目' in text_of(fn)]
assert len(fund_fn) == 1
fn = fund_fn[0]
assert '作者简介' not in text_of(fn), '已补过'
p0 = fn.find(w('p'))
rpr = [r.find(w('rPr')) for r in p0.iter(w('r')) if r.find(w('t')) is not None][0]
last = p0
for s in (BIO, CORR):
    np_ = para_like(p0, rpr, s)
    last.addnext(np_); last = np_
FILES['word/footnotes.xml'] = etree.tostring(fr, xml_declaration=True, encoding='UTF-8', standalone=True)

# ---------- 文末 ----------
root = etree.fromstring(FILES['word/document.xml'])
body = root.find(w('body'))
kw = [p for p in body if p.tag == w('p') and text_of(p).startswith('Keywords:')]
assert len(kw) == 1
tpl = kw[0]
plain_rpr = None
for r in tpl.iter(w('r')):
    if r.find(w('t')) is not None and (r.find(w('rPr')) is None or r.find(w('rPr')).find(w('b')) is None):
        plain_rpr = r.find(w('rPr'))
        break
last = tpl
for s in (FUND, CONTACT):
    np_ = para_like(tpl, plain_rpr, s)
    last.addnext(np_); last = np_
FILES['word/document.xml'] = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)

zout = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED)
for it in INFOS:
    zout.writestr(it, FILES[it.filename])
zout.close()
print('written', DST)
