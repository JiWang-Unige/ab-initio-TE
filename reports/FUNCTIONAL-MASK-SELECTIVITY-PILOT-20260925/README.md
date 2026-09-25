# FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925

This report directory is reserved for the fixed development pilot described in
[`docs/experiments/FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925.md`](../../docs/experiments/FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925.md).

The pilot has two fixed species (chicken and zebrafish), no new training, and
no GPU request. `jobs.jsonl` is created only when the pilot submission helper
is used. Per-species `RESULTS.md` and machine-readable `result.json` are
written after all four new AUGUSTUS arms complete and the unchanged reference
denominator passes the paired score.

The historical U/D/R_TE/RED results remain in
`reports/NONMAMMAL-GENE-UTILITY-20260918`; this directory will not overwrite
them. The pilot is development evidence and cannot be reported as an
independent confirmation test.

**Both fixed species are complete and validated.** See the
[joint closure report and next-stage recommendation](CLOSURE-20260925.md).
Fish native D improves over full RM2, but the chicken equal-budget advantage
does not reproduce in fish. No independent functional-selectivity claim is
released by this pilot.

## Current execution audit

Preparation completed with exit 0 for chicken `13192925` and zebrafish
`13192926`. The public `prepare-summary.json` records full-input, core, halo,
source-length-stratum, and actual-length-stratum counts. Full per-fragment
selection records remain in the native species `manifest.json` on Baobab and
the ignored local `*-manifest*.json` files; they are omitted only from this
compact export. The native alignment
parser found zero RM2 runs without a native alignment in both species.

The pre-repair rule audit is preserved as
`conf-rule-comparison-v2-pre-repair-{species}.json`. It distinguishes the
materialized/prepared state from reconstructions under the old raw-SW rule and
the frozen corrected SW/aligned-length rule. The post-repair audit is
`conf-rule-comparison-v2-{species}.json`: all 20 cores (10 chicken, 10
zebrafish) match the corrected rule interval by interval; the old raw-SW
reconstruction does not match. Chicken/c01 was the only mixed-preparation
exception. Its original mask, GFF, command record and manifest are retained as
`*-bugged-pre-repair`; only its `RM2_COMMON_CONF` FASTA/GFF was regenerated
under the corrected rule (repair job `13193088`). No other arm was rerun.

Prediction arrays `13192930` and `13192931` were released at `%2` per species.
Chicken's ten cells, c01 repair and score `13192933` have now completed; its
validated results are linked below. Zebrafish's ten cells and score
`13192934` (13 s) are now complete, with [native-output and count validation](zebrafish/validation.json).

`slurm-launch-snapshot.tsv` preserves the launch-time states and elapsed
allocation of failed preparation, cancelled dependents, audits and repair.
Active tasks in that snapshot are not terminal outcomes. `jobs.jsonl` is an
event history: its final dependency-update/release records supersede original
submission dependencies. Both original preparation failures (wrong input-root
join) and the first confidence-repair failure remain charged to this pilot.

The launch snapshot was retrieved at 2026-09-24T23:41:19.698193+00:00;
the chicken terminal update below supersedes its active-job states.

## Chicken terminal update

Chicken prediction and score 13192933 have completed and passed native-output/count validation. See [results](chicken/RESULTS.md) and the subsequent [fish terminal result](zebrafish/RESULTS.md). All fixed controls and the original U/D values are retained.

`slurm-chicken-terminal-snapshot.tsv` updates allocation accounting for the
completed chicken work while retaining all failed/cancelled preparations and
shared audits. Zebrafish rows still marked running are interim elapsed times,
not final total costs; the snapshot retrieval time is in `jobs.jsonl`.

The final `slurm-terminal.tsv` and `terminal-cost.json` supersede interim
accounting. All registered jobs are terminal; incremental pilot allocation
totals include failed preparation and repair, not only successful predictions.

## Descriptive source-stratum correction

Terminal review found that the `source_length_strata` summary fields had
duplicated post-truncation actual strata. `prepare-summary.json` now uses the
retained selection records' source bins; all 60 common-budget cells match
their frozen source quotas. `source-stratum-audit.json` records the checks,
and `prepare-summary-pre-source-field-fix.json` preserves the original compact
export. Native manifests retain their historical fields and selection records;
only the corrected compact summary should be used for source-bin counts.
No sequence, mask, prediction or score was changed. Actual output lengths and
core/halo residuals remain as measured.
