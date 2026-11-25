# Screened Relinquished Prospect Inventory and Pre-Registered Audit of 756 NCS Licences

**Bottom line.** Joining 738 unique Norwegian Continental Shelf relinquishment reports (5,325 prospects) against 536 active SODIR licences, the APA gross boundary, and 154 in-service surface host facilities (snapshot `2026-11-25`, reflecting 56 APA 2025 awards) identifies **242 APA-eligible open-acreage prospects (`Pg >= 0.20`, post-award assessed, undrilled, >=50% of the Norwegian slice outside active licences) holding 6.30 Bboe unrisked and 1.95 Bboe risked**. Since 2013, nearly one in five completed NCS wildcat parent wells (77 of 410, 18.8%) was drilled inside a relinquished prospect polygon, showing a near-field technical discovery penalty that survives licence clustering, quadrant clustering, and operator incumbency controls (`is_redrill x log1p(dist_km)` most conservative p = 0.0043; p = 0.0351 with incumbency), but is not detectable for material (`>= 3 MSm3`) or commercial (`2013 to 2021`) discoveries. Only two infrastructure-constrained oil prospects moved into realistic tie-back range of a new processing host after relinquishment, Kraktind Orn (`174.5 -> 41.5 km`) and Borselv North Orn (`168.8 -> 36.2 km`), both brought within 45 km by Johan Castberg FPSO (2025).

---

## 1. APA-Eligible Open-Acreage Inventory and Changed Circumstances

**Bottom line.** Out of 242 APA-eligible open prospects (`1.95 Bboe` risked, median `5` years open, `35.1%` with at least one new licence awarded within 20 km since relinquishment), **89 pure Tier A prospects (`0.81 Bboe` risked)** carry commercial or non-technical drop reasons with zero geological-risk tags, **90 prospects (`0.63 Bboe` risked)** sit within 30 km of a fluid-compatible in-service surface processing host, and **four Tier A gas prospects within 52 to 71 km of Aasta Hansteen total 457.1 MMboe unrisked (192.8 MMboe risked)**.

- **Data snapshot and exports.** All SODIR FactPages and FactMaps layers were pulled on `2026-11-25` and include `56` APA 2025 awards. Machine-readable outputs with `host_end_year`, `host_end_source`, `years_open`, `apa_rounds_since`, `nearby_awards_since`, and `changed_circumstances_flag` live in `reports/open_acreage_inventory.csv` and `reports/open_acreage_inventory.geojson`. Only in-service surface processing facilities (`fclSurface == Y`) are used as hosts (subsea templates and tie-back developments such as Irpa and Tommeliten Gamma are excluded as processing hosts).
- **Step 5 re-risking result (no multiplier applied).** Recomputing observed-to-stated `Pg` on the `57` calibrated redrills using **material** target-period discoveries gives **0.858 (95% bootstrap CI 0.454 to 1.328)** at `>= 1 MSm3` (near-field `0.973` [0.484, 1.594]; far-field `0.539` [0.000, 1.376]) and **0.786 (95% CI 0.389 to 1.262)** at `>= 3 MSm3` (near-field `0.876` [0.380, 1.494]; far-field `0.539` [0.000, 1.357]). Because every material CI includes `1.0`, unadjusted stated `Pg` is retained under the pre-registered rule (the earlier `1.65 to 1.89` technical ratios were inflated by small sub-material hits and redrill selection).
- **Step 6 economic screen result (uninformative with respect to distance).** Fitting a pooled `tau = 0.10` quantile regression on `81` post-2010 tie-back PDOs (`62` oil, `19` gas, excluding standalone hubs `< 2 km`) still yielded a flat-to-negative raw distance slope (`-0.0051`), collapsing under a monotone constraint (`slope >= 0`) to a constant volume floor (`5.5 MSm3` oil, `3.0 MSm3` gas). The empirical screen does not separate long from short tie-backs and is omitted from the headline shortlist.
- **Step 7 changed-circumstances screen.** Restricting to infrastructure-cited prospects now within `<= 50 km` of a fluid-compatible processing host isolates two actionable Barents **oil** prospects unlocked by **Johan Castberg FPSO (startup 2025)**, **Kraktind Orn** (`PL1027`, relinquished 2022, `174.5 -> 41.5 km`, `20.0 MMboe` risked) and **Borselv North Orn** (`PL1027`, relinquished 2022, `168.8 -> 36.2 km`, `9.5 MMboe` risked). Three other distance-drop flags (`Viasat` 190 km, `Himmelbjerget West` 222 km, `Lutsi` 89 km to subsea Irpa) remain too distant from a processing host.
- **Step 8 Tier A audit.** Manual audit of 30 random prospects under the broader Tier A rule (`n = 178`) gave `26 / 30` (`86.7%`) agreement, with 4 items carrying primary geological or seismic risk. Tightening Tier A to zero geological-risk tags is strictly more conservative, yielding **89 pure Tier A prospects (`0.81 Bboe` risked)** and **153 Tier B prospects (`1.15 Bboe` risked)** (prospects whose main drop reason was commercial while also mentioning a minor risk move to Tier B under this rule).
- **Aasta Hansteen Voring cluster.** Four Cretaceous gas prospects within 52 to 71 km of Aasta Hansteen (Kelvin, Fjellflokk Far East 1, Svartbakkestjerne Springar, Birkeland) total **457.1 MMboe unrisked / 192.8 MMboe risked** (with Maiblom 145.8 km from Aasta Hansteen adding 143.0 MMboe unrisked). Summing risked volumes gives expected value only; shared Cretaceous play risk applies.

### Top APA-Eligible Open-Acreage Shortlist (In-Service Surface Processing Hosts)

Ranked rows appear first by unadjusted risked volume; caveated rows (median-line split or unstated volume basis) appear separately at the bottom. Public `host_end_year` sources are stored per row in `open_acreage_inventory.csv` (Equinor Aasta Hansteen `2039` with Irpa, Snohvit/Melkoya `2050+`, Johan Castberg `2055`; Aker BP Ula and Tambar cessation plan `2028`; Var Energi Balder/Ringhorne `2045+`; Greater Ekofisk licence extension `2048`).

| Prospect (Licence) | Basin / Tier | Stated Pg | Unrisked / Risked (MMboe) | Yrs Open | Near Aw. (20 km) | Nearest In-Service Surface Host (km, End Year) |
| --- | --- | --- | --- | --- | --- | --- |
| Kelvin (PL653) | Norw. / Tier A | 35% | 184.9 / 64.7 | 10 | 0 | Aasta Hansteen Spar (52.3, 2039) |
| Sjampis (PL695) | Barents / Tier A | 25% | 223.3 / 55.8 | 5 | 0 | Goliat FPSO (124.5, unknown) |
| Fjellflokk Far East 1 (PL847) | Norw. / Tier A | 60% | 87.4 / 52.5 | 6 | 0 | Aasta Hansteen Spar (65.4, 2039) |
| Bjork Intra Heather Lower (PL1051) | North / Tier B | 21% | 240.5 / 50.5 | 3 | 1 | Gjoa (24.5, unknown) |
| Svartbakkestjerne Springar (PL847) | Norw. / Tier A | 42% | 118.1 / 49.6 | 6 | 0 | Aasta Hansteen Spar (71.0, 2039) |
| Faering East Ula (PL809) | North / Tier B | 34% | 136.0 / 46.2 | 8 | 3 | Tambar (14.3, 2028) |
| Maiblom (PL944) | Norw. / Tier B | 32% | 143.0 / 45.8 | 5 | 0 | Aasta Hansteen Spar (145.8, 2039) |
| Faering South (PL809) | North / Tier A | 29% | 146.0 / 42.3 | 8 | 1 | Tambar (11.7, 2028, HPHT / unmanned) |
| Firebird (PL678S) | North / Tier B | 28% | 122.3 / 34.2 | 9 | 0 | Ringhorne (56.6, 2045+) |
| Fannaraken (PL450) | North / Tier B | 30% | 90.6 / 27.2 | 12 | 1 | Ula QP (14.5, 2028, HPHT gas) |
| Arenaria (PL709) | Barents / Tier B | 56% | 47.9 / 26.8 | 9 | 0 | Melkoya LNG (214.0, 2050+) |
| Birkeland (PL694) | Norw. / Tier A | 39% | 66.7 / 26.0 | 10 | 0 | Aasta Hansteen Spar (51.9, 2039) |
| *Caveated* Edinburgh (PL660) | North / Tier A | 44% | ~46.5 / ~20.5 (NO share) | 10 | 1 | Ekofisk B (31.0, 2048) |
| *Caveated* Jaktfalk (PL595) | Barents / Tier A | 28% | 170.5 / 47.7 | 12 | 0 | Goliat FPSO (92.5, unknown) |

---

## 2. Cluster-Robust Redrill Regressions, Decision Outcomes, and Incumbency

**Bottom line.** Across 410 completed NCS wildcat parent wells (`2013 to 2026`, `396` licence clusters, `68` quadrant clusters), the near-field redrill penalty and positive distance interaction **survive licence and quadrant clustering for technical discoveries** (most conservative `p = 0.0019` and `p = 0.0043`), **are not statistically significant under the most conservative SE for material discoveries (`>= 3 MSm3`, `p = 0.1304`)**, and **are not detectable for commercial discoveries (`2013 to 2021`, `n = 281`, `50` events, low power, `p = 0.8511`)**. Adding operator incumbency shows that incumbents strongly outperform non-incumbents on active acreage (`OR = 2.33` technical, `OR = 3.98` material, `OR = 13.92` commercial), **but hold no advantage when redrilling relinquished polygons** (net incumbent log-odds among redrills `0.845 - 1.362 = -0.52`, `is_redrill x incumbent` `p = 0.0314`).

![Spatial point-in-polygon join and calibration comparison](figures/fig1_spatial_join_and_calibration.svg)

| Outcome and Model | Term | Coef (OR) | p Naive | p Lic-Clust | p Quad-Clust | Most Cons. p |
| --- | --- | --- | --- | --- | --- | --- |
| Technical (`n=410`, 204 hits) M1 | `is_redrill` | -0.359 (0.70) | 0.1934 | 0.2130 | 0.2197 | 0.2197 |
| Technical M2 (Interaction) | `is_redrill` | -2.506 (0.08) | 0.0008 | 0.0019 | 0.0004 | **0.0019** |
| Technical M2 (Interaction) | `is_redrill x log_dist` | +0.976 (2.65) | 0.0018 | 0.0043 | 0.0027 | **0.0043** |
| Technical M3 (+Incumbent) | `is_redrill x log_dist` | +0.737 (2.09) | 0.0231 | 0.0351 | 0.0225 | **0.0351** |
| Technical M3 (+Incumbent) | `incumbent` | +0.845 (2.33) | 0.0010 | 0.0012 | 0.0111 | **0.0111** |
| Technical M3 (+Incumbent) | `is_redrill x incumbent` | -1.362 (0.26) | 0.0121 | 0.0134 | 0.0314 | **0.0314** |
| Material `>=3 MSm3` (`n=410`, 76) M1 | `is_redrill` | -0.173 (0.84) | 0.6368 | 0.6271 | 0.6317 | 0.6368 |
| Material `>=3 MSm3` M2 | `is_redrill x log_dist` | +0.618 (1.86) | 0.1304 | 0.0467 | 0.0590 | 0.1304 |
| Material `>=3 MSm3` M3 | `incumbent` | +1.382 (3.98) | 0.0003 | 0.0007 | 0.0015 | **0.0015** |
| Material `>=3 MSm3` M3 | `is_redrill x incumbent` | -1.832 (0.16) | 0.0154 | 0.0152 | 0.0295 | **0.0295** |
| Commercial `2013-2021` (`n=281`, 50) M1 | `is_redrill` | -1.077 (0.34) | 0.1590 | 0.1719 | 0.1683 | 0.1719 |
| Commercial `2013-2021` M2 | `is_redrill x log_dist` | +0.243 (1.28) | 0.8511 | 0.5835 | 0.6184 | 0.8511 |
| Commercial `2013-2021` M3 | `incumbent` | +2.633 (13.92) | 0.0000 | 0.0000 | 0.0000 | **0.0000** |

- **Material sensitivity (`1` and `5 MSm3`).** At `1 MSm3` (`98` events), M2 interaction `p_lic = 0.0243`, `p_quad = 0.0243`, `p_naive = 0.0927` (`max = 0.0927`). At `5 MSm3` (`65` events), `p_lic = 0.0294`, `p_quad = 0.0460`, `p_naive = 0.0935` (`max = 0.0935`).
- **Hypothesis A vs Hypothesis B.** Under Hypothesis B (newcomers know less), informed incumbents should outperform newcomers when redrilling relinquished polygons. Instead, the net incumbency log-odds among redrills is negative (`0.845 - 1.362 = -0.52`), meaning informed incumbents do no better than newcomers on relinquished ground. That rules out newcomer information disadvantage as the driver of the redrill penalty and is consistent with **Hypothesis A (adverse selection, relinquished near-field ground itself is worse)**, since the distance interaction survives controlling for incumbency (`p = 0.0351`), while incumbency explains why the non-redrill near-field comparison group is so strong.

---

## 3. Reconciled Dry-Hole Causes vs SODIR Resource Report 2020

**Bottom line.** Mapping `seal_risk`, `retention`, and residual-column / uplift language into Trap, weighting multi-factor failures equally, and restricting to post-drill conclusions (`2007 to 2019`, `n = 112`, **16/20 = 80.0% out-of-sample manual audit agreement on fresh `seed = 123`**) yields North Sea shares of **39.8% Charge, 22.9% Trap, and 37.3% Reservoir** vs SODIR Resource Report 2020 Fact box 3.4 (**47% Source/Charge, 29% Trap, 24% Reservoir**, counted per target rather than per dry hole).

| Basin (`2007 to 2019`) | Atlas Dry Holes (n) | Atlas Charge | Atlas Trap | Atlas Reservoir | SODIR RR 2020 Fact Box 3.4 Post-Drill Benchmark |
| --- | --- | --- | --- | --- | --- |
| All NCS (`2007 to 2019`) | 112 | 30.5% | 23.4% | 46.1% | Not tabulated shelf-wide |
| North Sea | 59 | 39.8% | 22.9% | 37.3% | Source 47%, Trap 29%, Reservoir 24% (per target) |
| Norwegian Sea | 27 | 23.5% | 30.9% | 45.7% | Not directly tabulated in text |
| Barents Sea | 26 | 16.7% | 16.7% | 66.7% | Not directly tabulated in text |

- **Interpreting the residual gap.** Adding seal and residual-column language raises North Sea Trap from `5.9%` to `22.9%` and Barents Trap from `10.9%` to `16.7%`, though a `+13.3 pp` North Sea Reservoir excess and `-6.1 pp` Trap shortfall remain relative to SODIR. One hypothesis for this gap is conditioning on relinquished licences (absent or poor reservoir frequently condemns an entire licence) alongside unit-of-analysis differences (SODIR counts individual dry targets, whereas this audit counts dry holes) and relinquishment-report narrative style.

---

## 4. Conditional Patterns, Operator Spread, and 18-PDF Self-Consistency

**Bottom line.** All in-licence metrics remain **conditional on licence relinquishment**.

![Pre-drill fear vs dry-hole killer and basin-adjusted operator Pg residuals](figures/fig2_reservoir_blindspot_and_operators.svg)

![Paired award vs relinquishment volume scatter and risked volume drift histogram](figures/fig3_apa_shrinkage_method.svg)

![DHI discovery rates with Barents gas-only inset and 18-PDF VLM polygon IoU consistency](figures/fig4_dhi_paradox_and_llm_iou.svg)

- **Conditional in-licence discovery rate and volume drift.** Within relinquished licences (`n = 138`), mean pre-drill `Pg` is 27.0% vs 18.1% realized (-8.9 pp, p = 0.0134). Among re-evaluated award-to-relinquishment pairs (`n = 183` mean volume, `n = 165` risked), 79.2% shrink in mean volume (median -52.0%) and 83.0% lose risked volume (median -61.4%).
- **Operator Pg spread (with current corporate successors).** Basin-adjusted stated `Pg` spans 16.5 pp across major historical operators (`n >= 20`), led by DNO (+9.6 pp) and Wintershall Dea (now **Harbour Energy**, +6.7 pp) vs Neptune/ENGIE (now **Var Energi**, -6.8 pp), ConocoPhillips (-5.3 pp), Shell (-4.4 pp), and Lundin (now **Aker BP**, -4.2 pp). Without unconditional outcomes and play/vintage controls, this reflects reporting conventions and portfolio mix.
- **DHI and 18-PDF self-consistency.** Positive DHI yields 54.2% vs 22.6% for negative DHI (p = 5.6e-5; Barents 2.5x technical lift with 84.6% gas-only hits vs 6.7% North Sea). Claimed flat spots (28.0% vs 69.0% positive amplitude conformance, unadjusted p = 0.0018) remain exploratory. Across 18 duplicate PDFs, independent VLM map digitizations (`n = 52`) show 0.861 median polygon IoU and 116.8 m median centroid shift (self-consistency only, not ground-truth accuracy).

---

## Deviations from Pre-Registered Plan v1.1

1. **Sample size (`n = 410` vs `401`).** Including all completed wildcat parent wells from `2013+` with valid coordinates and basin labels added 9 wells relative to the earlier `track7` filter.
2. **Wild cluster bootstrap.** Both licence clusters (`396`) and quadrant clusters (`64` to `68`) exceeded the `< 50` cluster trigger across all models, so asymptotic cluster-robust SEs were used.
3. **Dry-hole text scope and out-of-sample audit.** Restricting Step 4 to post-drill `conclusion` text plus Barents residual-column language after the initial `seed = 42` audit was validated on a fresh out-of-sample `seed = 123` draw (16/20 = 80.0% agreement).
4. **Economic screen uninformative.** Even restricted to tie-backs (`>= 2 km`, own-field hubs excluded) with pooled fluid offset, the `tau = 0.10` distance slope remained slightly negative (`-0.0051`), collapsing to a flat floor under monotonicity; omitted from the bottom line and shortlist.
5. **Re-risking evaluated on material outcomes.** Evaluating Step 5 on material target-period discoveries (`>= 1` and `>= 3 MSm3`) yielded 95% CIs spanning `1.0`, so unadjusted stated `Pg` was kept per the pre-registered decision rule.
6. **Surface processing hosts only.** Subsea tie-back PDOs (`Irpa`, `Tommeliten Gamma`, `Hugin`) were excluded from surface hosts in Step 7/8 so distances reflect processing hosts consistently.
7. **Commercial incumbency separation.** In Model 3 for commercial discoveries (`2013 to 2021`), `is_redrill x incumbent` exhibited quasi-complete separation (0 incumbent redrills reached commercial status), inflating its naive SE while leaving main `incumbent` (`OR = 13.92, p < 0.0001`) intact.

---

## Appendix. Exploratory P90 to P10 Volume Coverage vs SODIR Look-Back

Across 10 standalone SODIR discoveries (`discovery_reserves`) matched to tight (`<= 100 km2`) relinquished polygons with pre-drill `[P90, P10]` ranges, 8 of 10 (80.0%, 95% Wilson CI 49% to 94%) fall inside `[P90, P10]`, with 2 above P10, 0 below P90, and a median actual-to-pre-drill-mean ratio of 1.11x. This contrasts with SODIR's shelf-wide look-back analysis, where realized discovery size fell inside the stated P90 to P10 range in only **2 of 10** cases. Sample size (`n = 10`, CI 49% to 94%), discovery selection bias, and post-shrinkage range vintage explain why this figure is exploratory only.

---

## Reproducibility

- Pre-registration plan `analyses/PLAN_v1.1.md`
- Step 1 to 8 script and outputs `analyses/track8_inference_and_rerisk.py`, `analyses/track8_findings.json`
- Full APA-open inventory `reports/open_acreage_inventory.csv` and `reports/open_acreage_inventory.geojson`
- Shared loader `src/loader.py` and matplotlib figure generator `analyses/generate_figures.py`
