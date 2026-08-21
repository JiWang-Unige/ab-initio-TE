# Final Report: PIPE-TEFM-EXTEND-20260620

Date: 2026-06-21

Status: semantic success, screen complete. This is a single-seed GENERanno 4096 bp supplemental screen and is not claim-grade evidence by itself.

## Outputs

- Summary status: `reports/tefm_extend/PIPE-TEFM-EXTEND-20260620/summaries/current_status.json`
- Transfer evaluation: `reports/tefm_extend/PIPE-TEFM-EXTEND-20260620/summaries/transfer_eval.tsv`
- Strict embedding screen: `reports/tefm_extend/PIPE-TEFM-EXTEND-20260620/summaries/embedding_strict.tsv`
- Base-pretrained SF5: `reports/tefm_extend/PIPE-TEFM-EXTEND-20260620/summaries/sf5_base.tsv`
- PU segment/postprocess: `reports/tefm_extend/PIPE-TEFM-EXTEND-20260620/summaries/pu_segment.tsv`
- Decay formula: `reports/tefm_extend/PIPE-TEFM-EXTEND-20260620/decay_formula/formula_fits.json`

## Semantic Success

- Slurm completion: prep, embedding extract, embedding cluster, train, eval array, segment array, formula, and summary jobs completed with exit code `0:0`.
- Summary completeness: `transfer_rows=81`, `embedding_rows=20`, `sf5_rows=1`, `segment_rows=72`.
- Log scan found no final-run `Traceback`, CUDA OOM, killed process, failed-job signature, or NaN-loss signature.
- Claim eligibility: screen only. ACTIVE_GOAL and SOTA/comparability contracts remain draft, so this run cannot support a SOTA claim.

## Main Results

### 1. Embedding strictness

The stricter family-level screen supports the previous caution. Pretrained GENERanno embeddings plus contrastive projection improve over raw embeddings, but kmer/basic-sequence features with contrastive projection remain stronger.

- B_animal genomic internal: A1 ARI 0.4525 / NMI 0.5085 / holdout macro-F1 0.5839; C1 ARI 0.8663 / NMI 0.8514 / holdout macro-F1 0.7512.
- B_animal genomic boundary: A1 ARI 0.4242 / NMI 0.4735 / holdout macro-F1 0.5517; C1 ARI 0.8337 / NMI 0.8149 / holdout macro-F1 0.6919.
- D_cross genomic internal: A1 ARI 0.2492 / NMI 0.3654; C1 ARI 0.8396 / NMI 0.8329.
- D_cross genomic boundary: A1 ARI 0.3546 / NMI 0.4254 / holdout macro-F1 0.5000; C1 ARI 0.8669 / NMI 0.8570.

Dfam consensus extraction was attempted but skipped because no local consensus FASTA was provided or found. This branch remains incomplete until a real Dfam consensus sequence source is supplied.

### 2. Base-pretrained SF5

The base-pretrained main4+Unknown result replicates the prior finding that base initialization is better for Unknown/reject than binary-H0 initialization.

- TE-detect F1: 0.8982.
- Main4 conditional macro-F1: 0.8547.
- Unknown recall: 0.3957.
- Unknown precision/F1: 0.6922 / 0.5036.
- Main4 false-unknown rate: 0.00019.
- Unknown-to-main4 rate: 0.4053.

Interpretation: main4+Unknown/reject is still the right label design. Heterogeneous `Other` should not be forced into a single biological class.

### 3. Animal model to plants and cross-kingdom panels

`invert_boost_animal_4096` transfers better than expected to many plant and cross-panel targets and remains the strongest broad baseline in this screen.

- `invert_boost` to plant eval-only: mean TE-F1 0.7269, precision 0.7845, recall 0.6812.
- `invert_boost` to plant fine-tune species held-out chromosomes: mean TE-F1 0.6254, precision 0.7306, recall 0.6892.
- `invert_boost` on cross eval: mean TE-F1 0.5914, precision 0.5840, recall 0.7943.
- Plant PU/positive-only and cross-kingdom PU branches mostly overcall TE: recall is often near 1.0 but precision is low. TV regularization improves precision somewhat but does not beat `invert_boost` overall.

Best plant examples: teosinte TE-F1 0.8887 with `invert_boost`; maize TE-F1 0.9052 with `invert_boost` and 0.9091 with plant-from-invert PU+TV; rice and sorghum remain good under `invert_boost`. Soybean, brachypodium, thale cress, beetle, and honeybee remain stress/label-risk cases.

### 4. PU fragmentation and smoothing

Positive-only and naive PU collapse into near whole-window or whole-region TE overcalls. On soybean and teosinte, raw PU predictions can have recall near 1.0 but segment-F1 near 0.0.

TV-regularized PU plus HMM/CRF-style smoothing reduces fragmentation:

- Soybean PU+TV raw: bp-F1 0.2135, segment-F1 0.0064, predicted segments 12018, short-fragment rate 0.8442.
- Soybean PU+TV HMM penalty2: bp-F1 0.2471, segment-F1 0.0589, predicted segments 1919, short-fragment rate 0.0948.
- Teosinte PU+TV raw: bp-F1 0.7918, segment-F1 0.0409, predicted segments 2342, short-fragment rate 0.8527.
- Teosinte PU+TV HMM penalty2: bp-F1 0.7954, segment-F1 0.1585, predicted segments 354, short-fragment rate 0.0847.

Interpretation: smoothing helps, but it cannot rescue training without reliable negatives or a stronger U-control objective. PU remains a negative ablation/gated-repair direction, not the primary route.

### 5. Stress anchors

Stress-anchor substitution gives only small gains.

- Stress baseline `invert_boost`: mean TE-F1 0.1749.
- `vertebrate_anchor`: mean TE-F1 0.1936, slightly better for lizard, X. laevis, and honeybee.
- `insect_anchor`: mean TE-F1 0.0496 and does not rescue beetle/honeybee.

Interpretation: broad anchor substitution is weaker than the species-specific recovery seen in `PIPE-TEFM-LOCK-20260619`. Beetle/honeybee still require label/library/de novo diagnostics or target-specific calibration.

### 6. Generalization decay formula

Adding label-source variables materially improves the fit compared with genetic-distance-only regression.

- Distance only: R2 0.1870, RMSE 0.3181.
- Distance + label Jaccard: R2 0.4128, RMSE 0.2704.
- Distance + label Jaccard + TE bp log + plant indicator: R2 0.5249, RMSE 0.2432.

Interpretation: a useful decay model must include label concordance / annotation completeness. Genetic distance alone is not explanatory enough.

## Degraded Review / Council Synthesis

External multi-agent quorum was unavailable in this closing pass, so this entry is a degraded host self-review and cannot support claim-grade decisions.

Supported conclusions:

- Keep GENERanno 4096 and `invert_boost_animal_4096` as the current robust annotation branch.
- Keep base-pretrained SF5 for main4+Unknown/reject.
- Keep overlap/HMM-style smoothing as a decoder guardrail.
- Keep C1/A1 as mandatory embedding baselines; do not claim model embedding superiority over kmer/basic features yet.
- Use label concordance/completeness as a required variable in generalization decay analysis.

Not supported:

- Universal cross-kingdom PU as a better model than animal `invert_boost`.
- Positive-only or naive PU as a primary training objective.
- Dfam consensus vs genomic fragment conclusions, because the consensus source is missing.
- Universal all-animal performance including beetle/honeybee as one headline mean.

## Pivot

Decision: continue the GENERanno 4096 + `invert_boost` route, but do not promote this screen to a claim. The next claim-facing work should lock the evaluator/comparability contract and use primary/stress panels separately. Plant and PU results should be reported as domain/label-shift diagnostics and negative ablations unless reliable RN/hardN negatives are introduced.
