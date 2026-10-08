"""构造“公司—年度”研究面板（口径按开题报告表2、表3）。

用法：python -I 04_build_panel.py <CSMAR输入目录> <派生目录>
依赖：01 输出 top1_panel.csv、02 输出 detail_event_*.pkl、03 输出 pledgor_yearend_stat.csv。
主口径与开题报告一致；带 _alt 后缀的为核查后提出的改进口径，仅用于稳健性检验。
只做计算，不做插补；缺失即缺失。缩尾在回归脚本中进行，本文件保存未缩尾值。
"""
import sys, os
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from names import norm_basic
from matching import match_stat, match_events

src, der = sys.argv[1], sys.argv[2]
rd = lambda f, **k: pd.read_excel(os.path.join(src, f), header=0, skiprows=[1, 2], **k)

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
mv = mn.sort_values('Trdmnt').groupby(['Stkcd', 'year']).tail(1)[['Stkcd', 'year', 'Msmvttl', 'Mclsprc', 'Trdmnt']]
mv['mv'] = mv['Msmvttl'] * 1000.0  # 单位：千元 → 元；该代码（A股）的总市值
ret = (mn.assign(g=1 + mn['Mretwd']).groupby(['Stkcd', 'year'])
         .agg(Ret=('g', lambda s: s.prod(min_count=1) - 1), nmonth=('g', 'size')).reset_index())  # 全年无有效回报 → 缺失

# ---------- 第一大股东与质押（统计表口径） ----------
top1 = pd.read_csv(os.path.join(der, 'top1_panel.csv'), dtype={'Stkcd': str})
top1['name'] = top1['Top1Name'].map(norm_basic)
ye = pd.read_csv(os.path.join(der, 'pledgor_yearend_stat.csv'), dtype={'Symbol': str, 'PledgorID': str}, parse_dates=['last_date'])
st = pd.read_excel(os.path.join(src, 'PLED_TRDSTAT.xlsx'), header=0, skiprows=[1, 2], dtype={'Symbol': str, 'PledgorID': str})
yk = ye.rename(columns={'Symbol': 'Stkcd'})

# 主口径（与开题报告一致）：排名第1股东；同一出质方ID的任一历史名称与其名称（基本口径）相同即匹配
mm = match_stat(top1, ye, st, loose=False)
mm.to_csv(os.path.join(der, 'matched_ids_main.csv'), index=False)
mt = mm.merge(yk[['Stkcd', 'PledgorID', 'year', 'balance', 'last_date', 'TotNumShares']], on=['Stkcd', 'year', 'PledgorID'])
pos = mt[mt['balance'] > 0]
pl = mt.groupby(['Stkcd', 'year']).agg(pledged=('balance', 'sum'), totshares_pl=('TotNumShares', 'last')).reset_index()
newest = pos.groupby(['Stkcd', 'year'])['last_date'].max().rename('pl_last_date').reset_index()
p = top1.merge(pl, on=['Stkcd', 'year'], how='left').merge(newest, on=['Stkcd', 'year'], how='left')
p['pledged'] = p['pledged'].fillna(0.0)
p['Pledge_raw'] = p['pledged'] / p['Top1Shares']
# 陈旧余额：有正余额，但所有正余额出质方的最后一条记录都早于年末 3 年以上
p['pl_age'] = (pd.to_datetime(p['year'].astype(str) + '-12-31') - p['pl_last_date']).dt.days / 365.25
p['Pledge_stale'] = ((p['pledged'] > 0) & (p['pl_age'] > 3)).astype(float)

# 改进口径（稳健性）：仅全部解押时归零；非名义持有人为第一大股东；基本口径无匹配时用宽松口径；剔除重复出质方ID
dup = pd.read_csv(os.path.join(der, 'pledgor_duplicate_ids.csv'), dtype=str)
dupk = set(zip(dup.get('Symbol', []), dup.get('PledgorID', [])))
ye_a = ye[[(a, b) not in dupk for a, b in zip(ye.Symbol, ye.PledgorID)]]
t_a = top1[['Stkcd', 'year', 'Top1Name_nn', 'Top1Shares_nn']].rename(columns={'Top1Name_nn': 'Top1Name'}).dropna(subset=['Top1Name'])
ma = match_stat(t_a, ye_a, st, loose=True)
ma.to_csv(os.path.join(der, 'matched_ids_alt.csv'), index=False)
mta = ma.merge(ye_a.rename(columns={'Symbol': 'Stkcd'})[['Stkcd', 'PledgorID', 'year', 'balance_alt']], on=['Stkcd', 'year', 'PledgorID'])
pla = mta.groupby(['Stkcd', 'year'])['balance_alt'].sum().rename('pledged_alt').reset_index()
p = p.merge(pla, on=['Stkcd', 'year'], how='left')
p['pledged_alt'] = p['pledged_alt'].fillna(0.0)
p['Pledge_alt_raw'] = p['pledged_alt'] / p['Top1Shares_nn']

# 明细表口径（稳健性）：与第一大股东匹配的明细事件（出质方ID属于主口径已匹配ID，或任一记录名称相同）年末剩余数量之和
info = pd.read_pickle(os.path.join(der, 'detail_event_info.pkl'))
dey = pd.read_pickle(os.path.join(der, 'detail_event_year.pkl'))
evm = match_events(dey, info, top1, mm)
det = evm.groupby(['Stkcd', 'year'])['bal'].sum().rename('pledged_det').reset_index()
p = p.merge(det, on=['Stkcd', 'year'], how='left')
p['pledged_det'] = p['pledged_det'].fillna(0.0)
p['Pledge_det_raw'] = p['pledged_det'] / p['Top1Shares']

# ---------- 合并 ----------
df = fs.merge(p.drop(columns=['Nnindcd', 'Nnindnme', 'PROVINCE', 'Listdt', 'ListYear'], errors='ignore'),
              on=['Stkcd', 'year'], how='left')
df = df.merge(co[['Stkcd', 'Listdt', 'ListYear', 'Nnindcd', 'Nnindnme', 'PROVINCE']], on='Stkcd', how='left')
df = df.merge(en, on=['Stkcd', 'year'], how='left').merge(mv[['Stkcd', 'year', 'mv', 'Mclsprc']], on=['Stkcd', 'year'], how='left')
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
# 改进口径：证券代码变更的公司取原代码上市年份（001872←000022，001914←000043，601607←600849，302132←300114）
CODE_CHG = {'001872': '000022', '001914': '000043', '601607': '600849', '302132': '300114'}
ly = co.set_index('Stkcd')['ListYear']
df['ListYear_alt'] = [ly.get(CODE_CHG[c], y) if c in CODE_CHG else y for c, y in zip(df['Stkcd'], df['ListYear'])]
df['Age_alt'] = np.log((df['year'] - df['ListYear_alt']).clip(lower=0) + 1)
df['Top1'] = df['Top1Pct'] / 100.0
df['SOE'] = (df['EquityNature'] == '国企').astype(float).where(df['EquityNature'].notna())
df['Capex'] = df['capex_amt'] / df['ta']
df['OREC_raw'] = (df['oth_rec'] - df['oth_pay']) / df['ta']
df['Pledge_Dum'] = (df['pledged'] > 0).astype(float).where(df['Top1Shares'].notna())
# 总股本：优先取统计表“上市公司总股份”，否则由第一大股东持股数与持股比例推算
df['totshares'] = df['totshares_pl'].fillna(df['Top1Shares'] / (df['Top1Pct'] / 100.0))
# 占总股本的质押比例，以第一大股东自身持股为上限（与 Pledge 截取至[0,1]一致）
df['Pledge_Ratio2'] = np.minimum(df['pledged'].clip(lower=0), df['Top1Shares']) / df['totshares']
df.loc[df['pledged'] <= 0, 'Pledge_Ratio2'] = 0.0
# ---- 改进口径的其他变量（稳健性）----
# TobinQ：A+B、A+H 公司以 A 股价格计全部股本市值
a_sh = df['mv'] / df['Mclsprc']
scale = (a_sh / df['totshares']) < 0.97
df['mv_full'] = np.where(scale, df['Mclsprc'] * df['totshares'], df['mv'])
df['TobinQ_alt'] = (df['mv_full'] + df['tl']) / df['ta']
lagrev = lag('rev')
df['Growth_alt'] = (df['rev'] / lagrev - 1).where(lagrev > 0)
df['Top1_alt'] = df['Top1Pct_nn'] / 100.0
# SA：Size 为总资产（百万元）对数，上限 370 亿元；Age 为上市年数，上限 37 年（开题报告表3）
size_m = np.log(np.minimum(df['ta'] / 1e6, 37000.0))
age_c = np.minimum(df['ListAge'].clip(lower=0), 37)
df['SA'] = -0.737 * size_m + 0.043 * size_m ** 2 - 0.040 * age_c
# 行业（复现开题报告）：Ind 为证监会门类，用于行业×年度固定效应与行业年度均值；
# Ind7 为表7混合回归的行业虚拟变量：制造业按代码首位数字（C1—C4），其余为门类
df['Ind'] = df['Nnindcd'].str[0]
df['Ind7'] = np.where(df['Nnindcd'].str[0] == 'C', df['Nnindcd'].str[:2], df['Nnindcd'].str[0])

# ---------- 样本筛选标记 ----------
df['is_ST'] = df['FSName'].str.contains('ST', na=False)
df['is_fin'] = df['Nnindcd'].str[0] == 'J'
df['is_Ashare_SZSH'] = df['Stkcd'].str[:2].isin(['00', '30', '60', '68'])
df['insolvent'] = df['tl'] > df['ta']
df.to_pickle(os.path.join(der, 'panel_raw.pkl'))
print('面板行数', len(df), '公司', df.Stkcd.nunique(), '年份', df.year.min(), df.year.max())
