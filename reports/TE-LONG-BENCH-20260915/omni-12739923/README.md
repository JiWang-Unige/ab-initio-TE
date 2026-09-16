# Qualified Omnibenchmark replay

Omnibenchmark 0.6.0 completed the pinned `long_panel.yaml` workflow on 2026-09-16 using the actual Slurm bundle [score-12739923/result.json](../score-12739923/result.json). The GitHub module resolved to `4edaeb16e735be4c25fdbace12822f026604f649`; no `--dirty` option was used. All four Snakemake jobs completed successfully.

The collector retains all 14 planned cells: 13 qualified `COMPLETED` and one native `FAILED` (CB4 EDTA), with null accuracy for that failed cell. Both EarlGrey final libraries passed exact strained-plus-lineage concatenation and final-output coordinate checks before these results were accepted. The historical score/replay 12738470 remains preserved and is superseded for comparison because its two EarlGrey cells omitted the starting library.

This execution recomputed metrics from validated block counts, checked callable-base denominators and matched the Slurm metrics. It did not rerun native annotation tools. CB4 absolute precision/F1 and L3 insertion identity remain null; arithmetic reproducibility does not establish independent biological truth. Native runtimes include the recorded selected-protocol recovery costs and are not the runtime of this local replay.

Evidence: [collector](collector_summary.json), [manifest](manifest.json), [pinned modules](modules.txt), [execution log](snakemake-log.txt). Log trailing whitespace was normalized. No DNA, model weights or probability arrays are included.

With an installed Omni runtime, set `TE_LONG_BENCH_RESULT` to the absolute path of the committed source bundle, then run from the repository root:

```sh
ob run benchmarks/te_omnibenchmark/long_panel.yaml --out-dir /path/to/new-output --cores 1 -- --scheduler greedy
```
