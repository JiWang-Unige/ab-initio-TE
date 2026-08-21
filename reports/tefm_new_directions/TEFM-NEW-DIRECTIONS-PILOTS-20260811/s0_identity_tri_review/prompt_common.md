# Independent Full-Scope Research Review

You are Reviewer <REVIEWER_ID>. You are independent from the other reviewers. Output only a structured professional Simplified-Chinese review. Do not edit files or run research computation.

## 1. Research question, scope, north star

The user requires a strict sequence: first determine whether direct superfamily annotation is usable; only after S0 passes may the project study hierarchical/open-set correction of superfamily misclassification. The long-term goal is a publication-grade TE foundation-model evidence chain, but this run is a claim-ineligible CPU data/leakage gate. No GPU model ran.

## 2. Method / data contract under test

Experiment `SF-DIRECT-BASELINE-SCREEN-20260811-R2` materializes canonical 4096-bp windows from 15 species. P-state RepeatMasker family names must resolve one-to-one through the pinned FamDB 2.0 API to a versioned Dfam 3.9 accession with a consensus hash. That accession is the homology component. Components observed in held-out orders go to test; other fit-only components are deterministically train/val split. Random/chromosome fallback and silent dropping are forbidden. Fit and primary-test order taxids are disjoint. U is ignored; hardN/RN are separate guardrail states. Optional stress is physically audit-only. Historical 9000 windows are comparator-only.

The repair-only delta after Job 11522718 locally raises only the pinned wide TSV reader limit to 2,000,000 characters with try/finally restoration; 15/15 tests and a real 495-row × 17-column probe passed, maximum field 1,203,362.

## 3. Current result and trend

- First CPU DATA Job `11522718`: `DATA_FAILED` before materialization at Python CSV default field limit 131072.
- Repair Job `11523252`: fresh independent code review PASS; pre-submit/preflight/test-only PASS; 16 CPU/96 GiB/0 GPU; about 21 minutes. It passed the parser repair and then terminalized `DATA_TYPED_BLOCK`.
- Structured reason: `DFAM_FAMILY_IDENTITY_UNRESOLVED`, including generic/ambiguous names (`Alu`, marsupial Charlie variants) and many custom `DR...` RepeatMasker families.
- Canonical terminal manifest verifies. `DATA_PASS_MANIFEST.json` is absent. No data promotion, split/leakage audit, loss, checkpoint, training, inference or scientific S0 metric exists.
- `metrics.json`: semantic_success=false, scientific_screen_executed=0, hierarchical_stage_authorized=false. `validate_goal.py`: failed_run because `main4_conditional_macro_f1` is absent.

## 4. Known weaknesses and open conflict

The current annotation source is not identical to the Dfam 3.9 name universe. The contract protects against homology leakage but assumes all P-state names have a unique official family identity. Possible repairs include: (A) bind unresolved custom families to exact consensus sequences from the frozen RepeatMasker library/source run and use consensus SHA/sequence clustering as components; (B) formally amend S0 to exact normalized RepeatMasker family-name components with explicit limits; (C) obtain another complete official identity mapping. Dropping unresolved positives, treating them as BG/U, or random/chromosome fallback would bias the direct-superfamily test and are prohibited.

## 5. Comparability contract / acceptance

S0 acceptance is preregistered in `configs/SF-DIRECT-BASELINE-SCREEN-20260811-R2.yaml` and `GOAL_S_DIRECT_R2.json`: main4 conditional macro-F1 >=0.80, TE-detect F1 >=0.85, Unknown recall >=0.30, false-Unknown <=0.02, eligible main4 coverage >=0.70, minimum held-out order macro-F1 >=0.60, homology-component overlap=0 and clade overlap=0. Screen profile cannot claim SOTA. S1 remains prohibited until S0 result-log/validate/tri-review/pivot explicitly authorizes it.

## 6. Abandoned cousins

Do not recommend random/chromosome split, silent unresolved-family deletion, flat Unknown as an ordinary biological superfamily, or immediate S1/GPU. Prior post-hoc fragmentation decisions are unrelated and must not be revived here.

## 7. This round versus last round

This round correctly fixed the only previously diagnosed CSV parser capacity bug and revealed the next data-identity contract blocker. It did not test architecture or direct-superfamily performance. The required decision is whether and how to repair the identity layer without data leakage or selection bias, not whether to tune/scale a model.

## Artifacts

- `outputs/SF-DIRECT-BASELINE-SCREEN-20260811-R2/STATUS`
- `outputs/SF-DIRECT-BASELINE-SCREEN-20260811-R2/metrics.json`
- `outputs/SF-DIRECT-BASELINE-SCREEN-20260811-R2/TERMINAL_STATE.json`
- `outputs/SF-DIRECT-BASELINE-SCREEN-20260811-R2/validate_goal.json`
- `outputs/SF-DIRECT-BASELINE-SCREEN-20260811-R2/output_manifest.sha256`
- `outputs/SF-DIRECT-BASELINE-SCREEN-20260811-R2/attempts/data-slurm-11523252.tmp/typed_block.json`
- `configs/SF-DIRECT-BASELINE-SCREEN-20260811-R2.yaml`
- `scripts/experiments/SF-DIRECT-BASELINE-SCREEN-20260811-R2/direct_s0_data.py`
- `docs/06_results_log.md` section `SF-DIRECT-BASELINE-SCREEN-20260811-R2 CPU DATA`

## Required output

### 1. Overall judgment
Choose exactly one: continue-current-route; scale-to-track-b; tune-only-if-near-sota; replace-component; change-backbone; change-objective-or-loss; run-sanity-check-first; comparability-blocker; abandon-route; return-to-literature.

### 2. Scientific interpretation
State what this result does and does not imply about direct-superfamily usability and the S1 sequence.

### 3. Data/comparability/leakage audit
Give Pass/Fail/Unknown for source identity, split semantics, unresolved-family handling, coverage bias, leakage protection, metric readiness and claim eligibility.

### 4. Semantic/reproducibility audit
Assess terminal state, manifests, parser repair, whether this is a valid foundational typed block versus implementation failure, and whether another bounded repair iteration is justified.

### 5. Repair options
Rank concrete options. For each, state required frozen evidence, leakage risk and whether it changes the preregistered contract. Explicitly judge consensus-sequence hash/cluster recovery versus exact-family-name fallback. Do not propose silent record deletion.

### 6. Risks/blockers
List hard blockers before CPU DATA retry, GPU S0 and S1.

### 7. Next action
Give exactly one primary next action and an objective code/data-review gate. State confidence High/Medium/Low.
