# SF5 ontology closure: protocol and run record

Status: protocol implemented; Slurm run is recorded below. This is a new
seed-42 experiment and does not modify the historical SF5 checkpoints or
their reported scores.

## Question

The historical SF5 head used six IDs (`BG`, `SINE`, `LINE`, `LTR`, `DNA`,
`Unknown`). Its full source metadata contains six species, but the historical
Trainer scored only the first 1,200 validation and test windows. The new run
tests whether an explicit status ontology can be evaluated with the complete
balanced allocation and removes the mixed `Unknown` interpretation.

The target is a class/status classifier, not a specific-superfamily
annotator. The four named TE labels are RepeatMasker broad classes. A family
name is retained only as source provenance and is not treated as a learned
superfamily label.

## Frozen protocol

The source is the existing `comparator_plus_unknown` column in
`software_outputs/repeatmasker_dfam/02_ready_by_design/B_animal_production/SPLIT_MANIFEST.tsv`.
No raw genome, RepeatMasker run, or sealed evaluation asset is changed. The
window is 4,096 bp with step 4,096 and the historical `N` fraction limit of
0.2. The exact chromosome allocation is fixed in the YAML and prep script:

| species | train | validation | test |
|---|---|---|---|
| mouse | chr1 | chr2 | chrX |
| zebrafish | chr4 | chr7 | chr5 |
| chicken | chr1 | chr2 | chr3 |
| western_clawed_frog | chr1 | chr2 | chr5 |
| fruit_fly | chr3R | chr3L | chr2R |
| c_elegans | chrV | chrX | chrIV |

Each species contributes 900 train, 240 validation, and 360 test windows.
The new checkpoint is selected by the complete 1,440-window validation set and
evaluated once on the complete 2,160-window test set. Seed, optimizer settings,
class weights, and the single 8-label head are in the YAML.

## Ontology and denominator

| id | label | source rule | interpretation |
|---:|---|---|---|
| 0 | BG | no selected comparator interval | comparator-uncovered background; not independently verified non-TE |
| 1 | SINE | source class `SINE` without `?` | broad class |
| 2 | LINE | source class `LINE` without `?` | broad class |
| 3 | LTR | source class `LTR` without `?` | broad class |
| 4 | DNA | source class `DNA` without `?` | broad class |
| 5 | KNOWN_OTHER_TE | `RC` or `Retroposon` without `?` | recognized TE class outside the four broad classes |
| 6 | AMBIGUOUS_TE | `?` in source class or family | unresolved/ambiguous TE annotation |
| 7 | UNCLASSIFIED | `Unknown`, `Unspecified`, empty or otherwise unrecognized source class | unresolved annotation candidate |

The input export contains no separately labeled non-TE repeat class. Therefore
`BG` is not a confirmed biological negative, and `UNCLASSIFIED` is not a
confirmed TE truth label. The results report supports and source provenance
for every bucket. The primary material endpoint groups IDs 1--7 as comparator
material; per-class and status metrics remain separate. A species-level macro
average is interpreted over labels with positive support in that species; the
support table is mandatory because several status labels are absent or very
rare in individual species. It is not a fixed eight-label comparison unless
the absent-label convention is stated explicitly.

## Historical comparison

The old full metadata describes 5,400 train, 1,440 validation, and 2,160 test
windows. The old scoring prefix used 1,200 validation windows (no
*C. elegans*) and 1,200 test windows (mouse, zebrafish, chicken, and 120
western-clawed-frog windows only). The old checkpoint is retained as a
collapsed baseline, with new IDs 5--7 mapped to old `Unknown`; it is not
retroactively selected by the repaired validation set.

Because the new head is trained from the pretrained initialization while the
collapsed comparator is an existing SF5 checkpoint, their score difference is
descriptive and does not identify the isolated causal effect of label
splitting. A matched old six-label retraining would be required for that
ablation.

## Implementation and outputs

- Config: `configs/SF5-ONTOLOGY-CLOSURE-20260915.yaml`
- Data builder: `scripts/experiments/SF5-ONTOLOGY-CLOSURE-20260915/prepare_ontology_data.py`
- Training/evaluation: `scripts/experiments/SF5-ONTOLOGY-CLOSURE-20260915/ontology_task.py`
- Historical collapsed baseline: `scripts/experiments/SF5-ONTOLOGY-CLOSURE-20260915/evaluate_legacy_baseline.py`
- Contract tests: `scripts/experiments/SF5-ONTOLOGY-CLOSURE-20260915/test_ontology_contract.py`
- Slurm launcher: `scripts/experiments/SF5-ONTOLOGY-CLOSURE-20260915/train_and_eval.sbatch`

Remote data and checkpoints stay under the Baobab work area. Only compact
metadata, metrics, status and logs are copied into the report directory.

### Preparation result

Job `12731940` completed successfully. The generated files contain exactly
5,400 train windows, 1,440 validation windows and 2,160 test windows, with
900/240/360 windows for each of the six species. The train painted base counts
are `BG=13,173,894`, `SINE=275,037`, `LINE=2,985,143`, `LTR=2,778,599`,
`DNA=2,344,865`, `KNOWN_OTHER_TE=209,711`, `AMBIGUOUS_TE=218,675` and
`UNCLASSIFIED=132,476`; these counts describe the selected comparator labels,
not an independent biological truth set.

### Run status

| stage | job | status | output |
|---|---|---|---|
| source/window preparation | 12731940 | COMPLETED | `reports/SF5-ONTOLOGY-CLOSURE-20260915/prep-12731940/` |
| ontology training + full validation/test | 12731987 | RUNNING | remote run/report pending completion |
| collapsed legacy baseline | pending | pending | pending |

The protocol is scientifically interpretable only when all expected window
counts and per-class supports are present. A failed or incomplete job remains
in the denominator and is not presented as a classifier result.

## Limits on claims

This run can repair the six-species coverage and quantify performance under an
explicit split of the historical `Unknown` bucket. Because the new head and
the collapsed comparator are not a matched retraining pair, their difference
does not identify a causal effect of the ontology split. It cannot establish
independent biological truth, copy-level insertion recovery, family-level
annotation, or all-vertebrate robustness. The six species are the existing
animal panel; the held-out species and source-library qualification remain
separate questions.
