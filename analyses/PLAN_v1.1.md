# Pre-Registration Plan v1.1

All models, outcomes, thresholds, clustering variables, bootstrap specifications, and audit seeds are specified below prior to executing `analyses/track8_inference_and_rerisk.py`. All pre-registered results will be reported in `reports/WRITEUP.md`, including null or weakened findings. Any deviation forced by data availability will be documented in a `Deviations` section.

## Step 1. Cluster-Robust Inference on Redrill Regressions

- **Sample:** All completed NCS wildcat parent wells (`wlbPurpose == WILDCAT`, `wlbCompletionYear >= 2013`, excluding `wlbCompletionYear == 0`, valid coordinates and basin in North Sea, Norwegian Sea, or Barents Sea; target `n = 401`, `77` redrills).
- **Models:**
  - Model 1 (main effects): `outcome ~ is_redrill + log1p(dist_km) + C(basin) + C(yr5)`
  - Model 2 (interaction): `outcome ~ is_redrill + log1p(dist_km) + is_redrill:log1p(dist_km) + C(basin) + C(yr5)`
- **Standard errors (three versions reported per coefficient):**
  1. Naive (unclustered MLE).
  2. Cluster-robust by relinquished `licence_id` (each non-redrill wildcat is its own singleton cluster; if a redrill well hits multiple relinquished licences, assign the chronologically most recent relinquished licence).
  3. Cluster-robust by NCS quadrant (leading block/quadrant token before `/` in `wlbWell`, e.g., `6605`, `34`, `7122`).
- **Small-cluster bootstrap:** Whenever the number of clusters is `< 50`, run a wild cluster bootstrap (Rademacher weights `{-1, +1}`, `9,999` draws, fixed seed `42`, applied to a linear probability / score wild cluster bootstrap specification) and report its two-sided p-values.
- **Headline rule:** Report the most conservative valid p-value across the three SE estimators (and wild cluster bootstrap where `< 50` clusters). If the interaction loses significance at `p < 0.05`, state so directly in the bottom line.

## Step 2. Decision-Relevant Outcomes

Fit Model 1 and Model 2 identically across three binary outcomes:

1. **Technical discovery:** `wlbContent` contains `OIL`, `GAS`, or `COND` and does not contain `SHOW` (full `2013+` sample).
2. **Material discovery:** Technical discovery AND SODIR recoverable volume `>= 3.0 MSm3 o.e.` (from `discovery_reserves.dscRecoverableOe` or `field_reserves.fldRecoverableOE` via the discovery wellbore). Pre-registered sensitivity thresholds: `1.0 MSm3 o.e.` and `5.0 MSm3 o.e.`.
3. **Commercial discovery:** Discovery is linked to a named SODIR field (`fldName` non-null) OR `dscCurrentActivityStatus` in `{"PRODUCING", "APPROVED FOR PRODUCTION", "PLANNING PHASE", "DEVELOPMENT LIKELY", "PRODUCTION IS LIKELY, BUT UNCLARIFIED"}` (exact SODIR status strings logged in output). Restricted strictly to parent wells completed in **`2021` or earlier** (`2013 <= wlbCompletionYear <= 2021`) so recent discoveries have at least 4 to 5 years to mature.

## Step 3. Incumbent-Information Test

- **Variable:** `incumbent = 1` if the drilling operator (`wlbDrillingOperator`, normalized for corporate lineage/mergers) held an operator or licensee interest in the licence of the nearest prior discovery at the wildcat's spud/entry year (`wlbEntryYear`, falling back to `wlbCompletionYear`), determined from SODIR `licence_licensee_hst` and `licence_oper_hst`. Otherwise `0`.
- **Model 3 (Incumbency + Interaction):** Add `incumbent` and `is_redrill:incumbent` to Model 2 across all three SE specs (naive, licence-clustered, quadrant-clustered, plus wild cluster bootstrap if `< 50` clusters).
- **Decision rule:** Report whether the near-field redrill penalty (`is_redrill` and `is_redrill:log1p(dist_km)`) survives controlling for `incumbent`, and explicitly evaluate Hypothesis A ("operators retain the best structures") vs Hypothesis B ("incumbents hold superior local information").

## Step 4. Dry-Hole Cause Reconciliation with SODIR

- **SODIR 3-category mapping:**
  - `Reservoir` = reservoir presence + reservoir quality.
  - `Charge` = source presence + maturity + migration.
  - `Trap` = closure + top seal + lateral seal (`seal_risk` / `retention` maps to `Trap`).
- **Weighting:** Equal fractional weights (`1/k`) when a dry hole cites `k` distinct failure categories, matching SODIR methodology.
- **Window and benchmark:** Restrict to wildcat dry holes completed `2007 to 2019` and compare by basin (North Sea, Norwegian Sea, Barents Sea) against SODIR Resource Report 2020, Fact box 3.4 (North Sea: Source 47%, Trap 29%, Reservoir 24%, plus Norwegian Sea and Barents Sea figures cited by page).
- **Manual audit:** Draw a fixed-seed (`seed = 42`) random sample of `20` dry holes, check extracted failure categories against the raw source report text/quotes in the JSON, and report category agreement rate.

## Step 5. Re-Risking Inventory Against Redrill Outcomes

- **Calibration set:** Completed redrill parent wells matched to a relinquished prospect with stated `Pg`. If a well penetrates multiple polygons, select the prospect whose `reservoir.chrono.period` matches the well's penetrated formation tops; if multiple still match, take the mean stated `Pg`.
- **Outcome:** Hydrocarbons discovered in the target stratigraphic period (`wlbAgeWithHc1..3` matching `reservoir.chrono.period`, used strictly as the outcome variable, not as a selection filter).
- **Stratification and CI:** Compute `observed / mean_stated_Pg` separately for near-field (`<= 15 km` to prior discovery) and far-field (`> 15 km`) redrills with `9,999`-draw bootstrap 95% CIs (`seed = 42`).
- **Application rule:** Apply a calibration multiplier to inventory `Pg` ONLY if its 95% CI excludes `1.0`. Otherwise retain unadjusted `Pg` and report the 95% CI band.

## Step 6. Data-Driven Economic Screen

- **Empirical dataset:** SODIR discoveries that reached PDO approval (or entered production / `APPROVED FOR PRODUCTION`) since `2010`, paired with their recoverable volume (`MSm3 o.e.`) and Haversine distance to their tie-in/host surface facility, split separately for **oil** (oil / oil-gas) and **gas** (gas / gas-condensate).
- **Envelope:** Fit an empirical lower envelope via quantile regression (`tau = 0.10`, `log(volume) ~ distance_km`, or 10th percentile by distance bin if sample size `< 15` for a fluid).
- **Flag:** Flag every APA-open inventory prospect whose unrisked mean volume falls below the `tau = 0.10` envelope for its fluid type and nearest fluid-compatible host distance. Report flagged count and risked volume removed.

## Step 7. Changed-Circumstances Screen

- **Scope:** Tier A APA-open prospects whose drop reasons or conclusion cite infrastructure, host, distance, or capacity constraints.
- **Dual distance computation:**
  1. `dist_at_relinq_km`: nearest fluid-compatible surface host with `fclStartupDate <= report_year`.
  2. `dist_now_km`: nearest fluid-compatible in-service surface host OR field with status `APPROVED FOR PRODUCTION` (using facility or field coordinates).
- **Flag rule:** Flag prospects where `dist_at_relinq_km - dist_now_km >= 20 km` OR distance crossed from `> 50 km` at relinquishment to `<= 50 km` now. List each flagged prospect with the new host and startup/approval year.

## Step 8. Inventory Additions and Tier A Audit

- **New columns (saved to `reports/open_acreage_inventory.csv` and `reports/open_acreage_inventory.geojson`):**
  - `years_open`: `2026 - relinq_year`
  - `apa_rounds_since`: integer count of annual APA rounds elapsed since relinquishment year (`max(0, 2025 - relinq_year)` if APA 2025 is reflected, logged explicitly against FactMaps snapshot date).
  - `nearby_awards_since`: count of SODIR production licences granted strictly after `relinq_year` whose geometry or centroid lies within `20 km` of the prospect centroid.
  - `host_end_year`: planned cessation / end-of-life year for the top 10 hosts from public operator/SODIR statements with cited source; `"unknown"` otherwise.
- **Tier A manual audit:** Draw a fixed-seed (`seed = 42`) random sample of `30` Tier A prospects, verify drop-reason classification against source conclusion/quote text, report agreement %, reclassify errors, and update Tier A / Tier B totals.
- **Snapshot disclosure:** Record exact FactPages and FactMaps pull dates and whether APA 2025 awards (awarded Jan 2026) appear in the active licence snapshot.

## Step 9. Write-Up Structure

- Move P90 to P10 coverage to an Appendix contrasted with SODIR's look-back (2 of 10 discoveries inside stated P90 to P10).
- Update operator Pg spread with current corporate successors (`Lundin -> Aker BP`, `Wintershall Dea -> Harbour Energy`, `Neptune -> Var Energi`).
- Rebuild top-prospect table with `re_risked_pg`, `economic_flag`, `changed_circumstances_flag`, `years_open`, `nearby_awards_since`, and `host_end_year`.
- Rewrite bottom line strictly from Step 1 to 8 results. Preserve style constraints (`0` colons, `0` em/en dashes, `0` occurrences of `exact`).
