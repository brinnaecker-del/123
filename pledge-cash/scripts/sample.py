"""样本筛选与缩尾（供各回归脚本调用）。"""
import numpy as np
import pandas as pd

CTRL = ['Size', 'Lev', 'ROA', 'Growth', 'TobinQ', 'CF', 'CFVol', 'NWC', 'Age', 'Top1']
# Top1 不缩尾（与开题报告表4的取值范围一致）
WINS = ['Cash', 'Size', 'Lev', 'ROA', 'Growth', 'TobinQ', 'CF', 'CFVol', 'NWC', 'SA',
        'OREC', 'OREC_raw', 'Capex', 'Ret']

def winsor(s, lo=0.01, hi=0.99):
    a, b = s.quantile([lo, hi])
    return s.clip(a, b)

def load(path, cfvol_min=3):
    df = pd.read_pickle(path)
    s = df[(df.year >= 2007) & df.is_Ashare_SZSH & ~df.is_ST & ~df.is_fin & ~df.insolvent & (df.ListAge >= 0)].copy()
    # 质押比例截在 [0,1]：统计表累加存在漏记解押（>1）与残差（<0），表4的取值范围为 0—1
    s['Pledge'] = s['Pledge_raw'].clip(0, 1)
    s['Pledge_det'] = s['Pledge_det_raw'].clip(0, 1)
    s['Pledge_Ratio2'] = s['Pledge_Ratio2'].clip(0, 1)
    s['Pledge_gt1'] = (s['Pledge_raw'] > 1.0001).astype(float)
    # 资金占用：行业年度均值调整
    s['OREC'] = s['OREC_raw'] - s.groupby(['Ind', 'year'])['OREC_raw'].transform('mean')
    need = ['Cash', 'Pledge', 'SA', 'SOE'] + CTRL
    s = s.dropna(subset=need)
    for c in WINS:
        if c in s:
            s[c] = winsor(s[c])
    return s
