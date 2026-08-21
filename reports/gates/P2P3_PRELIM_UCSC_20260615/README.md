# P2/P3 Preliminary Gate Evidence Pack

Date: 2026-06-15

Source: `.backup/data` existing UCSC/external/legacy downloads and derived tables.

Claim eligibility: **NO**. This pack is for engineering rehearsal and route planning only. Final claim-bearing runs require self-run RepeatMasker+Dfam Label-A with versioned software/library manifests, then rerunning these gates.

## Outputs

- `species_manifest_prelim.tsv`: preliminary species/input inventory.
- `chromosome_ladder_prelim.tsv`: automatic largest non-sex/non-organelle chromosome candidates.
- `te_len_viz_summary_prelim.tsv`: TE interval length-bin summary from existing `rmsk_te.bed.gz`.
- `sf_target_step1_prelim.tsv`: preliminary species x superfamily bp table.
- `u_quality_prelim.tsv`: proxy-only U/hardN summary; RN is not constructed.
- `gate_status.tsv`: current gate status and remaining blockers.
- `summary.json`: machine-readable pack summary.

## Interpretation

`LABEL-CONCORDANCE` remains blocked because no independent Label-B audit source is present in this pack. `WIN-MATRIX` has only length-distribution input, not backbone context limits or GPU smoke. `U-QUALITY` is only a proxy because RN/hardN masks and interval-level contamination checks are not constructed.

## Summary

- Species rows: 65
- Species with interval TE annotation: 47
- Issues detected: 0
