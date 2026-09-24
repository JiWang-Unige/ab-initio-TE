# Frozen whole-genome comparison: final interpretable states

The chicken EDTA native workflow and its unchanged-denominator binary/class
scores are now complete. The remaining zebrafish EDTA cell is the preserved
128-GB out-of-memory failure, not a zero score. All frozen benchmark cells
have interpretable terminal states; this does not mean every method succeeded.

## Independent chromosome results

All values below use the fixed chr10/20 panel and the existing same-assembly
UCSC RepeatMasker comparator. Both species were present in D fine-tuning;
these are independent chromosomes, not unseen species or complete biological
truth. Binary and class endpoints have their separately frozen source-label
policies and must not be mixed into one denominator.

| Species | Method | Binary precision | Binary recall | Binary F1 | Known-five class macro-F1 | Conditional TE-four macro-F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Chicken | D binary | 0.938901 | 0.321670 | 0.479174 | N/A | N/A |
| Chicken | NTv2 class | N/A | N/A | N/A | 0.625913 | 0.641398 |
| Chicken | RM2 → RepeatMasker | 0.594979 | 0.849583 | 0.699844 | 0.609440 | 0.654189 |
| Chicken | EDTA | 0.483441 | 0.763503 | 0.592021 | 0.464938 | 0.467114 |
| Zebrafish | D binary | 0.815321 | 0.951810 | 0.878294 | N/A | N/A |
| Zebrafish | NTv2 class | N/A | N/A | N/A | 0.760377 | 0.786190 |
| Zebrafish | RM2 → RepeatMasker | 0.799611 | 0.958290 | 0.871789 | 0.688569 | 0.711482 |
| Zebrafish | EDTA | NA (OOM) | NA | NA | NA | NA |

Chicken EDTA binary TP/FP/FN are 1,134,560/1,212,285/351,433 bp, against
1,485,993 comparator-positive bp and 34,478,727 eligible callable bp. The
class primary support is 34,478,839 bp, as in the prior class result; the
112-bp difference reflects the pre-existing source policies, not a new
method-specific denominator. Chicken class full-eight macro-F1 is
0.446293/0.434748/0.332407 for NTv2-class/RM2/EDTA. Its zero-support class is
excluded from the macro by the frozen rule; all eight confusion rows remain.

D is substantially less complete than both native methods on chicken under
this binary comparator. On zebrafish D and RM2 are close, with opposite
precision/recall tradeoffs. The class model improves the primary macro-F1 over
both completed native methods on chicken and over RM2 on fish, but chicken
conditional TE-four still favors RM2. These outcomes support separate
material, category and downstream-utility claims, not universal superiority.
The prior PLE/Unknown mapping caveat remains in
[the RM2 comparison](RM2-COMPARISON-13180901.md).

Whole-assembly EDTA chicken F1 is 0.719512 (P=0.623909, R=0.849715), compared
with D 0.559412 and RM2 0.776525. Whole-assembly model scores include exposed
chromosomes and are descriptive. No new threshold, species, seed, label
mapping or region was selected from these outcomes.

## Native recovery and cumulative cost

Job 13190938 completed both native RAW aggregation (5.34 s) and FINAL/ANNO
(5,854.37 s), each return code 0, and the native log explicitly reported the
final library, annotation and annotation evaluation as finished. The wrapper
then failed because a recursive glob also selected EDTA's internal copies.
EDTA's top-level published GFF/library are the correct outputs after native
sequence-ID decoding; internal copies are not interchangeable.

Export-only job 13192771 selected those exact top-level products, verified the
native completion evidence, retained the failed source status and copied the
GFF, library and ID map into a fresh root. There were zero encoded annotation
IDs after decoding. It did not rerun annotation. The native `MAKER.masked`
file is a filtered hardmask (6.19%), separate from full TE annotation (12.97%),
and was not used as the full binary annotation or substituted for softmask.

| Chicken EDTA work | Slurm elapsed seconds |
| --- | ---: |
| Original attempts 12888165 + 12888133 | 166,862 |
| Four compatibility fixtures | 27 |
| Checkpoint-name failure 13180896 | 306 |
| TIR completion / missing Helitron 13189201 | 2,669 |
| Helitron/filter completion / invalid downstream stopped 13189902 | 3,255 |
| RAW aggregate + final annotation, exporter failure 13190938 | 5,948 |
| Export-only 13192771 | 4 |
| **Charged cell total** | **179,071 = 49h44m31s** |

The seven-day budget has 425,729 seconds unused. Main native attempts had
16 CPU/128 GB; export had 4 CPU/16 GB and fixtures are separately recorded,
so the table is accumulated elapsed allocation time, not a uniform CPU-hour
estimate. Current binary/class scores 13192796/13192797 cost 104/177 seconds
at 4/8 CPU, 32 GB. Earlier score attempts and engineering costs remain in
[the complete job ledger](recovery-jobs-20260924.json).

RM2 complete-workflow totals remain chicken 38h18m36s and fish 35h49m05s.
D chicken CPU inference alone took 110h39m04s, so there is no CPU speed
advantage over either completed native workflow. GPU inference uses different
hardware and is reported separately. Failed native attempts and model
training costs must not disappear in publication cost tables.

## Verification and preserved artifacts

The final [binary result](score-edta-export-20260925/result.json) and
[class result](../UNIFIED-NTV2-CLASS-MAP-BENCH-20260918/results/score-edta-export-20260925/result.json)
retain all numeric counts, labels and NA states. Ten binary numeric rows and
15 class endpoint objects were checked against TP/FP/FN; full-eight counts
sum to callable bp. Every pre-existing D/NTv2/RM2 metric object is unchanged
from the preceding score. See [validation](score-edta-export-20260925/validation.json).

The FASTA library descriptive summary was separately repaired to read the
classification after `#`, rather than treating the identifier as a class.
RM2 original summary versions are backed up and corrected sidecars accompany
[the export provenance](edta-export-13192771/status.json). This repair does
not change annotation, predictions or scientific scores. Native logs and
failed status are retained in [the compact source record](edta-native-13190938/status.json).

The old frozen benchmark is closed with its failures and limitations. The
new functional-mask pilot is a separately authorized development experiment;
its results cannot retrospectively change this comparison.
