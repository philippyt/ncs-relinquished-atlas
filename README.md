# ncs-relinquished-atlas

Exploratory analysis of the 756 Norwegian Continental Shelf licence relinquishment reports and prospect atlas (`10.5281/zenodo.24528585`) cross referenced against SODIR FactPages exploration wells.

## Structure

- `src/loader.py`: Shared loader for the 5 Zenodo zip parts with deduplication of the 18 multi licence report pairs and safe unit normalization.
- `analyses/`: Reproducible analysis scripts and markdown/JSON findings across four research tracks.
- `reports/`: Synthesized findings and charts.
