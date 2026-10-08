"""5.7 投资、5.8 稳健性与内生性（表5-15—5-19 及正文所引附加检验）。"""
import sys, os, json
import numpy as np
import pandas as pd
import pyfixest as pf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sample import CTRL
from reg_common import fit, cell, stats, pval, ci95

der = sys.argv[1]
C = '+'.join(CTRL)
s = pd.read_pickle(os.path.join(der, 'sample.pkl'))
s['indyear'] = s['Ind'].astype(str) + '_' + s['year'].astype(str)
s['soecat'] = s['SOE'].map({1.0: 'S', 0.0: 'N'}).fillna('M')       # 股权性质缺失单列一类
s['soeyear'] = s['soecat'] + '_' + s['year'].astype(str)
out = {}
base = lambda y, x, d, vcov=None, fe='Stkcd + year', ctrl=C: fit(f'{y} ~ {x} + {ctrl} | {fe}', d, vcov)
res = lambda m, v: {'coef': cell(m, v), 'r2': stats(m)[0], 'N': stats(m)[1], 'p': pval(m, v), 'ci': ci95(m, v)}

# 表5-15：资本支出
out['t5_15_capex'] = res(base('Capex', 'Pledge', s.dropna(subset=['Capex'])), 'Pledge')

# 表5-16：替换质押口径
out['t5_16'] = {v: res(base('Cash', v, s.dropna(subset=[v])), v) for v in ['Pledge_Dum', 'Pledge_Ratio2', 'Pledge_det']}

# 表5-17：样本与设定
out['t5_17'] = {
    'drop_crisis': res(base('Cash', 'Pledge', s[~s.year.isin([2008, 2015, 2020])]), 'Pledge'),
    'drop_first3': res(base('Cash', 'Pledge', s[s.ListAge >= 3]), 'Pledge'),
    'twoway': res(base('Cash', 'Pledge', s, {'CRV1': 'Stkcd+indyear'}), 'Pledge'),
    'soe_year': res(base('Cash', 'Pledge', s, fe='Stkcd + soeyear'), 'Pledge'),
    'ind_soe_year': res(base('Cash', 'Pledge', s, fe='Stkcd + indyear + soeyear'), 'Pledge'),
}

# 质押余额的时效（陈旧余额：所有正余额出质方的最后一条记录都早于年末3年以上）
stale = s['Pledge_stale'] == 1
flag_no = s['Top1Flag_raw'] != 1
out['stale'] = {
    'n_stale': int(stale.sum()), 'share_among_pledgers': float(stale.sum() / (s.Pledge > 0).sum()),
    'n_stale_flag_no': int((stale & flag_no).sum()),
    'zero_stale_flagno': res(base('Cash', 'P', s.assign(P=np.where(stale & flag_no, 0, s.Pledge))), 'P'),
    'zero_all_stale': res(base('Cash', 'P', s.assign(P=np.where(stale, 0, s.Pledge))), 'P'),
    'drop_stale': res(base('Cash', 'Pledge', s[~stale]), 'Pledge'),
}

# 改进口径：非名义持有人为第一大股东、宽松名称匹配、剔除重复出质方ID、全部股本市值、Growth 无穷值记缺失、代码变更公司原上市年份
alt_ctrl = C.replace('TobinQ', 'TobinQ_alt').replace('Growth', 'Growth_alt').replace('Top1', 'Top1_alt').replace('Age', 'Age_alt')
sa = s.dropna(subset=['Pledge_alt', 'TobinQ_alt', 'Growth_alt', 'Top1_alt', 'Age_alt'])
out['alt_construction'] = res(base('Cash', 'Pledge_alt', sa, ctrl=alt_ctrl), 'Pledge_alt')
out['alt_construction']['n_nominee'] = int(s['Rank1IsNominee'].fillna(False).sum())

# 表5-18：上市年限分组（上市当年记为第1年）与同一阶段内估计
grp = {'1-3': s.ListAge.between(0, 2), '4-6': s.ListAge.between(3, 5), '7+': s.ListAge >= 6}
out['t5_18'] = {k: res(base('Cash', 'Pledge', s[v]), 'Pledge') for k, v in grp.items()}
s['stage'] = np.select([s.ListAge <= 2, s.ListAge <= 5], ['a', 'b'], 'c')
s['firmstage'] = s['Stkcd'] + '_' + s['stage']
out['t5_18_within'] = res(base('Cash', 'Pledge', s, fe='firmstage + year'), 'Pledge')
ns = s[s.groupby('firmstage').Stkcd.transform('size') > 1]
out['t5_18_samesample_firmfe'] = res(base('Cash', 'Pledge', ns), 'Pledge')
out['listage_counts'] = {str(k): int(v) for k, v in s.ListAge.clip(upper=3).value_counts().sort_index().items()}

# 表5-19 (1)：滞后一期
raw = pd.read_pickle(os.path.join(der, 'panel_raw.pkl'))[['Stkcd', 'year', 'Pledge_raw']]
lagp = raw.assign(year=raw.year + 1, L_Pledge=raw.Pledge_raw.clip(0, 1))[['Stkcd', 'year', 'L_Pledge']]
sl = s.merge(lagp, on=['Stkcd', 'year'], how='left').dropna(subset=['L_Pledge'])
out['t5_19_lag'] = res(base('Cash', 'L_Pledge', sl), 'L_Pledge')

# 表5-19 (2)：PSM（逐年 logit 倾向得分；1:1 近邻、有放回、卡尺 0.05）。对照组按被匹配次数加权（主结果），并报告去重不加权结果
rows = []
for y, g in s.groupby('year'):
    g = g.reset_index(drop=True)
    lm = pf.feglm(f'Pledge_Dum ~ {C}', data=g, family='logit')
    g['ps'] = np.asarray(lm.predict(type='response'))
    tr, co = g[g.Pledge_Dum == 1], g[g.Pledge_Dum == 0]
    if len(co) == 0:
        continue
    cps = co['ps'].to_numpy(); order = np.argsort(cps); cs = cps[order]
    tp_ = tr['ps'].to_numpy()
    idx = np.searchsorted(cs, tp_)
    lo = np.clip(idx - 1, 0, len(cs) - 1); hi = np.clip(idx, 0, len(cs) - 1)
    pick = np.where(np.abs(cs[lo] - tp_) <= np.abs(cs[hi] - tp_), lo, hi)
    ok = np.abs(cs[pick] - tp_) <= 0.05
    trm = tr[ok].assign(w=1.0)
    com = co.iloc[order[pick[ok]]].copy()
    com = com.groupby(['Stkcd', 'year'], as_index=False).size().merge(co, on=['Stkcd', 'year']).rename(columns={'size': 'w'})
    rows.append(pd.concat([trm, com], ignore_index=True))
mt = pd.concat(rows, ignore_index=True)

def sbias(d, c, w=None):
    a, b = d[d.Pledge_Dum == 1], d[d.Pledge_Dum == 0]
    if w is None:
        ma, mb, va, vb = a[c].mean(), b[c].mean(), a[c].var(), b[c].var()
    else:
        wa, wb = a[w], b[w]
        ma, mb = np.average(a[c], weights=wa), np.average(b[c], weights=wb)
        va, vb = np.average((a[c] - ma) ** 2, weights=wa), np.average((b[c] - mb) ** 2, weights=wb)
    return float(100 * (ma - mb) / np.sqrt((va + vb) / 2))
out['psm_balance'] = [{'var': c, 'before': sbias(s, c), 'after_unweighted': sbias(mt, c), 'after_weighted': sbias(mt, c, 'w')} for c in CTRL]
out['psm_n'] = {'treated_total': int((s.Pledge_Dum == 1).sum()), 'treated_matched': int((mt.Pledge_Dum == 1).sum()),
                'controls_unique': int((mt.Pledge_Dum == 0).sum()), 'control_matches': int(mt.loc[mt.Pledge_Dum == 0, 'w'].sum()),
                'max_reuse': int(mt.loc[mt.Pledge_Dum == 0, 'w'].max())}
mw = pf.feols(f'Cash ~ Pledge + {C} | Stkcd + year', data=mt.reset_index(drop=True), weights='w', vcov={'CRV1': 'Stkcd'})
out['t5_19_psm'] = res(mw, 'Pledge')
out['t5_19_psm']['N_obs'] = int(len(mt)); out['t5_19_psm']['N_weighted'] = int(mt.w.sum())
out['t5_19_psm_unweighted'] = res(base('Cash', 'Pledge', mt), 'Pledge')

# 表5-19 (3)：2SLS，工具变量为同行业同年度（剔除本公司）平均质押比例；工具变量在行业—年度层面变化，另报告行业聚类结果
g = s.groupby(['Ind', 'year'])['Pledge']
s['IV_Pledge'] = (g.transform('sum') - s['Pledge']) / (g.transform('count') - 1)
si = s.dropna(subset=['IV_Pledge']).reset_index(drop=True)
iv = {}
for k, v in [('firm', {'CRV1': 'Stkcd'}), ('industry', {'CRV1': 'Ind'})]:
    mi = pf.feols(f'Cash ~ {C} | Stkcd + year | Pledge ~ IV_Pledge', data=si, vcov=v)
    fsm = pf.feols(f'Pledge ~ IV_Pledge + {C} | Stkcd + year', data=si, vcov=v)
    t1 = fsm.tidy().loc['IV_Pledge']
    iv[k] = {'second': res(mi, 'Pledge'), 'first': cell(fsm, 'IV_Pledge'), 'F': float((t1['Estimate'] / t1['Std. Error']) ** 2)}
out['t5_19_iv'] = iv
out['iv_n_cells'] = {'industries': int(si.Ind.nunique()), 'industry_years': int(si.groupby(['Ind', 'year']).ngroups)}
json.dump(out, open(os.path.join(der, 'res_robust.json'), 'w'), ensure_ascii=False, indent=1, default=str)
for k, v in out.items():
    print(k, str(v)[:400])
