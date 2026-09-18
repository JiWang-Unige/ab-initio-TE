# EXTERNAL-ANIMAL-CLOSURE-20260918 status

Updated 2026-09-18 after the fixed-D external inference, source-layer scoring,
and clade-conditioned LoRA comparison completed on Baobab. The two
nonmammal D masks and the finite LoRA comparison are terminal; the remaining
external status below records only the qualification and scoring evidence.

## Qualification completed

| species | assembly | full strict-known TE union | fixed 20 × 5-MiB panel strict-known TE | panel fraction | mixed regions | status |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| *Takifugu rubripes* | fr3 | 18,582,705 bp | 2,295,569 bp | 2.19% | 20/20 | QUALIFIED |
| *Taeniopygia guttata* | taeGut2 | 81,160,964 bp | 4,479,542 bp | 4.27% | 20/20 | QUALIFIED |

Qualification uses assembly-matched UCSC FASTA and RepeatMasker `.out`
metadata, a deterministic length-only contig selection, and the gates in
`configs/EXTERNAL-ANIMAL-CLOSURE-20260918.json`. It does not use model scores.
The full `.out` source contains 6,825 Unknown rows for fr3 and 2,487 Unknown
plus 2,288 question-marked class rows for taeGut2. On the selected panel, the
uncertain union is 341,429 bp for fr3 and 122,019 bp for taeGut2. These are
retained as uncertain metadata and excluded from the optional
source-comparator denominator.

## Slurm chain

* quality: `12887623` (fr3) and `12887624` (taeGut2), completed;
* prepare: `12887631` and `12887632`, completed on the private CPU-only
  allocation;
* frozen-D inference: `12887633` (fr3) and `12887634` (taeGut2), completed on
  the private GPU allocation;
* score: `12887635` (fr3) and `12887636` (taeGut2), completed on
  `private-teodoro-gpu` CPU-only with 8 CPUs and 16G.

Both inference outputs have completed `summary.json` and `material_runs.bed`,
and both source-layer score outputs are present.

## Frozen-D external results

| species | panel / callable bp | strict-known positive bp | recovered positive bp | positive-only recovery | predicted bp | no source support bp | source-comparator P / R / F1 | unknown or unlabelled callable bp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| *T. rubripes* (fr3) | 104,857,600 / 101,522,896 | 2,289,458 | 1,908,739 | 0.833708 | 3,219,224 | 1,310,485 | 0.599147 / 0.833769 / 0.697250 | 99,233,438 |
| *T. guttata* (taeGut2) | 104,857,600 / 104,279,300 | 4,476,142 | 990,248 | 0.221228 | 1,227,922 | 237,674 | 0.810570 / 0.221227 / 0.347588 | 99,803,158 |

The two fixed external screens therefore show heterogeneous transfer: fr3 has
high source-positive recovery, whereas taeGut2 has high source-comparator
precision but low recovery. These are same-assembly source-layer diagnostics,
not a claim of universal nonmammalian generalization. The comparator excludes
Unknown/ambiguous/ARTEFACT bases and is not biological truth.

## Architecture comparison

The first LoRA submission (`12888116`) failed before an adapter update because
new CPU parameters were wrapped around a CUDA checkpoint. Its failure record
is retained. The repair moves the wrapped model to the checkpoint device and
was submitted as `12888288`; it uses the same fixed contract: NTv2-500M D,
seed 42, first 256/128/128 complete tiles per species, shared rank-16 versus
two fixed routes of rank-8 in query/value of layers 27–28, 1,024 steps/arm,
AdamW `1e-4`, weight decay `0.01`, alpha equal to rank, and zero dropout.

The smoke check passed with 131,072 total trainable parameters per adapter
arm. The formal job `12888288` completed (`44:57`, one RTX 3090, 4 CPUs, 32G,
exit 0). Shared rank-16 has 131,072 active parameters per sample; the routed
2×rank-8 arm has 131,072 total parameters but activates 65,536 for each
sample, with fixed vertebrate versus worm routing and frozen-D fallback for
unknown taxonomy. Both arms ran 1,024/1,024 steps with no skipped updates.

On the matched CAL-refit D reference, DEV macro bp-F1 was 0.891834 for D,
0.890150 for shared rank-16, and 0.890696 for fixed 2×rank-8. Thus both
adapter arms were slightly below D; clade minus shared was only +0.000546.
Chicken was the weakest species by bp-F1 for all arms, while *C. elegans* was
weakest by IoU-0.8 segment F1. The *C. elegans* segment-level increase is a
topology diagnostic, not insertion-level recovery or external generalization.
Full per-species values and the matched historical full-CAL D column are in
`reports/D-BACKBONE-LORA-CLADE-20260918/RESULTS.md` and
`reports/D-BACKBONE-LORA-CLADE-20260918/compact-results.json`.

## Metric boundary

`score.py` emits primary strict-positive recovery separately from an optional
source-comparator P/R/F1. The latter removes Unknown/ambiguous/ARTEFACT
intervals and treats remaining callable non-positive sequence as source
background. It is explicitly not biological truth and must not replace the
positive-only readout.
