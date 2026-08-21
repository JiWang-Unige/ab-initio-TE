# PIPE-TEFM-NEXT-DECAY-FRAG-20260630 selector calibration

## Scope

This report asks whether the deployable genome-derived selector is usable as a new-species trust guide.
It evaluates leave-species-out and leave-clade-out prediction, anchor-choice accuracy, regret, risk-bin calibration, and empirical uncertainty intervals.

## Headline

- Best screen row: `baseline_plus_kmer` / `leave_species_out`.
- RMSE: 0.2642; ECE: 0.0372; top-1 anchor accuracy: 0.4545; top-2: 0.6818; mean regret: 0.0680.
- Usable screen gate: False.

## Usability Gate

A selector is marked screen-usable only if it meets all provisional thresholds: at least 10 held-out species, top-2 anchor accuracy >=0.75, mean regret <=0.10, ECE <=0.10, and RMSE <=0.20.
Failing this gate means the selector can still support a paper discussion as triage/risk stratification, but it should not be presented as a reliable deployment confidence formula.

## Outputs

- `selector_calibration_summary.tsv`
- `selector_calibration_bins.tsv`
- `selector_species_recommendations.tsv`
- `selector_row_predictions.tsv`
- `selector_calibration_status.json`
