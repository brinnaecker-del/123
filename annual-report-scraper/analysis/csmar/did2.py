"""探索性检验：入表规模与研发规模之比、按 2023 年规模与经营状态的调节、倾向得分匹配双重差分。"""
import numpy as np, pandas as pd, pyfixest as pf
import statsmodels.formula.api as smf
p = pd.read_pickle("csmar/analysis.pkl")
d = p[(p.year >= 2021) & (p.year <= 2025)].copy()
def show(m, keys):
    t = m.tidy()
    return "  ".join(f"{k}={t.loc[k,'Estimate']:.4f}(p={t.loc[k,'Pr(>|t|)']:.3f})" for k in keys if k in t.index)
# 入表规模与研发资本化规模
t = p[(p.adopt_now == 1) & (p.year.isin([2024, 2025]))].copy()
t["DR_l"] = t.groupby("Stkcd").DR.shift(1)
t["newDR"] = np.where(t.year == 2024, t.DR, t.DR - t.DR_l.fillna(0))
r = (t.newDR / t.rdcap).where(t.rdcap > 0)
print("新增数据资源 / 当年资本化研发投入：中位数 %.3f，均值 %.3f，N=%d；资本化研发为 0 的入表公司 %d 家" % (r.median(), r.clip(upper=5).mean(), r.notna().sum(), (t.rdcap == 0).sum()))
print("新增数据资源 / 当年研发投入：中位数 %.4f" % (t.newDR / t.RDSpendSum).where(t.RDSpendSum > 0).median())

# 2023 年特征分组：规模（行业内中位数以下）、承压（2023 亏损或利润下滑）
pre = p[p.year == 2023][["Stkcd", "size", "loss", "decl", "ind"]].copy()
pre["smallfirm"] = (pre["size"] < pre.groupby("ind")["size"].transform("median")).astype(int)
pre["press"] = ((pre.loss == 1) | (pre.decl == 1)).astype(int)
d = d.merge(pre[["Stkcd", "smallfirm", "press"]], on="Stkcd", how="left")
ctrl = "size + lev + roa + growth + age"
print("\n===== 调节：post × 小规模、post × 承压（2023 年状态）")
for y in ("caprate", "capta", "absDA", "small"):
    xs = (ctrl + (" + rdint" if y == "caprate" else "")) if y != "small" else "size + lev + growth + age"
    dd = d.dropna(subset=[y, "smallfirm", "press"]).copy()
    dd["post_s"] = dd.post * dd.smallfirm; dd["post_p"] = dd.post * dd.press
    m = pf.feols(f"{y} ~ post + post_s + post_p + {xs} | Stkcd + year", dd, vcov={"CRV1": "Stkcd"})
    print(f"{y:<8} {show(m, ['post', 'post_s', 'post_p'])}")

print("\n===== 倾向得分匹配后的双重差分（2023 年特征，同行业 1:3 近邻，有放回）")
base = p[p.year == 2023].dropna(subset=["size", "lev", "roa", "growth", "soe", "ind"]).copy()
base["rdint"] = base.rdint.fillna(0); base["caprate"] = base.caprate.fillna(0)
base["letter"] = base.ind.str[0]
ps = smf.logit("treat ~ size + lev + roa + growth + soe + rdint + caprate + C(letter)", base).fit(disp=0)
base["ps"] = ps.predict(base)
pairs = []
for _, r in base[base.treat == 1].iterrows():
    pool = base[(base.treat == 0) & (base.letter == r.letter)]
    if len(pool) == 0:
        continue
    near = pool.iloc[(pool.ps - r.ps).abs().argsort()[:3]]
    pairs += [r.Stkcd] + list(near.Stkcd)
w = pd.Series(pairs).value_counts()
md = d[d.Stkcd.isin(w.index)].copy(); md["w"] = md.Stkcd.map(w)
tr, co = base[base.treat == 1], base[base.Stkcd.isin(set(pairs)) & (base.treat == 0)]
print("匹配：处理组 %d 家，对照组 %d 家（去重）" % (tr.Stkcd.nunique(), co.Stkcd.nunique()))
bal = pd.DataFrame({"处理组": tr[["size", "lev", "roa", "rdint", "caprate", "soe"]].mean(),
                    "匹配前对照": base[base.treat == 0][["size", "lev", "roa", "rdint", "caprate", "soe"]].mean(),
                    "匹配后对照": co.set_index("Stkcd").loc[[s for s in pairs if s not in set(tr.Stkcd)], ["size", "lev", "roa", "rdint", "caprate", "soe"]].mean()})
print(bal.round(4).to_string())
for y in ("caprate", "capta", "absDA", "DA", "small", "loss"):
    xs = (ctrl + (" + rdint" if y == "caprate" else "")) if y not in ("small", "loss") else "size + lev + growth + age"
    m = pf.feols(f"{y} ~ post + {xs} | Stkcd + year", md.dropna(subset=[y]), vcov={"CRV1": "Stkcd"}, weights="w")
    print(f"{y:<8} N={m._N:<5} {show(m, ['post'])}")
