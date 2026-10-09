"""
把「人工确认清单」里要核对的年报页面挑出来，合成一个小文件，便于发给别人逐条核对。

用法：在 PyCharm 里右键本文件 → 运行。结果存到 REPORT_DIR：
  · 核对页.txt：每页的文字按行列出，每个词后面括号里是它在页面上的横向位置，用来判断数字属于哪一列；
  · 核对页.pdf：这些页面的原样截取，每页顶部标注「公司 年度 原文第几页」。
需要先安装：pip install pymupdf
"""

import re
import sys
import unicodedata
from pathlib import Path

try:
    import pymupdf
except ImportError:
    print("缺少工具包，请先在终端运行：pip install pymupdf")
    input("按回车键退出…")
    sys.exit(1)

REPORT_DIR = r"E:\数据资产入表年报"

# (报告年度, 股票代码, 简称, 要看的原文页码, 是否另外把提到「数据资源」的页面都带上)
TARGETS = [
    ("2024", "600926", "杭州银行", [183, 184], True),
    ("2024", "601665", "齐鲁银行", [180, 181], True),
    ("2025", "601665", "齐鲁银行", [180, 181], True),
    ("2024", "601800", "中国交建", [219, 267, 336], True),
    ("2025", "601800", "中国交建", [198, 270, 342], True),
    ("2025", "000546", "金圆股份", [71, 72], True),
    ("2025", "601059", "信达证券", [111, 172, 208], True),
    ("2025", "600029", "南方航空", [92, 93], True),
    ("2024", "002609", "捷顺科技", [], True),
    ("2025", "002609", "捷顺科技", [], True),
    ("2024", "000783", "长江证券", [166, 167, 229], False),
    ("2024", "001872", "招商港口", [239], False),
    ("2024", "002142", "宁波银行", [151], False),
    ("2024", "600100", "同方股份", [175], False),
    ("2024", "601818", "光大银行", [256], False),
    ("2024", "601998", "中信银行", [322], False),
    ("2024", "605006", "山东玻纤", [233], False),
    ("2025", "002142", "宁波银行", [145], False),
    ("2025", "002673", "西部证券", [202], False),
    ("2025", "600926", "杭州银行", [175], False),
    ("2025", "601077", "渝农商行", [261], False),
    ("2025", "601998", "中信银行", [311], False),
    ("2024", "002468", "申通快递", [124, 125], False),
    ("2025", "002468", "申通快递", [120, 121], False),
    ("2025", "600600", "青岛啤酒", [69, 70], False),
]
MAX_MENTION_PAGES = 12


def compact(s):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", s))


def page_rows(page):
    """把页面上的文字按纵坐标拼成一行行，每个词带上横向位置。"""
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
    return [" ".join(f"{unicodedata.normalize('NFKC', w[4])}({w[0]:.0f}-{w[2]:.0f})"
                     for w in sorted(r, key=lambda w: w[0])) for r in rows]


def pages_for(doc, wanted, scan):
    pages = {p - 1 for p in wanted if 1 <= p <= len(doc)}
    if scan:
        texts = [compact(p.get_text()) for p in doc]
        audit = next((i for i, t in enumerate(texts) if "我们审计了" in t), 0)
        mention = [i for i in range(audit, len(doc)) if "数据资源" in texts[i]]
        if not mention:   # 全文没有「数据资源」：带上无形资产附注的明细表
            mention = [i for i in range(audit, len(doc)) if "无形资产" in texts[i] and "累计摊销" in texts[i]][:4]
        pages.update(mention[:MAX_MENTION_PAGES])
    return sorted(pages)


def main():
    root = Path(REPORT_DIR)
    out_pdf = pymupdf.open()
    lines = ["核对页：每行文字后括号里是该词在页面上的横向位置（左边界-右边界），同一列的数字位置相近。", ""]
    missing = []
    for n, (year, code, name, wanted, scan) in enumerate(TARGETS, 1):
        files = sorted((root / f"{year}年报").glob(f"{code}_*.[pP][dD][fF]"))
        if not files:
            missing.append(f"{year} {code} {name}")
            continue
        doc = pymupdf.open(files[0])
        pages = pages_for(doc, wanted, scan)
        print(f"[{n}/{len(TARGETS)}] {year} {code} {name}：{len(pages)} 页")
        for i in pages:
            tag = f"[{n}] {year} {code} {name}  原文第 {i + 1} 页（共 {len(doc)} 页）"
            lines.append("=" * 20 + " " + tag + " " + "=" * 20)
            lines.extend(page_rows(doc[i]))
            lines.append("")
            out_pdf.insert_pdf(doc, from_page=i, to_page=i)
            out_pdf[-1].insert_text((20, 14), tag, fontname="china-s", fontsize=8, color=(0.8, 0, 0))
    (root / "核对页.txt").write_text("\n".join(lines), encoding="utf-8")
    out_pdf.save(root / "核对页.pdf", garbage=3, deflate=True)
    size = (root / "核对页.pdf").stat().st_size / 1e6
    print("\n" + "=" * 50)
    print(f"已生成：{root / '核对页.txt'}")
    print(f"已生成：{root / '核对页.pdf'}（{size:.1f} MB，共 {len(out_pdf)} 页）")
    if missing:
        print("没找到这些年报的 PDF：" + "、".join(missing))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        print("\n出错了，请把上面的报错信息截图发给我。")
    input("\n按回车键退出…")
