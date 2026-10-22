"""Clean the 74-county Tibet panel (2016-2024) for the JEA manuscript.

Rules (documented in Appendix A of the manuscript):
  R1  Chengguan District has no observations at all -> dropped (73 counties remain).
  R2  Spike rule for own revenue and expenditure: a county-year value is set to
      missing when its log deviates from BOTH adjacent years by more than ln(4)
      in the same direction (a one-year jump of more than 4x that reverses).
      For end years, the single neighbour is used together with the county median.
  R3  Mirror rule: own revenue is set to missing when it is >= 80% of expenditure
      in a county whose median self-sufficiency ratio is below 20%
      (values that look like an expenditure figure keyed into the revenue column).
  R4  Expenditure is set to missing when it falls below own revenue (self-sufficiency
      ratio > 1), which no Tibetan county records in any other year.
  R5  GDP level shifts (statistical re-basing) are kept; the two counties
      concerned (Gar 2020, Seni 2019) are flagged and excluded in a robustness check.
Output: jea/output/panel_clean.csv and jea/output/cleaning_log.csv
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
os.makedirs(OUT, exist_ok=True)

PREF_EN = {"拉萨市": "Lhasa", "日喀则市": "Shigatse", "昌都市": "Chamdo", "林芝市": "Nyingchi",
           "山南市": "Shannan", "那曲市": "Nagqu", "阿里地区": "Ngari"}

raw = pd.read_excel(os.path.join(HERE, "..", "data", "区县面板2016-2024.xlsx"))
raw.columns = ["code", "pref_cn", "county_cn", "year", "gdp", "pop_res", "pop", "rev", "exp"]
df = raw[raw.county_cn != "城关区"].copy()
df["pref"] = df.pref_cn.map(PREF_EN)
log = []


def spike_flags(series):
    """series indexed by year for one county (log values)."""
    flags = []
    yrs = list(series.index)
    med = series.median()
    thr = np.log(4)
    for k, y in enumerate(yrs):
        v = series[y]
        if np.isnan(v):
            continue
        nb = [series[yrs[j]] for j in (k - 1, k + 1) if 0 <= j < len(yrs) and not np.isnan(series[yrs[j]])]
        if not nb:
            continue
        if len(nb) == 1:
            nb.append(med)
        d = [v - n for n in nb]
        if all(x > thr for x in d) or all(x < -thr for x in d):
            flags.append(y)
    return flags


for var in ["rev", "exp"]:
    for code, g in df.groupby("code"):
        s = np.log(g.set_index("year")[var].astype(float))
        for y in spike_flags(s):
            i = g.index[g.year == y][0]
            log.append(dict(county=g.county_cn.iloc[0], year=y, variable=var, value=df.at[i, var], rule="R2 spike"))
            df.at[i, var] = np.nan

ratio = df.rev / df.exp
med_ratio = ratio.groupby(df.code).transform("median")
mask = (ratio >= 0.8) & (med_ratio < 0.2)
for i in df.index[mask]:
    log.append(dict(county=df.at[i, "county_cn"], year=df.at[i, "year"], variable="rev",
                    value=df.at[i, "rev"], rule="R3 mirror"))
    df.at[i, "rev"] = np.nan

mask = df.rev > df.exp
for i in df.index[mask]:
    log.append(dict(county=df.at[i, "county_cn"], year=df.at[i, "year"], variable="exp",
                    value=df.at[i, "exp"], rule="R4 exp<rev"))
    df.at[i, "exp"] = np.nan

df["level_shift"] = df.county_cn.isin(["噶尔县", "色尼区"])

pd.DataFrame(log).to_csv(os.path.join(OUT, "cleaning_log.csv"), index=False, encoding="utf-8-sig")
raw[raw.county_cn != "城关区"].assign(pref=lambda d: d.pref_cn.map(PREF_EN),
    level_shift=lambda d: d.county_cn.isin(["噶尔县", "色尼区"])).to_csv(os.path.join(OUT, "panel_raw.csv"), index=False, encoding="utf-8-sig")
df.to_csv(os.path.join(OUT, "panel_clean.csv"), index=False, encoding="utf-8-sig")
print(pd.DataFrame(log).to_string())
print("counties:", df.code.nunique(), " obs:", len(df))
print(df[["gdp", "pop", "rev", "exp"]].notna().sum())
