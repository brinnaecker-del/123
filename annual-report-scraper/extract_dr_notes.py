"""
从年报 PDF 的财务报表附注中提取数据资源的明细（配合 extract_data_resources.py、extract_financials.py 使用）

用法：在 PyCharm 里右键本文件 → 运行。
读取 REPORT_DIR 下 2024年报、2025年报 两个文件夹里的全部 PDF，结果存为 REPORT_DIR 里的「数据资源附注明细.xlsx」：
  · 无形资产明细：每份年报一行——确认为无形资产的数据资源：账面原值（期初、本期增加及其中购置/内部研发、本期减少、期末）、
                  累计摊销（期初、本期计提、本期减少、期末）、减值准备（期初、本期计提、本期减少、期末）、账面价值（期末、期初），
                  均已折算成元；并列出取自哪一页、表格样式、三项勾稽是否平衡；
  · 摊销政策：数据资源无形资产的使用寿命（年）与摊销方法，以及原文；会计估计变更的线索；
  · 开发支出：附注开发支出表中写有「数据资源」的行（原文与各列金额），供人工核对；
  · 明细行：每个数取自哪一页、哪一行原文；
  · 诊断：没取到无形资产明细的年报里，同时含「数据资源」与「摊销」或「原值」的页面原文（每个词带横向位置）。
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
UNIT_RE = re.compile(r"单位(?:均为|为)?[:：]?(?:人民币)?(百万元|千元|万元|亿元|元)")
UNIT_RE2 = re.compile(r"人民币(百万元|千元|万元|亿元)")
NUM_RE = re.compile(r"^\(?-?\d[\d,]*(?:\.\d+)?\)?$")
DASH_RE = re.compile(r"^[-—–－]+$")
DATE_RE = re.compile(r"(20\d\d)年(\d{1,2})月(\d{1,2})日")
ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")   # Excel 单元格不接受的控制字符
OTHER_HEADERS = ("土地使用权", "软件", "专利", "非专利技术", "商标", "特许经营权", "著作权", "合计", "知识产权", "其他", "域名",
                 "客户关系", "技术", "采矿权", "使用权", "经营权", "版权", "系统", "资质")
SECTIONS = (("原值", r"(账面原值|账面原价|原值|原价|成本)(合计)?$"), ("摊销", r"累计摊销(合计)?$"),
            ("减值", r"减值准备(合计)?$"), ("净值", r"(账面价值|账面净值|净值|净额)(合计)?$"))
METHODS = (("年数总和法", r"年数总和"), ("双倍余额递减法", r"双倍余额"), ("工作量法", r"工作量法|产量法"),
           ("直线法", r"直线法|平均年限法|年限平均法|平均摊销|分期平均|直线摊销"))


def norm(s):
    return unicodedata.normalize("NFKC", s)


def compact(s):
    return re.sub(r"\s+", "", norm(s))


def page_rows(page):
    """把页面上的文字按纵坐标拼成一行行；每行是 [(x0, x1, y, 文字), …]，从左到右。"""
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
    out = [[(w[0], w[2], (w[1] + w[3]) / 2, norm(w[4]).strip()) for w in sorted(r, key=lambda w: w[0]) if norm(w[4]).strip()]
           for r in rows]
    return [r for r in out if r]


def row_text(row):
    return "".join(w[3] for w in row)


def page_unit(rows):
    for r in rows[:40]:
        t = compact(row_text(r))
        m = UNIT_RE.search(t) or UNIT_RE2.search(t)
        if m:
            return m.group(1)
    return None


def to_num(w):
    if DASH_RE.match(w):
        return 0.0
    if NUM_RE.match(w):
        v = float(w.strip("()-").replace(",", ""))
        return -v if (w.startswith("(") or w.startswith("-")) else v
    return None


# ---------------------------------------------------------------- 表头
def header_columns(rows, i):
    """rows[i] 含「数据资源」作列名时，把它与上下紧邻的、没有数字的行合并成表头，返回 [(x0, x1, 列名)…]。"""
    block = [rows[i]]
    y0 = rows[i][0][2]
    for j in (i - 1, i - 2, i + 1, i + 2):
        if 0 <= j < len(rows) and abs(rows[j][0][2] - y0) <= 16 and \
                not any(to_num(w[3]) is not None and w[3] not in "-—" and not re.match(r"^20\d\d$", w[3]) for w in rows[j]):
            block.append(rows[j])
    toks = sorted((w for r in block for w in r), key=lambda w: (w[0], w[2]))
    cols = []
    for x0, x1, y, t in toks:
        for c in cols:
            if min(x1, c[1]) - max(x0, c[0]) > -2:      # 横向重叠：同一列的上下两行
                c[0], c[1] = min(c[0], x0), max(c[1], x1)
                c[2].append((y, t))
                break
        else:
            cols.append([x0, x1, [(y, t)]])
    return [(c[0], c[1], "".join(t for _, t in sorted(c[2]))) for c in sorted(cols)]


def find_tables(rows):
    """找本页上以「数据资源」为一列的无形资产表（列式），或「确认为无形资产的数据资源」专表（列为取得方式与合计）。
    列名可能折成两行（如「自主研发的数据 / 资源无形资产」），所以用合并后的表头判断。"""
    out, used = [], set()
    if not rows:
        return out
    left = min(w[0] for rr in rows for w in rr)
    for i, r in enumerate(rows):
        if i in used or any(to_num(w[3]) is not None and not DASH_RE.match(w[3]) and not re.match(r"^20\d\d$", w[3]) for w in r):
            continue
        near = compact("".join(row_text(rows[k]) for k in range(max(0, i - 1), min(len(rows), i + 2))))
        if "数据资源" not in near and not ("外购" in near and "自行开发" in near):
            continue
        cols = header_columns(rows, i)
        names = [compact(c[2]) for c in cols]
        dr = [k for k, n in enumerate(names) if "数据资源" in n and cols[k][0] > left + 80]
        if not dr:
            continue
        others = [k for k, n in enumerate(names) if any(h in n for h in OTHER_HEADERS)]
        tot = [k for k, n in enumerate(names) if n.endswith("合计") or n == "合计"]
        special = any(re.search(r"无形资产|外购|自行开发|自主研发|其他方式", names[k]) for k in dr)
        if special:
            tab = {"row": i, "cols": cols, "target": tot[-1] if tot else dr[0], "style": "数据资源专表", "left": left}
        elif others:
            tab = {"row": i, "cols": cols, "target": dr[0], "style": "无形资产表数据资源列", "left": left}
        else:
            continue
        used.update({i, i + 1})
        out.append(tab)
    return out


def split_label(row, label_bound):
    label = "".join(w[3] for w in row if (w[0] + w[1]) / 2 < label_bound)
    cells = [(w[0], w[1], to_num(w[3])) for w in row if (w[0] + w[1]) / 2 >= label_bound and to_num(w[3]) is not None]
    return compact(label), cells


def pick(cells, cols, target):
    """把每个数归到最近的表头列，返回落在目标列的数。"""
    best = None
    for x0, x1, v in cells:
        cx, scores = (x0 + x1) / 2, []
        for k, (c0, c1, _) in enumerate(cols):
            ov = min(x1, c1) - max(x0, c0)
            d = 0 if ov > 0 else min(abs(x1 - c1), abs(cx - (c0 + c1) / 2), abs(x0 - c0))
            scores.append((-(ov if ov > 0 else 0), d, k))
        k = min(scores)[2]
        if k == target:
            best = v
    return best


# ---------------------------------------------------------------- 行的归类
def classify(label, year):
    """返回 ('open'|'close'|'add'|'add_buy'|'add_rd'|'add_merge'|'sub'|'sub_disp'|None)。"""
    s = re.sub(r"^[一二三四五六七八九十\d]+[、.．]|^\(\d+\)|^[(（]?[一二三四五六七八九十]+[)）]|^其中[:：]", "", label)
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"[()（）]", "", s)                 # 括号被拆成单独的词时留下的半边
    m = DATE_RE.search(label)
    if m:
        yy, mm, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if (yy == year - 1 and mm == 12) or (yy == year and mm == 1 and dd == 1):
            return "open"
        if yy == year and mm == 12:
            return "close"
        return "other_date"
    if re.match(r"^(\d\.)?(期初|年初|上年年末|上年末|本期期初|本年年初)(余额|数|账面价值|金额)?$", s) or s in ("期初账面价值", "年初账面价值"):
        return "open"
    if re.match(r"^(\d\.)?(期末|年末|本期期末|本年年末)(余额|数|账面价值|金额)?$", s) or s in ("期末账面价值", "年末账面价值"):
        return "close"
    if re.match(r"^(\d\.)?(本期|本年)?(增加|计提|摊销)(金额|额)?$", s):
        return "add"
    if re.search(r"购置|购入|外购|购买", s):
        return "add_buy"
    if re.search(r"内部研发|自行开发|研发支出转入|开发支出转入|由开发支出|内部开发", s):
        return "add_rd"
    if re.search(r"企业合并|合并增加|非同一控制", s):
        return "add_merge"
    if re.match(r"^(\d\.)?(本期|本年)?减少(金额|额)?$", s):
        return "sub"
    if re.search(r"处置|报废|出售|终止确认|失效", s):
        return "sub_disp"
    return None


def read_table(rows, tab, year, unit, page_no):
    cols, target = tab["cols"], tab["target"]
    data_cols = [c for c in cols if any(h in compact(c[2]) for h in OTHER_HEADERS + ("数据资源", "外购", "自行开发", "其他方式"))
                 and c[0] > tab.get("left", 0) + 80]
    label_bound = min(c[0] for c in data_cols) - 4 if data_cols else cols[0][1] + 4
    res, sec, seen_open, lines, closed = {}, None, {}, [], set()
    for r in rows[tab["row"] + 1:]:
        label, cells = split_label(r, label_bound)
        if not label and not cells:
            continue
        base = re.sub(r"^[一二三四五六七八九十]+[、.．]|^\d+[、.．]", "", label).rstrip(":：")
        is_sec = any(re.match(p, base) or re.search(r"^(无形资产|数据资源)?" + p, base) for _, p in SECTIONS)
        if res and not cells and not is_sec and re.match(r"^(\d{1,2}[、.．]|\(\d{1,2}\)|[一二三四五六七八九十]+[、.．])\D", label) \
                and not classify(label, year):
            break                         # 下一个附注项目（或下一张表）开始
        for name, pat in SECTIONS:
            b2 = re.sub(r"\(.*?\)", "", base)
            if not cells and (re.match(pat, base) or re.match(pat, b2) or re.search(r"^(无形资产|数据资源)?" + pat, b2)):
                sec = name
                seen_open[sec] = False
                closed.discard(sec)
                break
        else:
            if sec is None or not cells or sec in closed:
                continue
            kind = classify(label, year)
            v = pick(cells, cols, target)
            if kind is None:
                continue
            v = abs(v) if v is not None else 0.0          # 本列空白：该项为零
            if kind == "open":
                seen_open[sec] = True
                res[f"{sec}_期初"] = v * UNITS[unit]
                lines.append((page_no, sec, kind, row_text(r)))
                continue
            if kind == "close":
                if sec == "净值" or seen_open.get(sec):
                    res[f"{sec}_期末"] = v * UNITS[unit]
                    lines.append((page_no, sec, kind, row_text(r)))
                    if sec != "净值":
                        closed.add(sec)
                    if sec == "净值" and f"净值_期初" in res:
                        break
                continue
            if kind == "other_date":
                seen_open[sec] = False
                continue
            if not seen_open.get(sec) and sec != "净值":
                continue
            key = {"add": "增加", "add_buy": "增加_购置", "add_rd": "增加_内部研发", "add_merge": "增加_企业合并",
                   "sub": "减少", "sub_disp": "减少_处置"}[kind]
            res[f"{sec}_{key}"] = res.get(f"{sec}_{key}", 0) + v * UNITS[unit] if kind in ("add_buy", "add_rd") else v * UNITS[unit]
            lines.append((page_no, sec, kind, row_text(r)))
    return res, lines


MOVE_COLS = (("open", r"^(期初|年初|上年年末|上年末)"), ("add", r"^(本期|本年)?增加"), ("sub", r"^(本期|本年)?减少"), ("close", r"^(期末|年末)"))


def read_row_style(rows, year, unit, page_no):
    """行式无形资产表：各类资产占一行，列为期初、本期增加、本期减少、期末；取「数据资源」那几行。"""
    for i, r in enumerate(rows):
        cols = [(w[0], w[1], compact(w[3])) for w in r]
        hit = {}
        for x0, x1, t in cols:
            for k, pat in MOVE_COLS:
                if k not in hit and re.match(pat, t):
                    hit[k] = (x0, x1)
        if len(hit) < 3 or any(to_num(w[3]) is not None and not DASH_RE.match(w[3]) for w in r):
            continue
        hcols = [(x0, x1, k) for k, (x0, x1) in sorted(hit.items(), key=lambda kv: kv[1][0])]
        label_bound = min(c[0] for c in hcols) - 4
        res, sec, lines = {}, None, []
        for rr in rows[i + 1:]:
            label, cells = split_label(rr, label_bound)
            base = re.sub(r"^[一二三四五六七八九十]+[、.．]|^\d+[、.．]|^其中[:：]", "", label)
            for name, pat in SECTIONS:
                if re.search(pat.rstrip("$") + r"(合计)?$", re.sub(r"\(.*?\)", "", base)) and "数据资源" not in base:
                    sec = name
                    break
            else:
                if sec and "数据资源" in base and cells:
                    for k_idx, (_, _, k) in enumerate(hcols):
                        v = pick(cells, [(c[0], c[1], c[2]) for c in hcols], k_idx)
                        if v is not None:
                            key = {"open": "期初", "add": "增加", "sub": "减少", "close": "期末"}[k]
                            res[f"{sec}_{key}"] = abs(v) * UNITS[unit]
                    lines.append((page_no, sec, "行式", row_text(rr)))
        if len(res) >= 3:
            return res, lines
    return {}, []


TXT_RE = {"原值_期末": r"原值(?:为|是)?(?:人民币)?([\d,.]+)(百万元|千元|万元|亿元|元)",
          "摊销_期末": r"累计摊销(?:为|是)?(?:人民币)?([\d,.]+)(百万元|千元|万元|亿元|元)",
          "净值_期末": r"(?:净值|账面价值|净额)(?:为|是)?(?:人民币)?([\d,.]+)(百万元|千元|万元|亿元|元)"}


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
    """在「数据资源」所在的句子或表格行里找使用寿命与摊销方法。"""
    hits = []
    for pno, rows in rows_by_page:
        texts = [compact(row_text(r)) for r in rows]
        for k, t in enumerate(texts):
            if "数据资源" not in t:
                continue
            ctx = t if len(t) > 12 else t + "".join(texts[k + 1:k + 2])
            seg = ctx[ctx.index("数据资源"):]
            seg = re.split(r"[。；;]", seg)[0][:80]
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


# ---------------------------------------------------------------- 开发支出
def dev_rows(rows_by_page):
    out = []
    for pno, rows in rows_by_page:
        texts = [compact(row_text(r)) for r in rows]
        if not any("开发支出" in t for t in texts):
            continue
        for r, t in zip(rows, texts):
            if "数据资源" in t and any(to_num(w[3]) is not None and not DASH_RE.match(w[3]) for w in r):
                nums = [w[3] for w in r if to_num(w[3]) is not None]
                out.append((pno, t[:80], " ".join(nums)))
    return out


# ---------------------------------------------------------------- 主程序
def prev_unit(doc, pno):
    """本页没写单位时，往前 40 页找附注里的「单位：」或「人民币千元」之类的说明。"""
    for i in range(pno - 2, max(-1, pno - 42), -1):
        t = compact(doc[i].get_text())
        m = UNIT_RE.search(t) or UNIT_RE2.search(t)
        if m:
            return m.group(1)
    return None


def process(pdf, year):
    doc = pymupdf.open(pdf)
    pages = []
    for i, pg in enumerate(doc):
        t = compact(pg.get_text())
        if "数据资源" in t:
            pages.append((i + 1, page_rows(pg), t))
    found, lines, style = {}, [], None
    for pno, rows, t in pages:
        if found:
            break
        if not re.search(r"累计摊销|原值|原价", t):
            continue
        unit = page_unit(rows) or prev_unit(doc, pno) or "元"
        if not find_tables(rows):
            res, ln = read_row_style(rows, year, unit, pno)
            if res:
                found, lines, style = res, ln, ("行式无形资产表", pno, unit)
                break
        for tab in find_tables(rows):
            res, ln = read_table(rows, tab, year, unit, pno)
            if len(res) >= 3:
                found, lines, style = res, ln, (tab["style"], pno, unit)
                # 表格跨页：下一页没有表头时沿用本页列位置
                if "净值_期末" not in res and "摊销_期末" not in res:
                    nxt = next((rw for p2, rw, _ in pages if p2 == pno + 1), None)
                    if nxt is None and pno < len(doc):
                        nxt = page_rows(doc[pno])
                    if nxt:
                        tab2 = dict(tab, row=-1)
                        res2, ln2 = read_table(nxt, tab2, year, unit, pno + 1)
                        for k, v in res2.items():
                            found.setdefault(k, v)
                        lines += ln2
                break
    if not found:
        res, ln = read_text_disclosure(pages)
        if res:
            found, lines, style = res, ln, ("附注文字披露", ln[0][0], "见原文")
    best, hits, change = policy([(p, r) for p, r, _ in pages])
    dev = dev_rows([(p, r) for p, r, _ in pages])
    diag = []
    if not found:
        for pno, rows, t in pages:
            if re.search(r"摊销|原值|原价", t):
                diag.append((pno, "\n".join(" ".join(f"{w[3]}({w[0]:.0f}-{w[1]:.0f})" for w in r) for r in rows)))
    return found, lines, style, best, hits, change, dev, diag[:6]


FIELDS = ["原值_期初", "原值_增加", "原值_增加_购置", "原值_增加_内部研发", "原值_增加_企业合并", "原值_减少", "原值_减少_处置", "原值_期末",
          "摊销_期初", "摊销_增加", "摊销_减少", "摊销_期末", "减值_期初", "减值_增加", "减值_减少", "减值_期末", "净值_期末", "净值_期初"]


def put(ws, row):
    ws.append([ILLEGAL.sub("", v) if isinstance(v, str) else v for v in row])


def main():
    base = Path(REPORT_DIR)
    files = [(f, fd) for fd in FOLDERS for f in sorted((base / fd).glob("*.[pP][dD][fF]"))]
    if not files:
        sys.exit(f"在 {base} 下没有找到 PDF，请检查 REPORT_DIR 与 FOLDERS 两行。")
    print(f"共 {len(files)} 份年报，开始处理（大约需要十几到几十分钟，请不要关闭窗口）…")
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "无形资产明细"
    put(ws, ["报告年度", "股票代码", "简称", "表格样式", "页码", "单位"] + FIELDS + ["原值勾稽", "摊销勾稽", "文件"])
    wp = wb.create_sheet("摊销政策")
    put(wp, ["报告年度", "股票代码", "简称", "使用寿命下限(年)", "使用寿命上限(年)", "摊销方法", "页码", "原文", "其他候选", "会计估计变更线索"])
    wd = wb.create_sheet("开发支出"); put(wd, ["报告年度", "股票代码", "简称", "页码", "原文", "数字（从左到右）"])
    wl = wb.create_sheet("明细行"); put(wl, ["报告年度", "股票代码", "简称", "页码", "部分", "归类", "原文"])
    wg = wb.create_sheet("诊断"); put(wg, ["报告年度", "股票代码", "简称", "页码", "页面原文（词后括号为横向位置）"])
    ok = 0
    for n, (f, fd) in enumerate(files, 1):
        m = re.match(r"(\d{6})_(.+?)_(20\d\d)", f.stem)
        code, name, year = (m.group(1), m.group(2), int(m.group(3))) if m else ("", f.stem, int(fd[:4]))
        print(f"[{n}/{len(files)}] {f.name}")
        try:
            found, lines, style, best, hits, change, dev, diag = process(f, year)
        except Exception as e:                                          # 个别文件损坏时继续
            print("   出错，跳过：", e)
            put(wg, [year, code, name, "", f"出错：{e}"])
            continue
        ok += bool(found)
        g = lambda k: found.get(k)
        chk = lambda a, b, c, d: (None if None in (a, d) else round((a or 0) + (b or 0) - (c or 0) - d, 2))
        put(ws, [year, code, name, style[0] if style else "未取到", style[1] if style else None, style[2] if style else None]
            + [g(k) for k in FIELDS]
            + [chk(g("原值_期初"), g("原值_增加"), g("原值_减少"), g("原值_期末")),
               chk(g("摊销_期初"), g("摊销_增加"), g("摊销_减少"), g("摊销_期末")), f.name])
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
    out = base / "数据资源附注明细.xlsx"
    try:
        wb.save(out)
    except PermissionError:
        sys.exit(f"写不进 {out}：请先关掉 Excel 里打开的这个文件，再重新运行")
    print("\n" + "=" * 50)
    print(f"处理 {len(files)} 份年报，其中 {ok} 份取到了数据资源无形资产明细")
    print("没取到的多为数据资源只在开发支出或存货项下，或附注表格样式特殊，见「诊断」页")
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
