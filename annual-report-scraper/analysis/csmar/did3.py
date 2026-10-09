"""探索性检验：2023 年亏损 / 下滑的入表企业此后是否更多落入微利区间（论文第五部分（五）最后一段）。"""
import numpy as np, pandas as pd, pyfixest as pf
p = pd.read_pickle("csmar/analysis.pkl")
d = p[(p.year >= 2021) & (p.year <= 2025)].copy()
d["small2"] = ((d.roa >= 0) & (d.roa < 0.02)).astype(int)
d["small05"] = ((d.roa >= 0) & (d.roa < 0.005)).astype(int)
d["nearzero"] = ((d.roa > -0.01) & (d.roa < 0.01)).astype(int)
pre = p[p.year == 2023][["Stkcd", "loss", "decl"]].rename(columns={"loss": "l23", "decl": "d23"})
d = d.merge(pre, on="Stkcd", how="left")
d["press"] = ((d.l23 == 1) | (d.d23 == 1)).astype(int)
def show(m, keys):
    t = m.tidy()
    return "  ".join(f"{k}={t.loc[k,'Estimate']:.4f}(p={t.loc[k,'Pr(>|t|)']:.3f})" for k in keys if k in t.index)
xs = "size + lev + growth + age"
for lab, dd in (("全样本", d), ("仅 2024 首入表 vs 从未入表", d[d["first"].isna() | (d["first"] == 2024)])):
    print("==", lab)
    dd = dd.dropna(subset=["press"]).copy()
    dd["post_p"] = dd.post * dd.press
    dd["post_l"] = dd.post * dd.l23.fillna(0); dd["post_d"] = dd.post * dd.d23.fillna(0)
    for y in ("small05", "small", "small2", "nearzero", "loss", "roa"):
        m = pf.feols(f"{y} ~ post + post_p + {xs} | Stkcd + year", dd, vcov={"CRV1": "Stkcd"})
        m2 = pf.feols(f"{y} ~ post + post_l + post_d + {xs} | Stkcd + year", dd, vcov={"CRV1": "Stkcd"})
        print(f"  {y:<9} {show(m, ['post', 'post_p'])}   |  {show(m2, ['post_l', 'post_d'])}")
# 描述：承压/非承压处理组各年微利占比
t = d[d.treat == 1].groupby(["press", "year"]).small.agg(["mean", "size"]).unstack(0)
c = d[d.treat == 0].groupby(["press", "year"]).small.mean().unstack(0)
print(t.round(3).to_string()); print(c.round(3).to_string())
print("\n== 控制「2023 年状态 × 年度」固定效应（吸收亏损企业的均值回归）")
dd = d.dropna(subset=["press"]).copy()
dd["st"] = dd.l23.fillna(0).astype(int).astype(str) + dd.d23.fillna(0).astype(int).astype(str)
dd["st_year"] = dd.st + "_" + dd.year.astype(str)
dd["post_p"] = dd.post * dd.press; dd["post_l"] = dd.post * dd.l23.fillna(0)
for y in ("small", "nearzero", "loss", "roa"):
    m = pf.feols(f"{y} ~ post + post_p + {xs} | Stkcd + st_year", dd, vcov={"CRV1": "Stkcd"})
    m2 = pf.feols(f"{y} ~ post + post_l + {xs} | Stkcd + st_year", dd, vcov={"CRV1": "Stkcd"})
    print(f"  {y:<9} {show(m, ['post', 'post_p'])}   |  {show(m2, ['post', 'post_l'])}")
