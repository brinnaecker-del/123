"""
深化分析一：按质权人类型区分场内质押（证券公司）与场外质押（银行、信托、资管等）。

动机：
  1. 场内股票质押由证券公司逐日盯市，跌破平仓线可强制卖出；银行等场外质押的处置更依赖协商，平仓约束较弱。
     若风险规避说成立，其效应应在场内质押中最强。
  2. 2018 年质押新规只约束场内股票质押式回购。以场外质押为"安慰剂"，可以更干净地识别新规效应。

    python deepen_pledgee.py --raw <原始数据目录> --panel <panel.csv> --out <结果.md>
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd
import pyfixest as pf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_panel as B  # noqa: E402
import mechanism as M  # noqa: E402
from pledge_from_csmar import _norm  # noqa: E402
from preregression import CONTROLS  # noqa: E402

BROKER = '2'  # PledgeeCatergoryCode：2 = 证券公司


def event_balances(raw):
    """每笔质押（EventID）在各年末的剩余股数，附质权人类型；只保留第一大股东的质押。"""
    d = B.load(raw, 'detl')
    d['date'] = pd.to_datetime(d['ChangeDate'], errors='coerce')
    d['start'] = pd.to_datetime(d['StartDate'], errors='coerce')
    d['end'] = pd.to_datetime(d['EndDate'], errors='coerce')
    d['seq'] = pd.to_numeric(d['EventSeq'], errors='coerce')
    d['after'] = pd.to_numeric(d['NumAfterChg'], errors='coerce').fillna(0)
    d['name'] = _norm(d['Pledgor'])
    d['broker'] = (d['PledgeeCatergoryCode'].astype(str).str.split(',').str[0].str.strip() == BROKER)
    d = d.dropna(subset=['date']).sort_values(['EventID', 'date', 'seq'])
    d['year'] = d['date'].dt.year
    first = d.groupby('EventID').agg(stkcd=('stkcd', 'first'), name=('name', 'first'), broker=('broker', 'first'),
                                     start=('start', 'first'), date0=('date', 'first'))
    first['start'] = first['start'].fillna(first['date0'])
    last = d.groupby(['EventID', 'year']).tail(1)
    rows = []
    for eid, g in last.groupby('EventID'):
        ys, a, fl, en = g['year'].values, g['after'].values, g['IsLastestRecord'].values, g['end'].values
        for i, y in enumerate(ys):
            for yy in range(y, ys[i + 1] if i + 1 < len(ys) else 2026):
                expired = fl[i] != 'O' and not pd.isna(en[i]) and pd.Timestamp(en[i]) < pd.Timestamp(f'{yy - 1}-01-01')
                rows.append((eid, yy, 0.0 if expired else a[i]))
    ev = pd.DataFrame(rows, columns=['EventID', 'year', 'bal'])
    ev = ev[(ev['bal'] > 0) & ev['year'].between(2007, 2025)].join(first, on='EventID')

    c = B.CFG['hld']
    h = B.load(raw, 'hld')
    h = h[h[c['rank']].astype(str).str.strip().isin(['1', '1.0'])]
    h = pd.DataFrame({'stkcd': h['stkcd'], 'year': pd.to_datetime(h[c['date']], errors='coerce').dt.year,
                      'top1': _norm(h[c['name']]), 'sh': pd.to_numeric(h[c['shares']], errors='coerce')})
    h = h.dropna(subset=['year']).astype({'year': int}).drop_duplicates(['stkcd', 'year'])
    ev = ev.merge(h, on=['stkcd', 'year'])
    return ev[ev['name'] == ev['top1']].copy(), h


def split_ratios(ev, h):
    g = ev.groupby(['stkcd', 'year', 'broker'])['bal'].sum().unstack(fill_value=0)
    g.columns = ['bal_N' if not c else 'bal_B' for c in g.columns]
    out = h.set_index(['stkcd', 'year']).join(g).reset_index().fillna({'bal_B': 0, 'bal_N': 0})
    out['Pledge_B'] = (out['bal_B'] / out['sh']).clip(0, 1)
    out['Pledge_N'] = (out['bal_N'] / out['sh']).clip(0, 1)
    return out[['stkcd', 'year', 'Pledge_B', 'Pledge_N']]


def split_pressure(ev, mret):
    ev = ev.copy()
    ev['ym0'] = ev['start'].dt.to_period('M') - 1
    base = mret.rename(columns={'ym': 'ym0', 'idx': 'idx0'})[['stkcd', 'ym0', 'idx0']]
    ev = ev.merge(base, on=['stkcd', 'ym0'], how='left').dropna(subset=['idx0'])
    mr = mret.assign(year=mret['ym'].dt.year)
    mm = ev[['EventID', 'stkcd', 'year', 'ym0', 'idx0', 'start']].merge(mr[['stkcd', 'year', 'ym', 'idx']], on=['stkcd', 'year'])
    mm = mm[mm['ym'] > mm['ym0']]
    held = (mm['ym'].dt.to_timestamp(how='end') - mm['start']).dt.days.clip(lower=0) / 365
    mm['hit'] = (mm['idx'] / mm['idx0']) < M.PLEDGE_RATE * (1 + M.RATE * held) * M.WARN
    hit = mm.groupby(['EventID', 'year'])['hit'].any().rename('hit')
    ev = ev.join(hit, on=['EventID', 'year'])
    ev['hit'] = ev['hit'].fillna(False).astype(float)
    ev['hb'] = ev['hit'] * ev['bal']
    s = ev.groupby(['stkcd', 'year', 'broker'])[['hb', 'bal']].sum()
    s['p'] = s['hb'] / s['bal']
    p = s['p'].unstack()
    p.columns = ['Pressure_N' if not c else 'Pressure_B' for c in p.columns]
    return p.reset_index()


def fit(fml, data, keys):
    r = pf.feols(fml, data=data, vcov={'CRV1': 'stkcd'})
    t = r.tidy()
    return {k: (t.loc[k, 'Estimate'], t.loc[k, 'Std. Error'], t.loc[k, 'Pr(>|t|)']) for k in keys}, r._N


def stars(p):
    return '***' if p < .01 else '**' if p < .05 else '*' if p < .1 else ''


def fmt(v):
    b, se, p = v
    return f'{b:+.4f}{stars(p)} ({se:.4f})'


def main(raw, panel_path, out):
    panel = pd.read_csv(panel_path, dtype={'stkcd': str})
    panel['ipo_age'] = (panel['year'] - panel['listyear']).clip(0, 40).astype(int)
    ev, h = event_balances(raw)
    mret = M.monthly_index(raw)
    d = panel.merge(split_ratios(ev, h), on=['stkcd', 'year'], how='left').merge(split_pressure(ev, mret), on=['stkcd', 'year'], how='left')
    for c in ['Pledge_B', 'Pledge_N']:
        d[c] = d[c].fillna(0)
    X = ' + '.join(CONTROLS)
    base = d.dropna(subset=['Cash', 'Pledge'] + CONTROLS).copy()
    L = ['# 深化分析一：场内质押（证券公司）与场外质押\n',
         '被解释变量为 Cash；标准误按公司聚类；括号内为标准误。*** p<0.01，** p<0.05，* p<0.1。\n']

    # 描述
    L.append('## 一、质押结构\n')
    yr = base.groupby('year')[['Pledge_B', 'Pledge_N']].mean()
    L.append('| 年份 | 场内（证券公司）质押比例均值 | 场外质押比例均值 |\n|---|---|---|')
    for y in [2008, 2012, 2013, 2015, 2017, 2018, 2019, 2021, 2023, 2025]:
        if y in yr.index:
            L.append(f'| {y} | {yr.loc[y, "Pledge_B"]:.3f} | {yr.loc[y, "Pledge_N"]:.3f} |')
    L.append(f'\n统计表口径 Pledge 与（场内 + 场外）之和的相关系数：{base["Pledge"].corr(base["Pledge_B"] + base["Pledge_N"]):.3f}\n')

    # 基准拆分
    L.append('## 二、基准回归：场内与场外质押分别对现金的影响\n')
    L.append('| 设定 | 场内质押 Pledge_B | 场外质押 Pledge_N | N |\n|---|---|---|---|')
    for lab, fe, sub in [('公司 + 年度 FE', 'stkcd + year', base),
                         ('公司 + 年度 + 上市年数 FE', 'stkcd + year + ipo_age', base),
                         ('2013 年后（场内质押业务开通后）', 'stkcd + year + ipo_age', base[base.year >= 2013]),
                         ('上市满 5 年', 'stkcd + year', base[base.ipo_age >= 5])]:
        v, n = fit(f'Cash ~ Pledge_B + Pledge_N + {X} | {fe}', sub, ['Pledge_B', 'Pledge_N'])
        L.append(f'| {lab} | {fmt(v["Pledge_B"])} | {fmt(v["Pledge_N"])} | {n} |')

    # 平仓压力拆分
    L.append('\n## 三、平仓压力：场内与场外分别计算\n')
    L.append('Pressure_B / Pressure_N 分别为场内、场外质押中触及预警线的股数占比（无该类质押记为 0，并加入是否有该类质押的虚拟变量）。控制公司、年度与上市年数固定效应。\n')
    pb = base.copy()
    pb['HasB'] = pb['Pressure_B'].notna().astype(int)
    pb['HasN'] = pb['Pressure_N'].notna().astype(int)
    pb[['Pressure_B', 'Pressure_N']] = pb[['Pressure_B', 'Pressure_N']].fillna(0)
    L.append('| 样本 | 场内平仓压力 Pressure_B | 场外平仓压力 Pressure_N | N |\n|---|---|---|---|')
    for lab, sub in [('全样本', pb), ('2013 年后', pb[pb.year >= 2013]), ('上市满 5 年', pb[pb.ipo_age >= 5])]:
        v, n = fit(f'Cash ~ Pledge + Pressure_B + Pressure_N + HasB + HasN + {X} | stkcd + year + ipo_age', sub,
                   ['Pressure_B', 'Pressure_N'])
        L.append(f'| {lab} | {fmt(v["Pressure_B"])} | {fmt(v["Pressure_N"])} | {n} |')
    L.append('\n风险规避说预测：场内质押（强制平仓约束更强）的平仓压力系数应为正且大于场外。\n')

    # DID
    L.append('## 四、2018 年新规：以场外质押为安慰剂\n')
    L.append('新规只约束场内股票质押式回购。PledgePre_B / PledgePre_N 为 2016—2017 年第一大股东场内 / 场外质押比例均值，Post 为 2018 年及以后。控制公司与年度固定效应，样本 2013—2025 年。\n')
    pre = base[base.year.isin([2016, 2017])].groupby('stkcd')[['Pledge_B', 'Pledge_N']].mean().add_prefix('Pre_')
    dd = base[base.year >= 2013].join(pre, on='stkcd').dropna(subset=['Pre_Pledge_B'])
    dd['Post'] = (dd.year >= 2018).astype(int)
    dd['DID_B'] = dd['Pre_Pledge_B'] * dd['Post']
    dd['DID_N'] = dd['Pre_Pledge_N'] * dd['Post']
    L.append('| 被解释变量 | PledgePre_B × Post | PledgePre_N × Post | N |\n|---|---|---|---|')
    for y, lab in [('Pledge_B', '场内质押比例'), ('Pledge_N', '场外质押比例'), ('Pledge', '总质押比例'), ('Cash', '现金持有 Cash')]:
        ctrl = '' if y != 'Cash' else f' + {X}'
        v, n = fit(f'{y} ~ DID_B + DID_N{ctrl} | stkcd + year', dd, ['DID_B', 'DID_N'])
        L.append(f'| {lab} | {fmt(v["DID_B"])} | {fmt(v["DID_N"])} | {n} |')

    # 动态效应
    L.append('\n### 动态效应（以 2017 年为基期）\n')
    L.append('| 年份 | 对场内质押比例 | 对现金持有 |\n|---|---|---|')
    ys = [y for y in range(2013, 2026) if y != 2017]
    for y in ys:
        dd[f'e{y}'] = dd['Pre_Pledge_B'] * (dd.year == y)
    terms = ' + '.join(f'e{y}' for y in ys)
    v1, _ = fit(f'Pledge_B ~ {terms} | stkcd + year', dd, [f'e{y}' for y in ys])
    v2, _ = fit(f'Cash ~ {terms} + {X} | stkcd + year', dd, [f'e{y}' for y in ys])
    for y in ys:
        L.append(f'| {y} | {fmt(v1[f"e{y}"])} | {fmt(v2[f"e{y}"])} |')
    L.append('\n说明：对场内质押比例的前期系数反映 2013 年后场内质押从无到有的扩张（处理强度本身由 2016—2017 年质押比例定义），'
             '不能作为平行趋势检验；对现金的前期系数中 2015 年显著为负（当年股灾），平行趋势不完全满足，DID 结论需谨慎解读。\n')

    open(out, 'w', encoding='utf-8').write('\n'.join(L))
    print('已写出', out)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw', default=os.path.join(HERE, '..', 'data_raw'))
    ap.add_argument('--panel', default=os.path.join(HERE, '..', 'data_clean', 'panel.csv'))
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'results', '深化分析一-场内与场外质押.md'))
    a = ap.parse_args()
    main(a.raw, a.panel, a.out)
