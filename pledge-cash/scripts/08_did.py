"""5.5 2018年股票质押新规：第一阶段（表5-11）、主回归（表5-12）、事件研究（图5-1）、趋势检验与安慰剂（图5-2）。

用法：python -I 08_did.py <派生目录> [置换次数，默认2000]
PledgePre 用全部 2016—2017 年公司—年度（含不在回归样本中的年度，如 ST 年度）计算；
描述统计、二值处理组的中位数与置换检验的抽样池均限于 DID 估计样本中的公司。
"""
import sys, os, json
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sample import CTRL
from reg_common import fit, cell, stats, pval

der = sys.argv[1]
NPERM = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
C = '+'.join(CTRL)
raw = pd.read_pickle(os.path.join(der, 'panel_raw.pkl'))
raw['Pl'] = raw['Pledge_raw'].clip(0, 1)
s = pd.read_pickle(os.path.join(der, 'sample.pkl'))
pr = pd.read_csv(os.path.join(der, 'pressure.csv'), dtype={'Stkcd': str})
s = s.merge(pr[['Stkcd', 'year', 'Pressure']], on=['Stkcd', 'year'], how='left')
s['Pressure'] = s['Pressure'].fillna(0.0)
s['indyear'] = s['Ind'].astype(str) + '_' + s['year'].astype(str)
s['provyear'] = s['PROVINCE'].astype(str) + '_' + s['year'].astype(str)

def pre_intensity(y0, y1, list_before):
    r = raw[raw.year.between(y0, y1) & raw.Pl.notna() & (raw.Listdt < list_before)]
    return r.groupby('Stkcd')['Pl'].mean()

def did_sample(pre, post_year, years=None):
    d = s[s.Stkcd.isin(pre.index)].copy()
    if years:
        d = d[d.year.between(*years)]
    d['PledgePre'] = d['Stkcd'].map(pre)
    d['Post'] = (d.year >= post_year).astype(float)
    d['DID'] = d['PledgePre'] * d['Post']
    return d

out = {}
pre_all = pre_intensity(2016, 2017, pd.Timestamp('2016-01-01'))
d = did_sample(pre_all, 2018)
pre = pre_all[pre_all.index.isin(d.Stkcd.unique())]
med = pre.median()
d['Treat'] = (d['PledgePre'] > med).astype(float)
d['TDID'] = d['Treat'] * d['Post']
r1617 = raw[raw.year.between(2016, 2017) & raw.Pl.notna() & raw.Stkcd.isin(pre.index)]
in_s = set(zip(s.Stkcd, s.year))
out['did_sample'] = {'N': len(d), 'firms': int(d.Stkcd.nunique()), 'PledgePre_mean': float(pre.mean()),
                     'PledgePre_median': float(med), 'share_pos': float((pre > 0).mean()),
                     'firms_pre_all': int(len(pre_all)),
                     'intensity_obs': int(len(r1617)),
                     'intensity_obs_outside_sample': int(sum((a, b) not in in_s for a, b in zip(r1617.Stkcd, r1617.year)))}
print(out['did_sample'])

# ---- 第一阶段 ----
fs = []
for y in ['Pledge', 'Pressure', 'OREC']:
    m = fit(f'{y} ~ DID + {C} | Stkcd + year', d.dropna(subset=[y]))
    fs.append({'y': y, 'DID': cell(m, 'DID'), 'r2': stats(m)[0], 'N': stats(m)[1]})
out['t5_11'] = fs
# 均值回归基准：窗口结构对齐的真实队列与安慰剂队列
def fs_pledge(y0, y1, post, win):
    pp = pre_intensity(y0, y1, pd.Timestamp(f'{y0}-01-01'))
    dd = did_sample(pp, post, win)
    m = fit(f'Pledge ~ DID + {C} | Stkcd + year', dd)
    return {'window': f'{win[0]}—{win[1]}', 'DID': cell(m, 'DID'), 'N': stats(m)[1], 'r2': stats(m)[0]}
out['mean_reversion'] = {
    'short': {'main': fs_pledge(2016, 2017, 2018, (2016, 2021)), 'placebo': fs_pledge(2012, 2013, 2014, (2012, 2017))},
    'medium': {'main': fs_pledge(2016, 2017, 2018, (2012, 2021)), 'placebo': fs_pledge(2012, 2013, 2014, (2008, 2017))},
}
print(fs, out['mean_reversion'])

# ---- 主回归 ----
specs = [('DID', 'Stkcd + year', d), ('DID', 'Stkcd + indyear', d), ('DID', 'Stkcd + indyear + provyear', d),
         ('DID', 'Stkcd + indyear + provyear', d[d.year != 2018]), ('TDID', 'Stkcd + indyear + provyear', d)]
main = []
for v, fe, dd in specs:
    m = fit(f'Cash ~ {v} + {C} | {fe}', dd)
    main.append({'var': v, 'coef': cell(m, v), 'r2': stats(m)[0], 'N': stats(m)[1], 'p': pval(m, v)})
out['main_nocontrols'] = cell(fit('Cash ~ DID | Stkcd + year', d), 'DID')
out['t5_12'] = main
print(main, out['main_nocontrols'])

# ---- 事件研究（基期 2017）----
def event(dd):
    yrs = [y for y in sorted(dd.year.unique()) if y != 2017]
    for y in yrs:
        dd[f'E{y}'] = dd['PledgePre'] * (dd.year == y)
    m = fit('Cash ~ ' + '+'.join(f'E{y}' for y in yrs) + f' + {C} | Stkcd + year', dd)
    return m, yrs
m, yrs = event(d.copy())
t = m.tidy()
es = [{'year': int(y), 'b': float(t.loc[f'E{y}', 'Estimate']), 'lo': float(t.loc[f'E{y}', '2.5%']),
       'hi': float(t.loc[f'E{y}', '97.5%']), 'p': float(t.loc[f'E{y}', 'Pr(>|t|)'])} for y in yrs]
es.append({'year': 2017, 'b': 0.0, 'lo': 0.0, 'hi': 0.0, 'p': 1.0})
out['event'] = sorted(es, key=lambda r: r['year'])
out['event_pre_sig05'] = [r['year'] for r in es if r['year'] <= 2016 and r['p'] < 0.05]
names = list(m.coef().index)
def wald(R):
    idx = [names.index(r) for r in R]
    b = m.coef().values[idx]; V = m._vcov[np.ix_(idx, idx)]
    W = float(b @ np.linalg.solve(V, b))
    from scipy import stats as sst
    return {'statistic': W, 'df': len(idx), 'pvalue': float(1 - sst.chi2.cdf(W, len(idx)))}
out['event_pre_wald'] = wald([f'E{y}' for y in yrs if y <= 2015])
out['event_pre_wald_2016'] = wald([f'E{y}' for y in yrs if y <= 2016])
# 全样本事件研究中政策前系数（2007—2017，θ2017=0）的线性斜率
py = [y for y in yrs if y <= 2016]
xs = np.array(py + [2017], float); w = (xs - xs.mean()) / ((xs - xs.mean()) ** 2).sum()
idx = [names.index(f'E{y}') for y in py]
slope = float(w[:-1] @ m.coef().values[idx]); se = float(np.sqrt(w[:-1] @ m._vcov[np.ix_(idx, idx)] @ w[:-1]))
from scipy import stats as sst
out['event_pre_slope'] = {'slope': slope, 'se': se, 'p': float(2 * (1 - sst.norm.cdf(abs(slope / se))))}
# 仅用政策前样本（≤2017）的事件研究
mpre, ypre = event(d[d.year <= 2017].copy())
tp_ = mpre.tidy()
out['event_preonly'] = [{'year': int(y), 'b': float(tp_.loc[f'E{y}', 'Estimate']), 'p': float(tp_.loc[f'E{y}', 'Pr(>|t|)'])} for y in ypre]
print(out['event_pre_wald'], out['event_pre_wald_2016'], out['event_pre_slope'])

# ---- 线性趋势 ----
d['PreTrend'] = d['PledgePre'] * (d['year'] - 2017)
tr = []
for fe in ['Stkcd + year', 'Stkcd + indyear + provyear']:
    mt = fit(f'Cash ~ DID + PreTrend + {C} | {fe}', d)
    tr.append({'fe': fe, 'DID': cell(mt, 'DID'), 'PreTrend': cell(mt, 'PreTrend'), 'N': stats(mt)[1]})
out['trend_adj'] = tr
mt = fit(f'Cash ~ PreTrend + {C} | Stkcd + year', d[d.year <= 2017])   # 仅用政策前样本估计的线性趋势
out['pre_only_trend'] = cell(mt, 'PreTrend'); out['pre_only_trend_p'] = pval(mt, 'PreTrend')
print('trend', tr, out['pre_only_trend'], out['pre_only_trend_p'])

# ---- 安慰剂：虚构政策时点 ----
fake = []
for fy in (2014, 2015):
    pf_ = pre_intensity(fy - 2, fy - 1, pd.Timestamp(f'{fy - 2}-01-01'))
    m2 = fit(f'Cash ~ DID + {C} | Stkcd + year', did_sample(pf_, fy, (2007, 2017)))
    fake.append({'fake_year': fy, 'coef': cell(m2, 'DID'), 'N': stats(m2)[1]})
out['placebo_fake'] = fake
print(fake)

# ---- 安慰剂：在估计样本公司内随机置换处理强度 ----
true_b = float(fit(f'Cash ~ DID + {C} | Stkcd + year', d).coef()['DID'])
rng = np.random.default_rng(20261007)
firms, vals = pre.index.to_numpy(), pre.to_numpy()
perm = []
for k in range(NPERM):
    mp = dict(zip(firms, rng.permutation(vals)))
    perm.append(float(fit(f'Cash ~ DID + {C} | Stkcd + year', d.assign(DID=d['Stkcd'].map(mp) * d['Post'])).coef()['DID']))
perm = np.array(perm)
k = int((np.abs(perm) >= abs(true_b)).sum())
out['placebo_perm'] = {'true': true_b, 'n': NPERM, 'mean': float(perm.mean()), 'sd': float(perm.std()),
                       'k_abs_ge_true': k, 'p_two_sided': (k + 1) / (NPERM + 1), 'pctile_true': float((perm < true_b).mean())}
np.save(os.path.join(der, 'perm.npy'), perm)
print(out['placebo_perm'])
json.dump(out, open(os.path.join(der, 'res_did.json'), 'w'), ensure_ascii=False, indent=1)
