# -*- coding: utf-8 -*-
"""按论文现行方法（固定基准标准化 + 子系统内等权 + MPI）复算，与论文载值比对。
数据源：data/计算底稿-旧版方法.xlsx 的「1_原始数据」表（该表原始数据有效，
        但同工作簿的 2_—7_ 计算表使用的是旧版方法，与现稿不符）。"""
import openpyxl, os, sys

XLSX = os.path.join(os.path.dirname(__file__), '..', 'data', '计算底稿-旧版方法.xlsx')
YS = list(range(2016, 2026))

def load():
    ws = openpyxl.load_workbook(XLSX, data_only=True)['1_原始数据']
    return {r[1]: list(r[4:14]) for r in ws.iter_rows(min_row=2, values_only=True) if r[1]}

def std(x, lo, hi, positive=True):
    """式(1)(2) 固定基准标准化并截断，式(3) 平移压缩至 [0.01, 0.99]"""
    v = (x - lo) / (hi - lo) if positive else (hi - x) / (hi - lo)
    return 0.98 * min(1.0, max(0.0, v)) + 0.01

def mpi(u):
    M = sum(u) / 3
    S2 = sum((x - M) ** 2 for x in u) / 3
    return M - S2 / M, M, S2

def elasticity(u):
    D, M, S2 = mpi(u)
    return [(1/3 - 2*(x - M)/(3*M) + S2/(3*M*M)) * x / D for x in u]

# ---- 论文载值 ----
PAPER = {
 'US': [.537,.575,.617,.615,.619,.626,.615,.661,.688,.715],
 'UD': [.467,.483,.489,.519,.484,.528,.539,.672,.713,.718],
 'UE': [.267,.423,.499,.542,.634,.657,.686,.710,.733,.843],
 'D':  [.393,.486,.528,.556,.571,.598,.607,.680,.711,.754]}
PAPER_EPS = {2017:(.271,.351,.378),2018:(.274,.365,.361),2019:(.297,.357,.346),
             2020:(.317,.379,.305),2021:(.326,.370,.304),2022:(.339,.370,.291),
             2023:(.343,.338,.319),2024:(.344,.333,.323),2025:(.354,.353,.292)}

def main():
    R = load()
    # 生态子系统：E1—E4 四项均可由原始数据直接算得
    E = {
      'E1': [std(v, 60, 100, False)        for v in R['单位GDP能耗指数']],
      'E2': [std(v*100, 11.98, 12.51)      for v in R['森林覆盖率']],
      'E3': [std(v, 0, 100)                for v in R['空气质量优良天数比例']],
      'E4': [std(v, 42.3, 50)              for v in R['草原综合植被盖度']]}
    UE = [sum(E[k][i] for k in E) / 4 for i in range(10)]

    print("生态子系统 UE　复算 vs 论文表3")
    bad = 0
    for i, y in enumerate(YS):
        d = UE[i] - PAPER['UE'][i]; bad += abs(d) > 6e-4
        print("  %d  复算 %.4f  论文 %.3f  差 %+.4f  %s" % (y, UE[i], PAPER['UE'][i], d, "OK" if abs(d) <= 6e-4 else "不符"))
    print("  → %d/10 吻合\n" % (10 - bad))

    print("MPI 协调指数　由论文 US/UD/UE 复算 vs 论文表3 D列")
    bad = 0
    for i, y in enumerate(YS):
        c, _, _ = mpi((PAPER['US'][i], PAPER['UD'][i], PAPER['UE'][i]))
        d = c - PAPER['D'][i]; bad += abs(d) > 6e-4
        print("  %d  复算 %.4f  论文 %.3f  差 %+.4f  %s" % (y, c, PAPER['D'][i], d, "OK" if abs(d) <= 6e-4 else "边界"))
    print("  → %d/10 在容差内\n" % (10 - bad))

    print("局部敏感性　复算 vs 论文表5")
    bad = 0
    for i, y in enumerate(YS):
        if y not in PAPER_EPS: continue
        eps = elasticity((PAPER['US'][i], PAPER['UD'][i], PAPER['UE'][i]))
        for k, nm in enumerate(('S', 'D', 'E')):
            d = eps[k] - PAPER_EPS[y][k]; bad += abs(d) > 1.1e-3
        print("  %d  eS %.3f/%.3f  eD %.3f/%.3f  eE %.3f/%.3f" % (
            y, eps[0], PAPER_EPS[y][0], eps[1], PAPER_EPS[y][1], eps[2], PAPER_EPS[y][2]))
    print("  → %d/27 吻合\n" % (27 - bad))

    print("尚缺的三条辅助序列（缺则 US、UD 无法复算）：")
    print("  1. 西藏常住人口（万人，2016—2025）      → S1 人均一般公共预算收入、D4 人均接待游客")
    print("  2. 全国城乡居民人均可支配收入比（倍）    → S2 与全国差距")
    print("  3. 全国农村居民人均可支配收入（元）      → D2 相对全国水平")

if __name__ == '__main__':
    main()
