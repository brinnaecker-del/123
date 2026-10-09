"""全样本检验（命题 1、2）：Spearman 相关、OLS、分组比较。用法：python stats.py 入表财务效应分析样本.csv
需要：pip install pandas statsmodels scipy"""
import sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

d = pd.read_csv(sys.argv[1], dtype={"代码": str, "年度": str})
d = d.rename(columns={"相对重要性%": "rel", "净利率影响pp": "imp", "存量相对重要性%": "srel", "测算入表额": "E",
                      "总资产": "TA", "营业收入": "REV", "入表额占净利润绝对值%": "share"})
d["fin"] = (d.行业 == "金融").astype(int)
d["press"] = d.经营状态.isin(["亏损", "下滑"]).astype(int)
d["loss"] = (d.经营状态 == "亏损").astype(int)
d["lnTA"] = np.log(d.TA)
d["AS"] = d.TA / d.REV


def report(g, tag):
    g = g[(g.E > 0)].copy()
    g["lnrel"], g["lnimp"], g["lnE"] = np.log(g.rel), np.log(g.imp), np.log(g.E)
    g["lnAS"] = np.log(g.AS)
    n = len(g)
    print(f"\n######## {tag}  N={n}  （亏损{g.loss.sum()} 下滑{(g.press - g.loss).sum()} 稳健{n - g.press.sum()}；金融{g.fin.sum()}）")
    r1 = stats.spearmanr(g.rel, g.imp); r2 = stats.spearmanr(g.E, g.imp); r3 = stats.spearmanr(g.lnTA, g.rel)
    r4 = stats.spearmanr(g.lnTA, g.imp); r5 = stats.spearmanr(g.lnTA, g.E)
    print(f"Spearman 相对重要性-净利率影响 {r1.statistic:.3f} (p={r1.pvalue:.2g}); 绝对金额-净利率影响 {r2.statistic:.3f} (p={r2.pvalue:.2g})")
    print(f"Spearman 规模-相对重要性 {r3.statistic:.3f} (p={r3.pvalue:.2g}); 规模-净利率影响 {r4.statistic:.3f} (p={r4.pvalue:.2g}); 规模-绝对金额 {r5.statistic:.3f} (p={r5.pvalue:.2g})")
    # 方差分解：ln imp = ln rel + ln(A/S)
    v = np.var(g.lnimp); print(f"ln影响 方差 {v:.2f}；ln相对重要性 方差 {np.var(g.lnrel):.2f}；ln(资产/收入) 方差 {np.var(g.lnAS):.2f}；"
                              f"协方差×2 {2*np.cov(g.lnrel, g.lnAS, bias=True)[0,1]:.2f}")
    for f in ["lnimp ~ lnE", "lnimp ~ lnrel", "lnimp ~ lnrel + lnTA + fin", "lnimp ~ lnrel + press + lnTA + fin",
              "lnimp ~ lnrel + loss + lnTA + fin"]:
        m = smf.ols(f, g).fit(cov_type="HC1")
        coefs = "  ".join(f"{k}={m.params[k]:.3f}({m.pvalues[k]:.2g})" for k in m.params.index if k != "Intercept")
        print(f"OLS {f:<40} R2={m.rsquared:.3f}  {coefs}")
    for f in ["lnrel ~ lnTA + fin", "lnrel ~ press + lnTA + fin", "lnrel ~ loss + lnTA + fin"]:
        m = smf.ols(f, g).fit(cov_type="HC1")
        coefs = "  ".join(f"{k}={m.params[k]:.3f}({m.pvalues[k]:.2g})" for k in m.params.index if k != "Intercept")
        print(f"OLS {f:<40} R2={m.rsquared:.3f}  {coefs}")
    # 分组
    for col, lab in (("rel", "相对重要性%"), ("imp", "净利率影响pp"), ("share", "占|净利润|%")):
        a, b = g[g.press == 1][col], g[g.press == 0][col]
        u = stats.mannwhitneyu(a, b)
        kw = stats.kruskal(*[g[g.经营状态 == s][col] for s in ("亏损", "下滑", "稳健")])
        meds = {s: g[g.经营状态 == s][col].median() for s in ("亏损", "下滑", "稳健")}
        print(f"{lab}: 中位数 亏损{meds['亏损']:.4f} 下滑{meds['下滑']:.4f} 稳健{meds['稳健']:.4f}；承压vs稳健 MW p={u.pvalue:.3g}；KW p={kw.pvalue:.3g}")
    # 规模四分位
    g["q"] = pd.qcut(g.lnTA, 4, labels=["Q1小", "Q2", "Q3", "Q4大"])
    print(g.groupby("q", observed=True).agg(N=("rel", "size"), 总资产中位亿=("TA", lambda s: s.median() / 1e8),
                                            入表额中位万=("E", lambda s: s.median() / 1e4), 相对重要性中位=("rel", "median"),
                                            影响中位=("imp", "median"), 承压占比=("press", "mean")).round(4).to_string())
    top = g.sort_values("rel", ascending=False).head(10)
    print("相对重要性前 10：", "、".join(f"{r.简称}({r.rel:.2f}%,{r.经营状态})" for r in top.itertuples()))
    print("影响>1pp：", (g.imp > 1).sum(), "；其中承压", g[(g.imp > 1)].press.sum())


report(d[d.年度 == "2024"], "2024 年报（入表额=期末余额）")
report(d[(d.年度 == "2024") & (d.fin == 0)], "2024 非金融")
report(d[d.年度 == "2025"], "2025 年报（入表额=当期新增>0）")
report(d[(d.年度 == "2025") & (d.fin == 0)], "2025 非金融")
g = d[d.年度 == "2025"].copy()
g["E"] = g.入表期末; g["rel"] = g.srel; g["imp"] = g.入表期末 / g.REV * 100
report(g, "2025 年报（存量口径：期末余额）")
