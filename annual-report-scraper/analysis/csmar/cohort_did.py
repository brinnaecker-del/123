"""第 13 步：分批次的双重差分，检验 2024、2025 两批入表企业的处理效应是否不同。
  1. 双向固定效应：从未入表企业分别与 2024 年批次、2025 年批次组成样本（设定与 robust.py「仅 2024 年入表批次」相同）；
  2. Callaway-Sant'Anna 分批次平均处理效应（双重稳健，从未入表企业为对照）；两批之差用堆叠样本中 post×2025 年批次的系数检验；
  3. 2025 年批次的事件研究（以 2024 年为基期）与各组微利比例，判断入表前是否已有趋势；
  4. 2025 年批次中 2025 年微利的企业，若把当年入表额全部费用化，是否仍处于微利区间（入表额取年报手工数，名单外企业取 CSMAR 数据资源余额之差）。
用法：python cohort_did.py csmar/analysis6.pkl 入表财务效应分析样本.csv 输出.json"""
import json, sys, warnings
import pandas as pd, pyfixest as pf
from scipy import stats
from differences import ATTgt

warnings.filterwarnings("ignore")
AP, SAMPLE, OUT = sys.argv[1:4]
p = pd.read_pickle(AP)
d = p[p.year.between(2021, 2025)].copy()


def star(pv): return "***" if pv < 0.01 else "**" if pv < 0.05 else "*" if pv < 0.1 else ""
def cell(b, se, pv): return f"{b:.4f}{star(pv)}\n({b / se:.2f})"
def pval(b, se): return float(2 * (1 - stats.norm.cdf(abs(b / se))))


C = ["size", "lev", "roa", "growth", "age"]
XS = {"caprate": C + ["rdint"], "absDA": C, "small": ["size", "lev", "growth", "age"], "REM": C}
res = {"post_years": {"2024": [2024, 2025], "2025": [2025]}, "n_treated": {}, "twfe": {}, "cs": {}}
for g in (2024, 2025):
    res["n_treated"][str(g)] = int(d[d["first"] == g].Stkcd.nunique())
for y, xs in XS.items():
    res["twfe"][y], res["cs"][y] = {}, {}
    for g in (2024, 2025):
        dd = d[d["first"].isna() | (d["first"] == g)].dropna(subset=[y] + xs)
        m = pf.feols(f"{y} ~ post + {' + '.join(xs)} | Stkcd + year", dd, vcov={"CRV1": "Stkcd"})
        t = m.tidy().loc["post"]
        b, se, pv = float(t.Estimate), float(t["Std. Error"]), float(t["Pr(>|t|)"])
        res["twfe"][y][str(g)] = {"b": round(b, 4), "se": round(se, 4), "p": round(pv, 3), "N": int(m._N), "cell": cell(b, se, pv)}
    dd = d.dropna(subset=[y] + xs).copy()
    dd["gc"] = dd["first"]
    att = ATTgt(data=dd.set_index(["Stkcd", "year"]), cohort_column="gc", base_period="varying")
    att.fit(formula=f"{y} ~ " + " + ".join(xs), est_method="dr", control_group="never_treated", progress_bar=False)
    a = att.aggregate("cohort")
    out = {}
    for g in (2024, 2025):
        row = a[a.index.get_level_values(-1) == g].iloc[0]
        b, se = float(row.iloc[0]), float(row.iloc[1])
        out[str(g)] = {"b": round(b, 4), "se": round(se, 4), "p": round(pval(b, se), 3), "cell": cell(b, se, pval(b, se))}
    res["cs"][y] = out
    # 两批之差：两个子样本（各自与从未入表企业组成）堆叠，固定效应按子样本区分，post×2025 年批次的系数即两批之差；按公司聚类
    st = pd.concat([d[d["first"].isna() | (d["first"] == g)].assign(stk=g) for g in (2024, 2025)]).dropna(subset=[y] + xs)
    st["sid"] = st.Stkcd.astype(str) + "_" + st.stk.astype(str)
    st["syear"] = st.year.astype(str) + "_" + st.stk.astype(str)
    st["post25"] = st.post * (st.stk == 2025)
    m = pf.feols(f"{y} ~ post + post25 + {' + '.join(xs)} | sid + syear", st, vcov={"CRV1": "Stkcd"})
    t = m.tidy().loc["post25"]
    res["twfe"][y]["diff_2025_minus_2024"] = {"b": round(float(t.Estimate), 4), "se": round(float(t["Std. Error"]), 4),
                                               "p": round(float(t["Pr(>|t|)"]), 3)}
# 2025 年批次的事件研究：从未入表企业为对照，以 2024 年为基期
e = d[d["first"].isna() | (d["first"] == 2025)].copy()
for k in (2021, 2022, 2023, 2025):
    e[f"T{k}"] = ((e["first"] == 2025) & (e.year == k)).astype(int)
res["event2025"] = {}
for y, xs in XS.items():
    es = e.dropna(subset=[y] + xs)
    ts = [f"T{k}" for k in (2021, 2022, 2023, 2025) if es[f"T{k}"].sum() > 0]     # |DA| 始于 2022 年，没有 2021 年
    te = pf.feols(f"{y} ~ {' + '.join(ts)} + {' + '.join(xs)} | Stkcd + year", es, vcov={"CRV1": "Stkcd"}).tidy()
    res["event2025"][y] = {k: [round(float(te.loc[k, "Estimate"]), 4), round(float(te.loc[k, "Pr(>|t|)"]), 3)] for k in ts}
grp = d["first"].fillna(0).astype(int).map({0: "never", 2024: "c2024", 2025: "c2025"})
res["small_rate"] = {g: {str(y): round(float(v), 3) for y, v in s_.items()} for g, s_ in d.groupby(grp).apply(lambda t: t.groupby("year").small.mean()).iterrows()}
c25 = d[d["first"] == 2025]
res["small_count_c2025"] = {str(y): [int(g.small.sum()), int(len(g))] for y, g in c25.groupby("year")}
# 2025 年微利的 2025 年批次企业：扣除当年入表额后的总资产收益率
m = pd.read_csv(SAMPLE, dtype={"代码": str})
m["Stkcd"] = m.代码.str.zfill(6).replace({"835184": "920184", "836208": "920208"})
E = m[m.年度 == 2025].set_index("Stkcd").测算入表额
x = c25[(c25.year == 2025) & (c25.small == 1)].copy()
dr = p.pivot_table(index="Stkcd", columns="year", values="DR")
x["E"] = x.Stkcd.map(E).fillna(x.Stkcd.map(dr[2025].fillna(0) - dr[2024].fillna(0)))
x["roa_wo_E"] = (x.NI - x.E) / x.TA
res["small_2025_mechanical"] = {"firms": int(len(x)), "still_small_wo_E": int(((x.roa_wo_E >= 0) & (x.roa_wo_E < 0.01)).sum()),
                                "loss_wo_E": int((x.roa_wo_E < 0).sum()), "max_E_TA_pct": round(float((100 * x.E / x.TA).max()), 3)}
json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
