"""图 3：Callaway-Sant'Anna 动态效应（双重稳健，从未入表企业为对照，通用基期为入表前一年），读 pretrend.py 的输出。
用法：python fig3_cs.py pretrend.json 图3.png"""
import json, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

font_manager.fontManager.addfont("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc")
plt.rcParams.update({"font.family": "WenQuanYi Zen Hei", "font.size": 8.5, "axes.unicode_minus": False})
ev = json.load(open(sys.argv[1], encoding="utf-8"))["cs_event"]
fig, axes = plt.subplots(2, 2, figsize=(15.5 / 2.54, 11 / 2.54))
panels = [("caprate", "(a) 研发资本化率"), ("absDA", "(b) |可操纵应计利润|"), ("small", "(c) 微利"), ("REM", "(d) 真实盈余管理")]
for ax, (y, title) in zip(axes.ravel(), panels):
    ks = sorted(int(k) for k in ev[y])
    b = np.array([ev[y][str(k)][0] for k in ks])
    se = np.array([ev[y][str(k)][1] if ev[y][str(k)][1] is not None else 0 for k in ks], dtype=float)
    ax.axhline(0, color="0.5", lw=0.6); ax.axvline(-0.5, color="0.5", lw=0.6, ls=":")
    ax.errorbar(ks, b, yerr=1.96 * se, fmt="o", color="black", ms=3.5, capsize=2.5, lw=0.8)
    ax.set_xticks(ks); ax.set_title(title, fontsize=8.5)
    ax.tick_params(labelsize=7.5, direction="in")
for ax in axes[1]:
    ax.set_xlabel("相对入表年份（入表前一年为基期）")
for ax in axes[:, 0]:
    ax.set_ylabel("ATT 与 95% 置信区间")
fig.tight_layout(w_pad=1.2, h_pad=1.0); fig.savefig(sys.argv[2], dpi=300)
