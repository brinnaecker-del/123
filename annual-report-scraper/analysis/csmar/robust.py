"""论文第四、五部分的补充检验：描述性统计、选择模型与双重差分的稳健性、安慰剂检验、事件研究图、异质性。
用法：python robust.py csmar/analysis.pkl 入表财务效应分析样本.csv 输出.json 图3.png"""
import json, sys
import numpy as np, pandas as pd, pyfixest as pf
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

AP, SAMPLE, OUT, FIG = sys.argv[1:5]
p = pd.read_pickle(AP)
res = {}
def star(pv): return "***" if pv < 0.01 else "**" if pv < 0.05 else "*" if pv < 0.1 else ""
def cell(b, t, pv, nd=4): return f"{b:.{nd}f}{star(pv)}\n({t:.2f})"

# ---------------- 1. 描述性统计 ----------------
s = pd.read_csv(SAMPLE, dtype={"代码": str, "年度": str})
# 高金名单中经核对实际未列报数据资源的年报（神马股份 2024、金圆股份 2025、信达证券 2025）期末、期初余额均为 0，不计入入表企业样本
s = s[(s.入表期末 > 0) | (s.入表期初 > 0)]
s["入表期末万"] = s.入表期末 / 1e4; s["测算入表额万"] = s.测算入表额 / 1e4; s["总资产亿"] = s.总资产 / 1e8; s["营业收入亿"] = s.营业收入 / 1e8
s["亏损"] = (s.经营状态 == "亏损").astype(int); s["下滑"] = (s.经营状态 == "下滑").astype(int)
va = [("入表期末万", "入表余额（万元）"), ("测算入表额万", "当期新增额（万元）"), ("存量相对重要性%", "入表余额/总资产（%）"),
      ("相对重要性%", "新增额/总资产（%）"), ("净利率影响pp", "净利率影响（百分点）"), ("总资产亿", "总资产（亿元）"),
      ("营业收入亿", "营业收入（亿元）"), ("净利率%", "净利率（%）"), ("亏损", "亏损"), ("下滑", "利润下滑")]
res["descA"] = {y: [[lab] + [f"{g[v].count():d}", f"{g[v].mean():.3f}", f"{g[v].std():.3f}", f"{g[v].min():.3f}", f"{g[v].median():.3f}", f"{g[v].max():.3f}"]
                    for v, lab in va] for y, g in s.groupby("年度")}

X = ["loss", "decl", "small", "size", "lev", "growth", "cfo", "soe", "age", "rdint", "caprate"]
lag = p[["Stkcd", "year", "ind"] + X].copy(); lag["year"] += 1
rows = []
for t in (2024, 2025):
    a = lag[lag.year == t].merge(p[p.year == t][["Stkcd", "first"]], on="Stkcd")
    a = a[~((t == 2025) & (a["first"] == 2024))]
    a["y"] = (a["first"] == t).astype(int)
    a["rdint"] = a.rdint.fillna(0); a["caprate"] = a.caprate.fillna(0)
    rows.append(a.dropna(subset=X + ["ind"]))
sel = pd.concat(rows); sel["letter"] = sel.ind.str[0]
labX = {"loss": "亏损", "decl": "利润下滑", "small": "微利", "size": "企业规模", "lev": "资产负债率", "growth": "营业收入增长率",
        "cfo": "经营现金流", "soe": "国有企业", "age": "上市年限", "rdint": "研发强度", "caprate": "研发资本化率"}
res["descB"] = []
for v in ["y"] + X:
    a1, a0 = sel[sel.y == 1][v], sel[sel.y == 0][v]
    tt = stats.ttest_ind(a1, a0, equal_var=False)
    res["descB"].append([labX.get(v, "当年首次入表"), f"{sel[v].mean():.3f}", f"{sel[v].std():.3f}", f"{a1.mean():.3f}", f"{a0.mean():.3f}",
                         f"{a1.mean() - a0.mean():.3f}{star(tt.pvalue)}" if v != "y" else "—"])
res["descB_n"] = [int(len(sel)), int(sel.y.sum())]

d = p[(p.year >= 2021) & (p.year <= 2025)].copy()
vc = [("caprate", "研发资本化率"), ("capta", "资本化研发/总资产"), ("absDA", "|可操纵应计利润|"), ("small", "微利"), ("loss", "亏损"),
      ("size", "企业规模"), ("lev", "资产负债率"), ("roa", "总资产收益率"), ("growth", "营业收入增长率"), ("age", "上市年限"), ("rdint", "研发强度")]
res["descC"] = [[lab, f"{d[v].count():d}", f"{d[v].mean():.4f}", f"{d[v].std():.4f}", f"{d[v].quantile(.25):.4f}", f"{d[v].median():.4f}", f"{d[v].quantile(.75):.4f}"] for v, lab in vc]

# ---------------- 2. 选择模型稳健性 ----------------
rhs = " + ".join(X)
keys = ["loss", "decl", "small", "size", "soe", "caprate"]
sr = {}
m = smf.probit(f"y ~ {rhs} + C(letter) + C(year)", sel).fit(disp=0, maxiter=300, cov_type="cluster", cov_kwds={"groups": sel.Stkcd.astype("category").cat.codes})
t = m.summary2().tables[1]; sr["probit"] = {k: cell(t.loc[k, "Coef."], t.loc[k, "z"], t.loc[k, "P>|z|"], 3) for k in keys}; sr["probit"]["N"] = str(int(m.nobs))
sel["ind_year"] = sel.ind + "_" + sel.year.astype(str)
for lab, dd, fe in (("lpm_indyear", sel, "ind_year"), ("lpm_rd", sel[sel.rdint > 0], "ind + year"), ("lpm_2024", sel[sel.year == 2024], "ind")):
    m = pf.feols(f"y ~ {rhs} | {fe}", dd, vcov={"CRV1": "Stkcd"}); t = m.tidy()
    sr[lab] = {k: cell(t.loc[k, "Estimate"] * 100, t.loc[k, "t value"], t.loc[k, "Pr(>|t|)"], 3) for k in keys}; sr[lab]["N"] = str(m._N)
res["sel_robust"] = sr

# ---------------- 3. 应计模型替换 ----------------
def est_da(df, kind):
    out = pd.Series(np.nan, index=df.index)
    cols = ["tacc", "x0", "x1", "x1j", "x2"] + (["roa"] if kind == "kothari" else [])
    for _, g in df.dropna(subset=cols).groupby(["ind", "year"]):
        g = g[g.tacc.abs() < 2]
        if len(g) < 10:
            continue
        Xm = g[["x0", "x1j", "x2"] + (["roa"] if kind == "kothari" else [])]
        b = sm.OLS(g.tacc, Xm).fit().params
        if kind == "jones":
            pred = b.x0 * g.x0 + b.x1j * g.x1j + b.x2 * g.x2
        else:
            pred = b.x0 * g.x0 + b.x1j * g.x1 + b.x2 * g.x2 + b.roa * g.roa
        out[g.index] = g.tacc - pred
    return out
for kind in ("jones", "kothari"):
    da = est_da(p, kind).abs()
    lo, hi = da.quantile([.01, .99]); p[f"absDA_{kind}"] = da.clip(lo, hi)
d = p[(p.year >= 2021) & (p.year <= 2025)].copy()

ctrl = "size + lev + roa + growth + age"
Y = {"caprate": ctrl + " + rdint", "absDA": ctrl, "absDA_jones": ctrl, "absDA_kothari": ctrl, "small": "size + lev + growth + age"}
def did(dd, y, xs, w=None):
    kw = {"weights": "w"} if w else {}
    m = pf.feols(f"{y} ~ post + {xs} | Stkcd + year", dd.dropna(subset=[y]), vcov={"CRV1": "Stkcd"}, **kw)
    t = m.tidy().loc["post"]
    return t["Estimate"], t["t value"], t["Pr(>|t|)"], m._N

# 匹配
base = p[p.year == 2023].dropna(subset=["size", "lev", "roa", "growth", "soe", "ind"]).copy()
base["rdint"] = base.rdint.fillna(0); base["caprate"] = base.caprate.fillna(0); base["letter"] = base.ind.str[0]
ps = smf.logit("treat ~ size + lev + roa + growth + soe + rdint + caprate + C(letter)", base).fit(disp=0, maxiter=300)
base["ps"] = ps.predict(base)
def matched(k, caliper=None):
    pairs = []
    for _, r in base[base.treat == 1].iterrows():
        pool = base[(base.treat == 0) & (base.letter == r.letter)]
        if caliper is not None:
            pool = pool[(pool.ps - r.ps).abs() <= caliper]
        if len(pool) == 0:
            continue
        pairs += [r.Stkcd] + list(pool.iloc[(pool.ps - r.ps).abs().argsort()[:k]].Stkcd)
    w = pd.Series(pairs).value_counts()
    md = d[d.Stkcd.isin(w.index)].copy(); md["w"] = md.Stkcd.map(w)
    return md
variants = {
    "主回归（全样本）": (d, None),
    "1∶1 匹配": (matched(1), "w"),
    "1∶3 匹配": (matched(3), "w"),
    "1∶5 匹配": (matched(5), "w"),
    "1∶3 匹配，卡尺 0.01": (matched(3, 0.01), "w"),
    "仅 2024 年入表批次": (d[d["first"].isna() | (d["first"] == 2024)], None),
    "剔除信息技术行业": (d[d.ind.str[0] != "I"], None),
}
rb = {}
for lab, (dd, w) in variants.items():
    rb[lab] = {}
    for y, xs in Y.items():
        b, tv, pv, n = did(dd, y, xs, w)
        rb[lab][y] = cell(b, tv, pv)
        rb[lab][f"N_{y}"] = str(n)
res["did_robust"] = rb

# ---------------- 4. 安慰剂：在同一行业门类内随机指定处理组与入表年份 ----------------
rng = np.random.default_rng(20261009)
firms = p[(p.year == 2023)][["Stkcd", "ind", "treat", "first"]].dropna(subset=["ind"]).drop_duplicates("Stkcd")
firms["letter"] = firms.ind.str[0]
real = {y: did(d, y, Y[y])[1] for y in ("caprate", "absDA")}
draws = {y: [] for y in real}
for it in range(500):
    fake = {}
    for L, g in firms.groupby("letter"):
        tr = g[g.treat == 1]
        if len(tr) == 0:
            continue
        pick = g.sample(len(tr), random_state=int(rng.integers(1e9)))
        fake.update(dict(zip(pick.Stkcd, tr["first"].values)))
    dd = d.drop(columns=["post"]).copy()
    f = dd.Stkcd.map(fake)
    dd["post"] = (f.notna() & (dd.year >= f)).astype(int)
    for y in draws:
        m = pf.feols(f"{y} ~ post + {Y[y]} | Stkcd + year", dd.dropna(subset=[y]), vcov="iid")
        draws[y].append(m.tidy().loc["post", "Estimate"])
res["placebo"] = {y: {"real_b": float(did(d, y, Y[y])[0]), "mean": float(np.mean(v)), "sd": float(np.std(v)),
                      "p_two": float(np.mean(np.abs(np.array(v)) >= abs(did(d, y, Y[y])[0])))} for y, v in draws.items()}

# ---------------- 5. 事件研究图 ----------------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
font_manager.fontManager.addfont("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc")
plt.rcParams.update({"font.family": "WenQuanYi Zen Hei", "font.size": 8.5, "axes.unicode_minus": False})
e = d[(d["first"].isna()) | (d["first"] == 2024)].copy()
yrs = [2021, 2022, 2024, 2025]
for k in yrs:
    e[f"T{k}"] = ((e["first"] == 2024) & (e.year == k)).astype(int)
fig, axes = plt.subplots(1, 2, figsize=(15.5 / 2.54, 6.2 / 2.54))
ev = {}
for ax, (y, title) in zip(axes, [("caprate", "(a) 研发资本化率"), ("absDA", "(b) |可操纵应计利润|")]):
    terms = [f"T{k}" for k in yrs if e.dropna(subset=[y])[e.dropna(subset=[y]).year == k].shape[0] > 0]
    m = pf.feols(f"{y} ~ {' + '.join(terms)} + {Y[y]} | Stkcd + year", e.dropna(subset=[y]), vcov={"CRV1": "Stkcd"})
    t = m.tidy()
    xs_, bs, lo_, hi_ = [], [], [], []
    for k in sorted(set(int(c[1:]) for c in terms) | {2023}):
        if k == 2023:
            b, se = 0.0, 0.0
        else:
            b, se = t.loc[f"T{k}", "Estimate"], t.loc[f"T{k}", "Std. Error"]
        xs_.append(k); bs.append(b); lo_.append(b - 1.96 * se); hi_.append(b + 1.96 * se)
    ev[y] = {str(k): [round(b, 4), round(l, 4), round(h, 4)] for k, b, l, h in zip(xs_, bs, lo_, hi_)}
    ax.axhline(0, color="0.5", lw=0.6); ax.axvline(2023.5, color="0.5", lw=0.6, ls=":")
    ax.errorbar(xs_, bs, yerr=[np.array(bs) - np.array(lo_), np.array(hi_) - np.array(bs)], fmt="o", color="black", ms=3.5, capsize=2.5, lw=0.8)
    ax.set_xticks(xs_); ax.set_title(title, fontsize=8.5); ax.set_xlabel("年度（2023 年为基期）")
    ax.tick_params(labelsize=7.5, direction="in")
axes[0].set_ylabel("系数与 95% 置信区间")
fig.tight_layout(w_pad=1.2); fig.savefig(FIG, dpi=300)
res["event"] = ev

# ---------------- 6. 异质性 ----------------
pre = p[p.year == 2023][["Stkcd", "size", "loss", "decl", "ind", "soe"]].rename(columns={"size": "s23", "loss": "l23", "decl": "d23", "soe": "soe23"})
pre["smallfirm"] = (pre.s23 < pre.groupby("ind").s23.transform("median")).astype(int)
pre["press"] = ((pre.l23 == 1) | (pre.d23 == 1)).astype(int)
dh = d.merge(pre[["Stkcd", "smallfirm", "press", "soe23"]], on="Stkcd", how="left")
dh["it"] = (dh.ind.str[0] == "I").astype(int)
het = {}
for mod, lab in (("soe23", "国有企业"), ("smallfirm", "规模较小"), ("press", "2023年承压"), ("it", "信息技术行业")):
    het[lab] = {}
    for y in ("caprate", "absDA", "small"):
        dd = dh.dropna(subset=[y, mod]).copy(); dd["post_x"] = dd.post * dd[mod]
        m = pf.feols(f"{y} ~ post + post_x + {Y[y]} | Stkcd + year", dd, vcov={"CRV1": "Stkcd"}); t = m.tidy()
        het[lab][y] = {"post": cell(t.loc["post", "Estimate"], t.loc["post", "t value"], t.loc["post", "Pr(>|t|)"]),
                       "post_x": cell(t.loc["post_x", "Estimate"], t.loc["post_x", "t value"], t.loc["post_x", "Pr(>|t|)"])}
res["het"] = het
json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: res[k] for k in ("sel_robust", "did_robust", "placebo", "event", "het")}, ensure_ascii=False, indent=1))
