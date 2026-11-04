"""市调大赛参赛报告 · 二手数据分析与抽样框

输入（全部为仓库现有数据，不新增任何数值）：
  ../jea/output/panel_clean.csv           73 区县 2016—2024 面板（清洗规则见 jea/clean.py）
  ../data/城关区GDP2016-2024.xlsx          城关区 GDP（只用于 74 区县规模排序）
  ../workbook/西藏三元协调评价-计算底稿.xlsx  自治区级宏观序列（1_基础数据）

输出：output/*.csv、output/fig*.png、output/numbers.json（报告与 PPT 中的数字全部从这里读取）
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
OUT = os.path.join(HERE, "output")
os.makedirs(OUT, exist_ok=True)
plt.rcParams["font.sans-serif"] = ["WenQuanYi Zen Hei"]
plt.rcParams["axes.unicode_minus"] = False
PAL = ["#8C2F39", "#D08C3A", "#3E7C6B", "#4A5A78", "#9AA0A6"]
N = {}

# ---------------- 1. 自治区宏观序列 ----------------
base = pd.read_excel(os.path.join(ROOT, "workbook", "西藏三元协调评价-计算底稿.xlsx"),
                     sheet_name="1_基础数据", header=None)
base = base.set_index(0)
years = [int(y) for y in base.loc["项目"].iloc[1:11]]
def row(name):
    return [float(v) for v in base.loc[name].iloc[1:11]]
macro = pd.DataFrame({
    "year": years,
    "gdp_yi": row("地区生产总值"),
    "rural_income": row("农村居民人均可支配收入"),
    "tourists_wan": row("接待游客总人数"),
    "pop_wan": row("西藏年末常住人口"),
    "nat_rural_income": row("全国农村居民人均可支配收入"),
})
macro["rural_income_rel"] = macro.rural_income / macro.nat_rural_income
macro["tourists_per_resident"] = macro.tourists_wan / macro.pop_wan
macro.to_csv(os.path.join(OUT, "T1_macro.csv"), index=False, encoding="utf-8-sig")
def cagr(a, b, n):
    return (b / a) ** (1 / n) - 1
N["macro"] = {
    "gdp_2016": macro.gdp_yi.iloc[0], "gdp_2025": macro.gdp_yi.iloc[-1],
    "gdp_cagr": cagr(macro.gdp_yi.iloc[0], macro.gdp_yi.iloc[-1], 9),
    "rural_2016": macro.rural_income.iloc[0], "rural_2025": macro.rural_income.iloc[-1],
    "rural_cagr": cagr(macro.rural_income.iloc[0], macro.rural_income.iloc[-1], 9),
    "rural_rel_2016": macro.rural_income_rel.iloc[0], "rural_rel_2025": macro.rural_income_rel.iloc[-1],
    "tour_2016": macro.tourists_wan.iloc[0], "tour_2025": macro.tourists_wan.iloc[-1],
    "tour_2020": macro.tourists_wan.iloc[4], "tour_2022": macro.tourists_wan.iloc[6],
    "tour_per_res_2025": macro.tourists_per_resident.iloc[-1],
}

fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
ax[0].bar(macro.year, macro.gdp_yi, color=PAL[0])
ax[0].set_title("西藏地区生产总值（亿元）")
ax2 = ax[0].twinx()
ax2.plot(macro.year, macro.rural_income / 1e4, color=PAL[1], marker="o")
ax2.set_ylabel("农村居民人均可支配收入（万元）", color=PAL[1])
ax[1].bar(macro.year, macro.tourists_wan, color=PAL[2])
ax[1].set_title("接待游客总人数（万人次）")
for a in ax:
    a.spines[["top"]].set_visible(False)
    a.set_xticks(macro.year)
    a.tick_params(axis="x", labelsize=8)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig1_macro.png"), dpi=200)
plt.close(fig)

# ---------------- 2. 区县市场指标 ----------------
p = pd.read_csv(os.path.join(ROOT, "jea", "output", "panel_clean.csv"))
p["gdp_pc"] = p.gdp / p["pop"]                       # 元/人（gdp 万元 / pop 万人）
p["exp_pc"] = p.exp / p["pop"]
p["ssr"] = p.rev / p.exp

def avg(var, yrs):
    return p[p.year.isin(yrs)].groupby("code")[var].mean()

ind = p[p.year == 2024].set_index("code")[["pref_cn", "county_cn", "level_shift"]].copy()
ind["gdp_2024"] = p[p.year == 2024].set_index("code").gdp / 1e4          # 亿元
ind["pop_2024"] = p[p.year == 2024].set_index("code")["pop"]              # 万人
ind["gdp_pc"] = avg("gdp_pc", [2022, 2023, 2024])                         # 三年均值，平滑波动
ind["exp_pc"] = avg("exp_pc", [2022, 2023, 2024])
ind["ssr"] = avg("ssr", [2022, 2023, 2024])
g16 = p[p.year == 2016].set_index("code").gdp
g24 = p[p.year == 2024].set_index("code").gdp
ind["gdp_cagr"] = (g24 / g16) ** (1 / 8) - 1
ind = ind.dropna()
N["n_counties"] = int(len(ind))

# 市场潜力指数：熵权法（六项均为正向）
cols = {"gdp_2024": "经济规模", "pop_2024": "人口规模", "gdp_pc": "人均产出",
        "gdp_cagr": "成长速度", "exp_pc": "人均公共支出", "ssr": "财政自给率"}
X = ind[list(cols)].astype(float)
Z = (X - X.min()) / (X.max() - X.min()) * 0.99 + 0.01
P = Z / Z.sum()
e = -(P * np.log(P)).sum() / np.log(len(Z))
w = (1 - e) / (1 - e).sum()
ind["mpi"] = (Z * w).sum(axis=1) / (Z * w).sum(axis=1).max() * 100
weights = pd.DataFrame({"指标": [cols[c] for c in cols], "代码": list(cols),
                        "熵值": e.values, "权重": w.values})
weights.to_csv(os.path.join(OUT, "T2_entropy_weights.csv"), index=False, encoding="utf-8-sig")
N["weights"] = {cols[c]: float(w[c]) for c in cols}

# ---------------- 3. K-means 市场分层 ----------------
F = pd.DataFrame({
    "lgdp": np.log(ind.gdp_2024), "lpop": np.log(ind.pop_2024),
    "lgdppc": np.log(ind.gdp_pc), "cagr": ind.gdp_cagr,
    "lexppc": np.log(ind.exp_pc), "ssr": ind.ssr})
Fz = (F - F.mean()) / F.std()
sil = {}
for k in range(3, 7):
    km = KMeans(n_clusters=k, n_init=50, random_state=2026).fit(Fz)
    sil[k] = silhouette_score(Fz, km.labels_)
pd.DataFrame({"k": list(sil), "silhouette": list(sil.values())}).to_csv(
    os.path.join(OUT, "T3_silhouette.csv"), index=False)
K = 4                                     # 见 T3：k=4 时类别可解释且每类样本量足以分层抽样
km = KMeans(n_clusters=K, n_init=50, random_state=2026).fit(Fz)
ind["cluster_raw"] = km.labels_
N["silhouette"] = {int(k): float(v) for k, v in sil.items()}
N["k"] = K

# 按类别特征命名：人均产出最高且自给率高 → 核心；人均公共支出最高、人口最少 → 高原牧区；
prof = ind.groupby("cluster_raw")[list(cols) + ["mpi"]].mean()
order = prof.mpi.sort_values(ascending=False).index.tolist()
rank = {c: i for i, c in enumerate(order)}
ind["tier"] = ind.cluster_raw.map(rank) + 1
prof = ind.groupby("tier")[list(cols) + ["mpi"]].mean()
prof["n"] = ind.groupby("tier").size()
prof["pop_sum"] = ind.groupby("tier").pop_2024.sum()
prof["gdp_sum"] = ind.groupby("tier").gdp_2024.sum()
prof["pop_share"] = prof.pop_sum / prof.pop_sum.sum()
prof["gdp_share"] = prof.gdp_sum / prof.gdp_sum.sum()
prof.to_csv(os.path.join(OUT, "T4_tier_profile.csv"), encoding="utf-8-sig")


def name_tier(r, allp):
    if r.gdp_pc == allp.gdp_pc.max():
        return "高产出核心型"
    if r.exp_pc == allp.exp_pc.max():
        return "财政支撑型"
    if r.pop_2024 == allp.pop_2024.max():
        return "地市中心型"
    return "农牧基础型"
names = {t: name_tier(prof.loc[t], prof) for t in prof.index}
# 名称若重复，退回为“第 t 层”
if len(set(names.values())) < len(names):
    names = {t: f"第{t}层" for t in prof.index}
ind["tier_name"] = ind.tier.map(names)
prof["name"] = [names[t] for t in prof.index]
prof.to_csv(os.path.join(OUT, "T4_tier_profile.csv"), encoding="utf-8-sig")
N["tiers"] = {int(t): {k: (float(v) if not isinstance(v, str) else v) for k, v in prof.loc[t].items()}
              for t in prof.index}

# 稳健性：(a) 去掉“成长速度”重聚类；(b) 不同随机种子；用调整兰德指数衡量与基准分层的一致性
from sklearn.metrics import adjusted_rand_score
rob = {}
km_a = KMeans(n_clusters=K, n_init=50, random_state=2026).fit(Fz.drop(columns="cagr"))
rob["去掉成长速度"] = adjusted_rand_score(ind.tier, km_a.labels_)
seeds = [adjusted_rand_score(ind.tier, KMeans(n_clusters=K, n_init=50, random_state=s).fit(Fz).labels_)
         for s in range(1, 21)]
rob["20个随机种子_最低"] = min(seeds)
# (c) 两个口径跳变县（噶尔、色尼）的成长速度改用 2020—2024 年
cag2 = ind.gdp_cagr.copy()
g20 = p[p.year == 2020].set_index("code").gdp
for c in ind.index[ind.level_shift]:
    cag2[c] = (g24[c] / g20[c]) ** (1 / 4) - 1
F2 = F.copy(); F2["cagr"] = cag2
km_c = KMeans(n_clusters=K, n_init=50, random_state=2026).fit((F2 - F2.mean()) / F2.std())
rob["跳变县改用2020-24增速"] = adjusted_rand_score(ind.tier, km_c.labels_)
N["robust_ari"] = {k: float(v) for k, v in rob.items()}
pd.Series(rob).to_csv(os.path.join(OUT, "T8_cluster_robustness.csv"), encoding="utf-8-sig")

ind = ind.sort_values("mpi", ascending=False)
ind["mpi_rank"] = range(1, len(ind) + 1)
ind.reset_index().to_csv(os.path.join(OUT, "T5_county_mpi.csv"), index=False, encoding="utf-8-sig")
N["top10"] = ind.head(10)[["county_cn", "pref_cn", "mpi", "tier_name"]].values.tolist()
N["bottom5"] = ind.tail(5)[["county_cn", "pref_cn", "mpi", "tier_name"]].values.tolist()

# 地市 × 层级交叉
ct = pd.crosstab(ind.pref_cn, ind.tier_name)
ct.to_csv(os.path.join(OUT, "T6_pref_by_tier.csv"), encoding="utf-8-sig")

# 散点：人均产出 × 人均公共支出，按层级着色，点大小=人口
fig, ax = plt.subplots(figsize=(7.5, 4.6))
for t in sorted(ind.tier.unique()):
    s = ind[ind.tier == t]
    ax.scatter(s.gdp_pc / 1e4, s.exp_pc / 1e4, s=s.pop_2024 * 18, alpha=0.75,
               color=PAL[t - 1], edgecolor="white", label=f"{names[t]}（{len(s)}个）")
for _, r in ind.head(6).iterrows():
    ax.annotate(r.county_cn, (r.gdp_pc / 1e4, r.exp_pc / 1e4), fontsize=8,
                xytext=(4, 3), textcoords="offset points")
ax.set_xscale("log"); ax.set_yscale("log")
from matplotlib.ticker import FixedLocator, NullLocator, FormatStrFormatter
ax.xaxis.set_major_locator(FixedLocator([2, 3, 4, 6, 10, 15, 20])); ax.xaxis.set_minor_locator(NullLocator())
ax.yaxis.set_major_locator(FixedLocator([3, 4, 6, 10, 15, 20])); ax.yaxis.set_minor_locator(NullLocator())
ax.xaxis.set_major_formatter(FormatStrFormatter("%g")); ax.yaxis.set_major_formatter(FormatStrFormatter("%g"))
ax.set_xlabel("人均地区生产总值，2022—2024 年均值（万元，对数轴）")
ax.set_ylabel("人均一般预算支出（万元，对数轴）")
ax.legend(frameon=False, fontsize=8, loc="upper left")
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig2_tiers.png"), dpi=200)
plt.close(fig)

# 潜力指数前 15
top = ind.head(15).iloc[::-1]
fig, ax = plt.subplots(figsize=(7, 4.6))
ax.barh(top.county_cn, top.mpi, color=[PAL[t - 1] for t in top.tier])
for i, v in enumerate(top.mpi):
    ax.text(v + 0.8, i, f"{v:.1f}", va="center", fontsize=8)
ax.set_xlabel("市场潜力指数（最高=100）")
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig3_top15.png"), dpi=200)
plt.close(fig)

# ---------------- 4. 规模集中度（74 区县，含城关区） ----------------
cg = pd.read_excel(os.path.join(ROOT, "data", "城关区GDP2016-2024.xlsx"))
conc = pd.read_csv(os.path.join(ROOT, "jea", "output", "T_concentration_74.csv"))
N["chengguan_share_2016"] = float(conc.chengguan_share.iloc[0])
N["chengguan_share_2024"] = float(conc.chengguan_share.iloc[-1])
N["top5_share_2024"] = float(conc.top5_share.iloc[-1])

# ---------------- 5. 抽样设计 ----------------
z, pp, e_m, deff, resp = 1.96, 0.5, 0.04, 1.5, 0.85
n0 = z ** 2 * pp * (1 - pp) / e_m ** 2
n_eff = int(np.ceil(n0 * deff))
n_issue = int(np.ceil(n_eff / resp))
N["sample"] = {"n0": n0, "n_eff": n_eff, "n_issue": n_issue, "e": e_m, "deff": deff, "resp": resp}

# 层间分配：与人口平方根成比例（兼顾精度与小层可分析性），每层不少于 150
sq = np.sqrt(prof.pop_sum)
alloc = np.maximum(150, np.round(n_eff * sq / sq.sum())).astype(int)
# 每层抽 2 个县（PSU），按人口规模成比例系统抽样（PPS），固定随机种子可复现
rng = np.random.default_rng(20261104)
picks = []
for t in prof.index:
    s = ind[ind.tier == t].sort_values(["pref_cn", "county_cn"]).copy()
    m = 2
    cum = s.pop_2024.cumsum().values
    step = cum[-1] / m
    start = rng.uniform(0, step)
    hits = [start + i * step for i in range(m)]
    idx = [int(np.searchsorted(cum, h)) for h in hits]
    for j in idx:
        r = s.iloc[j]
        picks.append({"层级": names[t], "区县": r.county_cn, "地市": r.pref_cn,
                      "户籍人口(万人)": r.pop_2024, "入样概率": round(m * r.pop_2024 / cum[-1], 3),
                      "本县样本量": int(alloc[t] // m)})
psu = pd.DataFrame(picks)
psu.to_csv(os.path.join(OUT, "T7_sample_psu.csv"), index=False, encoding="utf-8-sig")
N["psu"] = psu.values.tolist()
N["alloc"] = {names[t]: int(alloc[t]) for t in prof.index}
N["n_total_alloc"] = int(alloc.sum())
N["n_issue_alloc"] = int(np.ceil(alloc.sum() / resp))

with open(os.path.join(OUT, "numbers.json"), "w", encoding="utf-8") as f:
    json.dump(N, f, ensure_ascii=False, indent=1, default=float)
print(json.dumps(N, ensure_ascii=False, indent=1, default=float)[:6000])
print(prof.round(3).to_string())
print(weights.round(4).to_string())
