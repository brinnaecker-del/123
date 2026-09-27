"""
第三步：机制检验（H2a 平仓压力、H2a/H2b 现金边际价值）。

    python mechanism.py --raw ../data_raw --panel ../data_clean/panel.csv --out ../results/机制检验.md

需要的原始文件（除 build_panel.py 用到的以外）：
    PLED_TRDDETL   股东股权质押情况明细表（逐笔质押，含起始日期）
    TRD_Mnth       月个股回报率文件（Mretwd）

一、平仓压力 Pressure（参照胡聪慧等，2020）
    对第一大股东每一笔在年末仍未解押的质押，用考虑现金红利再投资的月回报率构造累计收益指数，
    以质押起始月为基期，计算当年各月「股价 / 质押时股价」的最小值；
    预警线 = 质押率 40% ×（1 + 年利率 10% × 已质押年数）× 预警线 160%，
    即股价跌到质押时的 64%（加上利息）以下视为触及预警线。
    Pressure = 当年触及预警线的质押股数 / 第一大股东全部未解押质押股数（0—1）。
    说明：累计收益指数含分红，会略微高估股价，从而低估 Pressure。

二、现金边际价值（Faulkender 和 Wang，2006）
    r_it − R_it^B = γ1·ΔC/M + γ2·(ΔC/M)×Pledge + γ3·Pledge + ΔE/M + ΔNA/M + C_{t−1}/M + L + L·ΔC/M + C_{t−1}/M·ΔC/M + FE
    R^B：按上年末规模与账面市值比各分 5 组（共 25 组）的等权年收益；
    M：上年末总市值；L：市场杠杆 = 负债 /（负债 + 市值）。
    原文中的 ΔRD、ΔI、ΔD、NF 暂缺数据，未纳入。
    γ2 显著为负 → 高质押公司的现金被外部投资者打折，支持 H2b；γ2 不显著为负 → 支持 H2a。
"""
import argparse
import os
import sys
import warnings

import numpy as np
import pandas as pd
import pyfixest as pf

warnings.filterwarnings('ignore')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_panel as B  # noqa: E402
from pledge_from_csmar import _norm  # noqa: E402

CONTROLS = ['Size', 'Lev', 'ROA', 'Growth', 'TobinQ', 'CF', 'CFVol', 'NWC', 'Top1']
PLEDGE_RATE, RATE, WARN = 0.40, 0.10, 1.60


def stars(p):
    return '***' if p < 0.01 else '**' if p < 0.05 else '*' if p < 0.1 else ''


def fit(fml, data, key):
    m = pf.feols(fml, data=data, vcov={'CRV1': 'stkcd'})
    t = m.tidy().loc[key]
    return t['Estimate'], t['Std. Error'], t['Pr(>|t|)'], int(m._N)


def row(label, fmlkey, res):
    b, se, p, n = res
    return f'| {label} | `{fmlkey}` | {b:.4f}{stars(p)} | ({se:.4f}) | {p:.3f} | {n:,} |'


def monthly_index(raw):
    m = pd.read_csv(B.find(raw, 'TRD_Mnth')[0], dtype=str)
    m = m[pd.to_numeric(m['Stkcd'], errors='coerce').notna()].copy()
    m['stkcd'] = m['Stkcd'].str.zfill(6)
    m['ym'] = pd.PeriodIndex(m['Trdmnt'], freq='M')
    m['r'] = pd.to_numeric(m['Mretwd'], errors='coerce')
    m = m.dropna(subset=['ym']).sort_values(['stkcd', 'ym'])
    m['idx'] = (1 + m['r'].fillna(0)).groupby(m['stkcd']).cumprod()
    return m[['stkcd', 'ym', 'r', 'idx']]


def pressure(raw, mret):
    d = B.load(raw, 'detl')
    d['date'] = pd.to_datetime(d['ChangeDate'], errors='coerce')
    d['start'] = pd.to_datetime(d['StartDate'], errors='coerce')
    d['seq'] = pd.to_numeric(d['EventSeq'], errors='coerce')
    d['after'] = pd.to_numeric(d['NumAfterChg'], errors='coerce').fillna(0)
    d['name'] = _norm(d['Pledgor'])
    d = d.dropna(subset=['date']).sort_values(['EventID', 'date', 'seq'])
    d['year'] = d['date'].dt.year
    first = d.groupby('EventID').agg(stkcd=('stkcd', 'first'), name=('name', 'first'),
                                     start=('start', 'first'), date0=('date', 'first'))
    first['start'] = first['start'].fillna(first['date0'])
    last = d.groupby(['EventID', 'year']).tail(1)[['EventID', 'year', 'after']]

    # 每笔质押在各年末的剩余股数（向后填充到下一次变动）
    rows = []
    for eid, g in last.groupby('EventID'):
        ys, a = g['year'].values, g['after'].values
        for i, y in enumerate(ys):
            for yy in range(y, ys[i + 1] if i + 1 < len(ys) else 2026):
                rows.append((eid, yy, a[i]))
    ev = pd.DataFrame(rows, columns=['EventID', 'year', 'bal'])
    ev = ev[(ev['bal'] > 0) & (ev['year'] >= 2007) & (ev['year'] <= 2025)].join(first, on='EventID')

    h = B.load(raw, 'hld')
    c = B.CFG['hld']
    h = h[h[c['rank']].astype(str).str.strip().isin(['1', '1.0'])]
    h = pd.DataFrame({'stkcd': h['stkcd'], 'year': pd.to_datetime(h[c['date']], errors='coerce').dt.year,
                      'top1': _norm(h[c['name']])}).dropna().astype({'year': int})
    ev = ev.merge(h, on=['stkcd', 'year'])
    ev = ev[ev['name'] == ev['top1']].copy()

    # 基期指数：质押起始月的上月末（即质押时的价格水平）
    ev['ym0'] = ev['start'].dt.to_period('M') - 1
    base = mret.rename(columns={'ym': 'ym0', 'idx': 'idx0'})[['stkcd', 'ym0', 'idx0']]
    ev = ev.merge(base, on=['stkcd', 'ym0'], how='left')
    mret = mret.assign(year=mret['ym'].dt.year)
    mm = ev[['EventID', 'stkcd', 'year', 'ym0', 'idx0', 'start']].merge(mret[['stkcd', 'year', 'ym', 'idx']], on=['stkcd', 'year'])
    mm = mm[mm['ym'] > mm['ym0']]
    held = (mm['ym'].dt.to_timestamp(how='end') - mm['start']).dt.days.clip(lower=0) / 365
    mm['warn'] = PLEDGE_RATE * (1 + RATE * held) * WARN
    mm['hit'] = (mm['idx'] / mm['idx0']) < mm['warn']
    hit = mm.groupby(['EventID', 'year'])['hit'].any().rename('hit')
    ev = ev.join(hit, on=['EventID', 'year'])
    ev['hit'] = ev['hit'].fillna(False).astype(float)
    ev = ev.dropna(subset=['idx0'])
    out = ev.groupby(['stkcd', 'year']).apply(
        lambda g: pd.Series({'Pressure': np.average(g['hit'], weights=g['bal']), 'n_ev': len(g)}))
    print(f'平仓压力：{len(ev)} 笔「第一大股东 × 年」质押，覆盖 {len(out)} 个公司年度')
    return out.reset_index()


def cash_value(raw, panel, mret):
    bs = B.annual_fs(raw, 'bs', ['cash', 'ta', 'tl'])
    inc = B.annual_fs(raw, 'is', ['ni'])
    mv = B.load(raw, 'mv')
    c = B.CFG['mv']
    mv = pd.DataFrame({'stkcd': mv['stkcd'], 'year': pd.to_numeric(mv[c['year']], errors='coerce'),
                       'M': pd.to_numeric(mv[c['mv']], errors='coerce') * c['mv_unit']}).dropna().astype({'year': int})
    f = bs.merge(inc, on=['stkcd', 'year'], how='left').merge(mv, on=['stkcd', 'year'], how='left')
    f = f.sort_values(['stkcd', 'year'])
    g = f.groupby('stkcd')
    ok = g['year'].diff() == 1
    lag = lambda v: g[v].shift(1).where(ok)  # noqa: E731
    f['M1'] = lag('M')
    f['dC'] = (f['cash'] - lag('cash')) / f['M1']
    f['dE'] = (f['ni'] - lag('ni')) / f['M1']
    f['dNA'] = ((f['ta'] - f['cash']) - (lag('ta') - lag('cash'))) / f['M1']
    f['C1'] = lag('cash') / f['M1']
    f['Lm'] = f['tl'] / (f['tl'] + f['M'])
    f['BM1'] = (lag('ta') - lag('tl')) / f['M1']

    ann = mret.assign(year=mret['ym'].dt.year).groupby(['stkcd', 'year'])['r'].agg(
        ret=lambda s: np.prod(1 + s.dropna()) - 1, nm='count').reset_index()
    ann = ann[ann['nm'] >= 10]
    f = f.merge(ann[['stkcd', 'year', 'ret']], on=['stkcd', 'year'], how='inner')
    f = f[f['stkcd'].isin(panel['stkcd'].unique())]

    # 25 个规模 × 账面市值比组合的等权收益作为基准
    f = f[(f['M1'] > 0) & (f['BM1'] > 0)].copy()
    f['sz'] = f.groupby('year')['M1'].transform(lambda s: pd.qcut(s.rank(method='first'), 5, labels=False))
    f['bm'] = f.groupby('year')['BM1'].transform(lambda s: pd.qcut(s.rank(method='first'), 5, labels=False))
    f['RB'] = f.groupby(['year', 'sz', 'bm'])['ret'].transform('mean')
    f['exret'] = f['ret'] - f['RB']
    for v in ['exret', 'dC', 'dE', 'dNA', 'C1', 'Lm']:
        f[v] = B.winsor(f[v])
    f = f.merge(panel[['stkcd', 'year', 'Pledge', 'SOE', 'ind', 'listyear']], on=['stkcd', 'year'], how='inner')
    f['dC_Pledge'] = f['dC'] * f['Pledge']
    f['dC_L'] = f['dC'] * f['Lm']
    f['dC_C1'] = f['dC'] * f['C1']
    f['ind1'] = f['ind'].fillna('Z').str[:1]
    return f


def main(raw, panel_path, out):
    panel = pd.read_csv(panel_path, dtype={'stkcd': str})
    panel['ipo_age'] = (panel['year'] - panel['listyear']).clip(0, 40).astype(int)
    mret = monthly_index(raw)
    X = ' + '.join(CONTROLS)
    L = ['# 机制检验\n', '被解释变量、样本与固定效应见各表说明；标准误按公司聚类。*** p<0.01，** p<0.05，* p<0.1。\n']

    # ---------- H2a 平仓压力 ----------
    pr = pressure(raw, mret)
    d = panel.merge(pr, on=['stkcd', 'year'], how='left')
    d['Pressure'] = d['Pressure'].fillna(0)
    d = d.sort_values(['stkcd', 'year'])
    g = d.groupby('stkcd')
    d['L_Pressure'] = g['Pressure'].shift(1).where(g['year'].diff() == 1)
    d['Pressure_Dum'] = (d['Pressure'] > 0).astype(int)
    base = d.dropna(subset=['Cash', 'Pledge'] + CONTROLS)
    pl = base[base['Pledge'] > 0]
    L.append('## 一、H2a：平仓压力\n')
    L.append(f'有质押的公司年度中，当年触及预警线的比例（Pressure>0）：**{(pl["Pressure"] > 0).mean():.1%}**；'
             '按年：' + '，'.join(f'{y}年 {v:.0%}' for y, v in pl.groupby('year')['Pressure'].apply(lambda s: (s > 0).mean()).items()
                                if y in (2008, 2012, 2015, 2016, 2018, 2019, 2022, 2024)) + '。\n')
    L.append('被解释变量为 Cash；公司 + 年度 + 上市年数固定效应。\n')
    L.append('| 设定 | 关键变量 | 系数 | 标准误 | p 值 | N |\n|---|---|---|---|---|---|')
    fe = 'stkcd + year + ipo_age'
    L.append(row('全样本：Pledge × Pressure', 'Pledge:Pressure',
                 fit(f'Cash ~ Pledge + Pressure + Pledge:Pressure + {X} | {fe}', base, 'Pledge:Pressure')))
    L.append(row('全样本：Pressure 主效应', 'Pressure', fit(f'Cash ~ Pledge + Pressure + {X} | {fe}', base, 'Pressure')))
    L.append(row('质押公司子样本：Pressure', 'Pressure', fit(f'Cash ~ Pledge + Pressure + {X} | {fe}', pl, 'Pressure')))
    L.append(row('质押公司子样本：是否触及预警线', 'Pressure_Dum',
                 fit(f'Cash ~ Pledge + Pressure_Dum + {X} | {fe}', pl, 'Pressure_Dum')))
    lp = pl.dropna(subset=['L_Pressure'])
    L.append(row('质押公司子样本：上年 Pressure', 'L_Pressure', fit(f'Cash ~ Pledge + L_Pressure + {X} | {fe}', lp, 'L_Pressure')))
    L.append('')
    L.append('H2a 预测 Pressure（或其交乘项）为正：越接近平仓线，大股东越倾向于推动公司储备现金。\n')

    # ---------- 现金边际价值 ----------
    f = cash_value(raw, panel, mret)
    L.append('## 二、现金边际价值（Faulkender 和 Wang，2006）\n')
    L.append(f'样本 {len(f):,} 个公司年度。被解释变量为股票年度超额收益（减去 25 个规模 × 账面市值比组合的等权收益）；'
             '解释变量均除以上年末市值。\n')
    L.append('| 设定 | 关键变量 | 系数 | 标准误 | p 值 | N |\n|---|---|---|---|---|---|')
    Z = 'dC + dE + dNA + C1 + Lm + dC_L + dC_C1 + Pledge'
    for lab, fe_, sub in [('行业 + 年度 FE', 'ind1 + year', f), ('公司 + 年度 FE', 'stkcd + year', f),
                          ('行业 + 年度 FE，2016—2025', 'ind1 + year', f[f['year'] >= 2016]),
                          ('行业 + 年度 FE，民营企业', 'ind1 + year', f[f['SOE'] == 0])]:
        L.append(row(f'ΔC × Pledge（{lab}）', 'dC_Pledge', fit(f'exret ~ {Z} + dC_Pledge | {fe_}', sub, 'dC_Pledge')))
    b, se, p, n = fit(f'exret ~ {Z} + dC_Pledge | ind1 + year', f, 'dC')
    L.append('')
    L.append(f'参照：ΔC 主效应（行业 + 年度 FE）为 {b:.3f}（p = {p:.3f}），即一元现金的边际价值约 {b:.2f} 元'
             '（未与杠杆、现金存量交乘时的解读需结合均值计算）。\n')
    L.append('γ2（ΔC × Pledge）显著为负 → 高质押公司的现金被外部投资者打折，支持 H2b（掏空）；'
             '不显著为负 → 支持 H2a。\n')

    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w', encoding='utf-8').write('\n'.join(L))
    print('已写出', out)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw', default=os.path.join(HERE, '..', 'data_raw'))
    ap.add_argument('--panel', default=os.path.join(HERE, '..', 'data_clean', 'panel.csv'))
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'results', '机制检验.md'))
    a = ap.parse_args()
    main(a.raw, a.panel, a.out)
