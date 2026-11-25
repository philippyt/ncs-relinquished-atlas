# Track 2: Risk Calibration, Optimism Bias & The Anatomy of Exploration Failure

Reproducible script: [track2_risk_calibration.py](file:///C:/Users/philip/Documents/ncs-relinquished-atlas/analyses/track2_risk_calibration.py)  
Structured output: [track2_findings.json](file:///C:/Users/philip/Documents/ncs-relinquished-atlas/analyses/track2_findings.json)

## Corpus Scope
- **738 deduplicated NCS relinquishment reports** (18 multi-licence duplicates dropped), covering **5,325 prospects** and **2,233 exploration prospects** with valid pre-drill/relinquishment `Pg` (`0 < Pg < 0.99`, excluding already-known `Pg = 1.0` discoveries).
- **553 in-licence drilled prospects** (340 dry, 213 discoveries), of which **138** have strict pre-drill `Pg` (`drill_or_drop`, `intermediate`, `application`, `award`, `prior_licence`) and **150** have vetted pre-drill `Pg` (including non-post-well `final` assessments).
- **92 post-relinquishment out-of-sample prospects** (76 with compact `<= 50 km²` polygons) where a FactPages `WILDCAT` well was spudded inside the relinquished prospect polygon *after* the relinquishment report year.

---

## 1. Drilled Prospects Calibration: The Two-Regime Paradox

NCS explorers are **systematically overconfident on the prospects they choose to drill**, yet **dramatically outperform low relinquishment `Pg` on the rare prospects resurrected by later operators**:

| Cohort | n | Mean Predicted `Pg` | Actual Discovery Rate | Gap (Actual − Pred) | Z-stat | p-value | Brier |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Strict in-licence exploration** | 138 | 27.0% | **18.1%** (25/138) | **−8.89 pp** | −2.47 | **0.0134** | 0.1386 |
| **Full in-licence exploration** | 150 | 28.4% | **20.0%** (30/150) | **−8.36 pp** | −2.40 | **0.0163** | 0.1453 |
| **Commercial-only strict in-licence** | 138 | 27.0% | **8.0%** (11/138) | **−19.03 pp** | −5.30 | **< 0.0001** | 0.1112 |
| **Post-relinquishment (FactPages polygon)** | 92 | 23.6% | **47.8%** (44/92) | **+24.25 pp** | +6.09 | **< 0.0001** | 0.2711 |
| **Post-relinquishment tight (`<= 50 km²`)** | 76 | 25.5% | **52.6%** (40/76) | **+27.16 pp** | +6.07 | **< 0.0001** | 0.2876 |

### Calibration Curve (Strict In-Licence Exploration, `n = 138`)

Every single `Pg` bin falls below the 45° calibration line, peaking in the `35–50%` "sweet spot" where operators are overconfident by **−17.1 pp**:

| Stated `Pg` Bin | n | Mean `Pg` | Discoveries | Actual Rate | Gap | 95% Wilson CI |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| `<15%` | 18 | 10.1% | 1 | 5.6% | −4.6 pp | [1.0%, 25.8%] |
| `15–25%` | 55 | 19.9% | 6 | 10.9% | −9.0 pp | [5.1%, 21.8%] |
| `25–35%` | 36 | 29.7% | 8 | 22.2% | −7.5 pp | [11.7%, 38.1%] |
| `35–50%` | 21 | 40.9% | 5 | 23.8% | **−17.1 pp** | [10.6%, 45.1%] |
| `50%+` | 8 | 65.4% | 5 | 62.5% | −2.9 pp | [30.6%, 86.3%] |

### Key Drivers of Overconfidence
- **Basin gradient (in-licence, `n = 150`):** Overconfidence worsens monotonically northward: North Sea **−6.5 pp** (`n=90`, 28.7% pred vs 22.2% actual), Norwegian Sea **−8.9 pp** (`n=41`, 28.4% vs 19.5%), **Barents Sea −16.3 pp** (`n=19`, 26.8% vs 10.5%).
- **Pre-drill optimism creep (`n = 12` paired `application` → `drill_or_drop`):** Operators raised mean `Pg` by **+6.67 pp** (22.1% → 28.8%, 6 upgraded vs 4 downgraded) right before the drill decision, yet actual discovery rate was **16.7%**.
- **Post-relinquishment resurrection paradox (`n = 76` compact `<= 50 km²` polygons):** Relinquished prospects later drilled by FactPages wildcats hit **52.6% discoveries** vs **25.5% original `Pg`** (`+27.2 pp`, `p < 1e-9`)—beating stated `Pg` by `+20 to +34 pp` in every bin, reflecting strong re-screening/selection bias (only the top ~2% of relinquished prospects are re-licensed and drilled after new seismic/play breakthroughs) plus relinquishment-report pessimism.

---

## 2. Pre-Drill Fear vs Actual Cause of Failure: The Reservoir Blind Spot

Comparing what operators identify as the #1 risk across the atlas (`n = 891` prospects with 4-factor probabilities) against what actually killed the **214 dry holes** with documented failure causes (271 factor-failure mentions) reveals a massive inversion between **Reservoir** and **Trap**:

| Risk Factor | Atlas #1 Fear Share (lowest of 4 factors) | Actual Dry-Hole Cause Share (`n=214` wells) | Reality / Fear Ratio |
| :--- | ---: | ---: | ---: |
| **Reservoir** | 21.5% (3rd) | **47.6%** (129 mentions, **#1**) | **2.21× under-feared** |
| **Charge** | 32.6% (#1) | 32.5% (88 mentions, #2) | 1.00× calibrated |
| **Retention / Seal** | 16.3% (4th) | 14.0% (38 mentions, #3) | 0.86× calibrated |
| **Trap** | **29.5%** (2nd) | **5.9%** (16 mentions, 4th) | **0.20× (5× over-feared)** |

- **Raw dry-hole killers:** `reservoir_quality` (72), `reservoir_absent` + `reservoir_absent_at_location` (80), `migration` (63), `charge` (38), `top_seal` (26), `fault_seal` (23), `trap` (19).
- **Direct matched dry-hole audit (quantitative 4-factor, `n = 10`):** Top pre-drill fear predicted the actual killer 60.0% of the time (6/10). When **Reservoir** killed the well (`n = 6`), it was **not** the operator's #1 pre-drill fear in **5 of 6 cases (83.3%)** (mean pre-drill `P_reservoir = 0.56`).
- **Qualitative high-risk audit (`n = 52` dry holes with pre-drill `high`/`very_high` risk tags):** At least one flagged risk matched the actual killer in **80.8%** (42/52) of wells, but **Retention/Seal** was unflagged in **38.5%** (5/13) of seal failures and **Reservoir** was unflagged in **33.3%** (10/30) of reservoir failures.

---

## 3. Operator, Basin & Decade Optimism Fingerprints

### Basin & Decade Profiles
- **Basins:** Mean exploration `Pg` is nearly flat across basins—North Sea **20.0%** (`n=1,047`), Barents Sea **19.6%** (`n=400`), Norwegian Sea **18.9%** (`n=786`)—despite Barents Sea in-licence discovery rates being half the North Sea's. Risk factor bottlenecks differ sharply: **Charge** is lowest in the Norwegian Sea (`0.559`), **Trap** (`0.591`) and **Retention** (`0.726`) are lowest in the Barents Sea.
- **Decades (2010s → 2020s):** Mean `Pg` stayed flat (20.0% → 19.2%), but **median P10/P90 volume ratio compressed by 33%** (`8.51×` → `5.67×`, `n=602` vs `1,082`) while `P_retention` rose from `0.716` to `0.851` as operators converged on Equinor/Aker BP's risking convention.

### Operator Fingerprints (`n >= 20` exploration prospects, sorted by basin-adjusted `Pg`)

| Operator | n | Mean `Pg` | Basin-Adj `Pg` | Median P10/P90 | `P_res` | `P_trp` | `P_chg` | `P_ret` | In-Lic Drilled Gap |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| **DNO** | 105 | **29.2%** | **+9.61 pp** | 5.23× | 0.74 | 0.66 | 0.77 | 0.95 | — |
| **Wintershall Dea** | 126 | **26.0%** | **+6.66 pp** | 14.05× | 0.68 | 0.72 | 0.74 | 0.70 | **−16.6 pp** (`n=13`) |
| **OKEA** | 27 | 22.8% | +3.88 pp | 6.16× | 0.81 | 0.82 | 0.60 | 0.71 | — |
| **Premier Oil** | 22 | 23.7% | +3.69 pp | 17.25× | 0.80 | 0.55 | 0.73 | — | — |
| **Harbour Energy** | 26 | 22.5% | +3.10 pp | 10.45× | 0.55 | 0.75 | 0.77 | 0.69 | — |
| **Aker BP** | 379 | 19.2% | −0.53 pp | **3.94×** | 0.65 | 0.52 | 0.64 | **0.91** | −9.1 pp (`n=40`) |
| **Equinor** | 615 | 17.9% | −1.44 pp | 5.85× | 0.73 | 0.53 | 0.49 | **0.98** | −8.5 pp (`n=24`) |
| **Vår Energi** | 87 | 17.9% | −1.87 pp | 5.71× | 0.69 | 0.65 | 0.77 | 0.73 | +19.6 pp (`n=5`) |
| **Lundin** | 95 | 15.4% | −4.21 pp | 7.00× | 0.61 | 0.71 | 0.60 | 0.65 | −21.9 pp (`n=7`) |
| **Shell** | 59 | 15.0% | −4.40 pp | 11.67× | 0.53 | 0.72 | 0.59 | 0.61 | −22.2 pp (`n=6`) |
| **ConocoPhillips** | 34 | 14.3% | −5.32 pp | 8.80× | 0.69 | 0.76 | 0.46 | 0.67 | — |
| **Neptune / ENGIE** | 46 | **12.9%** | **−6.84 pp** | 7.29× | 0.69 | 0.78 | 0.57 | 0.57 | — |

- **16.5 pp optimism spread** across major operators after controlling for basin mix (**DNO +9.61 pp** and **Wintershall Dea +6.66 pp** vs **Neptune / ENGIE −6.84 pp** and **ConocoPhillips −5.32 pp**).
- **4.8× spread in volumetric precision:** **Wellesley** (`3.61×`) and **Aker BP** (`3.94×`) report ultra-narrow P10/P90 ranges compared to **Spirit / Centrica** (`17.35×`), **Premier Oil** (`17.25×`), **OMV** (`16.95×`), and **Wintershall Dea** (`14.05×`).
- **Structural risking-system split:** **Equinor** (`P_ret = 0.98`, `P_trp = 0.53`) and **Aker BP** (`P_ret = 0.91`, `P_trp = 0.52`) systematically fold seal risk into `P_trap`, whereas **TotalEnergies** (`P_ret = 0.48`, `P_trp = 0.71`) and **Suncor** (`P_ret = 0.49`, `P_trp = 0.75`) load seal risk onto `P_retention`.

---

## 4. The "Pg Math Gap"

Across **1,240 assessments** reporting both `Pg` and all 4 factors (`P_reservoir`, `P_trap`, `P_charge`, `P_retention`):
- **85.6%** (`1,061/1,240`) match the product within `±0.5 pp`.
- **14.4%** (`179/1,240`) disagree by `> 0.5 pp`, and **9.5%** (`118/1,240`) disagree materially by `> 1.5 pp`.
- **Direction is systematically LOWER, not higher:** `Pg < product` in **106 cases (8.55%, mean −7.15 pp)** vs `Pg > product` in **73 cases (5.89%, mean +6.24 pp)**; among material gaps (`> 1.5 pp`), **80 are lower vs 38 higher (2.1:1 ratio)**.
- **Mechanisms:**
  - `Pg > product` is partly driven by **DHI uplift** (`10` explicit `pg_before_dhi` cases, e.g. `PL887 Novus East`, PGNiG/ORLEN: product `0.275` → stated `Pg 0.57`, `+29.5 pp`) and multi-segment/override adjustments (e.g. `PL472 Imsa`, Wintershall Dea: product `0.448` → `0.87`, `+42.2 pp`; `PL814 Freke`, Aker BP: `0.32` → `0.72`, `+40.0 pp`).
  - `Pg < product` reflects **unprinted play-risk / dependency / phase-case multipliers** (only 3 explicitly list `p_play` in the JSON, e.g. `PL884 Counterparts`, Wellesley: product `1.00` → `0.36`, `−64.0 pp`; `PL1040 Ramstadslottet`, Equinor: `0.49` → `0.14`, `−35.0 pp`).
- **Operator compliance varies 12×:** **Wellesley** (40.7% disagree), **OMV** (35.9%, almost all lower: 13 lower vs 1 higher, mean −3.28 pp), **PGNiG / ORLEN** (35.0%), **Shell** (27.9%), and **Vår Energi** (26.4%) disagree far more often than **Harbour Energy** (3.3%), **DNO** (5.6%), **Lundin** (6.8%), and **Aker BP** (9.1%). **Suncor** is the lone operator whose math gaps are 100% upward (5 higher, 0 lower, mean `+4.93 pp`).
