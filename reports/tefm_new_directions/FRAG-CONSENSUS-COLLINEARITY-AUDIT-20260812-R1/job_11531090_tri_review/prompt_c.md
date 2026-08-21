You are Reviewer C (Antigravity). You are independent from the other reviewers.


You are an independent external reviewer. Do not assume a special role. Review all dimensions and recommend the single next decision most likely to advance a publishable TE foundation-model project. Output professional Simplified Chinese and include the exact heading `### 1. Overall judgment`.

## 1. Research question, scope and north star

The long-term north star is a publishable TE foundation model with rigorous leakage-safe, cross-species evaluation. This experiment is a claim-ineligible CPU information-sufficiency audit for one fragmentation component: can immutable positive TE fragments be grouped into biological parent copies using only label-blind leaf-sequence evidence mapped to frozen TE consensus identity, strand and consensus coordinates?

This is not a whole-genome benchmark. Truth is Rice T1 positive-only; unlabelled genome is unknown, not negative. Whole-genome/bp/segment precision, recall and F1 are forbidden. The experiment cannot claim SOTA or authorize GPU work.

## 2. Method under test

- Frozen Rice RGAP7 assembly, EDTA v2.3.0 positive truth and Rice consensus library; all hashes were verified before execution.
- Sampled 756 truth groups (2–12 rows), 2,450 immutable leaves across Chr1–Chr12, and 304 topology-evaluable groups. Sampling was stratified by class root and row-count bin without reading mapping/evaluator outcomes.
- Public assembler receives only leaf coordinates/sequences; truth parent IDs, parent boundaries, classes, names and topology markers are physically evaluator-only.
- Fixed k=13 exact seeds, stride 4, repetitive posting cutoff 64, diagonal tolerance ±32 bp, at least 3 query seed positions, seed query-bp coverage ≥0.08 and winner margin ≥0.02. These produce consensus identity/strand/coordinates; they are not directly a join rule.
- A chromosome-wide DAG links only monotonic consensus-coordinate evidence for the same consensus identity and strand, followed by deterministic minimum path cover. It never reads genomic gap or truth.
- Every leaf is retained exactly once. Comparators are RAW singleton and experiment-local positive-only GAP20/GAP100. A deterministic evidence-shuffle null tests whether evidence carries signal.
- Promotion requires mapped fraction ≥0.60, recovery/harmonic improvements over the best comparator, exact recovery improvement over shuffle, false fusion ≤0.05, comparator-safe boundary/fusion/topology metrics, topology ≥0.95 and leaf retention exactly 1.

This mechanism was deliberately designed outside abandoned DEC-001/002 cousins: no threshold smoothing, HMM, CRF, duration/survival loss, local fragment graph, lightweight interval head or leaf deletion. Do not recommend tuning those cousins.

## 3. Result and trend

Job 11531090 completed 0:0 in 25 seconds with exact 8 CPU/32 GiB/2h/0GPU. Route-local semantic success is true; scientific screen executed; claim eligibility and whole-genome metrics are false. All input, command, scheduler, environment and 17 payload hashes independently verify. Values are finite; 1,000 chromosome-block bootstrap replicates used pooled sufficient statistics and reselected the best comparator inside each replicate.

Candidate CONSENSUS_COLLINEARITY:

- mapped leaf fraction 0.555102; leaf retention 1.0
- exact group recovery 0.138889; complete group recovery 0.142857
- pairwise same-parent purity/recall/harmonic 0.924138/0.184930/0.308188
- cross-RM-ID false fusion 0.075862; safety 0.924138
- topology preservation 0.105263
- boundary within 5/10/25/50 bp 0.186508/0.189153/0.195767/0.227513

Best comparators:

- GAP100 exact recovery 0.371693, harmonic 0.669109, topology 0.473684, all boundary curves 0.376984, false fusion 0.090995.
- GAP20 exact recovery 0.202381, harmonic 0.516570, topology 0.355263, false fusion 0.051622, safety 0.948378.
- Shuffle null exact recovery 0.001323, harmonic 0.000540, false fusion 0.988095.

Bootstrap candidate-minus-best-comparator:

- exact recovery mean -0.232150, 95% interval [-0.280093,-0.173410]
- pairwise harmonic mean -0.359041, interval [-0.448915,-0.273644]
- topology mean -0.371362, interval [-0.452308,-0.274306]

Only leaf retention, exact-recovery separation from shuffle and topology evaluability pass. Every comparator, coverage, boundary, false-fusion and topology promotion gate fails. Terminal is `VALID_NEGATIVE_INFORMATION_INSUFFICIENT`.

The prior attempt Job11529694 failed before payload due incomplete reviewed-runtime closure. That sole engineering issue was independently fixed without changing scientific code or frozen inputs; Job11531090 is therefore the first and final scientific result.

## 4. Comparability and known limits

- T1 gives positive recovery/boundary/topology and false-fusion proxy only; it cannot establish whole-genome precision or absence of false positives.
- GAP20/GAP100 are positive-only diagnostic comparators, not production methods and not historical MERGE_STRICT/LOOSE identity claims.
- Current ACTIVE_GOAL.json is an older selector/decoder milestone. `validate_goal.py` returns `failed_run` because selector keys are absent. This is a mandatory automation stop, not a route-local semantic failure.
- No model, training loss, checkpoint, seed variance or SOTA comparison applies. Treat those review rows as N/A, not as evidence of failure.
- No further F compute is currently authorized. Do not propose tuning fixed seed thresholds on these test families, Fly/H0 escalation, or revival of abandoned gap/HMM/CRF/local-graph/lightweight-head cousins.

## 5. Decision question

Decide whether this component should be recorded as a conservative limitation or abandoned component/route, and give explicit scientific re-entry conditions. Assess whether the above is a trustworthy valid negative, what it implies mechanistically, and whether any genuinely orthogonal future mechanism remains plausible without consuming more compute now.

## Artifacts

- `outputs/FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1/metrics.json`
- `outputs/FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1/result_semantic_audit.11531090.json`
- `outputs/FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1/AUDITED_MANIFEST_11531090.sha256`
- `configs/FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1.yaml`
- `docs/experiments/FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1.md`
- `docs/09_decisions_log.md` DEC-001/002

## Required output

### 1. Overall judgment
Choose exactly one:
- continue-current-route
- scale-to-track-b
- tune-only-if-near-sota
- replace-component
- change-backbone
- change-objective-or-loss
- run-sanity-check-first
- comparability-blocker
- abandon-route
- return-to-literature

### 2. SOTA gap interpretation
- Current metric:
- SOTA metric:
- Absolute gap:
- Relative gap:
- Is tuning justified? yes/no/only-if-near-sota. Explain.

### 3. Comparability and benchmark fairness audit

| Dimension | Pass / Fail / Unknown / N/A | Notes |
|---|---|---|
| Dataset version | | |
| Official split / same split | | |
| Metric implementation | | |
| Preprocessing | | |
| External weights / pretrained backbone version | | |
| Test-time inference protocol | | |
| Resource profile supports claim? | | |

### 4. Semantic success and reproducibility audit

| Check | Pass / Fail / Unknown / N/A | Notes |
|---|---|---|
| Metrics file exists and is parseable | | |
| Values finite / no NaN or Inf | | |
| Loss trend or expected pattern is sane | | |
| Seed variance known or not needed | | |
| No suspicious leakage signal | | |
| Logs/config/artifacts sufficient to reproduce | | |

### 5. Architecture assessment
- What does the result imply about the mechanism hypothesis?
- Is insufficiency attributable to evidence, mapper, global partition, truth limitations, or another component?
- Name 2–4 genuinely orthogonal future architecture/evidence moves, without recommending a run now.

### 6. Track recommendation
- Should this candidate be promoted? Why?
- Should this exact component stop?

### 7. Risks and blockers

### 8. Next action
Give one concrete non-compute decision or blocker-resolution step and explicit re-entry criteria.

### 9. Confidence
High / Medium / Low, with reason.
