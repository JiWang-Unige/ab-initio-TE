# hg19 to CHM13v2 fixed-2022 annotation overlap

This appendix defines a descriptive annotation-support stage after the
completed mapping qualification. The definition is frozen in
`configs/HG19-CHR1-REVISION-20260914-CHM13-2022-OVERLAP.json` before the
2022 annotation rows are read.

The input is the complete mapping outcome table from the fixed old hg19 EVAL.
All source TP/FP/FN/TN rows remain in the output denominator. Only rows with
`UNIQUE_RECIPROCAL_SAME_LENGTH` and target chromosome chr2/chr3/chr4 are
eligible for target annotation overlap. Unmapped, ambiguous, non-reciprocal,
length-changing, and other failed mappings are retained with their original
status and empty annotation-support fields; they are not converted into
zero-overlap evidence.

The target annotation is the fixed CHM13v2 RepeatMasker output
`chm13v2.0_RepeatMasker_4.1.2p1.2022Apr14.out`. Only annotation rows whose
target chromosome is chr2, chr3, or chr4 are parsed; chr16, chr18, and
chr19–chr22 and all other target chromosomes are excluded before coordinate or
class parsing. RepeatMasker 1-based closed coordinates are normalized to
0-based half-open intervals.

Each annotation row is assigned independently to one category:

- `TE`: base class `SINE`, `LINE`, `LTR`, `DNA`, `RC`, or `RETROPOSON`;
- `UNKNOWN`: base class `UNKNOWN` or a class/family field containing `?`;
- `NONTE`: the known non-TE classes `SIMPLE_REPEAT`, `LOW_COMPLEXITY`,
  `SATELLITE`, `RNA`, `SNRNA`, `SCRNA`, `SRPRNA`, `TRNA`, and `RRNA`;
- `UNRECOGNIZED`: any other class, retained separately and never treated as
  known non-TE.

Within each category and target chromosome, overlapping annotation intervals
are union-merged. For every qualified mapped interval, the report records
category-specific union overlap in base pairs and three fixed support layers:

- `any`: at least one overlapping base;
- `ge50`: overlap divided by the qualified target interval length is at least
  0.50;
- `ge80`: overlap divided by the qualified target interval length is at least
  0.80.

TE, UNKNOWN, NONTE, and UNRECOGNIZED support are measured in parallel, so
overlapping source annotations are not forced into a single winner. This stage reads no new
model output and does not alter thresholds, windows, or models. It computes no
F1, no same-base score, and no FP-rescue claim. Equal source/target span from
the mapping stage does not establish an internal base-by-base bijection, so
the overlap is descriptive support only. Any matched-background analysis is
outside this bounded run and remains unperformed unless separately specified.

Execution is Slurm-only with at most 4 CPUs, 16 GB RAM, and 30 minutes. The
annotation file is already present on Baobab; no large download is performed.
