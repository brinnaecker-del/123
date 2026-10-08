# 脚本运行顺序

所有脚本只读 CSMAR 原始文件、写派生文件，不做插补。`<in>` 为 CSMAR 文件目录，`<der>` 为派生目录。
主口径复现开题报告（见 ../复现对照-开题答辩.md）；带 `_alt` 后缀的变量为核查后提出的改进口径，只用于稳健性检验。

1. `01_top1_panel.py <in> <der>` 十大股东 → 第一大股东面板（另存非名义持有人口径）
2. `02_pledge_detail.py <in> <der>` 质押明细表 → 事件—年度余额与事件信息
3. `03_pledge_stat.py <in> <der>` 质押统计表 → 出质方年末余额（主口径与改进口径）
4. `04_build_panel.py <in> <der>` 合并财务、市值、行业、股权性质，构造变量
5. `04b_sample.py <der>` 样本筛选与缩尾 → sample.pkl
6. `05_pressure.py <in> <der>` 平仓压力
7. `10_baseline.py <der>` 表4、表6、表7与质押口径核验
8. `06_channels.py <der>`、`07_boundary.py <der>`、`08_did.py <der> 2000`、`09_robust.py <der>` 后续检验
9. `11_figures.py <der> ../figures`
10. 把 `<der>/res_*.json` 复制到 `../results/`，再 `node ../build-results.js`

公用模块：`names.py`（名称规范化）、`matching.py`（第一大股东与出质方匹配）、`sample.py`（样本与缩尾）、
`reg_common.py`（估计与取数）、`lind_mehlum.py`（U 型检验）。需 `pip install pyfixest`。

注：`../results/` 与结果稿目前仍是复现口径调整之前的版本，待作者确认复现结果后统一重跑。
