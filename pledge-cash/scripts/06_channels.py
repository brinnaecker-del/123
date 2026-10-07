"""5.3 渠道检验：平仓压力（表5-5）、控股股东资金占用（表5-6）。输出 JSON 供续写稿取数。"""
import sys, os, json
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from sample import CTRL, winsor
from reg_common import fit, cell, stats

der = sys.argv[1]
s = pd.read_pickle(os.path.join(der, 'sample.pkl'))
pr = pd.read_csv(os.path.join(der, 'pressure.csv'), dtype={'Stkcd': str})
lag = pr[['Stkcd', 'year', 'Pressure']].assign(year=pr.year + 1).rename(columns={'Pressure': 'Pressure_l1'})
s = s.merge(pr[['Stkcd', 'year', 'Pressure', 'Pressure_Mkt']], on=['Stkcd', 'year'], how='left').merge(lag, on=['Stkcd', 'year'], how='left')
for c in ['Pressure', 'Pressure_Mkt', 'Pressure_l1']:
    s[c] = s[c].fillna(0.0)   # 无保留的未解押质押 → 0
s = s.dropna(subset=['Ret'])
C = '+'.join(CTRL)
out = {}
cols = []
for nm, pv, fe in [('(1)', 'Pressure', 'Stkcd + year'), ('(2)', 'Pressure_l1', 'Stkcd + year'),
                   ('(3)', 'Pressure_Mkt', 'Stkcd + year'), ('(4)', 'Pressure_Mkt', 'Stkcd + Ind^year')]:
    d = s.assign(P=s[pv], PxP=s['Pledge'] * s[pv])
    m = fit(f'Cash ~ Pledge + PxP + P + Ret + {C} | {fe}', d)
    cols.append({'Pledge': cell(m, 'Pledge'), 'PxP': cell(m, 'PxP'), 'P': cell(m, 'P'), 'Ret': cell(m, 'Ret'),
                 'r2': stats(m)[0], 'N': stats(m)[1], 'p_PxP': float(m.tidy().loc['PxP', 'Pr(>|t|)'])})
    print(nm, pv, fe, cols[-1])
out['t5_5'] = cols
diag = {}
for pv in ['Pressure', 'Pressure_Mkt']:
    q = s[s.Pledge > 0]
    diag[pv] = {'corr_PxP_P_all': float(np.corrcoef(s.Pledge * s[pv], s[pv])[0, 1]),
                'mean_among_pledgers': float(q[pv].mean()), 'share_pos_among_pledgers': float((q[pv] > 0).mean())}
out['pressure_diag'] = diag
print(diag)

cols = []
for nm, y, fe in [('(1)', 'OREC', 'Stkcd + year'), ('(2)', 'OREC_raw', 'Stkcd + year'), ('(4)', 'OREC', 'Stkcd + Ind^year')]:
    d = s if y in s else s
    m = fit(f'{y} ~ Pledge + {C} | {fe}', pd.read_pickle(os.path.join(der, 'sample.pkl')).dropna(subset=[y]))
    cols.append({'col': nm, 'Pledge': cell(m, 'Pledge'), 'r2': stats(m)[0], 'N': stats(m)[1]})
    print(nm, y, cols[-1])
out['t5_6'] = cols
json.dump(out, open(os.path.join(der, 'res_channels.json'), 'w'), ensure_ascii=False, indent=1)
