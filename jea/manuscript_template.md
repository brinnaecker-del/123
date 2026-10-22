---
title: "Asymmetric fiscal capacity and insulated spending in a transfer-dependent periphery: County-level evidence from Tibet, 2016–2024"
---

# Abstract {.unnumbered}

This paper documents three asymmetries in the public finances and output of a transfer-dependent periphery, using a panel of 73 county-level units in the Tibet Autonomous Region of China over 2016–2024. First, the distribution of fiscal capacity is far more unequal than the distribution of spending: the population-weighted Gini coefficient of own revenue per capita lies between <<gini_rev_lo>> and <<gini_rev_hi>>, against <<gini_gdp_lo>>–<<gini_gdp_hi>> for output and <<gini_exp_lo>>–<<gini_exp_hi>> for expenditure. Own revenue finances a median of <<ssr_med_lo>>–<<ssr_med_hi>>% of county spending, and the elasticity of own revenue with respect to output (<<el_rev>>) is more than three times that of expenditure (<<el_exp>>). Second, the strength of equalisation itself was uneven over time: the share of revenue inequality removed by the spending distribution rose from <<eq16>> in 2016 to <<eq_mid_lo>>–<<eq_mid_hi>> in 2018–2022 and fell back to <<eq24>> by 2024. Third, the cyclical behaviour of the two sides of the budget differs. Own revenue rises with output growth (elasticity <<rp>>) but does not fall when output contracts; equality of the two responses is rejected (*p* = <<rwp>>). Expenditure, in contrast, is insulated from both increases and decreases in local output and revenue. Output per capita shows β-convergence of about <<speed>>% per year but no σ-convergence. The findings suggest that transfers in such regions act less as an equaliser of growth than as insurance for the level of public spending, while the burden of downturns falls asymmetrically on local revenue collection.

**Keywords:** Fiscal asymmetry; Intergovernmental transfers; Fiscal equalisation; Regional inequality; Convergence; Tibet

**JEL classification:** H71; H77; R11; O18

# 1. Introduction

Large federations and unitary states alike sustain peripheral regions whose own fiscal base is a small fraction of what they spend. In these regions the relationship between the local economy and the local public sector is shaped less by local preferences and tax bases than by the rules of the intergovernmental system. The resulting asymmetries are of two kinds. The first is distributional: fiscal capacity is concentrated in a few places, while spending is spread more evenly because transfers fill the gap. The second is dynamic: the two sides of the budget need not respond in the same way when the local economy expands as when it contracts. Both kinds of asymmetry bear on central questions about intergovernmental finance, including whether transfers equalise opportunities or merely spending levels, and who absorbs the cost of local downturns.

The empirical literature on asymmetric fiscal responses has focused mainly on spending. Gamkhar and Oates (1996) and Stine (1994) asked whether local governments cut spending when grants fall by the same amount as they raise it when grants rise, building on the flypaper puzzle reviewed by Hines and Thaler (1995). For China, a large literature studies the equalising power of intergovernmental transfers across provinces and counties (Tsui, 2005; Huang & Chen, 2012; Yang et al., 2024) and documents the pressure that higher levels of government place on local revenue collection (Lü & Landry, 2014; Chen, 2017). What is less well documented is how these features combine in a region where transfers dominate local budgets, and whether revenue and spending respond symmetrically to positive and negative output shocks.

This paper studies that combination in the Tibet Autonomous Region (hereafter Tibet), which offers an extreme case. Tibet is large, sparsely populated and high-altitude, and its counties combine very low own-revenue capacity with spending financed overwhelmingly by transfers. Fischer (2014) argues that Tibet's growth has been driven by external subsidy and investment rather than by its local economy. I use a county-level panel compiled from official statistical sources covering 73 of the region's 74 county-level units for 2016–2024, with data on gross domestic product (GDP), registered population, local general budget revenue and local general budget expenditure. The period includes the COVID-19 disruption of 2020–2022 and the recovery that followed.

The analysis proceeds in four steps. I first measure the inequality of output, own revenue and expenditure per capita with population-weighted Gini and Theil indices. I then decompose these indices into between- and within-prefecture components. Second, I estimate cross-sectional and within-county elasticities of revenue and expenditure with respect to output. These elasticities summarise how far the transfer system decouples spending from the local economy. Third, I test for β- and σ-convergence in output per capita. Fourth, I estimate first-difference models in which positive and negative changes in output and own revenue enter separately, and I test whether county revenue and expenditure respond symmetrically.

The paper makes three contributions. First, it quantifies the gap between the distribution of fiscal capacity and the distribution of public spending at the county level in a transfer-dependent region, and it shows that the degree of equalisation is not constant. Equalisation was stronger during 2018–2022 than either before or after. Second, it shows that the two sides of the county budget behave asymmetrically over the cycle. Spending is insulated from local output in both directions, so there is no evidence of the grant asymmetries reported for US local governments. Own revenue, however, follows output upwards but not downwards. Third, it shows that output per capita in Tibet's counties exhibits β-convergence without σ-convergence. The fiscal system has therefore stabilised spending without compressing the dispersion of output.

The remainder of the paper is organised as follows. Section 2 describes the institutional setting and related literature. Section 3 presents the data, the inequality measures and the econometric specifications. Section 4 reports the results and robustness checks. Section 5 discusses interpretation, policy implications and limitations, and Section 6 concludes.

# 2. Institutional background and related literature

## 2.1. County public finance in Tibet

China's 1994 tax-sharing reform assigned the most buoyant taxes largely to the central government and left subnational governments with spending responsibilities that exceed their own revenue. The gap is closed by a combination of tax rebates, general (equalisation) transfers and earmarked transfers (Shen et al., 2012). Below the provincial level, revenue assignments and transfer rules are set by each province, and counties are the main providers of basic public services. Tsui (2005) shows that the resulting system left large county-level disparities in fiscal capacity. Huang and Chen (2012) find that the equalising effect of transfers across provinces has been limited.

Tibet is the most transfer-dependent provincial-level unit in China. Its 74 county-level units are grouped into seven prefecture-level units: Lhasa, Shigatse, Chamdo, Nyingchi, Shannan, Nagqu and Ngari. They differ greatly in population density, altitude, access to markets and economic structure. Lhasa and Nyingchi have the largest service and tourism sectors. Nagqu and Ngari are dominated by pastoralism and have very low population density. Because own revenue is small, most of a county's budget is determined by allocations from higher levels. The distinction that matters for this paper is between *own revenue*, which reflects the local tax base and collection effort, and *expenditure*, which reflects both own revenue and transfers.

## 2.2. Asymmetries in subnational public finance

Three strands of work motivate the analysis. The first concerns the distributional asymmetry between fiscal capacity and fiscal need. In the fiscal federalism tradition, transfers are justified partly by the mismatch between where taxable capacity is located and where public services must be provided (Oates, 1999). A simple way to describe this mismatch is to compare the inequality of own revenue with that of expenditure. The difference indicates how much of the capacity gap the transfer system closes.

The second strand concerns dynamic asymmetry. Gamkhar and Oates (1996) study US state and local governments and find that spending responds differently to increases and decreases in federal grants. Stine (1994) finds an asymmetric response of Pennsylvania county governments during a period of grant retrenchment. A related question concerns local revenue. Chinese local officials face strong incentives to meet revenue targets (Lü & Landry, 2014). When revenue sources shrink, counties can offset the loss through tighter enforcement (Chen, 2017). These incentives imply that local revenue may not fall in proportion to output when output contracts. Notably, Lü and Landry (2014) report that the competition–extraction relationship they document does not hold in politically sensitive ethnic minority regions. That makes the behaviour of revenue in Tibet an open empirical question.

The third strand concerns regional convergence and the decomposition of regional inequality. Barro and Sala-i-Martin (1992) formalise β-convergence. Quah (1993) and Friedman (1992) show that a negative relation between initial level and subsequent growth does not imply a decline in dispersion, so σ-convergence must be examined separately. Additively decomposable inequality indices (Shorrocks, 1980) allow inequality to be split into between-group and within-group components. Kanbur and Zhang (2005) and Akita (2003) apply such decompositions to Chinese regional inequality. I follow these approaches but apply them to fiscal as well as output variables, so that the inequality of capacity, spending and output can be compared on the same footing.

# 3. Data and methods

## 3.1. Data

The data are an annual panel of the county-level units of Tibet for 2016–2024. They were compiled from county and prefecture statistical bulletins and official statistical compilations. The variables are GDP at current prices, year-end registered (*hukou*) population, local general budget revenue (own revenue) and local general budget expenditure. Chengguan District, the urban core of Lhasa, has GDP data but no population or fiscal data. It is therefore excluded from all per-capita and fiscal analyses, leaving 73 counties and <<n_obs>> county-year observations. Chengguan's share of the GDP of all 74 units fell from <<cg16>>% in 2016 to <<cg24>>% in 2024, so excluding it removes the single largest urban economy and makes the estimates conservative with respect to the core–periphery gap.

Two features of the data shape the analysis. First, county own revenue is small and volatile, and the raw series contains a few values that are clearly misreported. In several counties in 2018, for example, the reported revenue nearly equals the expenditure figure for the same year and is more than ten times the values in adjacent years. I apply three mechanical rules, fixed before estimation, to identify such values and set them to missing. A value is treated as a reversing spike if it differs by a factor of more than four from both adjacent years in the same direction. Own revenue is treated as a duplicated expenditure figure if it is at least 80% of expenditure in a county whose median self-sufficiency is below 20%. Expenditure is treated as misreported if it falls below own revenue. These rules affect <<n_clean>> of the 1,314 fiscal observations and are listed in Appendix A (Table A.1). All main results are re-estimated on the uncleaned data in Section 4.5. Second, the GDP series of two counties (Gar in 2020 and Seni in 2019) show level shifts consistent with statistical re-basing rather than real growth. I retain them in the baseline and exclude them in robustness checks.

Per-capita variables use registered population, which is the only population measure available for all counties throughout the period. Registered population is rounded to the nearest thousand persons in the source, which introduces measurement error in per-capita levels for the smallest counties. This error is absorbed by county fixed effects in the within-county specifications. All monetary variables are in current yuan. Year fixed effects absorb common price movements in all regressions.

## 3.2. Inequality measures

For a variable $x_i$ (per capita) in county $i$ with population share $p_i$ and population-weighted mean $\mu$, I compute the Gini coefficient and two members of the generalised entropy class, the Theil *T* index and the mean log deviation (Theil *L*):

$$T = \sum_i p_i \frac{x_i}{\mu} \ln\frac{x_i}{\mu}, \qquad L = \sum_i p_i \ln\frac{\mu}{x_i}. \qquad (1)$$

Both indices are additively decomposable across the seven prefectures $g$ (Shorrocks, 1980):

$$T = \sum_g s_g T_g + T_B, \qquad (2)$$

where $s_g$ is prefecture $g$'s share of the aggregate, $T_g$ is inequality among counties within $g$ and $T_B$ is the Theil index computed on prefecture means. I report the between-prefecture share $T_B/T$.

To summarise how much of the inequality in fiscal capacity is removed by the spending distribution, I define the equalisation ratio

$$E_t = 1 - G_t^{\text{exp}} / G_t^{\text{rev}}, \qquad (3)$$

where $G_t^{\text{exp}}$ and $G_t^{\text{rev}}$ are the Gini coefficients of expenditure and own revenue per capita in year $t$, computed on the common sample of counties that report both. $E_t = 0$ means spending is as unequal as own revenue, as it would be with no transfers. $E_t = 1$ means spending is perfectly equal. The ratio is descriptive: it does not separate transfers from differences in spending needs, which are themselves unequally distributed across a region as heterogeneous as Tibet.

## 3.3. Econometric specifications

**Fiscal gradients.** The decoupling of revenue and expenditure from the local economy is summarised by the elasticities $\gamma$ in

$$\ln f_{it} = \alpha + \gamma \ln y_{it} + \lambda_t + \eta_i + \varepsilon_{it}, \qquad (4)$$

where $f_{it}$ is own revenue or expenditure per capita and $y_{it}$ is GDP per capita. I estimate Eq. (4) with year effects $\lambda_t$ only (a pooled cross-county gradient), with prefecture effects added, and with county effects $\eta_i$ (a within-county elasticity). I also estimate the elasticity of expenditure with respect to own revenue.

**Convergence.** Absolute and conditional β-convergence in GDP per capita are estimated from

$$\frac{1}{8}\ln\frac{y_{i,2024}}{y_{i,2016}} = a + \beta \ln y_{i,2016} + \delta_g + u_i, \qquad (5)$$

with and without prefecture effects $\delta_g$. The implied speed is $\lambda = -\ln(1+8\beta)/8$, and the half-life is $\ln 2/\lambda$ (Barro & Sala-i-Martin, 1992). I also report annual panel versions. The specification with county effects is subject to the bias described by Nickell (1981) in short panels and is shown only for completeness. σ-convergence is assessed from the standard deviation of log GDP per capita and from the Gini and Theil indices.

**Asymmetric adjustment.** To test whether county budgets respond symmetrically to positive and negative shocks, I split the log change of a driver $z$ (GDP or own revenue) into its positive and negative parts, $\Delta z^{+}_{it} = \max(\Delta \ln z_{it}, 0)$ and $\Delta z^{-}_{it} = \min(\Delta \ln z_{it}, 0)$, and estimate

$$\Delta \ln f_{it} = \beta^{+}\Delta z^{+}_{it} + \beta^{-}\Delta z^{-}_{it} + \lambda_t + \eta_i + \varepsilon_{it}. \qquad (6)$$

Here $f$ is total expenditure or own revenue. Symmetry is the hypothesis $\beta^{+} = \beta^{-}$. Because the regressors are log changes, $\beta^{-}$ measures the percentage change in $f$ per one per cent *decline* in $z$. A positive $\beta^{-}$ means $f$ falls when $z$ falls. Year effects remove region-wide shocks, including the pandemic years and changes in the regional transfer envelope. County effects allow for county-specific trends in the level of $f$. Standard errors in Eqs. (4) and (6) are clustered by county (Cameron & Miller, 2015). Eq. (6) is a reduced-form description of co-movement, not a causal model of fiscal behaviour. In particular, own revenue can affect measured GDP through the public-sector component of value added. I return to this point in Section 5.

# 4. Results

## 4.1. The asymmetry between fiscal capacity and spending

Table 1 summarises the seven prefectures. Own revenue covers <<ssr_pool>>% of the expenditure of the 73 counties taken together, and the median county finances only <<ssr_med_lo>>–<<ssr_med_hi>>% of its spending from own revenue, depending on the year. In each year, between <<share10_lo>>% and <<share10_hi>>% of counties finance less than 10% of their spending from own revenue. Self-sufficiency ranges from <<ssr_lhasa>>% in Lhasa's counties to <<ssr_nagqu>>% in Nagqu's. Spending per capita bears little relation to output per capita. In 2024 the counties of Ngari spent <<exp_ngari>> yuan per registered resident and those of Chamdo <<exp_chamdo>> yuan, although Ngari's output per capita is less than twice Chamdo's. This pattern is consistent with large differences in the cost of service provision across a sparsely populated, high-altitude territory.

*Table 1. Fiscal self-sufficiency and output by prefecture (73 counties).*

<<T1>>

*Notes:* Pop. 2024 is registered population in 2024 (10,000 persons). GDP p.c. and Exp. p.c. are GDP and expenditure per registered resident (yuan). SSR is the self-sufficiency ratio. Prefecture values aggregate the member counties in the sample (Chengguan District excluded). Self-sufficiency is own (local general budget) revenue divided by local general budget expenditure. "Pooled" is the ratio of summed revenue to summed expenditure over 2016–2024 for county-years in which both are observed. Per-capita values use registered population. Current prices.

Table 2 and Fig. 1 compare the inequality of the three per-capita variables. Own revenue is the most unequally distributed, with a Gini coefficient of <<gini_rev_lo>>–<<gini_rev_hi>>. Output follows at <<gini_gdp_lo>>–<<gini_gdp_hi>>, and expenditure is the least unequal at <<gini_exp_lo>>–<<gini_exp_hi>>. Spending is therefore more equally distributed than the output that underlies it, which is the most direct evidence that the transfer system closes most of the capacity gap. The decomposition shows that the asymmetry has a strong spatial dimension. Between <<bsrev_lo>>% and <<bsrev_hi>>% of revenue inequality (Theil *T*) lies between prefectures, mainly reflecting the concentration of the tax base in Lhasa's counties. The between-prefecture share of output inequality is lower and fell from <<bs16>>% in 2016 to <<bs24>>% in 2024. Disparities in output per capita have thus become relatively more a matter of differences among counties within the same prefecture.

*Table 2. Inequality of output, own revenue and expenditure per capita, 2016–2024.*

<<T2>>

*Notes:* Population-weighted indices of GDP (GDP), own revenue (Rev) and expenditure (Exp) per capita. *E* is the equalisation ratio of Eq. (3); *T* is the Theil *T* index; *B* is the between-prefecture share of *T* (Eq. 2). Gini coefficients and *E* are computed on the common sample of counties that report all three variables in a given year (*N*). Theil *T* and its decomposition by seven prefectures (Eq. 2) use all available counties for each variable. The 2016 and 2018 common samples are smaller because several 2018 revenue values are set to missing by the cleaning rules (Appendix A).

![Fig. 1. Population-weighted Gini coefficients (panel a) and the between-prefecture share of the Theil *T* index (panel b) for GDP, own revenue and expenditure per capita across 73 counties of Tibet, 2016–2024. The 2016 and 2018 values for own revenue and expenditure are based on slightly smaller samples; see Table 2.](Figure_1.png){width=100%}

The equalisation ratio in Eq. (3) moved in two phases. It rose from <<eq16>> in 2016 to <<eq_mid_lo>>–<<eq_mid_hi>> in 2018–2022, as the Gini coefficient of expenditure fell while that of own revenue rose. It then declined to <<eq24>> in 2024, because the expenditure Gini rose from <<gexp22>> in 2022 to <<gexp24>> in 2024 while revenue inequality changed little. The pattern is asymmetric around the pandemic. Spending was most compressed during the years of disruption, when region-wide support was largest, and became more dispersed in the recovery. One plausible reading is that the post-2022 expansion in spending was allocated in proportion to county-specific projects rather than by the formula-like equalisation that dominated earlier. Without data on transfer composition, however, this cannot be tested directly.

## 4.2. Fiscal gradients

Table 3 reports the elasticities of Eq. (4), and Fig. 2(a) shows the 2024 cross-section. Across counties, own revenue per capita rises more than proportionally with output per capita (elasticity <<el_rev>> with year effects). Expenditure per capita rises with an elasticity of only <<el_exp>>. The difference between the two slopes measures the extent to which transfers flatten the spending gradient. Holding constant the location of a county within a prefecture lowers both elasticities, but the gap remains. Within counties over time, the revenue elasticity falls to <<el_rev_fe>> and the expenditure elasticity is <<el_exp_fe>>. The elasticity of expenditure with respect to own revenue is <<el_er_fe>> within counties. Because expenditure is many times own revenue, this small elasticity corresponds to a large marginal effect: evaluated at the pooled and median ratios of expenditure to own revenue, it implies roughly <<mpe_lo>>–<<mpe_hi>> yuan of additional spending per additional yuan of own revenue. Transfers therefore do not offset increases in local revenue. If anything, the two move together, although this within-county association may also reflect common shocks, such as project funding that raises both spending and local revenue.

*Table 3. Elasticities of own revenue and expenditure with respect to output.*

<<T3>>

*Notes:* Estimates of Eq. (4). Standard errors clustered by county in parentheses. \*\*\* *p* < 0.01, \*\* *p* < 0.05, \* *p* < 0.1. All specifications include year fixed effects.

![Fig. 2. Panel (a): log own revenue and log expenditure per capita against log GDP per capita across counties in 2024, with OLS fitted lines. Panel (b): average annual growth of GDP per capita over 2016–2024 against its 2016 level, with the OLS fitted line; hollow markers identify the two counties with re-based GDP series.](Figure_2.png){width=100%}

## 4.3. Output: β-convergence without σ-convergence

Table 4 reports the convergence estimates. The cross-sectional coefficient on initial log GDP per capita is <<beta>> (standard error <<beta_se>>), which implies a convergence speed of <<speed>>% per year and a half-life of about <<hl>> years. Adding prefecture effects lowers the coefficient slightly to <<beta_c>> (speed <<speed_c>>%). Excluding the two counties with re-based GDP gives <<beta_x>> (speed <<speed_x>>%). The annual pooled panel gives similar speeds. The large coefficient in the panel with county effects (marked †) reflects Nickell bias and strong mean reversion of transitory shocks, so it should not be read as a convergence speed.

*Table 4. β-convergence of GDP per capita across counties.*

<<T4>>

*Notes:* λ is the implied annual speed of convergence. Cross-section: Eq. (5), average annual log growth 2016–2024 on log GDP per capita in 2016, with heteroskedasticity-robust standard errors. Annual panel: annual log growth on lagged log GDP per capita, with standard errors clustered by county. † Subject to the bias described by Nickell (1981); not interpretable as a convergence speed. \*\*\* *p* < 0.01, \*\* *p* < 0.05, \* *p* < 0.1.

β-convergence is not matched by σ-convergence. The standard deviation of log GDP per capita was <<sd16>> in 2016, rose to <<sd20>> in 2020 and returned to <<sd24>> in 2024. The population-weighted Gini moved from <<gg16>> to <<gg24>> (Table 2). Poorer counties grew faster on average, but new county-specific shocks offset the reduction in dispersion that mean reversion alone would produce. This is the configuration emphasised by Quah (1993) and Friedman (1992). In fiscal terms, a transfer system that stabilises spending levels (Section 4.1) has coexisted with an output distribution whose dispersion has not narrowed.

## 4.4. Asymmetric cyclical adjustment

Table 5 and Fig. 3 report Eq. (6). Over the sample there are <<n_changes>> annual changes in county GDP, of which <<n_contr_all>> are declines, clustered in 2019, 2022 and 2024. Columns (1)–(4) show that county expenditure is insulated from local fluctuations. With county and year effects, the elasticity of expenditure with respect to output increases is <<ep>>, and the elasticity with respect to output decreases is <<en>>. Neither is significantly different from zero, and symmetry is not rejected (*p* = <<ewp>>). The same holds for own revenue as the driver (<<erp>> and <<ern>>, *p* = <<erwp>>). There is therefore no sign of the spending asymmetry found for US local governments, either a stronger response to increases or a ratchet that prevents cuts. County spending in Tibet appears to be set largely independently of the local economy, and region-wide year effects explain most of its variation.

*Table 5. Asymmetric responses of expenditure and own revenue to changes in output and own revenue.*

<<T5>>

*Notes:* Estimates of Eq. (6). The dependent variable is the annual change in log total expenditure (columns 1–4, "Exp.") or log own revenue (column 5). Δln GDP⁺ and Δln GDP⁻ are the positive and negative parts of the annual change in log GDP; Δln own revenue⁺ and Δln own revenue⁻ are defined in the same way. Standard errors clustered by county in parentheses. \*\*\* *p* < 0.01, \*\* *p* < 0.05, \* *p* < 0.1.

![Fig. 3. Point estimates and 95% confidence intervals of the responses to increases (Δ > 0) and decreases (Δ < 0) in the driver variable, from Table 5, columns (2), (3) and (5). All models include county and year fixed effects; standard errors are clustered by county.](Figure_3.png){width=70%}

Own revenue behaves very differently (column 5). When output rises, own revenue rises with an elasticity of <<rp>> (standard error <<rp_se>>). When output falls, the coefficient is <<rn>> (standard error <<rn_se>>). The negative sign means that, in the <<n_contr>> county-years with an output decline and observed revenue, own revenue tended to *rise* rather than fall. Symmetry is rejected at *p* = <<rwp>>. Local revenue is thus procyclical in expansions but not in contractions. A one-per-cent fall in output is associated with no loss of revenue, and if anything with additional collection.

Because the negative-change coefficient rests on a small number of contraction episodes, I check whether any single episode drives it. Dropping each contraction observation in turn yields coefficients between <<jk_lo>> and <<jk_hi>>, and the largest *p*-value for the symmetry test across these regressions is <<jk_p>> (Appendix B). The asymmetry is therefore not the product of one county-year. Its magnitude should nevertheless be read with caution given the small number of contractions.

## 4.5. Robustness

Table 6 re-estimates the asymmetry models under alternative samples and treatments. These include excluding the two counties with re-based GDP, excluding Lhasa prefecture, excluding the pandemic years 2020–2022, winsorising all changes at the 2.5th and 97.5th percentiles, using the uncleaned raw data, and using expenditure per capita instead of total expenditure. Across all specifications, the coefficient on output declines in the revenue equation lies between <<rob_rn_lo>> and <<rob_rn_hi>>, and symmetry is rejected at *p* ≤ <<rob_p_max>>. The insulation of expenditure is equally robust: no specification rejects symmetry for expenditure at the 5% level (smallest *p* = <<exp_rob_pmin>>). Splitting the sample by counties' average self-sufficiency (Appendix B, Table B.1) yields the same conclusion for expenditure in both groups. Excluding the two re-based counties leaves the level of output inequality almost unchanged but moderates the decline in its between-prefecture share, which then falls from <<bsx16>>% in 2016 to <<bsx24>>% in 2024; the 2019 drop in Table 2 is largely due to the re-basing of Seni's GDP.

*Table 6. Robustness of the asymmetric-adjustment results.*

<<T6>>

*Notes:* Each row is a separate estimate of Eq. (6) with county and year fixed effects. β⁺ and β⁻ are the coefficients on the positive and negative parts of the change in the driver (GDP or own revenue). Standard errors clustered by county in parentheses. \*\*\* *p* < 0.01, \*\* *p* < 0.05, \* *p* < 0.1.

# 5. Discussion

## 5.1. Interpretation

The three asymmetries fit together. The transfer system in Tibet decouples county spending from county output in levels (Section 4.2) and in changes (Section 4.4). It also compresses the distribution of spending well below that of fiscal capacity (Section 4.1). In this sense, transfers act as insurance for public spending. A county whose economy contracts does not experience a corresponding fall in its budget, and a county whose economy booms does not receive a proportional increase in spending. This insurance function is distinct from the equalisation of economic opportunities. The persistence of output dispersion (Section 4.3) shows that stabilising spending has not, over this period, narrowed the gaps in output between counties.

The asymmetry on the revenue side is consistent with the incentive structure described in the literature on Chinese local public finance. If county governments face revenue targets or are evaluated on revenue performance, a fall in the tax base calls for greater collection effort, a reallocation toward non-tax revenue, or a one-off asset sale (Lü & Landry, 2014; Chen, 2017). Any of these would sustain measured revenue when output falls. The result is notable because Lü and Landry (2014) find that the competitive extraction mechanism does not operate in ethnic minority regions in their 1999–2006 sample. The present evidence suggests that downward revenue rigidity nonetheless characterises Tibet's counties in the more recent period. Two alternative explanations deserve mention. First, some recorded GDP declines may reflect statistical revisions rather than real contractions, especially in 2019, when county accounts may have been affected by the revisions that followed the Fourth National Economic Census. Pure measurement error of this kind would bias the coefficient on output declines toward zero, so it cannot generate the negative estimate. It may, however, affect its magnitude. Second, own revenue partly funds public employment and investment that enter GDP, so the two series are jointly determined. This feedback runs in the direction of a positive co-movement and so also works against the asymmetry found.

The finding has an asymmetric-burden interpretation. In a downturn, the region-wide transfer system protects county spending, but the local share of the adjustment falls on the local tax base through steady or higher collection. If collection effort rises when local incomes fall, local revenue policy is procyclical in downturns, which is the opposite of what stabilisation would require.

## 5.2. Policy implications

Three implications follow, with the caution appropriate to descriptive evidence. First, transfer formulas in such regions could be evaluated on two criteria rather than one: equalisation of spending capacity and the stabilisation of local revenue effort. Allowing county revenue targets to adjust automatically to measured output, for example, would reduce the incentive to raise collection during contractions. Second, the decline in the equalisation ratio after 2022 deserves monitoring. If it reflects a shift toward project-based allocation, the distribution of spending may increasingly follow administrative capacity to prepare projects rather than need. Third, since output dispersion did not narrow despite heavy transfers, policies aimed at county economic convergence probably require instruments other than budget transfers, such as connective infrastructure, market access and human capital, whose effects the present data cannot evaluate.

## 5.3. Limitations

The analysis has several limitations. The fiscal data do not distinguish types of transfer, so the implied transfer (expenditure minus own revenue) combines formula-based equalisation with earmarked and project funds. The panel is short, and contractions are rare, which limits the precision of the negative-change estimates. Per-capita values use registered rather than resident population, and the urban core of Lhasa (Chengguan District) lacks population and fiscal data. Finally, the estimates describe co-movements and do not identify the causal effect of transfers on output or on revenue effort. Data on the composition of transfers and on tax versus non-tax revenue would allow the mechanisms proposed in Section 5.1 to be tested directly.

# 6. Conclusion

This paper has documented three asymmetries in the public finances of Tibet's counties over 2016–2024. Fiscal capacity is far more unequally distributed than public spending, and the degree to which spending inequality is compressed relative to capacity rose during 2018–2022 and fell afterwards. County spending is insulated from local output in both directions, whereas own revenue rises with output but does not fall when output falls. Output per capita shows β-convergence but no σ-convergence. Taken together, the evidence characterises transfers in a highly dependent periphery as insurance for spending levels rather than as an equaliser of growth, with the local side of downturn adjustment borne asymmetrically by revenue collection. The same diagnostic framework, which compares the inequality and cyclical behaviour of capacity, spending and output, can be applied to other transfer-dependent regions where the relationship between local economies and local budgets is shaped by intergovernmental rules.

# Declaration of generative AI and AI-assisted technologies in the manuscript preparation process {.unnumbered}

During the preparation of this work the author used Claude (Anthropic) in order to assist with data cleaning scripts, statistical computation, drafting and language editing. After using this tool, the author reviewed and edited the content as needed and takes full responsibility for the content of the published article.

# References {.unnumbered}

::: {#refs custom-style="Bibliography"}
Akita, T. (2003). Decomposing regional income inequality in China and Indonesia using two-stage nested Theil decomposition method. *The Annals of Regional Science, 37*(1), 55–77.

Barro, R. J., & Sala-i-Martin, X. (1992). Convergence. *Journal of Political Economy, 100*(2), 223–251.

Cameron, A. C., & Miller, D. L. (2015). A practitioner's guide to cluster-robust inference. *Journal of Human Resources, 50*(2), 317–372.

Chen, S. X. (2017). The effect of a fiscal squeeze on tax enforcement: Evidence from a natural experiment in China. *Journal of Public Economics, 147*, 62–76. https://doi.org/10.1016/j.jpubeco.2017.01.001

Fischer, A. M. (2014). *The disempowered development of Tibet in China: A study in the economics of marginalization*. Lexington Books.

Friedman, M. (1992). Do old fallacies ever die? *Journal of Economic Literature, 30*(4), 2129–2132.

Gamkhar, S., & Oates, W. E. (1996). Asymmetries in the response to increases and decreases in intergovernmental grants: Some empirical findings. *National Tax Journal, 49*(4), 501–512.

Hines, J. R., & Thaler, R. H. (1995). Anomalies: The flypaper effect. *Journal of Economic Perspectives, 9*(4), 217–226.

Huang, B., & Chen, K. (2012). Are intergovernmental transfers in China equalizing? *China Economic Review, 23*(3), 534–551. https://doi.org/10.1016/j.chieco.2012.01.001

Kanbur, R., & Zhang, X. (2005). Fifty years of regional inequality in China: A journey through central planning, reform, and openness. *Review of Development Economics, 9*(1), 87–106.

Lü, X., & Landry, P. F. (2014). Show me the money: Interjurisdiction political competition and fiscal extraction in China. *American Political Science Review, 108*(3), 706–722.

Nickell, S. (1981). Biases in dynamic models with fixed effects. *Econometrica, 49*(6), 1417–1426.

Oates, W. E. (1999). An essay on fiscal federalism. *Journal of Economic Literature, 37*(3), 1120–1149.

Quah, D. (1993). Galton's fallacy and tests of the convergence hypothesis. *The Scandinavian Journal of Economics, 95*(4), 427–443.

Shen, C., Jin, J., & Zou, H. (2012). Fiscal decentralization in China: History, impact, challenges and next steps. *Annals of Economics and Finance, 13*(1), 1–51.

Shorrocks, A. F. (1980). The class of additively decomposable inequality measures. *Econometrica, 48*(3), 613–625.

Stine, W. F. (1994). Is local government revenue response to federal aid symmetrical? Evidence from Pennsylvania county governments in an era of retrenchment. *National Tax Journal, 47*(4), 799–816.

Tsui, K. (2005). Local tax system, intergovernmental transfers and China's local fiscal disparities. *Journal of Comparative Economics, 33*(1), 173–196.

Yang, X., Barros, L., Matthews, K., & Meenagh, D. (2024). The dynamics of redistribution, inequality and growth across China's regions. *Journal of Policy Modeling, 46*(3), 613–637. https://doi.org/10.1016/j.jpolmod.2024.01.011
:::

# Appendix A. Data cleaning {.unnumbered}

The rules described in Section 3.1 were applied mechanically before estimation and are implemented in the replication code supplied as supplementary material. Table A.1 lists every value they set to missing. The 2018 revenue values for five counties are close to the same counties' 2018 expenditure and are roughly 20 to 40 times the same counties' own revenue in 2017 and 2019, which indicates that the expenditure figure was entered in the revenue column. The cleaned panel, the cleaning log and the GDP of the 74 county-level units (including Chengguan District) are provided in the supplementary data file.

*Table A.1. Observations set to missing by the cleaning rules.*

<<TA1>>

*Notes:* R2 spike: the value differs by a factor of more than four from both adjacent years in the same direction (for end years, from the adjacent year and the county median). R3 mirror: own revenue is at least 80% of expenditure in a county whose median self-sufficiency is below 20%. R4: expenditure below own revenue.

# Appendix B. Additional results {.unnumbered}

*Table B.1. Expenditure responses by county self-sufficiency.*

<<TB1>>

*Notes:* Counties are split at the median of their average self-sufficiency ratio over 2016–2024. Each row is a separate estimate of Eq. (6) with county and year fixed effects. Standard errors clustered by county in parentheses. \*\*\* *p* < 0.01, \*\* *p* < 0.05, \* *p* < 0.1.

Leave-one-out check for the revenue equation (Table 5, column 5): re-estimating after dropping each of the <<n_contr>> contraction observations in turn gives coefficients on Δln GDP⁻ between <<jk_lo>> and <<jk_hi>>, with Wald *p*-values for β⁺ = β⁻ no larger than <<jk_p>>. The full set of estimates is included in the supplementary data.
