"""读取 CSMAR 旧版三张报表，合并为公司—年度面板（被 prepare_raw.py 调用）。"""
import glob
import numpy as np
import pandas as pd

def read(pattern):
    """读旧表（2004–2025、字段较少的那一份）。"""
    for f in glob.glob(f"csmar/*/{pattern}.xlsx"):
        d = pd.read_excel(f, dtype=str)
        if "A001111000" not in d.columns and "B001216000" not in d.columns:
            break
    d = d.iloc[2:]
    d = d[(d.Typrep == "A") & d.Accper.str.endswith("12-31")].copy()
    d["year"] = d.Accper.str[:4].astype(int)
    for c in d.columns:
        if c[:1] in "ABC" and c[1:].isdigit():
            d[c] = pd.to_numeric(d[c], errors="coerce")
    return d.drop(columns=["Typrep", "Accper"]).drop_duplicates(["Stkcd", "year"])

def panel():
    bs, inc, cf = read("FS_Combas"), read("FS_Comins"), read("FS_Comscfd")
    p = bs.merge(inc.drop(columns="ShortName"), on=["Stkcd", "year"], how="outer").merge(cf.drop(columns="ShortName"), on=["Stkcd", "year"], how="outer")
    p = p.rename(columns={"A001000000": "TA", "A002000000": "TL", "A001101000": "CASH", "A001100000": "CA", "B001100000": "REV",
                          "B002000000": "NI", "C001000000": "CFO", "C002006000": "CAPEX"})
    return p.sort_values(["Stkcd", "year"])
