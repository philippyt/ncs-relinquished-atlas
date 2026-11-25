# Track 3: The Incredible Shrinking Prospect (APA Application Optimism Tax) & The Untested NCS Prize

Reproducible script: [track3_volume_drift_and_prize.py](file:///C:/Users/philip/Documents/ncs-relinquished-atlas/analyses/track3_volume_drift_and_prize.py)  
Structured data output: [track3_findings.json](file:///C:/Users/philip/Documents/ncs-relinquished-atlas/analyses/track3_findings.json)

## Dataset & Data-Quality Controls
- **Corpus:** 756 raw relinquishment reports -> **738 deduplicated licences** (18 multi-licence duplicate pairs removed via `deduplicate_records`), containing **5,325 prospects** (`4,762` undrilled, `563` drilled/discoveries).
- **Volume normalization:** All recoverable unrisked volumes converted to `1e6 Sm3 o.e.` (`MSm3 o.e.`) via `safe_canonical_volume_msmo3` (protecting against the PL531/PL1019 1,000x unit-scale bugs), plus an additional 1,000x unit-scale fix discovered in **PL883 (Tåren East condensate)** where `0.75` and `0.89 MSm3` were mistyped as `1e9Sm3` (`factor = 1000.0`).
- **Prize de-duplication:** Child segments (`parent_prospect_id` present in same licence) are excluded from totals, proven/appraisal `Pg = 1.0` segments (`Titan-SE`, PL420) are excluded from the exploration prize, and straddling duplicates across adjacent licences (e.g., `Celsius` in `PL653 / PL694`) are merged once.

---

## 1. The APA Application Optimism Tax (Award/Application -> Relinquishment Drift)

When operators move from APA/round application estimates to post-award 3D seismic re-mapping and relinquishment assessments, both **volume** and **geological chance of success (`Pg`)** suffer systematic, compounding deflation.

### Headline Paired Drift
| Cohort | Metric | `n` | % Shrank / Dropped | % Unchanged | % Grew / Increased | Median Ratio (`Final/Init`) | Geom. Mean Ratio | Portfolio Ratio (`Sum Final/Init`) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **All paired** | Mean Volume | 248 | **58.5%** | 26.2% | 15.3% | **0.748** (-25.2%) | 0.560 | **0.587** (`3,909 -> 2,295 MSm3`) |
| **Re-evaluated only** | Mean Volume | 183 | **79.2%** | 0.0% | 20.8% | **0.480** (-52.0%) | **0.456** | **0.540** (-46.0%) |
| **All paired** | P50 Volume | 27 | **77.8%** | 0.0% | 22.2% | **0.479** (-52.1%) | 0.457 | **0.403** (-59.7%) |
| **All paired** | `Pg` | 337 | **54.0%** | 24.9% | 21.1% | **0.874** (`-2.2 pp` med / `-2.8 pp` mean) | 0.779 | Mean `25.1% -> 22.3%` |
| **Re-evaluated only** | `Pg` | 253 | **71.9%** | 0.0% | 28.1% | **0.727** (`-6.0 pp` med / `-3.8 pp` mean) | 0.713 | Mean `23.8% -> 20.0%` |
| **All paired** | Risked Volume (`Pg * Mean`) | 217 | **63.1%** | 24.0% | 12.9% | **0.612** (-38.8%) | 0.472 | **0.517** (`640.2 -> 331.3 MSm3`) |
| **Re-evaluated only** | Risked Volume (`Pg * Mean`) | 165 | **83.0%** | 0.0% | 17.0% | **0.386** (-61.4%) | **0.371** | **0.485** (-51.5%) |
| **Undrilled only** | Mean Volume / `Pg` / Risked | 223 / 295 / 196 | 57.4% / 56.9% / 63.3% | — | — | **0.769** / `-3.7 pp` / **0.603** | — | **0.579** / `22.1%->18.1%` / **0.469** |

**Key takeaway:** Among prospects actually re-mapped after award (excluding untouched carry-overs), **nearly 4 in 5 (79.2%) shrink in volume** by a **median cut of 52%**, and **71.9% lose `Pg`** (median `-6.0 pp`). Compounded together, **83.0% lose risked volume**, with the median prospect losing **61.4% of its risked resource**.

### Basin Breakdown: The Mature-Basin Paradox
| Basin | All Paired Vol (`n`, % Shrank, Med, Port) | Re-evaluated Vol (`n`, % Shrank, Med, Port) | Re-evaluated `Pg` (`n`, % Drop, Mean Diff) |
|---|---|---|---|
| **North Sea** | `n=82`, 72.0%, `0.499`, `0.433` | `n=71`, **83.1%**, **0.392** (-60.8%), **0.373** | `n=117`, **80.3%**, **-7.6 pp** |
| **Norwegian Sea** | `n=95`, 68.4%, `0.633`, `0.681` | `n=76`, **85.5%**, **0.481** (-51.9%), **0.647** | `n=111`, 61.3%, `+0.5 pp` |
| **Barents Sea** | `n=71`, 29.6%, `1.000`, `0.604` | `n=36`, **58.3%**, **0.815** (-18.5%), **0.548** | `n=25`, **80.0%**, **-4.7 pp** |

Counter-intuitively, the **North Sea** — the most data-dense basin on the NCS — exhibits the **harshest optimism tax**: re-evaluated North Sea prospects lose **60.8% at the median** (`62.7%` portfolio-wide) and **80.3% drop in `Pg`** (`-7.6 pp`). In the Barents Sea, ~49% of paired entries are carried over unchanged from application (e.g., PL966), masking a `-45.2%` portfolio shrinkage among re-evaluated structures.

### Time-Period Trend: Modern 3D Seismic Increased Shrinkage
| Award Decade | Mean Vol `n` | % Shrank | Median Ratio | Portfolio Ratio | `Pg` `n` | Mean `Pg` Shift |
|---|---:|---:|---:|---:|---:|---:|
| **2000s (`<=2009`)** | 13 | 53.8% | 0.571 | 0.425 | 27 | `-1.4 pp` (`36.5% -> 35.0%`) |
| **2010s (`2010-2019`)** | 164 | 56.7% | 0.765 | 0.621 | 229 | `-2.2 pp` (`23.3% -> 21.1%`) |
| **2020s (`>=2020`)** | 71 | **63.4%** | **0.679** | **0.479** (-52.1%) | 81 | **-5.1 pp** (`26.6% -> 21.5%`) |

Modern broadband 3D reprocessing and quantitative interpretation (QI/AVO) have **not** eliminated APA optimism — instead, shrinkage **worsened** in the 2020s (`-52.1%` portfolio volume cut and `-5.1 pp` mean `Pg` drop, more than double the 2010s `Pg` drop). Licences explicitly reporting new/reprocessed 3D seismic (`n = 222`) see `60.8%` shrink (median `0.702`, portfolio `0.582`), with `78.5%` shrinking among re-evaluated structures.

### Major Operator Comparison (`n_vol >= 8`)
| Operator | All Paired Vol (`n`, Med, Port) | Re-evaluated Vol (`n`, % Shrank, Med) | `Pg` (`n`, Mean Diff) |
|---|---|---|---|
| **Equinor (incl. Statoil)** | `n=67`, `1.000`, `0.500` | `n=31`, **80.6%**, **0.366** | `n=71`, `-2.5 pp` |
| **Aker BP (incl. Det norske)** | `n=36`, `0.513`, `0.486` | `n=36`, **69.4%**, **0.513** | `n=36`, `-3.0 pp` |
| **DNO (incl. Faroe)** | `n=26`, `0.850`, `0.709` | `n=17`, **88.2%**, **0.467** | `n=27`, `+1.1 pp` |
| **OKEA** | `n=13`, `0.750`, `0.614` | `n=11`, **90.9%**, **0.686** | `n=18`, **-8.1 pp** |
| **Lundin** | `n=12`, `0.702`, `0.445` | `n=7`, **100.0%**, **0.414** | `n=16`, **-7.2 pp** |
| **Wintershall Dea** | `n=9`, `0.570`, `0.546` | `n=9`, **77.8%**, **0.570** | `n=12`, `-3.1 pp` |
| **Shell** | `n=8`, `0.643`, `0.328` | `n=7`, **71.4%**, **0.633** | `n=9`, `+4.0 pp` |
| **TotalEnergies (incl. Maersk)** | `n=8`, `0.494`, `0.581` | `n=7`, **100.0%**, **0.480** | `n=14`, `+2.3 pp` |

**Notable extreme collapses:** `Røros` (PL904, North Sea, MOL: `70.55 -> 1.99 MSm3`, `-97.2%`), `Monadhliath` (PL862, North Sea, Shell: `109.4 -> 5.38 MSm3`, `-95.1%`, `Pg 12% -> 5%`), `Tromtind Lower Norian` (PL1026, Barents Sea, Aker BP: `35.6 -> 3.43 MSm3`, `-90.4%`).  
**Rare big growers:** `Kamskjell` (PL640, Norwegian Sea, Repsol: `76.8 -> 312.2 MSm3`, `4.07x`), `Balderbrå` (PL522, Norwegian Sea, BG Norge: `11.4 -> 25.2 MSm3`, `2.21x`, `Pg 25% -> 37%`).

---

## 2. Why Operators Really Walk Away

### Undrilled Prospects (`n = 4,762` of 5,325 total; 563 drilled/discoveries)
- **Both Geological Risk + Sub-Commercial Size ("too small for the risk"):** **40.2%** (`1,912`)
- **Geological / Technical Risk Only:** **35.6%** (`1,693`)
- **Purely Commercial / Too Small (no geological risk tag):** **12.3%** (`586`)
- **Purely Non-Technical / Outside-Licence / Strategic:** **4.3%** (`203`)
- **Other / Unspecified:** **7.7%** (`368`)

Multi-label prevalence among undrilled prospects: **75.8%** cite geological risk, **52.5%** cite volume/commerciality (`volume_too_small`: 2,170; `commercial`: 1,228; `negative_emv`: 158; `below_mef`: 128), and **25.4%** (`1,210`) involve non-technical/external friction.

### Non-Technical Friction Across All 738 Licences (Full Licence + Prospect Evidence)
| Non-Technical Factor | Licences (`n / 738`) | % of NCS | North Sea | Norwegian Sea | Barents Sea |
|---|---:|---:|---:|---:|---:|
| **Infrastructure / Tie-back / Host Capacity** | 254 | **34.4%** | 28.0% | 38.7% | **45.1%** |
| **Licence Expiry / 10-yr Ceiling / Time** | 103 | **14.0%** | 17.3% | 10.3% | 11.5% |
| **Partner Disagreement / Farm-out / Sole Risk** | 100 | **13.6%** | 12.1% | **17.6%** | 8.8% |
| **Outside Licence / Straddling Boundary** | 51 | **6.9%** | 7.7% | 6.5% | 5.3% |
| **Portfolio Prioritization / Capital Allocation** | 40 | **5.4%** | 4.7% | 7.3% | 3.5% |
| **Gas Market / Evacuation / LNG Constraint** | 26 | **3.5%** | 0.5% | 5.0% | **9.7%** (19x North Sea) |
| **Rig / Well Cost / Drilling Capacity** | 13 | **1.8%** | 0.8% | 3.1% | 1.8% |

Structured licence governance fields confirm this is not anecdotal: **85 licences (11.5%)** record explicit divergent `partner_views`, **34 licences (4.6%)** record failed/attempted `farm_out` processes, and **7 licences (0.9%)** record `operator_sole_risk_actions`.

---

## 3. The "Left Behind" Untested NCS Prize

Filtering strictly to **undrilled, post-award assessed (`final`/`drill_or_drop`/`intermediate`)** relinquished prospects (excluding child segments, `Pg = 1.0` appraisal segments, and straddling duplicates) dropped for **commercial or non-technical reasons**:

| Threshold & Scope | Unique Prospects | Total Unrisked (`MSm3 o.e.` / `MMboe`) | Total Risked (`MSm3 o.e.` / `MMboe`) |
|---|---:|---:|---:|
| **Post-award assessed, Comm/Non-Tech, `Pg >= 0.20`** | **355** | **1,496.7 MSm3** (`9,414 MMboe`) | **471.3 MSm3** (`2,965 MMboe`) |
| **Post-award assessed, Comm/Non-Tech, `Pg >= 0.25`** | **262** | **964.6 MSm3** (`6,067 MMboe`) | **353.8 MSm3** (`2,225 MMboe`) |
| *Incl. application-stage fallback, Comm/Non-Tech, `Pg >= 0.20`* | *387* | *1,791.2 MSm3 (`11,267 MMboe`)* | *558.6 MSm3 (`3,513 MMboe`)* |
| *Incl. application-stage fallback, Comm/Non-Tech, `Pg >= 0.25`* | *274* | *1,110.5 MSm3 (`6,985 MMboe`)* | *408.1 MSm3 (`2,567 MMboe`)* |

### Basin Distribution of the Post-Award Untested Prize (`Pg >= 0.20`, Comm/Non-Tech)
- **Norwegian Sea:** `n = 128` | **651.3 MSm3 (`4,097 MMboe`) unrisked** | **216.9 MSm3 (`1,364 MMboe`) risked** (**46.0% of total NCS risked prize**, heavily gas-weighted in Vøring/Halten!)
- **North Sea:** `n = 148` | **517.7 MSm3 (`3,257 MMboe`) unrisked** | **152.9 MSm3 (`961 MMboe`) risked** (32.4%)
- **Barents Sea:** `n = 79` | **327.6 MSm3 (`2,061 MMboe`) unrisked** | **101.6 MSm3 (`639 MMboe`) risked** (21.6%)

### Top 10 Most Intriguing Undrilled Relinquished Prospects (Post-Award Assessed, `Pg >= 0.20`, Comm/Non-Tech)
| # | Prospect | Licence | Basin | Operator (Relinq.) | Unrisked (`MSm3` / `MMboe`) | `Pg` | Risked (`MSm3` / `MMboe`) | Phase | Why Left Behind |
|---:|---|---|---|---|---:|---:|---:|---|---|
| 1 | **Edinburgh** | PL660 | North Sea | DNO / Faroe (2016) | 33.6 / 211.5 | **44%** | **14.8 / 93.1** | Oil eq. | Deemed drillable & viable, but only 22% lay inside Norway (UK/NCS border straddle). |
| 2 | **Natator Cluster** | PL728 | North Sea | DONG (2018) | 49.7 / 312.7 | **24%** | **11.9 / 75.1** | Gas | Large Jurassic gas cluster; residual commercial/risk hurdle at drill-or-drop. |
| 3 | **Kelvin** | PL653 | Norwegian Sea | Wintershall Dea (2017) | 29.4 / 184.9 | **35%** | **10.3 / 64.7** | Gas | Stranded Vøring gas extending into open acreage; needs area development solution. |
| 4 | **Celsius** | PL653 / PL694 | Norwegian Sea | Wintershall Dea (2017) | 26.3 / 165.4 | **39%** | **10.3 / 64.5** | Gas | Straddling gas giant (`P50 23.8 GSm3`); dropped due to 2017 gas market economics. |
| 5 | **Balderbrå** | PL522 | Norwegian Sea | BG Norge (2014) | 25.2 / 158.5 | **37%** | **9.3 / 58.6** | Gas | Doubled post-award (`11.4 -> 25.2 MSm3`), robust closure; remote Vøring gas. |
| 6 | **Sjampis** | PL695 | Barents Sea | Equinor (2021) | 35.5 / 223.3 | **25%** | **8.9 / 55.8** | Oil | Largest undrilled oil target on list; CSEM/amplitude inconclusive for stand-alone well. |
| 7 | **Fjellflokk Far East 1** | PL847 | Norwegian Sea | Wintershall Dea (2020) | 14.1 / 88.7 | **60%** | **8.5 / 53.2** | Gas | High-Pg (`60%`) 491 Bcf gas prospect left behind after nearby Marisko well. |
| 8 | **Svartbakkestjerne Springar** | PL847 | Norwegian Sea | Wintershall Dea (2020) | 18.8 / 118.1 | **42%** | **7.9 / 49.6** | Gas | 663 Bcf Springar gas target in same Vøring licence (PL847). |
| 9 | **Maiblom** | PL944 | Norwegian Sea | Wintershall Dea (2021) | 22.7 / 143.0 | **32%** | **7.3 / 45.8** | Oil eq. | Substantial Halten/Vøring volume; commercial & technical threshold not cleared. |
| 10 | **Faering South** | PL809 | North Sea | TotalEnergies / Maersk (2018) | 23.2 / 146.0 | **29%** | **6.7 / 42.3** | Oil eq. | Unanimous partnership decision that economics were not viable under 2018 terms. |

*Bonus high-Pg Barents watch-list:* **Shadowcat** (`PL852`, Spirit Energy, 2021: `10.4 MSm3` / `65.5 MMboe`, **`Pg 59%`**, `6.1 MSm3` risked) and **Sweetums South Norian** (`PL1083`, Aker BP, 2024: `27.2 MSm3` / `170.8 MMboe`, `Pg 22%`, `6.0 MSm3` risked).
