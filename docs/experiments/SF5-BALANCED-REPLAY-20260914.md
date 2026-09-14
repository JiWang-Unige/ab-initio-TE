# SF5 balanced replay — 2026-09-14

This is a fixed, inference-only reanalysis of the already scored SF5 test
prefix. The historical SF5 runs and their aggregate metrics are not changed.
The purpose is to remove the species-count imbalance in the old scored
prefix, not to create an independent validation set.

## Frozen selection

The input is
`software_outputs/tefm_lock/PIPE-TEFM-LOCK-20260619/data/animal_sf5_w4096/test/data.jsonl.gz`.
The selector reads only the first 1,200 records, the exact prefix used by the
legacy `max_eval_samples=1200` score. Within the original file order it takes
the first 120 records for each of:

| species | old prefix records | new quota |
|---|---:|---:|
| mouse | 360 | 120 |
| zebrafish | 360 | 120 |
| chicken | 360 | 120 |
| western_clawed_frog | 120 | 120 |

The result is 480 windows. In the observed prefix these are record indices
0–119, 360–479, 720–839, and 1080–1199. Fruit fly and *C. elegans* are not
present in this old scored prefix and are explicitly excluded. No later test
records, human data, sealed species, or western-clawed-frog records after the
first 120 are read for scoring. Every selected record keeps its zero-based
source index, species rank, and original `chr/start/end` metadata; the
coordinates are trace metadata, not newly reconstructed genome coordinates.

The selection manifest is written before either checkpoint is loaded. Focused
tests cover first-per-species quota selection, missing-species fail-closed
behavior, original-order retention, and exclusion of non-target species.

## Models and token contract

The two existing checkpoints are loaded through
`pipelines/PIPE-TEFM-LOCK-20260619/superfamily5_task.py:load_model`:

- `SF5_base_pretrained_seed42/best_model`;
- `SF5_binary_h0_seed42/best_model`.

The training function is never called. The seed is recorded as 42 and is only
for deterministic run metadata; inference uses `model.eval()` and
`torch.inference_mode()`.

For every selected record, the actual checkpoint tokenizer is checked before
forward inference. The contract requires 4,096 raw nucleotides to produce
4,096 tokens, then one BOS and one EOS token, for a tensor of 4,098 tokens.
The scored positions are token indices 1 through 4,096, aligned one-to-one
with the 4,096 label positions. Tokenizer class, raw/input lengths, BOS/EOS
positions, and all-record pass status are stored for each model. A failed
contract stops the run rather than treating token positions as base pairs.

## Metrics and retained outputs

For each model the run stores raw per-position labels and predictions in a
compressed NPZ on Baobab only, together with the frozen selection indices. It
also writes six-class confusion matrices for every species and globally, with
true labels as rows and predicted labels as columns.

The main4 metric is named `main4_macro_f1_all_positions`: each SINE, LINE,
LTR, and DNA F1 is computed over all six-label valid positions, and the four
F1 values are averaged. BG and Unknown errors therefore remain in the FP/FN
counts for each main4 F1. The binary-material endpoint is explicitly BG
versus all five non-BG labels, including Unknown. Per-class precision, recall,
F1, support, prediction counts, Unknown recall, all-six macro-F1, and the
binary-material confusion counts are recorded.

The compact `selection.json`, `selection.tsv`, `metrics.json`,
`completion.json`, and `STATUS` can be copied locally. Raw prediction arrays
remain on Baobab unless a later release decision explicitly requires them.

## Interpretation boundary

The old 1,200-row aggregate score is numerically valid for the population it
actually scored: mouse 360, zebrafish 360, chicken 360, and western-clawed
frog 120. It cannot be described as a complete six-species typing evaluation
because fruit fly and *C. elegans* have no rows in that evaluated prefix.
This balanced replay changes the weighting to 120 records per observed species
and is useful for a transparent species-balanced comparison, but it reuses
the same old test prefix and the same two frozen checkpoints. It is therefore
not independent validation and does not establish six-species generalization.

All computation is submitted through Slurm with one RTX 3090 GPU, four CPUs,
64 GB RAM, and a two-hour limit. No threshold, label dictionary, test order,
checkpoint, or training configuration is changed.

## Implementation and run record

The implementation is
`scripts/experiments/SF5-BALANCED-REPLAY-20260914/replay.py`; focused tests
are in `test_replay.py`, with configuration in
`configs/SF5-BALANCED-REPLAY-20260914.json` and submission in
`sbatch/SF5-BALANCED-REPLAY-20260914.sbatch`. Local and Baobab static checks,
compile checks, JSON parsing, selection tests, and a direct entry-contract
test over every configuration section passed. The entry validates the
`selection.data_relpath`, `model_paths`, output, resource, metric, and
execution-policy fields before creating an output directory or loading a
checkpoint. The submission script and the resource record use the approved
shared GPU partition with one RTX 3090, four CPUs, 64 GB, and two hours.

The first Slurm job, `12708712`, was submitted on the private RTX 3090
partition and failed after one second before selection or model loading. The
failure was an entry-contract bug: the script read top-level
`config["data_relpath"]`, while the frozen configuration stores the path at
`selection.data_relpath`; its output directory and log are retained as
historical failure evidence. The corrected run uses the canonical
`selection.data_relpath` and `model_paths` fields, validates all later keys at
entry, and is submitted under a new job ID below. Its output is isolated at
`outputs/SF5-BALANCED-REPLAY-20260914/replay-<jobid>/`; after completion copy
only `selection.json`, `selection.tsv`, `metrics.json`, `completion.json`, and
`STATUS` to the corresponding local report directory. Leave
`raw_predictions/*.npz` on Baobab and do not add them to Git.

## Corrected Slurm run

The corrected job was Slurm `12708861`, submitted on `shared-gpu` with the
same RTX 3090, four CPU, 64 GB, and two-hour resource contract. It completed
in `00:10:08` with exit code 0. Its isolated output is
`outputs/SF5-BALANCED-REPLAY-20260914/replay-12708861/`, and the compact
local report is
`reports/SF5-BALANCED-REPLAY-20260914/replay-12708861/`. The first live
check saw `PENDING (Priority)` and later `PENDING (Resources)`; neither queue
state was treated as a result.

The completed selection manifest has 480 records: 120 each for mouse,
zebrafish, chicken, and western-clawed frog, with source-index blocks
`0–119`, `360–479`, `720–839`, and `1080–1199`. Each model reports 1,966,080
labeled positions (`480 × 4,096`), and each per-species confusion matrix sums
to 491,520 positions (`120 × 4,096`). The two model records both report the
same 1-nt-to-1-token contract for all 480 records: 4,096 raw tokens, BOS at
0, EOS at 4,097, and 4,098 input tokens. A local compact-invariant check
passed for the selection counts, confusion-matrix totals, and token contract.

## Balanced replay results

The table gives the aggregate over all 1,966,080 positions and the arithmetic
mean over the four species. `binary F1` is BG versus all five non-BG labels,
including Unknown. `main4 F1` is the mean of SINE, LINE, LTR, and DNA F1;
each component is computed over all six-label positions, so BG and Unknown
errors remain in FP/FN. Unknown is recall for the Unknown class only when its
true support is nonzero.

| model | level | binary F1 | main4 F1 | Unknown support (bp) | Unknown recall |
|---|---|---:|---:|---:|---:|
| base pretrained | global pooled | 0.893830 | 0.847821 | 7,872 | 0.438008 |
| base pretrained | four-species macro | 0.861297 | 0.733729 | 7,872 total | N/A (3/4 species have zero support) |
| binary H0 | global pooled | 0.878067 | 0.845838 | 7,872 | 0.091845 |
| binary H0 | four-species macro | 0.839775 | 0.745040 | 7,872 total | N/A (3/4 species have zero support) |

Per-species values are:

| species | base binary F1 | base main4 F1 | base Unknown support | base Unknown recall | H0 binary F1 | H0 main4 F1 | H0 Unknown support | H0 Unknown recall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mouse | 0.959913 | 0.835546 | 0 | N/A | 0.958880 | 0.846866 | 0 | N/A |
| zebrafish | 0.850346 | 0.766350 | 7,872 | 0.438008 | 0.846041 | 0.780617 | 7,872 | 0.091845 |
| chicken | 0.879604 | 0.764835 | 0 | N/A | 0.871750 | 0.721696 | 0 | N/A |
| western-clawed frog | 0.755323 | 0.568185 | 0 | N/A | 0.682427 | 0.630980 | 0 | N/A |

The true support in the four main classes and Unknown is the same for both
models because the labels are fixed:

| species | SINE support (bp) | LINE support (bp) | LTR support (bp) | DNA support (bp) | Unknown support (bp) |
|---|---:|---:|---:|---:|---:|
| mouse | 7,747 | 205,516 | 157,759 | 3,741 | 0 |
| zebrafish | 17,335 | 12,964 | 25,147 | 151,851 | 7,872 |
| chicken | 292 | 26,065 | 5,597 | 3,057 | 0 |
| western-clawed frog | 2,334 | 19,796 | 22,578 | 50,358 | 0 |
| global | 27,708 | 264,341 | 211,081 | 209,007 | 7,872 |

The JSON retains `0.0` for recall and F1 when a class has zero true support,
following the scorer's zero-division convention. Those values are reported
as N/A above rather than interpreted as Unknown recovery. The literal
`macro_f1_all6` field still averages all six class F1 values and therefore
includes zero for a zero-support Unknown class; the main4 macro remains
interpretable here because all four main classes have positive support in
each species.

The full six-class confusion matrices, class precision/recall/F1, binary
material counts, and per-species records are in the copied `metrics.json`.
The compact `verification.json` records the post-copy invariant checks. The
report directory contains `selection.json`, `selection.tsv`, `metrics.json`,
`completion.json`, `STATUS`, and `verification.json`; no raw prediction file
was copied locally.
The raw prediction arrays remain only at the two Baobab paths recorded in
that file and were not copied into the repository.

These numbers are a transparent species-balanced replay of the same first
1,200 test records and the same frozen checkpoints. They do not constitute
independent validation or complete six-species typing evaluation, and they
do not retroactively change the historical aggregate score.
