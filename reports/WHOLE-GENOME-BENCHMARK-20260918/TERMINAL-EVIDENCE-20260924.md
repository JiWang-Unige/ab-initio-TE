# Whole-genome benchmark terminal evidence (2026-09-24)

This is an independent machine ledger for the frozen whole-genome benchmark. It preserves the original native output directories and their `status.json` files. The machine-readable record is [observed-terminal-20260924.json](observed-terminal-20260924.json).

The native jobs did not produce a complete set of four native cells (EDTA and RepeatModeler2 on the two assemblies). Both RepeatModeler2 cells completed all five discovery rounds and the `-LTRStruct` stage, then failed at the bundled FamDB classification step because the container's default FamDB was empty or not configured. Their top-level `RM_*/consensi.fa` and `families.stk` are therefore valid terminal post-`-LTRStruct` discovery products. The classification-only recovery uses those files in fresh roots and the fixed benchmark Dfam 4.0 asset; it does not repeat discovery.

Chicken EDTA reached the TIR-Learner stage but stopped in the nested swifter/Dask path, where daemon-process creation is the confirmed fatal event. Source review also found a pandas 3 positional-index compatibility issue at `x[0]` for `TIR_type`; the exploratory slice-index message is not treated as an independent biological coordinate failure. Zebrafish EDTA reached the same stage, was killed with the Slurm terminal state `OUT_OF_MEMORY` under 128 GB, and has no final annotation. The current zebrafish EDTA `status.json` is now `FAILED` because the wrapper later persisted `RuntimeError('EDTA failed')`; the earlier `RUNNING` observation and the Slurm OOM event are retained in the independent ledger rather than overwriting that file. `--force` was not used because it would substitute missing TIR categories with the EDTA fallback library and change the frozen contract.

The original score job `12891298` never started and is not a scientific result. No native comparator F1, precision, recall, or class score should be reported from that job. The eventual scorer must use explicit method roots and mark EDTA zebrafish as a terminal OOM/NA cell unless an explicitly authorized contract-preserving repair produces a fresh annotation.

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

The chicken initial recovery classified successfully in 436.50 s and wrote a 939,739-byte classified library, but its mask stage stopped in 25.95 s because the first wrapper did not bind RepeatMasker's two default FamDB library paths. The original root is retained. Mask-only job `13180772` uses a fresh root `native/chicken/RM2-mask-recovery-v2`, binds both fixed library paths, and reuses the successful classifier output without rerunning classification; its wall limit is reduced by the 477 s consumed by the failed continuation. The zebrafish continuation then reached the same terminal condition: classification returned 0 and wrote a 2,703,406-byte classified library, while RepeatMasker returned 1 after 19.77 s for the same missing default FamDB directory. Its original root and 934 s Slurm cost are retained. Mask-only job `13180877` started at 2026-09-24 01:23:17 +02:00 in a fresh root `native/zebrafish/RM2-mask-recovery-v2`, reuses that classified library without rerunning classification, and has a requested remaining wall budget of 507,074 s (Slurm rounded the limit to `5-20:52:00`).

A tiny engineering-only probe using the pinned RepeatMasker image, a custom classified library, a tiny FASTA, and the same two default FamDB binds returned 0 and generated `.out`, masked FASTA, and GFF outputs. This validates the repaired container path; it is not a benchmark result.

The recovery script validates the failed parent state, `-LTRStruct`, the ordered terminal log markers, and the top-level final library before starting. It fails closed on nonzero classifier/masker returns and on a failed native summary. The tiny dual-FamDB probe remains engineering evidence only and is not substituted for either native result.

## Completed D score and queued final comparison

CPU job `13180826` completed the fixed D score in 79 seconds with the original failed native cells recorded as NA. Independent chr10/20 F1 is 0.479174 for chicken and 0.878294 for zebrafish; chicken recall is only 0.321670. These constrain coverage claims despite positive downstream gene utility. See [D results](D-RESULTS-13180826.md).

Chicken EDTA checkpoint recovery `13180896` is now queued after `13180772`. Whole binary score `13180901` and class-map score `13180902` are queued with `afterany:13180772:13180877:13180896`, using the explicit fresh recovery roots. The complete schedule, resources and output paths are in [recovery-jobs-20260924.json](recovery-jobs-20260924.json). The benchmark remains scientifically incomplete until these attempts settle and the actual artifacts are interpreted; submission is not completion.
