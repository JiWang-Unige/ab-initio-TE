# Frozen-D clade-conditioned LoRA comparison

The formal run completed successfully as Slurm job `12888288` (`44:57`, one
RTX 3090, four CPUs, 32 GB). It compares a shared rank-16 last-two-layer
query/value LoRA with two fixed-route rank-8 experts on the same frozen NTv2
500M binary D model. The result is a completed finite seed-42 comparison, not
a learned sparse-MoE result.

## Frozen protocol and matched capacity

All arms used the same checkpoint, tokenizer, binary head, 4096-bp windows,
source-order selection, and six-species TRAIN/CAL/DEV panels. Each species
contributed 256 TRAIN, 128 CAL, and 128 DEV tiles; each tile contains two
4096-bp halves. The adapters trained for 1,024 optimizer steps with AdamW,
learning rate `1e-4`, weight decay `0.01`, gradient clipping `1.0`, TE base-pair
weight `3.0`, dropout `0`, and seed `42`. Each step used one tile per species
and both halves, giving 12 valid half-loss terms. CAL fit one arm-specific
Platt calibration and global threshold; DEV never selected a parameter or
threshold.

The capacity match is a match in total trainable parameters across the two
adapter arms:

| arm | trainable parameters in all installed adapters | active LoRA parameters per routed sample | route |
| --- | ---: | ---: | --- |
| frozen D | 0 | 0 | frozen D logits |
| shared rank-16 | 131,072 | 131,072 | one shared adapter |
| fixed clade 2×rank-8 | 131,072 | 65,536 | vertebrate expert 0 or worm expert 1 |

The adapter-augmented model reports 493,217,235 total parameters; subtracting
the 131,072 adapter parameters gives 493,086,163 frozen checkpoint
parameters. Thus each adapter arm trains 0.026575% of the adapter-augmented
model. In the routed arm, the unused rank-8 expert is still trained and counts
toward the matched total capacity, but only one expert is activated for a
species. The route is fixed: human, mouse, pig,
chicken, and zebrafish use vertebrate expert 0; *C. elegans* uses worm-only
expert 1. Unknown taxonomy falls back to frozen D logits. There is no learned
gate, top-k selection, or claim of invertebrate-wide generalization.

## Calibration and DEV results

The matched D reference was recalibrated on the same 128-tile-per-species CAL
panel. The historical full-CAL D artifact is retained as a descriptive column;
it was not used to choose either adapter.

| arm | CAL threshold | Platt slope | Platt intercept | CAL loss | DEV macro bp-F1 | DEV minimum bp-F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| historical D full-CAL | 0.423301 | 0.698405 | −0.805031 | — | 0.891305 | 0.815133 |
| D, matched CAL refit | 0.414203 | 0.700049 | −0.777118 | 0.134204 | 0.891834 | 0.817015 |
| shared rank-16 | 0.427426 | 0.670060 | −0.808927 | 0.135752 | 0.890150 | 0.810191 |
| fixed clade 2×rank-8 | 0.426089 | 0.670640 | −0.813047 | 0.135571 | 0.890696 | 0.810814 |

Per-species DEV base-pair F1 is shown below. The deltas use the matched
CAL-refit D reference, so they do not mix calibration artifacts with adapter
effects.

| species | historical D F1 | matched D F1 | shared rank-16 F1 | shared Δ vs D | clade 2×rank-8 F1 | clade Δ vs D | clade − shared |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| human | 0.935157 | 0.935099 | 0.933796 | −0.001303 | 0.934149 | −0.000950 | +0.000353 |
| mouse | 0.950912 | 0.950965 | 0.949801 | −0.001165 | 0.949940 | −0.001025 | +0.000140 |
| pig | 0.893808 | 0.893625 | 0.892144 | −0.001481 | 0.892108 | −0.001517 | −0.000036 |
| chicken | 0.815133 | 0.817015 | 0.810191 | −0.006824 | 0.810814 | −0.006201 | +0.000623 |
| zebrafish | 0.921972 | 0.921627 | 0.920784 | −0.000843 | 0.921092 | −0.000535 | +0.000308 |
| *C. elegans* | 0.830852 | 0.832674 | 0.834185 | +0.001511 | 0.836074 | +0.003400 | +0.001889 |

The corresponding per-species precision and recall for the two adapter arms
are retained in `compact-results.json`, together with average precision,
boundary F1, segment F1 at IoU 0.8, missed rate, split rate, and all TP/FP/FN
counts. The principal summary metrics are:

| arm | macro precision | macro recall | macro average precision | macro segment F1 (IoU 0.8) | macro boundary F1 (25 bp) | macro boundary F1 (5 bp) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| matched D | 0.903364 | 0.880811 | 0.952210 | 0.450120 | 0.382147 | 0.201782 |
| shared rank-16 | 0.903219 | 0.877717 | 0.951399 | 0.450558 | 0.383426 | 0.201864 |
| fixed clade 2×rank-8 | 0.903412 | 0.878582 | 0.951275 | 0.450308 | 0.383986 | 0.203495 |

By base-pair F1, chicken is the weakest species for all three evaluated arms:
matched D `0.817015`, shared `0.810191`, and clade `0.810814`. By the stricter
IoU-0.8 segment metric, *C. elegans* is weakest: matched D `0.333758`, shared
`0.336250`, and clade `0.344565`. For *C. elegans* specifically, clade
base-pair F1 also increases slightly over matched D (`0.836074` versus
`0.832674`), but the six-species macro bp-F1 remains below D. The topology
increase therefore does not establish improved insertion recovery, and the
experiment does not test external species.

Relative to matched D, shared rank-16 retains 99.811% of macro bp-F1 and fixed
clade 2×rank-8 retains 99.872%. The clade arm is only 0.000546 macro bp-F1
above shared rank-16, while remaining 0.001138 below matched D. The small
clade-versus-shared difference is therefore not evidence of a stable MoE
advantage in this single-seed, fixed-route comparison.

## Runtime and failed first attempt

The two successful adapter fits used the same requested 1,024 steps and
matched 131,072 trainable parameters. The recorded fit times were 957.8 s for
shared rank-16 and 936.0 s for fixed clade 2×rank-8; the whole formal job,
including checkpoint loading, materialization, D references, calibration, and
DEV evaluation, took 44:57.

The immediately preceding job `12888116` consumed 6:21 on one RTX 3090 with
four CPUs and 64 GB, then failed before a scientific result because newly
installed LoRA tensors remained on CPU while the frozen model was on CUDA.
Its preserved failure bundle contains no metrics. The formal runner was
repaired only to move the complete wrapped model to the active device before
the first forward pass; no data, model, route, optimizer, or evaluation rule
changed.

The failed and successful formal allocations together consumed 51m18s of
single-GPU elapsed allocation time (0.855 GPU-hours). This total includes the
failed attempt and is not an inference-throughput measurement.

## Scientific interpretation and boundary

This run shows that, at matched total adapter capacity and fixed seed, a
clade-conditioned last-two-layer route preserves the frozen D model's strong
multi-species DEV performance but does not improve its macro bp-F1. It also
does not establish that clade routing is better than a shared adapter: the
observed difference is small, and no multi-seed uncertainty estimate was
authorized. The *C. elegans* segment-F1 increase is a topology-level
diagnostic and should not be promoted to a claim of biological-instance or
external-species recovery.

The result is a controlled adapter comparison only. It does not support
claims about a full sparse backbone MoE, learned routing, species-independent
invertebrate performance, multi-seed stability, or a taxonomy-based confidence
formula. The frozen D reference, calibration values, all per-species DEV
metrics, route manifest, and the complete raw result are retained in:

- `source-results.json` — copied formal `results.json` from run `12888288`;
- `compact-results.json` — compact metrics and adapter-versus-D deltas;
- `scheduler-evidence.json` — successful and failed scheduler evidence;
- `../../configs/D-BACKBONE-LORA-CLADE-20260918.json` — frozen protocol;
- `../../scripts/experiments/D-BACKBONE-LORA-CLADE-20260918/lora_clade.py` —
  formal runner;
- `../../scripts/experiments/D-BACKBONE-LORA-CLADE-20260918/analyze_results.py` —
  deterministic compact-summary generator.
