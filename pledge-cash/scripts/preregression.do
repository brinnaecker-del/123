* =====================================================================
* 预回归（Stata 版）：读 build_panel.py 生成的 panel.csv
* 需要：ssc install reghdfe ; ssc install ftools ; ssc install estout ; ssc install coefplot
* 与 preregression.py 的设定一一对应，两边结果应当一致
* =====================================================================
clear all
set more off
cd "`c(pwd)'"
import delimited "../data_clean/panel.csv", encoding(utf-8) stringcols(1 3) case(lower) clear

destring stkcd, gen(id)
xtset id year

global X "size lev roa growth tobinq cf cfvol nwc age top1"

* ---------- 描述性统计 ----------
tabstat cash pledge pledge_dum sa soe $X, s(n mean sd min p50 max) c(s) format(%9.4f)
tabstat pledge_dum pledge cash, by(year) s(mean) format(%9.3f)

* ---------- 基准回归（H1a／H1b） ----------
eststo clear
eststo m1: reghdfe cash pledge,               absorb(id year) vce(cluster id)
eststo m2: reghdfe cash pledge $X,            absorb(id year) vce(cluster id)
eststo m3: reghdfe cash pledge_dum $X,        absorb(id year) vce(cluster id)
eststo m4: reghdfe cash L.pledge $X,          absorb(id year) vce(cluster id)
gen ind1 = substr(ind, 1, 1)
egen indyear = group(ind1 year)
eststo m5: reghdfe cash pledge $X,            absorb(id indyear) vce(cluster id)
eststo m6: reghdfe cash2 pledge $X,           absorb(id year) vce(cluster id)
esttab m1 m2 m3 m4 m5 m6, b(%9.4f) se(%9.4f) star(* 0.1 ** 0.05 *** 0.01) ///
    keep(pledge pledge_dum L.pledge) r2 ar2 scalars(N) compress

* ---------- H3：滞后一期融资约束分组 ----------
gen L_sa = L.sa
bys year: egen med_Lsa = median(L_sa)
gen highfc = L_sa > med_Lsa if !missing(L_sa)
qui sum pledge
gen pledge_c = pledge - r(mean)
reghdfe cash c.pledge_c##i.highfc $X, absorb(id year) vce(cluster id)

* ---------- H4：产权性质分组 + 组间差异 ----------
reghdfe cash pledge $X if soe == 0, absorb(id year) vce(cluster id)
reghdfe cash pledge $X if soe == 1, absorb(id year) vce(cluster id)
tabstat pledge_dum pledge, by(soe) s(n mean sd)
* 组间系数差异：用交互项版本检验（等价于允许两组系数不同）
reghdfe cash c.pledge##i.soe $X, absorb(id year) vce(cluster id)

* SA 方向核验：两者都应为负
corr sa size age

* ---------- 2018 新规处理强度 DID ----------
bys id: egen pledgepre = mean(cond(inlist(year, 2016, 2017), pledge, .))
gen post = year >= 2018
gen did  = pledgepre * post
preserve
keep if year >= 2012 & listyear < 2016 & !missing(pledgepre)
reghdfe cash did $X,                      absorb(id year) vce(cluster id)
reghdfe cash did $X if year != 2018,      absorb(id year) vce(cluster id)
reghdfe cash did $X,                      absorb(id indyear) vce(cluster id)
reghdfe pledge did $X,                    absorb(id year) vce(cluster id)   // “第一阶段”
* 事件研究，基期 2017
forvalues y = 2012/2025 {
    if `y' != 2017 gen ev`y' = pledgepre * (year == `y')
}
reghdfe cash ev2012-ev2016 ev2018-ev2025 $X, absorb(id year) vce(cluster id)
coefplot, keep(ev*) vertical yline(0) xline(5.5) title("PledgePre × 年份（基期2017）")
restore
