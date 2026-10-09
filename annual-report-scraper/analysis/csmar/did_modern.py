"""异质性处理效应稳健的双重差分：Callaway-Sant'Anna、Sun-Abraham（饱和事件研究）、两阶段 DID（Gardner）、堆叠 DID、
Goodman-Bacon 分解、野自助法（wild cluster bootstrap）、最小可检测效应（功效），以及固定效应与趋势的替换、提前时点安慰剂。
用法：python did_modern.py csmar/analysis.pkl csmar/co.pkl 输出.json 图.png"""
import json, sys, warnings
import numpy as np, pandas as pd, pyfixest as pf
from differences import ATTgt

warnings.filterwarnings("ignore")
AP, CO, OUT, FIG = sys.argv[1:5]
p = pd.read_pickle(AP)
co = pd.read_pickle(CO)[["Stkcd", "PROVINCE"]].drop_duplicates("Stkcd")
d = p[(p.year >= 2021) & (p.year <= 2025)].merge(co, on="Stkcd", how="left").copy()
d["g"] = d["first"].fillna(0).astype(int)                   # 首次入表年度，从未入表为 0
d["fid"] = d.Stkcd.astype("category").cat.codes
d["capsales"] = (d.rdcap / d.SALES).where(d.SALES > 0).clip(0, 1)
lo, hi = d.capsales.quantile([.01, .99]); d["capsales"] = d.capsales.clip(lo, hi)
pre = p[p.year == 2023][["Stkcd", "loss", "decl"]].rename(columns={"loss": "l23", "decl": "d23"})
d = d.merge(pre, on="Stkcd", how="left")
d["st_year"] = d.l23.fillna(-1).astype(int).astype(str) + d.d23.fillna(-1).astype(int).astype(str) + "_" + d.year.astype(str)
d["ind_year"] = d.ind.astype(str) + "_" + d.year.astype(str)
d["prov_year"] = d.PROVINCE.astype(str) + "_" + d.year.astype(str)

C = ["size", "lev", "roa", "growth", "age"]
XS = {"caprate": C + ["rdint"], "capta": C, "capsales": C + ["rdint"], "absDA": C, "small": ["size", "lev", "growth", "age"],
      "loss": ["size", "lev", "growth", "age"]}
MAIN = ["caprate", "absDA", "small"]
res = {}
z80 = 1.959964 + 0.841621                                   # 双侧 5%、功效 80%


def star(pv): return "***" if pv < 0.01 else "**" if pv < 0.05 else "*" if pv < 0.1 else ""
def cell(b, se, pv, nd=4): return f"{b:.{nd}f}{star(pv)}\n({b / se:.2f})"


def twfe(dd, y, fe="Stkcd + year", extra=""):
    m = pf.feols(f"{y} ~ post + {' + '.join(XS[y])}{extra} | {fe}", dd.dropna(subset=[y] + XS[y]), vcov={"CRV1": "Stkcd"})
    t = m.tidy().loc["post"]
    return m, float(t.Estimate), float(t["Std. Error"]), float(t["Pr(>|t|)"])


def wild_p(dd, y, B=1999):
    """Restricted wild cluster bootstrap（Rademacher 权重，按公司聚类，施加 post 系数为 0 的原假设）。"""
    import statsmodels.api as sm
    from wildboottest.wildboottest import wildboottest
    dd = dd.dropna(subset=[y] + XS[y]).copy()
    dd = dd[dd.groupby("Stkcd").year.transform("count") > 1]
    yd = pd.get_dummies(dd.year, prefix="yr", drop_first=True).astype(float)
    X = pd.concat([dd[["post"] + XS[y]].astype(float), yd], axis=1)
    Xw = X - X.groupby(dd.Stkcd.values).transform("mean")
    Yw = dd[y] - dd.groupby("Stkcd")[y].transform("mean")
    mod = sm.OLS(Yw.values, Xw)
    r = wildboottest(mod, param="post", cluster=dd.Stkcd.astype("category").cat.codes.values, B=B, seed=20261009, show=False)
    return round(float(r["p-value"].iloc[0]), 3)


# ---------------- 1. 双向固定效应基准、功效与野自助法 ----------------
base = {}
for y in XS:
    m, b, se, pv = twfe(d, y)
    mean23 = d[(d.treat == 1) & (d.year == 2023)][y].mean()
    sd23 = d[(d.treat == 1) & (d.year == 2023)][y].std()
    rec = {"b": round(b, 4), "se": round(se, 4), "p": round(pv, 3), "N": int(m._N), "cell": cell(b, se, pv),
           "ci95": [round(b - 1.96 * se, 4), round(b + 1.96 * se, 4)], "mde80": round(z80 * se, 4),
           "mean2023": round(float(mean23), 4), "sd2023": round(float(sd23), 4)}
    if y in MAIN:
        rec["wild_p"] = wild_p(d, y)
    base[y] = rec
res["twfe"] = base

print("step:", ' 2. Callaway', flush=True)
# ---------------- 2. Callaway-Sant'Anna（双重稳健，从未入表为对照；另报尚未入表为对照） ----------------
cs = {}
ev = {}
for y in XS:
    dd = d.dropna(subset=[y] + XS[y]).copy()
    dd["gc"] = dd["first"]
    dd = dd.set_index(["Stkcd", "year"])
    out = {}
    for cg in ("never_treated", "not_yet_treated"):
        att = ATTgt(data=dd, cohort_column="gc", base_period="varying")
        att.fit(formula=f"{y} ~ " + " + ".join(XS[y]), est_method="dr", control_group=cg, progress_bar=False)
        s = att.aggregate("simple")
        b = float(s.iloc[0, 0]); se = float(s.iloc[0, 1])
        pv = float(2 * (1 - __import__("scipy").stats.norm.cdf(abs(b / se))))
        out[cg] = {"b": round(b, 4), "se": round(se, 4), "p": round(pv, 3), "cell": cell(b, se, pv), "mde80": round(z80 * se, 4)}
        if cg == "never_treated" and y in ("caprate", "absDA"):
            att_u = ATTgt(data=dd, cohort_column="gc", base_period="universal")
            att_u.fit(formula=f"{y} ~ " + " + ".join(XS[y]), est_method="dr", control_group=cg, progress_bar=False)
            e = att_u.aggregate("event")
            ev[y] = {int(k): [round(float(r.iloc[0]), 4), round(float(r.iloc[1]), 4)] for k, r in e.iterrows()}
    cs[y] = out
res["cs"] = cs
res["cs_event"] = ev

print("step:", ' 3. Sun-Abra', flush=True)
# ---------------- 3. Sun-Abraham（饱和事件研究）与两阶段 DID（Gardner） ----------------
sa, g2 = {}, {}
for y in MAIN:
    dd = d.dropna(subset=[y] + XS[y]).copy()
    dd = dd[dd.groupby("fid").fid.transform("size") > 1]          # 去掉只有一年观测的公司
    fit = pf.event_study(dd, yname=y, idname="fid", tname="year", gname="g", xfml=" + ".join(XS[y]), estimator="saturated", cluster="fid")
    agg = fit.aggregate(agg="period", weighting="shares")
    t = fit.tidy()
    # 入表后各期（相对年份≥0）系数按处理组观测数加权平均，标准误由系数协方差矩阵得到
    names = list(fit._coefnames)
    w = np.zeros(len(names))
    for k, nm in enumerate(names):
        if nm.startswith("rel_time::") and ":first_treated_period::" in nm:
            rt = float(nm.split("rel_time::")[1].split(":")[0]); gy = int(float(nm.split("first_treated_period::")[1]))
            if rt >= 0:
                w[k] = ((dd.g == gy) & (dd.year - gy == rt)).sum()
    w = w / w.sum()
    beta = np.asarray(fit._beta_hat); V = np.asarray(fit._vcov)
    b = float(w @ beta); se = float(np.sqrt(w @ V @ w)); pv = float(2 * (1 - __import__("scipy").stats.norm.cdf(abs(b / se))))
    sa[y] = {"cell": cell(b, se, pv), "b": round(b, 4), "se": round(se, 4), "p": round(pv, 3),
             "event": {str(k): [round(float(r.Estimate), 4), round(float(r["Std. Error"]), 4)] for k, r in agg.iterrows()}}
    try:
        fit2 = pf.event_study(dd, yname=y, idname="fid", tname="year", gname="g", xfml=" + ".join(XS[y]), estimator="did2s", cluster="fid")
        t2 = fit2.tidy(); r2 = t2.iloc[0]
        g2[y] = {"term": str(t2.index[0]), "cell": cell(float(r2.Estimate), float(r2["Std. Error"]), float(r2["Pr(>|t|)"])),
                 "b": round(float(r2.Estimate), 4), "p": round(float(r2["Pr(>|t|)"]), 3)}
    except Exception as e:
        g2[y] = {"error": f"{type(e).__name__}: {e}"[:200]}
res["sa"] = sa
res["did2s"] = g2

print("step:", ' 4. 堆叠', flush=True)
# ---------------- 4. 堆叠 DID（每个入表批次只与从未入表企业比较） ----------------
stk = {}
for y in MAIN:
    parts = []
    for gy in (2024, 2025):
        s = d[(d["first"] == gy) | d["first"].isna()].copy()
        s["stack"] = gy
        s["post_s"] = ((s["first"] == gy) & (s.year >= gy)).astype(int)
        parts.append(s)
    s = pd.concat(parts)
    s["fs"] = s.Stkcd + "_" + s["stack"].astype(str); s["ys"] = s.year.astype(str) + "_" + s["stack"].astype(str)
    s = s.dropna(subset=[y] + XS[y])
    m = pf.feols(f"{y} ~ post_s + {' + '.join(XS[y])} | fs + ys", s, vcov={"CRV1": "Stkcd"})
    t = m.tidy().loc["post_s"]
    stk[y] = {"cell": cell(float(t.Estimate), float(t["Std. Error"]), float(t["Pr(>|t|)"])), "b": round(float(t.Estimate), 4),
              "p": round(float(t["Pr(>|t|)"]), 3), "N": int(m._N)}
res["stacked"] = stk

print("step:", ' 5. Goodman', flush=True)
# ---------------- 5. Goodman-Bacon 分解（平衡面板、不含控制变量） ----------------
def bacon(y):
    years = sorted(d[d[y].notna()].year.unique())
    bal = d.dropna(subset=[y]).groupby("Stkcd").filter(lambda g: len(g) == len(years) and sorted(g.year) == years).copy()
    T = len(years)
    tw = pf.feols(f"{y} ~ post | Stkcd + year", bal, vcov="iid").tidy().loc["post", "Estimate"]
    groups = {"2024": bal[bal["first"] == 2024], "2025": bal[bal["first"] == 2025], "U": bal[bal["first"].isna()]}
    n = {k: v.Stkcd.nunique() for k, v in groups.items()}; N = sum(n.values())
    sh = {k: n[k] / N for k in n}
    Dbar = {"2024": sum(yy >= 2024 for yy in years) / T, "2025": sum(yy >= 2025 for yy in years) / T}
    m = lambda gdf, yrs: gdf[gdf.year.isin(yrs)][y].mean()
    def dd2(tr, ctl, pre, post):
        return (m(groups[tr], post) - m(groups[tr], pre)) - (m(groups[ctl], post) - m(groups[ctl], pre))
    pre24 = [t for t in years if t < 2024]; post24 = [t for t in years if t >= 2024]
    pre25 = [t for t in years if t < 2025]; post25 = [t for t in years if t >= 2025]
    mid = [t for t in years if 2024 <= t < 2025]
    est = {"2024 vs 从未入表": dd2("2024", "U", pre24, post24), "2025 vs 从未入表": dd2("2025", "U", pre25, post25),
           "2024 vs 2025（2025 尚未入表）": dd2("2024", "2025", pre24, mid), "2025 vs 2024（2024 已入表）": dd2("2025", "2024", mid, post25)}
    # 权重（Goodman-Bacon 2021, 定理 1），以双重去均值处理变量的方差归一
    bal["Dt"] = bal.post - bal.groupby("Stkcd").post.transform("mean") - bal.groupby("year").post.transform("mean") + bal.post.mean()
    VD = (bal.Dt ** 2).mean()
    k, l = "2024", "2025"
    nkU = sh[k] / (sh[k] + sh["U"]); nlU = sh[l] / (sh[l] + sh["U"]); nkl = sh[k] / (sh[k] + sh[l])
    w = {"2024 vs 从未入表": (sh[k] + sh["U"]) ** 2 * nkU * (1 - nkU) * Dbar[k] * (1 - Dbar[k]) / VD,
         "2025 vs 从未入表": (sh[l] + sh["U"]) ** 2 * nlU * (1 - nlU) * Dbar[l] * (1 - Dbar[l]) / VD,
         "2024 vs 2025（2025 尚未入表）": ((sh[k] + sh[l]) * (1 - Dbar[l])) ** 2 * nkl * (1 - nkl) * ((Dbar[k] - Dbar[l]) / (1 - Dbar[l]))
         * ((1 - Dbar[k]) / (1 - Dbar[l])) / VD,
         "2025 vs 2024（2024 已入表）": ((sh[k] + sh[l]) * Dbar[k]) ** 2 * nkl * (1 - nkl) * (Dbar[l] / Dbar[k]) * ((Dbar[k] - Dbar[l]) / Dbar[k]) / VD}
    tot = sum(w.values())
    return {"twfe_balanced": round(float(tw), 4), "weighted_sum": round(float(sum(w[c] * est[c] for c in est) / tot), 4),
            "weight_sum_raw": round(float(tot), 4), "N_firms": n,
            "parts": {c: [round(float(est[c]), 4), round(float(w[c] / tot), 4)] for c in est}}


res["bacon"] = {y: bacon(y) for y in MAIN}

print("step:", ' 6. 固定效应', flush=True)
# ---------------- 6. 固定效应与趋势的替换、提前时点安慰剂、替代被解释变量 ----------------
alt = {}
for y in MAIN:
    r = {}
    for lab, fe in (("行业×年度", "Stkcd + ind_year"), ("省份×年度", "Stkcd + year + prov_year"), ("2023年状态×年度", "Stkcd + st_year")):
        m, b, se, pv = twfe(d, y, fe)
        r[lab] = {"cell": cell(b, se, pv), "N": int(m._N)}
    # 公司线性趋势：在公司内对年份做线性回归取残差（Frisch-Waugh），再含年度虚拟变量回归
    dd = d.dropna(subset=[y] + XS[y]).copy()
    dd = dd[dd.groupby("Stkcd").year.transform("count") >= 3]
    yd = pd.get_dummies(dd.year, prefix="yr", drop_first=True).astype(float)
    dd = pd.concat([dd, yd], axis=1)
    cols = [y, "post"] + XS[y] + list(yd.columns)
    t_c = dd.year - dd.groupby("Stkcd").year.transform("mean")
    for c in cols:
        v = dd[c].astype(float)
        vc = v - v.groupby(dd.Stkcd).transform("mean")
        slope = (vc * t_c).groupby(dd.Stkcd).transform("sum") / (t_c ** 2).groupby(dd.Stkcd).transform("sum")
        dd[c + "_r"] = vc - slope * t_c
    m = pf.feols(f"{y}_r ~ post_r + {' + '.join(c + '_r' for c in XS[y] + list(yd.columns))} - 1", dd, vcov={"CRV1": "Stkcd"})
    t = m.tidy().loc["post_r"]
    r["公司线性趋势"] = {"cell": cell(float(t.Estimate), float(t["Std. Error"]), float(t["Pr(>|t|)"])), "N": int(m._N)}
    # 提前时点安慰剂：只用入表前的年份，把入表时点提前两年
    pre_d = d[d.year < d["first"].fillna(9999)].copy()
    pre_d = pre_d[pre_d.year <= 2023] if y != "absDA" else pre_d[(pre_d.year >= 2022) & (pre_d.year <= 2024)]
    pre_d["post"] = ((pre_d.treat == 1) & (pre_d.year >= pre_d["first"] - 2)).astype(int)
    m, b, se, pv = twfe(pre_d, y)
    r["入表时点提前两年（安慰剂）"] = {"cell": cell(b, se, pv), "N": int(m._N)}
    alt[y] = r
res["alt_fe"] = alt
res["alt_outcomes"] = {y: base[y]["cell"] for y in ("capta", "capsales", "loss")}

print("step:", ' 7. 动态效应图', flush=True)
# ---------------- 7. 动态效应图：Callaway-Sant'Anna（通用基期）与双向固定效应事件研究 ----------------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
font_manager.fontManager.addfont("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc")
plt.rcParams.update({"font.family": "WenQuanYi Zen Hei", "font.size": 8.5, "axes.unicode_minus": False})
fig, axes = plt.subplots(1, 2, figsize=(15.5 / 2.54, 6.2 / 2.54))
for ax, (y, title) in zip(axes, [("caprate", "(a) 研发资本化率"), ("absDA", "(b) |可操纵应计利润|")]):
    e = ev[y]
    ks = sorted(e)
    b = np.array([e[k][0] for k in ks]); se = np.array([e[k][1] for k in ks])
    ax.axhline(0, color="0.5", lw=0.6); ax.axvline(-0.5, color="0.5", lw=0.6, ls=":")
    ax.errorbar(ks, b, yerr=1.96 * se, fmt="o", color="black", ms=3.5, capsize=2.5, lw=0.8)
    ax.set_xticks(ks); ax.set_title(title, fontsize=8.5); ax.set_xlabel("相对入表年份（入表前一年为基期）")
    ax.tick_params(labelsize=7.5, direction="in")
axes[0].set_ylabel("ATT 与 95% 置信区间")
fig.tight_layout(w_pad=1.2); fig.savefig(FIG, dpi=300)

json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1, default=str)
print(json.dumps({k: res[k] for k in ("twfe", "cs", "did2s", "stacked", "bacon", "alt_fe")}, ensure_ascii=False, indent=1, default=str))
