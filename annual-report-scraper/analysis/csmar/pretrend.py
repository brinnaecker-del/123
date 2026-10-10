"""第 14 步：平行趋势与控制变量设定的检验。
  1. 2024 年批次的事件研究（从未入表企业为对照，以 2023 年为基期）：研发资本化率、|可操纵应计|、微利、真实盈余管理三项指标及合计，
     报告各期系数与 95% 置信区间，以及入表前系数联合为零的 Wald 检验（按公司聚类）；
  2. Callaway-Sant'Anna 动态效应（双重稳健，从未入表企业为对照，通用基期为入表前一年），供图 3 使用；
  3. 真实盈余管理 2021 年差异的稳健性：逐年缩尾 5%/95%、行业×年度固定效应、去掉 2021 年；
  4. 控制变量设定：不加控制变量、剔除总资产收益率、控制变量取上一年值；
  5. 与截面设计的对比（郑心泓和徐雨，2026）：2024 年截面上应计、真实盈余管理（原值与绝对值）对数据资源占总资产比重回归；
     同一回归改用 2023 年（入表前）的被解释变量作安慰剂；剔除入表强度最高的一家、改用是否入表的虚拟变量；真实盈余管理绝对值的双重差分。
用法：python pretrend.py csmar/analysis6.pkl 输出.json"""
import json, sys, warnings
import numpy as np, pandas as pd, pyfixest as pf
from scipy import stats
from differences import ATTgt

warnings.filterwarnings("ignore")
AP, OUT = sys.argv[1:3]
p = pd.read_pickle(AP).sort_values(["Stkcd", "year"])
C = ["size", "lev", "roa", "growth", "age"]
for c in C + ["rdint"]:
    p[c + "_l"] = p.groupby("Stkcd")[c].shift(1)
d = p[p.year.between(2021, 2025)].copy()
d["ind_y"] = d.ind.astype(str) + "_" + d.year.astype(str)
XS = {"caprate": C + ["rdint"], "absDA": C, "small": ["size", "lev", "growth", "age"],
      "abCFO": C, "abPROD": C, "abDISX": C, "REM": C}


def star(pv): return "***" if pv < 0.01 else "**" if pv < 0.05 else "*" if pv < 0.1 else ""
def cell(b, se, pv): return f"{b:.4f}{star(pv)}\n({b / se:.2f})"


def event(dd, y, xs, fe="Stkcd + year"):
    """2024 年批次相对从未入表企业的事件研究；返回各期系数、95% 置信区间与入表前联合检验。"""
    e = dd[dd["first"].isna() | (dd["first"] == 2024)].dropna(subset=[y] + xs).copy()
    ks = [k for k in (2021, 2022, 2024, 2025) if ((e["first"] == 2024) & (e.year == k)).any()]
    for k in ks:
        e[f"T{k}"] = ((e["first"] == 2024) & (e.year == k)).astype(int)
    m = pf.feols(f"{y} ~ {' + '.join(f'T{k}' for k in ks)} + {' + '.join(xs)} | {fe}", e, vcov={"CRV1": "Stkcd"})
    t = m.tidy()
    out = {str(k): [round(float(t.loc[f"T{k}", "Estimate"]), 4), round(float(t.loc[f"T{k}", "Std. Error"]), 4),
                    round(float(t.loc[f"T{k}", "Pr(>|t|)"]), 3)] for k in ks}
    pre = [f"T{k}" for k in ks if k < 2023]
    names = list(m._coefnames); idx = [names.index(v) for v in pre]
    bvec = np.array([float(t.loc[v, "Estimate"]) for v in pre]); V = np.asarray(m._vcov)[np.ix_(idx, idx)]
    w = float(bvec @ np.linalg.solve(V, bvec))
    out["joint_pre"] = {"k": len(pre), "chi2": round(w, 3), "p": round(float(1 - stats.chi2.cdf(w, len(pre))), 3)}
    out["N"] = int(m._N)
    return out


def twfe(dd, y, xs, fe="Stkcd + year"):
    dd = dd.dropna(subset=[y] + xs)
    rhs = " + ".join(["post"] + xs)
    m = pf.feols(f"{y} ~ {rhs} | {fe}", dd, vcov={"CRV1": "Stkcd"})
    t = m.tidy().loc["post"]
    b, se, pv = float(t.Estimate), float(t["Std. Error"]), float(t["Pr(>|t|)"])
    return {"b": round(b, 4), "se": round(se, 4), "p": round(pv, 3), "N": int(m._N), "cell": cell(b, se, pv)}


res = {"event2024": {}, "cs_event": {}, "rem2021": {}, "controls": {}}
# 1. 事件研究与联合检验
for y, xs in XS.items():
    res["event2024"][y] = event(d, y, xs)
# 2. Callaway-Sant'Anna 动态效应
for y in ("caprate", "absDA", "small", "REM"):
    dd = d.dropna(subset=[y] + XS[y]).copy()
    dd["gc"] = dd["first"]
    att = ATTgt(data=dd.set_index(["Stkcd", "year"]), cohort_column="gc", base_period="universal")
    att.fit(formula=f"{y} ~ " + " + ".join(XS[y]), est_method="dr", control_group="never_treated", progress_bar=False)
    e = att.aggregate("event")
    res["cs_event"][y] = {str(int(k)): [round(float(r.iloc[0]), 4), round(float(r.iloc[1]), 4) if pd.notna(r.iloc[1]) else None]
                          for k, r in e.iterrows()}
# 3. 真实盈余管理 2021 年差异的稳健性
w = d.copy()
for y in ("REM", "abPROD", "abCFO"):
    lo = w.groupby("year")[y].transform(lambda s: s.quantile(0.05)); hi = w.groupby("year")[y].transform(lambda s: s.quantile(0.95))
    w[y] = w[y].clip(lo, hi)
for y in ("REM", "abPROD", "abCFO"):
    res["rem2021"][y] = {"winsor5": event(w, y, C), "ind_year": event(d, y, C, fe="Stkcd + ind_y"),
                         "twfe_2022_2025": twfe(d[d.year >= 2022], y, C), "twfe_winsor5": twfe(w, y, C)}
# 4. 控制变量设定
for y in ("caprate", "absDA", "small", "REM"):
    xs = XS[y]
    res["controls"][y] = {"base": twfe(d, y, xs), "none": twfe(d, y, []), "no_roa": twfe(d, y, [x for x in xs if x != "roa"]),
                          "lagged": twfe(d, y, [x + "_l" for x in xs])}
# 5. 与截面设计的对比：2024 年数据资源占总资产比重（Data）对盈余管理的截面回归，及其在入表前一年（2023 年）的安慰剂
d["absREM"] = d.REM.abs()
data24 = d[d.year == 2024].set_index("Stkcd").eval("DR.fillna(0) / TA")
XC = ["size", "roa", "loss", "growth", "lev", "inst"]
res["cross"] = {"n_data_pos": int((data24 > 0).sum())}
for y in ("DA", "absDA", "REM", "absREM"):
    for yr in (2024, 2023):
        x = d[d.year == yr].copy()
        x["data"] = x.Stkcd.map(data24)
        x = x.dropna(subset=[y, "data", "ind"] + XC)
        m = pf.feols(f"{y} ~ data + {' + '.join(XC)} | ind", x, vcov="hetero")
        t = m.tidy().loc["data"]
        res["cross"][f"{y}_{yr}"] = {"b": round(float(t.Estimate), 4), "t": round(float(t["t value"]), 2), "p": round(float(t["Pr(>|t|)"]), 3),
                                    "N": int(m._N), "cell": cell(float(t.Estimate), float(t["Std. Error"]), float(t["Pr(>|t|)"]))}
# 截面关联是否来自个别入表强度极高的企业：剔除 Data 最高的一家；改用是否入表的虚拟变量
x24 = d[d.year == 2024].copy(); x24["data"] = x24.Stkcd.map(data24); x24["adopt"] = (x24.data > 0).astype(int)
top1 = x24.sort_values("data", ascending=False).iloc[0]
res["cross"]["top1"] = {"name": top1.ShortName, "data": round(float(top1.data), 4), "REM": round(float(top1.REM), 4)}
for lab, xx, var in (("excl_top1", x24[x24.Stkcd != top1.Stkcd], "data"), ("adopt_dummy", x24, "adopt")):
    for y in ("REM", "absREM"):
        xy = xx.dropna(subset=[y, var, "ind"] + XC)
        t = pf.feols(f"{y} ~ {var} + {' + '.join(XC)} | ind", xy, vcov="hetero").tidy().loc[var]
        res["cross"][f"{y}_{lab}"] = {"b": round(float(t.Estimate), 4), "t": round(float(t["t value"]), 2), "p": round(float(t["Pr(>|t|)"]), 3), "N": int(len(xy))}
res["cross"]["absREM_twfe"] = twfe(d, "absREM", C)
dd = d.dropna(subset=["absREM"] + C).copy(); dd["gc"] = dd["first"]
att = ATTgt(data=dd.set_index(["Stkcd", "year"]), cohort_column="gc", base_period="varying")
att.fit(formula="absREM ~ " + " + ".join(C), est_method="dr", control_group="never_treated", progress_bar=False)
sm_ = att.aggregate("simple"); bcs, scs = float(sm_.iloc[0, 0]), float(sm_.iloc[0, 1])
pcs = float(2 * (1 - stats.norm.cdf(abs(bcs / scs))))
res["cross"]["absREM_cs"] = {"b": round(bcs, 4), "se": round(scs, 4), "p": round(pcs, 3), "cell": cell(bcs, scs, pcs)}
json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
