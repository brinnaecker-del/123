"""由 CSMAR 十大股东文件（可多个分卷）与公司文件 TRD_Co 构造“公司—年度”第一大股东面板。

用法：python -I 01_top1_panel.py <输入目录> <输出目录>
输入目录内放 HLD_Shareholders*.xlsx（任意个分卷）与 TRD_Co.xlsx。
只做整理与核查，不做任何插补；质押冻结标识 S0303a 保留原始代码，含义以 CSMAR 字段说明为准。
"""
import sys, glob, os
import pandas as pd

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
read = lambda f: pd.read_excel(f, header=0, skiprows=[1, 2], dtype={'Stkcd': str})

parts = sorted(glob.glob(os.path.join(src, '*HLD_Shareholders*.xlsx')))
h = pd.concat([read(f) for f in parts], ignore_index=True)
n_raw = len(h)
h = h.drop_duplicates()  # 分卷边界可能重叠
h['year'] = h['Reptdt'].str[:4].astype(int)
h = h[h['Reptdt'].str[5:] == '12-31']

co = read(os.path.join(src, 'TRD_Co.xlsx'))
co['Listdt'] = pd.to_datetime(co['Listdt'], errors='coerce')  # 0000-00-00 → 缺失

r1 = h[h['S0306a'] == 1].rename(columns={
    'S0301a': 'Top1Name', 'S0302a': 'Top1Shares', 'S0303a': 'Top1Flag_raw',
    'S0304a': 'Top1Pct', 'S0305a': 'Top1ShareType', 'ShareholderNature': 'Top1Nature'})
dup = r1.duplicated(['Stkcd', 'year'], keep=False)
r1 = r1[~dup]
panel = r1[['Stkcd', 'year', 'Top1Name', 'Top1Shares', 'Top1Pct', 'Top1Flag_raw', 'Top1ShareType', 'Top1Nature']]
panel = panel.merge(co[['Stkcd', 'Listdt', 'Nnindcd', 'Nnindnme', 'PROVINCE']], on='Stkcd', how='left')
panel['ListYear'] = panel['Listdt'].dt.year
panel['ListedBefore2016'] = (panel['Listdt'] < '2016-01-01').astype('Int64').where(panel['Listdt'].notna())
panel.to_csv(os.path.join(out, 'top1_panel.csv'), index=False, encoding='utf-8-sig')

rows = h.groupby(['Stkcd', 'year']).size()
rep = [
    f'分卷：{[os.path.basename(p) for p in parts]}',
    f'原始行数 {n_raw}，去重后 {len(h)}；公司 {h.Stkcd.nunique()} 家，代码范围 {h.Stkcd.min()}—{h.Stkcd.max()}，年份 {h.year.min()}—{h.year.max()}',
    f'公司—年度 {len(rows)} 个；第一大股东重复的公司—年度 {int(dup.sum() // 2)} 个（已剔除）；股东行数>10 的 {int((rows > 10).sum())} 个，<10 的 {int((rows < 10).sum())} 个',
    f'未匹配到 TRD_Co 的公司—年度 {int(panel.Listdt.isna().sum())} 个（含上市日期为 0000-00-00 者）',
    '第一大股东 S0303a 原始代码分布（按年）：',
    pd.crosstab(panel.year, panel.Top1Flag_raw).to_string(),
]
open(os.path.join(out, '核查报告.txt'), 'w', encoding='utf-8').write('\n'.join(rep))
print('\n'.join(rep[:4]))
