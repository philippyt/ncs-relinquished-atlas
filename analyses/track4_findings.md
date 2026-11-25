# Track 4: DHI Paradox, Play/Depth Sweet Spots & AI Extraction Consistency

## Dataset & Linkage Summary
- Deduplicated licences: **738** (5325 prospects)
- Prospect GeoJSON polygons linked: **4128** covering **4030** prospects
- SODIR FactPages wildcat wells loaded: **1436**
- Drilled prospects: **848** total (report-recorded: **539**, FactPages spatial polygon hit: **626**, post-relinquishment re-drills: **141** with **70** discoveries)

---

## (A1) The DHI Paradox

### Overall Discovery Rate by DHI Category (Combined Report + FactPages Wildcats)
| DHI Category | Prospects | Mean Pg | Drilled | Discoveries | Discovery Rate | Mean Pg (Drilled) | Report Disc Rate | FactPages Disc Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| positive_dhi | 377 | 29.4% | 107 | 58 | **54.2%** | 40.8% | 48.0% | 54.8% |
| observed_nonpositive_dhi | 625 | 21.6% | 83 | 28 | **33.7%** | 27.7% | 22.8% | 37.3% |
| negative_or_no_dhi | 544 | 13.1% | 62 | 14 | **22.6%** | 21.8% | 14.8% | 23.2% |
| assessed_unclear | 62 | 23.2% | 11 | 4 | **36.4%** | 42.7% | 42.9% | 42.9% |
| not_assessed | 3717 | 21.4% | 585 | 249 | **42.6%** | 35.5% | 40.0% | 45.0% |

### Fisher Exact Tests (Overall DHI Contrasts)
- **positive_dhi vs negative_or_no_dhi**: 54.2% (58/107) vs 22.6% (14/62), Fisher p = **5.6e-05**
- **positive_dhi vs all_without_dhi_observed**: 54.2% (58/107) vs 40.6% (267/658), Fisher p = **0.011121**
- **any_dhi_observed vs negative_or_no_dhi**: 45.3% (86/190) vs 22.6% (14/62), Fisher p = **0.001612**
- **any_dhi_observed vs not_assessed**: 45.3% (86/190) vs 42.6% (249/585), Fisher p = **0.555342**

### Basin Comparison: North Sea vs Norwegian Sea vs Barents Sea
| Basin | Positive DHI Disc Rate (n) | Any DHI Observed Disc Rate (n) | No DHI Observed Disc Rate (n) | Fisher p (Pos vs No DHI) | Pos DHI Mean Pg (Drilled) | Pos DHI Gas-Only Share |
|---|---:|---:|---:|---:|---:|---:|
| North Sea | **44.1%** (15/34) | 39.5% (30/76) | 40.1% (162/404) | 0.716844 | 32.4% | 6.7% |
| Norwegian Sea | **55.6%** (30/54) | 47.5% (38/80) | 49.7% (80/161) | 0.529816 | 46.0% | 43.3% |
| Barents Sea | **68.4%** (13/19) | 52.9% (18/34) | 26.9% (25/93) | 0.000992 | 40.9% | 84.6% |

### Discovery Rate by Specific DHI Type
| DHI Type | All Prospects | All Drilled Disc Rate (n) | Positive-Support Drilled Disc Rate (n) | Mean Pg (All) |
|---|---:|---:|---:|---:|
| flat_spot | 108 | 28.0% (7/25) | **29.4%** (5/17) | 26.7% |
| bright_spot | 305 | 51.3% (20/39) | **61.5%** (16/26) | 20.4% |
| avo_anomaly | 577 | 42.1% (48/114) | **55.4%** (36/65) | 18.5% |
| amplitude_conformance | 322 | 66.1% (39/59) | **69.0%** (29/42) | 28.8% |
| gas_chimney | 88 | 28.6% (2/7) | **50.0%** (1/2) | 8.9% |
| csem_anomaly | 33 | 16.7% (1/6) | **33.3%** (1/3) | 18.4% |
| dim_spot | 26 | 33.3% (3/9) | **40.0%** (2/5) | 24.5% |

### Operator Self-Granted DHI Pg Uplift (`pg` vs `pg_before_dhi`)
- Prospects reporting `pg_before_dhi`: **108**
- Mean Pg uplift: **+2.6%** (median **+1.7%**)
- Drilled subset with explicit DHI uplift: **5/13** (**38.5%** discovery rate vs mean drilled Pg 20.2%)

---

## (A2) Play / Reservoir Age & Depth Sweet Spots

### By Reservoir Geological Period
| Period | Prospects | Mean Pg | Mean Vol (MSm3 oe) | Median Vol | Median Area (km2) | Median Depth (m) | Drilled | Disc Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Jurassic | 2476 | 21.9% | 7.0 | 3.0 | 8.0 | 2795 | 414 | **42.3%** |
| Cretaceous | 932 | 21.3% | 15.0 | 5.8 | 20.4 | 3100 | 159 | **49.1%** |
| Paleogene | 664 | 19.6% | 12.0 | 5.7 | 12.5 | 2048 | 100 | **32.0%** |
| Triassic | 538 | 19.6% | 11.6 | 5.2 | 16.1 | 1550 | 74 | **33.8%** |
| Unknown | 370 | 20.6% | 10.7 | 4.9 | 9.9 | 1700 | 48 | **54.2%** |
| Permian | 195 | 9.9% | 16.8 | 8.3 | 23.2 | 2460 | 32 | **18.8%** |
| Neogene | 65 | 23.9% | 17.5 | 5.1 | 32.4 | 810 | 8 | **62.5%** |
| Basement | 37 | 21.9% | 19.5 | 8.9 | 25.1 | 2726 | 3 | **0.0%** |
| Carboniferous | 30 | 6.5% | 19.2 | 15.0 | 18.9 | 2850 | 6 | **50.0%** |
| Devonian | 11 | 15.6% | 3.0 | 2.2 | 15.0 | 3140 | 3 | **66.7%** |
| Other_Rare | 7 | 12.5% | 5.8 | 7.2 | 42.8 | 1592 | 1 | **100.0%** |

### By Crest Depth Bin
| Depth Bin | Prospects | Mean Pg | Mean Vol (MSm3 oe) | Median Vol | Median Area (km2) | Drilled | Discoveries | Disc Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| <1500 m | 383 | 17.6% | 12.2 | 5.8 | 16.4 | 47 | 19 | **40.4%** |
| 1500-2500 m | 540 | 15.7% | 10.2 | 4.9 | 11.8 | 64 | 27 | **42.2%** |
| 2500-3500 m | 520 | 23.5% | 9.0 | 3.5 | 10.2 | 107 | 42 | **39.2%** |
| 3500-4500 m | 376 | 24.8% | 9.8 | 3.8 | 11.5 | 58 | 29 | **50.0%** |
| >4500 m | 108 | 20.1% | 13.3 | 5.0 | 18.4 | 15 | 12 | **80.0%** |
| Unknown | 3398 | 22.1% | 8.8 | 2.7 | 10.4 | 557 | 224 | **40.2%** |

### Special Plays & Anomalies
- **HPHT-flagged prospects**: n=145, Mean Pg=25.4%, Mean Vol=9.6 MSm3 oe, Drilled=35, Disc Rate=**57.1%**
- **Deep (>=4000 m)**: n=282, Mean Pg=23.5%, Mean Vol=11.4 MSm3 oe, Drilled=44, Disc Rate=**61.4%**
- **Shallow Barents (<1500 m)**: n=268, Mean Pg=17.8%, Mean Vol=11.2 MSm3 oe, Drilled=22, Disc Rate=**31.8%**
- **Basement play**: n=37, Mean Pg=21.9%, Mean Vol=19.5 MSm3 oe, Drilled=3, Disc Rate=**0.0%**

---

## (B) The Accidental Natural Experiment in AI Geoscience Extraction (18 Duplicate PDF Pairs)

- **Exact prospect count match**: **10/18** (**55.56%**), mean abs diff = 0.72
- **Prospect name Jaccard overlap**: macro mean **0.862**, median **0.955**, micro **0.849** (140/165 union prospects)
- **Matched Volume agreement** (n=77): exact (<=1% diff) = **92.21%**, within 5% = **96.1%**, median % diff = **0.0%**, mean % diff = **1.81%**, catastrophic (>50% diff) = **1** (1.3%)
- **Matched Pg agreement** (n=88): exact match = **95.45%**, within 5 pp = **98.86%**, MAE = **0.0011** (0.11 pp), max error = **0.0700**
- **Secondary fields**: DHI observed agreement = **84.21%** (n=19), DHI support agreement = **85.71%** (n=28), Reservoir period agreement = **100.0%** (n=129), Crest depth within 10 m = **97.14%** (n=70, median abs diff = 0.0 m)
- **GeoJSON Polygon Digitization Consistency** (n=103 matched prospect polygons): median IoU = **0.987**, mean IoU = **0.885**, IoU >= 0.70 = **83.5%**, IoU >= 0.50 = **95.15%**, IoU < 0.10 = **0.0%** (zero overlap: 0)
- **Polygon Centroid Shift (All)**: median **19.0 m**, mean **243.9 m**, P90 **440.7 m**, median area diff = **0.18%** (byte-identical polygons: 48/103)
- **Independently Digitized Map Figures Only (`digitised_figure` vs `digitised_figure`, n=52)**: median IoU = **0.861**, mean IoU = **0.799**, IoU >= 0.70 = **73.08%**, IoU >= 0.50 = **92.31%**, median centroid shift = **116.8 m** (mean 354.9 m, P90 610.8 m), median area diff = **7.95%**
- **Companion Shapefile Only (`shapefile` vs `shapefile`, n=48)**: median IoU = **1.0**, mean IoU = **0.9935**, median centroid shift = **0.0 m**
- **Licence Boundary Baseline** (n=18): median IoU = **1.0**, median centroid dist = **0.0 m**

### Per-Pair Summary (18 Duplicate Multi-Licence PDFs)
| Licence | Pages | N1 | N2 | Matched | Jaccard | Matched Polys | Median IoU | Median Centroid Dist (m) | Licence IoU |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PL1003 | 28 | 2 | 2 | 2 | 1.000 | 2 | 0.809 | 26 | 1.000 |
| PL1007 | 22 | 15 | 15 | 15 | 1.000 | 11 | 0.772 | 60 | 1.000 |
| PL1009 | 23 | 4 | 4 | 4 | 1.000 | 4 | 0.929 | 44 | 1.000 |
| PL1013 | 13 | 3 | 4 | 3 | 0.750 | 2 | 1.000 | 0 | 0.000 |
| PL1039 | 9 | 10 | 11 | 10 | 0.909 | 9 | 1.000 | 0 | 1.000 |
| PL1043 | 15 | 12 | 8 | 8 | 0.667 | 6 | 1.000 | 0 | 0.000 |
| PL1045 | 13 | 5 | 5 | 5 | 1.000 | 3 | 1.000 | 0 | 1.000 |
| PL1055 | 18 | 3 | 3 | 3 | 1.000 | 3 | 0.935 | 120 | 1.000 |
| PL414 | 37 | 13 | 14 | 11 | 0.688 | 4 | 0.846 | 118 | 0.000 |
| PL423S | 32 | 8 | 9 | 8 | 0.889 | 3 | 0.901 | 173 | 1.000 |
| PL475 | 19 | 10 | 10 | 10 | 1.000 | 4 | 0.932 | 103 | 1.000 |
| PL498 | 19 | 11 | 10 | 10 | 0.909 | 9 | 0.684 | 212 | 1.000 |
| PL676S | 19 | 4 | 3 | 2 | 0.400 | 2 | 0.726 | 642 | 1.000 |
| PL785S | 12 | 31 | 28 | 28 | 0.903 | 22 | 1.000 | 0 | 1.000 |
| PL927 | 17 | 3 | 3 | 3 | 1.000 | 3 | 0.994 | 3 | 1.000 |
| PL969 | 23 | 7 | 7 | 4 | 0.400 | 3 | 1.000 | 0 | 1.000 |
| PL973 | 17 | 7 | 7 | 7 | 1.000 | 7 | 0.927 | 26 | 1.000 |
| PL987 | 17 | 7 | 7 | 7 | 1.000 | 6 | 0.932 | 86 | 1.000 |
