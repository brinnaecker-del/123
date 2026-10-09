"""论文图 2：入表相对重要性与净利率影响（双对数）。用法：python fig2.py 入表财务效应分析样本.csv 输出.png
需要：pip install pandas matplotlib；字体用文泉驿正黑，Windows 上可改成 SimHei"""
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter

font_manager.fontManager.addfont("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc")
plt.rcParams.update({"font.family": "WenQuanYi Zen Hei", "font.size": 8.5, "axes.unicode_minus": False,
                     "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6})
d = pd.read_csv(sys.argv[1], dtype={"代码": str, "年度": str})
d = d.rename(columns={"相对重要性%": "rel", "净利率影响pp": "imp", "测算入表额": "E"})
FILL = {"稳健": "white", "下滑": "0.6", "亏损": "black"}
fig, axes = plt.subplots(1, 2, figsize=(15.5 / 2.54, 7.4 / 2.54), sharey=True)
for ax, (year, title) in zip(axes, [("2024", "(a) 2024年报：入表额＝期末余额"), ("2025", "(b) 2025年报：入表额＝当期新增")]):
    g = d[(d.年度 == year) & (d.E > 0)]
    for _, r in g.iterrows():
        if r.案例企业 == r.案例企业 and r.案例企业:
            continue
        ax.scatter(r.rel, r.imp, s=13, marker="s" if r.行业 == "金融" else "o", facecolor=FILL[r.经营状态],
                   edgecolor="black", linewidth=0.5, zorder=3)
    nf = g[g.行业 == "非金融"]
    b, a = np.polyfit(np.log(nf.rel), np.log(nf.imp), 1)
    xs = np.logspace(np.log10(g.rel.min()) - 0.2, np.log10(g.rel.max()) + 0.2, 50)
    ax.plot(xs, np.exp(a) * xs ** b, ls="--", lw=0.7, color="0.35", zorder=2)
    for _, r in g[g.案例企业.notna() & (g.案例企业 != "")].iterrows():
        ax.scatter(r.rel, r.imp, s=34, marker="D", facecolor=FILL[r.经营状态], edgecolor="black", linewidth=0.8, zorder=4)
        off = {"开普云": (-30, 8), "拓尔思": (6, -16), "中国移动": (12, -14)}[r.案例企业]
        ax.annotate(r.案例企业, (r.rel, r.imp), xytext=off, textcoords="offset points", fontsize=7.5,
                    ha="right" if off[0] < 0 else "left", va="center", zorder=5,
                    arrowprops=dict(arrowstyle="-", lw=0.5, color="0.2", shrinkA=0, shrinkB=3))
    rho = pd.Series(g.rel).rank().corr(pd.Series(g.imp).rank())
    ax.text(0.97, 0.04, f"N＝{len(g)}，Spearman ρ＝{rho:.2f}", transform=ax.transAxes, fontsize=7.5, va="bottom", ha="right")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_title(title, fontsize=8.5)
    ax.set_xlabel("入表额／总资产（%，对数刻度）")
    ax.tick_params(labelsize=7.5, which="both", direction="in")
    fmt = FuncFormatter(lambda v, _: f"{v:g}")
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_locator(LogLocator(base=10))
        axis.set_major_formatter(fmt)
        axis.set_minor_formatter(NullFormatter())
axes[0].set_ylabel("净利率影响（百分点，对数刻度）")
handles = [Line2D([], [], marker="o", ls="", mfc="white", mec="black", ms=4.5, label="盈利且未下滑"),
           Line2D([], [], marker="o", ls="", mfc="0.6", mec="black", ms=4.5, label="盈利但归母净利润下滑"),
           Line2D([], [], marker="o", ls="", mfc="black", mec="black", ms=4.5, label="亏损"),
           Line2D([], [], marker="s", ls="", mfc="white", mec="black", ms=4.5, label="金融企业"),
           Line2D([], [], marker="D", ls="", mfc="white", mec="black", ms=5, label="案例企业"),
           Line2D([], [], ls="--", color="0.35", lw=0.8, label="非金融企业拟合线")]
fig.legend(handles=handles, loc="lower center", ncol=6, fontsize=7, frameon=False, handletextpad=0.2, columnspacing=0.8)
fig.tight_layout(rect=(0, 0.07, 1, 1), w_pad=0.6)
fig.savefig(sys.argv[2], dpi=300)
print("saved")
