"""Lind 和 Mehlum（2010）端点斜率检验：x∈[lo,hi]，y = b1 x + b2 x² + …"""
import numpy as np
from scipy import stats as sst

def utest(m, x='Pledge', x2='Pledge2', lo=0.0, hi=1.0):
    b = m.coef(); V = m._vcov
    names = list(b.index)
    i, j = names.index(x), names.index(x2)
    def slope(v):
        g = np.zeros(len(names)); g[i] = 1; g[j] = 2 * v
        est = g @ b.values; se = np.sqrt(g @ V @ g)
        return est, se, est / se
    s0, s1 = slope(lo), slope(hi)
    df = m._N - len(names)
    p0 = sst.t.cdf(s0[2], df)          # H1: 左端斜率<0
    p1 = 1 - sst.t.cdf(s1[2], df)      # H1: 右端斜率>0
    tp = -b.values[i] / (2 * b.values[j]) if b.values[j] != 0 else np.nan
    return dict(slope_lo=s0[0], t_lo=s0[2], p_lo=p0, slope_hi=s1[0], t_hi=s1[2], p_hi=p1,
                p_joint=max(p0, p1), turning=tp, holds=(max(p0, p1) < 0.05) and lo < tp < hi)
