# EarlGrey output qualification: sim100

Date: 2026-09-16
Protocol: `TE-LONG-BENCH-20260915`
Native job: `12738272_4` (continuation of the preserved EarlGrey work tree)
Score job: `12738470`

## Verdict

`12738272_4` produced the standard EarlGrey final output, and the native
adapter does not filter out GFF features. However, the resumed continuation
did not carry the requested initial `lineage.fa` library into the final
RepeatMasker library. The cell therefore has a valid native output file but
does not qualify as the intended full-library EarlGrey comparison. The
observed low score must not be interpreted as EarlGrey's intrinsic recall or
as evidence that the complete pipeline is naturally conservative.

## Output contract and adapter check

The benchmark implementation in
`scripts/experiments/TE-LONG-BENCH-20260915/native.py` runs:

```text
earlGrey -g /work/panel.fa -s longbench -o /work/eg -t 16 -q yes -l /work/lineage.fa
```

It explicitly selects:

```text
eg/longbench_EarlGrey/longbench_summaryFiles/longbench.filteredRepeats.gff
```

The remote output exists at:

```text
/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/outputs/TE-LONG-BENCH-20260915/native-12738272/sim100-earlgrey/work/eg/longbench_EarlGrey/longbench_summaryFiles/longbench.filteredRepeats.gff
```

The native status is `COMPLETED`, covers the full 100,000,000 bp input, and
records 35,363 native GFF rows. The final EarlGrey command exited 0. The score
job reads the resulting canonical prediction and reports for EarlGrey:

| metric | value |
|---|---:|
| predicted TE bp | 3,642,918 |
| precision | 0.987111 |
| reference-positive recall | 0.066004 |
| synthetic F1 | 0.123734 |

The adapter's GFF parser converts `start1/end1` to the benchmark's zero-based,
half-open coordinates (`start1 - 1`, `end1`) and preserves feature/class
attributes. Its GFF conversion has no TE-family or length filter. The scoring
code removes only classes explicitly classified as `NON_TE`; it does not
discard `RC/Helentron` or `Unknown` rows as a side effect of conversion.

## Actual final library and resume-path qualification

The installed EarlGrey source defines the expected sequence:

```text
firstMaskCustomLib -> buildDB -> RepeatModeler -> strainer
-> novoMask -> mergeRep -> sweepUp
```

When a starting library is supplied, `novoMask` runs
`cat $latestFile $RepSub` and uses the resulting
`longbench_Curated_Library/longbench_combined_library.fasta` for the final
RepeatMasker call. In this source, `RepSub` is assigned from `startCust` only
inside `firstMaskCustomLib` (the only `RepSub` assignment for `startCust`). On
a resumed run whose initial `.masked` file already exists, the branch at lines
629--635 skips `firstMaskCustomLib` and does not restore `RepSub` before
`novoMask`. This is a concrete resume-path failure mode, rather than an
output-selection issue.

The final work tree confirms that this happened in `12738272_4`:

| artifact | read-only evidence |
|---|---:|
| `/work/lineage.fa` supplied by the native wrapper | 3,633,839 bytes; 60,130 lines; Dfam headers such as `DF000000772.5` |
| `longbench_strainer/longbench-families.fa.strained` | 1,405 bytes |
| `longbench_Curated_Library/longbench_combined_library.fasta` | 1,405 bytes; 35 lines; eight `RND-*` de novo headers |

The combined library is byte-identical to the strained library in this work
tree and contains only the `RND-2`/`RND-3` de novo records inspected in its
headers. The final RepeatMasker `.out` likewise begins with `RND-2_FAMILY-16`
and `RND-3_FAMILY-*`, whereas the initial RepeatMasker `.out` begins with
`DF...`/`DR...` entries from the supplied lineage library. Thus the final RM
stage did not use the full initial `lineage.fa` library, even though the native
command included `-l /work/lineage.fa`.

`longbench.filteredRepeats.gff` remains the expected standard EarlGrey final
product after the actual final RM and merge stages; the path and adapter are
correct. The problem is upstream protocol fidelity in this resumed execution,
not selection of an earlier GFF or a canonical coordinate conversion error.

The same work tree contains both stages. Small native diagnostics show:

| stage | RepeatMasker diagnostic |
|---|---:|
| initial `longbench_RepeatMasker/panel.fa.prep.tbl` | 53,865,577 bp masked; 48,153,672 bp interspersed; LINE/LTR/DNA present |
| final `longbench_RepeatMasker_Against_Custom_Library/panel.fa.prep.tbl` | 3,642,588 bp masked; LINE/LTR/DNA all 0; rolling-circle 2,845,602 bp; unclassified 118,358 bp |
| EarlGrey `longbench.highLevelCount.txt` | 3,643,274 bp total interspersed repeat coverage |

The final summary is much smaller than the initial mask, but the size
difference cannot be assigned to EarlGrey's biological filtering or to a
general method property from this resumed cell. It is confounded by the
confirmed omission of the initial library. The 356 bp difference between the
final high-level summary and the score's 3,642,918 bp remains a canonical
handling/interval detail; it does not repair the missing-library problem.

## Run-environment notes

The EarlGrey log contains a timezone-database warning and a `bc: command not
found` message during the final tidy elapsed-time formatting. The biological
stages completed, the final GFF and summary files were written, and the native
wrapper recorded exit 0. These warnings are retained as run-quality metadata;
they do not alter output selection, coordinates, or the reported annotation
intervals.

## Scientific interpretation and action

Keep the native output and observed score as a preserved recovery artifact, but
label the EarlGrey comparison cell as failing the intended initial-library
protocol. Do not use its F1 to compare a full reference-assisted EarlGrey run
with fixed-library RepeatMasker, and do not replace the selected final GFF with
the initial RM output under the EarlGrey method label. A clean run or a
resume-safe repair that restores `RepSub` is required before drawing an
EarlGrey accuracy or conservativeness conclusion.

An explicit initial-mask versus final-merged diagnostic can be retained as a
separate ablation, but it does not repair this benchmark cell and was not run
here.

## Bounded protocol repair

`native.py` now patches the installed EarlGrey script to restore
`RepSub="$startCust"` immediately before `novoMask`; the generated Bash passes
`bash -n` and the patch is idempotent on both the installed source and the
preserved compatibility overlay. The independent
`earlgrey_recovery.py/.sbatch` driver accepts only a preserved `COMPLETED`
EarlGrey cell, copies it inside Slurm, removes only the final RM/merge/
landscape/summary caches, and reuses the initial mask, database and strained
library. It will accept a repaired cell only after verifying that the actual
final `longbench_combined_library.fasta` is the exact concatenation of the
strained library and `lineage.fa` and that the final GFF coordinates pass the
common adapter checks.

Recovery array `12739911` was submitted for both inputs. Its output is kept in
`native-12739911/{c_briggsae,sim100}-earlgrey`; final-library and repaired-score
evidence are pending. The original completed directories and the protocol-
invalid `12738470` score remain preserved.
