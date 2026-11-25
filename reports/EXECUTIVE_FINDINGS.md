# Executive Summary Screened NCS Relinquished Prospect Inventory and Conditional Audit

**Bottom line.** Joining 738 unique Norwegian Continental Shelf relinquishment reports (5,325 prospects after removing 18 duplicate multi-licence pairs and three 1,000x unit-scaling bugs) against 536 active SODIR licences, the APA gross boundary, and 154 in-service surface host facilities identifies **242 APA-eligible open-acreage prospects (`Pg >= 0.20`, post-award assessed, undrilled, >=50% of the Norwegian slice outside active licences) holding 6.30 Bboe unrisked and 1.95 Bboe risked**. Within that inventory, **178 prospects (1.31 Bboe risked) are Tier A commercial or non-technical drops**, **90 prospects (0.63 Bboe risked) lie within 30 km of a fluid-compatible surface host**, and **four core Tier A gas prospects within 52 to 71 km of Aasta Hansteen total 457.1 MMboe unrisked (192.8 MMboe risked)**.

## 1. Open-Acreage Inventory Highlights

- **Filter hierarchy.** 408 georeferenced post-award undrilled prospects (`Pg >= 0.20`, excluding already-redrilled targets and straddling duplicates) split into **242 APA-eligible open prospects (1.95 Bboe risked)**, 1 non-APA open prospect, and 165 re-licensed prospects.
- **Norwegian-sector clipping.** Polygons are clipped to the Norwegian sector before computing open share so foreign median-line acreage (such as the UK portion of Edinburgh, ~67% Norwegian polygon area / ~22% Norwegian volume) never counts as open Norwegian ground.
- **Fluid-aware surface hosts.** Gas prospects exclude oil-only gas-reinjection FPSOs (such as Goliat and Johan Castberg); only surface facilities are included (subsea templates and pipeline tie-ins excluded).
- **Aasta Hansteen Voring cluster.** Kelvin (64.7 MMboe risked, 52.3 km), Fjellflokk Far East 1 (52.5 MMboe, 65.4 km), Svartbakkestjerne Springar (49.6 MMboe, 71.0 km), and Birkeland (26.0 MMboe, 51.9 km) total **457.1 MMboe unrisked / 192.8 MMboe risked** (shared Cretaceous play risk applies).

## 2. Redrills and Maturity-Controlled Regression

- **Shelf share.** Since 2013, **77 of 401 completed NCS wildcat parent wells (19.2%)** were drilled inside a previously relinquished prospect polygon (4 additional uncompleted wells with `wlbCompletionYear == 0` excluded).
- **Maturity-controlled regression (`n = 401`, `2013+`).** Main-effects logistic regression shows **no significant overall redrill penalty** (OR = 0.76, p = 0.33; `log1p(dist_km)` OR = 0.58, p < 0.0001; reconciled binned 42.9% vs 52.0%, -9.1 pp, z = -1.60).
- **Near-field interaction.** Adding `is_redrill x log1p(dist_km)` reveals a robust **near-field penalty that fades with distance** (coef = +0.98, p = 0.0018; p = 0.0011 capped at 40 km; p = 0.0116 dropping all wells beyond 40 km, non-redrill distance OR = 0.48). Near-field (`<= 15 km`) redrills hit **44.1% vs 60.9% (-16.9 pp, z = -2.65)**, holding across nested 10, 15, 20, and 30 km cutoffs (-15.8 to -23.0 pp), while mid-field (`n = 13`) and frontier (`n = 5`) redrills cannot be distinguished from peers.
- **Outcome-blind stratigraphic check.** Using `wellbore_formation_top` (60 matches) with `wlbAgeAtTd` fallback only when a well has zero tops (14 matches) yields 41.9% vs 47.9% maturity baseline (z = -1.04).
- **Standalone fields vs satellites.** Berling (`6506/11-10`, 2018) and Bestla (`31/7-1`, 2016) are standalone field discoveries; Dvalin Nord (`6507/4-2 S`) and Cerisa West (`36/7-5 B`) are near-field satellites.

## 3. Conditional Patterns Inside Relinquished Licences

All metrics below are strictly **conditional on licence relinquishment** and reflect selection of disappointing licences rather than unconditional shelf-wide performance.

- **Conditional in-licence rate (`n = 138`).** Mean stated pre-drill `Pg` 27.0% vs 18.1% realized hydrocarbon discovery rate (-8.9 pp, p = 0.0134).
- **Conditional award-to-relinquishment drift.** Among re-evaluated pairs (`n = 183` mean volume, `n = 165` risked volume), 79.2% shrink in mean volume (median -52.0%) and 83.0% lose risked volume (median -61.4%).
- **Conditional dry-hole causes (`n = 214`).** Reservoir accounts for 47.6% of documented dry-hole causes vs 21.5% of pre-drill top risk ratings, while trap accounts for 5.9% vs 29.5% (reflecting both undrilled trap drop selection and charge vs trap diagnosis bias).
- **Exploratory P90 to P10 note (`n = 10` standalone `discovery_reserves`).** 8 of 10 (80.0%, 95% Wilson CI 49% to 94%) fall inside stated `[P90, P10]`, median actual-to-mean 1.11x (small sample, discovery selection, post-shrinkage vintage).
- **DHI and 18-PDF self-consistency.** Positive DHI yields 54.2% vs 22.6% for negative DHI (p = 5.6e-5; Barents 2.5x technical lift with 84.6% gas-only hits vs 6.7% North Sea). Flat-spot contrast (28.0% vs 69.0% positive amplitude conformance) is unadjusted for multiple testing. Across 18 duplicate PDFs, independent VLM map digitizations (`n = 52`) show 0.861 median polygon IoU and 116.8 m median centroid shift (self-consistency only, not ground-truth accuracy).

## Detailed Files

- Full BLUF writeup `reports/WRITEUP.md`
- Interactive summary dashboard `reports/ncs_atlas_discoveries.html`
- Reproducible scripts `analyses/track1_redrilled_graveyard.py` through `analyses/track7_reconcile_and_logit.py`
