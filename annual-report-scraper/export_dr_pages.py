"""
导出年报里与「数据资源」有关的页面（文字及其在页面上的位置），供附注明细的解析与核对使用（配合 extract_dr_notes.py）

用法：在 PyCharm 里右键本文件 → 运行。
读取 REPORT_DIR 下 2024年报、2025年报 两个文件夹里的全部 PDF，结果存为 REPORT_DIR 里的「数据资源页面.zip」：
  · 每份年报一个 json：含「数据资源」的页面及其前后各一页，逐词记录文字和坐标；
  · 每一页上「单位：……」「人民币千元」之类的说明（判断金额单位用）。
文件只有几 MB，不含图片，也不改动 PDF。
需要先安装：pip install pymupdf
"""

import json
import re
import sys
import unicodedata
import zipfile
from pathlib import Path

try:
    import pymupdf
except ImportError:
    print("缺少工具包，请先在终端运行：pip install pymupdf")
    input("按回车键退出…")
    sys.exit(1)

# ============================ 需要改的只有这里 ============================
REPORT_DIR = r"E:\数据资产入表年报"      # 年报所在文件夹
FOLDERS = ["2024年报", "2025年报"]       # 要处理的子文件夹
# ========================================================================

UNIT_HINT = re.compile(r".{0,12}(?:单位|人民币(?:百万元|千元|万元|亿元)).{0,16}")


def compact(s):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", s))


def dump(pdf):
    doc = pymupdf.open(pdf)
    texts = [compact(pg.get_text()) for pg in doc]
    want = set()
    for i, t in enumerate(texts):
        if "数据资源" in t:
            want.update({i - 1, i, i + 1})
    pages = []
    for i in sorted(k for k in want if 0 <= k < len(doc)):
        pg = doc[i]
        words = [[round(w[0], 1), round(w[1], 1), round(w[2], 1), round(w[3], 1), w[4], w[5], w[6]] for w in pg.get_text("words")]
        pages.append({"page": i + 1, "size": [round(pg.rect.width, 1), round(pg.rect.height, 1)],
                      "has_dr": "数据资源" in texts[i], "text": pg.get_text(), "words": words})
    units = [[i + 1, [m.group(0) for m in UNIT_HINT.finditer(t)][:8]] for i, t in enumerate(texts) if UNIT_HINT.search(t)]
    return {"file": pdf.name, "n_pages": len(doc), "pages": pages, "units": units}


def main():
    base = Path(REPORT_DIR)
    files = [(f, fd) for fd in FOLDERS for f in sorted((base / fd).glob("*.[pP][dD][fF]"))]
    if not files:
        sys.exit(f"在 {base} 下没有找到 PDF，请检查 REPORT_DIR 与 FOLDERS 两行。")
    out = base / "数据资源页面.zip"
    print(f"共 {len(files)} 份年报，开始导出（大约需要十几分钟，请不要关闭窗口）…")
    ok = 0
    try:
        zf = zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED)
    except PermissionError:
        sys.exit(f"写不进 {out}：请先关掉打开着的这个文件，再重新运行")
    with zf:
        for n, (f, fd) in enumerate(files, 1):
            print(f"[{n}/{len(files)}] {f.name}")
            try:
                rec = dump(f)
            except Exception as e:                                      # 个别文件损坏时继续
                print("   出错，跳过：", e)
                rec = {"file": f.name, "error": str(e)}
            else:
                ok += 1
            zf.writestr(f"{fd}/{f.stem}.json", json.dumps(rec, ensure_ascii=False))
    print("\n" + "=" * 50)
    print(f"导出 {ok}/{len(files)} 份年报")
    print(f"结果：{out}（大小 {out.stat().st_size / 1e6:.1f} MB），请把这个文件发给我")


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
