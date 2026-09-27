"""
用 CSMAR「股东股权质押统计表」(PLED_TRDSTAT) + 「十大股东文件」(HLD_Shareholders) 构造年末第一大股东质押比例。

PLED_TRDSTAT 每行是某出质方在某变动日期的一次变动：
  - ChangeNum（数量增减）带符号：新增质押、送转为正，解押为负；
  - 「全部解押」指某一笔质押全部解除，不是该出质方全部解押；
  - Pledtimes（质押笔数）为变动后仍处于质押状态的笔数，为空或 0 表示该出质方已无质押。
因此：对每个出质方按日期累加 ChangeNum，在 Pledtimes 为空/0 时归零，得到任意时点的未解押余额；
每年取 12-31 前最后一条记录作为年末余额，再按股东名称匹配当年第一大股东，除以其持股数。

在真实数据上的核验（2007—2025 年沪深 A 股）：
  - Pledtimes 归零时累加余额恰为 0 的比例约 81%；
  - 由此得到的「是否质押」与十大股东 S0303a 标识一致率约 95%。
"""
import numpy as np
import pandas as pd


def _norm(s):
    return (s.fillna('').astype(str).str.replace(r'\s', '', regex=True)
            .str.replace('（', '(').str.replace('）', ')'))


def pledgor_year_balance(pl):
    """pl：PLED_TRDSTAT 原表（已去掉 CSMAR 中文名/单位行）。返回 出质方×年 的年末未解押余额。"""
    d = pl.copy()
    d['stkcd'] = d['Symbol'].astype(float).astype(int).astype(str).str.zfill(6)
    d['row'] = np.arange(len(d))
    d['chg'] = pd.to_numeric(d['ChangeNum'], errors='coerce').fillna(0)
    d['pt'] = pd.to_numeric(d['Pledtimes'], errors='coerce')
    d['date'] = pd.to_datetime(d['ChangeDate'], errors='coerce')
    d = d.dropna(subset=['date']).sort_values(['stkcd', 'PledgorID', 'date', 'row'])

    bal = np.empty(len(d))
    k = 0
    for _, g in d.groupby(['stkcd', 'PledgorID'], sort=False):
        b = 0.0
        for c, pt in zip(g['chg'].values, g['pt'].values):
            b += c
            if np.isnan(pt) or pt == 0:
                b = 0.0
            b = max(b, 0.0)
            bal[k] = b
            k += 1
    d['bal'] = bal
    d['year'] = d['date'].dt.year
    d['name'] = _norm(d['Pledgor'])
    d['ctrl'] = d['RelationtoCom'].fillna('').str.contains('控股股东')

    last = d.groupby(['stkcd', 'PledgorID', 'year']).tail(1)
    names = d.groupby(['stkcd', 'PledgorID'])['name'].agg(lambda s: '|'.join(sorted(set(s))))
    ctrl = d.groupby(['stkcd', 'PledgorID'])['ctrl'].any()

    rows = []
    for (s, p), g in last.groupby(['stkcd', 'PledgorID']):
        ys, bs = g['year'].values, g['bal'].values
        for i, y in enumerate(ys):
            y_next = ys[i + 1] if i + 1 < len(ys) else 2026
            for yy in range(y, y_next):
                rows.append((s, p, yy, bs[i]))
    py = pd.DataFrame(rows, columns=['stkcd', 'pid', 'year', 'bal'])
    py = py.join(names.rename('names'), on=['stkcd', 'pid']).join(ctrl.rename('ctrl'), on=['stkcd', 'pid'])
    return py


def top1_pledge(pl, hld, cfg):
    """返回 stkcd, year, Pledge, Pledge_Dum, Pledge_Ratio2, Top1, Pledge_ctrl, Flag。"""
    c = cfg
    h = hld[hld[c['rank']].astype(str).str.strip().isin(['1', '1.0'])].copy()
    h['year'] = pd.to_datetime(h[c['date']], errors='coerce').dt.year
    h = h.dropna(subset=['year']).astype({'year': int})
    h['top1'] = _norm(h[c['name']])
    h['sh'] = pd.to_numeric(h[c['shares']], errors='coerce')
    h['Top1'] = pd.to_numeric(h[c['pct']], errors='coerce') / 100
    h['Flag'] = (h[c['flag']].astype(str).str.strip().str.replace('.0', '', regex=False) == c['flag_yes']).astype(int)
    h = h.drop_duplicates(['stkcd', 'year'])[['stkcd', 'year', 'top1', 'sh', 'Top1', 'Flag']]

    py = pledgor_year_balance(pl)
    m = py.merge(h[['stkcd', 'year', 'top1']], on=['stkcd', 'year'])
    m['hit'] = [t != '' and t in n.split('|') for t, n in zip(m['top1'], m['names'])]
    by_top1 = m[m['hit']].groupby(['stkcd', 'year'])['bal'].sum().rename('pl_top1')
    by_ctrl = m[m['ctrl']].groupby(['stkcd', 'year'])['bal'].sum().rename('pl_ctrl')

    out = h.set_index(['stkcd', 'year']).join(by_top1).join(by_ctrl).reset_index()
    out[['pl_top1', 'pl_ctrl']] = out[['pl_top1', 'pl_ctrl']].fillna(0)
    out['Pledge'] = (out['pl_top1'] / out['sh']).clip(0, 1)
    out['Pledge_ctrl'] = (out['pl_ctrl'] / out['sh']).clip(0, 1)
    out['Pledge_Dum'] = (out['Pledge'] > 0).astype(int)
    out['Pledge_Ratio2'] = out['Pledge'] * out['Top1']  # 质押股数 / 总股本
    agree = (out['Pledge_Dum'] == out['Flag']).mean()
    print(f'质押比例构造完成：{len(out)} 个公司年度；与十大股东质押标识一致率 {agree:.1%}')
    return out[['stkcd', 'year', 'Pledge', 'Pledge_Dum', 'Pledge_Ratio2', 'Top1', 'Pledge_ctrl', 'Flag']]


def detail_top1_pledge(detl, hld, cfg):
    """
    用「股东股权质押情况明细表」(PLED_TRDDETL) 独立构造第一大股东年末质押比例，作为稳健性口径。
    每笔交易（EventID）取年末前最后一条记录的「剩余质押数量」NumAfterChg；
    未见完结记录（IsLastestRecord≠O）但合同结束日早于上一年初的交易，视为已到期。
    在真实数据上与统计表口径的相关系数约 0.95，95% 的公司年度差异在 5 个百分点以内。
    """
    d = detl.copy()
    d['stkcd'] = d['Symbol'].astype(float).astype(int).astype(str).str.zfill(6)
    d['date'] = pd.to_datetime(d['ChangeDate'], errors='coerce')
    d['seq'] = pd.to_numeric(d['EventSeq'], errors='coerce')
    d['after'] = pd.to_numeric(d['NumAfterChg'], errors='coerce').fillna(0)
    d['end'] = pd.to_datetime(d['EndDate'], errors='coerce')
    d['name'] = _norm(d['Pledgor'])
    d = d.dropna(subset=['date']).sort_values(['EventID', 'date', 'seq'])
    d['year'] = d['date'].dt.year
    last = d.groupby(['EventID', 'year']).tail(1)

    rows = []
    for eid, g in last.groupby('EventID'):
        ys, a, fl, en = g['year'].values, g['after'].values, g['IsLastestRecord'].values, g['end'].values
        s, nm = g['stkcd'].values[0], g['name'].values[0]
        for i, y in enumerate(ys):
            y_next = ys[i + 1] if i + 1 < len(ys) else 2026
            for yy in range(y, y_next):
                expired = fl[i] != 'O' and not pd.isna(en[i]) and pd.Timestamp(en[i]) < pd.Timestamp(f'{yy - 1}-01-01')
                rows.append((s, nm, yy, 0.0 if expired else a[i]))
    e = pd.DataFrame(rows, columns=['stkcd', 'name', 'year', 'bal'])

    c = cfg
    h = hld[hld[c['rank']].astype(str).str.strip().isin(['1', '1.0'])].copy()
    h['year'] = pd.to_datetime(h[c['date']], errors='coerce').dt.year
    h = h.dropna(subset=['year']).astype({'year': int})
    h['top1'] = _norm(h[c['name']])
    h['sh'] = pd.to_numeric(h[c['shares']], errors='coerce')
    h = h.drop_duplicates(['stkcd', 'year'])[['stkcd', 'year', 'top1', 'sh']]
    m = e.merge(h, on=['stkcd', 'year'])
    bal = m[m['name'] == m['top1']].groupby(['stkcd', 'year'])['bal'].sum().rename('bal')
    out = h.set_index(['stkcd', 'year']).join(bal).reset_index()
    out['Pledge_detl'] = (out['bal'].fillna(0) / out['sh']).clip(0, 1)
    print(f'明细表口径质押比例构造完成：{len(out)} 个公司年度')
    return out[['stkcd', 'year', 'Pledge_detl']]
