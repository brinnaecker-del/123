"""入表利润效应（第 5 版表 3）：避开 IMP＝REL×(TA/REV) 的恒等式——
(1) 入表额对总资产的规模弹性：ln E＝a＋b·ln TA，检验 b＝0（与规模无关）与 b＝1（与规模同比例）；
(2) ln IMP 方差的 Shapley 分解：ln IMP＝ln E－ln TA＋ln(TA/REV)，三部分各解释多少；
(3) 亏损的放大效应：ln(TA/REV) 对亏损回归（即 ln IMP－ln REL，系数等于模型(1)中约束 lnREL 系数为 1 时的亏损系数）；
(4) 风险筛查标准：REL＞1% 或 入表额/|净利润|＞10% 的公司数与金额占比，及其覆盖（由盈转亏企业、税前利润率影响≥1 个百分点却未被筛出的企业）；
(5) 稳健性：规模弹性的中位数回归、剔除总资产两端各 5%；亏损放大效应加入行业门类固定效应（需第三个参数，取 CSMAR 行业代码）。
主样本为非金融入表企业，全样本（含银行、证券）作对照。用法：python profit_effect.py 入表财务效应分析样本.csv 输出.json [csmar/analysis6.pkl]"""
import itertools, json, math, sys
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

s = pd.read_csv(sys.argv[1], dtype={"代码": str, "年度": str})
s["fin"] = (s.行业 == "金融").astype(int)
s["loss"] = (s.经营状态 == "亏损").astype(int)
s["y25"] = (s.年度 == "2025").astype(int)
if len(sys.argv) > 3:                                                   # 行业门类（证监会行业代码首字母）
    ind = pd.read_pickle(sys.argv[3]).drop_duplicates("Stkcd").set_index("Stkcd").ind.astype(str).str[0]
    s["letter"] = s.代码.str.zfill(6).replace({"835184": "920184", "836208": "920208"}).map(ind)   # 北交所公司在 CSMAR 中已改用新代码
res = {}


def star(pv): return "***" if pv < 0.01 else "**" if pv < 0.05 else "*" if pv < 0.1 else ""


def fit(f, g, pooled):
    if pooled:
        return smf.ols(f + " + y25", g).fit(cov_type="cluster", cov_kwds={"groups": g.代码.astype("category").cat.codes})
    return smf.ols(f, g).fit(cov_type="HC1")


def r2(cols, g):
    if not cols:
        return 0.0
    return smf.ols("lnimp ~ " + " + ".join(cols), g).fit().rsquared


def shapley(g, comps):
    out = {}
    n = len(comps)
    for c in comps:
        others = [x for x in comps if x != c]
        v = 0.0
        for k in range(n):
            for S in itertools.combinations(others, k):
                wt = math.factorial(k) * math.factorial(n - k - 1) / math.factorial(n)
                v += wt * (r2(list(S) + [c], g) - r2(list(S), g))
        out[c] = v
    return out


for samp, gg in (("nonfin", s[s.fin == 0]), ("all", s)):
    R = {}
    for lab in ("2024", "2025", "pooled"):
        g = gg if lab == "pooled" else gg[gg.年度 == lab]
        g = g[g.测算入表额 > 0].copy()
        g["lnE"] = np.log(g.测算入表额); g["lnTA"] = np.log(g.总资产); g["lnrel"] = np.log(g["相对重要性%"])
        g["lnimp"] = np.log(g.净利率影响pp); g["lnAS"] = np.log(g.总资产 / g.营业收入)
        pooled = lab == "pooled"
        fe = " + fin" if samp == "all" else ""
        r = {"N": int(len(g))}
        if not pooled:
            for nm, a, b in (("rel_imp", g["相对重要性%"], g.净利率影响pp), ("E_imp", g.测算入表额, g.净利率影响pp),
                             ("TA_E", g.总资产, g.测算入表额), ("TA_rel", g.总资产, g["相对重要性%"])):
                t = stats.spearmanr(a, b)
                r[f"rho_{nm}"] = f"{t.statistic:.3f}{star(t.pvalue)}"
        m = fit("lnE ~ lnTA" + fe, g, pooled)
        b, se = m.params.lnTA, m.bse.lnTA
        p1 = 2 * (1 - stats.norm.cdf(abs((b - 1) / se)))
        r["elast"] = f"{b:.3f}{star(m.pvalues.lnTA)}\n({b / se:.2f})"
        r["elast_b"] = round(float(b), 3); r["elast_ci"] = [round(float(b - 1.96 * se), 3), round(float(b + 1.96 * se), 3)]
        r["elast_p_eq1"] = float(p1); r["elast_r2"] = f"{m.rsquared:.3f}"
        r["r2_lnE"] = round(float(r2(["lnE"], g)), 3); r["r2_lnrel"] = round(float(r2(["lnrel"], g)), 3)
        # 稳健性：中位数回归；剔除总资产两端各 5%
        q = smf.quantreg("lnE ~ lnTA" + fe + (" + y25" if pooled else ""), g).fit(q=0.5)
        bq, sq = float(q.params.lnTA), float(q.bse.lnTA)
        r["elast_q50"] = {"b": round(bq, 3), "ci": [round(bq - 1.96 * sq, 3), round(bq + 1.96 * sq, 3)],
                          "p_eq1": float(2 * (1 - stats.norm.cdf(abs((bq - 1) / sq)))), "cell": f"{bq:.3f}{star(float(q.pvalues.lnTA))}\n({bq / sq:.2f})"}
        lo, hi = g.lnTA.quantile([0.05, 0.95])
        gt = g[g.lnTA.between(lo, hi)]
        mt = fit("lnE ~ lnTA" + fe, gt, pooled)
        bt, st = float(mt.params.lnTA), float(mt.bse.lnTA)
        r["elast_trim5"] = {"N": int(len(gt)), "b": round(bt, 3), "ci": [round(bt - 1.96 * st, 3), round(bt + 1.96 * st, 3)],
                            "p_eq1": float(2 * (1 - stats.norm.cdf(abs((bt - 1) / st)))), "cell": f"{bt:.3f}{star(float(mt.pvalues.lnTA))}\n({bt / st:.2f})"}
        sh = shapley(g, ["lnE", "lnTA", "lnAS"])
        r["shapley3"] = {k: round(float(v), 3) for k, v in sh.items()}
        sh2 = shapley(g, ["lnrel", "lnAS"])
        r["shapley2"] = {k: round(float(v), 3) for k, v in sh2.items()}
        m = fit("lnAS ~ loss + lnTA" + fe, g, pooled)
        r["AS_loss"] = f"{m.params.loss:.3f}{star(m.pvalues.loss)}\n({m.params.loss / m.bse.loss:.2f})"
        r["AS_loss_b"] = round(float(m.params.loss), 3); r["AS_loss_p"] = round(float(m.pvalues.loss), 3)
        r["AS_loss_pct"] = round(float((np.exp(m.params.loss) - 1) * 100), 0)
        r["AS_lnTA"] = f"{m.params.lnTA:.3f}{star(m.pvalues.lnTA)}\n({m.params.lnTA / m.bse.lnTA:.2f})"
        r["AS_r2"] = f"{m.rsquared:.3f}"
        if "letter" in g:                                                # 加入行业门类固定效应
            gi = g.dropna(subset=["letter"])
            mi = fit("lnAS ~ loss + lnTA + C(letter)" + fe, gi, pooled)
            r["AS_loss_ind"] = {"N": int(len(gi)), "b": round(float(mi.params.loss), 3), "p": round(float(mi.pvalues.loss), 3),
                                "cell": f"{mi.params.loss:.3f}{star(mi.pvalues.loss)}\n({mi.params.loss / mi.bse.loss:.2f})"}
        m = fit("lnrel ~ loss + lnTA" + fe, g, pooled)
        r["REL_loss"] = f"{m.params.loss:.3f}{star(m.pvalues.loss)}\n({m.params.loss / m.bse.loss:.2f})"
        r["REL_loss_p"] = round(float(m.pvalues.loss), 3)
        r["REL_lnTA"] = f"{m.params.lnTA:.3f}{star(m.pvalues.lnTA)}\n({m.params.lnTA / m.bse.lnTA:.2f})"
        r["REL_r2"] = f"{m.rsquared:.3f}"
        if not pooled:
            g["q"] = pd.qcut(g.lnTA, 4, labels=False)
            q = g.groupby("q").agg(TA=("总资产", "median"), E=("测算入表额", "median"), rel=("相对重要性%", "median"), imp=("净利率影响pp", "median"))
            r["quart"] = {"TA_yi": [float(q.TA[0] / 1e8), float(q.TA[3] / 1e8)], "E_wan": [float(q.E[0] / 1e4), float(q.E[3] / 1e4)],
                          "rel_pct": [float(q.rel[0]), float(q.rel[3])], "imp_pp": [float(q.imp[0]), float(q.imp[3])],
                          "rel_ratio": float(q.rel[0] / q.rel[3])}
            r["imp_median"] = float(g.净利率影响pp.median()); r["imp_lt01"] = int((g.净利率影响pp < 0.1).sum())
            r["imp_ge1"] = int((g.净利率影响pp >= 1).sum())
            nf = g[g.经营状态 != "亏损"]; lf = g[g.经营状态 == "亏损"]
            r["AS_median"] = {"loss": float((lf.总资产 / lf.营业收入).median()), "nonloss": float((nf.总资产 / nf.营业收入).median())}
        R[lab] = r
    res[samp] = R

# 重点关注阈值（全部入表企业，含入表额为负者）
th = {}
# 高金名单中经核对实际未列报数据资源的年报（神马股份 2024、金圆股份 2025、信达证券 2025）期末、期初余额均为 0，不计入入表企业样本
for y, g in s[(s.入表期末 > 0) | (s.入表期初 > 0)].groupby("年度"):
    g = g.copy()
    share = (g.测算入表额 / g.净利润.abs()).where(g.净利润 != 0)
    a = g["相对重要性%"] > 1; b = share > 0.10
    flag = a | b
    th[y] = {"N": int(len(g)), "rel_gt1": int(a.sum()), "share_gt10": int(b.sum()), "either": int(flag.sum()),
             "either_pct": round(float(100 * flag.mean()), 1), "either_loss": int((flag & (g.净利润 < 0)).sum()),
             "E_share_of_flagged": round(float(100 * g[flag].测算入表额.clip(lower=0).sum() / g.测算入表额.clip(lower=0).sum()), 1),
             "names": g[flag].简称.tolist()}
    # 筛查标准的覆盖：是否包含由盈转亏的企业；税前利润率影响≥1 个百分点却未被筛出的企业（多为亏损很深、入表额相对亏损较小者）
    th[y]["flip_flagged"] = g[flag & (g.净利润 > 0) & (g.净利润 - g.测算入表额 < 0)].简称.tolist()
    imp1 = (g.行业 == "非金融") & (g.测算入表额 > 0) & (g.净利率影响pp >= 1)
    th[y]["imp_ge1"] = int(imp1.sum()); th[y]["imp_ge1_flagged"] = int((imp1 & flag).sum())
    th[y]["imp_ge1_missed"] = [[r.简称, round(float(r.净利率影响pp), 2), round(float(r["相对重要性%"]), 2), round(float(100 * share[i]), 2),
                                round(float(r["净利率%"]), 2)] for i, r in g[imp1 & ~flag].sort_values("净利率影响pp", ascending=False).iterrows()]
res["threshold"] = th
json.dump(res, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1)[:6000])
