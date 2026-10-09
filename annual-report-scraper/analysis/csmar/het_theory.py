"""理论驱动的异质性：若入表被用于调节利润，机会主义应集中在入表相对重要性高、且入表前业绩承压的企业；另比较国有与非国有。
相对重要性 REL0＝首次入表当年末数据资源余额÷总资产（余额取 CSMAR 与年报手工数据的较大者，手工数据含仅附注披露的公司）。
用法：python het_theory.py csmar/analysis.pkl 入表财务效应分析样本.csv 输出.json"""
import json, sys, warnings
import numpy as np, pandas as pd, pyfixest as pf

warnings.filterwarnings("ignore")
AP, SAMPLE, OUT = sys.argv[1:4]
p = pd.read_pickle(AP)
s = pd.read_csv(SAMPLE, dtype={"代码": str, "年度": str})
s["Stkcd"] = s.代码.replace({"835184": "920184", "836208": "920208"}); s["year"] = s.年度.astype(int)
d = p[(p.year >= 2021) & (p.year <= 2025)].copy()
first = d[d.treat == 1].drop_duplicates("Stkcd")[["Stkcd", "first"]]
f = first.merge(p[["Stkcd", "year", "DR", "TA"]], left_on=["Stkcd", "first"], right_on=["Stkcd", "year"], how="left") \
         .merge(s[["Stkcd", "year", "入表期末"]], on=["Stkcd", "year"], how="left")
f["bal"] = np.fmax(f.DR.fillna(0), f.入表期末.fillna(0))
f["REL0"] = f.bal / f.TA
med = f.REL0.median()
f["highrel"] = (f.REL0 > med).astype(int)
pre = p[p.year == 2023][["Stkcd", "loss", "decl", "soe"]].rename(columns={"loss": "l23", "decl": "d23", "soe": "soe23"})
d = d.merge(f[["Stkcd", "highrel", "REL0"]], on="Stkcd", how="left").merge(pre, on="Stkcd", how="left")
d["highrel"] = d.highrel.fillna(0); d["press"] = ((d.l23 == 1) | (d.d23 == 1)).astype(int)
d["p_h"] = d.post * d.highrel; d["p_p"] = d.post * d.press; d["p_hp"] = d.post * d.highrel * d.press
d["p_soe"] = d.post * d.soe23

C = "size + lev + roa + growth + age"
Y = {"caprate": C + " + rdint", "absDA": C, "small": "size + lev + growth + age"}


def star(pv): return "***" if pv < 0.01 else "**" if pv < 0.05 else "*" if pv < 0.1 else ""


res = {"REL0_median_pct": round(float(med * 100), 4), "n_high": int(f.highrel.sum()), "n_treated": int(len(f)),
       "n_high_press": int(d[(d.treat == 1) & (d.highrel == 1) & (d.press == 1)].Stkcd.nunique()),
       "n_soe_treated": int(d[(d.treat == 1) & (d.soe23 == 1)].Stkcd.nunique())}
for lab, terms in (("相对重要性高", ["post", "p_h"]), ("相对重要性高×2023年承压", ["post", "p_h", "p_p", "p_hp"]), ("国有企业", ["post", "p_soe"])):
    res[lab] = {}
    for y, xs in Y.items():
        dd = d.dropna(subset=[y] + (["soe23"] if lab == "国有企业" else []))
        m = pf.feols(f"{y} ~ {' + '.join(terms)} + {xs} | Stkcd + year", dd, vcov={"CRV1": "Stkcd"})
        t = m.tidy()
        res[lab][y] = {k: f"{t.loc[k, 'Estimate']:.4f}{star(t.loc[k, 'Pr(>|t|)'])}\n({t.loc[k, 't value']:.2f})" for k in terms}
        res[lab][y]["N"] = str(m._N)
json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
