"""论文正文引用的零散数字（描述性事实、分组比较、2025 年回转、子样本检验），统一在此计算并写入 JSON，供正文逐项核对。
用法：python paper_facts.py csmar/analysis.pkl 入表财务效应分析样本.csv 输出.json"""
import json, sys
import numpy as np, pandas as pd, pyfixest as pf
from scipy import stats

AP, SAMPLE, OUT = sys.argv[1:4]
p = pd.read_pickle(AP)
s = pd.read_csv(SAMPLE, dtype={"代码": str, "年度": str})
F = {}

# ---------------- 入表企业样本：总量与口径 ----------------
for y, g in s.groupby("年度"):
    F[f"n_{y}"] = int(len(g))
    F[f"sum_end_{y}_yi"] = round(g.入表期末.sum() / 1e8, 2)
    F[f"sum_new_{y}_yi"] = round(g.测算入表额.sum() / 1e8, 2)
    F[f"n_pos_{y}"] = int((g.测算入表额 > 0).sum())
    F[f"n_neg_{y}"] = int((g.测算入表额 < 0).sum())
    F[f"n_zero_{y}"] = int((g.测算入表额 == 0).sum())
    F[f"n_fin_{y}"] = int((g.行业 == "金融").sum())
F["n_firms"] = int(s.代码.nunique())
F["n_open_2024"] = int((s[s.年度 == "2024"].入表期初 > 0).sum())
g25 = s[s.年度 == "2025"]
op = g25[g25.入表期初 > 0]
F["n_open_2025"] = int(len(op))
F["n_open_decline_2025"] = int((op.测算入表额 < 0).sum())
F["share_open_decline_2025"] = round(100 * (op.测算入表额 < 0).mean(), 1)
F["n_first_2025"] = int((g25.入表期初 == 0).sum())

# ---------------- 净利率影响的分布、盈亏反转 ----------------
for y, g in s.groupby("年度"):
    pos = g[g.测算入表额 > 0]
    F[f"imp_med_pos_{y}"] = round(pos.净利率影响pp.median(), 3)
    F[f"imp_lt01_pos_{y}"] = int((pos.净利率影响pp < 0.1).sum())
    F[f"imp_ge1_pos_{y}"] = int((pos.净利率影响pp >= 1).sum())
    F[f"rel_med_pos_{y}"] = round(pos["相对重要性%"].median(), 4)
    flip = g[(g.净利润 > 0) & (g.净利润 - g.测算入表额 < 0)]
    F[f"flip_{y}"] = flip.简称.tolist()
    # 亏损企业若全部费用化亏损扩大的幅度（入表额占净亏损绝对值）
    lo = pos[pos.净利润 < 0]
    F[f"loss_share_med_{y}"] = round((lo.测算入表额 / lo.净利润.abs() * 100).median(), 2)

# ---------------- 亏损企业的放大效应：资产/收入 ----------------
for y, g in s.groupby("年度"):
    pos = g[(g.测算入表额 > 0)].copy()
    pos["AS"] = pos.总资产 / pos.营业收入
    nf = pos[pos.行业 == "非金融"]
    F[f"AS_med_loss_{y}"] = round(nf[nf.经营状态 == "亏损"].AS.median(), 2)
    F[f"AS_med_nonloss_{y}"] = round(nf[nf.经营状态 != "亏损"].AS.median(), 2)
    F[f"TA_med_loss_{y}_yi"] = round(pos[pos.经营状态 == "亏损"].总资产.median() / 1e8, 1)
    F[f"TA_med_nonloss_{y}_yi"] = round(pos[pos.经营状态 != "亏损"].总资产.median() / 1e8, 1)
    F[f"n_loss_pos_{y}"] = int((pos.经营状态 == "亏损").sum())
    F[f"n_decl_pos_{y}"] = int((pos.经营状态 == "下滑").sum())
    F[f"n_stable_pos_{y}"] = int((pos.经营状态 == "稳健").sum())

# ---------------- 2025 年回转的典型：海天瑞声 ----------------
h = s[s.简称 == "海天瑞声"].set_index("年度")
F["haitian_imp"] = {y: round(float(h.loc[y, "净利率影响pp"]), 2) for y in h.index}

# ---------------- 案例企业 ----------------
cases = {}
for name in ("开普云", "拓尔思", "中国移动"):
    c = s[s.简称 == name].set_index("年度")
    cases[name] = {y: {"期末万": round(c.loc[y, "入表期末"] / 1e4, 2), "新增万": round(c.loc[y, "测算入表额"] / 1e4, 2),
                       "存量占总资产%": round(c.loc[y, "存量相对重要性%"], 2), "新增占总资产%": round(c.loc[y, "相对重要性%"], 2),
                       "净利率%": round(c.loc[y, "净利率%"], 2), "影响pp": round(c.loc[y, "净利率影响pp"], 2),
                       "还原后净利率%": round(c.loc[y, "还原后净利率%"], 2), "营业收入亿": round(c.loc[y, "营业收入"] / 1e8, 2),
                       "总资产亿": round(c.loc[y, "总资产"] / 1e8, 2), "经营状态": c.loc[y, "经营状态"]} for y in c.index}
F["cases"] = cases

# ---------------- 新增数据资源相对于研发投入的规模 ----------------
mine = s.copy()
mine["Stkcd"] = mine.代码.replace({"835184": "920184", "836208": "920208"})
mine["year"] = mine.年度.astype(int)
x = mine[(mine.测算入表额 > 0) & (mine.行业 == "非金融")].merge(p[["Stkcd", "year", "RDSpendSum"]], on=["Stkcd", "year"], how="left")
r = (x.测算入表额 / x.RDSpendSum).where(x.RDSpendSum > 0)
F["new_over_rd_med_pct"] = round(100 * r.median(), 2)
F["new_over_rd_N"] = int(r.notna().sum())

# ---------------- 对照样本：入表企业数量 ----------------
F["treated_nonfin"] = int(p[p.treat == 1].Stkcd.nunique())
F["treated_first"] = {str(int(k)): int(v) for k, v in p[p.treat == 1].drop_duplicates("Stkcd")["first"].value_counts().sort_index().items()}

# ---------------- 子样本：2023 年亏损的入表企业此后是否更多进入微利区间（控制「2023 年状态×年度」） ----------------
d = p[(p.year >= 2021) & (p.year <= 2025)].copy()
pre = p[p.year == 2023][["Stkcd", "loss", "decl"]].rename(columns={"loss": "l23", "decl": "d23"})
d = d.merge(pre, on="Stkcd", how="left").dropna(subset=["l23"])
d["st_year"] = d.l23.astype(int).astype(str) + d.d23.fillna(0).astype(int).astype(str) + "_" + d.year.astype(str)
d["post_l"] = d.post * d.l23
F["n_treated_loss2023"] = int(d[(d.treat == 1) & (d.l23 == 1)].Stkcd.nunique())
sub = {}
for lab, dd in (("全部入表企业", d), ("2024年入表批次", d[d["first"].isna() | (d["first"] == 2024)])):
    sub[lab] = {}
    for y in ("small", "loss"):
        m = pf.feols(f"{y} ~ post + post_l + size + lev + growth + age | Stkcd + st_year", dd, vcov={"CRV1": "Stkcd"})
        t = m.tidy().loc["post_l"]
        sub[lab][y] = [round(float(t["Estimate"]), 4), round(float(t["Pr(>|t|)"]), 3)]
F["loss2023_sub"] = sub


# ---------------- 规模四分位、方差分解、承压的替代定义（入表额为正的样本） ----------------
import statsmodels.formula.api as smf
for y, g in s.groupby("年度"):
    g = g[g.测算入表额 > 0].copy()
    g["lnTA"] = np.log(g.总资产); g["lnrel"] = np.log(g["相对重要性%"]); g["lnimp"] = np.log(g.净利率影响pp)
    g["lnAS"] = np.log(g.总资产 / g.营业收入); g["fin"] = (g.行业 == "金融").astype(int)
    g["q"] = pd.qcut(g.lnTA, 4, labels=False)
    q = g.groupby("q").agg(TA=("总资产", "median"), E=("测算入表额", "median"), rel=("相对重要性%", "median"), imp=("净利率影响pp", "median"))
    F[f"quart_{y}"] = {"TA_yi": [round(q.TA[0] / 1e8, 2), round(q.TA[3] / 1e8, 2)], "E_wan": [round(q.E[0] / 1e4, 2), round(q.E[3] / 1e4, 2)],
                       "rel_pct": [round(q.rel[0], 4), round(q.rel[3], 5)], "imp_pp": [round(q.imp[0], 4), round(q.imp[3], 4)],
                       "rel_ratio": round(q.rel[0] / q.rel[3], 0)}
    F[f"var_{y}"] = {"lnimp": round(float(np.var(g.lnimp)), 2), "lnrel": round(float(np.var(g.lnrel)), 2), "lnAS": round(float(np.var(g.lnAS)), 2)}
    g["press30"] = ((g.净利润 < 0) | ((g.归母净利润上期 > 0) & (g.归母净利润 < 0.7 * g.归母净利润上期))).astype(int)
    m = smf.ols("lnrel ~ press30 + lnTA + fin", g).fit(cov_type="HC1")
    F[f"press30_{y}"] = [round(float(m.params.press30), 3), round(float(m.pvalues.press30), 3), int(g.press30.sum())]
    nf = g[g.fin == 0]
    m = smf.ols("lnimp ~ lnrel + loss + lnTA", nf.assign(loss=(nf.经营状态 == "亏损").astype(int))).fit(cov_type="HC1")
    F[f"nonfin_{y}"] = {"rho": round(float(stats.spearmanr(nf["相对重要性%"], nf.净利率影响pp).statistic), 3),
                        "loss": [round(float(m.params.loss), 3), round(float(m.pvalues.loss), 3)], "N": int(len(nf))}
g = s[(s.年度 == "2025") & (s.入表期末 > 0)].copy()
g["lnTA"] = np.log(g.总资产); g["fin"] = (g.行业 == "金融").astype(int); g["loss"] = (g.经营状态 == "亏损").astype(int)
g["imp_stock"] = g.入表期末 / g.营业收入 * 100
m = smf.ols("np.log(imp_stock) ~ np.log(g['存量相对重要性%']) + loss + lnTA + fin", g).fit(cov_type="HC1")
F["stock_2025"] = {"rho": round(float(stats.spearmanr(g["存量相对重要性%"], g.imp_stock).statistic), 3),
                   "loss": [round(float(m.params.loss), 3), round(float(m.pvalues.loss), 3)], "N": int(len(g))}

# ---------------- 入表选择样本的均值比较（t 值） ----------------
X = ["loss", "decl", "small", "size", "lev", "growth", "cfo", "soe", "age", "rdint", "caprate"]
lag = p[["Stkcd", "year", "ind"] + X].copy(); lag["year"] += 1
rows = []
for t in (2024, 2025):
    a = lag[lag.year == t].merge(p[p.year == t][["Stkcd", "first"]], on="Stkcd")
    a = a[~((t == 2025) & (a["first"] == 2024))]
    a["y"] = (a["first"] == t).astype(int)
    a["rdint"] = a.rdint.fillna(0); a["caprate"] = a.caprate.fillna(0)
    rows.append(a.dropna(subset=X + ["ind"]))
sel = pd.concat(rows)
F["descB_t"] = {v: round(float(stats.ttest_ind(sel[sel.y == 1][v], sel[sel.y == 0][v], equal_var=False).statistic), 2) for v in X}

# ---------------- 拟合优度、精确的四分位中位数 ----------------
for y, g in s.groupby("年度"):
    g = g[g.测算入表额 > 0].copy()
    g["lnimp"] = np.log(g.净利率影响pp); g["lnrel"] = np.log(g["相对重要性%"]); g["lnE"] = np.log(g.测算入表额)
    F[f"r2_{y}"] = {"lnE": round(float(smf.ols("lnimp ~ lnE", g).fit().rsquared), 3), "lnrel": round(float(smf.ols("lnimp ~ lnrel", g).fit().rsquared), 3)}
    g["q"] = pd.qcut(np.log(g.总资产), 4, labels=False)
    F[f"quart_exact_{y}"] = {k: [float(g[g.q == 0][c].median()), float(g[g.q == 3][c].median())]
                             for k, c in (("imp_pp", "净利率影响pp"), ("rel_pct", "相对重要性%"))}

# ---------------- 与 CSMAR 的核对（含金融业的全部 A 股） ----------------
import os
mp = os.path.join(os.path.dirname(AP), "master.pkl")
if os.path.exists(mp):
    m = pd.read_pickle(mp)
    chk = mine.merge(m[["Stkcd", "year", "TA", "DR"]], on=["Stkcd", "year"], how="left")
    F["csmar_check"] = {"N": int(len(chk)), "TA_same": int(((chk.总资产 - chk.TA).abs() < 1).sum()),
                        "DR_same": int(((chk.入表期末 - chk.DR.fillna(0)).abs() < 1).sum())}
    for y in (2024, 2025):
        cs_firms = set(m[(m.year == y) & (m.DR > 0)].Stkcd)
        gj = set(mine[(mine.year == y)].Stkcd)
        F[f"csmar_list_{y}"] = {"csmar": len(cs_firms), "covered_by_gaojin": len(cs_firms & gj)}

json.dump(F, open(OUT, "w"), ensure_ascii=False, indent=1)
print(json.dumps(F, ensure_ascii=False, indent=1))
