# Actual Omnibenchmark replay

Omnibenchmark 0.6.0 completed the pinned `long_panel.yaml` workflow on 2026-09-16 from the actual Slurm score bundle `score-12738470/result.json`. The GitHub module was resolved at `4edaeb16e735be4c25fdbace12822f026604f649`; no `--dirty` option was used. Snakemake completed all four jobs successfully.

The collector retained all 14 planned cells: 13 `COMPLETED` with metrics and one `FAILED` (CB4 EDTA) with null metrics. It recomputed metric totals from per-block counts, checked recovery of each callable-base denominator, and matched the Slurm metrics. Real-data precision/F1 and L3 insertion identity remain null. Native runtime is carried through from the original jobs; this local replay time is not tool runtime.

Evidence: `collector_summary.json`, `manifest.json`, `modules.txt`, and `snakemake-log.txt` (trailing whitespace normalized). The source bundle is committed in the sibling `score-12738470` directory; it contains compact counts and execution metadata, not DNA sequences, weights, GFF annotations or probability arrays.

This proves reproducible aggregation, not independent truth qualification or that native callers were executed by Omni. CB4's reference coverage limitation is documented separately. Subsequent qualification confirmed that both EarlGrey resumed pipelines omitted their initial lineage library because the skipped initial stage did not restore `RepSub`. The replayed arithmetic remains reproducible, but those two cells are protocol-ineligible. This bundle is preserved as a historical attempt; a new score/replay is required after the bounded source-state repair. See the sibling EarlGrey output-qualification report.

To replay with an installed Omni runtime, set `TE_LONG_BENCH_RESULT` to the absolute path of the committed source bundle and run:

```sh
ob run benchmarks/te_omnibenchmark/long_panel.yaml --out-dir /path/to/new-output --cores 1 -- --scheduler greedy
```
