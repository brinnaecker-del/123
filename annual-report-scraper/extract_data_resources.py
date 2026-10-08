"""
从已下载的年报 PDF 中提取「数据资源」入表信息（配合 data_assets_reports.py 使用）

用法：在 PyCharm 里右键本文件 → 运行。
读取 REPORT_DIR 下 2024年报、2025年报 两个文件夹里的全部 PDF，结果存为 REPORT_DIR 里的「数据资源提取结果.xlsx」：
  · 汇总：每份年报一行——合并资产负债表中存货 / 无形资产 / 开发支出项下「其中：数据资源」的期末、期初金额（已折算成元），
          以及「数据资源」「数据资产」等关键词在全文出现的次数；
  · 资产负债表原始行：找到的每一行「数据资源」原文、页码、单位，供逐条核对；
  · 原文摘录：全文中提到「数据资源」「数据资产」的段落及页码，写论文时引用。
自动提取难免有个别表格排版特殊的年报识别不准，请对照 PDF 抽查；页码和原文都保留在表里。
需要先安装：pip install pymupdf openpyxl
"""

import re
import sys
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

# 附注编号（如「七、10」「(七)10」「附注五」），先去掉，免得当成金额
NOTE_REF = re.compile(r"[一二三四五六七八九十]+\s*[、.．]\s*[（(]?\d+[）)]?|[（(][一二三四五六七八九十]+[）)]\s*\d*"
                      r"|附注\S*|注\s*\d+")
AMOUNT = re.compile(r"[（(]?-?\d[\d,]*(?:\.\d+)?[）)]?|[-—–]+")
UNIT_RE = re.compile(r"单位(?:均为|为)?[：:]?(?:人民币)?(百万元|千元|万元|亿元|元)")


def compact(s):
    return re.sub(r"\s+", "", s)


def page_rows(page):
    """把页面上的文字按纵坐标拼成一行行（表格的一行 = 一行文字）。"""
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
    return [" ".join(w[4] for w in sorted(r, key=lambda w: w[0])) for r in rows]


def split_row(text):
    """表格行 -> (项目名称, [金额…])；金额为 None 表示「-」。"""
    text = NOTE_REF.sub(" ", text)
    m = AMOUNT.search(text)
    label = compact(text[:m.start()] if m else text)
    values = []
    for tok in AMOUNT.findall(text[m.start():] if m else ""):
        if set(tok) <= set("-—–"):
            values.append(None)
            continue
        neg = tok.startswith(("(", "（")) or tok.lstrip("(（").startswith("-")
        num = float(re.sub(r"[^\d.]", "", tok) or 0)
        values.append(-num if neg else num)
    return label, values


def is_heading(row, names):
    """这一行是不是报表标题（单独成行，如「合并资产负债表」「合并资产负债表（续）」），而不是正文里提到它。"""
    c = compact(row)
    return len(c) <= 30 and c.startswith(names)


def find_balance_sheet(doc):
    """返回合并资产负债表起始页（从审计报告之后找，避开目录和管理层讨论里的同名表格）。"""
    texts = [compact(p.get_text()) for p in doc]
    audit = next((i for i, t in enumerate(texts) if "我们审计了" in t), 0)
    for i in range(audit, len(texts)):
        t = texts[i]
        if "合并资产负债表" in t and any(k in t for k in ("资产总计", "货币资金", "流动资产", "现金及存放中央银行款项")):
            if any(is_heading(r, ("合并资产负债表",)) for r in page_rows(doc[i])):
                return i, texts
    return None, texts


def extract(pdf_path):
    doc = pymupdf.open(pdf_path)
    start, texts = find_balance_sheet(doc)
    result = {"pages": len(doc), "bs_page": "", "unit": "", "lines": [], "quotes": [], "status": ""}

    if start is None:
        result["status"] = "没找到合并资产负债表"
    else:
        result["bs_page"] = start + 1
        unit = UNIT_RE.search(texts[start]) or (UNIT_RE.search(texts[start + 1]) if start + 1 < len(texts) else None)
        result["unit"] = unit.group(1) if unit else "元"
        if not unit:
            result["status"] = "未注明单位，按元处理"
        prev_label = ""
        done = False
        for i in range(start, min(start + 6, len(doc))):
            for row in page_rows(doc[i]):
                if i > start and is_heading(row, ("母公司资产负债表", "合并利润表", "利润表")):
                    done = True
                    break
                label, values = split_row(row)
                if not label:
                    continue
                if "数据资源" in label and len(label) <= 12:
                    parent = prev_label if prev_label in PARENTS else f"其他（{prev_label}）"
                    nums = values[-2:] if len(values) >= 2 else values + [None] * (2 - len(values))
                    result["lines"].append({"parent": parent, "end": nums[0], "begin": nums[1],
                                            "page": i + 1, "raw": row.strip()})
                elif not label.startswith("其中"):
                    prev_label = label
            if done:
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

    summary, raw_lines, quotes = [], [], []
    for n, (year, pdf) in enumerate(pdfs, 1):
        parts = pdf.stem.split("_")
        code = parts[0] if parts and re.fullmatch(r"\d{6}", parts[0]) else ""
        name = parts[1] if len(parts) > 1 else ""
        try:
            r = extract(pdf)
        except Exception as e:  # 个别 PDF 损坏或加密时不影响其他文件
            print(f"[{n}/{len(pdfs)}] {pdf.name}：出错 {e}")
            summary.append([year, code, name] + [None] * 9 + ["", "", "", f"出错：{e}", pdf.name])
            continue
        unit = r["unit"]
        by_parent = {p: [0.0, 0.0, False] for p in PARENTS}
        for ln in r["lines"]:
            raw_lines.append([year, code, name, ln["parent"], ln["end"], ln["begin"], unit,
                              to_yuan(ln["end"], unit), to_yuan(ln["begin"], unit), ln["page"], ln["raw"], pdf.name])
            if ln["parent"] in by_parent:
                b = by_parent[ln["parent"]]
                b[0] += to_yuan(ln["end"], unit) or 0
                b[1] += to_yuan(ln["begin"], unit) or 0
                b[2] = True
        cells = []
        for p in PARENTS:
            cells.append(by_parent[p][0] if by_parent[p][2] else None)
        total_end = sum(by_parent[p][0] for p in PARENTS)
        total_begin = sum(by_parent[p][1] for p in PARENTS)
        found = any(by_parent[p][2] for p in PARENTS)
        status = r["status"] or ("" if found else "资产负债表里没找到「数据资源」行")
        summary.append([year, code, name] + cells + [total_end if found else None, total_begin if found else None]
                       + [r["counts"][k] for k in COUNT_WORDS]
                       + [r["bs_page"], unit, r["pages"], status, pdf.name])
        for page, text in r["quotes"]:
            quotes.append([year, code, name, page, text, pdf.name])
        print(f"[{n}/{len(pdfs)}] {code} {name} {year}：资产负债表数据资源 {len(r['lines'])} 行，"
              f"摘录 {len(r['quotes'])} 段 {status}")

    out = root / "数据资源提取结果.xlsx"
    header = (["报告年度", "股票代码", "简称"] + [f"{p}中数据资源_期末(元)" for p in PARENTS]
              + ["数据资源合计_期末(元)", "数据资源合计_期初(元)"] + [f"「{k}」出现次数" for k in COUNT_WORDS]
              + ["合并资产负债表页码", "报表单位", "总页数", "提取情况", "文件"])
    try:
        write_book(out, {
            "汇总": (header, summary),
            "资产负债表原始行": (["报告年度", "股票代码", "简称", "挂在哪一项", "期末(原单位)", "期初(原单位)", "单位",
                          "期末(元)", "期初(元)", "页码", "原始行文本", "文件"], raw_lines),
            "原文摘录": (["报告年度", "股票代码", "简称", "页码", "段落", "文件"], quotes),
        })
    except PermissionError:
        sys.exit(f"写不进 {out}：请先关掉 Excel 里打开的这个文件，再重新运行")

    hit = sum(1 for s in summary if s[6] is not None)
    print("\n" + "=" * 50)
    print(f"处理 {len(pdfs)} 份年报，其中 {hit} 份在合并资产负债表里找到了「数据资源」金额")
    print(f"结果：{out}")
    miss = [s for s in summary if s[6] is None]
    if miss:
        print(f"\n下面 {len(miss)} 份没提取到金额，需要人工看一下：")
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
