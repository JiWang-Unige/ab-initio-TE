# Whole-genome benchmark terminal evidence (2026-09-24)

This is an independent machine ledger for the frozen whole-genome benchmark. It preserves the original native output directories and their `status.json` files. The machine-readable record is [observed-terminal-20260924.json](observed-terminal-20260924.json).

**19:29 UTC update:** chicken EDTA `13189201` finished TIR successfully but
failed in its subsequent filter stage after 2,669 total Slurm seconds. Its
annotation remains unavailable. Follow-up binary/class scores
`13189350`/`13189351` completed in 103/197 seconds with all prior numeric
results unchanged and both EDTA species still NA. See [the follow-up
snapshot](SCORE-FOLLOWUP-20260924.md). The recovery investigation is limited
to continuing the preserved native workflow under the remaining original
budget; the older active-job descriptions below are historical snapshots.

The initial native jobs did not produce a complete set of four cells (EDTA and RepeatModeler2 on the two assemblies). Both RepeatModeler2 cells completed all five discovery rounds and the `-LTRStruct` stage, then failed at the bundled FamDB classification step because the container's default FamDB was empty or not configured. Their top-level `RM_*/consensi.fa` and `families.stk` are therefore valid terminal post-`-LTRStruct` discovery products. The classification-only recovery used those files in fresh roots and the fixed benchmark Dfam 4.0 asset; it did not repeat discovery. Both RM2 recovery masks subsequently completed successfully, so the two RM2 native annotations are now available for comparator scoring.

Chicken EDTA reached the TIR-Learner stage but stopped in the nested swifter/Dask path, where daemon-process creation is the confirmed fatal event. Source review also found a pandas 3 positional-index compatibility issue at `x[0]` for `TIR_type`; the exploratory slice-index message is not treated as an independent biological coordinate failure. Zebrafish EDTA reached the same stage, was killed with the Slurm terminal state `OUT_OF_MEMORY` under 128 GB, and has no final annotation. The current zebrafish EDTA `status.json` is now `FAILED` because the wrapper later persisted `RuntimeError('EDTA failed')`; the earlier `RUNNING` observation and the Slurm OOM event are retained in the independent ledger rather than overwriting that file. `--force` was not used because it would substitute missing TIR categories with the EDTA fallback library and change the frozen contract.

The original score job `12891298` never started and is not a scientific result. The first complete score jobs (`13180901` and `13180902`) ran with both RM2 roots and the still-missing EDTA cells represented as explicit NA; their numeric parsers read `annotation.out` directly. The RM2 descriptive summaries were repaired afterward without changing those numeric outputs. A later score rerun can include any separately completed chicken EDTA repair, while zebrafish EDTA remains NA unless an explicitly authorized contract-preserving repair produces a fresh annotation.

## Completed D timing cells

The D runner's JSON key `callable_bp_per_second_end_to_end` uses total FASTA input bp as its numerator. In this report it is therefore called **input-bp/s**. Child inference wall time and Slurm scheduler elapsed are listed separately.

| species | lane | job | input bp | child wall (s) | input-bp/s | Slurm elapsed |
|---|---:|---:|---:|---:|---:|---:|
| chicken | GPU | 12888136 | 1,065,365,425 | 17,223.32 | 61,864.51 | 04:47:22 |
| zebrafish | GPU | 12889199 | 1,679,203,469 | 27,093.44 | 61,978.34 | 07:31:56 |
| chicken | CPU | 12891439 | 1,065,365,425 | 398,324.46 | 2,674.62 | 4-14:39:04 |

The full zebrafish CPU inference was not submitted after the frozen pilot's seven-day feasibility estimate exceeded the allocation. The CPU row above is a completed chicken deployment datum, not a whole-genome accuracy claim.

## RM2 recovery cells

The fixed Dfam-v2 asset is the same runtime asset used by the existing TE benchmark configuration: schema `TEFM-FAMDB-ASSET-2.0.0`, Dfam 4.0, preparation job `11522328`. A tiny 2.2-KB consensus probe with the pinned RepeatModeler 2.0.9 image returned 0 and produced `consensi.fa.classified`; the first-time FamDB cache construction is recorded as shared engineering preparation, not as species discovery time.

The authorized private recovery jobs are:

| species | job | fresh root | parent discovery wall | recovery wall limit |
|---|---:|---|---:|---:|
| chicken | 13180658 | `native/chicken/RM2-recovery` | 1-11:58:11 | 5-12:01:49 |
| zebrafish | 13180659 | `native/zebrafish/RM2-recovery` | 1-02:53:12 | 5-21:06:48 |

The chicken initial recovery classified successfully in 436.50 s and wrote a 939,739-byte classified library, but its mask stage stopped in 25.95 s because the first wrapper did not bind RepeatMasker's two default FamDB library paths. The original root is retained. Mask-only job `13180772` completed in 02:12:28 in the fresh root `native/chicken/RM2-mask-recovery-v2`, binding both fixed library paths and reusing the successful classifier output without rerunning classification. The zebrafish continuation then reached the same terminal condition: classification returned 0 and wrote a 2,703,406-byte classified library, while RepeatMasker returned 1 after 19.77 s for the same missing default FamDB directory. Its original root and 934 s Slurm cost are retained. Mask-only job `13180877` completed in 08:40:19 in the fresh root `native/zebrafish/RM2-mask-recovery-v2`, also without rerunning classification. The two mask-only recovery cells consumed 39,167 Slurm seconds combined.

A tiny engineering-only probe using the pinned RepeatMasker image, a custom classified library, a tiny FASTA, and the same two default FamDB binds returned 0 and generated `.out`, masked FASTA, and GFF outputs. This validates the repaired container path; it is not a benchmark result.

The recovery script validates the failed parent state, `-LTRStruct`, the ordered terminal log markers, and the top-level final library before starting. It fails closed on nonzero classifier/masker returns and on a failed native summary. The tiny dual-FamDB probe remains engineering evidence only and is not substituted for either native result.

## RM2 summary metadata repair

The first `annotation_summary.json` files were generated from RepeatMasker GFF3 attributes. Those records expose a `Target "Motif:..."` name rather than a stable class/family field, so the old summaries reported every row as `Motif`. The completed numeric score was unaffected because its RM2 parser already reads the native `.out` class column. The cross-contig union calculation also had to be corrected: intervals are now merged separately within each `(class, contig)` pair before class totals are summed.

Private CPU job `13189316` completed in 70 seconds. It copied each old summary byte-for-byte to `annotation_summary.original-gff-20260924.json`, rewrote canonical `annotation_summary.json` from the corresponding native `.out`, and emitted compact provenance sidecars under `rm2-summary-repair-20260924/`. It did not modify the GFF, `.out`, masked FASTA, library, status file, or any prior score output.

The corrected summaries contain 713,681 chicken rows with a 152,014,157-bp union and 5,036,276 zebrafish rows with a 1,001,966,212-bp union. Their principal known-class unions are chicken DNA 15,535,555 bp, LINE 80,761,630 bp, LTR 19,277,831 bp, SINE 708,292 bp, and Unknown 22,486,545 bp; zebrafish DNA 651,704,846 bp, LINE 65,606,237 bp, LTR 121,945,721 bp, RC 45,825,095 bp, SINE 15,096,086 bp, Retroposon 744,900 bp, and Unknown 44,999,555 bp. These are descriptive native composition values and do not replace the binary comparator metrics.

## Completed D score and comparison status

CPU job `13180826` completed the fixed D score in 79 seconds with the original failed native cells recorded as NA. Independent chr10/20 F1 is 0.479174 for chicken and 0.878294 for zebrafish; chicken recall is only 0.321670. These constrain coverage claims despite positive downstream gene utility. See [D results](D-RESULTS-13180826.md).

The first whole binary score `13180901` and class-map score `13180902` completed with the two RM2 recovery roots and explicit NA for unavailable EDTA cells. A fresh chicken EDTA checkpoint recovery is being handled separately; any score rerun must wait for that terminal artifact and use the repaired canonical summaries. The benchmark remains a comparator-relative result with an explicit EDTA availability boundary, not a complete EDTA/RM2 matrix across the two genomes.

The active chicken EDTA retry is `13189201`, which has loaded the original Module4/Step7 checkpoint and progressed past Step8 to Step9. Fresh follow-up binary/class scores `13189350`/`13189351` wait on `afterany:13189201`, use the corrected canonical summaries, and write separate `score-edta-retry-20260924` outputs. Previous scores remain preserved.
