"""5.7 投资（表5-15 列1）、5.8 稳健性（表5-16、5-17）、生命周期（表5-18）、内生性（表5-19）。"""
import sys, os, json
import numpy as np
import pandas as pd
import pyfixest as pf
sys.path.insert(0, os.path.dirname(__file__))
from sample import CTRL
from reg_common import fit, cell, stats

der = sys.argv[1]
C = '+'.join(CTRL)
s = pd.read_pickle(os.path.join(der, 'sample.pkl'))
s['indyear'] = s['Ind'].astype(str) + '_' + s['year'].astype(str)
out = {}
base = lambda y, x, d, vcov=None, fe='Stkcd + year': fit(f'{y} ~ {x} + {C} | {fe}', d, vcov)
res = lambda m, v: {'coef': cell(m, v), 'r2': stats(m)[0], 'N': stats(m)[1]}

# 表5-15：资本支出
out['t5_15_capex'] = res(base('Capex', 'Pledge', s.dropna(subset=['Capex'])), 'Pledge')

# 表5-16：替换质押口径
out['t5_16'] = {v: res(base('Cash', v, s.dropna(subset=[v])), v) for v in ['Pledge_Dum', 'Pledge_Ratio2', 'Pledge_det']}

# 表5-17：样本与设定
out['t5_17'] = {
    'drop_crisis': res(base('Cash', 'Pledge', s[~s.year.isin([2008, 2015, 2020])]), 'Pledge'),
    'drop_first3': res(base('Cash', 'Pledge', s[s.ListAge >= 3]), 'Pledge'),
    'twoway': res(base('Cash', 'Pledge', s, {'CRV1': 'Stkcd+indyear'}), 'Pledge'),
}

# 表5-18：上市年限分组（上市当年记为第1年）
grp = {'1-3': s.ListAge.between(0, 2), '4-6': s.ListAge.between(3, 5), '7+': s.ListAge >= 6}
out['t5_18'] = {k: res(base('Cash', 'Pledge', s[v]), 'Pledge') for k, v in grp.items()}

# 表5-19 (1)：滞后一期
raw = pd.read_pickle(os.path.join(der, 'panel_raw.pkl'))[['Stkcd', 'year', 'Pledge_raw']]
lagp = raw.assign(year=raw.year + 1, L_Pledge=raw.Pledge_raw.clip(0, 1))[['Stkcd', 'year', 'L_Pledge']]
sl = s.merge(lagp, on=['Stkcd', 'year'], how='left').dropna(subset=['L_Pledge'])
out['t5_19_lag'] = res(base('Cash', 'L_Pledge', sl), 'L_Pledge')

# 表5-19 (2)：PSM（逐年 logit 估计倾向得分；1:1 近邻、有放回、卡尺 0.05；保留匹配样本的唯一观测）
matched, bal = [], []
for y, g in s.groupby('year'):
    g = g.reset_index(drop=True)
    lm = pf.feglm(f'Pledge_Dum ~ {C}', data=g, family='logit')
    g['ps'] = np.asarray(lm.predict(type='response'))
    tr, co = g[g.Pledge_Dum == 1], g[g.Pledge_Dum == 0]
    if len(co) == 0:
        continue
    cps = co['ps'].to_numpy(); order = np.argsort(cps); cs = cps[order]
    idx = np.searchsorted(cs, tr['ps'].to_numpy())
    lo = np.clip(idx - 1, 0, len(cs) - 1); hi = np.clip(idx, 0, len(cs) - 1)
    pick = np.where(np.abs(cs[lo] - tr['ps'].to_numpy()) <= np.abs(cs[hi] - tr['ps'].to_numpy()), lo, hi)
    dist = np.abs(cs[pick] - tr['ps'].to_numpy())
    ok = dist <= 0.05
    m_co = co.iloc[order[pick[ok]]]
    matched.append(pd.concat([tr[ok], m_co]).drop_duplicates(subset=['Stkcd', 'year']))
mt = pd.concat(matched, ignore_index=True)
def sbias(a, b, c):
    return 100 * (a[c].mean() - b[c].mean()) / np.sqrt((a[c].var() + b[c].var()) / 2)
for c in CTRL:
    bal.append({'var': c, 'before': sbias(s[s.Pledge_Dum == 1], s[s.Pledge_Dum == 0], c),
                'after': sbias(mt[mt.Pledge_Dum == 1], mt[mt.Pledge_Dum == 0], c)})
out['psm_balance'] = bal
out['psm_n'] = {'treated_matched': int((mt.Pledge_Dum == 1).sum()), 'controls_unique': int((mt.Pledge_Dum == 0).sum()),
                'treated_total': int((s.Pledge_Dum == 1).sum())}
out['t5_19_psm'] = res(base('Cash', 'Pledge', mt), 'Pledge')

# 表5-19 (3)：2SLS，工具变量为同行业同年度（剔除本公司）平均质押比例
g = s.groupby(['Ind', 'year'])['Pledge']
s['IV_Pledge'] = (g.transform('sum') - s['Pledge']) / (g.transform('count') - 1)
si = s.dropna(subset=['IV_Pledge']).reset_index(drop=True)
mi = pf.feols(f'Cash ~ {C} | Stkcd + year | Pledge ~ IV_Pledge', data=si, vcov={'CRV1': 'Stkcd'})
out['t5_19_iv'] = res(mi, 'Pledge')
fsm = pf.feols(f'Pledge ~ IV_Pledge + {C} | Stkcd + year', data=si, vcov={'CRV1': 'Stkcd'})
t1 = fsm.tidy().loc['IV_Pledge']
out['iv_first'] = {'coef': cell(fsm, 'IV_Pledge'), 'cluster_robust_F': float((t1['Estimate'] / t1['Std. Error']) ** 2)}
json.dump(out, open(os.path.join(der, 'res_robust.json'), 'w'), ensure_ascii=False, indent=1, default=str)
for k, v in out.items():
    print(k, v)
