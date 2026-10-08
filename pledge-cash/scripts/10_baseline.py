"""表4（描述性统计）、表6（基准回归）、表7（U型复现）与质押口径核验，输出 JSON。

主口径：质押余额仅在全部解押时归零；行业为制造业两位大类、其余门类（表6列(3)行业×年度固定效应与表7混合回归的行业虚拟变量）；
表7各列均剔除上市当年观测（开题报告表7注）。另以开题报告口径（Pledge_rep、Ind_rep、Ind7_rep、SOE_rep）重算一遍，供复现对照。
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
s['Pledge_Dum'] = (s['Pledge'] > 0).astype(float)
s['Pledge2'] = s.Pledge ** 2

def tables(d, pv, ind6, ind7, soe):
    d = d.assign(P=d[pv], P2=d[pv] ** 2, I6=d[ind6], I7=d[ind7])
    r = {}
    t4 = d.assign(Pledge=d[pv], Pledge_Dum=(d[pv] > 0).astype(float), SOE=d[soe])[V].describe().T
    r['t4'] = t4[['count', 'mean', 'std', 'min', '50%', 'max']].round(3).to_dict('index')
    ms = [fit('Cash ~ P | Stkcd + year', d), fit(f'Cash ~ P + {C} | Stkcd + year', d),
          fit(f'Cash ~ P + {C} | Stkcd + I6^year', d), fit(f'Cash ~ P + {C} | Stkcd + year + ListAge', d)]
    r['t6'] = [{'coef': cell(m, 'P'), 'r2': stats(m)[0], 'N': stats(m)[1]} for m in ms]
    r['t6_1sd_over_mean'] = float(ms[1].coef()['P'] * d[pv].std() / d.Cash.mean())
    full = d[d.ListAge > 0]
    sub = full[full.year.between(2013, 2015)]
    t7 = []
    for dd, fe in [(sub, 'I7 + year'), (full, 'I7 + year'), (sub, 'Stkcd + year'), (full, 'Stkcd + year')]:
        m = fit(f'Cash ~ P + P2 + {C} | {fe}', dd); u = utest(m, x='P', x2='P2')
        t7.append({'b1': cell(m, 'P'), 'b2': cell(m, 'P2'), 'r2': stats(m)[0], 'N': stats(m)[1],
                   'tp': float(u['turning']), 'holds': bool(u['holds']), 'p_lo': float(u['p_lo']), 'p_hi': float(u['p_hi'])})
    r['t7'] = t7
    return r

out.update(tables(s, 'Pledge', 'Ind', 'Ind', 'SOE'))
out['rep'] = tables(s, 'Pledge_rep', 'Ind_rep', 'Ind7_rep', 'SOE_rep')
out['n_soe_missing'] = int(s.SOE.isna().sum())
# 表5-2 相关系数矩阵（Pearson）
CV = ['Cash', 'Pledge', 'Size', 'Lev', 'ROA', 'Growth', 'TobinQ', 'CF', 'CFVol', 'NWC', 'Age', 'Top1']
cm = s[CV].corr()
from scipy import stats as sst
pm = pd.DataFrame([[sst.pearsonr(s[a], s[b])[1] for b in CV] for a in CV], index=CV, columns=CV)
out['corr'] = {'vars': CV, 'r': cm.round(3).values.tolist(), 'p': pm.values.tolist()}
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
print('REP', json.dumps({k: out['rep'][k] for k in ['t6', 't7']}, ensure_ascii=False))
print(mc)
