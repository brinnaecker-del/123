"""合并 CSMAR 各表为公司—年度面板（2021–2025，A 股，合并报表）。"""
import numpy as np, pandas as pd

def clean(d, code, date):
    d = d.iloc[2:].copy()
    d = d.rename(columns={code: "Stkcd"})
    d["year"] = d[date].str[:4].astype(int)
    for c in d.columns:
        if (c[:1] in "ABC" and c[1:].isdigit()) or c.startswith("RD"):
            d[c] = pd.to_numeric(d[c], errors="coerce")
    return d

old = pd.read_pickle("csmar/panel_old.pkl")
bs = clean(pd.read_pickle("csmar/FS_Combas_new.pkl"), "Stkcd", "Accper").drop(columns=["ShortName", "Accper", "Typrep"]).drop_duplicates(["Stkcd", "year"])
inc = clean(pd.read_pickle("csmar/FS_Comins_new.pkl"), "Stkcd", "Accper").drop(columns=["ShortName", "Accper", "Typrep"]).drop_duplicates(["Stkcd", "year"])
rd = clean(pd.read_pickle("csmar/PT_LCRDSPENDING_new.pkl"), "Symbol", "EndDate")
rd = rd.sort_values("Source").drop_duplicates(["Stkcd", "year"])          # 定期报告（0）优先于 IPO（1）
rd = rd[["Stkcd", "year", "RDSpendSum", "RDExpenses", "RDInvest", "RDInvestRatio"]]
p = old.merge(bs, on=["Stkcd", "year"], how="outer").merge(inc, on=["Stkcd", "year"], how="outer").merge(rd, on=["Stkcd", "year"], how="left")
p = p.rename(columns={"A001111000": "REC", "A001123000": "INV", "A001123101": "DR_inv", "A001212000": "PPE", "A001218000": "INTAN",
                      "A001218201": "DR_int", "A001219000": "DEV", "A001219101": "DR_dev", "B001101000": "SALES", "B001216000": "RDEXP",
                      "B002000101": "NP"})
# A 股：剔除 B 股（200、900 开头）
p = p[~p.Stkcd.str[:3].isin(["200", "201", "900"])]
co = pd.read_pickle("csmar/co.pkl"); eq = pd.read_pickle("csmar/eq.pkl")
eq = eq.copy(); eq["year"] = eq.EndDate.str[:4].astype(int); eq["soe"] = eq.EquityNature.str.contains("国企").astype(int)
p = p.merge(eq[["Symbol", "year", "soe"]].drop_duplicates(["Symbol", "year"]).rename(columns={"Symbol": "Stkcd"}), on=["Stkcd", "year"], how="left")
co = co.copy(); co["ind"] = np.where(co.Nnindcd.str[0] == "C", co.Nnindcd.str[:3], co.Nnindcd.str[0])
p = p.merge(co[["Stkcd", "Nnindcd", "Nnindnme", "ind", "Listdt"]], on="Stkcd", how="left")
p["fin"] = (p.Nnindcd.str[0] == "J").astype(int)
p["DR"] = p[["DR_inv", "DR_int", "DR_dev"]].fillna(0).sum(axis=1)
p = p.sort_values(["Stkcd", "year"])
p.to_pickle("csmar/master.pkl")
print(p.shape, p.year.value_counts().sort_index().to_dict())
