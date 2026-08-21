---
exp_id: PIPE-TEFM-CALIB-20260621
date: 2026-06-21
approach_family: pretrained-LM
parent_exp: PIPE-TEFM-EXTEND-20260620
motivated_by: "user-requested calibration supplement after abandoning PU as primary route"
track: Track-A-screen
profile: screen
status: done
primary_metric: cross_supervised_mean_te_f1
value: 0.5786
vs_anchor: "screen only; no SOTA claim"
one_liner: "Standard supervised plant/cross calibration, Dfam consensus embedding, insect anchor, and extended decay formula"
---

## Why / Motivation

This experiment closes the user's correction that plant/cross screens had not yet been tested under normal supervised fine-tuning with reliable negatives. It also completes the missing Dfam consensus family-level embedding branch, tests direct honeybee/beetle and insect-no-beetle anchors, and extends the generalization-decay formula with label/source variables.

## Hypothesis

The weak plant/cross and stress results from previous screens are partly protocol-driven. Standard supervised calibration should outperform PU/positive-only plant/cross branches, Dfam consensus family-level embeddings should provide a stricter representation test, and insect-specific calibration may distinguish recoverable honeybee domain shift from beetle source/domain failure.

## Architecture

Backbone is GENERanno 4096 bp, seed 42. Branches include `plant_supervised_4096`, `cross_supervised_4096`, `direct_western_honey_bee_4096`, `direct_red_flour_beetle_4096`, and `insect_no_beetle_4096`, plus the prior `TFREPAIR_invert_boost_animal_4096_seed42` model as transfer reference.

## Data

Data comes from current ready-by-design RepeatMasker/Dfam/UCSC-derived panels:

- C_plantTE fine-tune and eval-only species.
- D_cross_kingdom_animal_plant eval-only species.
- B_animal stress/eval species for honeybee/beetle and insect anchor diagnostics.
- Dfam RepeatMasker consensus library at `.backup/data/libraries/dfam/3.9/families/Dfam-RepeatMasker.lib.gz`.

## Config

- Config: `configs/pipelines/PIPE-TEFM-CALIB-20260621.yaml`
- Seed: 42
- Window: 4096
- Max eval samples: 1200
- Training profile: screen, single seed

## Result

Semantic success passed. All Slurm stages completed with exit code `0:0`, and summary files contain 98 eval rows plus 4 Dfam consensus embedding rows.

Key values:

- `cross_supervised_4096` broad mean TE-F1: 0.5786.
- `animal_invert_boost` broad mean TE-F1: 0.5413.
- `cross_supervised_to_plant_fine` mean TE-F1: 0.8568.
- `animal_invert_boost_to_cross_eval` mean TE-F1: 0.6026.
- `insect_no_beetle_to_stress_eval` mean TE-F1: 0.3073, driven by honeybee 0.7983 and beetle 0.0059.
- Dfam consensus embedding: A1 ARI 0.2242 versus C1 ARI 0.7083.
- Extended decay full formula R2: 0.7407.

## Findings

- Standard supervised plant/cross fine-tuning is materially better than PU/positive-only for plant held-out species.
- Cross-supervised and animal invert-boost should be reported by panel, not collapsed into a single mean.
- Insect-no-beetle calibrates honeybee but not beetle.
- Dfam consensus embedding keeps C1 as the mandatory baseline; FM embedding superiority is not supported.
- Decay modeling needs label/source variables; genetic distance alone is too weak.

## Decision

Continue the robust GENERanno 4096 route with panel-specific reporting. Keep PU abandoned as the primary route. Carry forward cross-supervised and animal invert-boost as complementary branches for claim-prep after evaluator/comparability locking.

## Links

- Final report: `reports/tefm_calib/PIPE-TEFM-CALIB-20260621/FINAL_REPORT.md`
- Result-log: `docs/06_results_log.md#result-pipe-tefm-calib-20260621`
- Tri-review: `docs/07_tri_review.md#tri-review-pipe-tefm-calib-20260621`
- Pivot: `docs/08_pivot_decisions.md#pivot-decision-pipe-tefm-calib-20260621`
- Summary: `reports/tefm_calib/PIPE-TEFM-CALIB-20260621/summaries/current_status.json`
