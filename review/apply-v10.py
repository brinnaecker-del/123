# -*- coding: utf-8 -*-
# v10 投稿版：删除附表引用、表6扩为13项全表、参考文献按首次引用顺序重排、摘要标点
import sys, re, zipfile

SRC, DST = sys.argv[1], sys.argv[2]
zin = zipfile.ZipFile(SRC)
d = zin.read('word/document.xml').decode('utf8')

def sub1(old, new, label):
    global d
    n = d.count(old)
    assert n == 1, (label, n)
    d = d.replace(old, new)
    print('ok', label)

# 1 摘要多余逗号
sub1('MPI由0.393提高至0.754，；', 'MPI由0.393提高至0.754；', '摘要标点')

# 2 附表A2：改为在正文交代辅助序列来源
m = re.search(r'直接计算，其中，用于人均化与相对全国水平处理的</w:t></w:r>.*?<w:t>附表</w:t></w:r>.*?<w:t>A2</w:t></w:r>.*?<w:t>。</w:t></w:r>', d, re.S)
assert m and m.group(0).count('</w:p>') == 0
d = d[:m.start()] + ('直接计算；用于人均化与相对全国水平处理的西藏年末常住人口取自历年统计公报（2020年为第七次全国人口普查数），'
                     '全国城乡居民人均可支配收入取自国家统计局历年发布的居民收入和消费支出数据。</w:t></w:r>') + d[m.end():]
print('ok 附表A2')

# 3 附表A1 三处引用
sub1('结果见表6；表6列出分别来自安全、发展、生态三子系统的5项代表性指标，完整13项见附表A1。', '结果见表6。', 'A1-正文1')
sub1('其中13项设定有11项不少于3年（完整结果见附表A1）。', '其中13项设定有11项不少于3年。', 'A1-正文2')
sub1('最低的年数；全部13项结果见附表A1。', '最低的年数。', 'A1-表注')
sub1('表6　关键指标留一法（LOO）结果（节选）', '表6　13项指标留一法（LOO）结果', '表6标题')

# 4 表6扩为13行（数据取自作者附录A1，与原表5行逐项一致）
FULL = [
 ('S1 人均一般公共预算收入','0.400','0.755','7'),
 ('S2 城乡居民收入比与全国差距','0.392','0.769','8'),
 ('S3 居民医保人均财政补助标准','0.402','0.766','8'),
 ('S4 养老参保率','0.370','0.722','2'),
 ('D1 人均GDP相对全国水平','0.378','0.745','7'),
 ('D2 农村居民人均收入相对全国水平','0.371','0.732','9'),
 ('D3 外向度','0.395','0.791','2'),
 ('D4 人均接待游客','0.405','0.751','5'),
 ('D5 发电量','0.408','0.746','4'),
 ('E1 单位GDP能耗指数','0.426','0.770','6'),
 ('E2 森林覆盖率','0.439','0.740','5'),
 ('E3 空气质量优良天数比例','0.205','0.741','3'),
 ('E4 草原综合植被盖度','0.439','0.762','5'),
]
i = d.find('表6　13项指标留一法')
ts = d.find('<w:tbl>', i); te = d.find('</w:tbl>', ts) + len('</w:tbl>')
tbl = d[ts:te]
rows = re.findall(r'<w:tr[ >].*?</w:tr>', tbl, re.S)
assert len(rows) == 6
old = {re.findall(r'<w:t>([^<]*)</w:t>', r)[0]: re.findall(r'<w:t>([^<]*)</w:t>', r) for r in rows[1:]}
for k, *v in FULL:
    if k in old: assert old[k] == [k, *v], (k, old[k])
mid_tpl, last_tpl = rows[1], rows[-1]
def make(tpl, vals):
    tpl = re.sub(r' w14:paraId="[0-9A-F]+"', '', tpl)
    tpl = re.sub(r' w14:textId="[0-9A-F]+"', '', tpl)
    it = iter(vals)
    out = re.sub(r'<w:t>[^<]*</w:t>', lambda _: '<w:t>%s</w:t>' % next(it), tpl)
    assert next(it, None) is None
    return out
new_rows = [make(mid_tpl, r) for r in FULL[:-1]] + [make(last_tpl, FULL[-1])]
body_start = tbl.find(rows[1]); body_end = tbl.find(rows[-1]) + len(rows[-1])
d = d[:ts] + tbl[:body_start] + ''.join(new_rows) + tbl[body_end:] + d[te:]
print('ok 表6 13行')

# 5 参考文献：[14]—[16]与正文所述内容对应；[35]—[37]按首次引用先后排序
def ref_para(num):
    m = re.search(r'<w:p [^>]*>(?:(?!</w:p>).)*?<w:t>\[%d\] ' % num, d, re.S)
    s = m.start(); e = d.find('</w:p>', s) + len('</w:p>')
    # 确保匹配的是该段落本身的起点
    s = d.rfind('<w:p ', 0, m.end())
    return s, e
def reorder(nums, new_order):
    """nums: 原编号（连续段落）；new_order: 新顺序下依次放入的原编号"""
    global d
    spans = [ref_para(n) for n in nums]
    for a, b in zip(spans, spans[1:]): assert a[1] == b[0]
    paras = {n: d[s:e] for n, (s, e) in zip(nums, spans)}
    out = ''
    for newnum, oldnum in zip(nums, new_order):
        p = paras[oldnum].replace('<w:t>[%d] ' % oldnum, '<w:t>[%d] ' % newnum, 1)
        out += p
    d = d[:spans[0][0]] + out + d[spans[-1][1]:]
reorder([14, 15, 16], [15, 16, 14])   # 卜洁文、徐伍达、冯娜娜
reorder([35, 36, 37], [36, 37, 35])   # 陈爱东、罗绒战堆、孙勇
print('ok 参考文献重排')

# 正文角标：政策建议中的徐伍达 [16]→[15]；H2 的 [36][37]→[35][36]；S4 段 [35]→[37]
SUP = '<w:vertAlign w:val="superscript"/></w:rPr><w:t>[%d]</w:t>'
sub1('已有讨论</w:t></w:r><w:r><w:rPr><w:sz w:val="21"/><w:szCs w:val="21"/>' + SUP % 16,
     '已有讨论</w:t></w:r><w:r><w:rPr><w:sz w:val="21"/><w:szCs w:val="21"/>' + SUP % 15, '角标 徐伍达')
for o, n, ctx in [(36, 35, '禀赋'), (37, 36, '转化通道本身的重要性'), (35, 37, '维系边疆长期稳定的关键环节')]:
    sub1(ctx + '</w:t></w:r><w:r><w:rPr><w:sz w:val="21"/><w:szCs w:val="21"/>' + SUP % o,
         ctx + '</w:t></w:r><w:r><w:rPr><w:sz w:val="21"/><w:szCs w:val="21"/>' + SUP % n, '角标 %d→%d' % (o, n))

# 6 留一法段落“转移” 这个”中多余空格
sub1('<w:t>”</w:t></w:r><w:r><w:rPr><w:rFonts w:hint="eastAsia"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr><w:t>这个',
     '<w:t>”</w:t></w:r><w:r><w:rPr><w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr><w:t>这个', '多余空格')

# 7 原附表A3的有用信息并入§6(一)：地市财政自给率（数值与 review/F8-附录.docx 附表A3 一致）
sub1('可用于市场性投入的空间相应受到压缩。据此推断',
     '可用于市场性投入的空间相应受到压缩。地市层面的财政结构也与此相符：据七地市2024年统计公报与财政决算资料计算，'
     '除拉萨市（36.19%）外，其余六个地市（区）的财政自给率均低于11%，基层运转与公共服务主要依靠财政转移支付维系。据此推断',
     '§6(一) 补地市财政自给率')

# 8 表6首列加宽（13行指标名较长）：3000 + 1800 + 1800 + 2200 = 8800
i = d.find('表6　13项指标留一法'); ts = d.find('<w:tbl>', i); te = d.find('</w:tbl>', ts)
t = d[ts:te]
t = t.replace('<w:tblGrid><w:gridCol w:w="2200"/><w:gridCol w:w="2200"/><w:gridCol w:w="2200"/><w:gridCol w:w="2200"/></w:tblGrid>',
              '<w:tblGrid><w:gridCol w:w="3000"/><w:gridCol w:w="1800"/><w:gridCol w:w="1800"/><w:gridCol w:w="2200"/></w:tblGrid>')
def fix_row(m):
    k = [0]
    def w(_):
        k[0] += 1
        return '<w:tcW w:w="%d" w:type="dxa"/>' % {1: 3000, 2: 1800, 3: 1800, 4: 2200}[k[0]]
    return re.sub(r'<w:tcW w:w="2200" w:type="dxa"/>', w, m.group(0))
t = re.sub(r'<w:tr[ >].*?</w:tr>', fix_row, t, flags=re.S)
assert t.count('w:w="2200"') == len(re.findall(r'<w:tr[ >]', t)) + 1
d = d[:ts] + t + d[te:]
print('ok 表6列宽')

zout = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED)
# 9 图1、图2 换为重绘版（figures/build_figs.py；宽高比与原图一致，版面尺寸不变）
import os
FIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'figures')
MEDIA = {'word/media/image1.png': os.path.join(FIG, 'fig1.png'),
         'word/media/image2.png': os.path.join(FIG, 'fig2.png')}
for it in zin.infolist():
    if it.filename in MEDIA:
        data = open(MEDIA[it.filename], 'rb').read()
    else:
        data = d.encode('utf8') if it.filename == 'word/document.xml' else zin.read(it.filename)
    zout.writestr(it, data)
zout.close()
print('written', DST)
