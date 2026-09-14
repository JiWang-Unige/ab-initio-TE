# hg19 to CHM13 matched background and sequence qualification

This is a bounded follow-up to the completed mapping qualification and fixed
2022 annotation-overlap run. The rules in
`configs/HG19-CHR1-REVISION-20260914-MATCHED.json` are written before reading
the CHM13 FASTA or joining any precomputed new-annotation support fields.

The population is the complete old EVAL export: every TP, FP, FN, and TN
interval remains in the output. Chain and sequence qualification is restricted
to the existing `UNIQUE_RECIPROCAL_SAME_LENGTH` mappings on source and target
chr2/3/4. The existing forward destination is treated as fixed. The forward
chain must expose a path covering the complete source interval and mapping
exactly to that destination; the reverse chain must cover the complete target
interval and return exactly to the original source interval. A chain path is
strictly internally bijective only when every source base is covered and the
query blocks are contiguous in chain orientation. A one-block path is reported
as `SINGLE_BLOCK`; a multi-block path with no internal gap or indel is
`MULTIBLOCK_CONTIGUOUS`. Internal source gaps, target gaps/indels, and target
overlaps are retained in separate strata and excluded from strict sequence
qualification. Equal outer span alone is never treated as proof of a
base-by-base correspondence.

The source sequence is the already used hg19 FASTA. The target sequence is
CHM13v2.0 FASTA acquired separately by Slurm if no existing copy is present.
Only chr2, chr3, and chr4 records are loaded from either FASTA. For a forward
chain on `+`, the source and target slices are compared directly; for `-`, the
target slice is reverse-complemented before comparison. The report keeps GC,
non-ACGT, mismatch bp, and mismatch fraction for every sequence-checked
qualified interval. `SEQUENCE_EXACT` requires a strict internal path and zero
aligned-base mismatches; it does not hide non-ACGT counts.

Old TE boundaries are derived from the fixed old hg19 comparator using the
same known TE base classes as the training label contract. Intervals are
classified independently as:

- `OVERLAP`: overlaps the merged old TE union;
- `ADJACENT`: no overlap but touches an old TE boundary, treated as a
  boundary-extension candidate;
- `ISOLATED`: all other intervals, with positive distance to the nearest old
  TE boundary.

Distance is reported in bp and binned as `ZERO`, `1_10`, `11_50`, `51_200`, or
`GT_200`. The bins and all matching tolerances are fixed here before any
matching run.

For each qualified old FP, the control pool is qualified old TN only. The
control must have the same source chromosome, exact source length, old-TE
relation, exact source non-ACGT count, and old-TE distance bin. It must be
within 0.02 absolute source GC fraction. Among candidates, choose the minimum
absolute GC-fraction difference, then minimum boundary-distance difference,
then source row id. Controls can be reused; reuse counts and all unmatched FP
rows are retained. This selection uses no model probability, CHM13 annotation
support, target sequence identity, or hidden label. Matching is deterministic;
seed 42 is recorded for protocol consistency.

Only after the matching table is complete may the reporting pass join the
already computed CHM13 support fields. It reports TE, UNKNOWN, NONTE, and
UNRECOGNIZED at `any`, `ge50`, and `ge80` for matched FP and matched TN pairs,
both overall and by old-TE relation. It reports pair-weighted values because
reuse is allowed and also gives unique-control diagnostics. These are balance
and descriptive-support statistics, not an enrichment test, a biological
confirmation, a same-base F1 correction, or an FP-rescue claim.

All compute passes use Slurm with at most 8 CPU, 32 GB RAM, and 2 hours per
job. New outputs live below `HG19-CHR1-REVISION-20260914-MATCHED`; the prior
mapping, overlap, model, threshold, and source records are not modified.
