"""论文表 3（入表选择）与表 4（双重差分）。用法：python final_tables.py analysis.pkl 输出.json"""
import json, sys
import numpy as np, pandas as pd, pyfixest as pf
import statsmodels.formula.api as smf

p = pd.read_pickle(sys.argv[1])
def star(pv): return "***" if pv < 0.01 else "**" if pv < 0.05 else "*" if pv < 0.1 else ""
out = {"sel": {}, "did": {}, "info": {}}

# ---------- 表 3：入表选择 ----------
X = ["loss", "decl", "small", "size", "lev", "growth", "cfo", "soe", "age", "rdint", "caprate"]
lag = p[["Stkcd", "year", "ind"] + X].copy(); lag["year"] += 1
rows = []
for t in (2024, 2025):
    s = lag[lag.year == t].merge(p[p.year == t][["Stkcd", "first"]], on="Stkcd")
    s = s[~((t == 2025) & (s["first"] == 2024))]
    s["y"] = (s["first"] == t).astype(int)
    s["rdint"] = s.rdint.fillna(0); s["caprate"] = s.caprate.fillna(0)
    rows.append(s.dropna(subset=X + ["ind"]))
a = pd.concat(rows); a["letter"] = a.ind.str[0]
rhs = " + ".join(X)
m1 = pf.feols(f"y ~ {rhs} | ind + year", a, vcov={"CRV1": "Stkcd"})
m2 = smf.logit(f"y ~ {rhs} + C(letter) + C(year)", a).fit(disp=0, maxiter=200, cov_type="cluster",
                                                               cov_kwds={"groups": a.Stkcd.astype("category").cat.codes})
t1, t2 = m1.tidy(), m2.summary2().tables[1]
for v in X:
    out["sel"][v] = {"lpm": f"{t1.loc[v,'Estimate']*100:.3f}{star(t1.loc[v,'Pr(>|t|)'])}\n({t1.loc[v,'t value']:.2f})",
                     "logit": f"{t2.loc[v,'Coef.']:.3f}{star(t2.loc[v,'P>|z|'])}\n({t2.loc[v,'z']:.2f})"}
out["sel"]["N"] = {"lpm": str(m1._N), "logit": str(int(m2.nobs))}
out["sel"]["treated"] = int(a.y.sum())
out["sel"]["r2"] = {"lpm": f"{m1._r2:.3f}", "logit": f"{m2.prsquared:.3f}"}
out["info"]["sel_rate"] = float(a.y.mean())

# ---------- 表 4：双重差分 ----------
d = p[(p.year >= 2021) & (p.year <= 2025)].copy()
ctrl = "size + lev + roa + growth + age"
Y = {"caprate": ctrl + " + rdint", "capta": ctrl, "absDA": ctrl, "small": "size + lev + growth + age", "loss": "size + lev + growth + age"}
base = p[p.year == 2023].dropna(subset=["size", "lev", "roa", "growth", "soe", "ind"]).copy()
base["rdint"] = base.rdint.fillna(0); base["caprate"] = base.caprate.fillna(0); base["letter"] = base.ind.str[0]
ps = smf.logit("treat ~ size + lev + roa + growth + soe + rdint + caprate + C(letter)", base).fit(disp=0, maxiter=200)
base["ps"] = ps.predict(base)
pairs = []
for _, r in base[base.treat == 1].iterrows():
    pool = base[(base.treat == 0) & (base.letter == r.letter)]
    if len(pool):
        pairs += [r.Stkcd] + list(pool.iloc[(pool.ps - r.ps).abs().argsort()[:3]].Stkcd)
w = pd.Series(pairs).value_counts()
md = d[d.Stkcd.isin(w.index)].copy(); md["w"] = md.Stkcd.map(w)
out["info"]["psm"] = {"treated": int(base[(base.treat == 1)].Stkcd.isin(pairs).sum()), "controls": int(len(set(pairs) - set(base[base.treat == 1].Stkcd)))}
for y, xs in Y.items():
    for lab, dd, kw in (("full", d, {}), ("psm", md, {"weights": "w"})):
        m = pf.feols(f"{y} ~ post + {xs} | Stkcd + year", dd.dropna(subset=[y]), vcov={"CRV1": "Stkcd"}, **kw)
        t = m.tidy().loc["post"]
        out["did"].setdefault(lab, {})[y] = {"b": f"{t['Estimate']:.4f}{star(t['Pr(>|t|)'])}\n({t['t value']:.2f})", "N": str(m._N), "r2": f"{m._r2:.3f}"}
    out["info"].setdefault("mean2023", {})[y] = float(d[(d.treat == 1) & (d.year == 2023)][y].mean())
# 事件研究：前期系数
e = d[(d["first"].isna()) | (d["first"] == 2024)].copy()
for k in (2021, 2022, 2024, 2025):
    e[f"T{k}"] = ((e["first"] == 2024) & (e.year == k)).astype(int)
for y, xs in Y.items():
    m = pf.feols(f"{y} ~ T2021 + T2022 + T2024 + T2025 + {xs} | Stkcd + year", e.dropna(subset=[y]), vcov={"CRV1": "Stkcd"})
    t = m.tidy()
    out["info"].setdefault("event", {})[y] = {k: [round(t.loc[k, "Estimate"], 4), round(t.loc[k, "Pr(>|t|)"], 3)]
                                              for k in ("T2021", "T2022", "T2024", "T2025") if k in t.index}   # 可操纵应计从 2022 年起
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
