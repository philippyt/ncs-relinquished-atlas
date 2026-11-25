# ncs-relinquished-atlas

Private exploratory audit and screened open-acreage inventory built from 756 Norwegian Continental Shelf licence relinquishment reports cross referenced against SODIR FactPages and FactMaps.

## Key Outputs

- [reports/WRITEUP.md](reports/WRITEUP.md) Final BLUF technical writeup (`v1.0.1`).
- [reports/EXECUTIVE_FINDINGS.md](reports/EXECUTIVE_FINDINGS.md) Concise executive summary aligned with `v1.0.1`.
- [reports/ncs_atlas_discoveries.html](reports/ncs_atlas_discoveries.html) Visual summary dashboard (`v1.0.1`).
- `reports/figures/` Four publication-style matplotlib figures in both `.svg` and `.png`.
- `analyses/track6_production_audit.py` and `analyses/track7_reconcile_and_logit.py` Norwegian-sector-clipped APA open-acreage screen, fluid-aware surface host distances, outcome-blind formation-top matching, and maturity-controlled logistic regression.
- `analyses/track1_redrilled_graveyard.py` through `analyses/track5_reviewer_upgrades.py` Earlier exploratory analysis scripts.
- `src/loader.py` Shared loader deduplicating the 18 multi-licence report pairs and fixing three 1,000x unit-scaling bugs.
