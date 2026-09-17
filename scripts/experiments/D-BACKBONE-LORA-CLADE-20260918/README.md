# D backbone LoRA clade comparison (2026-09-18)

This is a finite architecture comparison for the frozen six-species D binary
model. It keeps the NTv2-500M checkpoint, tokenization, 4096-bp window,
binary labels, species-balanced training contract, seed 42, and CAL/DEV
protocol fixed. It compares a shared rank-16 LoRA with two fixed-taxonomy
rank-8 experts inserted into `query` and `value` in the final two encoder
layers. Both arms have 131,072 trainable LoRA parameters.

The vertebrate expert is used for human, mouse, pig, chicken, and zebrafish.
The second route is explicitly a *C. elegans-only* worm route: one worm
species does not support a claim about invertebrates as a whole. Unknown
taxonomy falls back to the frozen D logits. There is no learned gate and the
backbone remains otherwise frozen.

The formal job uses the first 256 complete 8192-bp TRAIN tiles and first 128
complete CAL and DEV tiles for each of the six species. The worm TRAIN file
uses the existing upstream materialization override. Each arm runs exactly
1,024 optimizer steps (the configured hard maximum is 1,500), with AdamW
(`lr=1e-4`, `weight_decay=0.01`, `gradient_clip=1.0`), LoRA `alpha=rank`, no
dropout, and the fixed TE base-pair weight of 3.0. One private GPU job runs
the two arms sequentially under a four-hour limit; the total allocation is
bounded by eight GPU-hours.

The D reference reports both historical full-CAL calibration and a fresh
six-species CAL refit. Each LoRA arm fits its own Platt calibration and global
threshold on CAL. DEV is touched only once after the fixed training steps.
The output reports total model parameters, active trainable parameters,
per-species binary metrics, calibration parameters, route counts, and wall
time. A positive result is a finite clade-conditioned adaptation signal; it
does not establish a sparse or universally routed MoE.
