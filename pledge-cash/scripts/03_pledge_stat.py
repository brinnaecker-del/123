"""由 CSMAR 股东股权质押统计表（PLED_TRDSTAT）推算出质方年末未解押质押股数（开题报告“第1步”的基准口径）。

用法：python -I 03_pledge_stat.py <输入目录> <派生目录>
规则：同一公司、同一出质方ID按变动日期累加“数量增减”；当记录为全部解押且“质押笔数”为空或为 0 时，余额归零
（本数据中质押笔数从不为 0，全部解押时为空值）；负余额与归零前的残差另行报告，不做插补。
取每年 12 月 31 日前最后一条记录的余额作为年末余额。
"""
import sys, os, re
import numpy as np
import pandas as pd

src, der = sys.argv[1], sys.argv[2]
st = pd.read_excel(os.path.join(src, 'PLED_TRDSTAT.xlsx'), header=0, skiprows=[1, 2],
                   dtype={'Symbol': str, 'PledgorID': str, 'ChangeReasonCode': str})
st['ChangeDate'] = pd.to_datetime(st['ChangeDate'])
st = st.reset_index().sort_values(['Symbol', 'PledgorID', 'ChangeDate', 'index'])

def norm(s):
    s = str(s).strip().replace('（', '(').replace('）', ')')
    return re.sub(r'\s+', '', s)
st['name'] = st['Pledgor'].map(norm)

full = st['ChangeReason'].str.contains('全部解押') & (st['Pledtimes'].isna() | (st['Pledtimes'] == 0))
bal, resid = [], []
for _, g in st.groupby(['Symbol', 'PledgorID'], sort=False):
    b = 0.0
    for chg, f in zip(g['ChangeNum'].to_numpy(float), full.loc[g.index].to_numpy()):
        b += chg
        if f:
            resid.append(b)  # 归零前的累加残差，理想情况为 0
            b = 0.0
        bal.append(b)
st['balance'] = bal
resid = np.array(resid)

rows = []
for y in range(2004, 2026):
    last = st[st['ChangeDate'] <= f'{y}-12-31'].groupby(['Symbol', 'PledgorID']).tail(1)
    rows.append(last.assign(year=y)[['Symbol', 'PledgorID', 'name', 'year', 'balance', 'NumHolderOwn', 'TotNumShares']])
ye = pd.concat(rows, ignore_index=True)
ye = ye[ye['balance'] != 0]
ye.to_csv(os.path.join(der, 'pledgor_yearend_stat.csv'), index=False, encoding='utf-8-sig')

rep = [
    f'统计表：{len(st)} 条记录，{st.Symbol.nunique()} 家公司，{st.groupby(["Symbol", "PledgorID"]).ngroups} 个公司—出质方',
    f'全部解押归零 {len(resid)} 次；归零前残差为 0 的占 {(np.abs(resid) < 1).mean():.3f}，残差为正（漏记解押或股本变动）{(resid > 1).mean():.3f}，为负 {(resid < -1).mean():.3f}',
    f'出现负余额的记录 {(st.balance < -1).sum()} 条',
    f'年末非零余额的出质方—年度 {len(ye)} 个',
]
open(os.path.join(der, '质押统计表核查报告.txt'), 'w', encoding='utf-8').write('\n'.join(rep))
print('\n'.join(rep))
