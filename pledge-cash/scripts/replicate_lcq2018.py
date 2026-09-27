"""
复现并检验李常青、幸伟、李茂良（2018，《财贸经济》）的 U 型结论。

原文：2013—2015 年季度数据；Cash = 现金及现金等价物 /（总资产 − 现金及现金等价物）；
PledgeRate = 控股股东质押股数 / 其持股数；混合 OLS，控制行业（制造业按二级）与季度虚拟变量，公司聚类；
结果：一次项 −0.16***、平方项 +0.15***，拐点约 55%，U 型只存在于非国有企业。

本脚本在年度数据上：
  1. 按原文口径（混合 OLS + 行业 + 年度）复现；
  2. 延长样本期；
  3. 加入公司固定效应，看 U 型的上升段是否来自公司间差异；
  4. 用 Lind 和 Mehlum（2010）的端点斜率检验判断 U 型是否成立：
     左端点（质押比例 = 0）斜率显著为负、右端点（= 1）斜率显著为正，才算 U 型成立。

    python replicate_lcq2018.py --panel ../data_clean/panel.csv --out ../results/复现李常青2018.md
"""
import argparse
import os
import warnings

import numpy as np
import pandas as pd
import pyfixest as pf

warnings.filterwarnings('ignore')
HERE = os.path.dirname(os.path.abspath(__file__))
X = 'Size + Lev + ROA + Growth + TobinQ + CF + CFVol + NWC + Top1 + Age'


def st(p):
    return '***' if p < 0.01 else '**' if p < 0.05 else '*' if p < 0.1 else ''


def ushape(sub, fe):
    m = pf.feols(f'Cash ~ Pledge + Pledge2 + {X} | {fe}', data=sub.dropna(subset=['Cash', 'Pledge']),
                 vcov={'CRV1': 'stkcd'})
    t = m.tidy()
    b1, b2 = t.loc['Pledge', 'Estimate'], t.loc['Pledge2', 'Estimate']
    p1, p2 = t.loc['Pledge', 'Pr(>|t|)'], t.loc['Pledge2', 'Pr(>|t|)']
    V = np.asarray(m._vcov)
    names = list(m._coefnames)
    i1, i2 = names.index('Pledge'), names.index('Pledge2')

    def slope(x):
        s = b1 + 2 * b2 * x
        return s, s / np.sqrt(V[i1, i1] + 4 * x * x * V[i2, i2] + 4 * x * V[i1, i2])

    s0, t0 = slope(0)
    s1, t1 = slope(1)
    ok = t0 < -1.645 and t1 > 1.645
    tp = -b1 / (2 * b2) if b2 > 0 else np.nan
    return (f'{b1:.4f}{st(p1)} | {b2:.4f}{st(p2)} | {tp:.2f} | {s0:.3f}（t={t0:.2f}） | {s1:.3f}（t={t1:.2f}） | '
            f'{"✅ 成立" if ok else "❌ 不成立"} | {m._N:,}')


def main(panel, out):
    d = pd.read_csv(panel, dtype={'stkcd': str})
    d['ipo_age'] = (d['year'] - d['listyear']).clip(0, 40).astype(int)
    ind = d['ind'].fillna('Z')
    d['ind2'] = np.where(ind.str[:1] == 'C', ind.str[:2], ind.str[:1])  # 制造业按二级，与原文一致
    d['Pledge2'] = d['Pledge'] ** 2
    d = d[d['year'] > d['listyear']]  # 原文剔除上市当年

    L = ['# 复现李常青等（2018b）的 U 型结论\n',
         '原文：2013—2015 年季度数据，混合 OLS + 行业 + 季度虚拟变量；一次项 −0.16***、平方项 +0.15***，拐点约 55%。\n',
         '本表为年度数据；「U 型检验」采用 Lind 和 Mehlum（2010）的端点斜率检验：'
         '质押比例 = 0 处斜率显著为负、= 1 处斜率显著为正（单侧 10%）才算成立。标准误按公司聚类。\n',
         '| 样本 / 设定 | 一次项 | 平方项 | 拐点 | 斜率（Pledge=0） | 斜率（Pledge=1） | U 型检验 | N |',
         '|---|---|---|---|---|---|---|---|']
    specs = [
        ('**原文口径**：2013—2015，行业 + 年度', d[d['year'].between(2013, 2015)], 'ind2 + year'),
        ('2007—2015，行业 + 年度', d[d['year'] <= 2015], 'ind2 + year'),
        ('2016—2025，行业 + 年度', d[d['year'] >= 2016], 'ind2 + year'),
        ('全样本，行业 + 年度', d, 'ind2 + year'),
        ('**2013—2015，公司 + 年度 FE**', d[d['year'].between(2013, 2015)], 'stkcd + year'),
        ('**全样本，公司 + 年度 FE**', d, 'stkcd + year'),
        ('全样本，公司 + 年度 + 上市年数 FE', d, 'stkcd + year + ipo_age'),
        ('非国企，行业 + 年度', d[d['SOE'] == 0], 'ind2 + year'),
        ('非国企，公司 + 年度 FE', d[d['SOE'] == 0], 'stkcd + year'),
        ('国企，行业 + 年度', d[d['SOE'] == 1], 'ind2 + year'),
    ]
    for lab, sub, fe in specs:
        L.append(f'| {lab} | {ushape(sub, fe)} |')
    pl = d.loc[d['Pledge'] > 0, 'Pledge']
    L.append('')
    L.append(f'有质押的公司年度中，质押比例中位数 {pl.median():.2f}，超过 55% 的占 {(pl > 0.55).mean():.1%}。\n')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w', encoding='utf-8').write('\n'.join(L))
    print('\n'.join(L))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--panel', default=os.path.join(HERE, '..', 'data_clean', 'panel.csv'))
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'results', '复现李常青2018.md'))
    a = ap.parse_args()
    main(a.panel, a.out)
