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
               tl='A002000000',     # 负债合计
               orec='A001121000',   # 其他应收款净额（资金占用，H2b）
               opay='A002120000'),  # 其他应付款（资金占用，H2b）
    # 利润表
    'is': dict(file='FS_Comins', id='Stkcd', date='Accper', type='Typrep',
               rev='B001100000',    # 营业总收入
               ni='B002000000'),    # 净利润
    # 现金流量表（直接法）
    'cf': dict(file='FS_Comscfd', id='Stkcd', date='Accper', type='Typrep',
               ocf='C001000000',    # 经营活动产生的现金流量净额
               capex='C002006000'), # 购建固定资产、无形资产和其他长期资产支付的现金（拓展检验用，可缺）
    # 公司基本信息（股票市场系列 → 公司基本信息）
    'co': dict(file='TRD_Co', id='Stkcd', listdt='Listdt', ind='Nnindcd', prov='PROVINCE'),  # 证监会2012行业代码，J 开头为金融
    # 年个股回报率文件，用其中的年末总市值（单位：千元）
    'mv': dict(file='TRD_Year', id='Stkcd', year='Trdynt', mv='Ysmvttl', mv_unit=1000),
    # 十大股东文件（股东研究 → 十大股东）：取持股排名为 1 的股东
    # S0303a 股份质押、冻结或托管标识（据 CSMAR 说明文件）：1 = 有，2 = 无，3 = 未知（2012 年后约半数为未知）
    'hld': dict(file='HLD_Shareholders', id='Stkcd', date='Reptdt', name='S0301a', rank='S0306a',
                shares='S0302a', flag='S0303a', pct='S0304a', flag_yes='1'),
    # 股东股权质押统计表（公司研究系列 → 股权质押 → 股东股权质押统计表）
    'pled': dict(file='PLED_TRDSTAT', id='Symbol'),
    # 股东股权质押情况明细表（同一子库），用于构造稳健性口径 Pledge_detl
    'detl': dict(file='PLED_TRDDETL', id='Symbol'),
    # 大股东质押比例：自己整理的文件（见 README）。有它就用它算质押比例；没有就只用十大股东标识生成是否质押
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
    bs = annual_fs(raw, 'bs', ['cash', 'ca', 'ta', 'cl', 'tl', 'orec', 'opay'])
    inc = annual_fs(raw, 'is', ['rev', 'ni'])
    cfs = annual_fs(raw, 'cf', ['ocf', 'capex'])
    df = bs.merge(inc, on=['stkcd', 'year'], how='left').merge(cfs, on=['stkcd', 'year'], how='left')

    co = load(raw, 'co')
    c = CFG['co']
    co = co.assign(listyear=pd.to_datetime(co[c['listdt']], errors='coerce').dt.year,
                   ind=co[c['ind']].str.strip(),
                   prov=co[c['prov']].str.strip() if c['prov'] in co else np.nan)[['stkcd', 'listyear', 'ind', 'prov']].drop_duplicates('stkcd')
    df = df.merge(co, on='stkcd', how='left')

    mv = load(raw, 'mv')
    c = CFG['mv']
    mv = mv.assign(year=num(mv[c['year']]).astype('Int64'), mv=num(mv[c['mv']]) * c['mv_unit'])
    df = df.merge(mv[['stkcd', 'year', 'mv']].dropna().astype({'year': int}), on=['stkcd', 'year'], how='left')

    pl = load(raw, 'pl', required=False)
    pled = load(raw, 'pled', required=False) if pl is None else None
    if pled is not None:
        import sys
        sys.path.insert(0, HERE)
        from pledge_from_csmar import top1_pledge
        pl = top1_pledge(pled, load(raw, 'hld'), CFG['hld'])
        pl = pl[['stkcd', 'year', 'Pledge', 'Pledge_Dum', 'Pledge_Ratio2', 'Top1', 'Pledge_ctrl', 'Flag']]
    elif pl is not None:
        c = CFG['pl']
        pl = pl.assign(year=num(pl[c['year']]).astype(int), sh=num(pl[c['shares']]), pd_=num(pl[c['pledged']]),
                       Top1=num(pl[c['top1pct']]) / 100,
                       tot=num(pl[c['total']]) if c['total'] in pl else np.nan)
        pl['Pledge'] = (pl['pd_'].fillna(0) / pl['sh']).clip(0, 1)
        pl['Pledge_Dum'] = (pl['pd_'].fillna(0) > 0).astype(int)
        pl['Pledge_Ratio2'] = (pl['pd_'].fillna(0) / pl['tot']).clip(0, 1)
        pl = pl[['stkcd', 'year', 'Pledge', 'Pledge_Dum', 'Pledge_Ratio2', 'Top1']]
    else:
        c = CFG['hld']
        h = load(raw, 'hld')
        h = h[h[c['rank']].astype(str).str.strip().isin(['1', '1.0'])]
        h = h.assign(year=pd.to_datetime(h[c['date']], errors='coerce').dt.year,
                     Top1=num(h[c['pct']]) / 100,
                     Pledge_Dum=(h[c['flag']].astype(str).str.strip().str.replace('.0', '', regex=False) == c['flag_yes']).astype(int),
                     Pledge=np.nan, Pledge_Ratio2=np.nan)
        pl = h[['stkcd', 'year', 'Pledge', 'Pledge_Dum', 'Pledge_Ratio2', 'Top1']].dropna(subset=['year'])
        pl['year'] = pl['year'].astype(int)
        print('未找到质押比例文件，暂用十大股东「质押/冻结/托管标识」生成 Pledge_Dum（粗口径）')
    df = df.merge(pl.drop_duplicates(['stkcd', 'year']), on=['stkcd', 'year'], how='left')
    detl = load(raw, 'detl', required=False)
    if detl is not None:
        import sys
        sys.path.insert(0, HERE)
        from pledge_from_csmar import detail_top1_pledge
        df = df.merge(detail_top1_pledge(detl, load(raw, 'hld'), CFG['hld']), on=['stkcd', 'year'], how='left')

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
    df['OREC_raw'] = ((df['orec'].fillna(0) - df['opay'].fillna(0)) / df['ta']  # 资金净占用，缩尾后再做行业年度调整
                      ).where(df['orec'].notna() | df['opay'].notna())
    df['OR_raw'] = df['orec'] / df['ta']
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
    df = df[df['stkcd'].str[:1].isin(['0', '3', '6'])]            # 只留沪深 A 股（剔除北交所 8/4/920 开头与 B 股 900/200 开头）
    df = df[~df['ind'].fillna('').str.startswith('J')]           # 金融业
    df = df[df['year'] >= df['listyear']]                        # 上市当年及以后
    df = df[df['Lev'] < 1]                                       # 资不抵债
    st = load(raw, 'st', required=False)
    if st is not None:
        st = st.assign(year=num(st[CFG['st']['year']]).astype(int), _st=1)[['stkcd', 'year', '_st']]
        df = df.merge(st.drop_duplicates(), on=['stkcd', 'year'], how='left')
        df = df[df['_st'] != 1].drop(columns='_st')
    df = df.dropna(subset=['Cash', 'Pledge_Dum'] + [c for c in CONTROLS if c != 'CFVol'])
    print(f'样本筛选：{n0} → {len(df)} 个公司年度，{df.stkcd.nunique()} 家公司')

    for v in ['Cash', 'Cash2', 'Size', 'Lev', 'ROA', 'Growth', 'TobinQ', 'CF', 'CFVol', 'NWC', 'Capex', 'SA', 'OREC_raw', 'OR_raw']:
        df[v] = winsor(df[v])
    # 资金占用：减去同行业同年度均值（Jiang 等，2010；毛捷和管星华，2022）
    df['OREC'] = df['OREC_raw'] - df.groupby(['ind', 'year'])['OREC_raw'].transform('mean')
    df['OR'] = df['OR_raw'] - df.groupby(['ind', 'year'])['OR_raw'].transform('mean')

    for v in ['Pledge_ctrl', 'Flag', 'Pledge_detl']:
        if v not in df:
            df[v] = np.nan
    keep = ['stkcd', 'year', 'ind', 'prov', 'listyear', 'Cash', 'Cash2', 'Pledge', 'Pledge_Dum', 'Pledge_Ratio2', 'Pledge_ctrl', 'Flag', 'Pledge_detl',
            'SA', 'SOE', 'Capex', 'OREC', 'OR'] + [c for c in CONTROLS if c not in ('Age',)] + ['Age']
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
