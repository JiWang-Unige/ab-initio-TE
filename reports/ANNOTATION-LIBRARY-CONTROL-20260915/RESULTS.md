# Annotation-library control result

The fixed hg19 library-control experiment is complete.  The two RepeatMasker
annotations were produced by the preserved main run `12732075`; its two-hour
TIMEOUT occurred while scoring, after both annotation outputs had finished.
The existing legacy score table was complete and was byte-identical to the
legacy table produced by the repaired scorer.  Jobs `12735616` (same-library
score recovery) and `12735617` (no-reuse matching sensitivity) completed with
exit code 0 in 46 s and 52 s, respectively.

## Fixed input and denominator

Both libraries were run with RepeatMasker 4.2.2, `-pa 4 -xsmall -gff -lib`,
against the same 2,500-tile hg19 panel.  Each tile has an 8,192-bp center and
a 4,096-bp halo; the center denominator is 20,480,000 bp and the panel is
40,960,000 bp.  The qualified source table contains 97,242 intervals:

| source state | n |
| --- | ---: |
| TP | 25,775 |
| FP | 21,402 |
| FN | 24,588 |
| TN | 25,477 |

The original source-only matched table contains 21,235 FP rows and 18,649
matched pairs after its existing reuse policy; 2,586 FP rows are unmatched.
The no-reuse sensitivity table assigns 5,540 unique TN controls once and
leaves 15,695 FP rows unmatched.  No model score, target annotation, or new
library support entered either selection procedure.

## Library-level support

The legacy configuration is the frozen global Dfam/RepBase 2018 consensus
library (26,292 records; 51,089,915 bp).  The second is the human-lineage
curated Dfam 3.9 export (1,437 records; 1,812,756 bp).  This is a comparison
of library configurations: release date, taxonomic scope, curation, and
RepBase content are confounded and are not separated here.

The fraction of qualified intervals with any, at least 50%, or at least 80%
TE overlap was:

| library | state | any | >=50% | >=80% |
| --- | --- | ---: | ---: | ---: |
| Dfam/RepBase 2018 | TP | 82.96% | 81.48% | 78.51% |
| Dfam/RepBase 2018 | FP | 33.57% | 30.76% | 28.80% |
| Dfam/RepBase 2018 | FN | 68.73% | 65.20% | 63.62% |
| Dfam/RepBase 2018 | TN | 36.61% | 10.72% | 8.25% |
| Dfam 3.9 human curated | TP | 82.06% | 80.92% | 77.94% |
| Dfam 3.9 human curated | FP | 24.46% | 22.04% | 20.05% |
| Dfam 3.9 human curated | FN | 67.30% | 63.73% | 62.29% |
| Dfam 3.9 human curated | TN | 23.46% | 6.41% | 4.95% |

Changing the library therefore changes apparent TE support substantially,
especially for both FP and TN intervals, while the high TP support remains
similar.  Within the original matched pairs, the FP-minus-TN support
difference for the legacy library is +2.20, +3.92, and +3.24 percentage
points at the three overlap layers.  For the curated library it is +2.85,
+4.38, and +3.21 percentage points.  The no-reuse sensitivity gives the same
direction at the 50% and 80% layers (+2.65/+2.85 pp for the legacy library and
+4.98/+4.49 pp for the curated library); its any-overlap differences are
-0.67 pp and +1.81 pp, respectively.

These values show that library choice and reference coverage materially
affect which intervals receive external TE support.  They do not establish
that an individual model FP is a true TE, do not provide biological truth,
and do not justify relabelling FP/FN or recomputing model F1.

## Pair-summary field denominators

`difference_pp` uses only the 5,540 matched pairs in the no-reuse summary.
In contrast, `fp_supported` and `fp_fraction_of_all_cases` count all 21,235
eligible FP cases, including unmatched cases; `matched_tn_supported` and
`tn_fraction_of_matched_pairs` use matched controls. Do not divide every count
by 5,540 or subtract the two differently scoped fractions. The reported
matched differences above use the correctly scoped `difference_pp` field.

The matched population is approximately 26.1% of eligible FP cases; 15,695
remain unmatched. Control uniqueness removes reuse, not spatial/homology
correlation or selection into the matchable subgroup. These remain descriptive
contrasts, with no uncomputed significance claim.

## Provenance and compact artifacts

- Preserved annotation attempt: `12732075` (`TIMEOUT`, 2:00:29); both native
  annotation logs reach `ProcessRepeats: Generating table output` and `done`,
  with complete `.out` artifacts retained.
- Recovered score: `12735616` (`COMPLETED`, 00:00:46).
- No-reuse score: `12735617` (`COMPLETED`, 00:00:52).
- Stale dependent score `12732397` was cancelled after its dependency became
  unsatisfiable; its preserved pending record is not a result.
- Recovered score summary:
  [`library-score-existing-12735616/summary.json`](library-score-existing-12735616/summary.json)
- No-reuse summary:
  [`library-no-reuse-score-12735617/summary.json`](library-no-reuse-score-12735617/summary.json)
- The independent source-only and RepeatPeps evidence is in
  [`orthogonal-run-12732331/RESULTS.md`](orthogonal-run-12732331/RESULTS.md).

The large interval tables, panel FASTA, library FASTA files, and raw
RepeatMasker outputs remain on Baobab.  The repaired scorer preserves the
legacy interval table byte-for-byte while completing the second-library and
no-reuse summaries within the declared scoring resources.
