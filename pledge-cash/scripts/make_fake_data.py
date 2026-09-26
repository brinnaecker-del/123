"""
仅用于测试代码：按 CSMAR 导出格式生成一套【模拟】原始数据，检验 build_panel.py / preregression.py 能否跑通。
模拟数据里人为设定了质押对现金的效应，结果不代表任何真实结论，切勿写进论文。

    python make_fake_data.py --out ../data_fake
"""
import argparse
import os

import numpy as np
import pandas as pd

rng = np.random.default_rng(7)


def write(df, path, cn_row):
    # 模仿 CSMAR：第二行是中文字段名
    head = pd.DataFrame([cn_row], columns=df.columns)
    pd.concat([head, df.astype(str)], ignore_index=True).to_csv(path, index=False, encoding='utf-8-sig')


def main(out, n=1500):
    os.makedirs(out, exist_ok=True)
    ids = np.arange(1, n + 1)
    stk = [f'{600000 + i:06d}' if i % 2 else f'{i:06d}' for i in ids]
    listyear = rng.integers(1995, 2022, n)
    soe = (rng.random(n) < 0.35).astype(int)
    fin = rng.random(n) < 0.03
    firm_cash = rng.normal(0, 0.08, n)
    size0 = rng.normal(21.5, 1.1, n)
    pledge_prone = np.where(soe == 1, 0.08, 0.45)

    rows = []
    for i in range(n):
        ta = np.exp(size0[i])
        pl = 0.0
        for y in range(2005, 2026):
            if y < listyear[i]:
                continue
            ta *= np.exp(rng.normal(0.08, 0.12))
            boom = 1.6 if 2014 <= y <= 2017 else (0.7 if y >= 2019 else 1.0)
            if rng.random() < pledge_prone[i] * boom * 0.35:
                pl = float(np.clip(rng.beta(2, 2.5), 0, 1))
            elif rng.random() < 0.3:
                pl = pl * rng.uniform(0, 0.8)
            fc = 0.05 * (soe[i] == 0)
            cash_ratio = np.clip(0.12 + firm_cash[i] + 0.06 * pl + 0.04 * fc * pl + rng.normal(0, 0.04), 0.005, 0.8)
            cash = ta * cash_ratio
            lev = np.clip(rng.normal(0.45, 0.18), 0.05, 1.05)
            ca = ta * np.clip(rng.normal(0.55, 0.15), cash_ratio + 0.02, 0.98)
            rows.append(dict(i=i, year=y, ta=ta, cash=cash, tl=ta * lev, ca=ca,
                             cl=ta * np.clip(lev * rng.uniform(0.5, 0.9), 0.02, 1),
                             rev=ta * rng.uniform(0.3, 1.2), ni=ta * rng.normal(0.035, 0.05),
                             ocf=ta * rng.normal(0.05, 0.06), capex=ta * abs(rng.normal(0.05, 0.03)),
                             mv=ta * rng.lognormal(0.3, 0.5) / 1000, pl=pl,
                             top1=np.clip(rng.normal(34, 14), 5, 90)))
    d = pd.DataFrame(rows)
    d['Stkcd'] = [stk[i] for i in d.i]
    d['Accper'] = d.year.astype(str) + '-12-31'
    d['Typrep'] = 'A'

    write(d.assign(A001101000=d.cash, A001100000=d.ca, A001000000=d.ta, A002100000=d.cl, A002000000=d.tl)
          [['Stkcd', 'Accper', 'Typrep', 'A001101000', 'A001100000', 'A001000000', 'A002100000', 'A002000000']],
          f'{out}/FS_Combas.csv', ['证券代码', '会计期间', '报表类型', '货币资金', '流动资产合计', '资产总计', '流动负债合计', '负债合计'])
    write(d.assign(B001100000=d.rev, B002000000=d.ni)[['Stkcd', 'Accper', 'Typrep', 'B001100000', 'B002000000']],
          f'{out}/FS_Comins.csv', ['证券代码', '会计期间', '报表类型', '营业总收入', '净利润'])
    write(d.assign(C001000000=d.ocf, C002006000=d.capex)[['Stkcd', 'Accper', 'Typrep', 'C001000000', 'C002006000']],
          f'{out}/FS_Comscfd.csv', ['证券代码', '会计期间', '报表类型', '经营活动现金流量净额', '购建固定资产等支付的现金'])
    co = pd.DataFrame(dict(Stkcd=stk, Listdt=[f'{y}-06-30' for y in listyear],
                           Nnindcd=np.where(fin, 'J66', rng.choice(['C39', 'C26', 'F51', 'I65', 'K70'], n))))
    write(co, f'{out}/TRD_Co.csv', ['证券代码', '上市日期', '行业代码'])
    write(d.assign(Trdynt=d.year, Ysmvttl=d.mv)[['Stkcd', 'Trdynt', 'Ysmvttl']], f'{out}/TRD_Year.csv',
          ['证券代码', '交易年份', '年个股总市值'])
    sh = d.ta / 10 * d.top1 / 100
    write(pd.DataFrame(dict(Stkcd=d.Stkcd, Year=d.year, Top1Shares=sh.round(), Top1PledgeShares=(sh * d.pl).round(),
                            Top1Pct=d.top1.round(2), TotalShares=(d.ta / 10).round())),
          f'{out}/pledge_top1.csv', ['证券代码', '年度', '第一大股东持股数', '第一大股东质押股数', '第一大股东持股比例', '总股本'])
    write(pd.DataFrame(dict(Symbol=d.Stkcd, EndDate=d.Accper,
                            EquityNature=np.where(soe[d.i] == 1, '国企', '民营'))),
          f'{out}/EN_EquityNature.csv', ['证券代码', '截止日期', '股权性质'])
    print('模拟数据已写到', out, '共', len(d), '行')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data_fake'))
    main(ap.parse_args().out)
