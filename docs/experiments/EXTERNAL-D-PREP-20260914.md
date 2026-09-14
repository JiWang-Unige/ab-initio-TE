# Frozen D external evaluation: concrete preparation

2026-09-14. No external model inference or new sealed-result access has occurred in this preparation.

## Model to carry forward

Use the existing **D, seed42** artifact as the preselected primary model, not the better historical seed17 selected after seeing its score. Keep the historical seed17 results in the record; no new multiseed training is requested.

Remote root: `/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE`.

- Model: `outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/train/seed42/12307410_1/final_model`.
- Frozen calibration: `outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/evaluate/seed42/12353905_1/calibration.json`.
- Inference entrypoint: `scripts/experiments/CROSS-SPECIES-L1-FASTA-INFERENCE-V1/infer_fasta.py`.
- This entrypoint checks that model/tokenizer/code paths belong to the saved calibration and that calibration was fitted only on six-species CAL. Supply its recorded tokenizer/code paths; do not regenerate calibration on external labels.

The source for these paths is the existing D DEV artifact. Its `conf_evaluated=false` is an old artifact-level field: the later archived CONF report does contain internal worm confirmation. The missing result is external-species evaluation.

## Candidate inputs

| Candidate | Exact assembly | Usable comparator preparation | Current limitation |
|---|---|---|---|
| Platypus | GCF_004115215.2 | `labela-12664906-0` | task-feedback independence and actual callable/label contract must be explicit |
| Sea urchin | GCF_000002235.5 | `labela-12664906-1` | same; sparse curated library is not complete TE truth |
| C. briggsae | GCA_000004555.3 | `labela-12522308-2` | appeared in historical planning; actual use/feedback must be distinguished from planning |

All reside under `software_outputs/L1-PANEL-PREP-20260908-kqZrej`. Do not consume the two original Matrix-error products. No automatic substitution with horse, opossum, dm6 or cattle: these have existing reserved-panel restrictions.

## Separate kinds of novelty

1. **Task-supervision/selection held-out:** no TE labels or evaluation feedback from the chosen external panel used to fit/select D or its calibration. This is the primary species-transfer claim to qualify.
2. **Backbone pretraining exposure:** independent from task supervision. The [NTv2-250M model card](https://huggingface.co/InstaDeepAI/nucleotide-transformer-v2-250m-multi-species) reports 850 NCBI genomes; a focused attempt to open its linked dataset in this turn did not return a usable inventory. The [GENERanno 0.5B model card](https://huggingface.co/GenerTeam/GENERanno-eukaryote-0.5b-base) reports 386 billion eukaryotic bp but does not supply a per-assembly list on the page. Apply the relevant lineage to the actual chosen component; do not assume that every model has both backbones. Exact candidate pretraining exposure remains unresolved here.
3. **Sequence/family novelty:** quantify on a frozen sequence-homology challenge separately. A species name difference does not establish new sequence or TE-family novelty.

Unknown pretraining exposure limits a claim of entirely unseen DNA. It does not by itself make supervised species-transfer evaluation meaningless or prove leakage from TE test labels. Report the distinction rather than endlessly searching for an unavailable upstream list.

## Before scoring

Close the actual project feedback history and input ownership; specify callable bases and P/U/N semantics from the current comparator outputs, preserving unannotated/unresolved regions. A sparse positive comparator supports positive recovery; it cannot certify genome-wide precision/F1 by treating all remaining bases as true negatives. If reporting agreement with a RepeatMasker-derived binary comparator, name that comparator-dependent endpoint explicitly and keep independent accuracy claims separate.

Freeze evaluation regions without model-score selection, include the full declared region denominator, and save raw probabilities/material intervals. No external species-specific threshold fitting, best-expert selection by target F1, or model change after seeing the result.

Primary outputs: per-species material agreement/recovery at the existing threshold, precision/recall only where the label contract supports them, worst-species outcome, calibration/risk coverage with defensible labels, and L2 topology separately. Fixed L1 output does not reconstruct insertion identities. Use spatial block uncertainty as applicable; it does not estimate initialization variance.

## Architecture follow-up

After the fixed-D evaluation and an explicit bounded design, compare one controlled dense objective/coverage change with a parameter-matched adapter. Use specialists to test recoverable negative transfer. A MoE experiment is justified by complementary specialists, not by its name: freeze label-blind routing, include parameter/compute controls, report every species and router collapse/fallback, and keep target adaptation separate from zero-shot transfer. New hypothesis registration must not rewrite the old D coverage or CONF decisions.
