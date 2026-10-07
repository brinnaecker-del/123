"""由 CSMAR 股东股权质押情况明细表（PLED_TRDDETL，可多个分卷）推算出质方年末未解押质押股数，
并与第一大股东面板匹配，得到“明细表口径”的第一大股东质押比例。

用法：python -I 02_pledge_detail.py <输入目录> <派生目录>
输入目录放 PLED_TRDDETL*.xlsx；派生目录须已有 01_top1_panel.py 输出的 top1_panel.csv。
规则：每个 EventID 取变动日期不晚于当年 12 月 31 日的最后一条记录，其 NumAfterChg 即年末余额；
不做任何插补。另报告一个敏感性口径：最后一条记录之后已过合同结束日期且无解押记录的，视为已解押。
"""
import sys, glob, os, re
import numpy as np
import pandas as pd

src, der = sys.argv[1], sys.argv[2]
parts = sorted(glob.glob(os.path.join(src, '*PLED_TRDDETL*.xlsx')))
# 第 1 卷带三行表头；后续分卷无表头、且前部为空行（接续第 1 卷行号），按第 1 卷列名对齐
head = pd.read_excel(parts[0], header=0, skiprows=[1, 2], dtype=str)
cols = list(head.columns)
frames = [head]
for f in parts[1:]:
    x = pd.read_excel(f, header=None, dtype=str).dropna(how='all')
    if str(x.iloc[0, 0]) == cols[0]:  # 若该卷也带表头
        x = x.iloc[3:]
    x.columns = cols
    frames.append(x)
d = pd.concat(frames, ignore_index=True).drop_duplicates()
for c in ['EventSeq', 'NumBeforeChg', 'ChangeNum', 'NumAfterChg', 'NumHolderOwn', 'TotNumShares', 'ClosePrice']:
    d[c] = pd.to_numeric(d[c], errors='coerce')
d['ChangeDate'] = pd.to_datetime(d['ChangeDate'], errors='coerce')
d['EndDate'] = pd.to_datetime(d['EndDate'], errors='coerce')
d = d.sort_values(['EventID', 'ChangeDate', 'EventSeq'])

def norm(s):
    s = str(s).strip().replace('（', '(').replace('）', ')')
    return re.sub(r'\s+', '', s)
d['name'] = d['Pledgor'].map(norm)

years = range(2004, 2026)
rows = []
for y in years:
    cut = pd.Timestamp(f'{y}-12-31')
    last = d[d['ChangeDate'] <= cut].groupby('EventID').tail(1)
    out = last['NumAfterChg'].astype(float)
    expired = last['EndDate'].notna() & (last['EndDate'] < cut)
    g = pd.DataFrame({'Stkcd': last['Symbol'], 'name': last['name'], 'year': y,
                      'pledged': out, 'pledged_endadj': out.where(~expired, 0.0)})
    rows.append(g.groupby(['Stkcd', 'name', 'year'], as_index=False)[['pledged', 'pledged_endadj']].sum())
bal = pd.concat(rows, ignore_index=True)
bal.to_csv(os.path.join(der, 'pledgor_yearend_balance.csv'), index=False, encoding='utf-8-sig')

top1 = pd.read_csv(os.path.join(der, 'top1_panel.csv'), dtype={'Stkcd': str})
top1['name'] = top1['Top1Name'].map(norm)
codes = sorted(d['Symbol'].unique())
lo, hi = codes[0], codes[-1]
# 仅保留明细表分卷完整覆盖的代码区间（末尾代码可能被截断，剔除）
cov = top1[(top1['Stkcd'] >= lo) & (top1['Stkcd'] < hi)].copy()
m = cov.merge(bal, on=['Stkcd', 'name', 'year'], how='left')
m[['pledged', 'pledged_endadj']] = m[['pledged', 'pledged_endadj']].fillna(0.0)
m['Pledge_detail'] = m['pledged'] / m['Top1Shares']
m['Pledge_detail_endadj'] = m['pledged_endadj'] / m['Top1Shares']
m['Pledge_Ratio2_detail'] = np.nan  # 须总股本，待交易/股本数据
m.to_csv(os.path.join(der, 'pledge_detail_panel.csv'), index=False, encoding='utf-8-sig')

firm_pledge = set(d['Symbol'])
rep = [
    f'明细表分卷：{[os.path.basename(p) for p in parts]}；记录 {len(d)} 条、事件 {d.EventID.nunique()} 个、公司 {len(firm_pledge)} 家，代码 {lo}—{hi}',
    f'用于匹配的代码区间：[{lo}, {hi})（末尾代码 {hi} 可能跨分卷，剔除）；第一大股东公司—年度 {len(m)} 个',
    f'其中第一大股东名下有未解押余额的 {int((m.pledged > 0).sum())} 个；比例>1 的 {int((m.Pledge_detail > 1.0001).sum())} 个（未截断，待核）',
    f'有余额但最后记录已过合同结束日的余额占比：{(1 - m.pledged_endadj.sum() / m.pledged.sum()):.3f}',
]
# 该区间内有质押事件、但第一大股东名称从未与出质方匹配上的公司（可能名称不一致）
any_top1 = m[m.pledged > 0]['Stkcd'].unique()
rel1 = d[d['RelationtoComCode'].astype(str).str.contains('1')]['Symbol'].unique()
miss = sorted(set(rel1) & set(cov.Stkcd) - set(any_top1))
rep.append(f'明细表中有“控股股东”质押、但从未与第一大股东名称匹配上的公司 {len(miss)} 家（需核对名称）：{miss[:20]}')
rep.append('Pledge_detail>0 与十大股东文件 S0303a 原始代码的交叉表（2007年起）：')
mm = m[m.year >= 2007]
rep.append(pd.crosstab(mm.Pledge_detail > 0, mm.Top1Flag_raw).to_string())
open(os.path.join(der, '质押明细核查报告.txt'), 'w', encoding='utf-8').write('\n'.join(rep))
print('\n'.join(rep))
