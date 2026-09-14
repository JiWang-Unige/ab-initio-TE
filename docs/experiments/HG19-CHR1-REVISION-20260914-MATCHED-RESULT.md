# hg19–CHM13 matched-background and sequence result

This record reports the bounded follow-up defined in
`configs/HG19-CHR1-REVISION-20260914-MATCHED.json`. It keeps the original
model, thresholds, source regions, and old TP/FP/FN/TN assignments fixed. The
new CHM13 annotation is joined only after source-only matching has finished.

## Execution

- CHM13v2.0 FASTA acquisition: Slurm `12708300`, `COMPLETED`; 981,185,361
  bytes, gzip test passed. The raw FASTA remains on Baobab and is not copied
  into the repository.
- First matcher attempt: Slurm `12708378`, `FAILED` because one non-strict
  chain row lacked source covariates. Its output and failure log are retained
  as historical evidence and were not used as a result.
- Corrected source-only qualification and matching: Slurm `12708406`,
  `COMPLETED`.
- Post-selection CHM13 support join: Slurm `12708553`, `COMPLETED`.

All jobs used the Bamboo jump route and the bounded CPU settings in the
protocol. The compact support output is archived at
`reports/HG19-CHR1-REVISION-20260914-MATCHED/support-12708553/summary.json`.

## Mapping and sequence qualification

All 97,242 old EVAL intervals were retained: TP 25,775, FP 21,402, FN
24,588, and TN 25,477. Existing unique reciprocal same-length mappings in
source and target chr2/3/4 yielded 93,116 qualified rows: TP 23,962, FP
21,235, FN 24,333, and TN 23,586. The remaining 4,126 rows remain in the
population but were not used in the qualified matching pool.

Among qualified rows, 93,063 were a single complete chain block. Fifty-three
had an internal source gap and were retained as `INTERNAL_SOURCE_GAP` but
excluded from strict sequence qualification (TP 29, TN 24). No FP or FN row
was in this stratum. Equal outer span was not used as evidence of a
base-by-base mapping.

The sequence comparison was performed against the source hg19 FASTA and the
acquired CHM13v2.0 FASTA, using the chain orientation and reverse-complementing
minus-orientation target slices. Of the strict rows, 84,221 were
`SEQUENCE_EXACT` and 8,842 had one or more aligned-base mismatches:

| old state | exact | mismatch | chain-not-strict | qualified total |
|---|---:|---:|---:|---:|
| TP | 19,767 | 4,166 | 29 | 23,962 |
| FP | 20,855 | 380 | 0 | 21,235 |
| FN | 23,836 | 497 | 0 | 24,333 |
| TN | 19,763 | 3,799 | 24 | 23,586 |

This is a sequence-correspondence diagnostic. It does not recompute the old
same-base F1 and does not claim that any old FP has been rescued.

## Source-only matched controls

The case pool contained all 21,235 qualified old FP rows. Controls were
qualified old TN rows selected using only source chromosome, exact source
length, old-TE relation, source non-ACGT count, old-TE distance bin, and a
0.02 source-GC-fraction tolerance. The fixed CHM13 annotation, target
sequence identity, and model probability were not read during selection.

There were 18,649 matched FP–TN pairs and 2,586 unmatched FP rows. The match
rate was 87.82%. The matched pairs used 2,931 unique TN controls; 1,357
controls were reused, with a maximum reuse count of 775. These reuse and
imbalance diagnostics are material: the paired numbers below are descriptive
support statistics, not a formal enrichment test.

| old-TE relation | qualified FP | matched | unmatched |
|---|---:|---:|---:|
| ADJACENT (boundary-extension candidate) | 17,548 | 16,541 | 1,007 |
| ISOLATED | 3,687 | 2,108 | 1,579 |
| OVERLAP | 0 | 0 | 0 |

## Fixed CHM13 support after matching

The following table joins the already computed 2022 CHM13 overlap fields only
after controls were selected. Each fraction has 18,649 matched pairs as its
denominator; a reused TN contributes to the pair-weighted control count each
time it is paired. The `unique TN` column uses the 2,931 distinct controls as
the denominator.

| category / layer | FP supported | FP fraction | matched TN supported | TN fraction | FP−TN fraction | unique TN supported / n |
|---|---:|---:|---:|---:|---:|---:|
| TE / any | 3,331 | 17.86% | 2,789 | 14.96% | +2.91 pp | 556 / 2,931 (18.97%) |
| TE / ≥50% | 2,946 | 15.80% | 2,087 | 11.19% | +4.61 pp | 332 / 2,931 (11.33%) |
| TE / ≥80% | 2,639 | 14.15% | 1,990 | 10.67% | +3.48 pp | 288 / 2,931 (9.83%) |
| UNKNOWN / any | 0 | 0.00% | 0 | 0.00% | 0.00 pp | 0 / 2,931 |
| UNKNOWN / ≥50% | 0 | 0.00% | 0 | 0.00% | 0.00 pp | 0 / 2,931 |
| UNKNOWN / ≥80% | 0 | 0.00% | 0 | 0.00% | 0.00 pp | 0 / 2,931 |
| NONTE / any | 551 | 2.95% | 1,133 | 6.08% | −3.12 pp | 170 / 2,931 (5.80%) |
| NONTE / ≥50% | 437 | 2.34% | 1,047 | 5.61% | −3.27 pp | 120 / 2,931 (4.09%) |
| NONTE / ≥80% | 382 | 2.05% | 989 | 5.30% | −3.25 pp | 82 / 2,931 (2.80%) |
| UNRECOGNIZED / any, ≥50%, ≥80% | 0 | 0.00% | 0 | 0.00% | 0.00 pp | 0 / 2,931 |

The fixed overlap table has no `UNKNOWN` or `UNRECOGNIZED` support rows in
this selected population; the zeros are therefore a property of that input
table, not evidence that these biological categories are absent in CHM13.

The TE support split by old-TE relation is:

| relation | pairs | any FP / TN | ≥50% FP / TN | ≥80% FP / TN |
|---|---:|---:|---:|---:|
| ADJACENT | 16,541 | 2,928 / 2,358 (17.70% / 14.26%) | 2,558 / 1,720 (15.46% / 10.40%) | 2,264 / 1,642 (13.69% / 9.93%) |
| ISOLATED | 2,108 | 403 / 431 (19.12% / 20.45%) | 388 / 367 (18.41% / 17.41%) | 375 / 348 (17.79% / 16.51%) |

The direction is therefore not uniform across the two relation strata. In
particular, the isolated subset does not support a general FP excess. Given
control reuse and the absence of a pre-specified matched-control inference
test, these values should be presented as a descriptive, annotation-aware
diagnostic rather than as confirmation that old FP labels are wrong.

## Scope and validation

### Joint exact-sequence subset

Slurm `12708578` subsequently stratified the **already selected pairs**,
without choosing new controls. Both members must have a strict complete
chain path, exact hg19–CHM13 sequence equality and no non-ACGT source bases.
This retained 18,079 pairs using 2,729 unique controls; maximum reuse remained
775. The other 570 pairs remain reported in separate sequence strata.

| same-sequence pair stratum | pairs | TE any FP / TN | TE ≥50% FP / TN | TE ≥80% FP / TN |
|---|---:|---:|---:|---:|
| All joint-exact pairs | 18,079 | 17.40% / 14.14% | 15.42% / 11.35% | 13.88% / 10.84% |
| ADJACENT | 16,070 | 17.24% / 13.36% | 15.09% / 10.56% | 13.42% / 10.10% |
| ISOLATED | 2,009 | 18.67% / 20.36% | 18.07% / 17.67% | 17.52% / 16.77% |

The sequence qualification preserves the same interpretation: the contrast
is concentrated at existing TE boundaries, while isolated candidates do not
show a consistent excess across support thresholds. This narrows the useful
manuscript point to annotation-version/boundary sensitivity. It does not
justify a numerical correction to F1 or a general discovery-of-missed-TE
claim. Reused controls and genomic dependence preclude interpreting these
pair counts as independent replicates.
[Joint sequence-qualified evidence](../../reports/HG19-CHR1-REVISION-20260914-MATCHED/support-12708553/exact-support-12708578.json)

The source-only matcher tests passed locally and on Baobab, including
single-block and internal-gap chain handling, negative orientation, old-TE
boundary relations, source covariates, unmatched FP retention, and control
selection. The post-selection support-join fixture and compile checks passed
locally and on Baobab. The production summary records the complete old-state
denominators, chain and sequence strata, all three support layers, all four
support categories, relation-specific counts, control reuse, and the fact
that target annotation was not used for selection.

No new target label was used to choose a control. No same-base F1, rescue
claim, or enrichment p-value is produced by this follow-up. The result is
sufficient to document the annotation-aware FP diagnostic and the limits of
that interpretation; it does not by itself establish a corrected benchmark
metric.
