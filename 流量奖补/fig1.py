# -*- coding: utf-8 -*-
"""重绘图1（分析框架）：理论基础第二项改为“公共财政与激励合同理论”，
第二列改为“现状与测算”并新增“激励结构与回收阈值测算”。版式沿用原图。"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle, Polygon
import sys
FD = sys.argv[1] if len(sys.argv) > 1 else '.'
REG = fm.FontProperties(fname=FD + '/NotoSerifSC-Regular.otf')
BOLD = fm.FontProperties(fname=FD + '/NotoSerifSC-Bold.otf')
W, H = 1340, 962
fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis('off')

def box(x0, y0, x1, y1, text, fill='white', font=REG, size=22, lw=2.2):
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=fill, edgecolor='black', lw=lw))
    ax.text((x0 + x1) / 2, (y0 + y1) / 2, text, ha='center', va='center', fontproperties=font,
            fontsize=size, linespacing=1.45)

cols = [(30, 242), (290, 503), (553, 797), (841, 1085), (1129, 1308)]
heads = ['理论基础', '现状与测算', '现实困境', '优化路径', '政策目标']
for (x0, x1), h in zip(cols, heads):
    box(x0, 55, x1, 128, h, fill='#e6e6e6', font=BOLD, size=25)
TOP, BOT = 172, 877
def stack(n, gap):
    hgt = (BOT - TOP - gap * (n - 1)) / n
    return [(TOP + i * (hgt + gap), TOP + i * (hgt + gap) + hgt) for i in range(n)]
for (y0, y1), t in zip(stack(3, 35), ['流量经济\n理论', '公共财政与\n激励合同理论', '产业融合\n理论']):
    box(*cols[0][:1], y0, cols[0][1], y1, t, size=22) if False else box(cols[0][0], y0, cols[0][1], y1, t, size=21)
for (y0, y1), t in zip(stack(4, 28), ['文旅产业\n发展成效', '产业发展\n现存短板', '财政金融\n扶持现状', '激励结构与\n回收阈值测算']):
    box(cols[1][0], y0, cols[1][1], y1, t, size=21)
left = ['流量评价单一', '重奖励轻培育', '政策协同碎片化', '基金运作不完善', '金融支撑薄弱', '绩效监管不健全']
right = ['双激励评价机制', '前移扶持关口', '强化政策协同', '创新基金运作', '财政引导金融', '全链条绩效监管']
for (y0, y1), a, b in zip(stack(6, 17), left, right):
    box(cols[2][0], y0, cols[2][1], y1, a, size=19)
    box(cols[3][0], y0, cols[3][1], y1, b, size=19)
    ym = (y0 + y1) / 2
    ax.plot([cols[2][1], cols[3][0]], [ym, ym], ls=(0, (2, 2)), color='black', lw=1.6)
box(cols[4][0], TOP, cols[4][1], BOT, '', fill='#f0f0f0', lw=3)
for y, t in [(385, '“流量”'), (432, '↓'), (478, '“留量”'), (525, '↓'), (572, '产业增量'), (618, '↓'), (664, '富民增收')]:
    ax.text((cols[4][0] + cols[4][1]) / 2, y, t, ha='center', va='center',
            fontproperties=BOLD if t != '↓' else REG, fontsize=24)
for xa, xb in [(242, 290), (503, 553), (797, 841), (1085, 1129)]:
    xm = (xa + xb) / 2; ym = 525
    ax.plot([xm - 10, xm + 2], [ym, ym], color='black', lw=2.5)
    ax.add_patch(Polygon([[xm + 2, ym - 8], [xm + 12, ym], [xm + 2, ym + 8]], color='black'))
fig.savefig('fig1-修订.png', dpi=200, facecolor='white')
