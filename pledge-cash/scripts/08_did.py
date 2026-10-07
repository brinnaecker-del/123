"""5.5 2018年股票质押新规：第一阶段（表5-11）、主回归（表5-12）、事件研究（图5-1）、安慰剂（图5-2）。

用法：python -I 08_did.py <派生目录> [置换次数，默认500]
"""
import sys, os, json
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from sample import CTRL
from reg_common import fit, cell, stats

der = sys.argv[1]
NPERM = int(sys.argv[2]) if len(sys.argv) > 2 else 500
C = '+'.join(CTRL)
raw = pd.read_pickle(os.path.join(der, 'panel_raw.pkl'))
raw['Pl'] = raw['Pledge_raw'].clip(0, 1)
s = pd.read_pickle(os.path.join(der, 'sample.pkl'))
pr = pd.read_csv(os.path.join(der, 'pressure.csv'), dtype={'Stkcd': str})
s = s.merge(pr[['Stkcd', 'year', 'Pressure']], on=['Stkcd', 'year'], how='left')
s['Pressure'] = s['Pressure'].fillna(0.0)

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
pre = pre_intensity(2016, 2017, pd.Timestamp('2016-01-01'))
d = did_sample(pre, 2018)
med = pre.median()
d['Treat'] = (d['PledgePre'] > med).astype(float)
d['TDID'] = d['Treat'] * d['Post']
out['did_sample'] = {'N': len(d), 'firms': int(d.Stkcd.nunique()), 'PledgePre_mean': float(pre.mean()),
                     'PledgePre_median': float(med), 'share_pos': float((pre > 0).mean())}
print(out['did_sample'])

# ---- 第一阶段 ----
fs = []
for y in ['Pledge', 'Pressure', 'OREC']:
    dd = d.dropna(subset=[y])
    m = fit(f'{y} ~ DID + {C} | Stkcd + year', dd)
    fs.append({'y': y, 'DID': cell(m, 'DID'), 'r2': stats(m)[0], 'N': stats(m)[1]})
pre_p = pre_intensity(2012, 2013, pd.Timestamp('2012-01-01'))
dp = did_sample(pre_p, 2014, (2012, 2017))
m = fit(f'Pledge ~ DID + {C} | Stkcd + year', dp)
fs.insert(1, {'y': 'Pledge（安慰剂队列）', 'DID': cell(m, 'DID'), 'r2': stats(m)[0], 'N': stats(m)[1]})
out['t5_11'] = fs
print(fs)

# ---- 主回归 ----
d['indyear'] = d['Ind'].astype(str) + '_' + d['year'].astype(str)
d['provyear'] = d['PROVINCE'].astype(str) + '_' + d['year'].astype(str)
specs = [('DID', 'Stkcd + year', d), ('DID', 'Stkcd + indyear', d), ('DID', 'Stkcd + indyear + provyear', d),
         ('DID', 'Stkcd + indyear + provyear', d[d.year != 2018]), ('TDID', 'Stkcd + indyear + provyear', d)]
main = []
for v, fe, dd in specs:
    m = fit(f'Cash ~ {v} + {C} | {fe}', dd)
    main.append({'var': v, 'coef': cell(m, v), 'r2': stats(m)[0], 'N': stats(m)[1]})
m = fit('Cash ~ DID | Stkcd + year', d)
out['main_nocontrols'] = cell(m, 'DID')
out['t5_12'] = main
print(main, out['main_nocontrols'])

# ---- 事件研究（基期 2017）----
yrs = [y for y in sorted(d.year.unique()) if y != 2017]
for y in yrs:
    d[f'E{y}'] = d['PledgePre'] * (d.year == y)
m = fit('Cash ~ ' + '+'.join(f'E{y}' for y in yrs) + f' + {C} | Stkcd + year', d)
t = m.tidy()
es = [{'year': int(y), 'b': float(t.loc[f'E{y}', 'Estimate']), 'lo': float(t.loc[f'E{y}', '2.5%']),
       'hi': float(t.loc[f'E{y}', '97.5%']), 'p': float(t.loc[f'E{y}', 'Pr(>|t|)'])} for y in yrs]
es.append({'year': 2017, 'b': 0.0, 'lo': 0.0, 'hi': 0.0, 'p': 1.0})
out['event'] = sorted(es, key=lambda r: r['year'])
pre_es = [r for r in es if r['year'] <= 2015]
out['event_pre_sig05'] = [r['year'] for r in pre_es if r['p'] < 0.05]
# 政策前系数联合检验（2007—2015）
try:
    R = [f'E{y}' for y in yrs if y <= 2015]
    W = m.wald_test(R=np.eye(len(m.coef()))[[list(m.coef().index).index(r) for r in R]])
    out['event_pre_wald'] = {k: float(v) for k, v in dict(W).items()}
except Exception as e:
    out['event_pre_wald'] = f'未能计算：{e}'
print(out['event_pre_sig05'], out['event_pre_wald'])

# ---- 安慰剂：虚构政策时点 ----
fake = []
for fy in (2014, 2015):
    pf_ = pre_intensity(fy - 2, fy - 1, pd.Timestamp(f'{fy - 2}-01-01'))
    dd = did_sample(pf_, fy, (2007, 2017))
    m = fit(f'Cash ~ DID + {C} | Stkcd + year', dd)
    fake.append({'fake_year': fy, 'coef': cell(m, 'DID'), 'N': stats(m)[1]})
out['placebo_fake'] = fake
print(fake)

# ---- 安慰剂：随机置换处理强度 ----
true_b = fit(f'Cash ~ DID + {C} | Stkcd + year', d).coef()['DID']
rng = np.random.default_rng(20261007)
firms = pre.index.to_numpy()
vals = pre.to_numpy()
perm = []
for k in range(NPERM):
    mp = dict(zip(firms, rng.permutation(vals)))
    dd = d.assign(DID=d['Stkcd'].map(mp) * d['Post'])
    perm.append(float(fit(f'Cash ~ DID + {C} | Stkcd + year', dd).coef()['DID']))
perm = np.array(perm)
out['placebo_perm'] = {'true': float(true_b), 'n': NPERM, 'mean': float(perm.mean()), 'sd': float(perm.std()),
                       'share_abs_ge_true': float((np.abs(perm) >= abs(true_b)).mean()),
                       'pctile_true': float((perm < true_b).mean())}
np.save(os.path.join(der, 'perm.npy'), perm)
print(out['placebo_perm'])
json.dump(out, open(os.path.join(der, 'res_did.json'), 'w'), ensure_ascii=False, indent=1)

# ---- 预案：加入 PledgePre×线性时间趋势（开题报告第三部分所列，事前系数呈趋势时使用）----
if __name__ == '__main__':
    d['PreTrend'] = d['PledgePre'] * (d['year'] - 2017)
    tr = []
    for fe in ['Stkcd + year', 'Stkcd + indyear + provyear']:
        m = fit(f'Cash ~ DID + PreTrend + {C} | {fe}', d)
        tr.append({'fe': fe, 'DID': cell(m, 'DID'), 'PreTrend': cell(m, 'PreTrend'), 'N': stats(m)[1]})
    # 仅用政策前样本估计趋势、外推后检验（更保守的做法）
    dpre = d[d.year <= 2017]
    mt = fit(f'Cash ~ PreTrend + {C} | Stkcd + year', dpre)
    out['trend_adj'] = tr
    out['pre_only_trend'] = cell(mt, 'PreTrend')
    print('trend_adj', tr, 'pre-only trend', out['pre_only_trend'])
    json.dump(out, open(os.path.join(der, 'res_did.json'), 'w'), ensure_ascii=False, indent=1)
