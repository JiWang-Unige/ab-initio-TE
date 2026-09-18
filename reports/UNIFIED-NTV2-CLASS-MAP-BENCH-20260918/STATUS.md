# UNIFIED-NTV2-CLASS-MAP-BENCH-20260918 status

Updated 2026-09-18. The implementation is ready and the target FASTA
preparation completed successfully. The class-map GPU and score jobs were
submitted with explicit dependencies and remain scheduler-gated until their
declared inputs are complete.

## Fixed panel

| species | assembly | target chromosomes | D exposure status |
| --- | --- | --- | --- |
| *Gallus gallus* | galGal6 | chr10, chr20 | absent from D TRAIN/CAL/DEV manifest |
| *Danio rerio* | danRer11 | chr10, chr20 | absent from D TRAIN/CAL/DEV manifest |

Preparation array `12890879` completed (`12890879_0` and `12890879_1`, exit
0). The prepared manifests record 35,017,127 bp for chicken (34,515,527 ACGT
and 501,600 non-ACGT) and 100,622,199 bp for zebrafish (100,505,689 ACGT and
116,510 non-ACGT). The exact
source FASTA and target lengths are preserved in
`outputs/UNIFIED-NTV2-CLASS-MAP-BENCH-20260918/prepared/*.manifest.json`.

The target chromosomes were fixed before reading native output or class scores.
They use complete source contigs, 0-based half-open coordinates, and all
ACGT positions. N/non-ACGT positions are retained as `NONCALLABLE` output runs
and excluded from class metrics.

## Contract and dependencies

| stage | implementation | dependency | status |
| --- | --- | --- | --- |
| target FASTA preparation | `prepare_targets.py` / `prepare.sbatch` | none | completed `12890879_[0-1]`, exit 0 |
| NTv2 class map | `run_class_map.py` / `run_class_map.sbatch` | completed target prep + class train `12889091`; retry after length `12897975` for GPU serialization | original `12890969_[0-1]` FAILED; repaired `12898018_0` map generation completed, `_1` running |
| EDTA/RM2 native normalization and score | `score_class_maps.py` / `score.sbatch` | repaired class-map array + terminal WHOLE native EDTA/RM2 cells | old `12890970` CANCELLED before start; new `12898022` dependency-gated |

The target preparation is completed as job `12890879` (the table's stage
label is retained for the original protocol; its current state is
`COMPLETED`). The class-map array `12890969` was submitted with
`afterok:12890879:12889676`, using the fixed checkpoint path
`.../class_training/last2-seed42-12889091/best_model`. The score job `12890970`
was submitted with `afterok:12890969:12888165:12888134:12888196:12888197`.

The terminal EDTA schema check is recorded in
`SCHEMA-CHECK-20260918.md`. On the pinned 100-Mb sample, the class parser and
the whole binary parser produce exactly the same 91,257 merged
`(chrom,start,end)` intervals (40,921,429 bp). EDTA's auxiliary `TEanno.bed`
is not the frozen score input and is reported only as an unused format
diagnostic because its union differs.

The class-map array is throttled to one private RTX 3090 GPU, 8 CPUs, 96G,
four hours. The score is CPU-only on the private partition, 8 CPUs, 32G, one
hour. Scientific preparation and checkpoint completion are required before
GPU inference; retry scheduling may use an `afterany` serialization gate
once those completed inputs have been verified. The score retains `afterok`
dependencies and does not modify the WHOLE binary scorer.

## Preserved failed attempt and span-length retry

The original class-map array `12890969_[0-1]` reached `FAILED` with exit
`1:0` after 27 s (chicken) and 25 s (zebrafish). Both logs terminate at the
same engineering assertion: the projected label length was 3,430 or 4,061
instead of the fixed 4,096-bp window. The failure is caused by the runner's
base-span expansion using `len(token)` after ambiguous 6-bp tokens have been
replaced by the five-character native tokenizer string `<unk>`. It is not a
model, label, chromosome, threshold, or resource result. The failed output
directories and logs remain preserved; no score is inferred from them.

The minimal repair imports the already frozen `token_span_lengths()` helper
from the matched trainer and expands each argmax by its original 6-bp (or
tail) source span. A direct fixture reproduces the historical old totals
`3,430` and `4,061` and gives `4,096` for both after the repair, including a
four-base tail. The repaired runner and score wrappers are synchronized to
the remote checkout. A fresh retry root is prepared at
`outputs/UNIFIED-NTV2-CLASS-MAP-BENCH-20260918/ntv2-spanfix-retry-20260918-12890969/`;
the original `ntv2/` failed outputs are never reused.

For the retry, submit the unchanged array contract with
`--export=ALL,CLASS_MODEL=<.../class_training/last2-seed42-12889091/best_model>,CLASSMAP_OUTPUT_ROOT=<retry-root>`
and the existing `afterok:12890879:12889676` inputs. The score wrapper now
accepts `CLASSMAP_OUTPUT_ROOT`/`--ntv2-root` and should use a fresh score
directory plus `afterok:<retry-array>:<four-terminal-native-cells>`. This
changes only the engineering output location and corrected projection; the
checkpoint, target chromosomes, class labels, windowing, and evaluation
denominators remain frozen.

### Active retry and score jobs

The repaired array is `12898018_[0-1%1]`, with
`afterany:12897975` to follow the length-only diagnostic on the second GPU
lane. Preparation `12890879` and selected-checkpoint training `12889091`
are already completed and verified. A first submission referencing old
completed preparation/extraction job IDs was rejected by Slurm with
`Job dependency problem` and allocated no job or resources; the accepted
submission retains only the active serialization dependency.

The actual fresh prediction root is
`outputs/UNIFIED-NTV2-CLASS-MAP-BENCH-20260918/ntv2-span-r1/`;
the earlier prepared `ntv2-spanfix-retry-20260918-12890969/` directory is unused.
New score job `12898022` reads `ntv2-span-r1` via the explicit
`CLASSMAP_OUTPUT_ROOT` and writes `score-span-r1`. Its dependency is
`afterok:12898018:12888165:12888134:12888196:12888197`.
Old score `12890970` never started, was stuck on the failed array, and was
cancelled with zero run time. It could not be reused because Slurm captured
its old batch script and original prediction-root argument at submission.

The two failed GPU array cells consumed 52 seconds of single-GPU allocation
time in total (27 + 25 s); those costs remain separate from the active retry.
No inference or benchmark score is reported from a submission alone.

The repaired chicken cell `12898018_0` subsequently completed (`0:0`,
9m30s allocated GPU time). Its native `summary.json`, retained in
`results/ntv2-span-r1/chicken-summary.json`, reports chr10/chr20 with
35,017,127 input bp, 34,515,527 ACGT bp, 8,550 windows, and 29,538 output
runs. The original projection failure did not recur. This establishes
completion of map generation, not benchmark accuracy; the common scorer
still waits for the native comparators. At this snapshot zebrafish
`12898018_1` is running and `12898022` remains dependency-gated.

## Mapping and metrics

The NTv2 map uses the native eight-state argmax from the matched class
checkpoint, not a binary threshold. Native RM2 `annotation.out` and EDTA
`annotation.gff3` are normalized to the same eight states. EDTA region-like and
structural child rows are excluded; a `repeat_region` container is suppressed
only when a complete TE child or explicit match-part evidence replaces it,
while complete bodies such as `LTR_retrotransposon` are retained despite
structural children. Missing-class/parent rows are counted in parser
diagnostics, and native Unknown/`?` stays explicit. Overlap painting is fixed
and never reference-guided.

The primary known-five endpoint excludes source `KNOWN_OTHER_TE`,
`AMBIGUOUS_TE`, and `UNCLASSIFIED` positions while reporting their complete
bp/row counts. A full eight-state confusion and conditional true-TE endpoint
are also required. The binary D method is `N/A` for class metrics.

No scientific result is recorded until the target preparation, class map, and
both native cells pass their terminal-output gates. Once complete, compact
JSON, metrics TSV, normalized per-base runs, and a manuscript-ready summary
will be added here.

## Transfer integrity note

During remote synchronization, a command initially flattened the experiment
README and protocol document into the repository root. The root `README.md`
was immediately restored with `git show HEAD:README.md`; the stray protocol
file was removed, and the two files were then synchronized to their intended
experiment directories. The local checkout had no `README.md` modification at
that point. The remote pre-incident uncommitted contents were not captured, so
their preservation cannot be independently proven; no further root-level
restoration was performed.
