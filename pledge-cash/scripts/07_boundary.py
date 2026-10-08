"""5.4 边界条件：融资约束（表5-8）与产权性质（表5-9、表5-10）。

交乘项按开题报告表3（温忠麟等，2005）对 Pledge 与调节变量中心化后构造；主效应保留原变量，
故 Pledge 的系数为调节变量取样本均值时的效应。
SA 主口径按开题报告表3：Size 为总资产（百万元人民币）对数，上限 370 亿元；稳健性口径按 Hadlock 和 Pierce（2010）原文的
美元单位：总资产按 8.28 元/美元（2004 年汇率，与开题报告折算 370 亿元的口径一致）折为百万美元，上限 4,500。
"""
import sys, os, json
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sample import CTRL
from reg_common import fit, cell, stats, pval

der = sys.argv[1]
C = '+'.join(CTRL)
s = pd.read_pickle(os.path.join(der, 'sample.pkl'))
raw = pd.read_pickle(os.path.join(der, 'panel_raw.pkl'))[['Stkcd', 'year', 'SA', 'ta', 'ListAge']].copy()
age_c = np.minimum(raw['ListAge'].clip(lower=0), 37)
size_u = np.log(np.minimum(raw['ta'] / 1e6 / 8.28, 4500.0))
raw['SA_usd'] = -0.737 * size_u + 0.043 * size_u ** 2 - 0.040 * age_c
lagSA = raw[['Stkcd', 'year', 'SA', 'SA_usd']].assign(year=raw.year + 1).rename(columns={'SA': 'SA_l1', 'SA_usd': 'SA_usd_l1'})
s = s.merge(lagSA, on=['Stkcd', 'year'], how='left').dropna(subset=['SA_l1']).reset_index(drop=True)
s = s.merge(raw[['Stkcd', 'year', 'SA_usd']], on=['Stkcd', 'year'], how='left')
out = {}

# SA 口径诊断（开题报告承诺报告）
size_m = np.log(np.minimum(s['ta'] / 1e6, 37000.0))
tp = 0.737 / (2 * 0.043)   # 二次项拐点：ln(百万) = 8.57
out['sa_diag'] = {
    'corr_SA_Size': float(s[['SA', 'Size']].corr().iloc[0, 1]), 'corr_SA_Age': float(s[['SA', 'Age']].corr().iloc[0, 1]),
    'corr_SAusd_Size': float(s[['SA_usd', 'Size']].corr().iloc[0, 1]), 'corr_SAusd_Age': float(s[['SA_usd', 'Age']].corr().iloc[0, 1]),
    'turning_point_yi_yuan': float(np.exp(tp) * 1e6 / 1e8), 'share_above_tp_rmb': float((size_m > tp).mean()),
    'share_above_tp_usd': float((np.log(np.minimum(s['ta'] / 1e6 / 8.28, 4500.0)) > tp).mean()),
}
print(out['sa_diag'])

pc = s['Pledge'] - s['Pledge'].mean()
res = []
for tag, lv, extra in [('SA', 'SA_l1', ''), ('SA', 'SA_l1', ' + PxAge + PxSize'),
                       ('SA_usd', 'SA_usd_l1', ''), ('SA_usd', 'SA_usd_l1', ' + PxAge + PxSize')]:
    hf = (s[lv] > s.groupby('year')[lv].transform('median')).astype(float)
    d = s.assign(HighFC=hf, PxH=pc * (hf - hf.mean()),
                 PxAge=pc * (s['Age'] - s['Age'].mean()), PxSize=pc * (s['Size'] - s['Size'].mean()))
    m = fit(f'Cash ~ Pledge + PxH + HighFC{extra} + {C} | Stkcd + year', d)
    res.append({'fc': tag, 'Pledge': cell(m, 'Pledge'), 'PxH': cell(m, 'PxH'), 'HighFC': cell(m, 'HighFC'),
                'PxAge': cell(m, 'PxAge'), 'PxSize': cell(m, 'PxSize'), 'r2': stats(m)[0], 'N': stats(m)[1],
                'p_PxH': pval(m, 'PxH'), 'corr_HighFC_Age': float(np.corrcoef(hf, s['Age'])[0, 1])})
    print(res[-1])
out['t5_8'] = res
out['corr_HighFC_Age'] = res[0]['corr_HighFC_Age']

# 产权性质
t = pd.read_pickle(os.path.join(der, 'sample.pkl'))
t['dm'] = t['Pledge'] - t.groupby('Stkcd')['Pledge'].transform('mean')
dist = []
for g, nm in [(1.0, '国有企业'), (0.0, '非国有企业')]:
    q = t[t.SOE == g]
    dist.append({'组别': nm, 'N': f'{len(q):,}', 'dum': float((q.Pledge > 0).mean()), 'mean': f'{q.Pledge.mean():.3f}',
                 'within_sd': f'{q.dm.std():.3f}', 'p75': f'{q.Pledge.quantile(.75):.3f}', 'p90': f'{q.Pledge.quantile(.9):.3f}'})
out['t5_9'] = dist
out['soe_coding'] = {'n_missing_as_0': int(t.SOE_raw.isna().sum()),
                     'n_mixed_guoqi_as_0': int(((t.SOE == 0) & t.EquityNature.fillna('').str.contains('国企')).sum())}
print(dist, out['soe_coding'])
t['PxSOE'] = (t['Pledge'] - t['Pledge'].mean()) * (t['SOE'] - t['SOE'].mean())
t['soeyear'] = t['SOE'].astype(int).astype(str) + '_' + t['year'].astype(str)
ma = fit(f'Cash ~ Pledge + PxSOE + SOE + {C} | Stkcd + year', t)
mp = fit(f'Cash ~ Pledge + {C} | Stkcd + year', t[t.SOE == 0])
ms = fit(f'Cash ~ Pledge + {C} | Stkcd + year', t[t.SOE == 1])
my = fit(f'Cash ~ Pledge + PxSOE + {C} | Stkcd + soeyear', t)
out['t5_10'] = [{'Pledge': cell(m, 'Pledge'), 'PxSOE': cell(m, 'PxSOE'), 'r2': stats(m)[0], 'N': stats(m)[1]} for m in (ma, mp, ms, my)]
print(out['t5_10'])
json.dump(out, open(os.path.join(der, 'res_boundary.json'), 'w'), ensure_ascii=False, indent=1)
