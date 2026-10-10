"""第 6 版：用附注明细拆分入表的利润效应，并检验摊销政策。
用法：python notes_analysis.py 数据资源附注明细.xlsx 入表财务效应分析样本.csv csmar/analysis6.pkl 输出.json
  1. 拆分：入表额 E（数据资源期末−期初）＝新增资本化 G −本期摊销 A −本期减值 I −处置等转出的账面价值 D（＋差额）；
     其中 G ＝无形资产原值本期增加＋存货、开发支出中数据资源的净增加。
  2. 跨期回转：两年都入表的企业，2025 年的摊销与 2024 年入表额之比；2025 年入表额为负（摊销超过新增）的企业数。
  3. 摊销政策：使用寿命与摊销方法的分布；使用寿命、隐含摊销率与入表前一年经营状态（亏损、利润下滑、微利）的关系。"""
import json, sys
import numpy as np, pandas as pd
import statsmodels.formula.api as smf

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
json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
