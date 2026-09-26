"""
第一步：把 CSMAR 导出的原始表整理成「公司—年度」面板 panel.csv。

用法：
    python build_panel.py                # 读 ../data_raw/，写 ../data_clean/panel.csv
    python build_panel.py --raw 目录 --out 文件

需要的原始文件见 ../README.md 的「数据清单」。每个文件既可以是 .csv 也可以是 .xlsx，
文件名只要以下面 CFG 里的 file 前缀开头即可（例如 FS_Combas.xlsx、FS_Combas2007-2025.csv）。
CSMAR 导出的 xlsx 通常前三行是「字段代码 / 中文名 / 单位」，脚本会自动丢掉非数据行。

字段代码以你实际导出的为准：如果和下面不一致，只改 CFG 里的对应值即可。
"""
import argparse
import glob
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))

CFG = {
    # 资产负债表（公司研究系列 → 财务报表 → 资产负债表），Typrep=A 为合并报表
    'bs': dict(file='FS_Combas', id='Stkcd', date='Accper', type='Typrep',
               cash='A001101000',   # 货币资金
               ca='A001100000',     # 流动资产合计
               ta='A001000000',     # 资产总计
               cl='A002100000',     # 流动负债合计
               tl='A002000000'),    # 负债合计
    # 利润表
    'is': dict(file='FS_Comins', id='Stkcd', date='Accper', type='Typrep',
               rev='B001100000',    # 营业总收入
               ni='B002000000'),    # 净利润
    # 现金流量表（直接法）
    'cf': dict(file='FS_Comscfd', id='Stkcd', date='Accper', type='Typrep',
               ocf='C001000000',    # 经营活动产生的现金流量净额
               capex='C002006000'), # 购建固定资产、无形资产和其他长期资产支付的现金（拓展检验用，可缺）
    # 公司基本信息（股票市场系列 → 公司基本信息）
    'co': dict(file='TRD_Co', id='Stkcd', listdt='Listdt', ind='Nnindcd'),  # 证监会2012行业代码，J 开头为金融
    # 年个股回报率文件，用其中的年末总市值（单位：千元）
    'mv': dict(file='TRD_Year', id='Stkcd', year='Trdynt', mv='Ysmvttl', mv_unit=1000),
    # 大股东质押：按 README 第 2 步自己整理的四列文件（见 README）
    'pl': dict(file='pledge_top1', id='Stkcd', year='Year',
               shares='Top1Shares',        # 年末第一大股东持股数
               pledged='Top1PledgeShares', # 年末第一大股东质押（或冻结）股数
               top1pct='Top1Pct',          # 第一大股东持股比例（%）
               total='TotalShares'),       # 总股本（算占总股本口径，可缺）
    # 股权性质（股东研究 → 股权性质），文本中含「国」或「央」视为国企
    'soe': dict(file='EN_EquityNature', id='Symbol', date='EndDate', nature='EquityNature'),
    # 可选：ST/*ST 名单（两列 Stkcd, Year）。没有就跳过这一筛选。
    'st': dict(file='st_list', id='Stkcd', year='Year'),
}

CONTROLS = ['Size', 'Lev', 'ROA', 'Growth', 'TobinQ', 'CF', 'CFVol', 'NWC', 'Age', 'Top1']


def find(raw, prefix, required=True):
    hits = sorted(glob.glob(os.path.join(raw, prefix + '*.csv')) + glob.glob(os.path.join(raw, prefix + '*.xlsx')))
    if not hits:
        if required:
            raise SystemExit(f'找不到 {prefix}*.csv / {prefix}*.xlsx，请放到 {raw}/')
        return None
    return hits


def load(raw, key, required=True):
    c = CFG[key]
    paths = find(raw, c['file'], required)
    if paths is None:
        return None
    parts = []
    for p in paths:
        d = pd.read_excel(p, dtype=str) if p.endswith('.xlsx') else pd.read_csv(p, dtype=str, encoding_errors='replace')
        parts.append(d)
    d = pd.concat(parts, ignore_index=True)
    idcol = c['id']
    d = d[pd.to_numeric(d[idcol], errors='coerce').notna()].copy()  # 丢掉 CSMAR 的中文名/单位行
    d['stkcd'] = d[idcol].astype(float).astype(int).astype(str).str.zfill(6)
    return d


def num(s):
    return pd.to_numeric(s, errors='coerce')


def annual_fs(raw, key, fields):
    c = CFG[key]
    d = load(raw, key)
    if c['type'] in d:
        d = d[d[c['type']].str.strip() == 'A']
    dt = pd.to_datetime(d[c['date']], errors='coerce')
    d = d[(dt.dt.month == 12) & (dt.dt.day == 31)].copy()
    d['year'] = dt[d.index].dt.year
    out = d[['stkcd', 'year']].copy()
    for f in fields:
        out[f] = num(d[c[f]]) if c[f] in d else np.nan
    return out.drop_duplicates(['stkcd', 'year'], keep='last')


def winsor(s, p=0.01):
    lo, hi = s.quantile([p, 1 - p])
    return s.clip(lo, hi)


def main(raw, out):
    bs = annual_fs(raw, 'bs', ['cash', 'ca', 'ta', 'cl', 'tl'])
    inc = annual_fs(raw, 'is', ['rev', 'ni'])
    cfs = annual_fs(raw, 'cf', ['ocf', 'capex'])
    df = bs.merge(inc, on=['stkcd', 'year'], how='left').merge(cfs, on=['stkcd', 'year'], how='left')

    co = load(raw, 'co')
    c = CFG['co']
    co = co.assign(listyear=pd.to_datetime(co[c['listdt']], errors='coerce').dt.year,
                   ind=co[c['ind']].str.strip())[['stkcd', 'listyear', 'ind']].drop_duplicates('stkcd')
    df = df.merge(co, on='stkcd', how='left')

    mv = load(raw, 'mv')
    c = CFG['mv']
    mv = mv.assign(year=num(mv[c['year']]).astype('Int64'), mv=num(mv[c['mv']]) * c['mv_unit'])
    df = df.merge(mv[['stkcd', 'year', 'mv']].dropna().astype({'year': int}), on=['stkcd', 'year'], how='left')

    pl = load(raw, 'pl')
    c = CFG['pl']
    pl = pl.assign(year=num(pl[c['year']]).astype(int), sh=num(pl[c['shares']]), pd_=num(pl[c['pledged']]),
                   Top1=num(pl[c['top1pct']]) / 100,
                   tot=num(pl[c['total']]) if c['total'] in pl else np.nan)
    pl['Pledge'] = (pl['pd_'].fillna(0) / pl['sh']).clip(0, 1)
    pl['Pledge_Dum'] = (pl['pd_'].fillna(0) > 0).astype(int)
    pl['Pledge_Ratio2'] = (pl['pd_'].fillna(0) / pl['tot']).clip(0, 1)
    df = df.merge(pl[['stkcd', 'year', 'Pledge', 'Pledge_Dum', 'Pledge_Ratio2', 'Top1']].drop_duplicates(['stkcd', 'year']),
                  on=['stkcd', 'year'], how='left')

    soe = load(raw, 'soe', required=False)
    if soe is not None:
        c = CFG['soe']
        soe = soe.assign(year=pd.to_datetime(soe[c['date']], errors='coerce').dt.year,
                         SOE=soe[c['nature']].fillna('').str.contains('国|央').astype(int))
        df = df.merge(soe[['stkcd', 'year', 'SOE']].dropna().drop_duplicates(['stkcd', 'year'], keep='last')
                      .astype({'year': int}), on=['stkcd', 'year'], how='left')
    else:
        df['SOE'] = np.nan

    # ---------------- 变量 ----------------
    df = df.sort_values(['stkcd', 'year']).reset_index(drop=True)
    g = df.groupby('stkcd')
    df['Cash'] = df['cash'] / (df['ta'] - df['cash'])
    df['Cash2'] = df['cash'] / df['ta']
    df['Size'] = np.log(df['ta'])
    df['Lev'] = df['tl'] / df['ta']
    df['ROA'] = df['ni'] / df['ta']
    prev_rev = g['rev'].shift(1).where(g['year'].diff() == 1)
    df['Growth'] = df['rev'] / prev_rev - 1
    df['TobinQ'] = (df['mv'] + df['tl']) / df['ta']
    df['CF'] = df['ocf'] / df['ta']
    df['CFVol'] = g['CF'].transform(lambda s: s.rolling(3, min_periods=3).std())
    df['NWC'] = (df['ca'] - df['cl'] - df['cash']) / df['ta']
    df['Capex'] = df['capex'] / df['ta']
    age_raw = (df['year'] - df['listyear']).clip(lower=0)
    df['Age'] = np.log(age_raw + 1)

    # SA 指数：按 Hadlock & Pierce (2010) 截尾并保留原始符号（越大 = 约束越强）
    # 原文规模上限 45 亿美元（2004 年价格）；这里粗略折算为 3.7 万百万元人民币（名义值），可按需要用 CPI 调整
    size_mn = np.log((df['ta'] / 1e6).clip(upper=37000))
    age_cap = age_raw.clip(upper=37)
    df['SA'] = -0.737 * size_mn + 0.043 * size_mn ** 2 - 0.040 * age_cap

    # ---------------- 样本筛选 ----------------
    n0 = len(df)
    df = df[(df['year'] >= 2007) & (df['year'] <= 2025)]
    df = df[~df['ind'].fillna('').str.startswith('J')]           # 金融业
    df = df[df['year'] >= df['listyear']]                        # 上市当年及以后
    df = df[df['Lev'] < 1]                                       # 资不抵债
    st = load(raw, 'st', required=False)
    if st is not None:
        st = st.assign(year=num(st[CFG['st']['year']]).astype(int), _st=1)[['stkcd', 'year', '_st']]
        df = df.merge(st.drop_duplicates(), on=['stkcd', 'year'], how='left')
        df = df[df['_st'] != 1].drop(columns='_st')
    df = df.dropna(subset=['Cash', 'Pledge'] + [c for c in CONTROLS if c != 'CFVol'])
    print(f'样本筛选：{n0} → {len(df)} 个公司年度，{df.stkcd.nunique()} 家公司')

    for v in ['Cash', 'Cash2', 'Size', 'Lev', 'ROA', 'Growth', 'TobinQ', 'CF', 'CFVol', 'NWC', 'Capex', 'SA']:
        df[v] = winsor(df[v])

    keep = ['stkcd', 'year', 'ind', 'listyear', 'Cash', 'Cash2', 'Pledge', 'Pledge_Dum', 'Pledge_Ratio2',
            'SA', 'SOE', 'Capex'] + [c for c in CONTROLS if c not in ('Age',)] + ['Age']
    keep = list(dict.fromkeys(keep))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    df[keep].to_csv(out, index=False, encoding='utf-8-sig')
    print('已写出', out)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw', default=os.path.join(HERE, '..', 'data_raw'))
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'data_clean', 'panel.csv'))
    a = ap.parse_args()
    main(a.raw, a.out)
