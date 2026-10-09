"""构造分析变量：处理组、研发资本化率、可操纵应计、微利等。"""
import numpy as np, pandas as pd
from pathlib import Path
SAMPLE = Path(__file__).resolve().parents[3] / "年报存档" / "入表财务效应分析样本.csv"
import statsmodels.api as sm

p = pd.read_pickle("csmar/master.pkl")
p = p[(p.year >= 2020) & (p.fin == 0)].copy()                 # 非金融
mine = pd.read_csv(SAMPLE, dtype={"代码": str, "年度": str})
mine["Stkcd"] = mine.代码.replace({"835184": "920184", "836208": "920208"})
listed = {int(y): set(g.Stkcd) for y, g in mine.groupby("年度")}
cs = {y: set(p[(p.year == y) & (p.DR > 0)].Stkcd) for y in (2024, 2025)}
adopt = {y: listed[y] | cs[y] for y in (2024, 2025)}
first = {}
for y in (2024, 2025):
    for s in adopt[y]:
        first.setdefault(s, y)
p["first"] = p.Stkcd.map(first)                                # 首次入表年度（NaN=从未入表）
p["treat"] = p["first"].notna().astype(int)
p["post"] = ((p.year >= p["first"]) & p.treat.eq(1)).astype(int)
p["adopt_now"] = p.apply(lambda r: int(r.year in adopt and r.Stkcd in adopt[r.year]), axis=1)
g = p.groupby("Stkcd")
for c in ("TA", "REV", "SALES", "REC", "NI", "NP"):
    p[c + "_l"] = g[c].shift(1)
p["size"] = np.log(p.TA)
p["lev"] = (p.TL / p.TA).clip(0, 2)
p["roa"] = p.NI / p.TA
p["loss"] = (p.NI < 0).astype(int)
p["decl"] = ((p.NI >= 0) & (p.NI < p.NI_l)).astype(int)
p["small"] = ((p.roa >= 0) & (p.roa < 0.01)).astype(int)
p["growth"] = (p.REV / p.REV_l - 1).clip(-1, 5)
p["cfo"] = p.CFO / p.TA
p["age"] = np.log1p((p.year - pd.to_numeric(p.Listdt.str[:4], errors="coerce")).clip(lower=0))
# 研发
rds = p.RDSpendSum
cap = p.RDInvest.where(p.RDInvest.notna(), np.where(p.RDExpenses.notna() & rds.notna(), rds - p.RDExpenses, np.nan))
p["rdcap"] = cap.clip(lower=0)
p["caprate"] = (p.rdcap / rds).where(rds > 0).clip(0, 1)
p["rdint"] = (rds / p.SALES).where(p.SALES > 0).clip(0, 2)
p["capta"] = (p.rdcap / p.TA_l)
# 修正琼斯模型：行业-年度截面回归（≥10 家）
p["tacc"] = (p.NI - p.CFO) / p.TA_l
p["x0"] = 1 / p.TA_l
p["x1"] = ((p.REV - p.REV_l) - (p.REC - p.REC_l).fillna(0)) / p.TA_l
p["x1j"] = (p.REV - p.REV_l) / p.TA_l
p["x2"] = p.PPE / p.TA_l
p["DA"] = np.nan
for (ind, y), d in p.dropna(subset=["tacc", "x0", "x1j", "x2"]).groupby(["ind", "year"]):
    d = d[(d.tacc.abs() < 2)]
    if len(d) < 10:
        continue
    m = sm.OLS(d.tacc, d[["x0", "x1j", "x2"]]).fit()         # 用琼斯模型估参数
    pred = m.params.x0 * d.x0 + m.params.x1j * d.x1 + m.params.x2 * d.x2   # 修正琼斯：扣除应收账款变动
    p.loc[d.index, "DA"] = d.tacc - pred
p["absDA"] = p.DA.abs()
# 缩尾
for c in ("roa", "cfo", "capta", "DA", "absDA", "tacc", "rdint"):
    lo, hi = p[c].quantile([0.01, 0.99])
    p[c] = p[c].clip(lo, hi)
p.to_pickle("csmar/analysis.pkl")
print("处理组公司", p[p.treat == 1].Stkcd.nunique(), "其中首入 2024", sum(v == 2024 for v in first.values()), "2025", sum(v == 2025 for v in first.values()))
print(p[p.year >= 2021].groupby("year")[["caprate", "DA", "rdint"]].count().to_string())
print(p[p.year >= 2021].groupby(["year", "treat"])[["caprate", "absDA", "small", "loss"]].mean().round(4).to_string())
