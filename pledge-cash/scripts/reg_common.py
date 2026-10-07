"""回归公用函数：pyfixest 估计、提取系数。"""
import sys
import numpy as np
import pandas as pd
import pyfixest as pf

def star(p):
    return '***' if p < 0.01 else '**' if p < 0.05 else '*' if p < 0.1 else ''

def fit(fml, data, vcov=None):
    vcov = vcov or {'CRV1': 'Stkcd'}
    # pyfixest 0.60 的 rust 去均值在非连续索引下会崩溃，统一重置索引
    return pf.feols(fml, data=data.reset_index(drop=True), vcov=vcov)

def cell(m, var, nd=4):
    t = m.tidy()
    if var not in t.index:
        return '', ''
    b, se, p = t.loc[var, 'Estimate'], t.loc[var, 'Std. Error'], t.loc[var, 'Pr(>|t|)']
    return f'{b:.{nd}f}{star(p)}', f'({se:.{nd}f})'

def stats(m):
    return f'{m._adj_r2:.3f}', f'{m._N:,}'
