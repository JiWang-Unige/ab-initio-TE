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
| NTv2 class map | `run_class_map.py` / `run_class_map.sbatch` | target prep + representation tail `12889676`; `CLASS_MODEL` from class train `12889091` | submitted `12890969_[0-1]`, dependency-gated |
| EDTA/RM2 native normalization and score | `score_class_maps.py` / `score.sbatch` | class-map array + terminal WHOLE native EDTA/RM2 cells | submitted `12890970`, dependency-gated |

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
hour. No GPU is submitted without an `afterok` dependency. The score does not
modify the WHOLE binary scorer.

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
