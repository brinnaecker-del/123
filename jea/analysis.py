"""Main analysis for the JEA manuscript (run clean.py first).

Sections
  1  Descriptives and fiscal self-sufficiency by prefecture
  2  Inequality of per-capita GDP, own revenue and expenditure (Gini, Theil T/L)
     and the between/within-prefecture Theil decomposition
  3  Equalisation asymmetry: cross-sectional elasticities of revenue and expenditure
     with respect to output
  4  sigma- and beta-convergence of per-capita GDP
  5  Asymmetric adjustment of expenditure to positive vs negative changes in
     output and own revenue (county and year fixed effects, clustered SE)
  6  Robustness
All tables are written to jea/output/*.csv; figures to jea/output/Figure_*.png
"""
import os
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")


def prep(d):
    d = d.copy().sort_values(["code", "year"])
    d["gdp_pc"] = d.gdp / d["pop"]          # 10k yuan / 10k persons = yuan per person
    d["rev_pc"] = d.rev / d["pop"]
    d["exp_pc"] = d.exp / d["pop"]
    d["ssr"] = d.rev / d.exp                 # fiscal self-sufficiency ratio
    for v in ["gdp_pc", "rev_pc", "exp_pc", "gdp", "rev", "exp"]:
        d["l" + v] = np.log(d[v])
    for v in ["lexp_pc", "lrev_pc", "lgdp_pc", "lexp", "lrev", "lgdp"]:
        d["d" + v] = d.groupby("code")[v].diff()
    for v in ["lgdp", "lrev"]:
        d[f"d{v}_pos"] = d[f"d{v}"].clip(lower=0)
        d[f"d{v}_neg"] = d[f"d{v}"].clip(upper=0)
    return d


df = prep(pd.read_csv(os.path.join(OUT, "panel_clean.csv")))
raw = prep(pd.read_csv(os.path.join(OUT, "panel_raw.csv")).rename(columns={"pop_res": "_pr"}))
YEARS = sorted(df.year.unique())
res = {}


# ---------------------------------------------------------------- inequality
def gini(x, w):
    o = np.argsort(x)
    x, w = np.asarray(x)[o], np.asarray(w)[o]
    w = w / w.sum()
    cw = np.cumsum(w)
    cxw = np.cumsum(x * w) / np.sum(x * w)
    return 1 - np.sum(w * (cxw + np.r_[0, cxw[:-1]]))


def theil(x, w, kind="T"):
    w = np.asarray(w) / np.sum(w)
    x = np.asarray(x)
    mu = np.sum(w * x)
    r = x / mu
    return np.sum(w * r * np.log(r)) if kind == "T" else np.sum(w * np.log(1 / r))


def theil_decomp(g, var, kind="T"):
    """Population-weighted Theil, between/within prefecture."""
    tot = theil(g[var], g["pop"], kind)
    P = g["pop"].sum()
    Y = (g[var] * g["pop"]).sum()
    within = 0.0
    btw_x, btw_w = [], []
    for _, h in g.groupby("pref"):
        p_share = h["pop"].sum() / P
        y_share = (h[var] * h["pop"]).sum() / Y
        wt = y_share if kind == "T" else p_share
        within += wt * theil(h[var], h["pop"], kind)
        btw_x.append((h[var] * h["pop"]).sum() / h["pop"].sum())
        btw_w.append(h["pop"].sum())
    between = theil(np.array(btw_x), np.array(btw_w), kind)
    return tot, between, within


rows = []
for y in YEARS:
    for var in ["gdp_pc", "rev_pc", "exp_pc"]:
        g = df[(df.year == y) & df[var].notna()]
        t, b, w = theil_decomp(g, var, "T")
        tl, bl, wl = theil_decomp(g, var, "L")
        rows.append(dict(year=y, var=var, n=len(g), gini=gini(g[var], g["pop"]),
                         cv=np.sqrt(np.cov(g[var], aweights=g["pop"])) / np.average(g[var], weights=g["pop"]),
                         theilT=t, T_between=b, T_within=w, T_between_share=b / t,
                         theilL=tl, L_between=bl, L_within=wl, L_between_share=bl / tl))
ineq = pd.DataFrame(rows)
ineq.to_csv(os.path.join(OUT, "T_inequality.csv"), index=False)

# Balanced sub-sample inequality (counties with all three variables in the year)
rows = []
for y in YEARS:
    g = df[(df.year == y)].dropna(subset=["gdp_pc", "rev_pc", "exp_pc"])
    rows.append(dict(year=y, n=len(g), **{f"gini_{v}": gini(g[v], g["pop"]) for v in ["gdp_pc", "rev_pc", "exp_pc"]},
                     **{f"T_{v}": theil(g[v], g["pop"]) for v in ["gdp_pc", "rev_pc", "exp_pc"]}))
ineq_bal = pd.DataFrame(rows)
ineq_bal["equalisation_gini"] = 1 - ineq_bal.gini_exp_pc / ineq_bal.gini_rev_pc
ineq_bal.to_csv(os.path.join(OUT, "T_inequality_common_sample.csv"), index=False)

# ------------------------------------------------------- descriptives / SSR
desc = df[["gdp_pc", "rev_pc", "exp_pc", "ssr", "pop"]].describe(percentiles=[.1, .5, .9]).T
desc.to_csv(os.path.join(OUT, "T_descriptives.csv"))
pref = (df.groupby(["pref"]).apply(lambda h: pd.Series(dict(
    counties=h.code.nunique(),
    pop_2024=h.loc[h.year == 2024, "pop"].sum(),
    gdp_pc_2016=(h.loc[h.year == 2016, "gdp"].sum() / h.loc[h.year == 2016, "pop"].sum()),
    gdp_pc_2024=(h.loc[h.year == 2024, "gdp"].sum() / h.loc[h.year == 2024, "pop"].sum()),
    ssr_pooled=h.rev.sum() / h.loc[h.rev.notna(), "exp"].sum(),
    ssr_median_county=h.ssr.median(),
    exp_pc_2024=(h.loc[h.year == 2024, "exp"].sum() / h.loc[h.year == 2024, "pop"].sum()),
))))
tot = pd.Series(dict(counties=df.code.nunique(), pop_2024=df.loc[df.year == 2024, "pop"].sum(),
                     gdp_pc_2016=df.loc[df.year == 2016, "gdp"].sum() / df.loc[df.year == 2016, "pop"].sum(),
                     gdp_pc_2024=df.loc[df.year == 2024, "gdp"].sum() / df.loc[df.year == 2024, "pop"].sum(),
                     ssr_pooled=df.rev.sum() / df.loc[df.rev.notna(), "exp"].sum(),
                     ssr_median_county=df.ssr.median(),
                     exp_pc_2024=df.loc[df.year == 2024, "exp"].sum() / df.loc[df.year == 2024, "pop"].sum()),
                name="All 73 counties")
pref = pd.concat([pref.sort_values("gdp_pc_2024", ascending=False), tot.to_frame().T])
pref.to_csv(os.path.join(OUT, "T_prefectures.csv"))

ssr_year = df.groupby("year").apply(lambda h: pd.Series(dict(
    ssr_pooled=h.rev.sum() / h.loc[h.rev.notna(), "exp"].sum(), ssr_median=h.ssr.median(),
    share_below_10=(h.ssr < 0.10).mean(), n=h.ssr.notna().sum())))
ssr_year.to_csv(os.path.join(OUT, "T_ssr_year.csv"))


# ------------------------------------------- equalisation elasticities (levels)
def ols(formula, data, cluster=None, weights=None):
    data = data.dropna(subset=[c for c in data.columns if c in formula])
    if weights is not None:
        m = smf.wls(formula, data, weights=data[weights])
    else:
        m = smf.ols(formula, data)
    if cluster:
        return m.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(data[cluster])[0]}), data
    return m.fit(cov_type="HC1"), data


elas = []
for dep in ["lrev_pc", "lexp_pc"]:
    r, d = ols(f"{dep} ~ lgdp_pc + C(year)", df, cluster="code")
    elas.append(dict(spec="pooled + year FE", dep=dep, b=r.params["lgdp_pc"], se=r.bse["lgdp_pc"], n=int(r.nobs), r2=r.rsquared))
    r, d = ols(f"{dep} ~ lgdp_pc + C(year) + C(pref)", df, cluster="code")
    elas.append(dict(spec="+ prefecture FE", dep=dep, b=r.params["lgdp_pc"], se=r.bse["lgdp_pc"], n=int(r.nobs), r2=r.rsquared))
    r, d = ols(f"{dep} ~ lgdp_pc + C(year) + C(code)", df, cluster="code")
    elas.append(dict(spec="county FE (within)", dep=dep, b=r.params["lgdp_pc"], se=r.bse["lgdp_pc"], n=int(r.nobs), r2=r.rsquared))
# expenditure on own revenue
for spec, f in [("pooled + year FE", "lexp_pc ~ lrev_pc + C(year)"),
                ("+ prefecture FE", "lexp_pc ~ lrev_pc + C(year) + C(pref)"),
                ("county FE (within)", "lexp_pc ~ lrev_pc + C(year) + C(code)")]:
    r, d = ols(f, df, cluster="code")
    elas.append(dict(spec=spec, dep="lexp_pc|lrev_pc", b=r.params["lrev_pc"], se=r.bse["lrev_pc"], n=int(r.nobs), r2=r.rsquared))
elas = pd.DataFrame(elas)
elas["t"] = elas.b / elas.se
elas.to_csv(os.path.join(OUT, "T_elasticities.csv"), index=False)

# ------------------------------------------------------------- convergence
sig = ineq[ineq["var"] == "gdp_pc"][["year", "cv", "gini", "theilT"]].copy()
# unweighted sd of log gdp_pc
sig["sd_log"] = [df.loc[df.year == y, "lgdp_pc"].std() for y in sig.year]
sig["sd_log_excl_shift"] = [df.loc[(df.year == y) & ~df.level_shift, "lgdp_pc"].std() for y in sig.year]
sig.to_csv(os.path.join(OUT, "T_sigma.csv"), index=False)

w = df.pivot(index="code", columns="year", values="lgdp_pc")
cs = pd.DataFrame({"g": (w[2024] - w[2016]) / 8, "l0": w[2016]})
cs = cs.join(df[df.year == 2016].set_index("code")[["pref", "level_shift", "pop"]])
beta = []
for name, d in [("all", cs), ("excl. level-shift counties", cs[~cs.level_shift])]:
    for spec, f in [("absolute", "g ~ l0"), ("conditional (prefecture FE)", "g ~ l0 + C(pref)")]:
        r = smf.ols(f, d).fit(cov_type="HC1")
        b = r.params["l0"]
        lam = -np.log(1 + 8 * b) / 8
        beta.append(dict(sample=name, spec=spec, beta=b, se=r.bse["l0"], p=r.pvalues["l0"], n=int(r.nobs), r2=r.rsquared,
                         speed=lam, half_life=np.log(2) / lam if lam > 0 else np.nan))
# annual panel beta with county FE (Nickell-biased, reported as upper bound on speed)
df = df.sort_values(["code", "year"])
df["dl_gdp_pc"] = df.groupby("code").lgdp_pc.diff()
df["l_lag"] = df.groupby("code").lgdp_pc.shift()
for spec, f in [("annual panel, year FE", "dl_gdp_pc ~ l_lag + C(year)"),
                ("annual panel, prefecture+year FE", "dl_gdp_pc ~ l_lag + C(year) + C(pref)"),
                ("annual panel, county+year FE", "dl_gdp_pc ~ l_lag + C(year) + C(code)")]:
    r, d = ols(f, df, cluster="code")
    b = r.params["l_lag"]
    lam = -np.log(1 + b)
    beta.append(dict(sample="all", spec=spec, beta=b, se=r.bse["l_lag"], p=r.pvalues["l_lag"], n=int(r.nobs), r2=r.rsquared,
                     speed=lam, half_life=np.log(2) / lam if lam > 0 else np.nan))
beta = pd.DataFrame(beta)
beta.to_csv(os.path.join(OUT, "T_beta.csv"), index=False)

# ------------------------------------------------- asymmetric adjustment
def asym(formula, data, a, b, label):
    r, d = ols(formula, data, cluster="code")
    wt = r.wald_test(f"{a} = {b}", scalar=True)
    return r, dict(model=label, n=int(r.nobs), counties=d.code.nunique(), r2=r.rsquared,
                   b_pos=r.params[a], se_pos=r.bse[a], b_neg=r.params[b], se_neg=r.bse[b],
                   wald_F=float(wt.statistic), wald_p=float(wt.pvalue))


A = []
models = {}
r, row = asym("dlexp ~ dlgdp_pos + dlgdp_neg + C(year)", df, "dlgdp_pos", "dlgdp_neg", "(1) Exp on GDP, year FE"); A.append(row); models[1] = r
r, row = asym("dlexp ~ dlgdp_pos + dlgdp_neg + C(year) + C(code)", df, "dlgdp_pos", "dlgdp_neg", "(2) Exp on GDP, county+year FE"); A.append(row); models[2] = r
r, row = asym("dlexp ~ dlrev_pos + dlrev_neg + C(year) + C(code)", df, "dlrev_pos", "dlrev_neg", "(3) Exp on own revenue, county+year FE"); A.append(row); models[3] = r
r, row = asym("dlexp ~ dlgdp_pos + dlgdp_neg + dlrev_pos + dlrev_neg + C(year) + C(code)", df, "dlgdp_pos", "dlgdp_neg", "(4a) joint: GDP"); A.append(row); models[4] = r
wt = r.wald_test("dlrev_pos = dlrev_neg", scalar=True)
A.append(dict(model="(4b) joint: own revenue", n=int(r.nobs), counties=row["counties"], r2=r.rsquared,
              b_pos=r.params["dlrev_pos"], se_pos=r.bse["dlrev_pos"], b_neg=r.params["dlrev_neg"], se_neg=r.bse["dlrev_neg"],
              wald_F=float(wt.statistic), wald_p=float(wt.pvalue)))
r, row = asym("dlrev ~ dlgdp_pos + dlgdp_neg + C(year) + C(code)", df, "dlgdp_pos", "dlgdp_neg", "(5) Own revenue on GDP, county+year FE"); A.append(row); models[5] = r
asymT = pd.DataFrame(A)
asymT.to_csv(os.path.join(OUT, "T_asymmetry.csv"), index=False)

# Heterogeneity: low vs high self-sufficiency counties (median split on county mean SSR)
cm = df.groupby("code").ssr.mean()
df["high_ssr"] = df.code.map(cm > cm.median())
H = []
for lab, d in [("low self-sufficiency", df[~df.high_ssr]), ("high self-sufficiency", df[df.high_ssr])]:
    for f, a, b, nm in [("dlexp ~ dlgdp_pos + dlgdp_neg + C(year) + C(code)", "dlgdp_pos", "dlgdp_neg", "Exp on GDP"),
                        ("dlexp ~ dlrev_pos + dlrev_neg + C(year) + C(code)", "dlrev_pos", "dlrev_neg", "Exp on own revenue")]:
        _, row = asym(f, d, a, b, f"{nm} | {lab}")
        H.append(row)
pd.DataFrame(H).to_csv(os.path.join(OUT, "T_asymmetry_heterogeneity.csv"), index=False)

# ------------------------------------------------------------- robustness
R = []
rob_specs = {
    "baseline": df,
    "excl. level-shift counties": df[~df.level_shift],
    "excl. Lhasa prefecture": df[df.pref != "Lhasa"],
    "excl. 2020-2022": df[~df.year.isin([2020, 2021, 2022])],
}
# winsorised changes
dw = df.copy()
for v in ["dlexp", "dlgdp_pos", "dlgdp_neg", "dlrev_pos", "dlrev_neg"]:
    lo, hi = dw[v].quantile([.025, .975])
    dw[v] = dw[v].clip(lo, hi)
rob_specs["winsorised 2.5/97.5"] = dw
rob_specs["uncleaned raw data"] = raw
for lab, d in rob_specs.items():
    for f, a, b, nm in [("dlexp ~ dlgdp_pos + dlgdp_neg + C(year) + C(code)", "dlgdp_pos", "dlgdp_neg", "Exp on GDP"),
                        ("dlexp ~ dlrev_pos + dlrev_neg + C(year) + C(code)", "dlrev_pos", "dlrev_neg", "Exp on own revenue")]:
        _, row = asym(f, d, a, b, f"{nm} | {lab}")
        R.append(row)
# per-capita version
_, row = asym("dlexp_pc ~ dlgdp_pos + dlgdp_neg + C(year) + C(code)", df, "dlgdp_pos", "dlgdp_neg", "Exp per capita on GDP | baseline"); R.append(row)
# revenue-on-GDP asymmetry under the same perturbations
for lab, d in rob_specs.items():
    if lab == "winsorised 2.5/97.5":
        d = df.copy()
        lo, hi = d.dlrev.quantile([.025, .975])
        d["dlrev"] = d.dlrev.clip(lo, hi)
    _, row = asym("dlrev ~ dlgdp_pos + dlgdp_neg + C(year) + C(code)", d, "dlgdp_pos", "dlgdp_neg", f"Own revenue on GDP | {lab}")
    R.append(row)
pd.DataFrame(R).to_csv(os.path.join(OUT, "T_robustness.csv"), index=False)

# leave-one-out over the GDP-contraction observations (revenue equation)
d0 = df.dropna(subset=["dlrev", "dlgdp_pos", "dlgdp_neg"])
J = []
for i in d0.index[d0.dlgdp < 0]:
    _, row = asym("dlrev ~ dlgdp_pos + dlgdp_neg + C(year) + C(code)", d0.drop(i), "dlgdp_pos", "dlgdp_neg",
                  f"drop {d0.at[i, 'county_cn']} {d0.at[i, 'year']}")
    J.append(row)
J = pd.DataFrame(J)
J.to_csv(os.path.join(OUT, "T_jackknife_contractions.csv"), index=False)
print("contraction obs:", int((d0.dlgdp < 0).sum()), " b_neg range:", J.b_neg.min().round(3), J.b_neg.max().round(3),
      " max Wald p:", J.wald_p.max().round(3))

# Decomposition-robustness for inequality: excluding level-shift counties
rows = []
for y in YEARS:
    g = df[(df.year == y) & ~df.level_shift]
    t, b, wv = theil_decomp(g.dropna(subset=["gdp_pc"]), "gdp_pc", "T")
    rows.append(dict(year=y, theilT_gdp_excl=t, between_share=b / t))
pd.DataFrame(rows).to_csv(os.path.join(OUT, "T_inequality_excl_shift.csv"), index=False)

# Chengguan (Lhasa urban core): GDP only, used for output concentration across all 74 units
cg = pd.read_excel(os.path.join(HERE, "..", "data", "城关区GDP2016-2024.xlsx"))
cg = pd.Series(cg.iloc[:, 1].values * 1e4, index=YEARS)  # 100m yuan -> 10k yuan
rows = []
for y in YEARS:
    g = np.r_[df.loc[df.year == y, "gdp"].dropna().values, cg[y]]
    s = g / g.sum()
    rows.append(dict(year=y, n=len(g), chengguan_share=cg[y] / g.sum(),
                     theil_share_74=np.sum(s * np.log(s * len(g))),
                     top5_share=np.sort(s)[-5:].sum()))
pd.DataFrame(rows).to_csv(os.path.join(OUT, "T_concentration_74.csv"), index=False)
print(pd.DataFrame(rows).round(3).to_string())

df.to_csv(os.path.join(OUT, "panel_analysis.csv"), index=False)

# ----------------------------------------------------------------- figures
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
C = {"gdp_pc": "#1f5f8b", "rev_pc": "#c0392b", "exp_pc": "#2e8b57"}
LBL = {"gdp_pc": "GDP per capita", "rev_pc": "Own revenue per capita", "exp_pc": "Expenditure per capita"}

fig, ax = plt.subplots(1, 2, figsize=(7.5, 3.0), dpi=300)
for v in ["gdp_pc", "rev_pc", "exp_pc"]:
    s = ineq[ineq["var"] == v]
    ax[0].plot(s.year, s.gini, marker="o", ms=3, color=C[v], label=LBL[v])
    ax[1].plot(s.year, s.T_between_share * 100, marker="o", ms=3, color=C[v], label=LBL[v])
ax[0].set_title("(a) Population-weighted Gini", loc="left")
ax[1].set_title("(b) Between-prefecture share of Theil T (%)", loc="left")
for a in ax:
    a.set_xticks(YEARS[::2])
ax[0].set_ylim(0, None); ax[1].set_ylim(0, None)
ax[0].legend(frameon=False, fontsize=7.5)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "Figure_1.png"))

fig, ax = plt.subplots(1, 2, figsize=(7.5, 3.0), dpi=300)
d = df[df.year == 2024].dropna(subset=["lgdp_pc", "lrev_pc", "lexp_pc"])
for v in ["rev_pc", "exp_pc"]:
    ax[0].scatter(d.lgdp_pc, d["l" + v], s=10, alpha=.7, color=C[v], label=LBL[v])
    b = np.polyfit(d.lgdp_pc, d["l" + v], 1)
    xs = np.linspace(d.lgdp_pc.min(), d.lgdp_pc.max(), 10)
    ax[0].plot(xs, np.polyval(b, xs), color=C[v], lw=1)
    ax[0].text(xs[-1], np.polyval(b, xs[-1]), f" slope {b[0]:.2f}", color=C[v], fontsize=7, va="center")
ax[0].set_xlabel("log GDP per capita, 2024"); ax[0].set_ylabel("log yuan per capita")
ax[0].set_title("(a) Revenue vs expenditure gradients", loc="left")
ax[0].legend(frameon=False, fontsize=7.5, loc="upper left")
ax[1].scatter(cs.l0, cs.g * 100, s=10, alpha=.7, color=C["gdp_pc"])
ax[1].scatter(cs.l0[cs.level_shift], cs.g[cs.level_shift] * 100, s=18, facecolors="none", edgecolors="k", lw=.7, label="re-based GDP series")
b = np.polyfit(cs.l0, cs.g * 100, 1)
xs = np.linspace(cs.l0.min(), cs.l0.max(), 10)
ax[1].plot(xs, np.polyval(b, xs), color=C["gdp_pc"], lw=1)
ax[1].set_xlabel("log GDP per capita, 2016"); ax[1].set_ylabel("avg. annual growth 2016–2024 (%)")
ax[1].set_title("(b) Unconditional β-convergence", loc="left")
ax[1].legend(frameon=False, fontsize=7.5)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "Figure_2.png"))

fig, ax = plt.subplots(figsize=(4.5, 3.0), dpi=300)
row = asymT.set_index("model")
labs = ["(2) Exp on GDP, county+year FE", "(3) Exp on own revenue, county+year FE", "(5) Own revenue on GDP, county+year FE"]
names = ["Expenditure\n← GDP", "Expenditure\n← own revenue", "Own revenue\n← GDP"]
x = np.arange(len(labs))
for k, (side, col, off) in enumerate([("pos", "#1f5f8b", -0.17), ("neg", "#c0392b", 0.17)]):
    bvals = [row.loc[l, f"b_{side}"] for l in labs]
    se = [1.96 * row.loc[l, f"se_{side}"] for l in labs]
    ax.errorbar(x + off, bvals, yerr=se, fmt="o", color=col, capsize=3, ms=4,
                label="increase (Δ>0)" if side == "pos" else "decrease (Δ<0)")
ax.axhline(0, color="grey", lw=.6)
ax.set_xticks(x); ax.set_xticklabels(names)
ax.set_ylabel("elasticity (95% CI)")
ax.legend(frameon=False, fontsize=7.5)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "Figure_3.png"))

pd.set_option("display.width", 250)
print(ineq.round(3).to_string())
print(ineq_bal.round(3).to_string())
print(pref.round(3).to_string())
print(ssr_year.round(3).to_string())
print(elas.round(3).to_string())
print(sig.round(3).to_string())
print(beta.round(4).to_string())
print(asymT.round(3).to_string())
print(pd.read_csv(os.path.join(OUT, "T_asymmetry_heterogeneity.csv")).round(3).to_string())
print(pd.read_csv(os.path.join(OUT, "T_robustness.csv")).round(3).to_string())
print(pd.read_csv(os.path.join(OUT, "T_inequality_excl_shift.csv")).round(3).to_string())
