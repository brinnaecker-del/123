# -*- coding: utf-8 -*-
"""生成双向匿名审稿用的匿名稿。

用法：python3 review/make-anon.py <输入.docx> <输出.docx>

去掉：中文作者行、中文单位行（连同其上的基金项目脚注）、英文作者与单位段；
      footnotes.xml 中的基金项目脚注；文件属性中的作者、最后修改者与 WPS 保存记录（含用户 ID）。
保留：题名、摘要、正文、图表、参考文献、英文题名与摘要。
"""
import sys, re, zipfile
from lxml import etree

SRC, DST = sys.argv[1], sys.argv[2]
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
w = lambda t: '{%s}%s' % (W, t)
AUTHORS = ['巩艳红', '王展鹏', '赵子欢', 'GONG Yanhong', 'WANG Zhanpeng', 'ZHAO Zihuan']
UNIT = ['财经学院', 'School of Finance']

zin = zipfile.ZipFile(SRC)
files = {i.filename: zin.read(i.filename) for i in zin.infolist()}

# ---------- 正文 ----------
root = etree.fromstring(files['word/document.xml'])
body = root.find(w('body'))
text_of = lambda el: ''.join(t.text or '' for t in el.iter(w('t')))
removed, fn_ids = [], []
for p in list(body):
    if p.tag != w('p'):
        continue
    t = text_of(p)
    if any(a in t for a in AUTHORS) or any(u in t for u in UNIT):
        fn_ids += [r.get(w('id')) for r in p.iter(w('footnoteReference'))]
        body.remove(p)
        removed.append(t[:40])
assert len(removed) == 3, removed
files['word/document.xml'] = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)

# ---------- 基金项目脚注 ----------
fr = etree.fromstring(files['word/footnotes.xml'])
for fn in list(fr):
    if fn.get(w('id')) in fn_ids:
        fr.remove(fn)
assert '基金项目' not in etree.tostring(fr, encoding='unicode')
files['word/footnotes.xml'] = etree.tostring(fr, xml_declaration=True, encoding='UTF-8', standalone=True)

# ---------- 文件属性 ----------
core = files['docProps/core.xml'].decode('utf8')
core = re.sub(r'<dc:creator>.*?</dc:creator>', '<dc:creator></dc:creator>', core)
core = re.sub(r'<cp:lastModifiedBy>.*?</cp:lastModifiedBy>', '<cp:lastModifiedBy></cp:lastModifiedBy>', core)
files['docProps/core.xml'] = core.encode('utf8')
if 'docProps/custom.xml' in files:
    cus = files['docProps/custom.xml'].decode('utf8')
    cus = re.sub(r'<property [^>]*name="KSOTemplateDocerSaveRecord".*?</property>', '', cus, flags=re.S)
    files['docProps/custom.xml'] = cus.encode('utf8')

# ---------- 自检：整个文件包中不再出现作者、单位、基金信息 ----------
blob = b''.join(files[f] for f in files if f.endswith('.xml') or f.endswith('.rels')).decode('utf8', 'ignore')
for k in AUTHORS + UNIT + ['基金项目', 'glora', 'KSOTemplateDocerSaveRecord']:
    assert k not in blob, k

zout = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED)
for it in zin.infolist():
    zout.writestr(it, files[it.filename])
zout.close()
print('删除段落：', removed)
print('written', DST)
