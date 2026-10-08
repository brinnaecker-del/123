"""由 CSMAR 十大股东文件（可多个分卷）与公司文件 TRD_Co 构造“公司—年度”第一大股东面板。

用法：python -I 01_top1_panel.py <输入目录> <输出目录>
输入目录内放 HLD_Shareholders*.xlsx（任意个分卷）与 TRD_Co.xlsx。
注：CSMAR 导出的第 2 卷 sheet1.xml 末尾结束标签重复，须先截去重复部分（见数据接收记录）。
只做整理与核查，不做任何插补；质押冻结标识 S0303a 保留原始代码，含义以 CSMAR 字段说明为准。
"""
import sys, glob, os
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from names import is_nominee

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
read = lambda f: pd.read_excel(f, header=0, skiprows=[1, 2], dtype={'Stkcd': str})

parts = sorted(glob.glob(os.path.join(src, '*HLD_Shareholders*.xlsx')))
# 第 1 卷带三行表头；后续分卷无表头、前部为空行，按第 1 卷列名对齐（分卷可能切在同一公司—年度中间，拼接后即完整）
h0 = read(parts[0])
frames = [h0]
for f in parts[1:]:
    x = pd.read_excel(f, header=None, dtype=str).dropna(how='all')
    if str(x.iloc[0, 0]) == h0.columns[0]:
        x = x.iloc[3:]
    x.columns = h0.columns
    frames.append(x)
h = pd.concat(frames, ignore_index=True)
for c in ['S0306a', 'S0302a', 'S0304a', 'S0303a']:
    h[c] = pd.to_numeric(h[c], errors='coerce')
h['Stkcd'] = h['Stkcd'].astype(str)
n_raw = len(h)
h = h.drop_duplicates()  # 分卷边界可能重叠
h['year'] = h['Reptdt'].str[:4].astype(int)
h = h[h['Reptdt'].str[5:] == '12-31']

co = read(os.path.join(src, 'TRD_Co.xlsx'))
co['Listdt'] = pd.to_datetime(co['Listdt'], errors='coerce')  # 0000-00-00 → 缺失

# 主口径：排名第 1 的股东（与开题报告一致）
r1 = h[h['S0306a'] == 1].rename(columns={
    'S0301a': 'Top1Name', 'S0302a': 'Top1Shares', 'S0303a': 'Top1Flag_raw',
    'S0304a': 'Top1Pct', 'S0305a': 'Top1ShareType', 'ShareholderNature': 'Top1Nature'})
dup = r1.duplicated(['Stkcd', 'year'], keep=False)
r1 = r1[~dup]
# 改进口径（稳健性）：排名最靠前的非名义持有人（香港结算等代理人账户汇总的是 H 股或陆股通持股，不是实际股东）
h['nominee'] = h['S0301a'].map(is_nominee)
nn = h[~h['nominee']].sort_values(['Stkcd', 'year', 'S0306a']).groupby(['Stkcd', 'year']).head(1)
nn = nn.rename(columns={'S0301a': 'Top1Name_nn', 'S0302a': 'Top1Shares_nn', 'S0304a': 'Top1Pct_nn', 'S0306a': 'Top1Rank_nn'})
r1 = r1.merge(nn[['Stkcd', 'year', 'Top1Name_nn', 'Top1Shares_nn', 'Top1Pct_nn', 'Top1Rank_nn']], on=['Stkcd', 'year'], how='left')
r1['Rank1IsNominee'] = r1['Top1Name'].map(is_nominee)
panel = r1[['Stkcd', 'year', 'Top1Name', 'Top1Shares', 'Top1Pct', 'Top1Flag_raw', 'Top1ShareType', 'Top1Nature',
            'Rank1IsNominee', 'Top1Name_nn', 'Top1Shares_nn', 'Top1Pct_nn', 'Top1Rank_nn']]
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
    f'排名第 1 为名义持有人的公司—年度（改进口径改取下一位非名义股东） {int(panel.Rank1IsNominee.sum())} 个（{panel[panel.Rank1IsNominee].Stkcd.nunique()} 家）',
    '第一大股东 S0303a 原始代码分布（按年）：',
    pd.crosstab(panel.year, panel.Top1Flag_raw).to_string(),
]
open(os.path.join(out, '核查报告.txt'), 'w', encoding='utf-8').write('\n'.join(rep))
print('\n'.join(rep[:4]))
