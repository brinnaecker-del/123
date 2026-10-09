"""图 1 研究框架。用法：python fig1.py 输出.png"""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch

font_manager.fontManager.addfont("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc")
plt.rcParams.update({"font.family": "WenQuanYi Zen Hei", "font.size": 8})

fig = plt.figure(figsize=(15.5 / 2.54, 7.2 / 2.54))
ax = fig.add_axes([0, 0, 1, 1])          # 坐标单位即毫米
ax.set_xlim(0, 155); ax.set_ylim(0, 72); ax.axis("off")


def box(x, y, w, h, title, lines, fill="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.5", fc=fill, ec="black", lw=0.7))
    ax.text(x + w / 2, y + h - 3.2, title, ha="center", va="top", fontsize=8.2, weight="bold")
    ax.text(x + w / 2, y + h - 9.0, "\n".join(lines), ha="center", va="top", fontsize=7.2, linespacing=1.45)


def arrow(x0, y0, x1, y1):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="-|>", lw=0.8, color="black", mutation_scale=8))


# 左：入表动机（H2）
ax.text(22, 70, "谁在入表（H2）", ha="center", va="top", fontsize=8.5, weight="bold")
box(1, 37, 42, 28, "盈余管理动机（H2a）", ["上年亏损、利润下滑、微利", "→ 借资本化改善利润"])
box(1, 4, 42, 28, "合规与信号动机（H2b）", ["规模较大、国有企业、", "已有研发资本化基础", "→ 分摊合规成本、响应政策"])
# 中：入表
box(56, 22, 38, 28, "数据资产入表", ["数据资源相关支出资本化，", "在存货、无形资产、开发支出", "项目下单列“数据资源”"], fill="0.93")
arrow(43, 51, 56, 40); arrow(43, 18, 56, 32)
# 右：后果
ax.text(132, 70, "入表改变了什么", ha="center", va="top", fontsize=8.5, weight="bold")
box(108, 37, 46, 28, "会计上的利润效应（H1）", ["净利率影响＝相对重要性", "×（总资产÷营业收入）", "→ 集中于中小、亏损企业"])
box(108, 4, 46, 28, "是否伴随盈余管理（H3）", ["H3a：资本化程度、可操纵应计、", "微利概率上升", "H3b：仅为列报细化，无显著变化"])
arrow(94, 40, 108, 51); arrow(94, 32, 108, 18)
fig.savefig(sys.argv[1], dpi=300)
