# 脚本运行顺序

所有脚本只读 CSMAR 原始文件、写派生文件，不做插补。`<in>` 为 CSMAR 文件目录，`<der>` 为派生目录。

1. `01_top1_panel.py <in> <der>` 十大股东 → 第一大股东面板
2. `02_pledge_detail.py <in> <der>` 质押明细表 → 出质方年末余额（明细表口径）
3. `03_pledge_stat.py <in> <der>` 质押统计表 → 出质方年末余额（基准口径）
4. `04_build_panel.py <in> <der>` 合并财务、市值、行业、股权性质，构造变量
5. `05_pressure.py <in> <der>` 平仓压力
6. `10_baseline.py <der>` 表4、表6、表7
7. `06_channels.py <der>` 表5-5、5-6
8. `07_boundary.py <der>` 表5-8—5-10
9. `08_did.py <der> 500` 表5-11、5-12、图5-1、图5-2 的数据
10. `09_robust.py <der>` 表5-15—5-19
11. `11_figures.py <der> ../figures`
12. 把 `<der>/res_*.json` 复制到 `../results/`，再 `node ../build-results.js`

`sample.py`（样本筛选与缩尾）、`reg_common.py`（估计与取数）、`lind_mehlum.py`（U 型检验）为公用模块。需 `pip install pyfixest`。
