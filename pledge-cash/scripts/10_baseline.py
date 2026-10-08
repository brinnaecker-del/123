"""表4（描述性统计）、表6（基准回归）、表7（U型复现）与质押口径核验，输出 JSON。

主口径复现开题报告：表6列(3)的行业×年度固定效应按证监会门类；表7列(1)(2)为混合回归，行业虚拟变量为
制造业按代码首位数字（C1—C4）、其余门类，并控制年度；表7各列均剔除上市当年观测（开题报告表7注）。
"""
import sys, os, json
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
full = s[s.ListAge > 0]
sub = full[full.year.between(2013, 2015)]
t7 = []
for d, fe in [(sub, 'Ind7 + year'), (full, 'Ind7 + year'), (sub, 'Stkcd + year'), (full, 'Stkcd + year')]:
    m = fit(f'Cash ~ Pledge + Pledge2 + {C} | {fe}', d); u = utest(m)
    t7.append({'b1': cell(m, 'Pledge'), 'b2': cell(m, 'Pledge2'), 'r2': stats(m)[0], 'N': stats(m)[1],
               'tp': float(u['turning']), 'holds': bool(u['holds']), 'p_lo': float(u['p_lo']), 'p_hi': float(u['p_hi'])})
out['t7'] = t7
json.dump(out, open(os.path.join(der, 'res_baseline.json'), 'w'), ensure_ascii=False, indent=1)

# 质押口径核验（开题报告第四部分（一）的三项说法）
both = s[(s.Pledge > 0) | (s.Pledge_det > 0)]
mc = {'corr_stat_detail': float(np.corrcoef(s.Pledge, s.Pledge_det)[0, 1]),
      'share_within_5pp': float((np.abs(s.Pledge - s.Pledge_det) <= 0.05).mean()),
      'agree_dum_flag1': float(((s.Pledge > 0) == (s.Top1Flag_raw == 1)).mean()),
      'corr_among_pledgers': float(np.corrcoef(both.Pledge, both.Pledge_det)[0, 1]),
      'share_within_5pp_among_pledgers': float((np.abs(both.Pledge - both.Pledge_det) <= 0.05).mean()),
      'share_raw_gt1': float((s.Pledge_raw > 1.0001).mean()), 'share_raw_neg': float((s.Pledge_raw < -1e-9).mean()),
      'share_stale': float(s.Pledge_stale.mean()), 'share_stale_among_pledgers': float(s.loc[s.Pledge > 0, 'Pledge_stale'].mean())}
json.dump(mc, open(os.path.join(der, 'res_measure_check.json'), 'w'), indent=1)
print(json.dumps({k: out[k] for k in ['N', 'firms', 't6', 't6_1sd_over_mean', 't7']}, ensure_ascii=False))
print(mc)
