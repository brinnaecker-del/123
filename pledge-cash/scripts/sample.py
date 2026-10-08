"""样本筛选与缩尾（供各回归脚本调用）。主口径与开题报告一致。"""
import numpy as np
import pandas as pd

CTRL = ['Size', 'Lev', 'ROA', 'Growth', 'TobinQ', 'CF', 'CFVol', 'NWC', 'Age', 'Top1']
# 缩尾变量（1%/99%）；Top1、Age 与质押比例类变量不缩尾（Top1 与开题报告表4的取值范围一致；质押比例截取至[0,1]）
WINS = ['Cash', 'Size', 'Lev', 'ROA', 'Growth', 'TobinQ', 'CF', 'CFVol', 'NWC', 'SA',
        'OREC', 'OREC_raw', 'Capex', 'Ret', 'TobinQ_alt', 'Growth_alt']


def winsor(s, lo=0.01, hi=0.99, ref=None):
    """按 ref（默认为 s 自身）的 1%、99% 分位数截尾。"""
    a, b = (s if ref is None else ref).quantile([lo, hi])
    return s.clip(a, b)


def load(path):
    df = pd.read_pickle(path)
    base = df[(df.year >= 2007) & df.is_Ashare_SZSH & ~df.is_ST & ~df.is_fin & ~df.insolvent]
    # 缩尾切点的计算样本（复现开题报告表4）：上述筛选后、Cash/Growth/TobinQ 非缺失的公司—年度（Growth 的无穷值参与分位数计算）
    wref = base.dropna(subset=['Cash', 'Growth', 'TobinQ'])
    s = base[base.ListAge >= 0].copy()
    # 质押比例截取至 [0,1]：统计表累加存在漏记解押（>1）与残差（<0），开题报告表4的取值范围为 0—1
    s['Pledge'] = s['Pledge_raw'].clip(0, 1)
    s['Pledge_det'] = s['Pledge_det_raw'].clip(0, 1)
    s['Pledge_alt'] = s['Pledge_alt_raw'].clip(0, 1)
    s['Pledge_gt1'] = (s['Pledge_raw'] > 1.0001).astype(float)
    # 股权性质（复现开题报告）：股权性质含“国企”（含“国企,民营”“国企,外资”）=1，其余与缺失=0
    s['SOE_raw'] = s['SOE']
    s['SOE'] = s['EquityNature'].fillna('').str.contains('国企').astype(float)
    need = ['Cash', 'Pledge', 'SA'] + CTRL
    s = s.dropna(subset=need).copy()
    # 资金占用：在最终样本上做行业年度均值调整（未缩尾值）
    s['OREC'] = s['OREC_raw'] - s.groupby(['Ind', 'year'])['OREC_raw'].transform('mean')
    for c in WINS:
        if c not in s:
            continue
        ref = wref[c] if c in wref and c != 'OREC' else s[c]
        s[c] = winsor(s[c], ref=ref)
    return s
