"""
修复卖家切分的大 xlsx（part2、part3 ……）：这类文件没有表头，且末尾的结束标签重复，Excel/pandas 可能读不出来。
流式读取工作表 XML，转成 CSV，并沿用 part1 的列名。

    python fix_split_xlsx.py 坏文件.xlsx 输出.csv --header-from part1.xlsx
"""
import argparse
import csv
import re
import zipfile

import pandas as pd
from lxml import etree

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


def col_index(ref):
    s = re.match(r'[A-Z]+', ref).group(0)
    n = 0
    for ch in s:
        n = n * 26 + ord(ch) - 64
    return n - 1


def main(src, dst, header_from):
    cols = list(pd.read_excel(header_from, nrows=0).columns)
    z = zipfile.ZipFile(src)
    sheet = [n for n in z.namelist() if n.startswith('xl/worksheets/sheet')][0]
    it = etree.iterparse(z.open(sheet), tag=NS + 'row')
    out = csv.writer(open(dst, 'w', newline='', encoding='utf-8-sig'))
    out.writerow(cols)
    n = 0
    try:
        for _, row in it:
            vals = [''] * len(cols)
            for c in row:
                i = col_index(c.get('r'))
                if i >= len(cols):
                    continue
                if c.get('t') == 'inlineStr':
                    v = c.findtext(f'{NS}is/{NS}t') or ''
                else:
                    v = c.findtext(NS + 'v') or ''
                    if v.endswith('.0'):
                        v = v[:-2]
                vals[i] = v
            if vals[0] and vals[0] != cols[0]:  # 跳过可能残留的表头行
                out.writerow(vals)
                n += 1
            row.clear()
            while row.getprevious() is not None:
                del row.getparent()[0]
    except etree.XMLSyntaxError as e:
        print('已忽略文件末尾的格式错误：', e)
    print(f'写出 {n} 行 → {dst}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--header-from', required=True)
    a = ap.parse_args()
    main(a.src, a.dst, a.header_from)
