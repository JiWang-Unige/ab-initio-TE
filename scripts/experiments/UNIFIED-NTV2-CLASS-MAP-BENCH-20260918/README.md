# UNIFIED-NTV2-CLASS-MAP-BENCH-20260918

This is a quality-only, class-level comparison on fixed `chr10` and `chr20`
of chicken `galGal6` and zebrafish `danRer11`. The chromosomes were fixed by
the D exposure audit before native outputs or class scores were read. The
same-assembly UCSC RepeatMasker layer is a comparator, not exhaustive
biological truth.

The NTv2 arm uses the validation-selected eight-state class checkpoint from
representation training job `12889091` and the native NTv2 loader plus
six-base token projection already used by the matched class trainer. It runs
non-overlapping 4,096-bp windows and projects native token argmax labels back
to base spans. No threshold, calibration, reference label, or chromosome
selection is used during inference. It writes `predicted_classes.bed.gz` with
one label run per base (`BG`, `SINE`, `LINE`, `LTR`, `DNA`,
`KNOWN_OTHER_TE`, `AMBIGUOUS_TE`, `UNCLASSIFIED`, or `NONCALLABLE`) and a
per-chromosome timing summary.

The native comparators are the completed whole-genome EDTA and RM2 cells. RM2
is parsed from its native `annotation.out`; EDTA is parsed from its native
`annotation.gff3` class attributes after the terminal file's feature schema is
inspected. Region/chromosome/contig and structural LTR/TIR child rows are not
painted as independent TE bodies. A `repeat_region` container is suppressed
only when a complete TE child or explicit match-part evidence replaces it;
complete bodies such as `LTR_retrotransposon` are retained even when they have
structural children. Explicit simple/low-complexity/RNA-like classes are not
treated as TE calls, and native Unknown/`?` remains an explicit output state.
Overlapping native rows use a fixed `(start,end,ontology_id)` order and ordered
paint; reference labels never resolve prediction overlaps.

The executable order is:

```bash
sbatch prepare.sbatch
sbatch --dependency=afterok:<prepare-array>:<class-training-tail> \
  --export=ALL,CLASS_MODEL=/path/to/last2-seed42-12889091/best_model \
  run_class_map.sbatch
sbatch --dependency=afterok:<class-map-array>:<edta-rm2-tail> \
  score.sbatch
```

The class-map GPU array is throttled to one GPU (`%1`) and is independent of
native discovery. The scorer is CPU-only and refuses to score incomplete
native cells or a missing class map. It writes a common source array and
callable mask for all methods, method-normalized per-base runs, known-five
macro metrics, full eight-state confusion, and a true-TE conditional readout.
The binary D output is retained as `N/A` because it has no class prediction.

The source Unknown/ambiguous strata are reported in full and excluded from
the primary known-five denominator. They are not converted to BG. Native
Unknown rows are retained in the full eight-state confusion and in native
parser statistics. The native whole-genome wall times are provenance fields;
this experiment does not claim a full-genome class-map CPU runtime.
