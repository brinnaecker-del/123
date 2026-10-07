"""表4（描述性统计）、表6（基准回归）、表7（U型复现）——用最终样本重算并输出 JSON。"""
import sys, os, json
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from sample import CTRL
from reg_common import fit, cell, stats
from lind_mehlum import utest

der = sys.argv[1]
s = pd.read_pickle(os.path.join(der, 'sample.pkl'))
C = '+'.join(CTRL)
out = {'N': len(s), 'firms': int(s.Stkcd.nunique())}
V = ['Cash', 'Pledge', 'Pledge_Dum', 'SA', 'Size', 'Lev', 'ROA', 'Growth', 'CFVol', 'TobinQ', 'CF', 'NWC', 'Age', 'Top1', 'SOE']
out['t4'] = s[V].describe().T[['count', 'mean', 'std', 'min', '50%', 'max']].round(3).to_dict('index')
ms = [fit('Cash ~ Pledge | Stkcd + year', s), fit(f'Cash ~ Pledge + {C} | Stkcd + year', s),
      fit(f'Cash ~ Pledge + {C} | Stkcd + Ind^year', s), fit(f'Cash ~ Pledge + {C} | Stkcd + year + ListAge', s)]
out['t6'] = [{'coef': cell(m, 'Pledge'), 'r2': stats(m)[0], 'N': stats(m)[1]} for m in ms]
b = ms[1].coef()['Pledge']; out['t6_1sd_over_mean'] = float(b * s.Pledge.std() / s.Cash.mean())
s['Pledge2'] = s.Pledge ** 2
sub = s[s.year.between(2013, 2015) & (s.ListAge > 0)]
t7 = []
for d, fe in [(sub, 'Ind + year'), (s, 'Ind + year'), (sub, 'Stkcd + year'), (s, 'Stkcd + year')]:
    m = fit(f'Cash ~ Pledge + Pledge2 + {C} | {fe}', d); u = utest(m)
    t7.append({'b1': cell(m, 'Pledge'), 'b2': cell(m, 'Pledge2'), 'r2': stats(m)[0], 'N': stats(m)[1],
               'tp': float(u['turning']), 'holds': bool(u['holds']), 'p_lo': float(u['p_lo']), 'p_hi': float(u['p_hi'])})
out['t7'] = t7
json.dump(out, open(os.path.join(der, 'res_baseline.json'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps({k: out[k] for k in ['N', 'firms', 't6', 't6_1sd_over_mean', 't7']}, ensure_ascii=False))
