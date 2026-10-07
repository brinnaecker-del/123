"""5.4 边界条件：融资约束（表5-8，SA 口径）与产权性质（表5-9、表5-10）。"""
import sys, os, json
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from sample import CTRL
from reg_common import fit, cell, stats

der = sys.argv[1]
s = pd.read_pickle(os.path.join(der, 'sample.pkl'))
raw = pd.read_pickle(os.path.join(der, 'panel_raw.pkl'))[['Stkcd', 'year', 'SA']]
lagSA = raw.assign(year=raw.year + 1).rename(columns={'SA': 'SA_l1'})
s = s.merge(lagSA, on=['Stkcd', 'year'], how='left').dropna(subset=['SA_l1'])
s['HighFC'] = (s['SA_l1'] > s.groupby('year')['SA_l1'].transform('median')).astype(float)
s['PxH'] = s['Pledge'] * s['HighFC']
s['PxAge'] = s['Pledge'] * (s['Age'] - s['Age'].mean())
s['PxSize'] = s['Pledge'] * (s['Size'] - s['Size'].mean())
C = '+'.join(CTRL)
out = {}
m1 = fit(f'Cash ~ Pledge + PxH + HighFC + {C} | Stkcd + year', s)
m2 = fit(f'Cash ~ Pledge + PxH + HighFC + PxAge + PxSize + {C} | Stkcd + year', s)
out['t5_8'] = [{'Pledge': cell(m, 'Pledge'), 'PxH': cell(m, 'PxH'), 'HighFC': cell(m, 'HighFC'),
                'PxAge': cell(m, 'PxAge'), 'PxSize': cell(m, 'PxSize'), 'r2': stats(m)[0], 'N': stats(m)[1]} for m in (m1, m2)]
print(out['t5_8'])
out['corr_HighFC_Age'] = float(s[['HighFC', 'Age']].corr().iloc[0, 1])
print('corr(HighFC, Age)', out['corr_HighFC_Age'])

# 产权性质
t = pd.read_pickle(os.path.join(der, 'sample.pkl'))
t['dm'] = t['Pledge'] - t.groupby('Stkcd')['Pledge'].transform('mean')
dist = []
for g, nm in [(1.0, '国有企业'), (0.0, '民营企业')]:
    q = t[t.SOE == g]
    dist.append({'组别': nm, 'N': f'{len(q):,}', 'dum': f'{(q.Pledge > 0).mean():.3f}', 'mean': f'{q.Pledge.mean():.3f}',
                 'within_sd': f'{q.dm.std():.3f}', 'p75': f'{q.Pledge.quantile(.75):.3f}', 'p90': f'{q.Pledge.quantile(.9):.3f}'})
out['t5_9'] = dist
print(dist)
t['PxSOE'] = t['Pledge'] * t['SOE']
ma = fit(f'Cash ~ Pledge + PxSOE + SOE + {C} | Stkcd + year', t)
mp = fit(f'Cash ~ Pledge + {C} | Stkcd + year', t[t.SOE == 0])
ms = fit(f'Cash ~ Pledge + {C} | Stkcd + year', t[t.SOE == 1])
out['t5_10'] = [{'Pledge': cell(m, 'Pledge'), 'PxSOE': cell(m, 'PxSOE'), 'r2': stats(m)[0], 'N': stats(m)[1]} for m in (ma, mp, ms)]
print(out['t5_10'])
json.dump(out, open(os.path.join(der, 'res_boundary.json'), 'w'), ensure_ascii=False, indent=1)
