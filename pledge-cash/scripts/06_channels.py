"""5.3 渠道检验：平仓压力（表5-5）、控股股东资金占用（表5-6）。输出 JSON 供续写稿取数。"""
import sys, os, json
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sample import CTRL
from reg_common import fit, cell, stats, pval, ci95

der = sys.argv[1]
s0 = pd.read_pickle(os.path.join(der, 'sample.pkl'))
pr = pd.read_csv(os.path.join(der, 'pressure.csv'), dtype={'Stkcd': str})
lag = pr[['Stkcd', 'year', 'Pressure']].assign(year=pr.year + 1).rename(columns={'Pressure': 'Pressure_l1'})
s = s0.merge(pr, on=['Stkcd', 'year'], how='left').merge(lag, on=['Stkcd', 'year'], how='left')
# 可测度：该公司—年度有保留的明细事件。质押公司若无可测度事件（全部被陈旧规则剔除或未匹配），主口径按 0 处理，稳健性中剔除
s['measured'] = s['Pressure'].notna()
for c in ['Pressure', 'Pressure_Mkt', 'Pressure_l1', 'Pressure_asof', 'Pressure_Mkt_asof']:
    s[c] = s[c].fillna(0.0)
s = s.dropna(subset=['Ret'])
C = '+'.join(CTRL)
out = {'n_ret_missing_dropped': int(len(s0) - len(s))}
SPECS = [('(1)', 'Pressure', 'Stkcd + year'), ('(2)', 'Pressure_l1', 'Stkcd + year'),
         ('(3)', 'Pressure_Mkt', 'Stkcd + year'), ('(4)', 'Pressure_Mkt', 'Stkcd + Ind^year')]

def run(d, specs, tag):
    cols = []
    for nm, pv, fe in specs:
        dd = d.assign(P=d[pv], PxP=d['Pledge'] * d[pv])
        m = fit(f'Cash ~ Pledge + PxP + P + Ret + {C} | {fe}', dd)
        cols.append({'col': nm, 'pv': pv, 'Pledge': cell(m, 'Pledge'), 'PxP': cell(m, 'PxP'), 'P': cell(m, 'P'), 'Ret': cell(m, 'Ret'),
                     'r2': stats(m)[0], 'N': stats(m)[1], 'p_PxP': pval(m, 'PxP'), 'ci_PxP': ci95(m, 'PxP'), 'p_Pledge': pval(m, 'Pledge')})
        print(tag, nm, pv, fe, cols[-1]['PxP'], cols[-1]['Pledge'], cols[-1]['N'])
    return cols

out['t5_5'] = run(s, SPECS, 'main')
# 稳健性 1：剔除无可测度事件的质押公司—年度
unm = (s.Pledge > 0) & ~s.measured
out['n_unmeasured_pledgers'] = int(unm.sum())
out['t5_5_measured_only'] = run(s[~unm], SPECS, 'measured')
# 稳健性 2：陈旧规则只用 t 年末前已披露的结束日期
SPECS_ASOF = [('(1)', 'Pressure_asof', 'Stkcd + year'), ('(3)', 'Pressure_Mkt_asof', 'Stkcd + year'), ('(4)', 'Pressure_Mkt_asof', 'Stkcd + Ind^year')]
out['t5_5_asof'] = run(s, SPECS_ASOF, 'asof')

diag = {}
for pv in ['Pressure', 'Pressure_Mkt']:
    q = s[s.Pledge > 0]
    dd = s.assign(P=s[pv], PxP=s['Pledge'] * s[pv])
    aux = fit(f'PxP ~ Pledge + P + Ret + {C} | Stkcd + year', dd)   # 辅助回归（组内）求方差膨胀因子
    diag[pv] = {'vif_within': float(1 / (1 - aux._r2_within)), 'mean_among_pledgers': float(q[pv].mean()),
                'share_pos_among_pledgers': float((q[pv] > 0).mean())}
out['pressure_diag'] = diag
print(diag)

cols = []
for nm, y, fe in [('(1)', 'OREC', 'Stkcd + year'), ('(2)', 'OREC_raw', 'Stkcd + year'), ('(4)', 'OREC', 'Stkcd + Ind^year')]:
    m = fit(f'{y} ~ Pledge + {C} | {fe}', s0.dropna(subset=[y]))
    cols.append({'col': nm, 'Pledge': cell(m, 'Pledge'), 'r2': stats(m)[0], 'N': stats(m)[1], 'ci': ci95(m, 'Pledge')})
    print(nm, y, cols[-1])
out['t5_6'] = cols
json.dump(out, open(os.path.join(der, 'res_channels.json'), 'w'), ensure_ascii=False, indent=1)
