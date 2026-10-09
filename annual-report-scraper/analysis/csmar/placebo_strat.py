"""安慰剂检验的补充：按「行业门类 × 2023 年是否有资本化研发」分层随机指定处理组，
使虚拟处理组在资本化基础上与真实入表企业可比；并比较入表企业与未入表企业研发资本化率的年度波动。
用法：python placebo_strat.py csmar/analysis.pkl 输出.json"""
import json, sys
import numpy as np, pandas as pd, pyfixest as pf

AP, OUT = sys.argv[1:3]
p = pd.read_pickle(AP)
d = p[(p.year >= 2021) & (p.year <= 2025)].copy()
ctrl = "size + lev + roa + growth + age"
Y = {"caprate": ctrl + " + rdint", "absDA": ctrl}
res = {}

# 研发资本化率的公司内波动（2021—2025 年标准差）
sd = d.groupby("Stkcd").agg(sd=("caprate", "std"), treat=("treat", "max"))
res["caprate_within_sd"] = {"treated": round(float(sd[sd.treat == 1].sd.mean()), 4), "control": round(float(sd[sd.treat == 0].sd.mean()), 4)}
c23 = p[p.year == 2023][["Stkcd", "caprate"]].rename(columns={"caprate": "c23"})
firms = p[p.year == 2023][["Stkcd", "ind", "treat", "first"]].dropna(subset=["ind"]).drop_duplicates("Stkcd").merge(c23, on="Stkcd", how="left")
firms["letter"] = firms.ind.str[0]
firms["capbase"] = (firms.c23.fillna(0) > 0).astype(int)
res["share_capbase"] = {"treated": round(float(firms[firms.treat == 1].capbase.mean()), 3), "control": round(float(firms[firms.treat == 0].capbase.mean()), 3)}
sd = sd.join(firms.set_index("Stkcd").capbase)
res["caprate_within_sd_capbase"] = {"treated": round(float(sd[(sd.treat == 1) & (sd.capbase == 1)].sd.mean()), 4),
                                    "control": round(float(sd[(sd.treat == 0) & (sd.capbase == 1)].sd.mean()), 4)}

real = {}
for y in Y:
    m = pf.feols(f"{y} ~ post + {Y[y]} | Stkcd + year", d.dropna(subset=[y]), vcov={"CRV1": "Stkcd"})
    real[y] = float(m.tidy().loc["post", "Estimate"])
rng = np.random.default_rng(20261010)
draws = {y: [] for y in Y}
for it in range(500):
    fake = {}
    for _, g in firms.groupby(["letter", "capbase"]):
        tr = g[g.treat == 1]
        if len(tr) == 0:
            continue
        pick = g.sample(len(tr), random_state=int(rng.integers(1e9)))
        fake.update(dict(zip(pick.Stkcd, tr["first"].values)))
    dd = d.drop(columns=["post"]).copy()
    f = dd.Stkcd.map(fake)
    dd["post"] = (f.notna() & (dd.year >= f)).astype(int)
    for y in Y:
        m = pf.feols(f"{y} ~ post + {Y[y]} | Stkcd + year", dd.dropna(subset=[y]), vcov="iid")
        draws[y].append(float(m.tidy().loc["post", "Estimate"]))
res["placebo_strat"] = {y: {"real_b": round(real[y], 4), "mean": round(float(np.mean(v)), 4), "sd": round(float(np.std(v)), 4),
                            "p_two": round(float(np.mean(np.abs(np.array(v)) >= abs(real[y]))), 3)} for y, v in draws.items()}
json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
