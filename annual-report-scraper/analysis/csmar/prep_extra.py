"""第 11 步：读入第 6 版补充的 CSMAR 表，构造真实盈余管理、有效税率、外部监督与问询函变量，存为 csmar/analysis6.pkl。
需要先跑完第 0—2 步（csmar/master.pkl、csmar/analysis.pkl）。新表解压到 csmar/ 的子文件夹：
  FS_Comins（营业成本、销售费用、管理费用、利润总额、所得税费用，2019–2025）
  FS_Combas（存货净额，2019–2020）；FS_Combas（半年报：三项「其中：数据资源」与资产总计，2024–2026 年 6 月 30 日）
  PLED_STKRATIO（股票质押比率，周度）；CMS_InquiriesSE（问询函，2024 年起发函）；FIN_Audit（审计事务所、审计费用）
  AF_CFEATUREPROFILE（分析师关注度）；INI_HolderSystematics（机构持股）
用法：python prep_extra.py"""
import glob
import numpy as np, pandas as pd
import statsmodels.api as sm

DATE = r"^\d{4}-\d\d-\d\d$"


def find(name, key):
    for f in glob.glob(f"csmar/*/{name}.xlsx"):
        d = pd.read_excel(f, dtype=str)
        if key(set(d.columns)):
            return d
    raise SystemExit(f"没找到 {name}")


def clean(d, code, date, md=None):
    d = d[d[date].astype(str).str.match(DATE)].copy()                    # 去掉表头的中文名、单位两行
    if md:
        d = d[d[date].str.endswith(md)]
    if "Typrep" in d.columns:
        d = d[d.Typrep == "A"]
    d = d.rename(columns={code: "Stkcd"})
    d["year"] = d[date].str[:4].astype(int)
    return d.drop_duplicates(["Stkcd", "year"])


def num(d, cols):
    for c in cols:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d


# ---------------- 财务报表补充字段
inc = num(clean(find("FS_Comins", lambda c: "B001201000" in c), "Stkcd", "Accper", "12-31"),
          ["B001201000", "B001209000", "B001210000", "B001000000", "B002100000"])
inc = inc.rename(columns={"B001201000": "COGS", "B001209000": "SELL", "B001210000": "ADMIN", "B001000000": "EBT", "B002100000": "TAX"})
inv = num(clean(find("FS_Combas", lambda c: "A001123000" in c and not c & {"A001111000", "A001000000"}), "Stkcd", "Accper", "12-31"),
          ["A001123000"]).rename(columns={"A001123000": "INV0"})
half = num(clean(find("FS_Combas", lambda c: "A001218201" in c and "A001111000" not in c), "Stkcd", "Accper", "06-30"),
           ["A001123101", "A001218201", "A001219101", "A001000000"])
half["DR_h"] = half[["A001123101", "A001218201", "A001219101"]].fillna(0).sum(axis=1)
half = half.rename(columns={"A001000000": "TA_h"})[["Stkcd", "year", "DR_h", "TA_h"]]

m = pd.read_pickle("csmar/master.pkl")
m = m[m.fin == 0].merge(inc[["Stkcd", "year", "COGS", "SELL", "ADMIN", "EBT", "TAX"]], on=["Stkcd", "year"], how="left")
m = m.merge(inv[["Stkcd", "year", "INV0"]], on=["Stkcd", "year"], how="left")
m["INV"] = m.INV.where(m.year >= 2021, m.INV0)
prev = m[["Stkcd", "year", "TA", "REV", "INV"]].copy(); prev["year"] += 1
prev2 = m[["Stkcd", "year", "REV"]].copy(); prev2["year"] += 2
m = m.merge(prev.rename(columns={"TA": "A1", "REV": "S1", "INV": "INV1"}), on=["Stkcd", "year"], how="left")
m = m.merge(prev2.rename(columns={"REV": "S2"}), on=["Stkcd", "year"], how="left")

# ---------------- 真实盈余管理（Roychowdhury, 2006）：行业—年度截面回归的残差
r = m[(m.year >= 2021) & (m.A1 > 0)].copy()
has_adm = r.ADMIN.notna()
r["y_cfo"] = r.CFO / r.A1
r["y_prod"] = (r.COGS + r.INV.fillna(0) - r.INV1.fillna(0)).where(r.INV.notna() | r.INV1.isna()) / r.A1
r["y_disx"] = (r.SELL.fillna(0) + r.ADMIN + r.RDEXP.fillna(0)).where(has_adm) / r.A1
r["x_inv"] = 1 / r.A1
r["x_s"] = r.REV / r.A1
r["x_ds"] = (r.REV - r.S1) / r.A1
r["x_dsl"] = (r.S1 - r.S2) / r.A1
r["x_sl"] = r.S1 / r.A1
V = ["y_cfo", "y_prod", "y_disx", "x_inv", "x_s", "x_ds", "x_dsl", "x_sl"]
for c in V:                                                                  # 逐年 1%/99% 缩尾后再回归
    lo, hi = r.groupby("year")[c].transform(lambda s: s.quantile(0.01)), r.groupby("year")[c].transform(lambda s: s.quantile(0.99))
    r[c] = r[c].clip(lo, hi)
MODELS = {"abCFO": ("y_cfo", ["x_inv", "x_s", "x_ds"]), "abPROD": ("y_prod", ["x_inv", "x_s", "x_ds", "x_dsl"]),
          "abDISX": ("y_disx", ["x_inv", "x_sl"])}
for k, (y, xs) in MODELS.items():
    r[k] = np.nan
    for _, d in r.dropna(subset=[y] + xs).groupby(["ind", "year"]):
        if len(d) < 10:
            continue
        fit = sm.OLS(d[y], sm.add_constant(d[xs])).fit()
        r.loc[d.index, k] = fit.resid
r["REM"] = r.abPROD - r.abCFO - r.abDISX                                     # 越大表示越倾向向上做高利润
for c in ("abCFO", "abPROD", "abDISX", "REM"):
    lo, hi = r[c].quantile([0.01, 0.99])
    r[c] = r[c].clip(lo, hi)
r["etr"] = (r.TAX / r.EBT).where(r.EBT > 0).clip(0, 1)

# ---------------- 外部监督与问询函
pl = find("PLED_STKRATIO", lambda c: "PledRatio" in c)
pl = pl[pl.EndDate.astype(str).str.match(DATE)].copy()
pl["year"] = pl.EndDate.str[:4].astype(int)
pl = pl.sort_values("EndDate").groupby(["Symbol", "year"]).tail(1)           # 每年最后一周的质押比例
pl = num(pl, ["PledRatio"]).rename(columns={"Symbol": "Stkcd", "PledRatio": "pled"})[["Stkcd", "year", "pled"]]
au = clean(find("FIN_Audit", lambda c: "Tcost" in c), "Stkcd", "Accper", "12-31")
au["big4"] = au.Dadtunit.fillna("").str.contains("普华永道|德勤|安永|毕马威").astype(int)
au["lnfee"] = np.log(pd.to_numeric(au.Tcost, errors="coerce").where(lambda x: x > 0))
au["firm"] = au.Dadtunit.fillna("").str.replace(r"[（(].*?[)）]", "", regex=True).str.replace("会计师事务所", "").str.strip()
pa = au[["Stkcd", "year", "firm"]].copy(); pa["year"] += 1
au = au.merge(pa.rename(columns={"firm": "firm_l"}), on=["Stkcd", "year"], how="left")
au["switch"] = ((au.firm != au.firm_l) & (au.firm != "")).astype(float).where(au.firm_l.notna())   # 更换境内审计事务所
an = num(clean(find("AF_CFEATUREPROFILE", lambda c: "AnaAttention" in c), "Stkcd", "Accper", "12-31"), ["AnaAttention"])
ins = num(clean(find("INI_HolderSystematics", lambda c: "InsInvestorProp" in c), "Symbol", "EndDate", "12-31"), ["InsInvestorProp"])
q = find("CMS_InquiriesSE", lambda c: "InquiryTitle" in c)
q = q[q.InquiryDate.astype(str).str.match(DATE)].copy()
t = q.InquiryTitle.fillna("")
q["ar"] = (q.InquiryType == "1") | (t.str.contains("年报|年度报告") & ~t.str.contains("半年|季"))
fy = pd.to_numeric(t.str.extract(r"(20\d\d)\s*年(?:年度报告|年报|度报告)")[0], errors="coerce")
fy_date = q.InquiryDate.str[:4].astype(int) - 1
q["year"] = np.where(fy.notna() & (fy <= fy_date), fy, fy_date).astype(int)   # 年报问询函对应的会计年度；标题年份晚于发函上一年的属标题错误
q["QuestionNum"] = pd.to_numeric(q.QuestionNum, errors="coerce")
qa = q[q.ar].groupby(["Symbol", "year"]).agg(inq_n=("EventID", "size"), inq_q=("QuestionNum", "sum")).reset_index()
qa = qa.rename(columns={"Symbol": "Stkcd"})

p = pd.read_pickle("csmar/analysis.pkl")
p = p.merge(r[["Stkcd", "year", "abCFO", "abPROD", "abDISX", "REM", "etr", "COGS", "SELL", "ADMIN", "EBT", "TAX"]], on=["Stkcd", "year"], how="left")
p = p.merge(pl, on=["Stkcd", "year"], how="left")
sh_sz = p.Stkcd.str[:1].isin(["0", "3", "6"])
p["pled"] = p.pled.where(p.pled.notna() | ~sh_sz | (p.year < 2022) | (p.year > 2025), 0.0)   # 沪深股票不在统计表里即无质押
p = p.merge(au[["Stkcd", "year", "big4", "lnfee", "switch"]], on=["Stkcd", "year"], how="left")
p = p.merge(an[["Stkcd", "year", "AnaAttention"]], on=["Stkcd", "year"], how="left")
p["nana"] = p.AnaAttention.where(p.year < 2022, p.AnaAttention.fillna(0))
p["lnana"] = np.log1p(p.nana)
p = p.merge(ins[["Stkcd", "year", "InsInvestorProp"]].rename(columns={"InsInvestorProp": "inst"}), on=["Stkcd", "year"], how="left")
p = p.merge(qa, on=["Stkcd", "year"], how="left")
cover = p.year.between(2023, 2025)
p["inq"] = np.where(cover, p.inq_n.notna().astype(float), np.nan)
p["inq_q"] = np.where(cover, p.inq_q.fillna(0), np.nan)

# ---------------- 2026 年上半年首次入表：此前年报、半年报都没有数据资源，2026 年 6 月 30 日有
hw = half.pivot_table(index="Stkcd", columns="year", values="DR_h", aggfunc="first")
ever = set(p[p.treat == 1].Stkcd) | set(hw.index[(hw.get(2024, 0).fillna(0) > 0) | (hw.get(2025, 0).fillna(0) > 0)])
new26 = (set(hw.index[hw.get(2026, 0).fillna(0) > 0]) - ever) & set(p.Stkcd)     # 只看非金融企业
early_half = (set(hw.index[(hw.get(2024, 0).fillna(0) > 0) | (hw.get(2025, 0).fillna(0) > 0)]) - set(p[p.treat == 1].Stkcd)) & set(p.Stkcd)
p["first6"] = p["first"]
p.loc[p.Stkcd.isin(new26), "first6"] = 2026
p.attrs["new26"] = sorted(new26)
p.attrs["early_half"] = sorted(early_half)
p.to_pickle("csmar/analysis6.pkl")
half.to_pickle("csmar/half.pkl")

d = p[p.year.between(2021, 2025)]
print("真实盈余管理样本量:", d.groupby("year")[["abCFO", "abPROD", "abDISX", "REM"]].count().to_dict("index"))
print(d.groupby("year")[["abCFO", "abPROD", "abDISX", "REM"]].mean().round(4).to_string())
print("有效税率中位数:", d.groupby("year").etr.median().round(3).to_dict())
print("质押比例>0 占比:", d.groupby("year").pled.apply(lambda s: round((s > 0).mean(), 3)).to_dict(), " 缺失:", d.groupby("year").pled.apply(lambda s: s.isna().sum()).to_dict())
print("四大占比:", d.groupby("year").big4.mean().round(3).to_dict(), " 审计费用缺失:", d.groupby("year").lnfee.apply(lambda s: s.isna().sum()).to_dict())
print("分析师关注均值:", d.groupby("year").nana.mean().round(2).to_dict(), " 机构持股均值:", d.groupby("year").inst.mean().round(2).to_dict())
print("收到年报问询函占比:", d.groupby("year").inq.mean().round(4).to_dict())
print("半年报有数据资源的公司:", {y: int((hw[y].fillna(0) > 0).sum()) for y in hw.columns})
print("2026 年上半年首次入表（非金融）:", len(new26), sorted(new26), " 半年报有、年报从未有的公司:", len(early_half), sorted(early_half))
