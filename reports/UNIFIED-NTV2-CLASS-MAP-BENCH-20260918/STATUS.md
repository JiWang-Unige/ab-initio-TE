# UNIFIED-NTV2-CLASS-MAP-BENCH-20260918 status

## 19:29 UTC follow-up, 2026-09-24

Chicken EDTA `13189201` completed its native TIR stage but failed in the
subsequent filter/final/annotation stage, so no completed EDTA annotation is
available. Class score `13189351` completed in 197 seconds with chicken EDTA
still explicit NA. All numeric endpoints and support counts are unchanged
from `13180902`; the failed attempt's root is updated in the NA metadata.
The complete snapshot is in `results/score-edta-retry-20260924/`. Its
successful scorer exit does not close the missing native comparator.

The native failure is missing Helitron raw output after the original TIR
interruption. Continuation `13189902` reuses the completed TIR and runs the
outstanding native branch under the same cell budget. The config points to
`EDTA-helitron-cont-13189902`; class score `13189917` waits on
`afterany:13189902`, writing fresh `score-helitron-cont-20260924`.

## Latest completed comparison, 2026-09-24

Score `13180902` completed in 170 seconds. Both RM2 methods are now scored
against the same fixed chr10/20 labels and callable denominators as NTv2.
Primary known-five F1 is NTv2/RM2 0.625913/0.609440 in chicken and
0.760377/0.688569 in zebrafish; conditional chicken TE-four favors RM2 and
full-eight differences are small. See [the complete comparison and limits](RM2-COMPARISON-13180902.md).

Chicken EDTA `13180896` failed in checkpoint-file validation before native
TIR. The corrected fresh attempt `13189201` has demonstrably resumed Module4
Step7 and entered Step8. The config now points to that new root. Follow-up
class score `13189351` waits on `afterany:13189201`, writes fresh
`score-edta-retry-20260924`, and preserves all earlier completed scores.
Zebrafish EDTA remains OOM/NA. The earlier pending/unsubmitted entries below
are historical snapshots, not the current state.

Updated 2026-09-24, after the repaired class-map score and native-recovery
handoff. Target preparation and both repaired class-map GPU cells are
complete. The historical dependency-gated score jobs `12898022` and
`12890970` were cancelled before start and produced no score file. A direct,
ledger-aware NTv2-only score is now complete in jobs `13180656` and preferred
rerun `13180671`; the latter has numeric NTv2 endpoints and explicit `NA` rows
for unavailable native cells. Map generation alone remains an accuracy
non-result, and the native-recovery comparison is still pending.

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
| NTv2 class map | `run_class_map.py` / `run_class_map.sbatch` | completed target prep + class train `12889091`; retry after length `12897975` for GPU serialization | original `12890969_[0-1]` FAILED; repaired `12898018_[0-1]` map generation completed |
| EDTA/RM2 native normalization and score | `score_class_maps.py` / `score.sbatch` | repaired class-map array; completed native cells are optional and failed/missing cells are explicit `NA` | preferred NTv2-only score `13180671` complete; native recovery comparison pending |

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
once those completed inputs have been verified. The score wrapper does not
modify the WHOLE binary scorer. A future score submission can use an
`afterany` dependency after class-map and native attempts settle; the updated
wrapper scores complete methods and records missing/non-terminal native cells
as `NA` rather than filling metrics with zero.

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
The previously submitted score job `12898022` was intended to read
`ntv2-span-r1` via the explicit `CLASSMAP_OUTPUT_ROOT` and write
`score-span-r1`; its dependency was
`afterok:12898018:12888165:12888134:12888196:12888197`. It was cancelled
before start after the native prerequisites failed or remained unavailable,
so it produced no score output. The local scorer is now prepared for a
future `afterany` submission with the same frozen labels and denominators.
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
completion of map generation, not benchmark accuracy; no common score was
produced by the cancelled job.

Zebrafish `12898018_1` also completed (`0:0`, 26m23s allocated GPU time).
Its native `results/ntv2-span-r1/zebrafish-summary.json` reports chr10/chr20
with 100,622,199 input bp, 100,505,689 ACGT bp, 24,567 windows and 616,802
output runs. For both species the native per-contig class counts sum to the
fixed input lengths and NONCALLABLE counts match non-ACGT counts. The two
successful cells consumed 35m53s of single-GPU allocation, or 36m45s when
including the preserved 52-second failed attempt. This is chr10/20 class-map
generation cost, not a whole-genome inference timing result. Score `12898022`
was cancelled before start and has no metrics; no class accuracy or method
superiority is inferred from these output-composition counts.

Read-only remote integrity checks passed for both `predicted_classes.bed.gz`
files: `gzip -t` succeeded, all records have four fields and valid labels, and
per chromosome runs are contiguous from coordinate 0 to the fixed chromosome
length with no gaps or overlaps. File label-length counts equal their native
summary counts (including `NONCALLABLE`); absent zero-count labels have no
emitted run by design.

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

The NTv2 class map is complete, but map composition alone is not an accuracy
result. The preferred terminal score `13180671` provides fixed-panel NTv2
accuracy endpoints and preserves
each missing or non-terminal native cell as a method-level `NA` row with its
execution reason; it never turns an unavailable native comparator into zero.
When terminal native outputs become available, only those completed methods
are normalized and scored under the unchanged callable mask, ontology, and
denominators. A terminal native cell with a missing annotation remains a hard
readiness error. A future recovery score will add native comparator metrics in
a fresh output directory; it will not replace this terminal NTv2-only result.

## NTv2-only terminal score (2026-09-24)

After the class-map BED.GZ integrity checks passed, the CPU scorer was run as
job `13180656` on the private partition with 8 CPUs, 32G, and a one-hour
limit. The class-map scheduler dependency was rejected because the historical
array identifier was no longer valid to Slurm; the map files themselves were
already verified complete, so the score ran directly against the fixed
`ntv2-span-r1` root. It completed in 1m15s with exit 0 and wrote
`results/score-ntv2-terminal-20260924/result.json` and `metrics.tsv`.

The completed NTv2 class endpoints are:

| species | primary-known macro-F1 | full8 macro-F1 | true-TE any-main4 recall |
| --- | ---: | ---: | ---: |
| chicken galGal6 chr10/chr20 | 0.625913 | 0.446293 | 0.837376 |
| zebrafish danRer11 chr10/chr20 | 0.760377 | 0.463252 | 0.933259 |

All four original native cells are explicit `NA` rows in this result. The NA
rows retain the observed status path and compact stage snapshot; they do not
contribute zero-valued metrics. The ledger-aware rerun records the zfish EDTA
Slurm terminal state as `OUT_OF_MEMORY` while preserving its later wrapper
`status.json` observation (`FAILED`, `returncode=2`, `max_rss_kb=127086448`).

After the observed terminal ledger became available, the same frozen score
was rerun as job `13180671` (private 8 CPU/32G, 1m15s, exit 0) into
`results/score-ntv2-terminal-ledger-20260924/`. The metrics are unchanged;
the corrected NA metadata now reports chicken EDTA/RM2 and zebrafish RM2 as
`FAILED`, and zebrafish EDTA as scheduler `OUT_OF_MEMORY`, with the original
status snapshot retained in parallel. This ledger-aware result is the
preferred terminal score for downstream reporting; the earlier `13180656`
directory remains preserved as the pre-ledger attempt.

The first RM2 continuation `13180658` (chicken) failed during RepeatMasker
after producing a classified library, while `13180659` (zebrafish) remains in
progress in its own `RM2-recovery` root. A separate chicken mask-only
continuation `13180772` is running in
`native/chicken/RM2-mask-recovery-v2`; it reuses the classified library and
does not overwrite the failed attempt. The final recovery score will use the
latest terminal RM2/mask-only roots and the chicken EDTA recovery root via
`afterany`; a failed or unavailable cell remains `NA`.

## Partial-native scorer readiness

The whole-genome native prerequisites are currently incomplete: the RM2
discovery assets exist but the classifier/FamDB stage did not yield a complete
classified annotation, and both EDTA cells lack terminal annotations. These
are execution states reported by the native benchmark owner; they are not
class-map accuracy results. The prior score job `12898022` was cancelled before
start and produced no score; the later NTv2-only terminal score is documented
above.

The scorer supports an explicit species-level `native_method_roots` override
for a recovery output tree. The RM2 recovery roots are now declared by the
native ledger, but they are not promoted into the current terminal score until
their outputs are complete. The preserved WHOLE directories remain unchanged;
no old FAILED directory is promoted by inference and no original native
directory is overwritten.

The fixed four-cell machine terminal ledger is
`reports/WHOLE-GENOME-BENCHMARK-20260918/observed-terminal-20260924.json`.
Its `slurm` and `native_status_snapshots` lists are joined by cell; the
attempt root is derived from each snapshot's `status_path`. When that root
matches the current native method root, the ledger's terminal state/reason are
attached to the NA record while the original `status.json` remains present as
an observed snapshot. A ledger entry for an old root cannot override a new
recovery root. The scorer does not infer `OUT_OF_MEMORY` from a return code or
a partial file; it uses the ledger's recorded scheduler state.

`score_class_maps.py` now evaluates the completed NTv2 map independently. For
each species and native method, a missing `status.json` or a non-`COMPLETED`
status becomes a method-level `NA` record carrying the exact root/reason.
Completed native cells are normalized and scored under the unchanged source
paint, callable mask, ontology, and denominator rules. A cell marked
`COMPLETED` but missing its required annotation or summary remains a hard
readiness error, so an incomplete terminal artifact cannot be mistaken for an
ordinary missing comparator. `metrics.tsv` includes status and reason columns;
unavailable methods have `NA` in every metric field and are never written as
zero.

The following bounded checks passed in the `te_benchmark` environment after
the change: `parser_smoke.py`; a three-state native fixture (missing,
FAILED, and COMPLETED-but-missing annotation); an observed-ledger root-join
fixture; and an end-to-end partial-score fixture in which NTv2 produced
numeric endpoints while EDTA/RM2 produced explicit `NA` rows. Jobs `13180656`
and ledger-aware rerun `13180671` both used CPU-only 8 CPUs, 32G, one hour on
the private partition and completed successfully. The recovery score remains
a separate fresh output that must wait for its native recovery dependencies,
using `afterany` where failed attempts are intentionally retained as `NA`.

## Transfer integrity note

An earlier handoff reported that a synchronization flattened an experiment
README and protocol document into the remote repository root, followed by a
`git show HEAD:README.md` restoration and removal of the stray protocol file.
This pass has no pre-incident remote status snapshot, exact command or timestamp
with which to verify that report or establish whether uncommitted README
contents existed. The incident is therefore retained as an unresolved transfer
provenance note, not a newly verified overwrite or a verified absence of loss.
The currently attributable misplaced transfer used the temporary directory
`.codex_sync_unified_ntv2/`, which was removed; it did not write the root README.
No further root-level restoration was performed.

## Current recovery dependency update

Both initial RM2 continuations completed classification but failed when the
masker could not find its default FamDB directory. Mask-only jobs `13180772`
(chicken) and `13180877` (zebrafish) now reuse the complete classified libraries
in `native/{species}/RM2-mask-recovery-v2`. The config points to these fresh
roots. They are not included in the already completed NTv2-only score above.
Chicken EDTA recovery `13180896` is queued after chicken mask-only `13180772`.
The config's chicken EDTA override points to
`outputs/RECOVER-EDTA-CHICKEN-20260924/native/chicken/EDTA-recovery-13180896`.
Final class score `13180902` is now queued with
`afterany:13180772:13180877:13180896`, CPU-only 8 CPU/32G/1h, reading the
verified `ntv2-span-r1` maps and writing fresh `score-recovery-20260924`.
This supersedes the earlier unsubmitted status. The original failures, NA rows
and all prior score outputs remain intact. A dependency or submitted score is
not a completed scientific comparison.
