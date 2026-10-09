"""入表选择的类别不平衡（入表率约 1.2%）：Firth 惩罚似然 Logit、King-Zeng 稀有事件偏差校正 Logit；
以及熵平衡（Hainmueller 2012）加权的双重差分。
用法：python rare_events.py csmar/analysis.pkl 输出.json"""
import json, sys, warnings
import numpy as np, pandas as pd, pyfixest as pf
import statsmodels.formula.api as smf
from scipy import optimize, stats

warnings.filterwarnings("ignore")
AP, OUT = sys.argv[1:3]
p = pd.read_pickle(AP)
res = {}


def star(pv): return "***" if pv < 0.01 else "**" if pv < 0.05 else "*" if pv < 0.1 else ""


# ---------------- 入表选择样本（与 final_tables.py 相同） ----------------
X = ["loss", "decl", "small", "size", "lev", "growth", "cfo", "soe", "age", "rdint", "caprate"]
lag = p[["Stkcd", "year", "ind"] + X].copy(); lag["year"] += 1
rows = []
for t in (2024, 2025):
    a = lag[lag.year == t].merge(p[p.year == t][["Stkcd", "first"]], on="Stkcd")
    a = a[~((t == 2025) & (a["first"] == 2024))]
    a["y"] = (a["first"] == t).astype(int)
    a["rdint"] = a.rdint.fillna(0); a["caprate"] = a.caprate.fillna(0)
    rows.append(a.dropna(subset=X + ["ind"]))
a = pd.concat(rows).reset_index(drop=True)
a["letter"] = a.ind.str[0]
# 设计矩阵：常数、解释变量、行业门类与年度虚拟变量（去掉没有入表企业的门类，否则极大似然不存在）
keep = a.groupby("letter").y.transform("sum") > 0
a = a[keep].reset_index(drop=True)
D = pd.get_dummies(a[["letter"]], drop_first=True).astype(float)
Xm = pd.concat([pd.Series(1.0, index=a.index, name="const"), a[X].astype(float), D, (a.year == 2025).astype(float).rename("y2025")], axis=1)
Xm = Xm.loc[:, (Xm.std() > 0) | (Xm.columns == 'const')]
yv = a.y.values.astype(float); Xa = Xm.values
names = list(Xm.columns)


def logit_ml(Xa, yv):
    import statsmodels.api as sm
    m = sm.Logit(yv, Xa).fit(disp=0, method="newton", maxiter=200)
    b = np.asarray(m.params)
    pi = 1 / (1 + np.exp(-Xa @ b)); W = pi * (1 - pi)
    return b, np.linalg.inv(Xa.T @ (Xa * W[:, None])), pi, W


def firth(Xa, yv, b0):
    b = b0.copy()
    for _ in range(200):
        pi = 1 / (1 + np.exp(-Xa @ b)); W = pi * (1 - pi)
        Iinv = np.linalg.inv(Xa.T @ (Xa * W[:, None]))
        h = W * np.einsum("ij,jk,ik->i", Xa, Iinv, Xa)                     # 帽子矩阵对角元
        U = Xa.T @ (yv - pi + h * (0.5 - pi))
        step = Iinv @ U
        step = step / max(1.0, np.max(np.abs(step)) / 2)                  # 步长上限，保证收敛
        b += step
        if np.max(np.abs(step)) < 1e-10:
            break
    pi = 1 / (1 + np.exp(-Xa @ b)); W = pi * (1 - pi)
    return b, np.linalg.inv(Xa.T @ (Xa * W[:, None]))


b_ml, V_ml, pi, W = logit_ml(Xa, yv)
b_f, V_f = firth(Xa, yv, b_ml)
# King-Zeng（2001）偏差校正：bias＝(X'WX)^{-1}X'Wξ，ξ_i＝0.5·Q_ii·[(1＋w1)π_i－w1]，全样本时 w1＝1
Q = np.einsum("ij,jk,ik->i", Xa, V_ml, Xa)
xi = 0.5 * Q * (2 * pi - 1)
bias = V_ml @ (Xa.T @ (W * xi))
b_kz = b_ml - bias
n, k = Xa.shape
V_kz = (n / (n + k)) ** 2 * V_ml
out = {}
for lab, b, V in (("logit", b_ml, V_ml), ("firth", b_f, V_f), ("kingzeng", b_kz, V_kz)):
    se = np.sqrt(np.diag(V))
    out[lab] = {}
    for v in ("loss", "decl", "small", "size", "soe", "caprate"):
        i = names.index(v); z = b[i] / se[i]; pv = 2 * (1 - stats.norm.cdf(abs(z)))
        out[lab][v] = f"{b[i]:.3f}{star(pv)}\n({z:.2f})"
    out[lab]["N"] = str(n)
res["selection_rare"] = out
res["selection_rare_info"] = {"N": int(n), "events": int(yv.sum()), "dropped_letters": sorted(set(pd.concat(rows).ind.str[0]) - set(a.letter))}

# ---------------- 熵平衡加权的双重差分 ----------------
base = p[p.year == 2023].dropna(subset=["size", "lev", "roa", "growth", "soe", "ind"]).copy()
base["rdint"] = base.rdint.fillna(0); base["caprate"] = base.caprate.fillna(0)
base["letter"] = base.ind.str[0]
cov = ["size", "lev", "roa", "growth", "soe", "rdint", "caprate"]
L = pd.get_dummies(base.letter, prefix="L").astype(float)
L = L.loc[:, L[base.treat == 1].sum() > 0]
Z = pd.concat([base[cov].astype(float), base[cov[:4]].astype(float).pow(2).add_suffix("_sq"), L], axis=1)
tr, co_ = base.treat == 1, base.treat == 0
target = Z[tr].mean().values
Zc = Z[co_].values
Zs = (Zc - target) / Z.std().replace(0, 1).values                       # 标准化以利于数值稳定
obj = lambda lam: np.log(np.exp(Zs @ lam - (Zs @ lam).max()).sum()) + (Zs @ lam).max()
grad = lambda lam: (np.exp(Zs @ lam - (Zs @ lam).max())[:, None] * Zs).sum(0) / np.exp(Zs @ lam - (Zs @ lam).max()).sum()
sol = optimize.minimize(obj, np.zeros(Zs.shape[1]), jac=grad, method="BFGS", options={"gtol": 1e-8, "maxiter": 5000})
wc = np.exp(Zs @ sol.x - (Zs @ sol.x).max()); wc = wc / wc.sum() * tr.sum()
bal = pd.DataFrame({"treated": Z[tr][cov].mean(), "control_raw": Z[co_][cov].mean(),
                    "control_eb": pd.Series((Zc[:, :len(cov)] * wc[:, None]).sum(0) / wc.sum(), index=cov)})
res["eb_balance"] = bal.round(4).to_dict()
res["eb_converged"] = bool(sol.success)
wz = (Zc * wc[:, None]).sum(0) / wc.sum()
res["eb_max_std_diff"] = float(np.max(np.abs(wz - target) / Z.std().replace(0, 1).values))   # 加权后各矩的最大标准化差异
wmap = pd.Series(np.r_[np.ones(tr.sum()), wc], index=pd.concat([base[tr].Stkcd, base[co_].Stkcd]).values)
d = p[(p.year >= 2021) & (p.year <= 2025)].copy()
d = d[d.Stkcd.isin(wmap.index)].copy(); d["w"] = d.Stkcd.map(wmap)
ctrl = "size + lev + roa + growth + age"
Y = {"caprate": ctrl + " + rdint", "absDA": ctrl, "small": "size + lev + growth + age"}
eb = {}
for y, xs in Y.items():
    m = pf.feols(f"{y} ~ post + {xs} | Stkcd + year", d.dropna(subset=[y]), vcov={"CRV1": "Stkcd"}, weights="w")
    t = m.tidy().loc["post"]
    eb[y] = f"{t.Estimate:.4f}{star(t['Pr(>|t|)'])}\n({t['t value']:.2f})"
    eb[f"N_{y}"] = str(m._N)
res["eb_did"] = eb
json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
