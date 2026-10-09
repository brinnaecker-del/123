"""
从已下载的年报 PDF 中提取主要财务数据（配合 extract_data_resources.py 使用，用于计算入表相对重要性和净利率影响）

用法：在 PyCharm 里右键本文件 → 运行。
读取 REPORT_DIR 下 2024年报、2025年报 两个文件夹里的全部 PDF，结果存为 REPORT_DIR 里的「财务数据提取结果.xlsx」：
  · 财务数据：每份年报一行——合并资产负债表的资产总计（期末、期初），合并利润表的营业（总）收入、净利润、
              归属于母公司股东的净利润、研发费用（本期、上期），管理层讨论中的研发投入合计与资本化金额，均已折算成元；
              另列第二节「主要会计数据」表里的营业收入、归母净利润、总资产（本年数），用来核对报表取数；
  · 明细行：每个数取自哪一页、原文是什么，供核对；
  · 未取到：没取到的项目、与主要会计数据对不上的项目；
  · 诊断：上述年报的报表原文行（带横向位置），用来查明原因。
需要先安装：pip install pymupdf openpyxl
"""

import re
import sys
import unicodedata
from pathlib import Path

try:
    import pymupdf
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
UNIT_RE = re.compile(r"单位(?:均为|为)?:?(?:人民币)?(百万元|千元|万元|亿元|元)")
UNIT_RE2 = re.compile(r"人民币(百万元|千元|万元|亿元)")   # 「以人民币千元列示」之类没有「单位」二字的写法
NUM_RE = re.compile(r"^\(?-?\d[\d,]*(?:\.\d+)?\)?$")
DASH_RE = re.compile(r"^[-—–]+$")
NOTE_RE = re.compile(r"^(附注.*|本节.*|注释?\d+"
                     r"|\(?[一二三四五六七八九十]+\)?([、.．·・\-—]?\(?[一二三四五六七八九十\d]+\)?)*[、.．·・,，\-—]?)$")
ENUM_RE = re.compile(r"^(\(\d{1,2}\)|\d{1,2}[、.．](?!\d)|\(?[一二三四五六七八九十]{1,3}\)?[、.．]?)")
BS_WORDS = ("货币资金", "现金及存放中央银行款项", "流动资产", "结算备付金", "存放同业", "资产总计")
IS_WORDS = ("营业收入", "营业总收入", "净利润")

# 利润表要取的项目：名称 -> 项目名（已去掉编号、括号说明）的匹配规则
IS_ITEMS = {
    "营业总收入": r"^营业总收入(合计)?$",
    "营业收入": r"^营业(净)?收入(合计|总计|总额)?$",
    "净利润": r"^净利润$",
    # 「归属于母公司股东的净利润」「归属于本行股东的净利润」；也有先写一行「归属于：」、下一行写「本行股东」的
    "归母净利润": r"^(归属于(?!少数)(?!.*(持续经营|终止经营|非经常)).{0,16}净利润"
                 r"|(本行|母公司|本公司|本集团|上市公司)(普通股)?(股东|所有者)(的净利润)?)$",
    "研发费用": r"^研发费用$",
}


def norm(s):
    return unicodedata.normalize("NFKC", s)


def compact(s):
    return re.sub(r"\s+", "", norm(s))


def page_rows(page):
    """把页面上的文字按纵坐标拼成一行行；每行是 [(x0, x1, 文字), …]，从左到右。"""
    words = sorted(page.get_text("words"), key=lambda w: ((w[1] + w[3]) / 2, w[0]))
    rows, cur, cy = [], [], None
    for w in words:
        y = (w[1] + w[3]) / 2
        if cur and abs(y - cy) > 3:
            rows.append(cur)
            cur = []
        if not cur:
            cy = y
        cur.append(w)
    if cur:
        rows.append(cur)
    return [[(w[0], w[2], norm(w[4])) for w in sorted(r, key=lambda w: w[0])] for r in rows]


def row_text(row):
    return " ".join(w[2] for w in row)


def parse_row(row, unit):
    """一行 -> (项目名称, [(左边界 x, 右边界 x, 金额或 None)…])。以元为单位时不带逗号和小数点的整数视为附注编号。"""
    label, cells, done = [], [], False
    for x0, x1, w in row:
        w = w.strip()
        if done or not w:        # 不间断空格等空白字符单独成词的，跳过
            continue
        if DASH_RE.match(w):
            cells.append((x0, x1, None))
        elif NUM_RE.match(w):
            digits = w.strip("()-")
            if unit == "元" and "," not in w and "." not in w and digits.strip("0"):
                continue
            num = float(digits.replace(",", ""))
            cells.append((x0, x1, -num if w.startswith("(") or w.startswith("-") else num))
        elif NOTE_RE.match(w):
            continue
        elif cells and all(c[2] is None for c in cells):
            label += ["-"] * len(cells) + [w]   # 项目名里的「-」号被拆成了单独的词，不是金额
            cells = []
        elif cells:
            done = True          # 金额后面又出现文字：左右并排报表的右半边，不要
        else:
            label.append(w)
    return compact("".join(label)), cells


def item_name(label):
    """项目名去掉编号、「加：」「减：」「其中：」和括号说明，如「五、净利润(净亏损以“-”号填列)」→「净利润」。"""
    s = re.sub(r"\([^)]*\)", "", label)
    s = re.sub(r"\([^)]*$", "", s)          # 括号说明折到下一行、没有右括号的
    for _ in range(3):
        s = ENUM_RE.sub("", s, count=1)
        s = re.sub(r"^(加|减|其中)[:：]?", "", s)
    return s.strip(":：")


ALIGNS = (lambda c: c[1], lambda c: c[0], lambda c: (c[0] + c[1]) / 2)   # 右对齐、左对齐、居中


def columns(cell_rows, wide):
    """找出本期（期末）、上期（期初）两列的位置；金额可能右对齐、左对齐或居中，选最能对齐的一种。"""
    def note_column(g):
        return all(v is not None and float(v).is_integer() and abs(v) < 100 for _, v, _ in g)

    best = None
    for key in ALIGNS:
        pts = sorted(((key(c), c[2], n) for n, cells in enumerate(cell_rows) if len(cells) >= 2 for c in cells),
                     key=lambda p: p[0])
        groups = []
        for x, v, n in pts:
            if groups and x - groups[-1][-1][0] <= 25:
                groups[-1].append((x, v, n))
            else:
                groups.append([(x, v, n)])
        # 同一行的两个数落进了同一组：相邻两列被连成了一片，说明不是这种对齐方式
        mixed = sum(len(g) - len({n for _, _, n in g}) for g in groups)
        good = [g for g in groups if len(g) >= 3 and not note_column(g)]
        if len(good) < 2:
            continue
        chosen = good[:2] if wide or len(good) >= 4 else good[-2:]
        score = (-mixed, sum(len(g) for g in chosen))
        if best is None or score > best[0]:
            best = (score, key, [sorted(x for x, _, _ in g)[len(g) // 2] for g in chosen])
    return None if best is None else (best[1], best[2])


def assign(cells, cols, wide):
    if cols:
        key, centers = cols
        cur = prev = None
        for c in cells:
            d = [abs(key(c) - x) for x in centers]
            if min(d) <= 40:
                if d[0] <= d[1]:
                    cur = c[2] if cur is None else cur
                else:
                    prev = c[2] if prev is None else prev
        return cur, prev
    vals = [c[2] for c in cells]
    vals = vals[:2] if wide or len(vals) >= 4 else vals[-2:]
    vals += [None] * (2 - len(vals))
    return vals[0], vals[1]


def statement_kind(row, name):
    """一行是不是某张报表的标题：返回 wide（合并与本公司并排）/ narrow（合并单列）/ parent（母公司或单体）/ None。"""
    c = compact(row_text(row))
    if len(c) > 80:
        return None
    t = ENUM_RE.sub("", c, count=1)
    # 标题后面紧跟顿号、逗号、「日」「中」等，是审计报告或附注里的句子，不是标题
    after = r"(?![、，,。及和与日中项表的时内期])"
    if re.match(rf"(合并及(母公司|公司|银行|本行){name}|合并{name}(及|和|与)(母公司|公司|银行|本行)?{name}){after}", t):
        return "wide"
    if re.match(rf"合并{name}{after}", t):
        return "narrow"
    if re.match(rf"(母公司|公司|银行|本行){name}(?![、，,。日中的时内])|{name}(?=$|\(续|-|20|编制|单位|会企)", t):
        return "parent"
    return None


def other_statement(row):
    """一行是不是任意一张报表的标题（用来判断上一张报表到哪里结束）。"""
    c = ENUM_RE.sub("", compact(row_text(row)), count=1)
    return len(c) <= 80 and bool(re.match(r"(合并|母公司|公司|银行|本行)?(及(母公司|公司|银行|本行))?"
                                          r"(资产负债表|利润表|现金流量表|所有者权益变动表|股东权益变动表)"
                                          r"(?![、，,。日中的时内])", c))


def find_statement(doc, texts, name, words, begin):
    """从第 begin 页往后找合并报表（资产负债表 / 利润表）的标题，返回 (页码, 标题是该页第几行, 标题类型)。"""
    def has_words(j):
        return 0 <= j < len(texts) and any(k in texts[j] for k in words)

    def first_title(j):
        for k, r in enumerate(page_rows(doc[j])):
            kind = statement_kind(r, name)
            if kind:
                return k, kind
        return None, None

    single = None
    for i in range(begin, len(texts)):
        if name not in texts[i] or not (has_words(i) or has_words(i + 1)):
            continue
        for k, r in enumerate(page_rows(doc[i])):
            kind = statement_kind(r, name)
            if kind in ("wide", "narrow"):
                # 只有标题、没有表格的页（如报表目录），以下一页的标题为准
                if not has_words(i) and i + 1 < len(texts):
                    k2, kind2 = first_title(i + 1)
                    if kind2 in ("wide", "narrow"):
                        return i + 1, k2, kind2
                return i, k, kind
            if kind == "parent" and single is None:
                single = (i, k, kind)     # 没有子公司的单体报表，标题就是「资产负债表」「利润表」
    if single:
        for j in range(max(begin, single[0] - 4), single[0]):
            if "合并" + name in texts[j] and (has_words(j) or has_words(j + 1)):
                return j, 0, "narrow"
    return single or (None, None, None)


def unit_near(texts, i, lo=0):
    for regex in (UNIT_RE, UNIT_RE2):
        for j in (i, i - 1, i + 1, i - 2):
            if lo <= j < len(texts):
                m = regex.search(texts[j])
                if m:
                    return m.group(1)
    for j in range(i, lo - 1, -1):       # 报表页附近没写的，取前面最近的一处说明
        m = UNIT_RE.search(texts[j])
        if m:
            return m.group(1)
    return None


CONTINUED = re.compile(r"^(“|”|\"|\)|号填列|填列|以“|以\")")


def read_statement(doc, start, row0, kind, name, unit, wanted, stop):
    """从报表标题行往后读，按 wanted（名称 -> 规则）取本期、上期两个数；遇到 stop 规则或下一张报表为止。"""
    rows = []
    for i in range(start, min(start + 6, len(doc))):
        page = page_rows(doc[i])
        rows += [(i, r) for r in (page[row0:] if i == start else page)]
    body = []
    for k, (i, r) in enumerate(rows):
        # 下一张报表的标题（母公司报表、现金流量表等）；本表的续页标题「合并利润表(续)」不算
        if k > 0 and other_statement(r) and statement_kind(r, name) != kind:
            break
        label, cells = parse_row(r, unit)
        # 项目名折成两行、金额排在第二行（或两行中间）的，并回一行
        if body and cells and not body[-1][3] and body[-1][2] and (not label or CONTINUED.match(label)):
            pi, pr, plabel, _ = body.pop()
            i, r, label = pi, pr + r, plabel + label
        body.append((i, r, label, cells))
        if stop and re.match(stop, item_name(label)):
            break
    wide = kind == "wide"
    cols = columns([cells for _, _, _, cells in body], wide)
    found = {}
    for i, r, label, cells in body:
        item = item_name(label)
        for key, pattern in wanted.items():
            if key not in found and cells and re.match(pattern, item):
                cur, prev = assign(cells, cols, wide)
                found[key] = (cur, prev, i + 1, row_text(r))
    found["_rows"] = [(i, r) for i, r, _, _ in body]
    return found


RD_TOTAL = r"^(本期|本年)?研发投入(金额|合计|总额|总计)(合计)?$"
RD_CAP = r"^(本期|本年)?(研发投入资本化的?金额|资本化研发投入|研发投入资本化金额)$"
# 第二节「主要会计数据」表：只取本年数，用来核对从报表里取的数
KEY_ITEMS = {
    "营业收入": r"^营业(总)?收入$",
    "归母净利润": r"^归属于(上市公司|本行|母公司|本公司|本集团)?(普通股)?(股东|所有者)的净利润$",
    "总资产": r"^(总资产|资产总额|资产总计)$",
}


def scan_rows(doc, texts, i):
    """管理层讨论等正文表格：逐行给出 (项目名, (第一个数, 页码, 原文, 单位))。单位看项目名括号或表格上方的说明。"""
    unit = unit_near(texts, i) or "元"
    for r in page_rows(doc[i]):
        c = compact(row_text(r))
        m = UNIT_RE.search(c) or UNIT_RE2.search(c)
        if m:
            unit = m.group(1)        # 表格上方的「单位：元」
        m = re.search(r"\((百万元|千元|万元|亿元|元)\)", c)
        row_unit = m.group(1) if m else unit   # 项目名里写的「研发投入金额(元)」
        label, cells = parse_row(r, row_unit)
        name = re.sub(r"\([^)]*\)", "", label)
        nums = [x for x in cells if x[2] is not None]
        if nums and "占" not in name and "比" not in name:
            yield name, (nums[0][2], i + 1, row_text(r), row_unit)


def read_rd(doc, texts, audit):
    """管理层讨论里的研发投入表：研发投入合计、资本化金额（本年）。返回 ((数, 页码, 原文, 单位) 或 None, 同上)。"""
    for i in range(0, audit or len(texts)):
        if "研发投入" not in texts[i]:
            continue
        total = next((v for name, v in scan_rows(doc, texts, i) if re.match(RD_TOTAL, name)), None)
        if not total:
            continue
        cap = None
        for j in (i, i + 1):        # 资本化金额可能在下一页
            if j < len(texts) and "资本化" in texts[j]:
                cap = next((v for name, v in scan_rows(doc, texts, j) if re.match(RD_CAP, name)), None)
                if cap:
                    break
        if cap and cap[0] * UNITS[cap[3]] > total[0] * UNITS[total[3]]:
            cap = None
        return total, cap
    return None, None


def read_key_data(doc, texts, audit):
    """第二节「主要会计数据」表里的营业收入、归母净利润、总资产（本年数）。"""
    end = audit or len(texts)
    start = next((i for i in range(end) if "主要会计数据" in texts[i] and "净利润" in texts[i]), None)
    found = {}
    if start is None:
        return found
    for i in range(start, min(start + 4, end)):
        for name, v in scan_rows(doc, texts, i):
            for key, pattern in KEY_ITEMS.items():
                if key not in found and re.match(pattern, name):
                    found[key] = v
    return found


def fmt_row(row):
    return " ".join(f"{w[2]}({w[0]:.0f}-{w[1]:.0f})" for w in row)


def title_candidates(doc, texts, audit, name):
    """没找到报表时，列出审计报告之后含报表名称的短行，便于查明原因。"""
    out = []
    for i in range(audit, len(texts)):
        if name not in texts[i]:
            continue
        for r in page_rows(doc[i]):
            if name in compact(row_text(r)) and len(compact(row_text(r))) <= 80:
                out.append((i, r))
                if len(out) >= 15:
                    return out
    return out


def extract(pdf_path):
    doc = pymupdf.open(pdf_path)
    texts = [compact(p.get_text()) for p in doc]
    audit = next((i for i, t in enumerate(texts) if "我们审计了" in t), 0)
    out = {"items": {}, "notes": [], "bs_page": "", "is_page": "", "bs_unit": "", "is_unit": "",
           "key": {}, "diag": []}

    bs, row0, kind = find_statement(doc, texts, "资产负债表", BS_WORDS, audit)
    if bs is None:
        out["notes"].append("没找到合并资产负债表")
        out["diag"] += [("资产负债表标题候选", i, r) for i, r in title_candidates(doc, texts, audit, "资产负债表")]
    else:
        unit = unit_near(texts, bs, audit) or "元"
        out["bs_page"], out["bs_unit"] = bs + 1, unit
        got = read_statement(doc, bs, row0, kind, "资产负债表", unit,
                             {"总资产": r"^资产(总计|合计)$"}, r"^资产(总计|合计)$")
        bs_rows = got.pop("_rows")
        if "总资产" in got:
            out["items"]["总资产"] = got["总资产"] + (unit,)
        else:
            out["notes"].append("资产负债表里没找到资产总计")
        if kind == "parent":
            out["notes"].append("只找到单体资产负债表")

    is_, row0, kind = find_statement(doc, texts, "利润表", IS_WORDS, bs if bs is not None else audit)
    if is_ is None:
        out["notes"].append("没找到合并利润表")
        out["diag"] += [("利润表标题候选", i, r) for i, r in title_candidates(doc, texts, audit, "利润表")]
    else:
        unit = unit_near(texts, is_, audit) or "元"
        out["is_page"], out["is_unit"] = is_ + 1, unit
        got = read_statement(doc, is_, row0, kind, "利润表", unit, IS_ITEMS, r"^(稀释每股收益|基本每股收益|每股收益)")
        is_rows = got.pop("_rows")
        if "营业总收入" not in got and "营业收入" in got:
            got["营业总收入"] = got["营业收入"]
        if kind == "parent" and "归母净利润" not in got and "净利润" in got:
            got["归母净利润"] = got["净利润"]     # 没有子公司，净利润全部归属于本公司股东
        for k in ("营业总收入", "营业收入", "净利润", "归母净利润", "研发费用"):
            if k in got:
                out["items"][k] = got[k] + (unit,)
            elif k in ("营业总收入", "净利润", "归母净利润"):
                out["notes"].append(f"利润表里没找到{k}")
        if kind == "parent":
            out["notes"].append("只找到单体利润表")

    total, cap = read_rd(doc, texts, audit)
    if total:
        out["items"]["研发投入合计"] = (total[0], None, total[1], total[2], total[3])
    if cap:
        out["items"]["研发投入资本化金额"] = (cap[0], None, cap[1], cap[2], cap[3])

    # 和「主要会计数据」表核对本年数
    out["key"] = read_key_data(doc, texts, audit)
    bad_bs = bad_is = False
    for k, item in (("总资产", "总资产"), ("营业收入", "营业总收入"), ("归母净利润", "归母净利润")):
        if k not in out["key"] or item not in out["items"]:
            continue
        a = yuan(out["key"][k][0], out["key"][k][3])
        b = yuan(out["items"][item][0], out["items"][item][4])
        if b is None or abs(a - b) > max(abs(a) * 0.002, 1000):
            if k == "营业收入" and "营业收入" in out["items"] and \
                    abs(a - (yuan(out["items"]["营业收入"][0], out["items"]["营业收入"][4]) or 0)) <= max(abs(a) * 0.002, 1000):
                continue     # 主要会计数据写的是营业收入，不是营业总收入
            out["notes"].append(f"{item}与主要会计数据不一致")
            bad_bs |= k == "总资产"
            bad_is |= k != "总资产"
    if bs is not None and ("总资产" not in out["items"] or bad_bs):
        out["diag"] += [("资产负债表", i, r) for i, r in bs_rows[:80]]
    if is_ is not None and (any(f"没找到{k}" in n for n in out["notes"] for k in ("营业总收入", "净利润", "归母净利润"))
                            or bad_is):
        out["diag"] += [("利润表", i, r) for i, r in is_rows[:90]]
    return out


def yuan(v, unit):
    return None if v is None else round(v * UNITS.get(unit, 1), 2)


def write_book(path, sheets):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for title, (header, rows) in sheets.items():
        ws = wb.create_sheet(title)
        ws.append(header)
        for row in rows:
            ws.append(row)
        for col in ws.columns:
            width = max(len(str(c.value or "")) for c in list(col)[:200])
            ws.column_dimensions[col[0].column_letter].width = min(max(8, width * 1.6), 70)
        ws.freeze_panes = "A2"
    wb.save(path)


FIELDS = [("总资产", "期末", "期初"), ("营业总收入", "本期", "上期"), ("净利润", "本期", "上期"),
          ("归母净利润", "本期", "上期"), ("研发费用", "本期", "上期")]


def main():
    root = Path(REPORT_DIR)
    pdfs = [(folder[:4], p) for folder in FOLDERS for p in sorted((root / folder).glob("*.[pP][dD][fF]"))]
    if not pdfs:
        sys.exit(f"在 {root} 下的 {'、'.join(FOLDERS)} 里没找到 PDF，请检查 REPORT_DIR 是否正确")
    print(f"共 {len(pdfs)} 份年报，开始提取财务数据……\n")

    rows, detail, misses, diags = [], [], [], []
    for n, (year, pdf) in enumerate(pdfs, 1):
        parts = pdf.stem.split("_")
        code = parts[0] if re.fullmatch(r"\d{6}", parts[0]) else ""
        name = next((x for x in parts[1:] if x), "")     # 「688066__ST航图_…」：*ST 的星号在文件名里成了下划线
        try:
            r = extract(pdf)
        except Exception as e:
            print(f"[{n}/{len(pdfs)}] {pdf.name}：出错 {e}")
            misses.append([year, code, name, f"出错：{e}"])
            rows.append([year, code, name] + [None] * 15 + ["", "", "", "", f"出错：{e}", pdf.name])
            continue
        it = r["items"]
        row = [year, code, name]
        for key, _, _ in FIELDS:
            cur, prev = (it[key][0], it[key][1]) if key in it else (None, None)
            unit = it[key][4] if key in it else ""
            row += [yuan(cur, unit), yuan(prev, unit)]
        for key in ("研发投入合计", "研发投入资本化金额"):
            row.append(yuan(it[key][0], it[key][4]) if key in it else None)
        for key in KEY_ITEMS:
            row.append(yuan(r["key"][key][0], r["key"][key][3]) if key in r["key"] else None)
        row += [r["bs_page"], r["bs_unit"], r["is_page"], r["is_unit"], "；".join(r["notes"]), pdf.name]
        rows.append(row)
        for key, (cur, prev, page, raw, unit) in it.items():
            detail.append([year, code, name, key, cur, prev, unit, yuan(cur, unit), yuan(prev, unit), page, raw])
        for key, (v, page, raw, unit) in r["key"].items():
            detail.append([year, code, name, f"主要会计数据·{key}", v, None, unit, yuan(v, unit), None, page, raw])
        for note in r["notes"]:
            misses.append([year, code, name, note])
        for what, i, rr in r["diag"]:
            diags.append([year, code, name, what, i + 1, fmt_row(rr)])
        print(f"[{n}/{len(pdfs)}] {code} {name} {year}：取到 {len(it)} 项 {'；'.join(r['notes'])}")

    header = ["报告年度", "股票代码", "简称"]
    for key, a, b in FIELDS:
        header += [f"{key}_{a}(元)", f"{key}_{b}(元)"]
    header += ["研发投入合计(元)", "研发投入资本化金额(元)"] + [f"主要会计数据_{k}(元)" for k in KEY_ITEMS]
    header += ["资产负债表页码", "资产负债表单位", "利润表页码", "利润表单位", "提取情况", "文件"]
    out = root / "财务数据提取结果.xlsx"
    try:
        write_book(out, {
            "财务数据": (header, rows),
            "明细行": (["报告年度", "股票代码", "简称", "项目", "本期/期末(原单位)", "上期/期初(原单位)", "单位",
                       "本期/期末(元)", "上期/期初(元)", "页码", "原文"], detail),
            "未取到": (["报告年度", "股票代码", "简称", "情况"], misses),
            "诊断": (["报告年度", "股票代码", "简称", "哪张表", "页码", "原文行（括号里是横向位置）"], diags),
        })
    except PermissionError:
        sys.exit(f"写不进 {out}：请先关掉 Excel 里打开的这个文件，再重新运行")
    full = sum(1 for r in rows if all(r[i] is not None for i in (3, 5, 7, 9)))
    print("\n" + "=" * 50)
    print(f"处理 {len(pdfs)} 份年报，其中 {full} 份总资产、营业收入、净利润、归母净利润四项齐全")
    print(f"有 {len({(m[0], m[1]) for m in misses})} 份年报有缺项或与主要会计数据对不上，见「未取到」页")
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
    input("\n按回车键退出…")
