"""论文表 2 的数字。用法：python table2.py 入表财务效应分析样本.csv 输出.json
需要：pip install pandas statsmodels scipy"""
import json, sys
import numpy as np, pandas as pd, statsmodels.formula.api as smf
from scipy import stats
d = pd.read_csv(sys.argv[1], dtype={"代码": str, "年度": str})
d = d.rename(columns={"相对重要性%": "rel", "净利率影响pp": "imp", "测算入表额": "E", "总资产": "TA"})
d["fin"] = (d.行业 == "金融").astype(int); d["loss"] = (d.经营状态 == "亏损").astype(int)
d["lnTA"] = np.log(d.TA)
p = d[d.E > 0].copy(); p["lnrel"] = np.log(p.rel); p["lnimp"] = np.log(p.imp); p["lnE"] = np.log(p.E); p["y25"] = (p.年度 == "2025").astype(int)
samples = {"2024": p[p.年度 == "2024"], "2025": p[p.年度 == "2025"], "pooled": p}
out = {"spearman": {}, "imp": {}, "rel": {}, "N": {}}
def star(pv): return "***" if pv < 0.01 else "**" if pv < 0.05 else "*" if pv < 0.1 else ""
for k in ("2024", "2025"):
    g = samples[k]
    for name, a, b in (("相对重要性—净利率影响", g.rel, g.imp), ("绝对金额—净利率影响", g.E, g.imp),
                       ("企业规模—绝对金额", g.lnTA, g.E), ("企业规模—相对重要性", g.lnTA, g.rel)):
        r = stats.spearmanr(a, b)
        out["spearman"].setdefault(name, {})[k] = f"{r.statistic:.3f}{star(r.pvalue)}"
for k, g in samples.items():
    out["N"][k] = len(g)
    kw = dict(cov_type="cluster", cov_kwds={"groups": g.代码}) if k == "pooled" else dict(cov_type="HC1")
    yr = " + y25" if k == "pooled" else ""
    for dep, f in (("imp", "lnimp ~ lnrel + loss + lnTA + fin" + yr), ("rel", "lnrel ~ loss + lnTA + fin" + yr)):
        m = smf.ols(f, g).fit(**kw)
        res = {v: f"{m.params[v]:.3f}{star(m.pvalues[v])}\n({m.tvalues[v]:.2f})" for v in m.params.index if v not in ("Intercept", "y25")}
        res["R2"] = f"{m.rsquared:.3f}"
        out[dep][k] = res
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
