"""
第二步：预回归。读 panel.csv，跑基准回归与几项快速检验，结果写到 ../results/预回归结果.md。

用法：
    python preregression.py                      # 默认读 ../data_clean/panel.csv
    python preregression.py --panel 文件 --out 文件

所有回归：公司 + 年度固定效应，标准误按公司聚类（等价于 Stata: reghdfe ..., absorb(stkcd year) vce(cluster stkcd)）。
"""
import argparse
import os
import warnings

import numpy as np
import pandas as pd
import pyfixest as pf

warnings.filterwarnings('ignore')
HERE = os.path.dirname(os.path.abspath(__file__))
CONTROLS = ['Size', 'Lev', 'ROA', 'Growth', 'TobinQ', 'CF', 'CFVol', 'NWC', 'Age', 'Top1']


def stars(p):
    return '***' if p < 0.01 else '**' if p < 0.05 else '*' if p < 0.1 else ''


def fit(formula, data, key):
    m = pf.feols(formula, data=data, vcov={'CRV1': 'stkcd'})
    t = m.tidy()
    b, se, p = t.loc[key, 'Estimate'], t.loc[key, 'Std. Error'], t.loc[key, 'Pr(>|t|)']
    return dict(b=b, se=se, p=p, n=int(m._N), r2=getattr(m, '_r2_within', np.nan), model=m)


def row(label, r, key):
    return f"| {label} | `{key}` | {r['b']:.4f}{stars(r['p'])} | ({r['se']:.4f}) | {r['p']:.3f} | {r['n']:,} | {r['r2']:.3f} |"


def main(panel, out):
    df = pd.read_csv(panel, dtype={'stkcd': str})
    df = df.sort_values(['stkcd', 'year'])
    df['ind1'] = df['ind'].fillna('NA').str[:1]
    df['ind_year'] = df['ind1'] + '_' + df['year'].astype(str)
    g = df.groupby('stkcd')
    consec = g['year'].diff() == 1
    df['L_Pledge'] = g['Pledge'].shift(1).where(consec)
    df['L_SA'] = g['SA'].shift(1).where(consec)
    df['HighFC'] = (df['L_SA'] > df.groupby('year')['L_SA'].transform('median')).astype(float).where(df['L_SA'].notna())
    df['Pledge_c'] = df['Pledge'] - df['Pledge'].mean()

    X = ' + '.join(CONTROLS)
    base = df.dropna(subset=['Cash', 'Pledge'] + CONTROLS)
    L = []
    L.append('# 预回归结果\n')
    L.append(f'数据：`{os.path.relpath(panel, os.path.dirname(out))}`；样本 {len(base):,} 个公司年度、{base.stkcd.nunique():,} 家公司，'
             f'{int(base.year.min())}—{int(base.year.max())} 年。\n')
    L.append('被解释变量 Cash = 货币资金 /（总资产 − 货币资金）；均控制公司与年度固定效应，括号内为公司聚类标准误。'
             '*** p<0.01，** p<0.05，* p<0.1。\n')

    # ---------- 描述性统计 ----------
    L.append('## 1. 描述性统计\n')
    L.append('| 变量 | N | 均值 | 标准差 | 最小值 | 中位数 | 最大值 |\n|---|---|---|---|---|---|---|')
    for v in ['Cash', 'Pledge', 'Pledge_Dum', 'SA', 'SOE'] + [c for c in CONTROLS if c not in ('Age',)] + ['Age']:
        s = base[v].dropna()
        L.append(f'| {v} | {len(s):,} | {s.mean():.4f} | {s.std():.4f} | {s.min():.4f} | {s.median():.4f} | {s.max():.4f} |')
    L.append('')

    yr = base.groupby('year').agg(质押公司占比=('Pledge_Dum', 'mean'), 平均质押比例=('Pledge', 'mean'), 平均Cash=('Cash', 'mean'))
    L.append('**质押随年份的变化**（2018 年前后应能看到明显拐点）\n')
    L.append('| 年份 | 质押公司占比 | 平均质押比例 | 平均 Cash |\n|---|---|---|---|')
    for y, r in yr.iterrows():
        L.append(f'| {int(y)} | {r.iloc[0]:.3f} | {r.iloc[1]:.3f} | {r.iloc[2]:.3f} |')
    L.append('')

    # ---------- 基准回归 ----------
    L.append('## 2. 基准回归（H1a／H1b）\n')
    L.append('| 设定 | 解释变量 | 系数 | 标准误 | p 值 | N | 组内 R² |\n|---|---|---|---|---|---|---|')
    r1 = fit('Cash ~ Pledge | stkcd + year', base, 'Pledge')
    L.append(row('(1) 无控制变量', r1, 'Pledge'))
    r2 = fit(f'Cash ~ Pledge + {X} | stkcd + year', base, 'Pledge')
    L.append(row('(2) 加控制变量（基准）', r2, 'Pledge'))
    r3 = fit(f'Cash ~ Pledge_Dum + {X} | stkcd + year', base, 'Pledge_Dum')
    L.append(row('(3) 是否质押虚拟变量', r3, 'Pledge_Dum'))
    lag = base.dropna(subset=['L_Pledge'])
    r4 = fit(f'Cash ~ L_Pledge + {X} | stkcd + year', lag, 'L_Pledge')
    L.append(row('(4) 质押比例滞后一期', r4, 'L_Pledge'))
    r5 = fit(f'Cash ~ Pledge + {X} | stkcd + ind_year', base, 'Pledge')
    L.append(row('(5) 公司 + 行业×年度 FE', r5, 'Pledge'))
    r6 = fit(f'Cash2 ~ Pledge + {X} | stkcd + year', base, 'Pledge')
    L.append(row('(6) Cash2 = 货币资金/总资产', r6, 'Pledge'))
    if base['Pledge_Ratio2'].notna().sum() > 1000:
        r7 = fit(f'Cash ~ Pledge_Ratio2 + {X} | stkcd + year', base.dropna(subset=['Pledge_Ratio2']), 'Pledge_Ratio2')
        L.append(row('(7) 占总股本口径', r7, 'Pledge_Ratio2'))
    L.append('')
    t = r2['model'].tidy()
    L.append('<details><summary>基准设定 (2) 的控制变量系数</summary>\n')
    L.append('| 变量 | 系数 | 标准误 | p 值 |\n|---|---|---|---|')
    for k, r in t.iterrows():
        L.append(f"| {k} | {r['Estimate']:.4f}{stars(r['Pr(>|t|)'])} | ({r['Std. Error']:.4f}) | {r['Pr(>|t|)']:.3f} |")
    L.append('\n</details>\n')

    # ---------- 边界条件 ----------
    L.append('## 3. 边界条件（H3 融资约束、H4 产权性质）\n')
    L.append('| 设定 | 解释变量 | 系数 | 标准误 | p 值 | N | 组内 R² |\n|---|---|---|---|---|---|---|')
    fc = base.dropna(subset=['HighFC'])
    r = fit(f'Cash ~ Pledge_c + Pledge_c:HighFC + HighFC + {X} | stkcd + year', fc, 'Pledge_c:HighFC')
    L.append(row('H3：Pledge × 滞后一期高融资约束', r, 'Pledge_c:HighFC'))
    for lab, v in [('H4：民营企业', 0), ('H4：国有企业', 1)]:
        sub = base[base['SOE'] == v]
        if len(sub) > 500:
            L.append(row(lab, fit(f'Cash ~ Pledge + {X} | stkcd + year', sub, 'Pledge'), 'Pledge'))
    L.append('')
    if base['SOE'].notna().any():
        d = base.groupby('SOE').agg(N=('Pledge', 'size'), 质押公司占比=('Pledge_Dum', 'mean'), 平均质押比例=('Pledge', 'mean'),
                                    质押比例标准差=('Pledge', 'std'))
        L.append('**两组的质押分布**（国企组质押变异小，不显著不代表效应不存在）\n')
        L.append('| SOE | N | 质押公司占比 | 平均质押比例 | 质押比例标准差 |\n|---|---|---|---|---|')
        for k, r_ in d.iterrows():
            L.append(f'| {int(k)} | {int(r_.N):,} | {r_.iloc[1]:.3f} | {r_.iloc[2]:.3f} | {r_.iloc[3]:.3f} |')
        L.append('')
    sa = base[['SA', 'Size', 'Age']].corr().loc['SA']
    L.append(f'**SA 方向核验**：corr(SA, Size) = {sa.Size:.3f}，corr(SA, Age) = {sa.Age:.3f}。'
             '按原文含义两者都应为负（规模越大、上市越久，约束越弱）。若出现正值，先检查总资产单位是否为「元」。\n')

    # ---------- DID ----------
    L.append('## 4. 2018 年新规处理强度 DID（快速版）\n')
    pre = base[base.year.isin([2016, 2017])].groupby('stkcd')['Pledge'].mean().rename('PledgePre')
    dd = base.merge(pre, on='stkcd')
    dd = dd[(dd.year >= 2012) & (dd.listyear < 2016)].copy()
    dd['Post'] = (dd.year >= 2018).astype(int)
    dd['DID'] = dd['PledgePre'] * dd['Post']
    L.append('| 设定 | 解释变量 | 系数 | 标准误 | p 值 | N | 组内 R² |\n|---|---|---|---|---|---|---|')
    L.append(row('PledgePre × Post（2012—2025）', fit(f'Cash ~ DID + {X} | stkcd + year', dd, 'DID'), 'DID'))
    L.append(row('剔除 2018 年', fit(f'Cash ~ DID + {X} | stkcd + year', dd[dd.year != 2018], 'DID'), 'DID'))
    L.append(row('加行业×年度 FE', fit(f'Cash ~ DID + {X} | stkcd + ind_year', dd, 'DID'), 'DID'))
    fs = fit(f'Pledge ~ DID + {X} | stkcd + year', dd, 'DID')
    L.append(row('“第一阶段”：被解释变量换成 Pledge', fs, 'DID'))
    L.append('')
    ev_terms = []
    for y in range(2012, 2026):
        if y == 2017:
            continue
        c = f'ev_{y}'
        dd[c] = dd['PledgePre'] * (dd.year == y)
        ev_terms.append(c)
    em = pf.feols(f'Cash ~ {" + ".join(ev_terms)} + {X} | stkcd + year', data=dd, vcov={'CRV1': 'stkcd'}).tidy()
    L.append('**事件研究（以 2017 年为基期）**：新规前各年系数应不显著（平行趋势）\n')
    L.append('| 年份 | 系数 | 标准误 | p 值 |\n|---|---|---|---|')
    for y in range(2012, 2026):
        if y == 2017:
            L.append('| 2017 | 0（基期） | — | — |')
            continue
        r_ = em.loc[f'ev_{y}']
        L.append(f"| {y} | {r_['Estimate']:.4f}{stars(r_['Pr(>|t|)'])} | ({r_['Std. Error']:.4f}) | {r_['Pr(>|t|)']:.3f} |")
    L.append('')

    # ---------- 怎么读 ----------
    b = r2
    direction = '正' if b['b'] > 0 else '负'
    sig = '显著' if b['p'] < 0.1 else '不显著'
    L.append('## 5. 一句话结论（自动生成，需人工复核）\n')
    L.append(f'基准设定 (2) 中 Pledge 的系数为 {b["b"]:.4f}（p = {b["p"]:.3f}），方向为{direction}、统计上{sig}。'
             f'按样本标准差折算，质押比例上升一个标准差（{base.Pledge.std():.3f}），Cash 变化 {b["b"] * base.Pledge.std():.4f}，'
             f'约为 Cash 均值的 {b["b"] * base.Pledge.std() / base.Cash.mean() * 100:.1f}%。\n')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w', encoding='utf-8').write('\n'.join(L))
    print('已写出', out)
    print(f'基准系数 {b["b"]:.4f}  se {b["se"]:.4f}  p {b["p"]:.3f}  N {b["n"]}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--panel', default=os.path.join(HERE, '..', 'data_clean', 'panel.csv'))
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'results', '预回归结果.md'))
    a = ap.parse_args()
    main(a.panel, a.out)
