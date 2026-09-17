# Fixed D: external nonmammalian positive-evidence results

Both complete native inferences, structural extractions and primary scores
finished on the preselected 4 × 4,194,304-bp panels. The same frozen D seed42,
CAL artifact, threshold and forward-only 4096-bp tiling were used for both.
Neither species is in the D task-supervision table; pretraining exposure is
unknown. These two new species are insects, not additional independent
vertebrate examples.

| Species | Positive layer | Positive bp | Recovered bp | Recovery |
|---|---|---:|---:|---:|
| Silkworm | Historical library | 3,722,232 | 2,285,642 | 61.41% |
| Silkworm | Structural LTR | 178,955 | 148,789 | 83.14% |
| D. simulans | Historical library | 377,883 | 278,171 | 73.61% |
| D. simulans | Structural LTR | 173,135 | 147,512 | 85.20% |

The structural layer uses native LTRharvest/LTR_FINDER and LTR_retriever pass lists; it is algorithmic support selected toward intact LTRs, not manually confirmed truth. The historical layer contains all eligible known TE classes. Their difference cannot be attributed solely to label quality because class, intactness and age differ.

Unannotated sequence remains unknown. Recovery denominators exclude non-ACGT bases. The plots show all four regional values and pooled positive-base recovery; the dots are not seeds or confidence intervals. No precision/F1, all-species >=0.8 conclusion, or biological insertion reconstruction is claimed.

For each species, `result.json` contains source paths, frozen regions, callable denominator, prediction coverage and native structural counts. Separate `source_decomposition.json` files, where present, are explicitly exploratory analyses added after the first silkworm primary result; they retain model misses both inside and outside the old annotation layer.

## Exploratory support outside the old TE annotation

| Species | Intact LTR candidates | Structural-positive bp outside old TE layer | Recovered bp | Missed bp | Recovery |
|---|---:|---:|---:|---:|---:|
| Silkworm | 32 | 137,134 | 109,380 | 27,754 | 79.76% |
| D. simulans | 25 | 1,754 | 1,495 | 259 | 85.23% |

The silkworm result supplies a concrete candidate annotation-gap observation: D detects 109,380 bp carrying native structural support outside the historical known-TE layer, while missing another 27,754 bp there. This supports coexistence of reference coverage differences and model misses; it does not certify these bases as biological TP. The outside-old-layer denominator in D. simulans is only 1,754 bp and is not a broad gap claim. Neither layer contrast alone explains the zebrafish-versus-pig/chicken ordering.
