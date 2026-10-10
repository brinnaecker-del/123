"""第 12 步：第 6 版新增检验。
  1. 真实盈余管理（异常经营现金流、异常生产成本、异常酌量费用及合计）的双重差分：双向固定效应、事件研究、Callaway-Sant'Anna；
  2. 入表选择：加入质押比例、分析师关注、机构持股、四大审计；扩展到 2026 年上半年首次入表的企业；
  3. 入表之后审计费用、分析师关注、机构持股、年报问询函的变化；
  4. 按入表前（2023 年）外部监督强弱分组的异质性；
  5. 税后口径的利润效应（年报手工样本）。
用法：python tests_v6.py csmar/analysis6.pkl csmar/half.pkl 入表财务效应分析样本.csv 输出.json"""
import json, sys, warnings
import numpy as np, pandas as pd, pyfixest as pf
import statsmodels.formula.api as smf
from scipy import stats
from differences import ATTgt

warnings.filterwarnings("ignore")
AP, HALF, SAMPLE, OUT = sys.argv[1:5]
p = pd.read_pickle(AP)
half = pd.read_pickle(HALF)
res = {}
z80 = 1.959964 + 0.841621


def star(pv): return "***" if pv < 0.01 else "**" if pv < 0.05 else "*" if pv < 0.1 else ""
def cell(b, se, pv, nd=4): return f"{b:.{nd}f}{star(pv)}\n({b / se:.2f})"
def pval(b, se): return float(2 * (1 - stats.norm.cdf(abs(b / se))))


CT = ["size", "lev", "roa", "growth", "age"]
d = p[p.year.between(2021, 2025)].copy()
d["fid"] = d.Stkcd.astype("category").cat.codes


def twfe(dd, y, xs, extra=""):
    m = pf.feols(f"{y} ~ post{extra} + {' + '.join(xs)} | Stkcd + year", dd.dropna(subset=[y] + xs), vcov={"CRV1": "Stkcd"})
    t = m.tidy().loc["post"]
    return m, float(t.Estimate), float(t["Std. Error"]), float(t["Pr(>|t|)"])


def cs_att(dd, y, xs):
    dd = dd.dropna(subset=[y] + xs).copy()
    dd["gc"] = dd["first"]
    att = ATTgt(data=dd.set_index(["Stkcd", "year"]), cohort_column="gc", base_period="varying")
    att.fit(formula=f"{y} ~ " + " + ".join(xs), est_method="dr", control_group="never_treated", progress_bar=False)
    s = att.aggregate("simple")
    b, se = float(s.iloc[0, 0]), float(s.iloc[0, 1])
    return b, se, pval(b, se)


# ---------------- 1. 真实盈余管理 ----------------
rem = {}
e = d[(d["first"].isna()) | (d["first"] == 2024)].copy()
for k in (2021, 2022, 2024, 2025):
    e[f"T{k}"] = ((e["first"] == 2024) & (e.year == k)).astype(int)
for y in ("abCFO", "abPROD", "abDISX", "REM"):
    m, b, se, pv = twfe(d, y, CT)
    t23 = d[(d.treat == 1) & (d.year == 2023)][y]
    rec = {"b": round(b, 4), "se": round(se, 4), "p": round(pv, 3), "N": int(m._N), "cell": cell(b, se, pv), "r2": round(float(m._r2), 3),
           "ci95": [round(b - 1.96 * se, 4), round(b + 1.96 * se, 4)], "mde80": round(z80 * se, 4),
           "mean2023": round(float(t23.mean()), 4), "sd2023": round(float(t23.std()), 4), "sd_all": round(float(d[y].std()), 4)}
    me = pf.feols(f"{y} ~ T2021 + T2022 + T2024 + T2025 + {' + '.join(CT)} | Stkcd + year", e.dropna(subset=[y] + CT), vcov={"CRV1": "Stkcd"})
    te = me.tidy()
    rec["event"] = {k: [round(float(te.loc[k, "Estimate"]), 4), round(float(te.loc[k, "Pr(>|t|)"]), 3)] for k in ("T2021", "T2022", "T2024", "T2025")}
    b2, se2, pv2 = cs_att(d, y, CT)
    rec["cs"] = {"b": round(b2, 4), "se": round(se2, 4), "p": round(pv2, 3), "cell": cell(b2, se2, pv2)}
    rem[y] = rec
res["rem"] = rem
print("1 done", flush=True)

# ---------------- 2. 入表选择 ----------------
X = ["loss", "decl", "small", "size", "lev", "growth", "cfo", "soe", "age", "rdint", "caprate"]
M = ["pled", "lnana", "inst", "big4"]
lag = p[["Stkcd", "year", "ind"] + X + M].copy()
lag["year"] += 1
f6 = p.groupby("Stkcd").first6.first()
alive = {t: set(p[p.year == t].Stkcd) for t in (2024, 2025)}
alive[2026] = set(half[(half.year == 2026) & half.TA_h.notna()].Stkcd)
early = set(p.attrs.get("early_half", []))


def sel_sample(cohorts, cols, drop_early=False):
    rows = []
    for t in cohorts:
        s = lag[(lag.year == t) & lag.Stkcd.isin(alive[t])].copy()
        s["g"] = s.Stkcd.map(f6)
        s = s[s.g.isna() | (s.g >= t)]                                   # 尚未入表的企业构成风险集
        if drop_early or t == 2026:
            s = s[~s.Stkcd.isin(early)]
        s["y"] = (s.g == t).astype(int)
        s["rdint"] = s.rdint.fillna(0); s["caprate"] = s.caprate.fillna(0)
        rows.append(s.dropna(subset=cols + ["ind"]))
    a = pd.concat(rows)
    a["letter"] = a.ind.str[0]
    return a


def fit_sel(a, cols, logit=True):
    rhs = " + ".join(cols)
    fe = "ind + year" if a.year.nunique() > 1 else "ind"
    m1 = pf.feols(f"y ~ {rhs} | {fe}", a, vcov={"CRV1": "Stkcd"})
    t1 = m1.tidy()
    out = {"N": int(m1._N), "events": int(a.y.sum()), "rate": round(float(a.y.mean()), 4),
           "lpm": {v: f"{t1.loc[v, 'Estimate'] * 100:.3f}{star(t1.loc[v, 'Pr(>|t|)'])}\n({t1.loc[v, 't value']:.2f})" for v in cols},
           "lpm_p": {v: round(float(t1.loc[v, "Pr(>|t|)"]), 3) for v in cols}}
    if logit:
        ok = a.groupby("letter").y.transform("sum") > 0                  # 去掉没有入表企业的行业门类，避免完全分离
        b = a[ok]
        yr = " + C(year)" if b.year.nunique() > 1 else ""
        m2 = smf.logit(f"y ~ {rhs} + C(letter){yr}", b).fit(disp=0, maxiter=300, cov_type="cluster",
                                                             cov_kwds={"groups": b.Stkcd.astype("category").cat.codes})
        t2 = m2.summary2().tables[1]
        out["logit"] = {v: f"{t2.loc[v, 'Coef.']:.3f}{star(t2.loc[v, 'P>|z|'])}\n({t2.loc[v, 'z']:.2f})" for v in cols}
        out["logit_p"] = {v: round(float(t2.loc[v, "P>|z|"]), 3) for v in cols}
        out["logit_N"] = int(m2.nobs)
        out["pseudo_r2"] = round(float(m2.prsquared), 3)
    return out


sel = {}
sel["base_2425"] = fit_sel(sel_sample((2024, 2025), X), X)
sel["monitor_2425"] = fit_sel(sel_sample((2024, 2025), X + M), X + M)
sel["monitor_2425_dropearly"] = fit_sel(sel_sample((2024, 2025), X + M, drop_early=True), X + M)
sel["base_242526"] = fit_sel(sel_sample((2024, 2025, 2026), X), X)
sel["monitor_242526"] = fit_sel(sel_sample((2024, 2025, 2026), X + M), X + M)
a26 = sel_sample((2026,), X + M)
sel["only2026"] = fit_sel(a26, ["loss", "decl", "small", "size", "soe", "caprate"], logit=False)
sel["new26"] = sorted(a26[a26.y == 1].Stkcd)
b23 = p[p.year == 2023]
sel["desc2023"] = {v: {"treated": round(float(b23[b23.treat == 1][v].mean()), 3), "control": round(float(b23[b23.treat == 0][v].mean()), 3),
                       "t_p": round(float(stats.ttest_ind(b23[b23.treat == 1][v].dropna(), b23[b23.treat == 0][v].dropna(), equal_var=False).pvalue), 3)}
                   for v in ["pled", "nana", "inst", "big4", "lnfee", "inq", "REM", "abCFO", "abPROD", "abDISX"]}
res["sel"] = sel
print("2 done", flush=True)

# ---------------- 3. 入表之后的外部反应 ----------------
CONS = {"lnfee": (2022, 2025), "big4": (2022, 2025), "lnana": (2022, 2025), "inst": (2022, 2025), "inq": (2023, 2025), "inq_q": (2023, 2025)}
XC = ["size", "lev", "roa", "growth", "loss"]
cons = {}
for y, (a0, a1) in CONS.items():
    dd = d[d.year.between(a0, a1)]
    m, b, se, pv = twfe(dd, y, XC)
    cons[y] = {"b": round(b, 4), "se": round(se, 4), "p": round(pv, 3), "N": int(m._N), "cell": cell(b, se, pv), "years": [a0, a1],
               "mean_pre_treated": round(float(dd[(dd.treat == 1) & (dd.post == 0)][y].mean()), 4)}
    if y in ("lnfee", "lnana", "inq"):
        b2, se2, pv2 = cs_att(dd, y, XC)
        cons[y]["cs"] = {"b": round(b2, 4), "p": round(pv2, 3), "cell": cell(b2, se2, pv2)}
res["cons"] = cons
print("3 done", flush=True)

# ---------------- 4. 外部监督强弱的异质性 ----------------
q = p[p.year == 2023][["Stkcd", "big4", "nana", "inst", "pled"]].copy()
H = {"big4": q.big4 == 1, "ana_hi": q.nana >= q.nana.median(), "inst_hi": q.inst >= q.inst.median(), "pled_hi": q.pled >= q.pled.quantile(0.75)}
het = {}
XS = {"caprate": CT + ["rdint"], "absDA": CT, "REM": CT, "small": ["size", "lev", "growth", "age"]}
for h, mask in H.items():
    hn = "H_" + h
    q[hn] = mask.astype(float).where(q[mask.name].notna())
    dd = d.merge(q[["Stkcd", hn]], on="Stkcd", how="left").dropna(subset=[hn])
    dd["post_h"] = dd.post * dd[hn]
    het[h] = {"share_treated": round(float(dd[(dd.treat == 1) & (dd.year == 2023)][hn].mean()), 3),
              "n_treated_h": int(dd[(dd.treat == 1) & (dd.year == 2023) & (dd[hn] == 1)].Stkcd.nunique())}
    for y, xs in XS.items():
        m = pf.feols(f"{y} ~ post + post_h + {' + '.join(xs)} | Stkcd + year", dd.dropna(subset=[y] + xs), vcov={"CRV1": "Stkcd"})
        t = m.tidy()
        b0, s0, p0 = float(t.loc["post", "Estimate"]), float(t.loc["post", "Std. Error"]), float(t.loc["post", "Pr(>|t|)"])
        b1, s1, p1 = float(t.loc["post_h", "Estimate"]), float(t.loc["post_h", "Std. Error"]), float(t.loc["post_h", "Pr(>|t|)"])
        V = m._vcov; names = list(m._coefnames); i, j = names.index("post"), names.index("post_h")
        bh = b0 + b1; sh = float(np.sqrt(V[i, i] + V[j, j] + 2 * V[i, j]))
        het[h][y] = {"low": cell(b0, s0, p0), "diff": cell(b1, s1, p1), "high": cell(bh, sh, pval(bh, sh)), "p_diff": round(p1, 3), "N": int(m._N)}
res["het"] = het
print("4 done", flush=True)

# ---------------- 5. 税后利润效应 ----------------
s = pd.read_csv(SAMPLE, dtype={"代码": str})
s["Stkcd"] = s.代码.str.zfill(6).replace({"835184": "920184", "836208": "920208"})
s["year"] = s.年度.astype(int)
s = s.merge(p[["Stkcd", "year", "etr", "EBT", "TAX"]], on=["Stkcd", "year"], how="left")
E, NI = s.测算入表额, s.净利润
s["tau"] = np.where(s.行业 == "金融", 0.25, np.where(NI > 0, s.etr.fillna(0.15), 0.0))   # 亏损企业不计所得税影响；缺有效税率时按 15%
s["E_at"] = E * (1 - s.tau)
tax = {"rule": "盈利企业按 CSMAR 所得税费用/利润总额（缺失按 15%），亏损企业不计税，金融企业按 25%"}
for lab, g in (("nonfin", s[s.行业 == "非金融"]), ("all", s)):
    for yr, gg in g.groupby("year"):
        pos = gg[gg.测算入表额 > 0]
        imp0 = (pos.测算入表额 / pos.营业收入 * 100); imp1 = (pos.E_at / pos.营业收入 * 100)
        rel0 = pos.测算入表额 / pos.总资产 * 100; rel1 = pos.E_at / pos.总资产 * 100
        e0 = pos.测算入表额 / pos.净利润.abs() * 100; e1 = pos.E_at / pos.净利润.abs() * 100
        flip0 = ((pos.净利润 > 0) & (pos.净利润 - pos.测算入表额 < 0)).sum()
        flip1 = ((pos.净利润 > 0) & (pos.净利润 - pos.E_at < 0)).sum()
        tax[f"{lab}_{yr}"] = {"n_pos": int(len(pos)), "tau_median_profit": round(float(pos[pos.净利润 > 0].tau.median()), 3),
                              "imp_median": [round(float(imp0.median()), 4), round(float(imp1.median()), 4)],
                              "E_sum_yi": [round(float(pos.测算入表额.sum() / 1e8), 3), round(float(pos.E_at.sum() / 1e8), 3)],
                              "focus": [int(((rel0 > 1) | (e0 > 10)).sum()), int(((rel1 > 1) | (e1 > 10)).sum())],
                              "flip": [int(flip0), int(flip1)], "n_all": int(len(gg))}
res["tax"] = tax
json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
