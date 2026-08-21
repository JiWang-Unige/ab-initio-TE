# TEFM direct continuation protocol — 2026-08-11

## Authorization and scope

The user explicitly authorized formal continued progress on 2026-08-11 and requested parallel advancement. This continuation keeps the previous bounded safety envelope unless a later user message changes it:

- profiles: smoke and screen only; claim-ineligible;
- maximum concurrent research directions: 3;
- maximum walltime per job: 12 hours;
- maximum new aggregate GPU allocation in this continuation: 24 GPU-hours;
- CPU-only work requests zero GPUs;
- no full/scale, deployment, global database migration, git commit/push or manuscript claim.

Exp-scoped database configuration and immutable asset acquisition are allowed. They must not mutate a shared production database or silently replace frozen tool identities.

## Wave plan

### Wave 1 — run concurrently after independent gates

1. `BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2`
   - Close exact Dfam/FamDB runtime for RepeatModeler2+RepeatMasker and Earl Grey.
   - Acquire or independently validate the exact HiTE 3.3.3 artifact.
   - Resolve EDTA 2.3.0 patch identity without accepting ambiguous `v2.3` output.
   - Close TEtrimmer 1.7.4 source-overlay, canonical output and frozen Pfam dependencies where feasible.
   - Every unresolved cell remains typed-block; no legacy substitution.

2. `SF-DIRECT-BASELINE-SCREEN-20260811-R2` (S0)
   - This precedes every hierarchical/open-set experiment.
   - Freeze Dfam ontology/crosswalk and family/homology-component plus clade-held-out splits.
   - Rejoin the historical direct-superfamily head exactly as a continuity comparator, but do not use it as the leakage-safe primary if it previously trained on held-out components. The primary direct baseline is clean-trained from the frozen base-pretrained checkpoint on the new blocked train/validation sets.
   - Calibration and model selection use train/validation only; test labels are never used.
   - S1 hierarchical/open-set work is authorized only if S0 meets all preregistered acceptance gates below.

3. `FRAG-EVIDENCE-REGISTRY-20260811-R2`
   - Freeze the H0 directory identity and a tiered T0/T1/T2 registry.
   - Freeze same-input RAW, CENTER70, MERGE_STRICT, MERGE_LOOSE and one accepted postprocessor with source/config/semantic probes and predicted-loci schema.
   - If real T0 remains absent, authorize only a T1-positive screen: positive recovery, boundary/topology and false-fusion proxies; no whole-genome precision/F1.

### Wave 2 — after Wave 1 collection, still max 3 concurrent

- `DECAY-TRANSFER-PROVENANCE-REBUILD-20260811-R2`: reconstruct exact five-anchor run records before any transfer-surface fitting.
- `EMB-BINDING-SPLIT-FREEZE-20260811-R2`: freeze all 2,200 family/copy/species/component bindings, sealed split, backend pins and weights before representation comparison.
- `SF-HIER-OPENSET-SCREEN-20260811-R3` may occupy the third slot only if S0 direct baseline passes.

## S0 direct-superfamily acceptance gate

Historical, non-homology-blocked SF5 screens provide the preregistration anchor: main4 conditional macro-F1 `0.8547–0.8644`, TE-detect F1 `0.8982–0.9041`, Unknown recall `0.3886–0.3957`, and main4 false-Unknown rate below `0.001`. To allow for the harder leakage-safe split without defining success after observing results, S0 passes only if all conditions hold:

- split audit: zero family/homology-component overlap across train/validation/test;
- any window containing TE components assigned to multiple splits is excluded and counted; eligible coverage includes this exclusion;
- primary `main4_conditional_macro_f1 >= 0.80`;
- `te_detect_f1 >= 0.85`;
- `unknown_recall >= 0.30`;
- `main4_false_unknown_rate <= 0.02`;
- evaluated main4 coverage `>= 0.70` of eligible, non-audit-only labeled units;
- minimum clade main4 conditional macro-F1 `>= 0.60`, with every clade and support reported;
- exact checkpoint/data/ontology/evaluator identity and finite metrics.

These are screen-acceptance gates, not claim thresholds. If S0 fails, first diagnose annotation/split/head identity; hierarchical abstention must not be used to hide an unacceptable direct baseline.

## Common chain

Each submitted experiment must follow:

`implement → independent code-review-gate → leakage/data audit → smart-sbatch Phase 1/2 → terminal reconciliation → result-log → route-specific validate_goal → cohort tri-review → pivot`.

No scientific job is submitted when a foundational gate is false. Asset repair can terminate as a reproducible typed block.
