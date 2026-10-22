"""Build the JEA submission files from the analysis outputs (run analysis.py first).

Every number quoted in the text and tables is read from jea/output/*.csv, so the
manuscript cannot drift from the code. Outputs (jea/submission/):
  Manuscript_anonymised.docx, Title_page.docx, Highlights.docx, Cover_letter.docx,
  Figure_1.png ... Figure_3.png, Supplementary_data.xlsx
"""
import os
import shutil
import subprocess
import numpy as np
import pandas as pd
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_LINE_SPACING

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
SUB = os.path.join(HERE, "submission")
os.makedirs(SUB, exist_ok=True)
rd = lambda f: pd.read_csv(os.path.join(OUT, f))

ineq = rd("T_inequality.csv")
bal = rd("T_inequality_common_sample.csv")
pref = pd.read_csv(os.path.join(OUT, "T_prefectures.csv"), index_col=0)
ssr = rd("T_ssr_year.csv")
el = rd("T_elasticities.csv")
sig = rd("T_sigma.csv")
beta = rd("T_beta.csv")
asy = rd("T_asymmetry.csv").set_index("model")
het = rd("T_asymmetry_heterogeneity.csv")
rob = rd("T_robustness.csv")
jk = rd("T_jackknife_contractions.csv")
conc = rd("T_concentration_74.csv").set_index("year")
clog = rd("cleaning_log.csv")
panel = rd("panel_analysis.csv")

f2 = lambda x: f"{x:.2f}"
f3 = lambda x: f"{x:.3f}"
pc = lambda x, d=1: f"{100 * x:.{d}f}"


def stars(p):
    return "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""


def coef(b, se, d=3):
    from scipy.stats import norm
    p = 2 * (1 - norm.cdf(abs(b / se)))
    return f"{b:.{d}f}{stars(p)}", f"({se:.{d}f})"


V = {}
g = lambda var, y, col: ineq[(ineq["var"] == var) & (ineq.year == y)][col].iloc[0]
b = bal.set_index("year")
V["n_obs"] = len(panel)
V["gini_rev_lo"], V["gini_rev_hi"] = f2(b.gini_rev_pc.min()), f2(b.gini_rev_pc.max())
V["gini_gdp_lo"], V["gini_gdp_hi"] = f2(b.gini_gdp_pc.min()), f2(b.gini_gdp_pc.max())
V["gini_exp_lo"], V["gini_exp_hi"] = f2(b.gini_exp_pc.min()), f2(b.gini_exp_pc.max())
V["eq16"], V["eq24"] = f2(b.equalisation_gini[2016]), f2(b.equalisation_gini[2024])
V["eq_mid_lo"] = f2(b.equalisation_gini.loc[2018:2022].min())
V["eq_mid_hi"] = f2(b.equalisation_gini.loc[2018:2022].max())
V["gexp22"], V["gexp24"] = f2(b.gini_exp_pc[2022]), f2(b.gini_exp_pc[2024])
V["ssr_med_lo"], V["ssr_med_hi"] = pc(ssr.ssr_median.min()), pc(ssr.ssr_median.max())
V["ssr_pool"] = pc(pref.loc["All 73 counties", "ssr_pooled"])
V["share10_lo"], V["share10_hi"] = pc(ssr.share_below_10.min(), 0), pc(ssr.share_below_10.max(), 0)
V["ssr_lhasa"] = pc(pref.loc["Lhasa", "ssr_pooled"])
V["ssr_nagqu"] = pc(pref.loc["Nagqu", "ssr_pooled"])
e = el.set_index(["spec", "dep"])
V["el_rev"] = f2(e.loc[("pooled + year FE", "lrev_pc"), "b"])
V["el_exp"] = f2(e.loc[("pooled + year FE", "lexp_pc"), "b"])
V["el_rev_fe"] = f2(e.loc[("county FE (within)", "lrev_pc"), "b"])
V["el_exp_fe"] = f2(e.loc[("county FE (within)", "lexp_pc"), "b"])
V["el_er_fe"] = f2(e.loc[("county FE (within)", "lexp_pc|lrev_pc"), "b"])
bt = beta.set_index(["sample", "spec"])
ab = bt.loc[("all", "absolute")]
V["beta"] = f3(ab.beta); V["beta_se"] = f3(ab.se)
V["speed"] = pc(ab.speed); V["hl"] = f"{ab.half_life:.0f}"
cd = bt.loc[("all", "conditional (prefecture FE)")]
V["beta_c"] = f3(cd.beta); V["speed_c"] = pc(cd.speed)
ex = bt.loc[("excl. level-shift counties", "absolute")]
V["beta_x"] = f3(ex.beta); V["speed_x"] = pc(ex.speed)
s = sig.set_index("year")
V["sd16"], V["sd24"] = f3(s.sd_log[2016]), f3(s.sd_log[2024])
V["sd20"] = f3(s.sd_log[2020])
V["gg16"], V["gg24"] = f3(s.gini[2016]), f3(s.gini[2024])
V["bs16"] = pc(g("gdp_pc", 2016, "T_between_share"), 0)
V["bs24"] = pc(g("gdp_pc", 2024, "T_between_share"), 0)
V["bsrev_lo"] = pc(ineq[ineq["var"] == "rev_pc"].T_between_share.min(), 0)
V["bsrev_hi"] = pc(ineq[ineq["var"] == "rev_pc"].T_between_share.max(), 0)
r5 = asy.loc["(5) Own revenue on GDP, county+year FE"]
V["rp"], V["rn"], V["rwp"] = f2(r5.b_pos), f2(r5.b_neg), f3(r5.wald_p)
V["rp_se"], V["rn_se"] = f2(r5.se_pos), f2(r5.se_neg)
r2 = asy.loc["(2) Exp on GDP, county+year FE"]
V["ep"], V["en"], V["ewp"] = f2(r2.b_pos), f2(r2.b_neg), f2(r2.wald_p)
r3 = asy.loc["(3) Exp on own revenue, county+year FE"]
V["erp"], V["ern"], V["erwp"] = f2(r3.b_pos), f2(r3.b_neg), f2(r3.wald_p)
V["n_contr"] = int((panel.dropna(subset=["dlrev"]).dlgdp < 0).sum())
V["n_contr_all"] = int((panel.dlgdp < 0).sum())
V["n_changes"] = int(panel.dlgdp.notna().sum())
V["jk_lo"], V["jk_hi"], V["jk_p"] = f2(jk.b_neg.min()), f2(jk.b_neg.max()), f3(jk.wald_p.max())
rr = rob.set_index("model")
rev_rob = rob[rob.model.str.startswith("Own revenue")]
V["rob_rn_lo"], V["rob_rn_hi"] = f2(rev_rob.b_neg.max()), f2(rev_rob.b_neg.min())
V["rob_p_max"] = f3(rev_rob.wald_p.max())
exp_rob = rob[rob.model.str.startswith("Exp")]
V["exp_rob_pmin"] = f2(exp_rob.wald_p.min())
ix = rd("T_inequality_excl_shift.csv").set_index("year")
V["bsx16"], V["bsx24"] = pc(ix.between_share[2016]), pc(ix.between_share[2024])
_er = e.loc[("county FE (within)", "lexp_pc|lrev_pc"), "b"]
V["mpe_lo"] = f"{_er / pref.loc['All 73 counties', 'ssr_pooled']:.1f}"
V["mpe_hi"] = f"{_er / panel.ssr.median():.1f}"
V["cg16"], V["cg24"] = pc(conc.chengguan_share[2016]), pc(conc.chengguan_share[2024])
V["n_clean"] = len(clog)
p24 = pref
V["exp_ngari"] = f"{p24.loc['Ngari', 'exp_pc_2024']:,.0f}"
V["exp_chamdo"] = f"{p24.loc['Chamdo', 'exp_pc_2024']:,.0f}"
V["gdp_lhasa"] = f"{p24.loc['Lhasa', 'gdp_pc_2024']:,.0f}"
V["gdp_nagqu"] = f"{p24.loc['Nagqu', 'gdp_pc_2024']:,.0f}"

# ------------------------------------------------------------------ tables
T1 = ["| Prefecture | Counties | Pop. 2024 | GDP p.c. 2016 | GDP p.c. 2024 | SSR pooled (%) | SSR median (%) | Exp. p.c. 2024 |",
      "|:------------------|------:|------:|---------:|---------:|--------:|--------:|---------:|"]
for k, r in pref.iterrows():
    T1.append(f"| {k} | {int(r.counties)} | {r.pop_2024:.0f} | {r.gdp_pc_2016:,.0f} | {r.gdp_pc_2024:,.0f} | {100 * r.ssr_pooled:.1f} | {100 * r.ssr_median_county:.1f} | {r.exp_pc_2024:,.0f} |")
T1 = "\n".join(T1)

T2 = ["| Year | *N* | Gini GDP | Gini Rev | Gini Exp | *E* | *T* GDP | *B* GDP (%) | *B* Rev (%) |",
      "|:-----|----:|------:|------:|------:|------:|------:|-------:|-------:|"]
for y, r in b.iterrows():
    T2.append(f"| {y} | {int(r.n)} | {r.gini_gdp_pc:.3f} | {r.gini_rev_pc:.3f} | {r.gini_exp_pc:.3f} | {r.equalisation_gini:.3f} | "
              f"{g('gdp_pc', y, 'theilT'):.3f} | {100 * g('gdp_pc', y, 'T_between_share'):.1f} | {100 * g('rev_pc', y, 'T_between_share'):.1f} |")
T2 = "\n".join(T2)

T3 = ["| Dependent variable | Regressor | Pooled, year FE | Prefecture and year FE | County and year FE |", "|:----------------|:----------------|:---------:|:---------:|:---------:|"]
for dep, lab, reg in [("lrev_pc", "ln own revenue p.c.", "ln GDP p.c."), ("lexp_pc", "ln expenditure p.c.", "ln GDP p.c."),
                      ("lexp_pc|lrev_pc", "ln expenditure p.c.", "ln own revenue p.c.")]:
    cells, ses = [], []
    for spec in ["pooled + year FE", "+ prefecture FE", "county FE (within)"]:
        r = e.loc[(spec, dep)]
        c, s_ = coef(r.b, r.se)
        cells.append(c); ses.append(s_)
    T3.append(f"| {lab} | {reg} | " + " | ".join(cells) + " |")
    T3.append("| | | " + " | ".join(ses) + " |")
    T3.append("| | *N* / *R*² | " + " | ".join(f"{int(e.loc[(sp, dep), 'n'])} / {e.loc[(sp, dep), 'r2']:.2f}"
                                              for sp in ["pooled + year FE", "+ prefecture FE", "county FE (within)"]) + " |")
T3 = "\n".join(T3)

T4 = ["| Specification | Sample | β (s.e.) | λ (%) | Half-life (years) | *N* | *R*² |", "|:---------------------|:-------------|:--------------:|------:|------:|----:|-----:|"]
for _, r in beta.iterrows():
    c, s_ = coef(r.beta, r.se, 4)
    hl = f"{r.half_life:.1f}" if np.isfinite(r.half_life) else "–"
    spec = {"absolute": "Cross-section, absolute", "conditional (prefecture FE)": "Cross-section, prefecture FE",
            "annual panel, year FE": "Panel, year FE", "annual panel, prefecture+year FE": "Panel, prefecture + year FE",
            "annual panel, county+year FE": "Panel, county + year FE†"}[r.spec]
    smp = "All 73" if r["sample"] == "all" else "Excl. re-based"
    T4.append(f"| {spec} | {smp} | {c} {s_} | {100 * r.speed:.1f} | {hl} | {int(r.n)} | {r.r2:.2f} |")
T4 = "\n".join(T4)

T5 = ["| | (1) Exp. | (2) Exp. | (3) Exp. | (4) Exp. | (5) Own revenue |", "|:----------------------|:-------:|:-------:|:-------:|:-------:|:-------:|"]
m = {k: asy.loc[k] for k in asy.index}
rowsT5 = {"Δln GDP⁺": ["(1) Exp on GDP, year FE", "(2) Exp on GDP, county+year FE", None, "(4a) joint: GDP", "(5) Own revenue on GDP, county+year FE"],
          "Δln own revenue⁺": [None, None, "(3) Exp on own revenue, county+year FE", "(4b) joint: own revenue", None]}
for lab, keys in rowsT5.items():
    for side, sym in [("pos", "⁺"), ("neg", "⁻")]:
        name = lab.replace("⁺", sym)
        cs, ss = [], []
        for k in keys:
            if k is None:
                cs.append(""); ss.append("")
            else:
                c, s_ = coef(m[k][f"b_{side}"], m[k][f"se_{side}"])
                cs.append(c); ss.append(s_)
        T5.append(f"| {name} | " + " | ".join(cs) + " |")
        T5.append("| | " + " | ".join(ss) + " |")
T5.append("| Wald *p*, GDP β⁺ = β⁻ | " + " | ".join(
    f"{m[k].wald_p:.3f}" if k else "" for k in rowsT5["Δln GDP⁺"]) + " |")
T5.append("| Wald *p*, own revenue β⁺ = β⁻ | " + " | ".join(
    f"{m[k].wald_p:.3f}" if k else "" for k in rowsT5["Δln own revenue⁺"]) + " |")
T5.append("| County FE | No | Yes | Yes | Yes | Yes |")
T5.append("| Year FE | Yes | Yes | Yes | Yes | Yes |")
T5.append("| *N* (counties) | " + " | ".join(f"{int(m[k].n)} ({int(m[k].counties)})" for k in
                                         ["(1) Exp on GDP, year FE", "(2) Exp on GDP, county+year FE", "(3) Exp on own revenue, county+year FE", "(4a) joint: GDP", "(5) Own revenue on GDP, county+year FE"]) + " |")
T5.append("| *R*² | " + " | ".join(f"{m[k].r2:.2f}" for k in
                                 ["(1) Exp on GDP, year FE", "(2) Exp on GDP, county+year FE", "(3) Exp on own revenue, county+year FE", "(4a) joint: GDP", "(5) Own revenue on GDP, county+year FE"]) + " |")
T5 = "\n".join(T5)

T6 = ["| Sample / treatment | Equation | β⁺ (s.e.) | β⁻ (s.e.) | Wald *p* | *N* |", "|:------------------|:------------------|:----------:|:----------:|-----:|----:|"]
for _, r in rob.iterrows():
    eq, smp = r.model.split(" | ")
    eq = {"Exp on GDP": "Expenditure ← GDP", "Exp on own revenue": "Expenditure ← own revenue",
          "Own revenue on GDP": "Own revenue ← GDP", "Exp per capita on GDP": "Expenditure p.c. ← GDP"}[eq]
    c1, s1 = coef(r.b_pos, r.se_pos); c2, s2 = coef(r.b_neg, r.se_neg)
    T6.append(f"| {smp} | {eq} | {c1} {s1} | {c2} {s2} | {r.wald_p:.3f} | {int(r.n)} |")
T6 = "\n".join(T6)

TA1 = ["| County | Year | Variable | Reported value (10,000 yuan) | Rule |", "|:--|--:|:--|--:|:--|"]
CN_EN = {"当雄县": "Damxung", "仁布县": "Rinbung", "定结县": "Dinggyê", "扎囊县": "Chanang", "贡嘎县": "Gonggar",
         "洛扎县": "Lhozhag", "札达县": "Zanda", "改则县": "Gêrzê", "噶尔县": "Gar", "巴宜区": "Bayi"}
for _, r in clog.iterrows():
    TA1.append(f"| {CN_EN.get(r.county, r.county)} | {r.year} | {'own revenue' if r.variable == 'rev' else 'expenditure'} | {r.value:,.0f} | {r.rule} |")
TA1 = "\n".join(TA1)

TB1 = ["| Group | Equation | β⁺ (s.e.) | β⁻ (s.e.) | Wald *p* | *N* (counties) |", "|:---------------|:------------------|:----------:|:----------:|-----:|------:|"]
for _, r in het.iterrows():
    eq, grp = r.model.split(" | ")
    eq = {"Exp on GDP": "Expenditure ← GDP", "Exp on own revenue": "Expenditure ← own revenue"}[eq]
    c1, s1 = coef(r.b_pos, r.se_pos); c2, s2 = coef(r.b_neg, r.se_neg)
    TB1.append(f"| {grp.capitalize()} | {eq} | {c1} {s1} | {c2} {s2} | {r.wald_p:.3f} | {int(r.n)} ({int(r.counties)}) |")
TB1 = "\n".join(TB1)

V.update(T1=T1, T2=T2, T3=T3, T4=T4, T5=T5, T6=T6, TA1=TA1, TB1=TB1)

TEMPLATE = open(os.path.join(HERE, "manuscript_template.md"), encoding="utf-8").read()
md = TEMPLATE
for k, v in V.items():
    md = md.replace(f"<<{k}>>", str(v))
assert "<<" not in md, md[md.index("<<"):md.index("<<") + 40]
open(os.path.join(SUB, "Manuscript_anonymised.md"), "w", encoding="utf-8").write(md)


# -------------------------------------------------------------- docx export
def reference_doc(path):
    subprocess.run(["pandoc", "-o", path, "--print-default-data-file", "reference.docx"], check=True)
    d = Document(path)
    for st in d.styles:
        try:
            st.font.name = "Times New Roman"
            st.font.color.rgb = None
        except Exception:
            pass
    for name in ["Normal", "Body Text", "First Paragraph", "Compact", "Abstract", "Bibliography"]:
        try:
            st = d.styles[name]
        except KeyError:
            continue
        st.font.size = Pt(12)
        st.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    for name, size in [("Title", 16), ("Heading 1", 13), ("Heading 2", 12), ("Heading 3", 12)]:
        try:
            d.styles[name].font.size = Pt(size)
            d.styles[name].font.bold = True
        except KeyError:
            pass
    d.save(path)


REF = os.path.join(SUB, "_reference.docx")
reference_doc(REF)


def to_docx(md_text, name):
    src = os.path.join(SUB, name + ".md")
    open(src, "w", encoding="utf-8").write(md_text)
    subprocess.run(["pandoc", src, "-f", "markdown", "-o", os.path.join(SUB, name + ".docx"),
                    f"--reference-doc={REF}", f"--resource-path={OUT}"], check=True)


to_docx(md, "Manuscript_anonymised")
_d = Document(os.path.join(SUB, "Manuscript_anonymised.docx"))
for t in _d.tables:
    t.autofit = True
    for row in t.rows:
        for cell in row.cells:
            for par in cell.paragraphs:
                par.paragraph_format.line_spacing = 1.0
                for run in par.runs:
                    run.font.size = Pt(10)
_d.save(os.path.join(SUB, "Manuscript_anonymised.docx"))
for f in ["Title_page", "Highlights", "Cover_letter"]:
    txt = open(os.path.join(HERE, f + "_template.md"), encoding="utf-8").read()
    for k, v in V.items():
        txt = txt.replace(f"<<{k}>>", str(v))
    to_docx(txt, f)
for i in (1, 2, 3):
    shutil.copy(os.path.join(OUT, f"Figure_{i}.png"), os.path.join(SUB, f"Figure_{i}.png"))
os.remove(REF)

# supplementary data: cleaned panel + log + code pointer
with pd.ExcelWriter(os.path.join(SUB, "Supplementary_data.xlsx")) as xw:
    cols = ["code", "pref", "county_cn", "year", "gdp", "pop", "rev", "exp", "level_shift"]
    pd.read_csv(os.path.join(OUT, "panel_clean.csv"))[cols].rename(columns={
        "code": "county_code", "pref": "prefecture", "county_cn": "county", "gdp": "GDP_10k_yuan",
        "pop": "registered_pop_10k", "rev": "own_revenue_10k_yuan", "exp": "expenditure_10k_yuan",
        "level_shift": "GDP_rebased_flag"}).to_excel(xw, sheet_name="county_panel_clean", index=False)
    clog.assign(county_en=clog.county.map(CN_EN)).to_excel(xw, sheet_name="cleaning_log", index=False)
    conc.reset_index().to_excel(xw, sheet_name="output_concentration_74", index=False)
print("written:", sorted(os.listdir(SUB)))
