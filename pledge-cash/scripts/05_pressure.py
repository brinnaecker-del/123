"""平仓压力 Pressure 与市场驱动口径 Pressure_Mkt（续写稿式 5-1）。

用法：python -I 05_pressure.py <CSMAR输入目录> <派生目录>
依赖：02 输出 detail_event_*.pkl、pled_detail_all.pkl；04 输出 matched_ids_main.csv。
规则（均在正文中说明）：
- 对象：与第一大股东匹配的明细事件（出质方ID属于统计表已匹配ID，或事件任一记录的名称相同）在 t 年末剩余数量>0 的每一笔质押；
- 剔除可能漏记解押的记录：以事件全部记录中最新的结束日期（含展期、解押记录）早于 t 年末的；无结束日且起始日早于 t 年末 3 年以上的；
  另输出仅用 t 年末前已披露的结束日期判断的变体（*_asof）；
- 价格路径：P(m)/P0 = [CI(m)/CI(m_s)] × [月收盘价(m_s)/起始日收盘价] × AF，CI 为考虑现金红利再投资的月回报累乘指数，m_s 为起始月；
  AF 为起始月内的除权因子 (1+月回报)/(月收盘价/上月收盘价)：当 AF>1.05 且起始日价格属于除权前（更接近上月收盘价）时取 AF，否则取 1；
  起始月无交易（停牌）时，基期比值取 1（停牌期间价格不变）；
- 预警条件：P(m)/P0 < 0.40×1.60×(1+0.10τ)，τ 为起始日至 m 月末的年数；t 年内起始月及以后任一月末满足即为触及；
- Pressure = 触及预警线的质押股数 / 保留的未解押质押股数；
- Pressure_Mkt：以沪深A股总市值加权（权重为上月总市值）的月回报构造市场指数替代个股路径；月度数据下以起始月末为基期。
没有保留事件的公司—年度不出现在输出中（由回归脚本决定如何处理，见 06）。
"""
import sys, os
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from matching import match_events

src, der = sys.argv[1], sys.argv[2]
d = pd.read_pickle(os.path.join(der, 'pled_detail_all.pkl'))
info = pd.read_pickle(os.path.join(der, 'detail_event_info.pkl'))
dey = pd.read_pickle(os.path.join(der, 'detail_event_year.pkl'))
top1 = pd.read_csv(os.path.join(der, 'top1_panel.csv'), dtype={'Stkcd': str})
mm = pd.read_csv(os.path.join(der, 'matched_ids_main.csv'), dtype={'Stkcd': str, 'PledgorID': str})

ey = match_events(dey[dey.year >= 2006], info, top1, mm)
ey = ey.join(info[['start', 'P0', 'end_full']], on='EventID')
ey = ey[ey['start'].notna() & (ey['P0'] > 0)].copy()

# t 年末前已披露的最新结束日期
dd = d.dropna(subset=['EndDate'])
asof = []
for y in sorted(ey.year.unique()):
    cut = pd.Timestamp(f'{y}-12-31')
    e = dd[dd['ChangeDate'] <= cut].groupby('EventID')['EndDate'].last()
    asof.append(pd.DataFrame({'EventID': e.index, 'year': y, 'end_asof': e.to_numpy()}))
ey = ey.merge(pd.concat(asof), on=['EventID', 'year'], how='left')
cut = pd.to_datetime(ey['year'].astype(str) + '-12-31')
old = ey['start'] < cut - pd.DateOffset(years=3)
ey['keep'] = ~((ey['end_full'].notna() & (ey['end_full'] < cut)) | (ey['end_full'].isna() & old))
ey['keep_asof'] = ~((ey['end_asof'].notna() & (ey['end_asof'] < cut)) | (ey['end_asof'].isna() & old))

# ---- 月度价格与指数 ----
mn = pd.read_csv(os.path.join(src, 'TRD_Mnth.csv'), dtype={'Stkcd': str})
mn['r'] = mn['Mretwd'].fillna(0.0)
mn['mdate'] = pd.to_datetime(mn['Trdmnt']) + pd.offsets.MonthEnd(0)
mn = mn.sort_values(['Stkcd', 'mdate'])
mn['CI'] = mn.groupby('Stkcd')['r'].transform(lambda s: (1 + s).cumprod())
mn['Pprev'] = mn.groupby('Stkcd')['Mclsprc'].shift(1)
mn['AF'] = (1 + mn['Mretwd']) / (mn['Mclsprc'] / mn['Pprev'])
a = mn[mn['Stkcd'].str[:2].isin(['00', '30', '60', '68'])].copy()
a['w'] = a.groupby('Stkcd')['Msmvttl'].shift(1)
a = a.dropna(subset=['w', 'Mretwd'])
mk = a.groupby('mdate').apply(lambda g: np.average(g['Mretwd'], weights=g['w'])).rename('rm').reset_index()
mk['MI'] = (1 + mk['rm']).cumprod()

ey['ms'] = ey['start'] + pd.offsets.MonthEnd(0)
base = pd.merge_asof(ey.sort_values('ms'), mn[['Stkcd', 'mdate', 'CI', 'Mclsprc', 'Pprev', 'AF']].sort_values('mdate'),
                     left_on='ms', right_on='mdate', by='Stkcd', direction='backward')
base = base.rename(columns={'CI': 'CI0', 'Mclsprc': 'Pm0', 'mdate': 'mbase'})
same = base['mbase'] == base['ms']
preex = (np.abs(np.log(base['P0'] / base['Pprev'])) < np.abs(np.log(base['P0'] * base['AF'] / base['Pprev'])))
adj = np.where(same & (base['AF'] > 1.05) & preex, base['AF'], 1.0)
base['bratio'] = np.where(same, base['Pm0'] / base['P0'] * adj, 1.0)
base['split_adj'] = same & (base['AF'] > 1.05) & preex
base = pd.merge_asof(base.sort_values('ms'), mk[['mdate', 'MI']].sort_values('mdate'),
                     left_on='ms', right_on='mdate', direction='backward').rename(columns={'MI': 'MI0'}).drop(columns='mdate')

mmn = mn[['Stkcd', 'mdate', 'CI']].copy(); mmn['year'] = mmn['mdate'].dt.year
x = base[['EventID', 'Stkcd', 'year', 'start', 'ms', 'CI0', 'bratio', 'MI0']].merge(mmn, on=['Stkcd', 'year'])
x = x[x['mdate'] >= x['ms']].merge(mk[['mdate', 'MI']], on='mdate', how='left')
x['thr'] = 0.64 * (1 + 0.10 * (x['mdate'] - x['start']).dt.days / 365.25)
x['h'] = x['CI'] / x['CI0'] * x['bratio'] < x['thr']
x['hm'] = x['MI'] / x['MI0'] < x['thr']
hit = x.groupby(['EventID', 'year'])[['h', 'hm']].any().reset_index()
ey = ey.merge(hit, on=['EventID', 'year'], how='left').merge(base[['EventID', 'year', 'split_adj']], on=['EventID', 'year'], how='left')
ey[['h', 'hm']] = ey[['h', 'hm']].fillna(False)

def agg(e, suf):
    e = e.assign(sh=e['bal'], hs=e['bal'] * e['h'], hms=e['bal'] * e['hm'])
    g = e.groupby(['Stkcd', 'year'])[['sh', 'hs', 'hms']].sum()
    return pd.DataFrame({f'Pressure{suf}': g.hs / g.sh, f'Pressure_Mkt{suf}': g.hms / g.sh, f'n_events{suf}': e.groupby(['Stkcd', 'year']).size()})

out = agg(ey[ey.keep], '').join(agg(ey[ey.keep_asof], '_asof'), how='outer').reset_index()
out.to_csv(os.path.join(der, 'pressure.csv'), index=False, encoding='utf-8-sig')
mk.to_csv(os.path.join(der, 'market_index.csv'), index=False)
k = ey[ey.keep]
print('匹配的事件—年度', len(ey), '；保留（全部记录口径）', int(ey.keep.sum()), '；保留（年末已知口径）', int(ey.keep_asof.sum()))
print('按ID匹配', int(ey.by_id.sum()), '按名称匹配', int(ey.by_name.sum()), '；起始月送转调整的事件—年度', int(k.split_adj.fillna(False).sum()))
print('公司—年度', int(out.Pressure.notna().sum()), '；Pressure>0 占比', round((out.Pressure > 0).mean(), 3), '；Pressure_Mkt>0', round((out.Pressure_Mkt > 0).mean(), 3))
