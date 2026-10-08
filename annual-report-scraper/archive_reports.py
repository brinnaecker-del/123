#!/usr/bin/env python3
"""
把用户发来的年报 PDF 存进仓库的「年报存档」文件夹，供写论文时查阅。

  python archive_reports.py 文件1.pdf 文件2.pdf ...

· 文件名沿用下载脚本的格式（代码_简称_标题.PDF），据此识别代码、简称、报告年度；
· PDF 按年度放进 年报存档/2024年报、年报存档/2025年报；
· 同时用 pdftotext 抽出全文存成同名 .txt，方便检索和引用页码（页与页之间用分页符 \\f 隔开）；
· 每存一份，在 年报存档/清单.csv 里登记一行。
"""

import csv
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "年报存档"
INDEX = ROOT / "清单.csv"
HEADER = ["报告年度", "股票代码", "简称", "文件", "页数", "大小MB", "存档日期"]


def parse_name(path):
    stem = path.stem
    code = re.search(r"(?<!\d)\d{6}(?!\d)", stem)
    year = re.search(r"(20\d{2})\s*年", stem)
    parts = stem.split("_")
    name = parts[1] if len(parts) > 1 and code and parts[0] == code.group(0) else ""
    return (code.group(0) if code else ""), name, (year.group(1) if year else "")


def pages_of(pdf):
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    m = re.search(r"^Pages:\s+(\d+)", out, re.M)
    return int(m.group(1)) if m else ""


def main(files):
    rows = []
    if INDEX.exists():
        with open(INDEX, encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))[1:]
    by_file = {r[3]: r for r in rows}
    for src in map(Path, files):
        code, name, year = parse_name(src)
        folder = ROOT / (f"{year}年报" if year else "未识别年度")
        folder.mkdir(parents=True, exist_ok=True)
        dest = folder / (src.stem + ".pdf")
        shutil.copyfile(src, dest)
        subprocess.run(["pdftotext", "-layout", str(dest), str(dest.with_suffix(".txt"))], check=True)
        rel = str(dest.relative_to(ROOT))
        by_file[rel] = [year, code, name, rel, pages_of(dest),
                        f"{dest.stat().st_size / 1e6:.1f}", date.today().isoformat()]
        print(f"已存档：{rel}（{by_file[rel][4]} 页）")
    with open(INDEX, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(sorted(by_file.values(), key=lambda r: (r[0], r[1])))
    print(f"清单共 {len(by_file)} 份：{INDEX}")


if __name__ == "__main__":
    main(sys.argv[1:])
