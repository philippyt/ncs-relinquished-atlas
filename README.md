# ncs-relinquished-atlas

Exploratory scientific audit of the 756 Norwegian Continental Shelf licence relinquishment reports and prospect atlas (`10.5281/zenodo.24528585`) cross referenced against SODIR FactPages exploration wells.

## Key Outputs

- [reports/EXECUTIVE_FINDINGS.md](reports/EXECUTIVE_FINDINGS.md): Synthesized headline findings across all four research tracks.
- [reports/ncs_atlas_discoveries.html](reports/ncs_atlas_discoveries.html): Visual dashboard of the four headline discoveries.
- `analyses/track1_redrilled_graveyard.py` + `track1_findings.md`: Relinquished prospects later redrilled into discoveries (`50.0%` hit rate, `4` fields).
- `analyses/track2_risk_calibration.py` + `track2_findings.md`: Pre-drill `Pg` calibration, the Reservoir Blind Spot (`47.6%` of dry holes vs `21.5%` feared), and operator fingerprints.
- `analyses/track3_volume_drift_and_prize.py` + `track3_findings.md`: The APA Double Optimism Tax (`-61.4%` median risked volume cut) and the `2.97 Bboe` risked untested prize.
- `analyses/track4_dhi_plays_and_llm_consistency.py` + `track4_findings.md`: The Barents Gas-Trap DHI Paradox (`84.6%` gas-only), the Flat Spot Trap (`28.0%`), and the 18-PDF AI map digitization benchmark (`0.861` median IoU).
- `src/loader.py`: Shared loader deduplicating the 18 multi licence report pairs and fixing upstream unit scale bugs.
