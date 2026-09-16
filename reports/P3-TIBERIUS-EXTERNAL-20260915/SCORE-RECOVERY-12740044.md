# Tiberius final-score dependency recovery

2026-09-16. During the successful connection at approximately 02:07 UTC, `sacct` showed original score job `12732548` as `CANCELLED by 0`, with no start time and an end time of 04:01 cluster local time (02:01 UTC). No cancellation reason was recorded. This does not establish a user cancellation, model failure or administrator motive.

The inference array `12738295` was still active: indices 37 and 38 were running and 39 remained pending in that Slurm snapshot. The formal `run-r1/result.json` did not yet exist. All preserved inference outputs and the full 40-core/200-cell requirement remain unchanged.

The original score script was submitted with its inference dependency:

```sh
sbatch --parsable --dependency=afterok:12738295 scripts/experiments/P3-TIBERIUS-EXTERNAL-20260915/score.sbatch
```

`sbatch` accepted the submission and returned **12740044**. Subsequent SSH calls were refused, including at 02:14 UTC, so a live `scontrol` read-back of this replacement job was not obtained. Verify this job on reconnection; do not create a duplicate. This recovery changes scheduling only, not data, arms, model, threshold, scoring or scientific gates. No partial utility results have been used.
