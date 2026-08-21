# TEFM-NEW-DIRECTIONS-PILOTS-20260811 Protocol

## Objective

Independently prepare and execute small, falsifiable experiments for the four
new TE annotation directions and the five-workflow benchmark. The work must not
depend on ChatGPT Pro implementation packages. Pro's ideas may define hypotheses,
but code, inputs, evaluators, runtime identities and results must be reconstructed
and validated from the existing Unige project and authoritative upstream sources.

## Mode and budget

- Mode: publication-validation, bounded discovery/screen.
- This user message constitutes the pursue first-run approval for this bounded
  cohort only.
- Maximum concurrent research directions: 3, further limited by
  `cluster_config.yaml`.
- Maximum per-job walltime: 12 hours.
- Maximum new aggregate GPU allocation for this cohort: 24 GPU-hours.
- CPU-only audits and tool smoke should request zero GPUs.
- No full/scale or multi-day training is authorized by this protocol.
- All results remain claim-ineligible until later full validation and independent
  statistical review.

## Entry-gate repair

The last observed `research_flow_guard.py` result was `ok_to_goal=false`, with
`/sota-inventory` recommended because the remote candidate inventory was not
recognized. This may be a documentation-state mismatch, but it must not be
waived by assertion.

1. Re-run the guard and save the exact JSON.
2. Reconcile the dated August handoff with remote `docs/02`, `docs/03`,
   `docs/19` and `docs/20` without overwriting historical records.
3. Verify current candidates against official papers, repositories, releases or
   container metadata. The intended end-to-end denominator is
   RepeatModeler2+RepeatMasker, EDTA, Earl Grey, HiTE and conditional TEtrimmer.
4. Run the project-prescribed Stage-A chain until the deterministic guard opens.
5. If it cannot open because a genuine evidence requirement is absent, finish
   the affected track as `FOUNDATIONAL_TYPED_BLOCK`; do not invent a waiver.

## Common implementation contract

For each experiment create:

- `configs/<exp_id>.yaml`
- `scripts/experiments/<exp_id>/`
- `sbatch/<exp_id>.sbatch`
- `outputs/<exp_id>/`
- `docs/experiments/<exp_id>.md`
- machine-readable finite `metrics.json`
- environment, command, input and output SHA-256 manifests

Before submission:

1. Inspect existing code and reuse canonical loaders/evaluators where valid.
2. Freeze biological units, coordinate convention, split keys and truth tier.
3. Implement deterministic synthetic tests for the new mechanism.
4. Run an independent read-only `code-review-gate` and record it in
   `docs/21_code_review_log.md`.
5. Run `check_data.py` or an equivalent deterministic leakage audit.
6. Use smart-sbatch Phase 1. Any failure means no Phase 2 and no submission.
7. Use a compute allocation even for smoke; never execute research code on the
   login node.
8. Reconcile Slurm terminal state, validate semantic success, and retain failed
   runs as diagnostic evidence.

## Experiment B: five-workflow smoke

### Purpose

Determine whether each frozen workflow can be invoked reproducibly on a tiny
non-claim input and converted to a canonical output schema.

### Required checks

- exact executable/container/environment identity and version output;
- all required databases and indexes, including their version/hash;
- dependency and licence/readability checks;
- offline `--help`/version and minimum-input launch;
- deterministic adapter to canonical BED/GFF-like coordinates;
- captured stdout, stderr, exit status, elapsed time and peak memory;
- explicit reason for every unavailable or version-mismatched workflow.

EDTA 2.2 versus target 2.3, TEtrimmer 1.7.2 versus target 1.7.4, and an unknown
HiTE version must block that cell unless the intended version is independently
acquired and frozen before results are viewed. MCHelper is not silently inserted
into the five-workflow denominator. TE_Bench is an evaluator anchor.

## Experiment F: preservation-constrained parent-aware lattice

### Hypothesis

A no-deletion parent-aware interval lattice can reconstruct more biologically
meaningful parent TE intervals than fixed gap/threshold merging while preserving
fragment evidence and limiting false fusions.

### Minimum implementation

- Treat raw positive intervals as immutable leaves.
- Generate typed candidate joins from distance, strand, class/family support,
  containment/nesting and intervening evidence.
- A parent interval references its leaves; it never erases or rewrites them.
- Reject joins crossing incompatible labels, chromosomes, hard-N regions or
  registered nested elements.
- Produce leaf, parent and rejected-edge tables for audit.

### Comparators and metrics

Use the same frozen inputs for raw intervals, CENTER70, MERGE_STRICT,
MERGE_LOOSE, the currently accepted postprocessor and the lattice. Report leaf
retention, true-backed-fragment deletion, parent/segment precision-recall-F1 at
predeclared IoU thresholds, boundary tolerance curves, false-fusion rate,
nested-element preservation, per-genome results and paired uncertainty. If only
T1/T2 partial truth is available, do not report whole-genome precision as T0.

### Stop rule

Do not promote if apparent segment gains require deleting raw true-backed leaves,
raise false fusion materially, or exist only under one permissive tolerance.

## Experiment S: hierarchical open-set superfamily

### Hypothesis

A calibrated hierarchical predictor that may abstain or return a higher ontology
node will reduce severe taxonomy errors on remote families/clades without
unacceptable coverage loss.

### Minimum implementation

- Freeze Dfam/ontology mapping and label provenance.
- Split by family or homology component; include a clade-held-out audit.
- Fit node/family prototypes or hierarchical logits using training labels only.
- Calibrate thresholds on validation only.
- Return the deepest supported node, higher node, Unknown or abstain.

### Metrics and baselines

Report coverage-selective risk curves, main-class conditional macro-F1,
hierarchical path distance, unknown/reject recall, false-unknown rate,
overconfident leaf error and per-clade uncertainty. Compare flat softmax,
nearest-prototype/k-mer and the existing direct-superfamily head under identical
splits. Never treat Unknown as an ordinary coherent biological superfamily.

### Stop rule

Do not promote if gains vanish on family/homology-blocked splits, calibration
uses test labels, or abstention only hides errors at unusably low coverage.

## Experiment G: transfer surface and conservative routing

Use clean rebuilds when any historical checkpoint lacks its exact training
genomes, code/config identity or evaluation record. Predict transfer performance
only at the genome/species unit. Compare fixed-anchor baselines against genomic
distance/composition features under leave-one-species-out and leave-clade-out.
Primary screen outputs are top-k contains-best, regret, rank correlation,
interval/conformal coverage and abstention—not a universal predicted F1.

Stop if the effective independent-species denominator is insufficient, clade
holdout is invalid, or uncertainty is anti-conservative.

## Experiment E: representation falsification

Use the verified zero-based half-open 2,200-fragment coordinate contract, but do
not run until exact family/copy/species and component bindings plus model weights
are frozen. Construct one sealed split and reuse it for every representation.
Use identical dimensionality reduction and clustering-selection budgets for
pretrained embeddings, k-mer, MinHash, alignment graph, length/GC, random
Gaussian and untrained same-architecture features. Report multiple-seed cluster
stability, family/copy/species leakage audits and metrics at the correct unit.

Stop if pretrained embeddings do not beat strong sequence baselines outside
confidence intervals or if the conclusion depends on a visual projection.

## Cohort order and concurrency

1. Entry-gate repair and B smoke first.
2. F and S may run concurrently after their independent code-review gates pass.
3. G and E begin only after their respective asset gates pass and only if the
   aggregate resource budget remains available.
4. Collect the cohort before tri-review/pivot. A failed direction is isolated;
   healthy directions may finish, but the failed result cannot be promoted.

## Final evidence package

Produce a durable index containing every experiment ID, hypothesis, data/truth
tier, code/config/input hashes, job ID, Slurm state, resource use, metric path,
semantic verdict, review verdict and claim eligibility. Distinguish:

- engineering PASS;
- valid scientific negative;
- foundational typed block;
- invalid run;
- claim-ineligible screen signal.

No manuscript claim, commit, push, deployment or database migration is allowed.

