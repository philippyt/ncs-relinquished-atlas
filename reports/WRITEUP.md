# Screened Open-Acreage Prospect Inventory from 738 NCS Relinquishment Reports

Screening the relinquishment atlas against current SODIR licences, surface hosts, and discovery outlines (`2026-11-25`, including APA 2025) leaves **227 unique open APA prospects holding 6.02 Bboe unrisked and 1.88 Bboe risked**. Since 2013, one in five completed NCS wildcats (`78` of `398`, `19.6%`) redrilled a relinquished polygon, showing a near-field technical penalty that does not hold with statistical significance for material or commercial discoveries. Using host PDO approval dates rather than first-oil start-up dates, **no prospect in the inventory was unlocked by a newly sanctioned host after relinquishment**.

---

## Key Findings

1. **227 unique open-acreage prospects hold 1.88 Bboe risked, anchored by a four-prospect Voring gas cluster.** After collapsing cross-licence polygon duplicates and removing overlaps with known SODIR discoveries, `84` pure Tier A prospects (`0.77 Bboe` risked) carry commercial or non-technical drop reasons with zero geological-risk tags, and `82` prospects (`0.60 Bboe` risked) sit within `30 km` of a fluid-compatible surface processing host. The open pool has a median age of `5` years, `33.5%` have seen at least one new licence awarded within `20 km` since relinquishment, and `30.0%` (`68` of `227`) sit within `5 km` of a historical same-play dry well. The single largest concentration is four Tier A Cretaceous gas prospects within `52 to 71 km` of Aasta Hansteen (`Kelvin`, `Fjellflokk Far East 1`, `Svartbakkestjerne Springar`, and `Birkeland`) totaling **457.1 MMboe unrisked (192.8 MMboe risked)**, subject to shared Cretaceous play risk (`Maiblom`, `145.8 km` away and relinquished twice, adds `143.0 MMboe` unrisked).

2. **Host decommissioning schedules eliminate several near-field North Sea targets before plausible start-up.** Public host end years are known for **106 of the 227 prospects** (`121` remain unknown). Assuming an APA 2026 or 2027 award needs roughly seven years to reach first production (`~2033`), **`10` of the `106` known prospects** lose their nearest host before start-up (including `Faering East`, `Faering South`, and `Fannaraken` around Tambar and Ula, both scheduled to cease in `2028`). Another **`21` prospects** face a tight `2033 to 2040` window (including the four Aasta Hansteen prospects with roughly `5 to 6` years of host life unless extended past `2039`), leaving **`75` known prospects** in a viable post-2040 window.

3. **No open prospect was clearly unlocked by a newly sanctioned processing host.** Measuring host availability from PDO approval rather than first-oil start-up returns **0 of 227 prospects**. The two apparent Barents oil candidates in `PL1027` (**Kraktind Orn**, `66.8` unrisked / `20.0 MMboe` risked, and **Borselv North Orn**, `31.7` / `9.5 MMboe` risked, both relinquished twice) sit within `45 km` of Johan Castberg FPSO (`2025` first oil), but Castberg's PDO was approved in June `2018`, before both `PL1027`'s award (`2019`) and relinquishment (`2022`). In the predecessor `PL715` report (`2018`), Aker BP had already evaluated `Kraktind North` as a Castberg tie-back (`20 MMboe` minimum economic size, `45 MMboe` marginal) and relinquished after the dry `7220/6-3` Borselv well (`380 m` of medium-to-poor Permian Orn Formation carbonates); Lundin's `PL1027` (`2022`) omission of Castberg in favor of Wisting (`120 km`) and Goliat (`150 km`) reflects commercial or access constraints rather than a new host. Both structures also sit in the lowest-performing play in the atlas (`18.8%` Permian discovery rate, `6` of `32` drilled vs `30%` stated `Pg`).

4. **Near-field redrills show a technical penalty, not a proven commercial risking rule.** On `398` completed NCS wildcats with final outcomes (`2013 to 2026`, `78` redrills or `19.6%`), redrilling a relinquished polygon close to prior discoveries carries a statistically robust penalty on technical discoveries that fades with distance and survives licence clustering, quadrant clustering, and incumbency controls. That penalty is not statistically significant for material (`>= 3 MSm3`) or commercial (`2013 to 2021`) discoveries, where event counts are smaller, so the data cannot distinguish between a penalty restricted to small technical finds and low statistical power. Incumbents strongly outperform newcomers on active acreage, yet show no advantage when redrilling relinquished polygons, pointing toward adverse selection on relinquished near-field ground rather than a newcomer information gap.

5. **Mechanical `Pg` multipliers and distance-based economic floors are not supported by the data.** Evaluating calibrated redrills against material target-period discoveries (`>= 1` and `>= 3 MSm3`) yields observed-to-stated `Pg` ratios whose `95%` confidence intervals span `1.0`, so unadjusted stated `Pg` is kept in the shortlist. A quantile regression on `81` post-2010 tie-back PDOs similarly found no upward volume-vs-distance slope, leaving a distance-based minimum economic size screen uninformative. Inside relinquished licences (conditional on relinquishment), realized discovery rates trail stated `Pg` (`18.1%` vs `27.0%`), `83.0%` of re-evaluated prospects lose risked volume between award and relinquishment (median `-61.4%`), and North Sea dry holes show higher reservoir failure shares (`37.3%`) than SODIR's shelf-wide benchmark (`24%`).

![Spatial point-in-polygon join and calibration comparison](figures/fig1_spatial_join_and_calibration.svg)

![Pre-drill fear vs dry-hole killer and basin-adjusted operator Pg residuals](figures/fig2_reservoir_blindspot_and_operators.svg)

![Paired award vs relinquishment volume scatter and risked volume drift histogram](figures/fig3_apa_shrinkage_method.svg)

---

## Top APA-Eligible Open-Acreage Shortlist

Ranked rows appear first by unadjusted risked volume; caveated rows (median-line split or unstated volume basis) appear separately at the bottom. Only in-service surface processing hosts are listed; full `227`-row exports with host end-year sources live in `reports/open_acreage_inventory.csv` and `reports/open_acreage_inventory.geojson`.

| Prospect (Licence) | Basin / Tier | Stated Pg | Unrisked / Risked (MMboe) | Times Relinq. | Dry <=5 km | Yrs Open | Near Aw. | Nearest Surface Host (km, End Year) | Host Viability |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Kelvin (PL653) | Norw. / Tier A | 35% | 184.9 / 64.7 | 1 | No (19.9) | 10 | 0 | Aasta Hansteen (52.3, 2039) | Short (~5-6 yr) |
| Sjampis (PL695) | Barents / Tier B | 25% | 223.3 / 55.8 | 1 | No (30.7) | 5 | 0 | Goliat FPSO (124.5, unknown) | Unknown |
| Fjellflokk Far East 1 (PL847) | Norw. / Tier A | 60% | 87.4 / 52.5 | 1 | No (20.7) | 6 | 0 | Aasta Hansteen (65.4, 2039) | Short (~5-6 yr) |
| Bjork Intra Heather Lower (PL1051) | North / Tier B | 21% | 240.5 / 50.5 | 1 | No (17.2) | 3 | 1 | Gjoa (24.5, unknown) | Unknown |
| Svartbakkestjerne Springar (PL847) | Norw. / Tier A | 42% | 118.1 / 49.6 | 1 | No (12.8) | 6 | 0 | Aasta Hansteen (71.0, 2039) | Short (~5-6 yr) |
| Faering East Ula (PL809) | North / Tier B | 34% | 136.0 / 46.2 | 1 | No (5.9) | 8 | 3 | Tambar (14.3, 2028) | Ends pre-startup |
| Maiblom (PL944) | Norw. / Tier B | 32% | 143.0 / 45.8 | 2 | No (41.8) | 5 | 0 | Aasta Hansteen (145.8, 2039) | Short (~5-6 yr) |
| Faering South (PL809) | North / Tier A | 29% | 146.0 / 42.3 | 1 | Yes (3.1) | 8 | 1 | Tambar (11.7, 2028, HPHT) | Ends pre-startup |
| Firebird (PL678S) | North / Tier B | 28% | 122.3 / 34.2 | 2 | No (7.2) | 9 | 0 | Ringhorne (56.6, 2045+) | Viable window |
| Sweetums South Norian (PL1083) | Barents / Tier B | 22% | 126.0 / 27.7 | 1 | No (10.6) | 2 | 0 | Goliat FPSO (272.3, unknown) | Unknown |
| Fannaraken (PL450) | North / Tier B | 30% | 90.6 / 27.2 | 1 | Yes (3.9) | 12 | 1 | Ula QP (14.5, 2028, HPHT) | Ends pre-startup |
| Arenaria (PL709) | Barents / Tier B | 56% | 47.9 / 26.8 | 1 | No (31.2) | 9 | 0 | Melkoya LNG (214.0, 2050+) | Viable window |
| Birkeland (PL694) | Norw. / Tier A | 39% | 66.7 / 26.0 | 1 | No | 10 | 0 | Aasta Hansteen (51.9, 2039) | Short (~5-6 yr) |
| *Caveated* Edinburgh (PL660) | North / Tier A | 44% | ~46.5 / ~20.5 (NO) | 1 | No (12.6) | 10 | 1 | Ekofisk B (31.0, 2048) | Viable window |
| *Caveated* Jaktfalk (PL595) | Barents / Tier B | 28% | 170.5 / 47.7 | 1 | No (29.0) | 12 | 0 | Goliat FPSO (92.5, unknown) | Unknown |

---

## Technical Appendix

### A1. Inventory Filtering, Spatial Deduplication, and Discovery Screen

- **Eligibility and snapshot.** All SODIR FactPages and FactMaps layers were pulled on `2026-11-25` and include `56` APA 2025 awards. Eligibility requires `Pg >= 0.20`, post-award assessment, undrilled status, and `>= 50%` of the Norwegian-sector-clipped prospect polygon outside active SODIR licences. Only in-service surface processing facilities (`fclSurface == Y`) are used as hosts (subsea tie-back developments such as Irpa and Tommeliten Gamma are excluded as processing hosts).
- **Spatial deduplication and SODIR discovery/field screen.** Grouping cross-licence prospect polygons overlapping by `>= 50%` at the same reservoir period collapsed `14` renamed or re-licensed duplicate pairs (keeping the newest assessment and recording `predecessor_ids` and `times_relinquished`, including `Maiblom / Nerthus`, `Firebird / Litlfjellet`, `Kraktind Orn / Kraktind North`, and `Borselv North Orn / Kraktind South`), reducing `242` rows to `228`. Screening all polygons against SODIR FactMaps discovery (`Layer 504`) and field (`Layer 502`) outlines excluded `1` prospect overlapping a known discovery by `>= 50%` (`PL817_EIRIK_WEDGE_2_SOUTH`, `67.9%` overlap with `15/2-2 S Eirik`), leaving **227 unique prospects** (`10` partial `20% to 49%` overlaps remain flagged in `sodir_disc_field_overlap_pct`).
- **Nearby same-play dry-well flag.** `68` of `227` prospects (`30.0%`) have a historical dry wildcat penetrating the same reservoir period within `5 km`. Both `nearest_same_play_dry_well_km` and `nearby_same_play_dry_well_5km` are recorded without altering the operator's drop reason.
- **Host lifetime viability (`host_viability_flag`).** Public host end years are known for `106` of `227` prospects (`121` `unknown`). Using `award + 7` years (`~2033` first production for an APA 2026 or 2027 award), `host_end_year < 2033` is flagged `host_ends_before_startup` (`10` of `106`), `2033 to 2040` is flagged `short_host_window` (`21` of `106`), and `> 2040` is flagged `viable_window` (`75` of `106`).
- **Step 8 Tier A manual audit.** Auditing `30` random prospects under the broader Tier A rule yielded `26 / 30` (`86.7%`) agreement, with `4` items carrying primary geological or seismic risk. Tightening Tier A to zero geological-risk tags yields `84` pure Tier A prospects (`0.77 Bboe` risked) and `143` Tier B prospects (`1.10 Bboe` risked).
- **Step 7 changed-circumstances screen.** Using host PDO approval dates rather than first-oil start-up dates returns **0 of 227 prospects** (`changed_circumstances_flag = False` across the inventory). Using start-up dates had previously flagged `Kraktind Orn` and `Borselv North Orn` in `PL1027` (`2022`) against Johan Castberg (`2025` first oil), but Castberg's PDO was approved in June `2018` and had already been evaluated as a tie-back host in predecessor licence `PL715` (`2018`).

### A2. Cluster-Robust Redrill Regressions and Incumbency Tests (Steps 1 to 3)

Across `398` completed NCS wildcat parent wells with final outcomes (`2013 to 2026`, `387` licence clusters, `68` quadrant clusters, excluding `12` junked wells and `1` unpublished `2026-11-16` well `36/7-6 S`), logistic models were fit for technical discoveries, material discoveries (`>= 3 MSm3`, with `1` and `5 MSm3` sensitivity), and commercial discoveries (`2013 to 2021`, `n = 274`, `50` events).

| Outcome and Model | Term | Coef (OR) | p Naive | p Lic-Clust | p Quad-Clust | Most Cons. p |
| --- | --- | --- | --- | --- | --- | --- |
| Technical (`n=398`, 204 hits) M1 | `is_redrill` | -0.385 (0.68) | 0.1695 | 0.1964 | 0.1901 | 0.1964 |
| Technical M2 (Interaction) | `is_redrill` | -2.535 (0.08) | 0.0008 | 0.0022 | 0.0004 | **0.0022** |
| Technical M2 (Interaction) | `is_redrill x log_dist` | +0.979 (2.66) | 0.0020 | 0.0049 | 0.0030 | **0.0049** |
| Technical M3 (+Incumbent) | `is_redrill x log_dist` | +0.765 (2.15) | 0.0197 | 0.0308 | 0.0188 | **0.0308** |
| Technical M3 (+Incumbent) | `incumbent` | +0.743 (2.10) | 0.0043 | 0.0047 | 0.0291 | **0.0291** |
| Technical M3 (+Incumbent) | `is_redrill x incumbent` | -1.222 (0.30) | 0.0265 | 0.0318 | 0.0527 | 0.0527 |
| Material `>=3 MSm3` (`n=398`, 76) M1 | `is_redrill` | -0.178 (0.84) | 0.6284 | 0.6188 | 0.6274 | 0.6284 |
| Material `>=3 MSm3` M2 | `is_redrill x log_dist` | +0.615 (1.85) | 0.1309 | 0.0475 | 0.0662 | 0.1309 |
| Material `>=3 MSm3` M3 | `incumbent` | +1.325 (3.76) | 0.0006 | 0.0011 | 0.0025 | **0.0025** |
| Material `>=3 MSm3` M3 | `is_redrill x incumbent` | -1.744 (0.18) | 0.0217 | 0.0220 | 0.0370 | **0.0370** |
| Commercial `2013-2021` (`n=274`, 50) M1 | `is_redrill` | -1.070 (0.34) | 0.1619 | 0.1733 | 0.1711 | 0.1733 |
| Commercial `2013-2021` M2 | `is_redrill x log_dist` | +0.299 (1.35) | 0.8152 | 0.4957 | 0.5362 | 0.8152 |
| Commercial `2013-2021` M3 | `incumbent` | +2.606 (13.55) | 0.0000 | 0.0001 | 0.0000 | **0.0001** |

- **Material sensitivity (`1` and `5 MSm3`).** At `1 MSm3` (`98` events), M2 interaction `p_lic = 0.0251`, `p_quad = 0.0281`, `p_naive = 0.0938` (`max = 0.0938`). At `5 MSm3` (`65` events), `p_lic = 0.0296`, `p_quad = 0.0513`, `p_naive = 0.0956` (`max = 0.0956`). Because point estimates at `1`, `3`, and `5 MSm3` point in the same direction as the technical penalty without reaching conservative significance, the data cannot separate "penalty restricted to small technical finds" from "too few material or commercial events to detect it".
- **Hypothesis A vs Hypothesis B.** Under Hypothesis B (newcomer information disadvantage), incumbents should outperform newcomers when redrilling relinquished polygons. Instead, the cluster-robust linear combination `incumbent + is_redrill x incumbent` among redrills is `-0.479` log-odds (`OR = 0.62`, licence-clustered `95%` CI `-1.519 to +0.561` or `OR 0.22 to 1.75`; quadrant-clustered `-1.438 to +0.479`; material `>= 3 MSm3` `-0.419`, `95%` CI `-1.649 to +0.811`). Because the CI includes moderately positive values, the data **provide no support for Hypothesis B** without definitively ruling it out, while remaining consistent with **Hypothesis A (adverse selection)** because the distance interaction survives incumbency control (`p = 0.0308`).
- **Redrill stratigraphic match audit.** Checking all `78` redrills (`39` incumbent, `39` non-incumbent) in the `398`-well `2013+` sample against SODIR `wellbore_formation_top` penetrated periods confirms `38 / 39` (`97.4%`) non-incumbent redrills and `35 / 39` (`89.7%`, with `1` unknown prospect period and `3` mismatches) incumbent redrills penetrated the same stratigraphic period as the relinquished polygon. Only `2` confirmed deep-vs-shallow mismatches occur among incumbents (`25/11-30` stopping in Paleogene above Jurassic lead `Romulus`, and `25/7-13` hitting Jurassic inside `198.3 km2` Cretaceous lead `Liddle Busta`), alongside `5` incumbent wells inside polygons larger than `100 km2`.

### A3. Reconciled Dry-Hole Causes vs SODIR Resource Report 2020 (Step 4)

Mapping `seal_risk`, `retention`, and residual-column / uplift language into Trap, weighting multi-factor failures equally, and restricting to post-drill conclusions (`2007 to 2019`, `n = 112`, `16/20 = 80.0%` out-of-sample manual audit agreement on fresh `seed = 123`) yields the basin shares below.

| Basin (`2007 to 2019`) | Atlas Dry Holes (n) | Atlas Charge | Atlas Trap | Atlas Reservoir | SODIR RR 2020 Fact Box 3.4 Post-Drill Benchmark |
| --- | --- | --- | --- | --- | --- |
| All NCS (`2007 to 2019`) | 112 | 30.5% | 23.4% | 46.1% | Not tabulated shelf-wide |
| North Sea | 59 | 39.8% | 22.9% | 37.3% | Source 47%, Trap 29%, Reservoir 24% (per target) |
| Norwegian Sea | 27 | 23.5% | 30.9% | 45.7% | Not directly tabulated in text |
| Barents Sea | 26 | 16.7% | 16.7% | 66.7% | Not directly tabulated in text |

Adding seal and residual-column language raises North Sea Trap from `5.9%` to `22.9%` and Barents Trap from `10.9%` to `16.7%`, leaving a `+13.3 pp` North Sea Reservoir excess and `-6.1 pp` Trap shortfall vs SODIR. Conditioning on relinquished licences (absent or poor reservoir frequently condemns a whole licence), unit-of-analysis differences (dry targets vs dry holes), and relinquishment-report narrative style likely contribute to the gap.

### A4. Null Calibration and Economic Screen Results (Steps 5 to 6)

- **Step 5 re-risking (no multiplier applied).** Recomputing observed-to-stated `Pg` on the `55` calibrated redrills using material target-period discoveries gives **0.869 (95% bootstrap CI 0.452 to 1.357)** at `>= 1 MSm3` (near-field `0.981` [0.485, 1.591]; far-field `0.553` [0.000, 1.393]) and **0.797 (95% CI 0.395 to 1.296)** at `>= 3 MSm3` (near-field `0.883` [0.398, 1.510]; far-field `0.553` [0.000, 1.401]). Every CI includes `1.0`, so unadjusted stated `Pg` is retained under the pre-registered rule.
- **Step 6 economic screen (uninformative with respect to distance).** Pooled `tau = 0.10` quantile regression on `81` post-2010 tie-back PDOs (`62` oil, `19` gas, excluding standalone hubs `< 2 km`) yielded a flat-to-negative raw distance slope (`-0.0051`), collapsing under monotonicity (`slope >= 0`) to a constant volume floor (`5.5 MSm3` oil, `3.0 MSm3` gas).

### A5. Conditional In-Licence Patterns, Operator Spread, DHI, and P90 to P10 Coverage

All in-licence metrics remain conditional on licence relinquishment.

![DHI discovery rates with Barents gas-only inset and 18-PDF VLM polygon IoU consistency](figures/fig4_dhi_paradox_and_llm_iou.svg)

- **Conditional in-licence discovery rate and volume drift.** Within relinquished licences (`n = 138`), mean pre-drill `Pg` is `27.0%` vs `18.1%` realized (`-8.9 pp`, `p = 0.0134`). Among re-evaluated award-to-relinquishment pairs (`n = 183` mean volume, `n = 165` risked), `79.2%` shrink in mean volume (median `-52.0%`) and `83.0%` lose risked volume (median `-61.4%`).
- **Operator `Pg` spread (with current corporate successors).** Basin-adjusted stated `Pg` spans `16.5 pp` across major historical operators (`n >= 20`), led by DNO (`+9.6 pp`) and Wintershall Dea (now **Harbour Energy**, `+6.7 pp`) vs Neptune/ENGIE (now **Var Energi**, `-6.8 pp`), ConocoPhillips (`-5.3 pp`), Shell (`-4.4 pp`), and Lundin (now **Aker BP**, `-4.2 pp`). Without unconditional outcomes and play/vintage controls, this reflects reporting conventions and portfolio mix.
- **DHI and 18-PDF self-consistency.** Positive DHI yields `54.2%` vs `22.6%` for negative DHI (`p = 5.6e-5`; Barents `2.5x` technical lift with `84.6%` gas-only hits vs `6.7%` North Sea). Claimed flat spots (`28.0%` vs `69.0%` positive amplitude conformance, unadjusted `p = 0.0018`) remain exploratory. Across `18` duplicate PDFs, independent VLM map digitizations (`n = 52`) show `0.861` median polygon IoU and `116.8 m` median centroid shift (self-consistency only, not ground-truth accuracy).
- **Exploratory P90 to P10 volume coverage vs SODIR look-back.** Across `10` standalone SODIR discoveries (`discovery_reserves`) matched to tight (`<= 100 km2`) relinquished polygons with pre-drill `[P90, P10]` ranges, `8` of `10` (`80.0%`, `95%` Wilson CI `49% to 94%`) fall inside `[P90, P10]` (`2` above P10, `0` below P90, median actual-to-pre-drill-mean ratio `1.11x`), vs `2` of `10` in SODIR's shelf-wide look-back. Small sample size, discovery selection bias, and post-shrinkage range vintage make this exploratory only.

### A6. Deviations from Pre-Registered Plan v1.1

1. **Sample size (`n = 398` vs `401`).** Restoring `4` genuinely completed parent wells whose un-drilled `A` sidetracks had `wlbCompletionYear = 0` (`16/7-11`, `34/6-8`, `34/8-20`, `6606/4-1`) and excluding `12` junked wells (`wlbStatus = JUNKED`) plus `1` unpublished `2026-11-16` well (`36/7-6 S`, `wlbContent = null`) yields `398` completed wildcats with final outcomes (`78` redrills).
2. **Wild cluster bootstrap.** Both licence clusters (`387`) and quadrant clusters (`64` to `68`) exceeded the `< 50` cluster trigger across all models, so asymptotic cluster-robust SEs were used.
3. **Dry-hole text scope and out-of-sample audit.** Restricting Step 4 to post-drill `conclusion` text plus Barents residual-column language after the initial `seed = 42` audit was validated on a fresh out-of-sample `seed = 123` draw (`16/20 = 80.0%` agreement).
4. **Economic screen uninformative.** Even restricted to tie-backs (`>= 2 km`, own-field hubs excluded) with pooled fluid offset, the `tau = 0.10` distance slope remained slightly negative (`-0.0051`), collapsing to a flat floor under monotonicity; omitted from the brief and shortlist.
5. **Re-risking evaluated on material outcomes.** Evaluating Step 5 on material target-period discoveries (`>= 1` and `>= 3 MSm3`) yielded `95%` CIs spanning `1.0`, so unadjusted stated `Pg` was kept per the pre-registered decision rule.
6. **Surface processing hosts and PDO approval dates.** Subsea tie-back PDOs (`Irpa`, `Tommeliten Gamma`, `Hugin`) were excluded from surface hosts in Step 7/8, and Step 7 measures host availability from PDO approval year rather than first-oil start-up year (returning `0` prospects).
7. **Spatial deduplication and SODIR discovery/field screen.** Cross-licence `>= 50%` polygon overlap deduplication at the same reservoir period (keeping `predecessor_ids` and `times_relinquished`) and exclusion of `>= 50%` overlaps with SODIR discovery/field polygons (`Layer 504` / `502`) reduced the APA-open inventory from `242` to `227` unique structures.
8. **Commercial incumbency separation.** In Model 3 for commercial discoveries (`2013 to 2021`, `n = 274`), `is_redrill x incumbent` exhibited quasi-complete separation (`0` incumbent redrills reached commercial status), inflating its naive SE while leaving main `incumbent` (`OR = 13.55`, `p = 0.0001`) intact.

### A7. Reproducibility

- Pre-registration plan `analyses/PLAN_v1.1.md`
- Step 1 to 8 script and outputs `analyses/track8_inference_and_rerisk.py`, `analyses/track8_findings.json`
- Spatial deduplication, SODIR discovery/field overlap screen, and nearby dry-well flag `analyses/track9_spatial_dedup_and_discovery_screen.py`, `analyses/track9_findings.json`
- Full APA-open inventory `reports/open_acreage_inventory.csv` and `reports/open_acreage_inventory.geojson`
- Shared loader `src/loader.py` and matplotlib figure generator `analyses/generate_figures.py`
