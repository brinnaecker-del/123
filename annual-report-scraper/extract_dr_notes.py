"""
从年报 PDF 的财务报表附注中提取数据资源的明细（配合 extract_data_resources.py、extract_financials.py 使用）

用法一：在 PyCharm 里右键本文件 → 运行。读取 REPORT_DIR 下 2024年报、2025年报 两个文件夹里的全部 PDF。
用法二：python extract_dr_notes.py 数据资源页面.zip [数据资源提取结果.xlsx]
        读取 export_dr_pages.py 导出的页面（不需要 PDF），结果写在 zip 旁边；给出提取结果表时，逐份与资产负债表核对。
结果存为「数据资源附注明细.xlsx」：
  · 无形资产明细：每份年报一行——确认为无形资产的数据资源：账面原值（期初、本期增加及其中购置/内部研发/企业合并、本期减少及其中处置、
                  期末）、累计摊销（期初、本期增加及其中计提、本期减少、期末）、减值准备、账面价值（期末、期初），均已折算成元；
                  取自哪一页、表格样式、单位，三项勾稽（原值、累计摊销的期初+增加−减少=期末；原值−累计摊销−减值=账面价值）；
  · 摊销政策：数据资源无形资产的使用寿命（年）与摊销方法，以及原文；会计估计变更的线索；
  · 开发支出：附注开发支出表中写有「数据资源」的行（原文与各列金额），供人工核对；
  · 明细行：每个数取自哪一页、哪一行原文；
  · 诊断：没取到明细的年报里，同时含「数据资源」与「摊销」或「原值」的页面原文（每个词带横向位置）。
解析要点：窄列里折成两三行的项目名和数字按「逻辑行」拼回；表头不并入「单位：元」等行；只列非零行、没有「一、账面原值」小标题的
专表按顺序推断区块；表格跨页时接着读（下一页开头的「额」接在上一页末行后面）；单位取表头上方最近的说明或前面的
「除特别注明外，金额单位为……」；「软件及数据资源」这类合并列、存货里的数据资源专表不取；横排（转置）的无形资产表单独处理。
需要先安装：pip install pymupdf openpyxl
"""

import json
import re
import sys
import unicodedata
import zipfile
from pathlib import Path

try:
    import openpyxl
except ImportError:
    print("缺少工具包，请先在终端运行：pip install pymupdf openpyxl")
    input("按回车键退出…")
    sys.exit(1)

# ============================ 需要改的只有这里 ============================
REPORT_DIR = r"E:\数据资产入表年报"      # 年报所在文件夹
FOLDERS = ["2024年报", "2025年报"]       # 要处理的子文件夹
# ========================================================================

UNITS = {"元": 1, "千元": 1e3, "万元": 1e4, "百万元": 1e6, "亿元": 1e8}
U = r"(百万元|千元|万元|亿元|元)"
UNIT_EXPLICIT = re.compile(r"(?:金额单位|单位)(?:均为|均|为)?[:：]?(?:人民币)?" + U + r"|以人民币" + U + r"(?:为单位|列示)")
UNIT_BARE = re.compile(r"人民币(百万元|千元|万元|亿元)")
NUM_RE = re.compile(r"^\(?-?\d[\d,]*(?:\.\d*)?\)?$")          # 允许「539,304,932.」这类折行的前半截
DASH_RE = re.compile(r"^[-—–－/]+$")
DATE_RE = re.compile(r"(20\d\d)年(\d{1,2})月(\d{1,2})日")
YEAR_RE = re.compile(r"^(20\d\d)(年(度)?)?$")
OTHER_HEADERS = ("土地使用权", "软件", "专利", "非专利技术", "商标", "特许经营权", "著作权", "知识产权", "其他", "域名", "客户关系",
                 "技术", "采矿权", "使用权", "经营权", "版权", "系统", "资质", "频谱", "电路", "海域", "林权", "排污权", "车牌",
                 "渠道", "许可", "合同权益", "品牌", "牌照", "专营权", "收费权", "数据库", "平台", "IP", "游戏")
ACQ = ("外购", "自行开发", "自主研发", "自研", "内部研发", "其他方式", "购入", "外部购买", "自行研发", "研发形成")
TOTAL_RE = re.compile(r"(合计|总计|小计)$")
SECTIONS = (("原值", r"(账面原值|账面原价|原值|原价|成本)(合计)?$"), ("摊销", r"累计摊销(额|金额)?(合计)?$"),
            ("减值", r"减值准备(额|金额)?(合计)?$"), ("净值", r"(账面价值|账面净值|净值|净额)(合计)?$"))
LABEL_HEAD = re.compile(r"^(项目|项目名称|类别|类型|名称|资产类别|20\d\d|20\d\d年度?|年|年度|本集团|本行|本银行|本公司|本集团及本公司|合并)$")
ORDINAL = re.compile(r"^(\d{1,2}[.、．]|[(（]\d{1,2}[)）]?|\d{1,2}[)）]|[一二三四五六七八九十]+[、.．]|[(（][a-zA-Z一二三四五六七八九十][)）])")
ORD_ONLY = re.compile(r"^(\d{1,2}[.、．]|[(（]?\d{1,2}[)）]|[(（]\d{1,2}|[一二三四五六七八九十]+[、.．])$")
METHODS = (("年数总和法", r"年数总和"), ("双倍余额递减法", r"双倍余额"), ("工作量法", r"工作量法|产量法"),
           ("直线法", r"直线法|平均年限法|年限平均法|平均摊销|分期平均|直线摊销"))
ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def norm(s):
    return unicodedata.normalize("NFKC", s)


def compact(s):
    return re.sub(r"\s+", "", norm(s))


class W:
    """页面上的一个词：x0, x1, 纵向中心 y, 上下边 y0/y1, 文字 t。"""
    __slots__ = ("x0", "x1", "y", "y0", "y1", "t")

    def __init__(self, x0, y0, x1, y1, t):
        self.x0, self.x1, self.y0, self.y1, self.t = x0, x1, y0, y1, t
        self.y = (y0 + y1) / 2

    @property
    def c(self):
        return (self.x0 + self.x1) / 2


GLUED = re.compile(r"\(-?[\d,]+(?:\.\d+)?\)|-?[\d,]+(?:\.\d+)?|-")


def split_glued(w):
    """「(1,515,964,496)(126,569,080)-」这类粘在一起的几个数拆开，按字符数分配横坐标。"""
    parts = GLUED.findall(w.t)
    if len(parts) < 2 or "".join(parts) != w.t or ")(" not in w.t and ")-" not in w.t and "-(" not in w.t:
        return [w]
    out, x, step = [], w.x0, (w.x1 - w.x0) / len(w.t)
    for p in parts:
        out.append(W(x, w.y0, x + step * len(p), w.y1, p))
        x += step * len(p)
    return out


def page_rows(page):
    """把页面上的词按纵坐标拼成一行行（纵向中心相差不超过 3 点算同一行），每行从左到右。"""
    ws = [W(w[0], w[1], w[2], w[3], norm(w[4]).strip()) for w in page.get_text("words")]
    ws = [p for w in ws for p in split_glued(w)]
    ws = sorted((w for w in ws if w.t), key=lambda w: (w.y, w.x0))
    rows, cur, cy = [], [], None
    for w in ws:
        if cur and abs(w.y - cy) > 3:
            rows.append(sorted(cur, key=lambda w: w.x0))
            cur = []
        if not cur:
            cy = w.y
        cur.append(w)
    if cur:
        rows.append(sorted(cur, key=lambda w: w.x0))
    return rows


def row_text(row):
    return "".join(w.t for w in row)


def to_num(t):
    if DASH_RE.match(t):
        return 0.0
    if NUM_RE.match(t):
        v = float(t.strip("()-").replace(",", ""))
        return -v if (t.startswith("(") or t.startswith("-")) else v
    return None


FRAG_RE = re.compile(r"^\(?-?(?:\d[\d,]*\.?\d*|\.\d+)\)?$")


def is_value(t):
    return to_num(t) is not None or bool(FRAG_RE.match(t))


def in_values(w, lb):
    """数值区的词：中心在项目列右边，或是右边界伸进数值区的数字（宽数字常向左越过列标题）。"""
    return w.c >= lb or (w.x1 > lb + 2 and NUM_RE.match(w.t) is not None and not YEAR_RE.match(w.t))


def in_label(w, lb):
    """项目名区的词；负数两边单独排版、落在项目列右侧的括号不算。"""
    return not in_values(w, lb) and not (w.t in ("(", ")", "（", "）") and w.x0 > lb - 160)


def has_numbers(row):
    """行内有金额（年份、破折号不算）。"""
    return any(NUM_RE.match(w.t) and not YEAR_RE.match(w.t) for w in row)


def section_of(label):
    base = re.sub(r"^[一二三四五六七八九十]+[、.．]|^\d+[、.．]|^其中[:：]", "", label).rstrip(":：")
    base = re.sub(r"\(.*?\)|（.*?）", "", base)
    for name, pat in SECTIONS:
        if re.match(pat, base) or re.search(r"^(无形资产|数据资源)" + pat, base):
            return name
    return None


def classify(label, year):
    """返回 ('open'|'close'|'add'|'add_buy'|'add_rd'|'add_merge'|'sub'|'sub_disp'|'other_date'|None)。"""
    m = DATE_RE.search(label)
    if m:
        yy, mm, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if (yy == year - 1 and mm == 12) or (yy == year and mm == 1 and dd == 1):
            return "open"
        if yy == year and mm == 12:
            return "close"
        return "other_date"
    s = re.sub(r"^[一二三四五六七八九十\d]+[、.．]|^[(（]\d+[)）]|^[(（]?[一二三四五六七八九十]+[)）]|^[(（][a-z][)）]|^其中[:：]?", "", label)
    s = re.sub(r"\(.*?\)|（.*?）", "", s)
    s = re.sub(r"[()（）:：]", "", s)
    if re.match(r"^(期初|年初|上年年末|上年末|本期期初|本年年初)(余额|数|账面价值|金额|账面余额)?$", s) or s in ("期初账面价值", "年初账面价值"):
        return "open"
    if re.match(r"^(期末|年末|本期期末|本年年末)(余额|数|账面价值|金额|账面余额)?$", s) or s in ("期末账面价值", "年末账面价值"):
        return "close"
    if re.match(r"^(本期|本年)?(增加|增加额)(金额|额)?$", s):
        return "add"
    if re.match(r"^(本期|本年)?(计提|摊销)(金额|额)?$", s):
        return "add_prov"
    if re.search(r"购置|购入|外购|购买", s):
        return "add_buy"
    if re.search(r"内部研发|自行开发|研发支出转入|开发支出转入|由开发支出|内部开发|自主研发|研发转入", s):
        return "add_rd"
    if re.search(r"企业合并|合并增加|非同一控制", s):
        return "add_merge"
    if re.match(r"^(本期|本年)?(减少|减少额)(金额|额)?$", s):
        return "sub"
    if re.search(r"处置|报废|出售|终止确认|失效", s):
        return "sub_disp"
    return None


def is_unit_row(text):
    return bool(UNIT_EXPLICIT.search(text) or UNIT_BARE.search(text) or "币种" in text)


def is_heading(text):
    """附注小标题或表题（如「(2)确认为无形资产的数据资源」「26、无形资产」），以及「适用/不适用」。"""
    if re.search(r"适用", text) and len(text) < 20:
        return True
    m = ORDINAL.match(text)
    if not m or len(text) - m.end() < 2:                              # 「(1」这类折行残片不算标题
        return False
    rest = text[m.end():]
    if any(v.startswith(rest) for v in ITEM_WORDS):                   # 「1.期初余」这类折行的项目名前半截
        return False
    if re.search(r"余额|增加|减少|计提|摊销|处置|转|折算|差额|汇率|外币|合并|购置|研发|其他|账面|价值|调整|重分类|划|终止|失效|报废|出售|变动|建造|在建|投入|捐赠|收购|置换|交换|重组|分配", rest):
        return False                                                  # 表内的变动项目，如「4.外币报表折算差额」
    return classify(text, 0) is None and section_of(text) is None


ITEM_WORDS = ("期初余额", "期末余额", "年初余额", "年末余额", "本期增加金额", "本期减少金额", "本年增加金额", "本年减少金额", "本年增加",
              "本年减少", "期末账面价值", "期初账面价值", "年末账面价值", "年初账面价值", "计提", "购置", "内部研发", "企业合并增加",
              "处置", "其他增加", "其他减少", "投资性房地产转入", "转入存货", "账面原值", "累计摊销", "减值准备", "账面价值", "其他",
              "本期计提", "本年计提", "外购", "自行开发", "报废", "失效且终止确认", "其他转出", "转出")


# ---------------------------------------------------------------- 表头
def header_block(rows, i):
    """以 rows[i] 为核心，向上下合并紧邻的、没有金额、也不是单位/标题/区块名/表体项目的行。
    表体项目从项目列（最左）起头；数据列的表头在项目列右边，即使写着「外购」「自行开发」也不算项目。"""
    near = [w for k in range(max(0, i - 4), min(len(rows), i + 5)) if not has_numbers(rows[k]) for w in rows[k]]
    head = [w for w in near if LABEL_HEAD.match(compact(w.t))]
    zone = (max(w.x1 for w in head) + 10) if head else (min(w.x0 for w in rows[i]) - 5)

    def ok(j):
        r = rows[j]
        t = compact(row_text(r))
        lz = compact("".join(w.t for w in r if w.x0 < zone))           # 项目列里的文字
        item = bool(lz) and not LABEL_HEAD.match(lz) and bool(ORDINAL.match(lz) or classify(lz, 0) is not None or section_of(lz))
        stray = head and all(w.x1 < zone - 10 for w in r)               # 项目列里的折行残片（如上一页末行的「加」）
        return (not has_numbers(r) and not is_unit_row(t) and not is_heading(t) and section_of(t) is None
                and not item and not stray and len(t) < 120)
    if not ok(i):
        return None
    block = [i]
    for step in (-1, 1):
        j, last = i + step, i
        while 0 <= j < len(rows) and abs(rows[j][0].y - rows[last][0].y) <= 16 and ok(j):
            block.append(j)
            last, j = j, j + step
    return sorted(block)


def header_columns(rows, block):
    toks = sorted((w for j in block for w in rows[j]), key=lambda w: (w.x0, w.y))
    cols = []
    for w in toks:
        for c in cols:
            if min(w.x1, c[1]) - max(w.x0, c[0]) > 0:            # 横向重叠：同一列的上下两行
                c[0], c[1] = min(c[0], w.x0), max(c[1], w.x1)
                c[2].append(w)
                break
        else:
            cols.append([w.x0, w.x1, [w]])
    out = []
    for c in sorted(cols):
        name = "".join(w.t for w in sorted(c[2], key=lambda w: (round(w.y), w.x0)))
        out.append((c[0], c[1], compact(name)))
    k = 0
    while k + 1 < len(out):
        a, b = out[k], out[k + 1]
        if a[2] + b[2] in ("项目", "合计", "小计", "总计", "名称", "软件", "其他") and b[0] - a[1] < 25:
            out[k:k + 2] = [(a[0], b[1], a[2] + b[2])]
        else:
            k += 1
    return out


def mixed(name):
    """「软件及数据资源」这类与其他资产合并的列，不是单独的数据资源列。"""
    rest = re.sub(r"数据资源|无形资产|其中|外购的?|自行开发的?|自主研发的?|其他方式取得的?|[:：()（）\d、]", "", name)
    return any(h in rest for h in OTHER_HEADERS if h != "其他")


def find_tables(rows):
    """找本页以「数据资源」为一列的无形资产表（列式），或「确认为无形资产的数据资源」专表（各列为取得方式与合计）。"""
    out, used = [], set()
    for i, r in enumerate(rows):
        if i in used:
            continue
        near = compact("".join(row_text(rows[k]) for k in range(max(0, i - 2), min(len(rows), i + 3))))
        if "数据资源" not in near and not ("数据" in near and "资源" in near):
            continue
        block = header_block(rows, i)
        if not block:
            continue
        cols = header_columns(rows, block)
        if len(cols) < 2 and not (cols and "数据资源" in cols[0][2] and re.search(r"无形资产|" + "|".join(ACQ), cols[0][2])
                                  and cols[0][0] > 200):
            continue                                                   # 只有一列的专表（如「自主研发的数据资源无形资产」）也要
        drx = min((c[0] for c in cols if "数据资源" in c[2]), default=None)
        if drx is None:
            continue
        lab = [c for c in cols if LABEL_HEAD.match(c[2]) and c[1] < drx]   # 项目列表头（可能拆成「2024」「年」两段），须在数据资源列左边
        label_x1 = max((c[1] for c in lab), default=None)
        data = [c for c in cols if c not in lab and (label_x1 is None or c[0] > label_x1)]
        tot = [c for c in data if TOTAL_RE.search(c[2])]
        dr = [c for c in data if "数据资源" in c[2] and c not in tot and not mixed(c[2])]
        if not dr or any("存货" in c[2] for c in data):
            continue                                                   # 存货里的数据资源专表不是这里要的
        rest = [c for c in data if c not in dr and c not in tot and not re.match(r"^(附注|注)$", c[2])]
        dedicated = all(any(a in c[2] for a in ACQ) for c in rest) or not rest
        if dedicated:
            dr = dr + [c for c in rest if c not in dr]                # 「自行开发的数据」这类折行后缺了「资源」二字的取得方式列
        if dedicated:
            if len(dr) == 1:
                target, style = dr[0], "数据资源专表"
            elif tot:
                target, style = tot[-1], "数据资源专表"
            else:
                target, style = dr, "数据资源专表"           # 多列相加
        else:
            if not any(any(h in c[2] for h in OTHER_HEADERS) for c in rest) and len(rest) > 0 and not tot:
                continue
            target, style = dr[0], "无形资产表数据资源列"
        lb = min(c[0] for c in data) - 3
        used.update(block)
        out.append({"row": max(block), "head": min(block), "cols": data, "target": target, "style": style, "lb": lb})
    return out


# ---------------------------------------------------------------- 表体
def assign_col(w, cols):
    best, bk = None, None
    for k, (c0, c1, _) in enumerate(cols):
        ov = min(w.x1, c1) - max(w.x0, c0)
        d = 0 if ov > 0 else min(abs(w.x1 - c1), abs(w.c - (c0 + c1) / 2), abs(w.x0 - c0))
        key = (-(ov if ov > 0 else 0), d)
        if bk is None or key < bk:
            best, bk = k, key
    return best


def item_start(lab):
    return bool(ORDINAL.match(lab) or re.match(r"^(其中|20\d\d|期初|期末|年初|年末|本期|本年|上年)", lab) or section_of(lab))


def complete(lab, year):
    return classify(lab, year) is not None or section_of(lab) is not None


def continuation(prev, lab, year):
    if lab[:1] in ")）":
        return True
    if re.match(r"^(余额|金额|额|数|面价值|账面价值|价值|加金额|少金额|值准备|摊销|原值)$", lab) and not complete(lab, year):
        return True
    if re.match(r"^(增加|减少)(金额|额)?$", lab) and re.search(r"(合并|其他|转入|转出)$", prev) and not DATE_RE.search(prev):
        return True                                                    # 「(3)企业合并」+「增加」
    if ORD_ONLY.match(prev) or prev[-1:] in "(（":
        return True
    if item_start(lab) or complete(prev, year):
        return False
    return True


class LRow:
    __slots__ = ("label", "y0", "y1", "vals", "raw", "carried")

    def __init__(self, label, y0, y1, raw):
        self.label, self.y0, self.y1, self.vals, self.raw, self.carried = label, y0, y1, [], raw, False


def logical_rows(body, lb, year, page_h, carry=None):
    """把表体的物理行合成逻辑行：折行的项目名接起来；只有数字的行按纵向距离归到最近的项目行。
    carry 是上一页末尾没写完的项目行（如「1.期初余」），本页开头的「额」接在它后面。"""
    lrows, cur, values = [], None, []
    if carry is not None:
        cur = LRow(carry.label, -1000.0, -1000.0, carry.raw)
        cur.vals = list(carry.vals)
        cur.carried = True
        lrows.append(cur)
    for r in body:
        if page_h and (r[0].y > page_h * 0.94 or r[0].y < page_h * 0.05):
            continue                                                   # 页眉页脚
        lab = compact("".join(w.t for w in r if in_label(w, lb)))
        vals = [w for w in r if in_values(w, lb) and is_value(w.t)]
        if lab:
            if cur is not None and continuation(cur.label, lab, year):
                cur.label += lab
                if cur.y0 < -999:
                    cur.y0 = r[0].y
                cur.y1 = max(cur.y1, r[0].y)
                cur.raw += " | " + row_text(r)
            else:
                cur = LRow(lab, r[0].y, r[0].y, row_text(r))
                lrows.append(cur)
        values += vals
    if not lrows:
        return lrows
    for v in values:
        best, bd = None, None
        for k, L in enumerate(lrows):
            d = 0 if L.y0 - 1.5 <= v.y <= L.y1 + 1.5 else min(abs(v.y - L.y0), abs(v.y - L.y1))
            if bd is None or d < bd - 0.5:
                best, bd = k, d
        if bd is not None and bd <= 14:
            lrows[best].vals.append(v)
    return lrows


def cell_value(frags):
    """同一逻辑行、同一列的若干片段：按纵向顺序拼接（折行的数字），拼不成再取第一个。"""
    if not frags:
        return None
    frags = sorted(frags, key=lambda w: (w.y, w.x0))
    if len(frags) > 1:
        s = "".join(w.t for w in frags)
        v = to_num(s)
        if v is not None:
            return v
    return to_num(frags[0].t)


def is_stop(r, lb, year):
    """表格到此结束：注释、下一个小标题、跨列的整段文字。只看项目名部分，破折号也算有数。"""
    label = compact("".join(w.t for w in r if in_label(w, lb)))
    vals = [w for w in r if in_values(w, lb) and is_value(w.t)]
    if label.startswith("注") or label.startswith("说明") or label.startswith("其他说明"):
        return True
    if not vals and label and is_heading(label):
        return True
    wide = [w for w in r if in_values(w, lb) and not is_value(w.t) and len(w.t) >= 6]
    if wide and not vals:                                             # 跨列的整段文字
        return True
    return False


def read_table(rows, tab, year, unit, page_no, state=None, page_h=None):
    """读一张表（或其在下一页的续表），返回 (res, lines, state)。state 记录区块与期初是否已读，供跨页续读。"""
    cols, target, lb = tab["cols"], tab["target"], tab["lb"]
    st = state or {"sec": None, "seen_open": {}, "closed": set(), "res": {}, "lines": []}
    res, lines = st["res"], st["lines"]
    start = tab["row"] + 1
    body = []
    st["ended"] = False
    for r in rows[start:]:
        t = compact(row_text(r))
        vals = [w for w in r if in_values(w, lb) and is_value(w.t)]
        if body and (is_stop(r, lb, year) or ("数据资源" in t and not vals and len(r) >= 2 and section_of(t) is None
                                               and classify(t, year) is None)):
            st["ended"] = True
            break
        if not body and not has_numbers(r) and not complete(compact("".join(w.t for w in r if in_label(w, lb))), year) and is_stop(r, lb, year):
            continue
        body.append(r)
    tidx = [i for i, c in enumerate(cols) if (c is target) or (isinstance(target, list) and c in target)]
    lrows = logical_rows(body, lb, year, page_h, carry=st.pop("carry", None))
    if lrows and not st["ended"] and not complete(lrows[-1].label, year) and not lrows[-1].carried:
        st["carry"] = lrows.pop()                                      # 本页最后一行没写完，留到下一页接上
    for L in lrows:
        per = {}
        for v in L.vals:
            per.setdefault(assign_col(v, cols), []).append(v)
        sec = section_of(L.label) if not L.vals else None
        if sec:
            st["sec"] = sec
            st["seen_open"][sec] = True                                # 出现「其他日期」行时再改为 False（银行的两年滚动表）
            st["closed"].discard(sec)
            continue
        kind = classify(L.label, year)
        nv = bool(re.search(r"账面价值|账面净值|净值|净额", L.label))
        if kind and kind != "other_date" and not nv:
            if st["sec"] is None:                                      # 表里没有「一、账面原值」这类小标题（只列非零行）
                st["sec"], st["implicit"] = "原值", True
                st["seen_open"]["原值"] = True
            elif st.get("implicit") and st["sec"] in st["closed"] and st["sec"] in ("原值", "摊销"):
                st["sec"] = {"原值": "摊销", "摊销": "减值"}[st["sec"]]
                st["seen_open"][st["sec"]] = True
        if kind in ("open", "close") and nv and st["sec"] != "净值":
            st["sec"] = "净值"                                        # 没有「四、账面价值」小标题，直接列期末/期初账面价值
            st["seen_open"]["净值"] = False
            st["closed"].discard("净值")
        if st["sec"] is None or st["sec"] in st["closed"]:
            continue
        if kind is None:
            continue
        vs = [cell_value(per.get(i, [])) for i in tidx]
        v = sum(x for x in vs if x is not None) if any(x is not None for x in vs) else 0.0   # 本列空白：该项为零
        v = abs(v) * UNITS[unit]
        sec = st["sec"]
        if kind == "open":
            st["seen_open"][sec] = True
            res[f"{sec}_期初"] = v
            lines.append((page_no, sec, kind, L.raw))
            if sec == "净值" and "净值_期末" in res:
                st["ended"] = True
                break
            continue
        if kind == "close":
            if sec == "净值" or st["seen_open"].get(sec):
                res[f"{sec}_期末"] = v
                lines.append((page_no, sec, kind, L.raw))
                if sec != "净值":
                    st["closed"].add(sec)
                elif "净值_期初" in res:
                    st["ended"] = True
                    break
            continue
        if kind == "other_date":
            st["seen_open"][sec] = False
            continue
        if not st["seen_open"].get(sec) and sec != "净值":
            continue
        key = {"add": "增加", "add_buy": "增加_购置", "add_rd": "增加_内部研发", "add_merge": "增加_企业合并", "add_prov": "增加_计提",
               "sub": "减少", "sub_disp": "减少_处置"}[kind]
        if kind in ("add_buy", "add_rd", "add_prov"):
            res[f"{sec}_{key}"] = res.get(f"{sec}_{key}", 0) + v
        elif not (v == 0 and res.get(f"{sec}_{key}")):                 # 后面重复出现的空白行不覆盖已读到的数
            res[f"{sec}_{key}"] = v
        lines.append((page_no, sec, kind, L.raw))
    return res, lines, st


MOVE_COLS = (("open", r"^(期初|年初|上年年末|上年末)"), ("add", r"^(本期|本年)?增加"), ("sub", r"^(本期|本年)?减少"), ("close", r"^(期末|年末)"),
             ("merge", r"^合并"), ("fx", r"^外币|^汇率|折算"))


def read_row_style(rows, year, unit, page_no):
    """行式无形资产表：各类资产占一行，列为期初、本期增加、本期减少、期末；取「数据资源」那几行。"""
    for i, r in enumerate(rows):
        hit = {}
        for w in r + (rows[i - 1] if i and not has_numbers(rows[i - 1]) and abs(rows[i - 1][0].y - r[0].y) < 8 else []):
            t = compact(w.t)
            for k, pat in MOVE_COLS:
                if k not in hit and re.match(pat, t):
                    hit[k] = (w.x0, w.x1)
        if len(hit) < 3 or has_numbers(r):
            continue
        hcols = [(x0, x1, k) for k, (x0, x1) in sorted(hit.items(), key=lambda kv: kv[1][0])]
        lb = min(c[0] for c in hcols) - 4
        res, sec, lines = {}, None, []
        for rr in rows[i + 1:]:
            label = compact("".join(w.t for w in rr if in_label(w, lb)))
            cells = [w for w in rr if in_values(w, lb) and is_value(w.t)]
            base = re.sub(r"^[一二三四五六七八九十]+[、.．]|^\d+[、.．]|^其中[:：]", "", label)
            s2 = section_of(base) if "数据资源" not in base else None
            if s2:
                sec = s2
                continue
            if sec and "数据资源" in base and cells:
                for w in cells:
                    k = hcols[assign_col(w, hcols)][2]
                    key = {"open": "期初", "add": "增加", "sub": "减少", "close": "期末", "merge": "增加_企业合并", "fx": "外币折算"}[k]
                    v = to_num(w.t)
                    if v is not None:
                        res[f"{sec}_{key}"] = abs(v) * UNITS[unit]
                lines.append((page_no, sec, "行式", row_text(rr)))
        if len(res) >= 3:
            return res, lines
    return {}, []


T_COLS = (("期初", r"^期初余额$|^年初余额$"), ("增加", r"^本期增加金额$|^本年增加$"), ("增加_购置", r"^购置$"),
          ("增加_内部研发", r"^(自主研发形成|内部研发)$"), ("增加_企业合并", r"^企业合并增加$"), ("减少", r"^本期减少金额$|^本年减少$"),
          ("减少_处置", r"^处置$"), ("期末", r"^期末余额$|^年末余额$"), ("增加_计提", r"^计提$"),
          ("净值_期末", r"^期末账面价值$"), ("净值_期初", r"^期初账面价值$"))


def read_transposed(rows, unit, page_no):
    """转置的无形资产表（页面横排）：各变动项目为列，资产类别为行，「一、账面原值」「二、累计摊销」等写在列标题里。"""
    secs = []
    for r in rows:
        for w in r:
            t = compact(w.t)
            m = re.match(r"^[一二三四]、(账面原值|累计摊销|减值准备|账面价值)", t)
            if m:
                secs.append((w.x0, {"账面原值": "原值", "累计摊销": "摊销", "减值准备": "减值", "账面价值": "净值"}[m.group(1)]))
    if len({s for _, s in secs}) < 2:
        return {}, []
    secs.sort()
    cols = []
    for r in rows:
        for w in r:
            t = compact(w.t)
            for key, pat in T_COLS:
                if re.match(pat, t):
                    sec = [s for x, s in secs if x <= w.x0 + 2]
                    sec = sec[-1] if sec else "原值"
                    name = key if key.startswith("净值") else f"{sec}_{key}"
                    cols.append((w.x0, w.x1, name))
    if len(cols) < 5:
        return {}, []
    lab = [(r, w) for r in rows for w in r if compact(w.t) == "数据资源"]
    if not lab:
        return {}, []
    r0, w0 = lab[0]
    res, raw = {}, []
    for r in rows:
        if not (w0.y - 25 < r[0].y <= w0.y + 1):
            continue
        for w in r:
            if w.x0 > w0.x1 and NUM_RE.match(w.t):
                k = assign_col(w, cols)
                c0, c1, name = cols[k]
                if min(w.x1, c1) - max(w.x0, c0) > 0:
                    res[name] = abs(to_num(w.t)) * UNITS[unit]
                    raw.append(f"{name}={w.t}")
    return (res, [(page_no, "转置表", "转置", "数据资源 " + " ".join(raw))]) if len(res) >= 3 else ({}, [])


TXT_RE = {"原值_期末": r"原值(?:为|是)?(?:人民币)?([\d,.]+)" + U,
          "摊销_期末": r"累计摊销(?:为|是)?(?:人民币)?([\d,.]+)" + U,
          "净值_期末": r"(?:净值|账面价值|净额)(?:为|是)?(?:人民币)?([\d,.]+)" + U}


NET_TXT = re.compile(r"(无形资产[^。]{0,30}?数据资源|数据资源[^。]{0,10}?无形资产)[^。]{0,30}?(?:账面价值|账面净值|净值|余额|金额)?(?:为|约|共计|合计)?"
                     r"(?:人民币)?约?([\d,]+(?:\.\d+)?)\s*" + U)


def read_text_net(pages):
    """只有一句话的披露，如「其他无形资产中包含数据资源约人民币1,809万元」「确认为无形资产的数据资源的账面价值为人民币135.36万元」。"""
    for pno, rows, t in pages:
        m = NET_TXT.search(t)
        if m:
            return {"净值_期末": float(m.group(2).replace(",", "")) * UNITS[m.group(3)]}, [(pno, "文字", "文字披露", m.group(0)[:200])]
    return {}, []


def read_text_disclosure(pages):
    for pno, rows, t in pages:
        for m in re.finditer(r"数据资源[^。]{0,120}?(原值|累计摊销|账面价值|净值)[^。]*。", t):
            seg = m.group(0)
            res = {}
            for k, pat in TXT_RE.items():
                mm = re.search(pat, seg)
                if mm:
                    res[k] = float(mm.group(1).replace(",", "")) * UNITS[mm.group(2)]
            if len(res) >= 2:
                return res, [(pno, "文字", "文字披露", seg[:200])]
    return {}, []


# ---------------------------------------------------------------- 摊销政策
YEARS_RE = re.compile(r"(\d{1,2}(?:\.\d)?)(?:\s*[-－~～至到]\s*(\d{1,2}(?:\.\d)?))?\s*年")


def policy(rows_by_page):
    hits = []
    for pno, rows in rows_by_page:
        texts = [compact(row_text(r)) for r in rows]
        for k, t in enumerate(texts):
            if "数据资源" not in t:
                continue
            ctx = t if len(t) > 12 else t + "".join(texts[k + 1:k + 2])
            seg = ctx[ctx.index("数据资源"):]
            seg = re.split(r"[。；;]", seg)[0][:80]
            seg = cut_other(seg)
            y = YEARS_RE.search(seg)
            meth = next((m for m, pat in METHODS if re.search(pat, seg)), None)
            if not y and not meth:
                continue
            if y and not re.search(r"使用寿命|使用年限|摊销|受益|年限|期限|年数|\d年", seg):
                continue
            if y and re.search(r"20\d\d年|月|日", seg[y.start() - 2:y.end() + 2]):
                y = None
            hits.append((pno, seg, y.group(1) if y else None, (y.group(2) or y.group(1)) if y else None, meth))
    good = [h for h in hits if h[2]]
    if not good:                                                       # 退而求其次：政策表的行、用中文数字或数字写在前面的句子
        good = policy_more(rows_by_page)
        hits = good + hits
    best = good[0] if good else (hits[0] if hits else None)
    if best and not best[4]:
        meth = next((h[4] for h in hits if h[4]), None)
        if meth is None:
            for pno, rows in rows_by_page:
                for r in rows:
                    t = compact(row_text(r))
                    if "无形资产" in t and re.search(r"使用寿命有限|摊销", t):
                        meth = next((m + "（无形资产总体政策）" for m, pat in METHODS if re.search(pat, t)), None)
                        if meth:
                            break
                if meth:
                    break
        best = best[:4] + (meth,)
    change = []
    for pno, rows in rows_by_page:
        for r in rows:
            t = compact(row_text(r))
            if "数据资源" in t and re.search(r"会计估计变更|变更.*摊销|摊销.*变更|使用寿命.*调整|调整.*使用寿命", t):
                change.append((pno, t[:120]))
    return best, hits, change


OTHER_ASSET = re.compile(r"软件|专利|商标|土地|特许|著作权|电路|频谱|客户关系|版权|域名|经营权|使用权|海域|林权|排污权|非专利")


def cut_other(seg):
    """「数据资源…」片段截到下一类资产之前，免得把「软件3-5年」算到数据资源头上。"""
    m = OTHER_ASSET.search(seg, 4)
    return seg[:m.start()] if m else seg


CN = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def cn_num(t):
    if t.isdigit():
        return float(t)
    if t in CN:
        return float(CN[t])
    if t.startswith("十"):
        return 10.0 + CN.get(t[1:], 0)
    if t.endswith("十"):
        return 10.0 * CN.get(t[:-1], 0)
    return None


POL_ROW = re.compile(r"^数据资源[^0-9。]{0,15}?(\d{1,2}(?:\.\d)?)(?:\s*[-－~～至到]\s*(\d{1,2}(?:\.\d)?))?(?:年)?(?![\d,.])")
POL_TXT = (re.compile(r"(?:按|以)(\d{1,2}|[一二三四五六七八九十两]{1,2})年(?:收益期|受益期|期限|为期)?[^。]{0,20}?数据资源"),
           re.compile(r"数据资源[^。]{0,40}?(?:按|以|为|期限为|寿命为|年限为)(\d{1,2}|[一二三四五六七八九十两]{1,2})年"))


def policy_more(rows_by_page):
    out = []
    for pno, rows in rows_by_page:
        texts = [compact(row_text(r)) for r in rows]
        page = "".join(texts)
        policy_page = bool(re.search(r"使用寿命|摊销方法|摊销年限|预计使用年限", page))
        for t in texts:
            t = cut_other(t) if t.startswith("数据资源") else t
            m = POL_ROW.match(t)
            if m and policy_page and 0 < float(m.group(1)) <= 30:
                meth = next((mm for mm, pat in METHODS if re.search(pat, t)), None)
                out.append((pno, t[:80], m.group(1), m.group(2) or m.group(1), meth))
        for pat in POL_TXT:
            for m in pat.finditer(page):
                v = cn_num(m.group(1))
                seg = m.group(0)
                if v and 0 < v <= 30 and not re.search(r"20\d\d年", seg):
                    meth = next((mm for mm, p2 in METHODS if re.search(p2, seg)), None)
                    out.append((pno, seg[:80], str(v), str(v), meth))
    return out


def dev_rows(rows_by_page):
    out = []
    for pno, rows in rows_by_page:
        texts = [compact(row_text(r)) for r in rows]
        if not any("开发支出" in t for t in texts):
            continue
        for r, t in zip(rows, texts):
            if "数据资源" in t and has_numbers(r):
                nums = [w.t for w in r if is_value(w.t)]
                out.append((pno, t[:80], " ".join(nums)))
    return out


# ---------------------------------------------------------------- 单位
def unit_near(rows, head):
    """表头上方最近的单位说明（同页内，含「人民币千元」这类简写）。"""
    for j in range(head, -1, -1):
        t = compact(row_text(rows[j]))
        m = UNIT_EXPLICIT.search(t)
        if m:
            return m.group(1) or m.group(2)
        m = UNIT_BARE.search(t)
        if m and j >= head - 3:
            return m.group(1)
    return None


def unit_back(doc, pno):
    """往前 60 页找「除特别注明外，金额单位为……」「单位：……」这类明确的总说明。"""
    for i in range(pno - 1, max(-1, pno - 61), -1):
        t = compact(doc[i].get_text())
        ms = list(UNIT_EXPLICIT.finditer(t))
        if ms:
            m = ms[-1] if i < pno - 1 else ms[0]
            return m.group(1) or m.group(2)
    return None


# ---------------------------------------------------------------- 主流程
def balanced(o):
    """三项勾稽：原值、累计摊销的期初+增加−减少=期末；原值−累计摊销−减值=账面价值。返回平衡的项数。"""
    n = 0
    for sec in ("原值", "摊销"):
        if f"{sec}_期初" in o and f"{sec}_期末" in o:
            n += abs(o[f"{sec}_期初"] + o.get(f"{sec}_增加", 0) - o.get(f"{sec}_减少", 0) - o[f"{sec}_期末"]) < 1
    if "原值_期末" in o and "净值_期末" in o:
        n += abs(o["原值_期末"] - o.get("摊销_期末", 0) - o.get("减值_期末", 0) - o["净值_期末"]) < 1
    return n


def score(o):
    return ("净值_期末" in o and o["净值_期末"] > 0, balanced(o), len(o))


def page_height(rows):
    ys = [w.y1 for r in rows for w in r]
    return max(842.0, max(ys) + 10) if ys else None


def process(pdf, year, open_doc):
    doc = open_doc(pdf)
    pages = []
    for i, pg in enumerate(doc):
        t = compact(pg.get_text())
        if "数据资源" in t:
            pages.append((i + 1, page_rows(pg), t))
    found, lines, style = {}, [], None
    cands = []
    for pno, rows, t in pages:
        if not re.search(r"累计摊销|原值|原价|账面价值|账面余额", t):
            continue
        tabs = find_tables(rows)
        if not tabs:
            u0 = unit_near(rows, len(rows) - 1) or unit_back(doc, pno) or "元"
            res, ln = read_row_style(rows, year, u0, pno)
            if res:
                cands.append((res, ln, ("行式无形资产表", pno, None)))
            res, ln = read_transposed(rows, u0, pno)
            if res:
                cands.append((res, ln, ("转置无形资产表", pno, u0)))
        for tab in tabs:
            unit = unit_near(rows, tab["head"]) or unit_back(doc, pno) or "元"
            res, ln, st = read_table(rows, tab, year, unit, pno, page_h=page_height(rows))
            p2 = pno
            # 表格跨页：下一页如有表头用新表头，否则沿用本页列位置
            while not st["ended"] and "净值_期末" not in res and p2 < len(doc) and p2 < pno + 2:
                nxt = next((rw for q, rw, _ in pages if q == p2 + 1), None)
                if nxt is None:
                    nxt = page_rows(doc[p2])
                p2 += 1
                if not nxt:
                    break
                t2 = find_tables(nxt)
                tab2 = t2[0] if t2 and t2[0]["head"] < 10 else dict(tab, row=-1)
                res, ln, st = read_table(nxt, tab2, year, unit, p2, state=st, page_h=page_height(nxt))
            if len(res) >= 3:
                cands.append((dict(res), list(ln), (tab["style"], pno, unit)))
    if cands:
        found, lines, style = max(cands, key=lambda c: score(c[0]))
    if not found:
        res, ln = read_text_disclosure(pages)
        if res:
            found, lines, style = res, ln, ("附注文字披露", ln[0][0], "见原文")
    if not found:
        res, ln = read_text_net(pages)
        if res:
            found, lines, style = res, ln, ("附注文字披露（仅账面价值）", ln[0][0], "见原文")
    best, hits, change = policy([(p, r) for p, r, _ in pages])
    dev = dev_rows([(p, r) for p, r, _ in pages])
    diag = []
    if not found:
        for pno, rows, t in pages:
            if re.search(r"摊销|原值|原价", t):
                diag.append((pno, "\n".join(" ".join(f"{w.t}({w.x0:.0f}-{w.x1:.0f})" for w in r) for r in rows)))
    return found, lines, style, best, hits, change, dev, diag[:6]


# ---------------------------------------------------------------- 导出页面（数据资源页面.zip）的读取
class ZPage:
    def __init__(self, rec=None, hint=""):
        self.rec, self.hint = rec, hint

    def get_text(self, kind="text"):
        if kind == "words":
            return [tuple(w[:4]) + (w[4], w[5], w[6], 0) for w in self.rec["words"]] if self.rec else []
        return self.rec["text"] if self.rec else self.hint


class ZDoc:
    """把导出的一份年报还原成像 pymupdf 文档那样可以按页取词的对象（没导出的页只有单位说明）。"""
    def __init__(self, d):
        self.n = d["n_pages"]
        self.pages = {p["page"]: p for p in d["pages"]}
        self.units = {p: "\n".join(s) for p, s in d["units"]}

    def __len__(self):
        return self.n

    def __getitem__(self, i):
        if i < 0:
            i += self.n
        return ZPage(self.pages.get(i + 1), self.units.get(i + 1, ""))

    def __iter__(self):
        for i in range(self.n):
            yield self[i]


FIELDS = ["原值_期初", "原值_增加", "原值_增加_购置", "原值_增加_内部研发", "原值_增加_企业合并", "原值_减少", "原值_减少_处置", "原值_期末",
          "摊销_期初", "摊销_增加", "摊销_增加_计提", "摊销_减少", "摊销_期末", "减值_期初", "减值_增加", "减值_减少", "减值_期末",
          "净值_期末", "净值_期初"]


def fill_totals(o):
    """表里只有明细项、没有「本期增加/减少」合计行时，用明细项相加；返回补过的项。"""
    filled = []
    for sec, kind in (("原值", "增加"), ("原值", "减少"), ("摊销", "增加"), ("摊销", "减少")):
        subs = [v for k, v in o.items() if k.startswith(f"{sec}_{kind}_")]
        if subs and not o.get(f"{sec}_{kind}") and sum(subs) > 0:
            o[f"{sec}_{kind}"] = sum(subs)
            filled.append(f"{sec}_{kind}")
    return filled


def checks(o):
    def d(a, b):
        return None if a is None or b is None else round(a - b, 2)
    g = o.get
    orig = d((g("原值_期初") or 0) + (g("原值_增加") or 0) - (g("原值_减少") or 0), g("原值_期末")) if "原值_期末" in o and "原值_期初" in o else None
    am = d((g("摊销_期初") or 0) + (g("摊销_增加") or 0) - (g("摊销_减少") or 0), g("摊销_期末")) if "摊销_期末" in o and "摊销_期初" in o else None
    net = d((g("原值_期末") or 0) - (g("摊销_期末") or 0) - (g("减值_期末") or 0), g("净值_期末")) if "原值_期末" in o and "净值_期末" in o else None
    return orig, am, net


def put(ws, row):
    ws.append([ILLEGAL.sub("", v) if isinstance(v, str) else v for v in row])


def load_bs(path):
    """数据资源提取结果.xlsx 的「汇总」页：每份年报资产负债表上「无形资产—其中：数据资源」的期末数。"""
    if not path or not Path(path).exists():
        return {}
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb["汇总"]
    rows = list(ws.iter_rows(values_only=True))
    h = list(rows[0])
    i_f, i_v = h.index("文件"), h.index("无形资产中数据资源_期末(元)")
    out = {}
    for r in rows[1:]:
        if r[i_f]:
            v = r[i_v]
            out[Path(str(r[i_f])).stem] = float(v) if v not in (None, "") else 0.0
    return out


def main():
    args = sys.argv[1:]
    if args and args[0].lower().endswith(".zip"):
        zpath = Path(args[0])
        with zipfile.ZipFile(zpath) as z:
            recs = {n: json.loads(z.read(n)) for n in sorted(z.namelist())}
        files = [(n.split("/", 1)[1][:-5], n.split("/", 1)[0], recs[n]) for n in recs if "error" not in recs[n]]
        open_doc = lambda key: ZDoc(key[2])
        out = zpath.with_name("数据资源附注明细.xlsx")
        bs = load_bs(args[1] if len(args) > 1 else zpath.with_name("数据资源提取结果.xlsx"))
    else:
        try:
            import pymupdf
        except ImportError:
            sys.exit("缺少工具包，请先在终端运行：pip install pymupdf openpyxl")
        base = Path(REPORT_DIR)
        files = [(f.stem, fd, f) for fd in FOLDERS for f in sorted((base / fd).glob("*.[pP][dD][fF]"))]
        if not files:
            sys.exit(f"在 {base} 下没有找到 PDF，请检查 REPORT_DIR 与 FOLDERS 两行。")
        open_doc = lambda key: pymupdf.open(key[2])
        out = base / "数据资源附注明细.xlsx"
        bs = load_bs(base / "数据资源提取结果.xlsx")
    print(f"共 {len(files)} 份年报，开始处理（大约需要十几到几十分钟，请不要关闭窗口）…")
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "无形资产明细"
    put(ws, ["报告年度", "股票代码", "简称", "表格样式", "页码", "单位"] + FIELDS
        + ["原值勾稽", "摊销勾稽", "净值勾稽", "由明细项相加补出", "资产负债表数", "与资产负债表核对", "文件"])
    wp = wb.create_sheet("摊销政策")
    put(wp, ["报告年度", "股票代码", "简称", "使用寿命下限(年)", "使用寿命上限(年)", "摊销方法", "页码", "原文", "其他候选", "会计估计变更线索"])
    wd = wb.create_sheet("开发支出"); put(wd, ["报告年度", "股票代码", "简称", "页码", "原文", "数字（从左到右）"])
    wl = wb.create_sheet("明细行"); put(wl, ["报告年度", "股票代码", "简称", "页码", "部分", "归类", "原文"])
    wg = wb.create_sheet("诊断"); put(wg, ["报告年度", "股票代码", "简称", "页码", "页面原文（词后括号为横向位置）"])
    ok = match = 0
    for n, key in enumerate(files, 1):
        stem, fd = key[0], key[1]
        m = re.match(r"(\d{6})_([^_]+)", stem)
        code, name = (m.group(1), m.group(2)) if m else ("", stem)
        year = int(fd[:4])
        print(f"[{n}/{len(files)}] {stem}")
        try:
            found, lines, style, best, hits, change, dev, diag = process(key, year, open_doc)
        except Exception as e:                                          # 个别文件损坏时继续
            print("   出错，跳过：", e)
            put(wg, [year, code, name, "", f"出错：{e}"])
            continue
        ok += bool(found)
        filled = fill_totals(found)
        c1, c2, c3 = checks(found)
        b = bs.get(stem)
        net = found.get("净值_期末")
        flag = None if b is None else ("一致" if net is not None and abs(net - b) <= max(1, 0.005 * b) else
                                        ("报表无此项" if b == 0 else ("附注未披露明细" if net is None else "不一致")))
        match += flag == "一致"
        put(ws, [year, code, name, style[0] if style else "未取到", style[1] if style else None, style[2] if style else None]
            + [found.get(k) for k in FIELDS] + [c1, c2, c3, "、".join(filled) or None, b, flag, stem])
        others = " | ".join(f"p{h[0]}:{h[1]}" for h in hits[1:4])
        put(wp, [year, code, name, float(best[2]) if best and best[2] else None, float(best[3]) if best and best[3] else None,
                 best[4] if best else None, best[0] if best else None, best[1] if best else None, others,
                 " | ".join(f"p{p}:{t}" for p, t in change[:3])])
        for pno, t, nums in dev:
            put(wd, [year, code, name, pno, t, nums])
        for pno, sec, kind, t in lines:
            put(wl, [year, code, name, pno, sec, kind, t])
        for pno, t in diag:
            put(wg, [year, code, name, pno, t[:30000]])
    for sh in wb.worksheets:
        sh.freeze_panes = "A2"
    try:
        wb.save(out)
    except PermissionError:
        sys.exit(f"写不进 {out}：请先关掉 Excel 里打开的这个文件，再重新运行")
    print("\n" + "=" * 50)
    print(f"处理 {len(files)} 份年报，其中 {ok} 份取到了数据资源无形资产明细" + (f"，{match} 份账面价值与资产负债表一致" if bs else ""))
    print("没取到的多为数据资源只在开发支出或存货项下，或附注没有单列明细，见「诊断」页")
    print(f"结果：{out}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if e.code not in (None, 0):
            print(e)
    except Exception:
        import traceback
        traceback.print_exc()
        print("\n出错了，请把上面的报错信息截图发给我。")
    if not sys.argv[1:]:
        input("\n按回车键退出…")
