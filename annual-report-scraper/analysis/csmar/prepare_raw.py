"""第 0 步：把 CSMAR 下载的 xlsx 读成 pickle。
用法：在本目录下建 csmar/ 文件夹，把 CSMAR 下载的 zip 逐个解压到其子文件夹（任意名称），然后运行 python prepare_raw.py。
需要的表：FS_Combas、FS_Comins、FS_Comscfd（旧表：资产总计、负债合计、货币资金、流动资产合计、营业总收入、净利润、经营现金流、资本支出，2004–2025）；
新导出的 FS_Combas、FS_Comins（应收账款、存货、固定资产、无形资产、开发支出及三项「其中：数据资源」；营业收入、研发费用、归母净利润，2021–2025）；
PT_LCRDSPENDING（研发投入）、TRD_Co（公司文件）、EN_EquityNatureAll（股权性质）。CSMAR 数据有使用许可，不要提交到仓库。"""
import glob
import pandas as pd
from load import panel

panel().to_pickle("csmar/panel_old.pkl")
for name, out in (("TRD_Co", "co"), ("EN_EquityNatureAll", "eq")):
    pd.read_excel(glob.glob(f"csmar/*/{name}.xlsx")[0], dtype=str).iloc[2:].to_pickle(f"csmar/{out}.pkl")
# 新导出的两张报表：按字段区分新旧（新表含应收账款 A001111000 / 研发费用 B001216000）
for name, key in (("FS_Combas", "A001111000"), ("FS_Comins", "B001216000"), ("PT_LCRDSPENDING", "RDSpendSum")):
    for f in glob.glob(f"csmar/*/{name}.xlsx"):
        d = pd.read_excel(f, dtype=str)
        if key in d.columns:
            d.to_pickle(f"csmar/{name}_new.pkl")
print("done")
