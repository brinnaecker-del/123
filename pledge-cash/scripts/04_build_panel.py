"""构造“公司—年度”研究面板（口径按开题报告表2、表3）。

用法：python -I 04_build_panel.py <CSMAR输入目录> <派生目录>
依赖：01 输出 top1_panel.csv、03 输出 pledgor_yearend_stat.csv。
只做计算，不做插补；缺失即缺失。缩尾在回归脚本中进行，本文件保存未缩尾值。
"""
import sys, os, re
import numpy as np
import pandas as pd

src, der = sys.argv[1], sys.argv[2]
rd = lambda f, **k: pd.read_excel(os.path.join(src, f), header=0, skiprows=[1, 2], **k)

def norm(s):
    s = str(s).strip().replace('（', '(').replace('）', ')')
    return re.sub(r'\s+', '', s)

# ---------- 财务 ----------
bas = rd('FS_Combas.xlsx', dtype={'Stkcd': str})
ins = rd('FS_Comins.xlsx', dtype={'Stkcd': str})
cfs = rd('FS_Comscfd.xlsx', dtype={'Stkcd': str})
fs = (bas.merge(ins.drop(columns=['ShortName', 'Typrep']), on=['Stkcd', 'Accper'], how='left')
         .merge(cfs.drop(columns=['ShortName', 'Typrep']), on=['Stkcd', 'Accper'], how='left'))
fs = fs[fs['Typrep'] == 'A'].copy()
fs['year'] = fs['Accper'].str[:4].astype(int)
fs = fs.rename(columns={'A001101000': 'cash_amt', 'A001121000': 'oth_rec', 'A001100000': 'cur_assets',
                        'A001000000': 'ta', 'A002120000': 'oth_pay', 'A002100000': 'cur_liab',
                        'A002000000': 'tl', 'B001100000': 'rev', 'B002000000': 'ni',
                        'C001000000': 'cfo', 'C002006000': 'capex_amt', 'ShortName': 'FSName'})
fs = fs.sort_values(['Stkcd', 'year'])

# ---------- 公司文件、股权性质 ----------
co = rd('TRD_Co.xlsx', dtype=str)
co['Listdt'] = pd.to_datetime(co['Listdt'], errors='coerce')
co['ListYear'] = co['Listdt'].dt.year
en = rd('EN_EquityNatureAll.xlsx', dtype={'Symbol': str})
en['year'] = pd.to_datetime(en['EndDate']).dt.year
en = en.sort_values('EndDate').groupby(['Symbol', 'year']).tail(1)
en = en.rename(columns={'Symbol': 'Stkcd'})[['Stkcd', 'year', 'EquityNature']]

# ---------- 市值（当年最后一个有交易的月份）与年度回报 ----------
mn = pd.read_csv(os.path.join(src, 'TRD_Mnth.csv'), dtype={'Stkcd': str})
mn['year'] = mn['Trdmnt'].str[:4].astype(int)
mv = mn.sort_values('Trdmnt').groupby(['Stkcd', 'year']).tail(1)[['Stkcd', 'year', 'Msmvttl', 'Trdmnt']]
mv['mv'] = mv['Msmvttl'] * 1000.0  # 单位：千元 → 元
ret = (mn.assign(g=1 + mn['Mretwd']).groupby(['Stkcd', 'year'])
         .agg(Ret=('g', lambda s: s.prod() - 1), nmonth=('g', 'size')).reset_index())

# ---------- 第一大股东与质押（统计表口径） ----------
top1 = pd.read_csv(os.path.join(der, 'top1_panel.csv'), dtype={'Stkcd': str})
top1['name'] = top1['Top1Name'].map(norm)
ye = pd.read_csv(os.path.join(der, 'pledgor_yearend_stat.csv'), dtype={'Symbol': str, 'PledgorID': str})
st = pd.read_excel(os.path.join(src, 'PLED_TRDSTAT.xlsx'), header=0, skiprows=[1, 2],
                   dtype={'Symbol': str, 'PledgorID': str})
# 同一出质方ID在不同时期可能使用不同名称：任一名称与第一大股东名称相同即视为匹配
names = st.assign(name=st['Pledgor'].map(norm))[['Symbol', 'PledgorID', 'name']].drop_duplicates()
cand = ye[['Symbol', 'PledgorID', 'year', 'balance', 'TotNumShares']].merge(names, on=['Symbol', 'PledgorID'])
cand = cand.rename(columns={'Symbol': 'Stkcd'})
mt = top1[['Stkcd', 'year', 'name']].merge(cand, on=['Stkcd', 'year', 'name'])
mt = mt.drop_duplicates(['Stkcd', 'year', 'PledgorID'])
pl = mt.groupby(['Stkcd', 'year']).agg(pledged=('balance', 'sum'), totshares_pl=('TotNumShares', 'last')).reset_index()
p = top1.merge(pl, on=['Stkcd', 'year'], how='left')
p['pledged'] = p['pledged'].fillna(0.0)
p['Pledge_raw'] = p['pledged'] / p['Top1Shares']

# 明细表口径（稳健性）
det = pd.read_csv(os.path.join(der, 'pledgor_yearend_balance.csv'), dtype={'Stkcd': str})
det = det.groupby(['Stkcd', 'name', 'year'], as_index=False)['pledged'].sum().rename(columns={'pledged': 'pledged_det'})
p = p.merge(det, on=['Stkcd', 'name', 'year'], how='left')
p['pledged_det'] = p['pledged_det'].fillna(0.0)
p['Pledge_det_raw'] = p['pledged_det'] / p['Top1Shares']

# ---------- 合并 ----------
df = fs.merge(p.drop(columns=['Nnindcd', 'Nnindnme', 'PROVINCE', 'Listdt', 'ListYear'], errors='ignore'),
              on=['Stkcd', 'year'], how='left')
df = df.merge(co[['Stkcd', 'Listdt', 'ListYear', 'Nnindcd', 'Nnindnme', 'PROVINCE']], on='Stkcd', how='left')
df = df.merge(en, on=['Stkcd', 'year'], how='left').merge(mv[['Stkcd', 'year', 'mv']], on=['Stkcd', 'year'], how='left')
df = df.merge(ret, on=['Stkcd', 'year'], how='left')

# ---------- 变量 ----------
df['Cash'] = df['cash_amt'] / (df['ta'] - df['cash_amt'])
df['Size'] = np.log(df['ta'])
df['Lev'] = df['tl'] / df['ta']
df['ROA'] = df['ni'] / df['ta']
g = df.groupby('Stkcd')
lag = lambda c: g[c].shift(1).where(g['year'].shift(1) == df['year'] - 1)
df['Growth'] = df['rev'] / lag('rev') - 1
df['TobinQ'] = (df['mv'] + df['tl']) / df['ta']
df['CF'] = df['cfo'] / df['ta']
cf1, cf2 = lag('CF'), g['CF'].shift(2).where(g['year'].shift(2) == df['year'] - 2)
df['CFVol'] = pd.concat([df['CF'], cf1, cf2], axis=1).std(axis=1, ddof=1).where(cf1.notna() & cf2.notna())
df['NWC'] = (df['cur_assets'] - df['cur_liab'] - df['cash_amt']) / df['ta']
df['ListAge'] = df['year'] - df['ListYear']                  # 上市年数（上市当年=0）
df['Age'] = np.log(df['ListAge'] + 1)
df['Top1'] = df['Top1Pct'] / 100.0
df['SOE'] = (df['EquityNature'] == '国企').astype(float).where(df['EquityNature'].notna())
df['Capex'] = df['capex_amt'] / df['ta']
df['OREC_raw'] = (df['oth_rec'] - df['oth_pay']) / df['ta']
df['Pledge_Dum'] = (df['pledged'] > 0).astype(float).where(df['Top1Shares'].notna())
df['Pledge_Ratio2'] = df['pledged'] / df['totshares_pl']
df.loc[df['pledged'] == 0, 'Pledge_Ratio2'] = 0.0
# SA：Size 为总资产（百万元）对数，上限 370 亿元；Age 为上市年数，上限 37 年（开题报告表3）
size_m = np.log(np.minimum(df['ta'] / 1e6, 37000.0))
age_c = np.minimum(df['ListAge'].clip(lower=0), 37)
df['SA'] = -0.737 * size_m + 0.043 * size_m ** 2 - 0.040 * age_c
# 行业：制造业取二级代码，其余取门类
df['Ind'] = np.where(df['Nnindcd'].str[0] == 'C', df['Nnindcd'].str[:3], df['Nnindcd'].str[0])

# ---------- 样本筛选标记 ----------
df['is_ST'] = df['FSName'].str.contains('ST', na=False)
df['is_fin'] = df['Nnindcd'].str[0] == 'J'
df['is_Ashare_SZSH'] = df['Stkcd'].str[:2].isin(['00', '30', '60', '68'])
df['insolvent'] = df['tl'] > df['ta']
df.to_pickle(os.path.join(der, 'panel_raw.pkl'))
print('面板行数', len(df), '公司', df.Stkcd.nunique(), '年份', df.year.min(), df.year.max())
