# Track 1: The Relinquished-Then-Discovered Graveyard

## Scope and Methodology

- **Atlas corpus**: 756 Norwegian Continental Shelf (NCS) relinquishment reports deduplicated to **738 unique licence reports** (18 multi-licence duplicate pairs removed via `deduplicate_records`), containing **5,325 prospects/leads**, of which **3,476** have mapped GeoJSON `Polygon`/`MultiPolygon` geometries (`layer` in `{"prospect", "lead"}`).
- **Wellbore dataset**: 2,149 completed exploration wells from SODIR FactPages (`wellbore_exploration_all.parquet`) with valid coordinates and completion year (`wlbStatus != "WILL NEVER BE DRILLED"`).
- **Spatial & temporal join**: Exact pure-Python ray-casting point-in-polygon (handling exterior and interior rings) matching GeoJSON prospect/lead polygons against SODIR exploration wells strictly post-relinquishment (`wlbCompletionYear > report_year`).
- **Primary cohort**: Strictly **undrilled** relinquished prospects/leads (`status_at_report` excluding `drilled_discovery`, `discovery_marginal`, and `drilled_dry`) penetrated by later **wildcat** (`wlbPurpose == "WILDCAT"`) wells with known hydrocarbon outcome (`OIL`, `GAS`, `OIL/GAS`, `GAS/CONDENSATE`, `OIL/GAS/CONDENSATE` vs `DRY`/shows/water). Already-drilled-dry prospects are tracked separately as resurrections.
- **Internal atlas enrichment cross-check**: Only **18** prospects in the deduplicated atlas contain an internal `qc_flags` note mentioning a SODIR wellbore inside their outline; the full geometric spatial join uncovers **130 undrilled relinquished prospects/leads** (192 raw feature-well hits) drilled by **87 unique wildcat wells** after relinquishment.

---

## Key Headline Findings

### 1. Discovery Rate vs Pre-Relinquishment Stated `Pg`

| Cohort | Prospects Redrilled | Prospects Discovered | Prospect Discovery Rate | Unique Wells | Unique Well Discovery Rate | Unique Named Discoveries | Producing / Approved Fields |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Undrilled -> Later Wildcat (Primary)** | **130** | **65** | **50.0%** | **87** | **42.5%** (37/87) | **36** | **4** (`BERLING`, `BESTLA`, `DUVA`, `DVALIN`) |
| Undrilled -> All Exploration (Wildcat + Appraisal) | 133 | 68 | 51.1% | 110 | 50.0% (55/110) | 39 | 6 |
| Previously `drilled_dry` -> Later Wildcat | 6 | 3 | 50.0% | 6 | 50.0% (3/6) | 3 | 0 |

Among the **86 undrilled redrilled prospects with a stated pre-relinquishment `Pg`**:
- **Actual discovery rate**: **46.5%** (40/86)
- **Mean stated pre-relinquishment `Pg`**: **24.0%** (median **19.0%**)
- **Calibration ratio (actual / stated)**: **1.94x** (two-sided binomial $p = 1 \times 10^{-6}$)
- **Original `Pg` still discriminates winners from losers**: Prospects that became discoveries had a mean pre-relinquishment `Pg` of **31.5%**, nearly double the **17.4%** mean `Pg` of prospects that later drilled dry.

| Stated `Pg` Bucket | Redrilled Prospects | Discoveries | Actual Discovery Rate | Mean Stated `Pg` |
|---|---:|---:|---:|---:|
| `< 10%` | 13 | 4 | **30.8%** | 5.4% |
| `10–20%` | 30 | 12 | **40.0%** | 13.5% |
| `20–30%` | 19 | 6 | **31.6%** | 23.1% |
| `30–50%` | 18 | 12 | **66.7%** | 37.8% |
| `>= 50%` | 6 | 6 | **100.0%** | 78.0% |

*Methodological note*: The 130 redrilled prospects represent a heavily selected 3.7% subset of the 3,476 mapped polygons. The 1.94x outperformance over stated `Pg` therefore reflects both **re-licensing selection alpha** (new 3D seismic, revised geological models, near-field tieback economics) and **conservative/outdated pre-relinquishment risking**—while the strong monotonic separation between discoveries (31.5% mean `Pg`) and dry holes (17.4% mean `Pg`) shows original operator risk rankings retained real predictive signal.

---

### 2. Different Operator vs Same Operator Returning

| Comparison Basis | Returning Operator | Sample | Discoveries | Discovery Rate | Became Field | Mean Stated `Pg` | Two-Prop $z$ ($p$) |
|---|---|---:|---:|---:|---:|---:|---:|
| **Prospect-level (lineage-normalized)** | **Different operator** | **97** | **52** | **53.6%** | **9** | 24.6% | $z = 1.41$ ($p = 0.158$) |
| **Prospect-level (lineage-normalized)** | **Same operator** | **33** | **13** | **39.4%** | **0** | 22.2% | |
| Prospect-level (canonical entity only) | Different operator | 100 | 52 | 52.0% | 9 | 24.6% | $z = 0.83$ ($p = 0.405$) |
| Prospect-level (canonical entity only) | Same operator | 30 | 13 | 43.3% | 0 | 22.1% | |
| **Unique-well-level (lineage-normalized)** | **Different operator** | **64** | **29** | **45.3%** | — | — | $z = 0.88$ ($p = 0.381$) |
| **Unique-well-level (lineage-normalized)** | **Same operator** | **23** | **8** | **34.8%** | — | — | |

Across every definition, **fresh eyes outperform**: different operators returning to relinquished acreage achieve a **+10.5 to +14.2 percentage-point higher discovery rate** than the same operator (or corporate successor) returning, and **100% of the field-making discoveries (9/9 prospect matches across `BERLING`, `BESTLA`, `DUVA`, `DVALIN`) were drilled by a different operator** than the one that walked away. (The gap is directionally consistent across all specifications, though not statistically significant at $p < 0.05$ on wildcats alone; when including all exploration wells, lineage-normalized different vs same reaches 56.0% vs 36.4%, $p = 0.050$.)

---

### 3. What Scared the Original Operator Off? (False-Negative Killers vs True Risks)

Comparing `conclusion.reasons_not_drilled` and `key_risks` on the 65 **discovered** vs 65 **dry** redrilled prospects reveals a sharp divide between **commercial/structural walk-aways** (which frequently turned into discoveries) and **charge/migration/seal warnings** (which were usually right):

| Reason Not Drilled (`conclusion`) | Cited on Discoveries ($n=65$) | Cited on Dry Holes ($n=65$) | Discovery Rate When Cited | Atlas Undrilled Baseline |
|---|---:|---:|---:|---:|
| **`commercial`** | 24 (36.9%) | 14 (21.5%) | **63.2%** | 22.6% |
| **`trap_risk`** | 13 (20.0%) | 8 (12.3%) | **61.9%** | 13.2% |
| **`volume_too_small`** | **30 (46.2%)** | 24 (36.9%) | **55.6%** | 42.5% |
| `reservoir_risk` | 18 (27.7%) | 20 (30.8%) | 47.4% | 23.8% |
| `high_risk` | 23 (35.4%) | 35 (53.8%) | 39.7% | 43.9% |
| `charge_risk` | 5 (7.7%) | 8 (12.3%) | **38.5%** | 15.7% |
| `seal_risk` | 11 (16.9%) | 20 (30.8%) | **35.5%** | 11.2% |
| `migration_risk` | 6 (9.2%) | 15 (23.1%) | **28.6%** | 12.0% |

Among structured `key_risks.element` tags on future discoveries, **`reservoir_quality`** (9, 13.8%), **`trap`** (9, 13.8%), and **`reservoir_presence`** (9, 13.8%) were cited most frequently, while `trap_seal` (33.3% hit rate) and `migration` / `lateral_fault_seal` (40.0% hit rate) were the most predictive of actual dry holes.

---

## Top 10 "Ones That Got Away"

Ranked by commercial field outcome (`wlbField`), discovery wellbore status, tight polygon match, and pre-relinquishment mean volume (`MSm3 o.e.` / `MMboe`):

| # | Relinquished Prospect (Licence, Operator, Year) | Pre-Relinq `Pg` & Mean Vol | Why Original Operator Walked Away | Later Discovery Well (Operator, Year) | Outcome & Field |
|---:|---|---|---|---|---|
| 1 | **Hades** (PL477, Centrica Resources, 2015) — *also dropped earlier as **Siggjo** (PL256, Det norske, 2011; `Pg=20%`, 11.8 MSm3 / 74.2 MMboe)* | Not stated in PL477 (`20%`, 11.8 MSm3 in PL256) | PL477 concluded *"no drillable candidates left"*; PL256 cited `high_risk` / `seal_risk` (`trap_seal`) | **6506/11-10** (OMV (Norge) AS, 2018) | **GAS/CONDENSATE** — `6506/11-10 Berling` -> **BERLING** field |
| 2 | **Yngling** (PL576, Lundin Norway AS, 2013; 8.0 km²) | `>20%` (text), vol not tabulated | `commercial`, `volume_too_small`: *"chance of success >20%, but volumes are too small to be commercially interesting"* | **31/7-1** (Faroe Petroleum Norge AS, 2016) | **OIL/GAS** — `31/7-1 Bestla` -> **BESTLA** field |
| 3 | **Sabina** (PL647, Maersk Oil Norway AS, 2014; 119.8 km²) | `Pg = 36%`, vol not tabulated | `segmented`, `high_risk`, `reservoir_risk`, `volume_too_small`: split into separate prospects straddling PL211/PL647 | **6507/4-2 S** (Wintershall Dea Norge AS, 2021) | **OIL/GAS/CONDENSATE** — `6507/4-2 S (Dvalin Nord)` -> **DVALIN** field |
| 4 | **Jotne** (PL686, A/S Norske Shell, 2015; 378.0 km² regional polygon) | `Pg = 9%`, **25.0 MSm3** (157.3 MMboe) | `high_risk`, `seal_risk`, `trap_risk`, `volume_too_small`: *"low POS on seal, no depth-conform contact, little AVO support"* | **36/7-5 B** (Vår Energi Norge AS, 2024) | **OIL** — `36/7-5 B (Cerisa West)` -> **DUVA** field |
| 5 | **Andotten** (PL768, Wintershall Norge AS, 2019; 26.3 km²) | `Pg = 15%`, **65.1 MSm3** (409.5 MMboe) | `charge_risk`, `migration_risk`, `trap_risk`, `high_risk`: trap effectiveness & charge/migration deemed too high | **7122/9-2** (Vår Energi ASA, 2025) | **GAS** — `7122/9-2 (Elgol)` (Barents Sea Permian gas) |
| 6 | **Celsius** (PL694, DEA Norge AS, 2017; 17.1 km²) | `Pg = 39%`, **26.3 MSm3** (165.4 MMboe) | `commercial`, `dependency_on_infrastructure`, `portfolio_strategy`: *"DEA wanted to drill Celsius in 2015"* but gas economics were marginal | **6607/3-1 S** (OMV (Norge) AS, 2023) | **GAS** — `6607/3-1 S (Velocette)` (Nise Fm) |
| 7 | **Toutatis** (PL656, DEA E&P Norge AS, 2016; 29.3 km²) | `Pg = 27%`, **25.7 MSm3** (161.7 MMboe) | `commercial`, `high_risk`, `seal_risk`: **partner veto** — *"despite technical recommendation from operator to drill, partnership unable to reach agreement"* | **6611/1-1** (DEA Norge AS, 2019) | **OIL** — `6611/1-1 (Toutatis)` (same operator returned 3 yrs later!) |
| 8 | **Balderbrå** (PL522, BG Norge AS, 2014; 40.3 km²) | `Pg = 37%`, **25.2 MSm3** (158.5 MMboe) | Reservoir effectiveness risk & partnership concluded *"not economically viable"* | **6604/5-1** (Wintershall Norge AS, 2018) | **GAS** — `6604/5-1 (Balderbrå)` |
| 9 | **Warka** (PL799, PGNiG Upstream International AS, 2017; 56.2 km²) | `Pg` not stated, **13.9 MSm3** (87.4 MMboe) | **Partner veto**: *"Operator recommended to drill Warka; licence partners did not support the drill decision and licence was surrendered"* | **6507/4-1** (ConocoPhillips Skandinavia AS, 2020) | **GAS** — `6507/4-1 (Warka)` |
| 10 | **Alfa** (PL525, Noreco / Hess Norge AS, 2013; 31.0 km²) | `Pg = 32%`, **10.0 MSm3** (62.9 MMboe) | `commercial`, `volume_too_small`: *"many small gas segments in the Fles area; licence relinquished for lack of a partner"* | **6605/6-1 S** (OMV (Norge) AS, 2024) | **GAS** — `6605/6-1 S` (Springar Fm) |

*Notable honorable mentions*: **Karma** (PL550, Tullow, 2016, `Pg=36%`, 4.8 MSm3 -> **31/1-2 S Røver Nord**, Equinor, 2021, OIL/GAS), **Dobby** (PL348C, Statoil, 2016, `Pg=69%`, 2.2 MSm3 -> **6407/8-8 S Calypso**, Neptune, 2022, OIL/GAS), **Svimse / Sebastian** (PL571, Suncor, 2017 -> **25/7-8 S Enniberg**, ConocoPhillips, 2020, OIL/GAS, partner disagreement), **Herzer** (PL597, VNG, 2013, `Pg=41%`, 14.5 MSm3 -> **6506/5-1 S Nidhogg**, Aker BP, 2020, GAS, partner veto), and **Otra / Freki** (PL861/PL567 -> **2/6-7 S Othello**, DNO, 2024, OIL).

### Bonus: "Drilled Dry, Walked Away, Later Discovered" (3 Resurrections)
Three prospects marked `drilled_dry` at relinquishment were later re-drilled by wildcats inside the same polygon and yielded discoveries (3/6 = 50.0%):
1. **Salander** (PL650, DEA E&P, 2017) -> `6507/3-15` (Aker BP, 2022, OIL/GAS)
2. **Kopervik** (PL625, Lundin, 2016) -> `16/1-34 S (Lillefix)` (Lundin, 2021, OIL)
3. **Clapton** (PL440S, Faroe Petroleum, 2013) -> `2/8-19 (Overly)` (Aker BP, 2022, OIL/GAS)

---

## Reproducibility

- Script: `C:\Users\philip\Documents\ncs-relinquished-atlas\analyses\track1_redrilled_graveyard.py`
- Structured JSON output: `C:\Users\philip\Documents\ncs-relinquished-atlas\analyses\track1_findings.json`
- Run command: `uv run --project C:\Users\philip\Documents\wellbore-completion python C:\Users\philip\Documents\ncs-relinquished-atlas\analyses\track1_redrilled_graveyard.py`
