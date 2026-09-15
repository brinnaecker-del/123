# -*- coding: utf-8 -*-
"""用 formulas 库对底稿逐格求值，与论文载值比对。"""
import formulas, warnings, logging, sys
warnings.filterwarnings("ignore"); logging.disable(logging.CRITICAL)
FN = "西藏三元协调评价-计算底稿.xlsx"
sol = formulas.ExcelModel().loads(FN).finish().calculate()
PRE = "'[%s]" % FN
def g(sheet, cell):
    v = sol.get("%s%s'!%s" % (PRE, sheet, cell.upper()))
    try: return float(v.value[0, 0])
    except Exception: return None

P = {"US":[.537,.575,.617,.615,.619,.626,.615,.661,.688,.715],
     "UD":[.467,.483,.489,.519,.484,.528,.539,.672,.713,.718],
     "UE":[.267,.423,.499,.542,.634,.657,.686,.710,.733,.843],
     "D" :[.393,.486,.528,.556,.571,.598,.607,.680,.711,.754]}
P5 = {2017:(.271,.351,.378),2018:(.274,.365,.361),2019:(.297,.357,.346),2020:(.317,.379,.305),
      2021:(.326,.370,.304),2022:(.339,.370,.291),2023:(.343,.338,.319),2024:(.344,.333,.323),
      2025:(.354,.353,.292)}
P4 = {"D3":.3109,"E2":.2556,"E4":.1582,"E1":.1145,"D5":.0922,"D4":.0513}
CODES = ["S1","S2","S3","S4","D1","D2","D3","D4","D5","E1","E2","E3","E4"]

print("=" * 78)
print("一、子系统指数与 MPI（对照论文表3）")
print("年份 |   US 底稿/论文   |   UD 底稿/论文   |   UE 底稿/论文   |  MPI 底稿/论文")
ok = tot = 0
for i, y in enumerate(range(2016, 2026)):
    r = i + 3
    vs = [g("4_子系统指数","B%d"%r), g("4_子系统指数","C%d"%r),
          g("4_子系统指数","D%d"%r), g("5_MPI协调指数","I%d"%r)]
    cells = []
    for v, p in zip(vs, [P[k][i] for k in ("US","UD","UE","D")]):
        tot += 1
        if v is None: cells.append("  ERR   "); continue
        d = abs(v - p); ok += d <= 6e-4
        cells.append("%.4f/%.3f%s" % (v, p, "✓" if d <= 6e-4 else "✗"))
    print("%d | %s" % (y, " | ".join(cells)))
print("→ 吻合 %d/%d" % (ok, tot))

print("\n" + "=" * 78)
print("二、最弱子系统判定（论文核心结论：16-17生态 / 18-22发展 / 23-25安全）")
claim = ["生态"]*2 + ["发展"]*5 + ["安全"]*3
row = []
for i, y in enumerate(range(2016, 2026)):
    v = sol.get("%s5_MPI协调指数'!N%d" % (PRE, i+3))
    try: w = str(v.value[0,0])
    except Exception: w = "?"
    row.append("%d:%s%s" % (y, w, "✓" if w == claim[i] else "✗"))
print("  " + "  ".join(row))

print("\n" + "=" * 78)
print("三、局部敏感性（对照论文表5）")
print("年份 |  εS 底稿/论文  |  εD 底稿/论文  |  εE 底稿/论文")
ok5 = tot5 = 0
for i, y in enumerate(range(2016, 2026)):
    if y not in P5: continue
    r = i + 3; cells = []
    for k, cc in enumerate("BCD"):
        v = g("8_局部敏感性", "%s%d" % (cc, r)); p = P5[y][k]; tot5 += 1
        if v is None: cells.append("  ERR  "); continue
        d = abs(v - p); ok5 += d <= 1.1e-3
        cells.append("%.3f/%.3f%s" % (v, p, "✓" if d <= 1.1e-3 else "✗"))
    print("%d | %s" % (y, " | ".join(cells)))
print("→ 吻合 %d/%d" % (ok5, tot5))

print("\n" + "=" * 78)
print("四、组合权重与结构性贡献缺口（对照论文表4、§5(二)）")
print("编码 | 组合权重 | 贡献缺口均值 底稿/论文")
for k, code in enumerate(CODES):
    w = g("6_组合权重", "L%d" % (k + 5)); o = g("7_结构性贡献缺口", "M%d" % (k + 3))
    p = P4.get(code)
    ws_ = "%.4f" % w if w is not None else " ERR "
    os_ = "%.2f%%" % (o*100) if o is not None else " ERR "
    ps_ = ("%.2f%%" % (p*100)) if p else "   —  "
    mark = ""
    if p and o is not None: mark = "✓" if abs(o - p) <= 0.005 else "✗"
    print("  %-3s |  %s  |   %s / %s %s" % (code, ws_, os_, ps_, mark))

print("\n" + "=" * 78)
print("五、留一法（对照论文表6）")
P6 = {"S1":(0.400,0.755,7),"S4":(0.370,0.722,2),"D3":(0.395,0.791,2),
      "E2":(0.439,0.740,5),"E4":(0.439,0.762,5)}
print("剔除 | 发展最弱年数 底稿/论文 | D(2016) 底稿/论文 | D(2025) 底稿/论文")
for k, code in enumerate(CODES):
    r = k + 3
    cnt = g("9_留一法", "M%d" % r); d16 = g("9_留一法", "N%d" % r); d25 = g("9_留一法", "O%d" % r)
    p = P6.get(code)
    f = lambda x, n=3: ("%.*f" % (n, x)) if x is not None else "ERR"
    if p:
        print("  %-3s |   %s / %d %s   |  %s / %.3f %s |  %s / %.3f %s" % (
            code, f(cnt,0), p[2], "OK" if cnt is not None and abs(cnt-p[2])<1.5 else "!",
            f(d16), p[0], "OK" if d16 is not None and abs(d16-p[0])<=0.004 else "!",
            f(d25), p[1], "OK" if d25 is not None and abs(d25-p[1])<=0.004 else "!"))
    else:
        print("  %-3s |   %s /  —      |  %s /   —        |  %s /   —" % (code, f(cnt,0), f(d16), f(d25)))

print("\n" + "=" * 78)
print("六、稳健性检验与权重集中度（对照论文§5(二)）")
rows=[("滚动端点：极差法最大绝对差异","D47",0.229,"指标层"),
      ("滚动端点：固定基准法最大差异","D48",0.0,"指标层"),
      ("最大单项组合权重","B63",0.303,""),
      ("前四项组合权重合计","B64",0.827,""),
      ("其余九项合计","B65",0.173,""),
      ("安全类四项组合权重合计","B66",None,""),
      ("安全类单项最大权重","B67",0.012,"论文『普遍低于1.2%』")]
for lbl,cell,pv,note in rows:
    v=g("10_稳健性检验",cell)
    vs="%.4f"%v if v is not None else "ERR"
    ps="%.4f"%pv if pv is not None else "  —   "
    mk=""
    if v is not None and pv is not None:
        mk = "OK" if abs(v-pv)<=0.006 else ("<=OK" if pv==0.012 and v<=pv else "差异")
    print("  %-26s %8s   论文 %s  %s %s"%(lbl,vs,ps,mk,note))
