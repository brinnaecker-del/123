"""由 CSMAR 股东股权质押统计表（PLED_TRDSTAT）推算出质方年末未解押质押股数（开题报告“第1步”的基准口径）。

用法：python -I 03_pledge_stat.py <输入目录> <派生目录>
规则：同一公司、同一出质方ID按变动日期累加“数量增减”。主口径仅在“全部解押”且“质押笔数”为空时归零；
开题报告口径（balance_rep，仅用于复现对照）在“质押笔数”为空时即归零。负余额与归零前的残差另行报告，不做插补。
取每年 12 月 31 日前最后一条记录的余额作为年末余额（不设时效；最后一条记录的日期另存为 last_date，供稳健性检验）。
同一公司下名称相同、变动记录被另一出质方ID完全包含的ID记入 pledgor_duplicate_ids.csv，主口径不剔除，改进口径剔除。
"""
import sys, os, re
import numpy as np
import pandas as pd

src, der = sys.argv[1], sys.argv[2]
st = pd.read_excel(os.path.join(src, 'PLED_TRDSTAT.xlsx'), header=0, skiprows=[1, 2],
                   dtype={'Symbol': str, 'PledgorID': str, 'ChangeReasonCode': str})
st['ChangeDate'] = pd.to_datetime(st['ChangeDate'])
st = st.reset_index().sort_values(['Symbol', 'PledgorID', 'ChangeDate', 'index'])

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from names import norm_basic
st['name'] = st['Pledgor'].map(norm_basic)

# 同一公司下，名称相同且变动记录（日期、数量）被另一出质方ID完全包含的ID，视为同一主体的重复记录（仅记录清单）
st['_rec'] = list(zip(st['ChangeDate'], st['ChangeNum']))
recs = st.groupby(['Symbol', 'PledgorID'])['_rec'].apply(set)
nm = st.groupby(['Symbol', 'PledgorID'])['name'].first()
drop_ids = []
for (sym, name), ids in nm.reset_index().groupby(['Symbol', 'name'])['PledgorID']:
    ids = list(ids)
    if len(ids) < 2:
        continue
    ids.sort(key=lambda i: -len(recs[(sym, i)]))
    for k, a in enumerate(ids):
        for b in ids[:k]:
            if (sym, b) not in drop_ids and recs[(sym, a)] <= recs[(sym, b)]:
                drop_ids.append((sym, a)); break
dup_ids = pd.DataFrame(drop_ids, columns=['Symbol', 'PledgorID'])
dup_ids.to_csv(os.path.join(der, 'pledgor_duplicate_ids.csv'), index=False)  # 主口径不剔除，改进口径在 04 中剔除
st = st.drop(columns='_rec')

def cumulate(reset):
    bal, resid = [], []
    for _, g in st.groupby(['Symbol', 'PledgorID'], sort=False):
        b = 0.0
        for chg, f in zip(g['ChangeNum'].to_numpy(float), reset.loc[g.index].to_numpy()):
            b += chg
            if f:
                resid.append(b)  # 归零前的累加残差，理想情况为 0
                b = 0.0
            bal.append(b)
    return pd.Series(bal, index=st.index), np.array(resid)

# 主口径：仅在“全部解押”且质押笔数为空时归零（转增、部分解押记录的质押笔数也为空，但质押并未解除，不应归零）
full = st['ChangeReason'].str.contains('全部解押') & (st['Pledtimes'].isna() | (st['Pledtimes'] == 0))
st['balance'], resid = cumulate(full)
# 开题报告口径（仅用于复现对照）：“质押笔数”为空即归零
st['balance_rep'], resid_rep = cumulate(st['Pledtimes'].isna() | (st['Pledtimes'] == 0))

rows = []
for y in range(2004, 2026):
    last = st[st['ChangeDate'] <= f'{y}-12-31'].groupby(['Symbol', 'PledgorID']).tail(1)
    rows.append(last.assign(year=y, last_date=last['ChangeDate'])[['Symbol', 'PledgorID', 'name', 'year', 'balance', 'balance_rep',
                                                                  'last_date', 'NumHolderOwn', 'TotNumShares']])
ye = pd.concat(rows, ignore_index=True)
ye = ye[(ye['balance'] != 0) | (ye['balance_rep'] != 0)]
ye.to_csv(os.path.join(der, 'pledgor_yearend_stat.csv'), index=False, encoding='utf-8-sig')

rep = [
    f'统计表：{len(st)} 条记录，{st.Symbol.nunique()} 家公司，{st.groupby(["Symbol", "PledgorID"]).ngroups} 个公司—出质方',
    f'主口径（仅全部解押归零）{len(resid)} 次；归零前残差为 0 的占 {(np.abs(resid) < 1).mean():.3f}，为正 {(resid > 1).mean():.3f}，为负 {(resid < -1).mean():.3f}',
    f'开题报告口径（笔数为空即归零）{len(resid_rep)} 次；残差为 0 的占 {(np.abs(resid_rep) < 1).mean():.3f}，为正 {(resid_rep > 1).mean():.3f}，为负 {(resid_rep < -1).mean():.3f}',
    f'出现负余额的记录 {(st.balance < -1).sum()} 条',
    f'名称相同且记录被另一ID完全包含、记为重复的出质方ID {len(dup_ids)} 个',
    f'年末非零余额的出质方—年度 {len(ye)} 个',
]
open(os.path.join(der, '质押统计表核查报告.txt'), 'w', encoding='utf-8').write('\n'.join(rep))
print('\n'.join(rep))
