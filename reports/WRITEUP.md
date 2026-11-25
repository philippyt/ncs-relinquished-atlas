# Screened Relinquished Prospect Inventory and Conditional Audit of 756 NCS Licences

**Bottom line.** Cleaning 756 Norwegian Continental Shelf relinquishment reports (`10.5281/zenodo.24528585`, 738 unique licences and 5,325 prospects after removing 18 duplicate multi-licence reports and three 1,000x unit-scaling errors) and spatially joining them to 536 currently active SODIR production licences identifies **287 georeferenced undrilled prospects (`Pg >= 0.20`) sitting in currently open acreage, holding 426.6 MSm3 o.e. (2.68 Bboe) risked**. Testing post-relinquishment redrills per unique wildcat (`n = 83`) against the exact year-matched shelf-wide wildcat baseline (50.1%) shows **no outperformance** (41.0% overall, 48.1% vs 48.0% on vertical, tight, stratigraphic-matched wells). On standalone SODIR discoveries with pre-drill volume ranges (`n = 10`), 80.0% fall inside stated P90 to P10 bounds. All in-licence calibration and shrinkage metrics below are strictly **conditional on relinquishment** and reflect selection of disappointing licences rather than shelf-wide operator bias.

---

## 1. Data Cleaning and Live Open-Acreage Inventory

**Bottom line.** Out of 469 georeferenced undrilled relinquished prospects with `Pg >= 0.20`, **61.2% (287 prospects, 2.68 Bboe risked)** remain in currently unlicensed open acreage while **38.8% (182 prospects, 1.31 Bboe risked)** have already been re-awarded into active SODIR licences.

- **Deduplication and unit fixes.** 18 joint relinquishment PDFs appear twice under paired licence NPDIDs (such as PL1003 and PL1003B, PL1043 and PL1043B, PL785S and PL785SB) and were deduplicated to 738 unique licences. Three 1,000x unit-scaling bugs (`PL531_JURASSIC` bcf converted with tcf factor 28.3168, `PL1019` GSm3 OE header multiplied by 1,000 against explicit MSm3 OE text, and `PL883 Taren East` condensate mistyped as 1e9 Sm3) were corrected prior to aggregation. Quieter extraction errors (such as swapped P10 and P90 labels or gas Sm3 vs oil-equivalent ambiguity) remain possible and require checking the source PDF page before relying on any individual prospect.
- **Active acreage join.** Prospect centroids were tested via point-in-polygon against all 536 currently active production licence polygons from SODIR FactMaps Layer 616 (`Production licence, all - current with geometry`).
- **Context.** Volume and `Pg` figures are the relinquishing operator's post-shrinkage estimates and are already counted inside SODIR's shelf-wide undiscovered resource inventory. The practical value is a georeferenced, queryable shortlist replacing manual reading of 738 PDFs.

| Prospect | Relinquished Licence | Basin | Stated Pg | Risked (MMboe) | Current Status | Active Licence / Operator |
| --- | --- | --- | --- | --- | --- | --- |
| Edinburgh | PL660 (2016) | North Sea | 44% | 93.1 | Open acreage | None |
| Natator Cluster | PL728 (2018) | North Sea | 24% | 75.1 | Re-licensed | PL1136 (ORLEN Upstream Norway) |
| Kelvin | PL653 (2016) | Norwegian Sea | 35% | 64.7 | Open acreage | None |
| Balderbra | PL522 (2014) | Norwegian Sea | 37% | 58.6 | Open acreage | None |
| Sjampis | PL695 (2021) | Barents Sea | 25% | 55.8 | Open acreage | None |
| Fjellflokk Far East 1 | PL847 (2020) | Norwegian Sea | 60% | 52.5 | Open acreage | None |
| Svartbakkestjerne Springar | PL847 (2020) | Norwegian Sea | 42% | 49.6 | Open acreage | None |
| Maiblom | PL944 (2021) | Norwegian Sea | 32% | 45.8 | Open acreage | None |
| Faering South | PL809 (2018) | North Sea | 29% | 42.3 | Open acreage | None |
| Barlind | PL503 | North Sea | 20% | n/a | Re-licensed | PL1283 (Equinor Energy) |

---

## 2. Unique-Well Redrills vs Year-Matched Shelf Baseline

**Bottom line.** Once overlapping prospect polygons are deduplicated to unique wildcats (`n = 83`) and benchmarked against the exact year-matched NCS shelf-wide wildcat discovery rate (50.1%), post-relinquishment redrills show **no discovery-rate edge** (41.0% overall, -9.2 pp vs shelf, z = -1.67). Restricting to vertical-only, tight polygons (`<= 50 km2`), and stratigraphic-age-matched targets (`n = 27`) yields 48.1% against a 48.0% year-matched shelf baseline (+0.1 pp, z = 0.01).

![Spatial point-in-polygon join and calibration comparison](figures/fig1_spatial_join_and_calibration.svg)

**Method.** All undrilled relinquished prospect polygons were joined by point-in-polygon to completed SODIR wildcat wellhead coordinates (`wlbCompletionYear > report_year`). Wells penetrating multiple overlapping polygons (35 of 83 unique wildcats, inflating 83 wells to 141 polygon hits) were collapsed to one record per unique well. Each subset was compared against the exact completion-year-weighted shelf-wide wildcat discovery rate computed from `wellbore_exploration_all.parquet`, with additional filters for vertical wells (excluding `S`, `A`, `B`, and `T` sidetrack/deviated suffixes) and stratigraphic period overlap (`reservoir.chrono.period` matching `wlbAgeWithHc1..3` or `wlbAgeAtTd`).

| Unique-Well Redrill Cohort | Unique Wildcats (n) | Discoveries | Observed Rate | Year-Matched Shelf Baseline | Diff vs Shelf (pp) | z-stat |
| --- | --- | --- | --- | --- | --- | --- |
| All unique post-relinquishment wildcats | 83 | 34 | 41.0% | 50.1% | -9.2 | -1.67 |
| Vertical-only wildcats | 39 | 16 | 41.0% | 48.2% | -7.1 | -0.89 |
| Deviated or sidetrack wildcats | 44 | 18 | 40.9% | 51.9% | -11.0 | -1.46 |
| Tight polygons (`<= 50 km2`) | 69 | 29 | 42.0% | 49.6% | -7.6 | -1.26 |
| Stratigraphic-age-matched wildcats | 63 | 32 | 50.8% | 51.2% | -0.4 | -0.06 |
| Vertical + tight + stratigraphic-matched | 27 | 13 | 48.1% | 48.0% | +0.1 | +0.01 |

- **Standalone fields vs near-field satellites.** Among redrilled discoveries linked to FactPages `wlbField`, two represent standalone field discoveries (`6506/11-10 Berling` in 2018, relinquished twice by Det norske in 2011 and Centrica in 2015, and `31/7-1 Bestla` in 2016, dropped by Lundin in 2013). Two others are near-field satellites filed under existing field names in FactPages (`6507/4-2 S Adriana` near `DVALIN` and `36/7-5 B` near `DUVA`, where the `DUVA` field itself was discovered earlier by `36/7-4` in 2016).
- **Different-operator share.** Different returning operators account for 75% of redrills, so observing all field-linked hits from different operators is consistent with base rates (roughly 7% under random assignment) rather than statistically significant.
- **Coordinate limitation.** FactPages `wlbEwDecDeg` and `wlbNsDecDeg` record surface wellhead locations rather than reservoir penetration points, which is why the vertical-only and stratigraphic-matched subset (`n = 27`, 48.1% vs 48.0%) is the cleanest test.

---

## 3. P90 to P10 Volume Calibration Against SODIR Reserves

**Bottom line.** Across 10 standalone SODIR discoveries (`discovery_reserves`) matched to tight (`<= 100 km2`) relinquished prospect polygons with pre-drill `[P90, P10]` ranges, **80.0% (8/10) of actual discovered volumes fall inside the stated P90 to P10 interval** (exact theoretical target for an 80% range), with 20.0% above P10, 0.0% below P90, and a median actual-to-pre-drill-mean ratio of 1.11x.

- **Method and scope.** Pre-drill recoverable oil-equivalent `[P90, P10]` distributions were matched to SODIR `discovery_reserves` (`dscRecoverableOe`). Four additional matches to `field_reserves` (`fldRecoverableOE`, including Statfjord Ost, Breidablikk, and Jotun) all sit above single-prospect P10 because field totals aggregate multiple segments and appraisal wells, so they are excluded from the single-prospect coverage rate.
- **Sample-size limit.** With `n = 10` standalone matches, overall coverage is well calibrated, but the sample is too small to test whether operators with ultra-narrow P10/P90 ratios (Wellesley 3.61x, Aker BP 3.94x vs Spirit/Centrica 17.35x, OMV 16.95x) under-cover realized volumes. Testing that requires SODIR's full pre-drill database across non-relinquished licences.

---

## 4. Conditional Findings Inside Relinquished Licences

**Bottom line.** All metrics in this section are **conditional on licence relinquishment**. Because licences with commercial discoveries or growing prospects mostly remain active and never file relinquishment reports, selection bias pushes in-licence outcomes toward lower discovery rates and shrinking volumes.

![Pre-drill fear vs dry-hole killer and basin-adjusted operator Pg residuals](figures/fig2_reservoir_blindspot_and_operators.svg)

![Paired award vs relinquishment volume scatter and risked volume drift histogram](figures/fig3_apa_shrinkage_method.svg)

- **Conditional in-licence discovery rate (`n = 138`).** Within relinquished licences, mean stated pre-drill `Pg` is 27.0% against an 18.1% realized hydrocarbon discovery rate (-8.9 pp, p = 0.0134). This measures disappointment inside dropped licences, not unconditional shelf-wide operator calibration.
- **Conditional award-to-relinquishment volume drift.** Among re-evaluated pairs with both award and relinquishment assessments (`n = 183` mean volume, `n = 165` risked volume), 79.2% shrink in mean volume (median cut -52.0%) and 83.0% lose risked volume (median cut -61.4%). Comparing 2020s against 2010s awards is right-censored because 2020s licences already relinquished are the fastest failures, so decade drift comparisons are omitted.
- **Conditional dry-hole causes (`n = 214` dry holes).** Reservoir absence or quality accounts for 47.6% of documented dry-hole causes against 21.5% of pre-drill top risk ratings, while trap accounts for 5.9% of dry-hole causes against 29.5% of pre-drill top risk ratings. Two selection mechanisms contribute to this gap, trap-risked prospects are frequently dropped undrilled before ever reaching a well, and water-wet good reservoir is often attributed to charge rather than trap failure.
- **Operator Pg spread.** Basin-adjusted stated `Pg` spans 16.5 pp across major operators (`n >= 20`, DNO +9.6 pp and Wintershall Dea +6.7 pp vs Neptune/ENGIE -6.8 pp, ConocoPhillips -5.3 pp, Shell -4.4 pp, and Lundin -4.2 pp). Without unconditional outcomes and play/vintage controls, this reflects reporting style and portfolio mix rather than proven optimism.

---

## 5. DHI Patterns and 18-PDF Extraction Reproducibility

**Bottom line.** Across drilled prospects in the atlas, positive DHI yields a 54.2% technical discovery rate vs 22.6% for negative DHI (p = 5.6e-5), reproducing known NCS DHI behavior (including Barents uplift gas expansion, where positive DHI lifts technical success 2.5x from 26.9% to 68.4% with 84.6% gas-only hits vs 6.7% in the North Sea). Across 18 duplicate joint-licence PDFs independently processed twice by Claude, true VLM map digitizations (`n = 52`, excluding GIS shapefiles) show 0.861 median polygon IoU and 116.8 m median centroid shift.

![DHI discovery rates with Barents gas-only inset and 18-PDF VLM polygon IoU consistency](figures/fig4_dhi_paradox_and_llm_iou.svg)

- **Flat-spot anomaly (unadjusted for multiple testing).** Claimed `flat_spot` prospects hit 28.0% (7/25) overall and 12.5% (1/8) in the North Sea vs 69.0% (29/42) for positive `amplitude_conformance` (unadjusted Fisher p = 0.0018). Because multiple DHI and play contrasts were tested without family-wise correction, treat this as exploratory.
- **Reproducibility vs accuracy.** Measuring inter-run agreement on the 18 duplicate PDFs (100.0% reservoir period, 95.5% exact `Pg`, 92.2% exact volume, 0.861 median VLM polygon IoU) quantifies self-consistency only, not ground-truth accuracy, since repeated runs can share systematic extraction errors. Validating accuracy requires hand-digitized ground truth on a random sample.

---

## Reproducibility

- Shared loader and deduplicator `src/loader.py`
- Reviewer upgrade tests (unique-well shelf baseline, P90 to P10 coverage, live FactMaps Layer 616 open-acreage screen) `analyses/track5_reviewer_upgrades.py`
- Tracks 1 to 4 scripts `analyses/track1_redrilled_graveyard.py`, `analyses/track2_risk_calibration.py`, `analyses/track3_volume_drift_and_prize.py`, `analyses/track4_dhi_plays_and_llm_consistency.py`
- Matplotlib PNG and SVG generator `analyses/generate_figures.py`
