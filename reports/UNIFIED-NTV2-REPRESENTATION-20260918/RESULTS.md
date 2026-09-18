# UNIFIED-NTV2-REPRESENTATION-20260918

## Current status

`CLASS_TRAIN_AND_REPRESENTATION_LENGTH_PASS`. The exact-D-coordinate eight-state class
materialization is complete (Slurm `12887930`, `PASS`).  Native loader smoke
is also complete (CPU Slurm `12888482`, `PASS`; 49 seconds): both native
token-classification loaders initialized successfully, the class logits had
shape `(1,688,8)`, and the D encoder versus the fresh class-head encoder had
maximum hidden-state difference `0.0`.  This is a loader check, not a
scientific score. Class fine-tuning `12889091`, the three-arm supervised /
fixed-K representation readouts, and the repaired length-only context
diagnostic `12897975`/`12897980` all completed. The original length branch had
a deterministic source-slice indexing bug and is retained separately as a
blocked engineering attempt. A separate legacy CPU readout is complete and
is also recorded below.

The full SIB TEST exposure audit (`12889831`, PASS) found exact coordinate and
sequence overlap for 3 chicken records in D TRAIN, 9 zebrafish records in D
CAL, and 7 zebrafish plus 149 *C. elegans* records in D DEV.  This is therefore
a retrospective matched representation panel rather than untouched evidence;
no favorable subset was selected and no record was removed.  Homology outside
exact coordinates and NTv2 pretraining exposure remain unresolved.

## Completed preparation

| split | half-records | paired 8,192-bp tiles |
|---|---:|---:|
| TRAIN | 21,000 | 10,500 |
| CAL | 6,000 | 3,000 |
| DEV | 6,000 | 3,000 |

TRAIN has 1,500 paired tiles for each of human, mouse, chicken, zebrafish,
and pig, and 3,000 for *C. elegans* because the binary D training override
contains 6,000 half-records for that species.  CAL/DEV contain 500 paired
tiles per species.  Class labels remain eight-state ontology labels; source
Unknown/Unclassified intervals remain UNCLASSIFIED.

## Fixed comparison contract

The representation panel is the existing SIB split (train 1,843; val 809;
test 1,580; 512 bp each).  All arms use the native NTv2 tokenizer, final
encoder hidden state, and attention mean after excluding padding and
structural special tokens while retaining input N/UNK tokens.  Supervised
5-NN/logistic and fixed-K train-only K-means are evaluated separately for
known-five, full-eight, and conditional TE-four endpoints.  UMAP is
diagnostic only.  See the matching experiment document for denominator and
exposure caveats.

## Results table

The class result, the three-arm supervised/fixed-K representation readout, and
the repaired context-length diagnostic are complete. The first bounded
context-length attempt is explicitly blocked by a repaired engineering bug;
its retry result is in `LENGTH-RETRY-RESULTS-12897975.md`.
Existing historical results must not be copied into this table because the
old GENERanno class arm used a different backbone and the old NTv2 run used a
different special-token naming contract.

The matched SIB representation readout is in
`REPRESENTATION-RESULTS-12889676.md`: KNN known-five macro-F1 is
`.4885/.6394/.7261` for pretrained/binary-D/class-D-last2, full-eight is
`.4730/.5934/.6512`, and conditional TE-four is `.6342/.7197/.8417`.
The supervised and fixed-K endpoints are held to the exact SIB panel and
train-only fitting rules.

## Completed matched class DEV result

Class training `12889091` selected step 900 with CAL token macro-F1
`0.6022688433`. Its one-pass DEV result is token macro-F1 `0.6066181` and
expanded bp macro-F1 `0.6067215` (bp accuracy `0.9053371`). Pooled bp F1 is
BG `0.9495`, SINE `0.9061`, LINE `0.8827`, LTR `0.7797`, DNA `0.7589`,
KNOWN_OTHER_TE `0.4028`, AMBIGUOUS_TE `0`, and UNCLASSIFIED `0.1740`. The
full per-class and per-species token/bp tables are in
`CLASS-TRAIN-RESULTS-12889091.md`; raw outputs are under
`results/class_training-12889091/`.

## Completed legacy readout diagnostic

The fixed known-five SIB binary denominator contains 1,281 test records
(BG=360, TE=921).  This train-only CPU diagnostic fit a standardized logistic
probe on TRAIN and applied it once to TEST; the composition baseline used only
GC fraction, N fraction, and sequence length.  It did not tune a threshold or
hyperparameter on TEST.  Full confusion matrices and per-class metrics are in
`results/legacy-linear-12889615.json`, and the compact interpretation is in
`LEGACY-LINEAR-DIAGNOSTIC.md`.

| arm | linear probe macro-F1 | linear confusion (true rows, predicted columns) | composition macro-F1 |
|---|---:|---|---:|
| GENERanno pretrained | 0.5396 | `[[63,297],[69,852]]` | 0.4242 |
| GENERanno binary FT | 0.5794 | `[[81,279],[60,861]]` | 0.4242 |
| GENERanno class FT | 0.7367 | `[[221,139],[132,789]]` | 0.4242 |
| NTv2 pretrained | 0.5867 | `[[136,224],[192,729]]` | 0.4242 |
| NTv2 binary D | 0.7031 | `[[181,179],[109,812]]` | 0.4242 |

The composition probe predicts almost every test record as TE
(`[[2,358],[0,921]]`), whereas the embedding probes outperform this tested
linear composition baseline. This comparison does not exclude nonlinear
composition effects or species and label-source confounding. It is a
fixed-panel diagnostic, not an independent biological validation.

## Execution record

| stage | job | status | note |
|---|---:|---|---|
| matched class materialization | 12887930 | PASS | exact D coordinates; 21,000/6,000/6,000 half-records |
| native D→class loader smoke | 12888482 | PASS | historical CPU-only debug-cpu smoke, 4 CPU/48G/49s; no scientific score |
| class fine-tuning | 12889091 | PASS | fixed `last2`, seed42, 900 steps; best CAL token macro-F1 .6022688; DEV token/bp macro-F1 .6066181/.6067215 |
| matched three-arm extraction + length diagnostic | 12889676 | PASS | pretrained, binary D, class D-last2; SIB extraction PASS; original length branch `BLOCKED_NATIVE_OFFSET` |
| train-only evaluator | 12889677/78/79 | PASS | pretrained/binary_D/class_D_last2; kNN/logistic/K-means |
| original context-length evaluator | 12889680 | BLOCKED_NATIVE_OFFSET; scheduler COMPLETED, 3s | original blocked input preserved; not a length result |
| repaired length-only retry | 12897975 | PASS | `length_retry.sbatch` only; private GPU 1/4CPU/32G/5m20s; all 3 models × 3 contexts × 768 records verified |
| repaired length evaluator | 12897980 | PASS | private CPU-only, 4 CPU/16G/20s; unchanged train-to-DEV probes |
| legacy binary linear/composition diagnostic | 12889615 | PASS | completed caches; debug-cpu 4 CPU/16G/8s; fixed known-five 1,281-record denominator |
| SIB TEST coordinate/sequence exposure audit | 12889831 | PASS | full 1,580-record panel; exact-match overlaps: chicken TRAIN=3, zebrafish CAL/DEV=9/7, *C. elegans* DEV=149 |

Superseded extraction/evaluation submissions `12889459–12889463` and
`12889562–12889566` are `CANCELLED` and carry no scientific result.  They
were replaced by `12889676–12889680` after the length-diagnostic wrapper was
changed so a native offset mismatch is recorded as a bounded
`BLOCKED_NATIVE_OFFSET` status instead of failing the primary three-arm
extraction. The class job `12889091` is complete and remains the single
training submission; no duplicate GPU job was created.

The first legacy linear attempt (`12889536`, `FAILED`) tried to recover
sequences from feature metadata and produced no result.  It was replaced by
`12889615`, which checks feature-record order and uses the validated raw SIB
records only for the composition covariates; the reported JSON is from this
successful rerun.

The GPU stages are scheduled on `private-teodoro-gpu` with one RTX 3090:
class training requests 8 CPU/64G/2h and extraction requests 4 CPU/48G/45m.
The four downstream evaluators are CPU-only `debug-cpu` jobs (4 CPU/16G/15m)
and are held by `afterok` dependencies.  Materialization used an earlier
`shared-cpu` 4 CPU/32G job and the loader smoke above used `debug-cpu`; these
historical resource choices are retained for provenance and are not evidence
that the pending GPU stages ran.

## Legacy UMAP and binary denominator boundary

The prior `.5221` binary value and its confusion matrix use the same fixed SIB
test panel and known-five denominator (1,281 test records: BG=360, TE=921;
the three non-main4 states are excluded).  The historical BG plot is not an
independent measurement of that denominator: it was generated from a separate
TE-enriched/balanced 512-bp panel using the older exploratory projection
pipeline (`max_length=2048`, no added special tokens, all-data
StandardScaler/PCA50 followed by UMAP/KMeans).  Its exact sample membership
and coordinate-to-denominator identity were not established in the bounded
diagnostic.  It is therefore retained as an exploratory illustration only;
the new three-arm readout will use the fixed SIB record identities.
