# Groundbreaking Findings from the 756 NCS Licence Relinquishment Reports

Independent scientific audit of the 756 Norwegian Continental Shelf licence relinquishment reports and prospect atlas (`10.5281/zenodo.24528585`, 738 unique licences and 5,325 prospects after removing 18 duplicate multi-licence pairs and 3 unit conversion bugs) cross referenced against SODIR FactPages exploration wells (`wellbore_exploration_all.parquet`).

## 1. The Two-Regime Exploration Paradox (Tracks 1 & 2)

- **In-licence exploration is systematically overconfident (`n = 138`):** Mean pre-drill `Pg` is **27.0%**, but actual hydrocarbon discovery rate is **18.1%** (`25/138`, `-8.89 pp`, `p = 0.0134`, commercial discovery rate just **8.0%**). Every `Pg` bin is overconfident, peaking at **`-17.1 pp`** in the `35-50%` bin (`40.9%` predicted vs `23.8%` actual). Overconfidence steepens northward: North Sea `-6.5 pp`, Norwegian Sea `-8.9 pp`, **Barents Sea `-16.3 pp`** (`26.8%` predicted vs `10.5%` actual).
- **Resurrected relinquishments beat their pre-relinquishment `Pg` nearly 2x (`n = 130`):** Full point-in-polygon ray casting against SODIR wildcat wells completed strictly *after* relinquishment uncovers **130 undrilled relinquished prospects** penetrated later by **87 unique wildcats**. **50.0% (`65/130`)** became discoveries (`36` unique named discoveries and **4 fields: `BERLING`, `BESTLA`, `DUVA`, `DVALIN`**). Among the `86` with stated pre-relinquishment `Pg`, actual discovery rate was **46.5%** vs **24.0%** mean `Pg` (`1.94x`, `p = 1e-6`), and **52.6% (`40/76`)** on tight `<= 50 km2` polygons.
- **Fresh eyes made 100% of the field discoveries:** Different operators returning hit **53.6% (`52/97`)** and discovered **9/9 (100%)** of the field-making prospects, compared to **39.4% (`13/33`)** and **0 fields** when the same operator (or successor) came back.
- **Standout "Ones That Got Away":**
  - **Hades / Siggjo -> `6506/11-10 Berling` (`BERLING` field, OMV, 2018):** Relinquished twice (Det norske PL256 in 2011 at `Pg 20%`, then Centrica PL477 in 2015 stating *"no drillable candidates left"*).
  - **Yngling -> `31/7-1 Bestla` (`BESTLA` field, Faroe, 2016):** Dropped by Lundin (PL576, 2013) at `>20%` `Pg` as *"too small to be commercially interesting"*.
  - **Sabina -> `6507/4-2 S` (`DVALIN` field, Wintershall Dea, 2021):** Dropped by Maersk (PL647, 2014, `Pg 36%`) due to licence boundary segmentation.
  - **Jotne -> `36/7-5 B` (`DUVA` field, Var Energi, 2024):** Dropped by Shell (PL686, 2015, `Pg 9%`).
  - **Partner-veto discoveries:** Warka (`6507/4-1`), Toutatis (`6611/1-1`), Celsius (`6607/3-1 S Velocette`), Herzer (`6506/5-1 S Nidhogg`), and Sebastian (`25/7-8 S Enniberg`).

## 2. The Reservoir Blind Spot (Track 2)

- Across `891` four-factor prospects, operators fear **Charge (32.6%)** and **Trap (29.5%)** most, ranking **Reservoir** only 3rd (**21.5%**).
- Across **214 dry holes** with documented failure causes (`271` mentions), **Reservoir is the #1 killer at 47.6%** (`2.21x` more lethal than feared), while **Trap causes only 5.9%** (`5x` over-feared).
- Confirming this from Track 1: relinquished prospects dropped for `trap_risk` (`61.9%` hit rate) or `commercial` (`63.2%`) were frequent false negatives, whereas `migration_risk` (`28.6%`) and `seal_risk` (`35.5%`) warnings were right.

## 3. The Compounding APA Double Optimism Tax (Track 3)

- Across `183` re-evaluated paired prospects (application/award -> relinquishment), **79.2% shrink vs 20.8% grow** (nearly 4-to-1), with a **median volume cut of `-52.0%` (`0.480x`)**.
- Simultaneously, `71.9%` of `253` re-evaluated prospects drop in `Pg` (median **`-6.0 pp`**).
- Combining both (`Pg * Mean`, `n = 165`), **83.0% lose risked volume** with a **median risked cut of `-61.4%` (`0.386x`)** and `48.3%` of total portfolio risked volume evaporating.
- **Two paradoxes:** Shrinkage is **worst in the data-dense North Sea** (`83.1%` shrink, median `-60.8%`) and got **worse in the 2020s** (`-52.1%` portfolio volume cut, `-5.1 pp` mean `Pg` drop vs `-37.9%` and `-2.2 pp` in the 2010s) as modern 3D QI/AVO deflates marginal APA traps faster post-award.
- **Left behind untested prize:** `355` unique undrilled prospects with `Pg >= 0.20` dropped for commercial or non-technical reasons represent **`1,496.7 MSm3 o.e.` (`9.41 Bboe`) unrisked** and **`471.3 MSm3 o.e.` (`2.97 Bboe`) risked** (`46.0%` in the Norwegian Sea). Across all 738 licences, **34.4%** cite infrastructure/tie-back limits and **13.6%** cite partner disagreement or failed farm-outs.

## 4. The Barents Gas-Trap DHI Paradox & The Flat Spot Trap (Track 4)

- **Overall DHI signal is strong:** `positive_dhi` hits **54.2% (`58/107`)** vs `negative_or_no_dhi` at **22.6% (`14/62`)** (`p = 5.6e-5`).
- **Barents Gas-Trap Paradox:** In the Barents Sea, positive DHI triples technical discovery rate (**68.4% vs 26.9%**, `p = 0.001`), **but 84.6% (`11/13`) of those discoveries are gas-only** (vs just **6.7% [`1/15`]** in the North Sea, `p = 5.4e-5`). Only `1/19` found commercial oil.
- **The Flat Spot Trap:** Claimed **`flat_spot`** prospects hit only **28.0% (`7/25`)** overall and **12.5% (`1/8`)** in the North Sea, vs **69.0% (`29/42`)** for positive **`amplitude_conformance`** (`p = 0.0018`).
- **Play & depth extremes:** **Cretaceous** leads at `49.1%` (`15.0 MSm3` mean) vs **Permian** at `18.8%` (`p = 0.0016`). Deep **`>4500 m`** HPHT prospects hit **80.0% (`12/15`)** (`p = 0.0051`), of which **83.3%** are gas/condensate relinquished as non-commercial HPHT gas.

## 5. Operator Fingerprints & The Accidental 18-PDF AI Benchmark (Tracks 2 & 4)

- **16.5 pp basin-adjusted operator optimism spread:** DNO (`+9.61 pp`) and Wintershall Dea (`+6.66 pp`) sit highest vs Neptune/ENGIE (`-6.84 pp`), ConocoPhillips (`-5.32 pp`), Shell (`-4.40 pp`), and Lundin (`-4.21 pp`). Median P10/P90 ratio spans `4.8x` (`Wellesley 3.61x`, `Aker BP 3.94x` vs `Spirit/Centrica 17.35x`, `OMV 16.95x`).
- **18 duplicate multi-licence PDFs as a natural AI reproducibility benchmark:** Across `52` true independent VLM map digitizations (`digitised_figure`, excluding companion GIS shapefiles), median polygon IoU is **0.861** with **116.8 m** median centroid shift; tabular extraction hits **95.5%** exact `Pg` match, **92.2%** exact volume match, **100%** reservoir period match, and **0.862** prospect name Jaccard.
- **Three upstream 1,000x unit bugs caught and patched in `src/loader.py`:** `PL531_JURASSIC` (`bcf` converted with `tcf` factor `28.3168` -> `9,736 MSm3`), `PL1019` (`GSm3 OE` header multiplied by `1,000` -> `6,900 MSm3`), and `PL883 Taren East` condensate (`0.75/0.89 MSm3` mistyped as `1e9Sm3` -> `750/890 MSm3`).

## Detailed Track Reports

- [track1_findings.md](../analyses/track1_findings.md)
- [track2_findings.md](../analyses/track2_findings.md)
- [track3_findings.md](../analyses/track3_findings.md)
- [track4_findings.md](../analyses/track4_findings.md)
