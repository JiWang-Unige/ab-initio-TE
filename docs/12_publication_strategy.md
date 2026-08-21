# Publication Strategy / 投稿推进计划

> 由 `/publication-plan` 维护。用于“已经有完整思路或已超越 SOTA，不是盲目迭代，而是把研究做成可投稿故事”的阶段。

## 0. Target positioning
- Target venue / journal tier:
- Backup venues:
- Article type: `<method paper / application paper / benchmark paper / resource+pipeline / short communication>`
- Expected novelty bar:
- Audience:

## 1. Core story
- One-sentence paper claim:
- Why now:
- Why existing work is insufficient:
- Our key insight:

## 2. Contribution menu（只保留可被证据支撑的贡献）

| Contribution ID | Claim | Evidence needed | Current evidence | Risk | Keep? |
|---|---|---|---|---|---|
| C1 |  |  |  |  | yes/no |
| C-TEFM-SUPP | A pretrained genomic FM can be adapted to UCSC strict TE annotation and its cross-species decay can be measured under controlled chromosome/window protocols | SUPP-1/2 model-window screen, SUPP-3 mouse-only transfer, SUPP-4 no-human mixture transfer, SUPP-6 fragmentation/postprocess analysis | PIPE-TEFM-SUPP-20260617 scripts/configs written; model smoke complete; first training arrays submitted as 9060945/9060949 | NTv3/Evo2 adapter blockers; first metrics are token-proxy until bp/segment evaluator is added | keep as validation track, not final claim yet |

## 3. Figure / table plan

| Fig/Table | Message | Required experiments / analyses | Owner docs | Status |
|---|---|---|---|---|
| Fig.1 |  |  |  | TODO |
| Table SUPP-1 | Backbone/window ranking under UCSC strict TE quick screen | SUPP-1/2 train/test metrics | docs/13 §8; docs/14 §9 | RUNNING/PENDING |
| Fig SUPP-2 | Transfer decay across animal/plant fine_tune species | SUPP-1 one-chrom species eval | docs/14 §9 | TODO_AFTER_TRAIN |
| Fig SUPP-3 | Mouse-only vs no-human mixture transfer to human and mammals | SUPP-3/4 | docs/14 §9 | TODO_AFTER_MODEL_SELECTION |
| Fig SUPP-4 | Fragmentation/edge-effect and overlap/smoothing decision | SUPP-6 | docs/14 §9; future postprocess report | TODO_AFTER_WINDOW_SWEEP |

## 4. Validation burden by venue tier

| Evidence type | Minimal | Strong | Needed for target? | Planned run/analysis |
|---|---|---|---|---|
| Main benchmark |  |  |  |  |
| Downstream task |  |  |  |  |
| Ablation |  |  |  |  |
| Robustness/OOD |  |  |  |  |
| Runtime/cost |  |  |  |  |
| Statistical test |  |  |  |  |

## 5. Rebuttal risk pre-mortem

| Likely reviewer criticism | Evidence to preempt | Where captured |
|---|---|---|
|  |  |  |

## 6. Manuscript readiness checklist
- [ ] Main claim has comparable full/scale result.
- [ ] Multi-seed or statistical test done when variance matters.
- [ ] Downstream/generalization tasks match target venue bar.
- [ ] Baselines are reproduced or explicitly justified.
- [ ] Data/split/metric provenance archived in `refs/dossiers/`.
- [ ] Figure/table evidence mapped to run IDs.
