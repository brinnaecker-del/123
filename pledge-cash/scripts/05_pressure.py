"""平仓压力 Pressure 与市场驱动口径 Pressure_Mkt（续写稿式 5-1）。

用法：python -I 05_pressure.py <CSMAR输入目录> <派生目录>
规则（均在正文中说明）：
- 对象：第一大股东（按名称与十大股东文件匹配）在 t 年末仍未解押的每一笔质押（明细表，取 t 年末前最后一条记录的剩余数量>0）；
- 剔除可能漏记解押的记录：合同结束日早于 t 年末的；无结束日且起始日早于 t 年末 3 年以上的；
- 价格路径：P(m)/P0 = [CI(m)/CI(m_s)]×[月收盘价(m_s)/起始日收盘价]，CI 为考虑现金红利再投资的月回报累乘指数，m_s 为起始月；
- 预警条件：P(m)/P0 < 0.40×1.60×(1+0.10τ)，τ 为起始日至 m 月末的年数；t 年内任一月末满足即为触及；
- Pressure = 触及预警线的质押股数 / 第一大股东全部（保留的）未解押质押股数；无质押为 0；
- Pressure_Mkt：以沪深A股总市值加权（权重为上月总市值）的月回报构造市场指数，替代个股路径。
"""
import sys, os, re, glob
import numpy as np
import pandas as pd

src, der = sys.argv[1], sys.argv[2]

def norm(s):
    s = str(s).strip().replace('（', '(').replace('）', ')')
    return re.sub(r'\s+', '', s)

# ---- 明细表 ----
cache = os.path.join(der, 'pled_detail_all.pkl')
if os.path.exists(cache):
    d = pd.read_pickle(cache)
else:
    parts = sorted(glob.glob(os.path.join(src, '*PLED_TRDDETL*.xlsx')))
    head = pd.read_excel(parts[0], header=0, skiprows=[1, 2], dtype=str)
    frames = [head]
    for f in parts[1:]:
        x = pd.read_excel(f, header=None, dtype=str).dropna(how='all')
        x.columns = head.columns
        frames.append(x)
    d = pd.concat(frames, ignore_index=True).drop_duplicates()
    for c in ['EventSeq', 'NumAfterChg', 'ClosePrice']:
        d[c] = pd.to_numeric(d[c], errors='coerce')
    for c in ['ChangeDate', 'StartDate', 'EndDate']:
        d[c] = pd.to_datetime(d[c], errors='coerce')
    d['name'] = d['Pledgor'].map(norm)
    d.to_pickle(cache)
d = d.sort_values(['EventID', 'ChangeDate', 'EventSeq'])
first = d.groupby('EventID').head(1).set_index('EventID')
ev = pd.DataFrame({'Stkcd': first['Symbol'], 'name': first['name'], 'start': first['StartDate'],
                   'P0': first['ClosePrice']})
ev['end'] = d.dropna(subset=['EndDate']).groupby('EventID')['EndDate'].last()

top1 = pd.read_csv(os.path.join(der, 'top1_panel.csv'), dtype={'Stkcd': str})
top1['name'] = top1['Top1Name'].map(norm)
keys = set(zip(top1.Stkcd, top1.name, top1.year))

rows = []
for y in range(2006, 2026):
    cut = pd.Timestamp(f'{y}-12-31')
    last = d[d['ChangeDate'] <= cut].groupby('EventID').tail(1)
    last = last[last['NumAfterChg'] > 0][['EventID', 'NumAfterChg']].set_index('EventID').join(ev)
    keep = ~((last['end'].notna() & (last['end'] < cut)) |
             (last['end'].isna() & (last['start'] < cut - pd.DateOffset(years=3))))
    last = last[keep & last['start'].notna() & (last['P0'] > 0)]
    last['year'] = y
    m = [(a, b, y) in keys for a, b in zip(last.Stkcd, last.name)]
    rows.append(last[m].reset_index())
ey = pd.concat(rows, ignore_index=True)

# ---- 月度价格与指数 ----
mn = pd.read_csv(os.path.join(src, 'TRD_Mnth.csv'), dtype={'Stkcd': str})
mn['r'] = mn['Mretwd'].fillna(0.0)
mn['mdate'] = pd.to_datetime(mn['Trdmnt']) + pd.offsets.MonthEnd(0)
mn = mn.sort_values(['Stkcd', 'mdate'])
mn['CI'] = mn.groupby('Stkcd')['r'].transform(lambda s: (1 + s).cumprod())
a = mn[mn['Stkcd'].str[:2].isin(['00', '30', '60', '68'])].copy()
a['w'] = a.groupby('Stkcd')['Msmvttl'].shift(1)
a = a.dropna(subset=['w', 'Mretwd'])
mk = a.groupby('mdate').apply(lambda g: np.average(g['Mretwd'], weights=g['w'])).rename('rm').reset_index()
mk['MI'] = (1 + mk['rm']).cumprod()

# 起始月基期：起始日所在月（若该月停牌则取此前最近一个有数据的月份）
ey['ms'] = ey['start'] + pd.offsets.MonthEnd(0)
base = pd.merge_asof(ey.sort_values('ms'), mn[['Stkcd', 'mdate', 'CI', 'Mclsprc']].sort_values('mdate'),
                     left_on='ms', right_on='mdate', by='Stkcd', direction='backward')
base = base.rename(columns={'CI': 'CI0', 'Mclsprc': 'Pm0'}).drop(columns='mdate')
base = pd.merge_asof(base.sort_values('ms'), mk[['mdate', 'MI']].sort_values('mdate'),
                     left_on='ms', right_on='mdate', direction='backward').rename(columns={'MI': 'MI0'}).drop(columns='mdate')

# t 年内各月末
mm = mn[['Stkcd', 'mdate', 'CI']].copy(); mm['year'] = mm['mdate'].dt.year
x = base.merge(mm, on=['Stkcd', 'year'])
x = x[x['mdate'] >= x['ms']].merge(mk[['mdate', 'MI']], on='mdate', how='left')
x['tau'] = (x['mdate'] - x['start']).dt.days / 365.25
x['thr'] = 0.64 * (1 + 0.10 * x['tau'])
x['rel'] = x['CI'] / x['CI0'] * x['Pm0'] / x['P0']
x['rel_m'] = x['MI'] / x['MI0']
hit = x.assign(h=x['rel'] < x['thr'], hm=x['rel_m'] < x['thr']).groupby(['EventID', 'year'])[['h', 'hm']].any().reset_index()
ey = ey.merge(hit, on=['EventID', 'year'], how='left')
ey[['h', 'hm']] = ey[['h', 'hm']].fillna(False)
ey['sh'] = ey['NumAfterChg']
agg = ey.groupby(['Stkcd', 'year']).apply(lambda g: pd.Series({
    'Pressure': (g['sh'] * g['h']).sum() / g['sh'].sum(),
    'Pressure_Mkt': (g['sh'] * g['hm']).sum() / g['sh'].sum(),
    'n_events': len(g), 'pledged_kept': g['sh'].sum()})).reset_index()
agg.to_csv(os.path.join(der, 'pressure.csv'), index=False, encoding='utf-8-sig')
mk.to_csv(os.path.join(der, 'market_index.csv'), index=False)
print('事件—年度', len(ey), '公司—年度', len(agg))
print('Pressure>0 的公司—年度占有质押者比例', round((agg.Pressure > 0).mean(), 3), '；Pressure_Mkt>0', round((agg.Pressure_Mkt > 0).mean(), 3))
print(agg.groupby('year')[['Pressure', 'Pressure_Mkt']].mean().round(3).to_string())
