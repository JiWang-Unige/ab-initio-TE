# Unified NTv2 class-map benchmark (2026-09-18)

## Question and fixed scope

This experiment tests whether the matched NTv2 eight-state class model can
produce a usable TE class map on chromosomes that were not observed in the D
training, calibration, or selection-development manifests. The fixed panel is
chicken `galGal6` `chr10`/`chr20` and zebrafish `danRer11` `chr10`/`chr20`.
Chromosome choice is recorded in the D exposure audit and is independent of
native outputs and class scores. The experiment is a quality comparison on
these four chromosomes, not a claim of whole-genome class accuracy or a CPU
full-genome timing result.

The NTv2 class arm uses the validation-selected checkpoint from representation
training job `12889091`, with the native NTv2-500M implementation. It imports
`sequence_tokens` from the matched class trainer and
`native_token_classifier` from the matched extraction code. Thus the backbone,
six-base token projection, special-token handling, and eight-state label map
are shared with the representation experiment. Inference uses non-overlapping
4,096-bp windows from contig origin zero, native token argmax, and base-span
projection. It performs no thresholding, calibration, score selection, or
reference-guided post-processing.

The eight states are `BG`, `SINE`, `LINE`, `LTR`, `DNA`, `KNOWN_OTHER_TE`,
`AMBIGUOUS_TE`, and `UNCLASSIFIED`. Non-ACGT bases are emitted as
`NONCALLABLE` runs and excluded from class denominators.

## Comparator contract

The source comparator is the same-assembly UCSC `rmsk.txt.gz` layer used by the
whole-genome benchmark. Source fields 11/12 are mapped with the frozen SF5
ontology: the four main classes retain their names, `RC`/`Retroposon` map to
`KNOWN_OTHER_TE`, question-mark classes map to `AMBIGUOUS_TE`, and
Unknown/Unspecified/unresolved classes map to `UNCLASSIFIED`. Explicit
simple-repeat, low-complexity, satellite, and RNA-like rows are mapped to BG
as documented source non-TE classes; unannotated bases also remain BG in the
comparator array. This is a source-dependent comparator convention, not
biological truth.

Source intervals are sorted by `(start,end,ontology_id)` and painted in that
order, with later intervals winning. This makes cross-row overlap deterministic
and is independent of every prediction. The scorer reports source
`UNCLASSIFIED` and `AMBIGUOUS_TE` bp/rows separately and excludes them from the
primary known-five denominator.

## Native output parsing

RepeatModeler2 plus RepeatMasker is read from the terminal `annotation.out`
produced by the whole-genome runner. RepeatMasker coordinates are converted
from 1-based inclusive to 0-based half-open. EDTA is read from terminal
`annotation.gff3` after inspecting the actual final TEanno feature schema;
class attributes (`classification`, `class_family`, `repeat_class`, `class`,
or `repclass`) are used when present. `region`, `chromosome`, `contig`,
`supercontig`, `sequence`, gene-like, target-site-duplication, and structural
LTR/TIR child features are skipped as independent bodies. A `repeat_region`
container is suppressed only when a complete TE child or explicit match-part
evidence replaces it. Complete bodies such as `LTR_retrotransposon` remain
eligible even when they have structural children, avoiding a false loss of
their internal sequence. Rows lacking a class attribute are counted as
skipped parent/missing-class rows unless their complete feature type has an
unambiguous class mapping. Explicit native simple/low-complexity/satellite or
RNA-like classes are skipped; native Unknown and question-mark classes remain
`UNCLASSIFIED` and `AMBIGUOUS_TE` respectively.

Native overlaps use the same fixed ordered paint rule, without inspecting the
source comparator. Native output is normalized to the same per-base run
format before scoring. If a native cell is not terminal-success, its
`annotation.gff3`/`annotation.out` is absent, or its `annotation_summary.json`
is missing, scoring stops with an explicit readiness error.

The EDTA schema rule was checked against a completed pinned TEanno example
before this benchmark was submitted. The example contains complete
`*_LTR_retrotransposon`, `*_TIR_transposon`, and `Helitron` feature rows with
`classification=...`, as well as structural `long_terminal_repeat` rows. On
that 100-Mb sample, the class parser and the whole binary parser produced the
same 91,257 merged material intervals and 40,921,429 bp. EDTA's auxiliary
`TEanno.bed` has a different union under its own format semantics and is not
used as a second score source; the frozen comparator remains the terminal
GFF3. See the [schema check](../../reports/UNIFIED-NTV2-CLASS-MAP-BENCH-20260918/SCHEMA-CHECK-20260918.md)
for the exact artifact and counts.

## Endpoints

For each method (`NTv2_class`, `EDTA`, `RM2`) the scorer emits:

1. primary known-five metrics over source `BG`, `SINE`, `LINE`, `LTR`, and
   `DNA` positions only, with per-class TP/FP/FN, precision, recall, F1, and
   macro values;
2. the full eight-by-eight reference-row/prediction-column confusion over all
   callable bases, retaining source Unknown and ambiguous rows;
3. a conditional true-TE readout over source `SINE`, `LINE`, `LTR`, and `DNA`,
   with exact per-class recall and any-main-TE recovery;
4. source class bp, Unknown/ambiguous bp, native parser rows, normalized run
   counts, and timing provenance.

The binary WHOLE D output is explicitly `N/A` for class endpoints. Its binary
material runs are not remapped into a class label. The result is comparator
relative and quality-only; it does not turn a high source agreement into a
claim of complete TE discovery.

## Execution status

The implementation files are under
`scripts/experiments/UNIFIED-NTV2-CLASS-MAP-BENCH-20260918/`. CPU target
preparation is independent and can run before the class checkpoint. The class
map GPU array is submitted only with an `afterok` dependency on target
preparation and representation tail job `12889676`; scoring is submitted only
after both native EDTA/RM2 cells and the class-map array are terminal-success.
See the companion status report and compact result files under
`reports/UNIFIED-NTV2-CLASS-MAP-BENCH-20260918/`.
