"""第 6 版：用附注明细拆分入表的利润效应，并检验摊销政策。
用法：python notes_analysis.py 数据资源附注明细.xlsx 入表财务效应分析样本.csv csmar/analysis6.pkl 输出.json
  1. 拆分：入表额 E（数据资源期末−期初）＝新增资本化 G −本期摊销 A −本期减值 I −处置等转出的账面价值 D（＋差额）；
     其中 G ＝无形资产原值本期增加＋存货、开发支出中数据资源的净增加。
  2. 跨期回转：两年都入表的企业，2025 年的摊销与 2024 年入表额之比；2025 年入表额为负（摊销超过新增）的企业数。
  3. 摊销政策：使用寿命与摊销方法的分布；使用寿命、隐含摊销率与入表前一年经营状态（亏损、利润下滑、微利）的关系；
  4. 口径审计：新增额按来源分解（内部研发转入、外购、企业合并、未分类）；年初已有开发支出余额的企业，其研发转入可能包含 2024 年以前
     已资本化的支出，以 min(研发转入, 年初未标为数据资源的开发支出) 作上界；扣除上界、外购与合并后的入表额下限，
     以及用扣除上界后的入表额重估规模弹性与净利率影响；
  5. 样本构成：由高金名单到双重差分处理组、入表选择模型、利润效应与入表额拆分样本的各步数量（附表）。"""
import json, sys
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

NOTES, SAMPLE, AP, OUT = sys.argv[1:5]
n = pd.read_excel(NOTES, sheet_name="无形资产明细", dtype={"股票代码": str})
pol = pd.read_excel(NOTES, sheet_name="摊销政策", dtype={"股票代码": str})
n["code"] = n["文件"].str[:6]
assert len(pol) == len(n)
pol["code"] = n["code"].values                                         # 两页按同一顺序逐份写入
s = pd.read_csv(SAMPLE, dtype={"代码": str})
s["code"] = s.代码.str.zfill(6)
d = s.merge(n.drop(columns=["简称"]), left_on=["年度", "code"], right_on=["报告年度", "code"], how="left")
d = d.merge(pol[["报告年度", "code", "使用寿命下限(年)", "使用寿命上限(年)", "摊销方法"]], on=["报告年度", "code"], how="left")
d["year"] = d.年度
d["nonfin"] = d.行业 == "非金融"
got = d["表格样式"].fillna("未取到") != "未取到"
f0 = lambda c: d[c].fillna(0)
d["E"] = d.测算入表额
# 期初账面价值优先用期初原值−累计摊销−减值推算（个别年报漏列或误印「期初账面价值」，如山东高速 2025）
d["net_open"] = np.where(d.原值_期初.notna(), f0("原值_期初") - f0("摊销_期初") - f0("减值_期初"), f0("净值_期初"))
d["E_int"] = np.where(got & d.净值_期末.notna(), f0("净值_期末") - d.net_open, np.nan)
d["E_oth"] = d.E - d.E_int                                              # 存货、开发支出中的数据资源净增加
d["G_int"] = f0("原值_增加")
d["A"] = f0("摊销_增加")
d["I"] = f0("减值_增加")
d["D"] = f0("原值_减少") - f0("摊销_减少") - f0("减值_减少")
full = got & d.原值_期末.notna() & d.净值_期末.notna() & d.原值_增加.notna()   # 有完整滚动表的（文字披露只有期末数，不能拆）
d["G"] = np.where(full, d.E_oth + d.G_int, np.nan)
d["resid"] = np.where(full, d.E - (d.G - d.A - d.I - d.D), np.nan)
res = {"n": {"all": int(len(d)), "notes_full": int(full.sum())},
       "coverage": {"bs_int_pos": int((n["资产负债表数"].fillna(0) > 0).sum()),
                    "matched": int(((n["资产负债表数"].fillna(0) > 0) & (n["与资产负债表核对"] == "一致")).sum()),
                    "not_disclosed": int((n["与资产负债表核对"] == "附注未披露明细").sum()),
                    "balanced": [int((n[c].dropna().abs() < 1).sum()) for c in ("原值勾稽", "摊销勾稽", "净值勾稽")],
                    "checked": [int(n[c].notna().sum()) for c in ("原值勾稽", "摊销勾稽", "净值勾稽")]}}


def agg(g):
    g = g[g.G.notna()]
    out = {"firms": int(len(g)), "E": round(g.E.sum() / 1e8, 3), "G": round(g.G.sum() / 1e8, 3), "A": round(g.A.sum() / 1e8, 3),
           "I": round(g.I.sum() / 1e8, 3), "D": round(g.D.sum() / 1e8, 3), "resid": round(g.resid.sum() / 1e8, 4),
           "A_over_G": round(g.A.sum() / g.G.sum(), 4) if g.G.sum() > 0 else None,
           "A_over_G_median": round(float((g.A / g.G).where(g.G > 0).median()), 4),
           "share_A": round(float((g.A > 0).mean()), 3), "n_I": int((g.I > 0).sum()), "n_D": int((g.D > 1).sum()),
           "n_E_neg": int((g.E < 0).sum()), "G_buy": round(g.原值_增加_购置.fillna(0).sum() / 1e8, 3),
           "G_rd": round(g.原值_增加_内部研发.fillna(0).sum() / 1e8, 3), "G_merge": round(g.原值_增加_企业合并.fillna(0).sum() / 1e8, 3),
           "G_int": round(g.G_int.sum() / 1e8, 3), "E_oth": round(g.E_oth.sum() / 1e8, 3),
           "resid_abs_max": round(float(g.resid.abs().max()), 2)}
    return out


res["decomp"] = {f"{lab}_{y}": agg(g[g.year == y]) for lab, g in (("nonfin", d[d.nonfin]), ("all", d)) for y in (2024, 2025)}

# ---------------- 跨期回转：两年都在样本里的企业
a = d[d.year == 2024].set_index("code"); b = d[d.year == 2025].set_index("code")
both = a.index.intersection(b.index)
r = pd.DataFrame({"E24": a.loc[both, "E"], "A25": b.loc[both, "A"], "E25": b.loc[both, "E"], "G25": b.loc[both, "G"],
                  "full25": b.loc[both, "G"].notna(), "nonfin": a.loc[both, "nonfin"]})


def rev(r):
    rr = r[r.full25 & (r.E24 > 0)]
    return {"firms_both": int(len(r)), "firms_with_notes": int(len(rr)),
            "sum_E24": round(rr.E24.sum() / 1e8, 3), "sum_A25": round(rr.A25.sum() / 1e8, 3),
            "A25_over_E24_agg": round(rr.A25.sum() / rr.E24.sum(), 4),
            "A25_over_E24_median": round(float((rr.A25 / rr.E24).median()), 4),
            "n_E25_neg": int((r.E25 < 0).sum()), "n_E25_le_A25": int((rr.E25 < rr.A25).sum())}


res["reversal"] = {**rev(r), "nonfin": rev(r[r.nonfin])}

# ---------------- 摊销政策
d["L_lo"], d["L_hi"] = d["使用寿命下限(年)"], d["使用寿命上限(年)"]
d["L"] = (d.L_lo + d.L_hi) / 2
firm = d.sort_values("year").groupby("code").agg(L=("L", "first"), L_lo=("L_lo", "first"), meth=("摊销方法", "first"),
                                                 nonfin=("nonfin", "first"), first=("year", "first"))
meth = firm.meth.fillna("未披露").str.replace("（无形资产总体政策）", "", regex=False)
res["policy"] = {"firms": int(len(firm)), "with_life": int(firm.L.notna().sum()),
                 "life_dist": {str(k): int(v) for k, v in firm.L_lo.value_counts().sort_index().items()},
                 "life_mean": round(float(firm.L.mean()), 2), "life_median": float(firm.L.median()),
                 "range_disclosed": int((d.groupby("code").apply(lambda g: (g.L_hi > g.L_lo).any())).sum()),
                 "methods": {k: int(v) for k, v in meth.value_counts().items()}}
# 隐含摊销率：2025 年初已有数据资源（原值期初＞0）的企业，本年摊销 ÷ 原值年均余额
q = d[(d.year == 2025) & full & (d.原值_期初 > 0)].copy()
q["rate"] = (q.A / ((q.原值_期初 + q.原值_期末) / 2)).clip(0, 1)      # 本年摊销 ÷ 原值年均余额
res["policy"]["implied_rate_2025"] = {"firms": int(len(q)), "median": round(float(q.rate.median()), 4), "mean": round(float(q.rate.mean()), 4),
                                      "implied_life_median": round(float(1 / q.rate[q.rate > 0].median()), 2)}

# 使用寿命、隐含摊销率与入表前一年经营状态
p = pd.read_pickle(AP)
lag = p[["Stkcd", "year", "loss", "decl", "small", "size", "soe", "lev", "roa"]].copy(); lag["year"] += 1
z = d[d.nonfin].merge(lag.rename(columns={"Stkcd": "code"}), on=["code", "year"], how="left")
ind = p.drop_duplicates("Stkcd").set_index("Stkcd").ind
z["it"] = z.code.map(ind).fillna("").str[0].eq("I").astype(int)
zf = z.sort_values("year").groupby("code").first().reset_index()           # 每家公司取首次入表那年
zf = zf[zf.L.notna() & zf.loss.notna()].assign(first=lambda t: t.year)
res["policy"]["by_status"] = {k: {"n": int(len(g)), "L_mean": round(float(g.L.mean()), 2)}
                              for k, g in (("loss_prev", zf[zf.loss == 1]), ("decl_prev", zf[zf.decl == 1]),
                                           ("small_prev", zf[zf.small == 1]),
                                           ("normal_prev", zf[(zf.loss == 0) & (zf.decl == 0) & (zf.small == 0)]))}
reg = {}
for y, data in (("L", zf), ("rate", q.merge(lag.rename(columns={"Stkcd": "code"}), on=["code", "year"], how="left").assign(
        it=lambda t: t.code.map(ind).fillna("").str[0].eq("I").astype(int)).dropna(subset=["loss"]))):
    if len(data) < 20:
        continue
    m = smf.ols(f"{y} ~ loss + decl + small + size + soe + it" + (" + C(first)" if y == "L" else ""), data).fit(cov_type="HC1")
    reg[y] = {"N": int(m.nobs), "r2": round(float(m.rsquared), 3),
              "coef": {v: [round(float(m.params[v]), 3), round(float(m.pvalues[v]), 3)] for v in ("loss", "decl", "small", "size", "soe", "it")}}
res["policy"]["reg"] = reg

# ---------------- 口径审计：新增额来源与以前年度资本化支出的上界（非金融、附注明细完整）
lg = p[["Stkcd", "year", "DEV", "DR_dev", "DR_inv"]].copy(); lg["year"] += 1
lg = lg.rename(columns={"Stkcd": "code", "DEV": "DEV_l", "DR_dev": "DRdev_l", "DR_inv": "DRinv_l"})
cur = p[["Stkcd", "year", "DR_dev", "DR_inv"]].rename(columns={"Stkcd": "code"})
b = d[d.nonfin & full].merge(lg, on=["code", "year"], how="left").merge(cur, on=["code", "year"], how="left")
g0 = lambda c: b[c].fillna(0)                                            # CSMAR 未列示的科目即为 0
b["G_rd"], b["G_buy"], b["G_merge"] = g0("原值_增加_内部研发"), g0("原值_增加_购置"), g0("原值_增加_企业合并")
b["G_other"] = b.G_int - b.G_rd - b.G_buy - b.G_merge
b["dev_open"] = (g0("DEV_l") - g0("DRdev_l")).clip(lower=0)               # 年初未标为数据资源的开发支出
b["bound"] = np.minimum(b.G_rd, b.dev_open)
b["bound_wide"] = np.minimum(b.G_rd + b.G_other.clip(lower=0), b.dev_open)
b["dInv"], b["dDev"] = g0("DR_inv") - g0("DRinv_l"), g0("DR_dev") - g0("DRdev_l")
yi = lambda x: round(float(x) / 1e8, 6)                                 # 多保留几位，表中再四舍五入，避免逐项相加出现进位误差
res["bridge"] = {}
for y, g in b.groupby("year"):
    res["bridge"][str(y)] = {"firms": int(len(g)), "net_open": yi(g.net_open.sum()), "G_int": yi(g.G_int.sum()), "G_rd": yi(g.G_rd.sum()),
                             "G_buy": yi(g.G_buy.sum()), "G_merge": yi(g.G_merge.sum()), "G_other": yi(g.G_other.sum()),
                             "E_oth": yi(g.E_oth.sum()), "dInv": yi(g.dInv.sum()), "dDev": yi(g.dDev.sum()),
                             "A": yi(g.A.sum()), "I": yi(g.I.sum()), "D": yi(g.D.sum()), "net_close": yi(g.净值_期末.fillna(0).sum()),
                             "E": yi(g.E.sum()), "resid": yi(g.resid.sum()),
                             "rd_firms": int((g.G_rd > 0).sum()), "rd_clean": yi(g[g.dev_open == 0].G_rd.sum()),
                             "bound": yi(g.bound.sum()), "bound_firms": int((g.bound > 0).sum()), "bound_wide": yi(g.bound_wide.sum()),
                             "E_low": yi((g.E - g.bound - g.G_buy - g.G_merge).sum()),
                             "bound_top": [[r.简称, yi(r.bound)] for r in g.sort_values("bound", ascending=False).head(2).itertuples()]}
# 用扣除上界后的入表额重估：规模弹性与净利率影响（非金融、入表额为正）
adj = d[d.nonfin].merge(b[["code", "year", "bound"]], on=["code", "year"], how="left")
adj["E_adj"] = adj.E - adj.bound.fillna(0)
res["bridge"]["robust"] = {}
for y, g in adj.groupby("year"):
    out = {}
    for lab, col in (("raw", "E"), ("adj", "E_adj")):
        h = g[g[col] > 0].copy()
        h["lnE"], h["lnTA"] = np.log(h[col]), np.log(h.总资产)
        m = smf.ols("lnE ~ lnTA", h).fit(cov_type="HC1")
        bb, se = float(m.params.lnTA), float(m.bse.lnTA)
        out[lab] = {"N": int(len(h)), "elast": round(bb, 3), "ci": [round(bb - 1.96 * se, 3), round(bb + 1.96 * se, 3)],
                    "p_eq1": round(float(2 * (1 - stats.norm.cdf(abs((bb - 1) / se)))), 4),
                    "imp_median": round(float((100 * h[col] / h.营业收入).median()), 4),
                    "rho_rel_imp": round(float(stats.spearmanr(h[col] / h.总资产, h[col] / h.营业收入).statistic), 3)}
    out["dropped"] = int(((g.E > 0) & (g.E_adj <= 0)).sum())
    res["bridge"]["robust"][str(y)] = out
# 跨期比例：剔除 2024 年初已有数据资源余额的企业
o24 = d[(d.year == 2024)].set_index("code").net_open
rr2 = r[r.full25 & (r.E24 > 0) & r.nonfin & ~r.index.isin(o24[o24 > 0].index)]
res["reversal"]["nonfin_no_open"] = {"firms": int(len(rr2)), "A25_over_E24_agg": round(rr2.A25.sum() / rr2.E24.sum(), 4)}

# ---------------- 样本构成：高金名单→非金融入表企业→首次入表（双重差分处理组）→入表选择模型→利润效应与拆分样本
s0 = s.copy()
s0["Stkcd"] = s0.code.replace({"835184": "920184", "836208": "920208"})
first = p.drop_duplicates("Stkcd").set_index("Stkcd")["first"]
names = p.sort_values("year").drop_duplicates("Stkcd", keep="last").set_index("Stkcd").ShortName
X = ["loss", "decl", "small", "size", "lev", "growth", "cfo", "soe", "age", "rdint", "caprate"]
lagp = p[["Stkcd", "year", "ind"] + X].copy(); lagp["year"] += 1
lagp["rdint"] = lagp.rdint.fillna(0); lagp["caprate"] = lagp.caprate.fillna(0)
ok_lag = set(map(tuple, lagp.dropna(subset=X + ["ind"])[["Stkcd", "year"]].values))
flow = {}
for y in (2024, 2025):
    g = s0[s0.年度 == y]; nf = g[g.行业 == "非金融"]; pos = nf[nf.入表期末 > 0]
    prev = set(s0[(s0.年度 < y) & (s0.入表期末 > 0)].Stkcd)
    fy = set(first[first == y].index)
    flow[str(y)] = {"reports": int(len(g)), "fin": int((g.行业 != "非金融").sum()), "nonfin": int(len(nf)),
                    "not_listed": nf[nf.入表期末 <= 0].简称.tolist(), "nonfin_dr": int(len(pos)),
                    "first_gaojin": int((~pos.Stkcd.isin(prev)).sum()),
                    "csmar_only": [names[c] for c in sorted(fy - set(s0[s0.入表期末 > 0].Stkcd))],
                    "first_total": int(len(fy)),
                    "no_lag": [names[c] for c in sorted(c for c in fy if (c, y) not in ok_lag)],
                    "sel_events": int(sum((c, y) in ok_lag for c in fy)),
                    "profit_sample": int(((d.year == y) & d.nonfin & (d.E > 0)).sum()),
                    "notes_full": int(((d.year == y) & d.nonfin & full).sum())}
res["sample_flow"] = flow
json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
