"""
从已下载的年报 PDF 中提取「数据资源」入表信息（配合 data_assets_reports.py 使用）

用法：在 PyCharm 里右键本文件 → 运行。
读取 REPORT_DIR 下 2024年报、2025年报 两个文件夹里的全部 PDF，结果存为 REPORT_DIR 里的「数据资源提取结果.xlsx」：
  · 汇总：每份年报一行——存货 / 无形资产 / 开发支出项下数据资源的期末、期初金额（已折算成元）、数据来源，
          以及「数据资源」「数据资产」等关键词在全文出现的次数；
  · 明细行：找到的每一行数据资源原文、页码、单位，供逐条核对；
  · 原文摘录：全文中提到「数据资源」「数据资产」的段落及页码，写论文时引用；
  · 诊断：没提取到金额的年报，列出其中的报表标题行和含「数据资源」的原文行，便于查明原因。
金额优先取合并资产负债表「其中：数据资源」行；报表正文没有这一行的（银行、证券公司常见），
改取附注无形资产明细表里「数据资源」一列的账面价值，并在「来源」一栏注明。
自动提取难免有个别排版特殊的年报识别不准，请对照 PDF 抽查；页码和原文都保留在表里。
需要先安装：pip install pymupdf openpyxl
"""

import re
import sys
import unicodedata
from collections import deque
from pathlib import Path

try:
    import pymupdf
    import openpyxl
except ImportError:
    print("缺少工具包，请先在终端运行：pip install pymupdf openpyxl")
    input("按回车键退出…")
    sys.exit(1)

# ============================ 需要改的只有这里 ============================
REPORT_DIR = r"E:\数据资产入表年报"      # 年报所在文件夹（下载程序的保存位置）
FOLDERS = ["2024年报", "2025年报"]       # 要处理的子文件夹
# ========================================================================

PARENTS = ["存货", "无形资产", "开发支出"]                  # 数据资源可以挂的三个资产负债表项目
COUNT_WORDS = ["数据资源", "数据资产", "数据要素", "入表"]   # 统计全文出现次数
QUOTE_WORDS = ["数据资源", "数据资产"]                      # 摘录含这些词的段落
UNITS = {"元": 1, "千元": 1e3, "万元": 1e4, "百万元": 1e6, "亿元": 1e8}

UNIT_RE = re.compile(r"单位(?:均为|为)?:?(?:人民币)?(百万元|千元|万元|亿元|元)")
NUM_RE = re.compile(r"^\(?-?\d[\d,]*(?:\.\d+)?\)?$")
DASH_RE = re.compile(r"^[-—–]+$")
# 附注编号，如「七、10」「七·83」「(五)」「五、(十二)」「附注七」「注释5」
NOTE_RE = re.compile(r"^(附注.*|注释?\d+|\(?[一二三四五六七八九十]+\)?[、.．·・]?(\(?[一二三四五六七八九十\d]+\)?)*[,，]?)$")
ENUM_RE = re.compile(r"^\(?(\d{1,2}|[一二三四五六七八九十]{1,3})\)?[、.．]?")   # 标题前的编号「1、」「(一)」
BS_WORDS = ("货币资金", "现金及存放中央银行款项", "流动资产", "结算备付金", "存放同业", "资产总计")
END_LABELS = ("资产总计", "资产合计", "流动负债", "负债:", "负债和", "负债及")


def norm(s):
    """统一字符：全角转半角，部首字（如「⾏」）转成常用字。"""
    return unicodedata.normalize("NFKC", s)


def compact(s):
    return re.sub(r"\s+", "", norm(s))


def title_kind(row_text):
    """判断一行是不是报表标题：wide=合并与本公司并排、narrow=合并单列、parent=母公司或单体、other=利润表等。"""
    c = compact(row_text)
    if len(c) > 40:
        return None
    t = ENUM_RE.sub("", c, count=1)
    if re.match(r"合并及(母公司|公司|银行|本行)资产负债表|合并资产负债表(及|和|与)(母公司|公司|银行|本行)?资产负债表", t):
        return "wide"
    if re.match(r"合并资产负债表(?![、，,。及和与日中项表])", t):
        return "narrow"
    if re.match(r"(母公司|公司|银行|本行)资产负债表(?![日中])|资产负债表(?=$|\(续|-|20)", t):
        return "parent"
    if re.match(r"(合并)?(及(母公司|公司|银行|本行))?利润表|(母公司|公司|银行|本行)利润表", t):
        return "other"
    return None


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
    """一行 -> (项目名称, [(左边界 x, 右边界 x, 金额或 None)…], 是否夹杂文字)。

    以元为单位时，不带逗号和小数点的整数（如「83」）多半是附注编号或页码，不算金额。
    """
    label, cells, extra_text = [], [], False
    for x0, x1, w in row:
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
        elif cells:
            extra_text = True          # 金额后面还有文字：不是报表行（如「数据资源 15 年 直线法」）
        else:
            label.append(w)
    return compact("".join(label)), cells, extra_text


def clean_label(label):
    """去掉项目名末尾残留的附注编号、标点，如「存货七·」「无形资产(五)」→「存货」「无形资产」。"""
    prev = None
    while prev != label:
        prev = label
        label = re.sub(r"[、,，.．·・()\d:]+$", "", label)
        label = re.sub(r"[一二三四五六七八九十]+$", "", label)
    return label


ALIGNS = (lambda c: c[1], lambda c: c[0], lambda c: (c[0] + c[1]) / 2)   # 右对齐、左对齐、居中


def columns(cell_rows, wide):
    """根据各行金额的位置找出「期末」「期初」两列。

    金额可能右对齐、左对齐或居中，三种都试，选能把最多金额归进两列的那种。返回 (对齐方式, [期末列, 期初列])。
    """
    def note_column(g):  # 整列都是两位以内的整数：是附注编号列，不是金额列
        return all(v is not None and float(v).is_integer() and abs(v) < 100 for _, v in g)

    best = None
    for key in ALIGNS:
        pts = sorted(((key(c), c[2]) for cells in cell_rows if len(cells) >= 2 for c in cells), key=lambda p: p[0])
        groups = []
        for x, v in pts:
            if groups and x - groups[-1][-1][0] <= 25:
                groups[-1].append((x, v))
            else:
                groups.append([(x, v)])
        good = [g for g in groups if len(g) >= 3 and not note_column(g)]
        if len(good) < 2:
            continue
        chosen = good[:2] if wide or len(good) >= 4 else good[-2:]
        score = sum(len(g) for g in chosen)
        if best is None or score > best[0]:
            best = (score, key, [sorted(x for x, _ in g)[len(g) // 2] for g in chosen])
    return None if best is None else (best[1], best[2])


def assign(cells, cols, wide):
    """把一行里的金额分到期末、期初两列。"""
    if cols:
        key, centers = cols
        end = begin = None
        for c in cells:
            d = [abs(key(c) - x) for x in centers]
            if min(d) <= 40:
                if d[0] <= d[1]:
                    end = c[2] if end is None else end
                else:
                    begin = c[2] if begin is None else begin
        return end, begin
    vals = [c[2] for c in cells]
    vals = vals[:2] if wide or len(vals) >= 4 else vals[-2:]
    vals += [None] * (2 - len(vals))
    return vals[0], vals[1]


def find_balance_sheet(doc, texts):
    """返回 (合并资产负债表起始页, 是否并排格式, 审计报告页)。从审计报告之后找，避开目录和管理层讨论。"""
    audit = next((i for i, t in enumerate(texts) if "我们审计了" in t), 0)
    single = loose = None
    for i in range(audit, len(texts)):
        t = texts[i]
        if "资产负债表" not in t or not any(k in t for k in BS_WORDS):
            continue
        for r in page_rows(doc[i]):
            kind = title_kind(row_text(r))
            if kind in ("wide", "narrow"):
                return i, kind == "wide", audit
            if kind == "parent" and single is None:
                single = i            # 没有子公司的单体报表，标题就是「资产负债表」
        if loose is None:
            loose = i
    return (single if single is not None else loose), False, audit


def unit_near(texts, i):
    for j in (i, i - 1, i + 1):
        if 0 <= j < len(texts):
            m = UNIT_RE.search(texts[j])
            if m:
                return m.group(1)
    return None


def from_balance_sheet(doc, start, wide, unit):
    rows = [(i, r) for i in range(start, min(start + 8, len(doc))) for r in page_rows(doc[i])]
    parsed = [(i, r, *parse_row(r, unit)) for i, r in rows]
    # 资产部分：从标题开始，到资产总计 / 负债 / 下一张报表为止
    body = []
    for k, item in enumerate(parsed):
        i, r, label, cells, extra = item
        if k > 0 and title_kind(row_text(r)) in ("parent", "other"):
            break
        body.append(item)
        if label.startswith(END_LABELS):
            break
    cols = columns([cells for _, _, _, cells, extra in body if not extra], wide)

    lines, recent = [], deque(maxlen=4)
    for k, (i, r, label, cells, extra) in enumerate(body):
        if not label:
            continue
        if ("数据资源" in label or "数据资产" in label) and len(label) <= 12:
            if extra:
                continue
            raw = row_text(r)
            if not cells:
                # 金额和项目名上下错开、被拆成了单独一行：取紧挨着的纯数字行
                for j in (k + 1, k - 1):
                    if 0 <= j < len(body) and not body[j][2] and body[j][3] and not body[j][4]:
                        cells = body[j][3]
                        raw += " ｜相邻行：" + row_text(body[j][1])
                        break
            end, begin = assign(cells, cols, wide)
            parent = next((p for p in reversed(recent) if p in PARENTS), None)
            lines.append({"parent": parent or f"其他（{recent[-1] if recent else ''}）", "end": end, "begin": begin,
                          "page": i + 1, "raw": raw, "source": "资产负债表"})
        elif not label.startswith("其中"):
            lab = clean_label(label)
            if lab and "公司" not in lab and "编制单位" not in lab and lab != "项目":
                recent.append(lab)
    return lines


def from_notes(doc, texts, start, unit):
    """报表正文没有数据资源行时，到附注里找无形资产明细表中「数据资源」一列的期末、期初账面价值。"""
    for i in range(start + 1, len(doc)):
        if "数据资源" not in texts[i] or "账面价值" not in texts[i]:
            continue
        col, end, begin, raw, in_book_value = None, None, None, [], False
        page_unit = unit_near(texts, i) or unit
        for r in page_rows(doc[i]):
            words = [compact(w[2]) for w in r]
            if col is None:
                if "数据资源" in words and any(w in ("软件", "计算机软件", "合计", "土地使用权", "软件及其他") for w in words):
                    x0, x1, _ = r[words.index("数据资源")]
                    col = (x0 + x1) / 2
                continue
            label, cells, _ = parse_row(r, page_unit)
            label = ENUM_RE.sub("", label, count=1)
            if "账面价值" in label and not cells:
                in_book_value = True   # 「四、账面价值」小标题，下面几行是「期末」「期初」
                continue
            if not cells or not ("账面价值" in label or (in_book_value and re.match(r"(期末|年末|期初|年初)", label))):
                continue
            c = min(cells, key=lambda c: abs((c[0] + c[1]) / 2 - col))
            x, v = (c[0] + c[1]) / 2, c[2]
            if abs(x - col) > 60:
                continue
            if re.search(r"(期末|年末)", label) and end is None:
                end = v
                raw.append(row_text(r))
            elif re.search(r"(期初|年初)", label) and begin is None:
                begin = v
                raw.append(row_text(r))
        if end is not None or begin is not None:
            return [{"parent": "无形资产", "end": end, "begin": begin, "page": i + 1,
                     "raw": "；".join(raw), "source": "附注·无形资产明细", "unit": page_unit}]
    return []


def extract(pdf_path):
    doc = pymupdf.open(pdf_path)
    texts = [compact(p.get_text()) for p in doc]
    start, wide, audit = find_balance_sheet(doc, texts)
    result = {"pages": len(doc), "bs_page": "", "unit": "", "wide": wide, "lines": [], "quotes": [],
              "status": "", "diag": []}

    if start is None:
        result["status"] = "没找到合并资产负债表"
    else:
        result["bs_page"] = start + 1
        unit = unit_near(texts, start)
        result["unit"] = unit or "元"
        if not unit:
            result["status"] = "未注明单位，按元处理"
        result["lines"] = from_balance_sheet(doc, start, wide, result["unit"])
        if not result["lines"]:
            result["lines"] = from_notes(doc, texts, start, result["unit"])

    if not any(ln["end"] is not None or ln["begin"] is not None for ln in result["lines"]):
        # 诊断信息：报表标题行、含「数据资源」的原文行
        for i in range(audit, len(doc)):
            if "资产负债表" not in texts[i] and "数据资源" not in texts[i]:
                continue
            for r in page_rows(doc[i]):
                c = compact(row_text(r))
                if ("资产负债表" in c and len(c) <= 40) or ("数据资源" in c and len(c) <= 80):
                    result["diag"].append((i + 1, row_text(r)[:120]))
            if len(result["diag"]) >= 25:
                break

    for i, page in enumerate(doc):
        for block in page.get_text("blocks"):
            text = compact(block[4])
            # 只要成段的文字：汉字少于 15 个的多半是表格里的一格或一行，不算摘录
            if any(k in text for k in QUOTE_WORDS) and len(re.findall(r"[\u4e00-\u9fff]", text)) >= 15:
                result["quotes"].append((i + 1, text[:800]))
    full = "".join(texts)
    result["counts"] = {k: full.count(k) for k in COUNT_WORDS}
    return result


def to_yuan(v, unit):
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


def main():
    root = Path(REPORT_DIR)
    pdfs = [(folder[:4], p) for folder in FOLDERS
            for p in sorted((root / folder).glob("*.[pP][dD][fF]"))]
    if not pdfs:
        sys.exit(f"在 {root} 下的 {'、'.join(FOLDERS)} 里没找到 PDF，请检查 REPORT_DIR 是否正确")
    print(f"共 {len(pdfs)} 份年报，开始提取……\n")

    summary, raw_lines, quotes, diags = [], [], [], []
    for n, (year, pdf) in enumerate(pdfs, 1):
        parts = pdf.stem.split("_")
        code = parts[0] if parts and re.fullmatch(r"\d{6}", parts[0]) else ""
        name = parts[1] if len(parts) > 1 else ""
        try:
            r = extract(pdf)
        except Exception as e:  # 个别 PDF 损坏或加密时不影响其他文件
            print(f"[{n}/{len(pdfs)}] {pdf.name}：出错 {e}")
            summary.append([year, code, name] + [None] * 5 + [""] + [None] * 4 + ["", "", "", "", f"出错：{e}", pdf.name])
            continue
        by_parent = {p: [0.0, 0.0, False] for p in PARENTS}
        sources = []
        for ln in r["lines"]:
            unit = ln.get("unit", r["unit"])
            end, begin = to_yuan(ln["end"], unit), to_yuan(ln["begin"], unit)
            raw_lines.append([year, code, name, ln["parent"], ln["source"], ln["end"], ln["begin"], unit,
                              end, begin, ln["page"], ln["raw"], pdf.name])
            if ln["parent"] in by_parent and (end is not None or begin is not None):
                b = by_parent[ln["parent"]]
                b[0] += end or 0
                b[1] += begin or 0
                b[2] = True
                if ln["source"] not in sources:
                    sources.append(ln["source"])
        found = any(by_parent[p][2] for p in PARENTS)
        cells = [by_parent[p][0] if by_parent[p][2] else None for p in PARENTS]
        totals = [sum(by_parent[p][0] for p in PARENTS), sum(by_parent[p][1] for p in PARENTS)] if found else [None, None]
        if r["lines"] and not found:
            status = "有数据资源行，但金额为空"
        else:
            status = r["status"] or ("" if found else "没找到数据资源金额")
        summary.append([year, code, name] + cells + totals + ["、".join(sources)]
                       + [r["counts"][k] for k in COUNT_WORDS]
                       + [r["bs_page"], r["unit"], "合并与本公司并排" if r["wide"] else "合并单列", r["pages"],
                          status, pdf.name])
        for page, text in r["diag"]:
            diags.append([year, code, name, status, page, text, pdf.name])
        for page, text in r["quotes"]:
            quotes.append([year, code, name, page, text, pdf.name])
        print(f"[{n}/{len(pdfs)}] {code} {name} {year}：数据资源 {len(r['lines'])} 行"
              f"{'（' + '、'.join(sources) + '）' if sources else ''}，摘录 {len(r['quotes'])} 段 {status}")

    out = root / "数据资源提取结果.xlsx"
    header = (["报告年度", "股票代码", "简称"] + [f"{p}中数据资源_期末(元)" for p in PARENTS]
              + ["数据资源合计_期末(元)", "数据资源合计_期初(元)", "来源"] + [f"「{k}」出现次数" for k in COUNT_WORDS]
              + ["合并资产负债表页码", "报表单位", "报表格式", "总页数", "提取情况", "文件"])
    try:
        write_book(out, {
            "汇总": (header, summary),
            "明细行": (["报告年度", "股票代码", "简称", "挂在哪一项", "来源", "期末(原单位)", "期初(原单位)", "单位",
                       "期末(元)", "期初(元)", "页码", "原文", "文件"], raw_lines),
            "原文摘录": (["报告年度", "股票代码", "简称", "页码", "段落", "文件"], quotes),
            "诊断": (["报告年度", "股票代码", "简称", "提取情况", "页码", "原文行", "文件"], diags),
        })
    except PermissionError:
        sys.exit(f"写不进 {out}：请先关掉 Excel 里打开的这个文件，再重新运行")

    hit = sum(1 for s in summary if s[6] is not None)
    print("\n" + "=" * 50)
    print(f"处理 {len(pdfs)} 份年报，其中 {hit} 份提取到了数据资源金额")
    print(f"结果：{out}")
    miss = [s for s in summary if s[6] is None]
    if miss:
        print(f"\n下面 {len(miss)} 份没提取到金额（原因线索见 Excel 的「诊断」页）：")
        for s in miss:
            print(f"  {s[0]} {s[1]} {s[2]}  {s[-2]}")


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
