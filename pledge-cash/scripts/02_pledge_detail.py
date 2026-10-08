"""整理 CSMAR 股东股权质押情况明细表（PLED_TRDDETL，可多个分卷），输出“事件—年度”余额与事件信息。

用法：python -I 02_pledge_detail.py <输入目录> <派生目录>
输出：
- pled_detail_all.pkl：全部明细记录（05 复用）
- detail_event_info.pkl：每个 EventID 的公司、出质方ID、起始日、起始日收盘价、历史上出现过的全部名称（基本与宽松口径）、
  全部记录中最新的结束日期
- detail_event_year.pkl：每年 12 月 31 日前最后一条记录的剩余质押数量（>0 者），及该记录日期
与第一大股东的匹配在 04（质押比例明细表口径）与 05（平仓压力）中用同一规则完成（matching.py）。不做任何插补。
"""
import sys, glob, os
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from names import norm_basic, norm_loose

src, der = sys.argv[1], sys.argv[2]
parts = sorted(glob.glob(os.path.join(src, '*PLED_TRDDETL*.xlsx')))
# 第 1 卷带三行表头；后续分卷无表头、且前部为空行（接续第 1 卷行号），按第 1 卷列名对齐
head = pd.read_excel(parts[0], header=0, skiprows=[1, 2], dtype=str)
cols = list(head.columns)
frames = [head]
for f in parts[1:]:
    x = pd.read_excel(f, header=None, dtype=str).dropna(how='all')
    if str(x.iloc[0, 0]) == cols[0]:
        x = x.iloc[3:]
    x.columns = cols
    frames.append(x)
d = pd.concat(frames, ignore_index=True).drop_duplicates()
for c in ['EventSeq', 'NumBeforeChg', 'ChangeNum', 'NumAfterChg', 'NumHolderOwn', 'TotNumShares', 'ClosePrice']:
    d[c] = pd.to_numeric(d[c], errors='coerce')
for c in ['ChangeDate', 'StartDate', 'EndDate']:
    d[c] = pd.to_datetime(d[c], errors='coerce')
d['name'] = d['Pledgor'].map(norm_basic)
d['name_loose'] = d['Pledgor'].map(norm_loose)
d = d.sort_values(['EventID', 'ChangeDate', 'EventSeq'])
d.to_pickle(os.path.join(der, 'pled_detail_all.pkl'))

g = d.groupby('EventID')
first = g.head(1).set_index('EventID')
info = pd.DataFrame({'Stkcd': first['Symbol'], 'PledgorID': first['PledgorID'], 'start': first['StartDate'],
                     'P0': first['ClosePrice']})
info['names'] = g['name'].agg(lambda s: frozenset(s))
info['names_loose'] = g['name_loose'].agg(lambda s: frozenset(s))
info['end_full'] = d.dropna(subset=['EndDate']).groupby('EventID')['EndDate'].last()
info.to_pickle(os.path.join(der, 'detail_event_info.pkl'))

rows = []
for y in range(2004, 2026):
    cut = pd.Timestamp(f'{y}-12-31')
    last = d[d['ChangeDate'] <= cut].groupby('EventID').tail(1)
    last = last[last['NumAfterChg'] > 0]
    rows.append(pd.DataFrame({'EventID': last['EventID'].to_numpy(), 'year': y, 'bal': last['NumAfterChg'].to_numpy(float),
                              'last_date': last['ChangeDate'].to_numpy()}))
ey = pd.concat(rows, ignore_index=True)
ey.to_pickle(os.path.join(der, 'detail_event_year.pkl'))

x = d.NumBeforeChg + d.ChangeNum - d.NumAfterChg
rep = [
    f'明细表分卷：{[os.path.basename(p) for p in parts]}；记录 {len(d)} 条、事件 {d.EventID.nunique()} 个、公司 {d.Symbol.nunique()} 家',
    f'剩余质押数量 = 初始数量 + 数量增减 不成立的记录 {int((x.abs() > 1).sum())} 条',
    f'事件—年度（年末剩余数量>0）{len(ey)} 个',
    f'同一事件出现多个名称的 {int((info.names.map(len) > 1).sum())} 个；同一事件出现多个出质方ID的 {int((g.PledgorID.nunique() > 1).sum())} 个',
]
open(os.path.join(der, '质押明细核查报告.txt'), 'w', encoding='utf-8').write('\n'.join(rep))
print('\n'.join(rep))
