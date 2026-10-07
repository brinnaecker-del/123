"""图5-1 事件研究、图5-2 置换安慰剂分布（静态 PNG，供 Word 插入）。"""
import sys, os, json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

der, outdir = sys.argv[1], sys.argv[2]
fp = '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'
fm.fontManager.addfont(fp)
plt.rcParams.update({'font.family': fm.FontProperties(fname=fp).get_name(), 'axes.unicode_minus': False,
                     'font.size': 10, 'axes.edgecolor': '#8a8a8a', 'axes.linewidth': 0.8,
                     'xtick.color': '#444444', 'ytick.color': '#444444'})
INK, MUTED, GRID = '#1f2a44', '#8a8a8a', '#e6e6e6'
r = json.load(open(os.path.join(der, 'res_did.json')))

ev = r['event']
yrs = np.array([e['year'] for e in ev]); b = np.array([e['b'] for e in ev])
lo = np.array([e['lo'] for e in ev]); hi = np.array([e['hi'] for e in ev])
fig, ax = plt.subplots(figsize=(6.3, 3.4), dpi=200)
ax.axhline(0, color=MUTED, lw=0.8)
ax.axvline(2017.5, color=MUTED, lw=0.8, ls='--')
ax.vlines(yrs, lo, hi, color=INK, lw=1.4)
ax.plot(yrs, b, 'o', color=INK, ms=4.5, mec='white', mew=0.8, zorder=3)
ax.text(2017.6, ax.get_ylim()[1] * 0.92, '新规实施（2018）', color='#444444', fontsize=9, va='top')
ax.set_xticks(yrs[::2]); ax.set_xlabel('年度（基期为2017年）'); ax.set_ylabel('PledgePre×年度 系数')
ax.grid(axis='y', color=GRID, lw=0.6); ax.set_axisbelow(True)
for sp in ['top', 'right']: ax.spines[sp].set_visible(False)
fig.tight_layout(); fig.savefig(os.path.join(outdir, 'fig5-1_event.png')); plt.close(fig)

perm = np.load(os.path.join(der, 'perm.npy')); true = r['placebo_perm']['true']
fig, ax = plt.subplots(figsize=(6.3, 3.2), dpi=200)
ax.hist(perm, bins=40, color='#9aa6bf', edgecolor='white', linewidth=0.6)
ax.axvline(true, color=INK, lw=1.6)
ax.text(true, ax.get_ylim()[1] * 0.95, f' 真实估计值 {true:.4f}', color=INK, fontsize=9, va='top', ha='left')
ax.set_xlabel('随机置换处理强度后的 PledgePre×Post 系数（500次）'); ax.set_ylabel('频数')
ax.grid(axis='y', color=GRID, lw=0.6); ax.set_axisbelow(True)
for sp in ['top', 'right']: ax.spines[sp].set_visible(False)
fig.tight_layout(); fig.savefig(os.path.join(outdir, 'fig5-2_placebo.png')); plt.close(fig)
print('ok')
