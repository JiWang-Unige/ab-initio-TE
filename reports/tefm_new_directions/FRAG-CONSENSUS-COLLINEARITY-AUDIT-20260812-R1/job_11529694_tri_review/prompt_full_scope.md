# Independent Full-Scope Research Review — F Job 11529694

你是独立外部科研 reviewer。请用专业简体中文输出，不修改文件。完整审阅并给出唯一下一步。

## Scope and north star

最终目标是raw-genome TE foundation model及可发表的fragmentation证据。旧 threshold/gap/HMM/CRF、轻量interval head、local fragment graph cousins已被DEC-001/002否决。新F re-entry必须保留immutable leaves，并只用richer/global evidence构造typed parents。

本实验 `FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1` 是Rice T1 curated-positive、CPU-only、claim-ineligible information-sufficiency audit。它测试：leaf sequence→frozen EDTA consensus的identity/strand/coordinate证据，加chromosome-wide consensus-collinearity DAG，是否比RAW singleton和positive-only GAP20/GAP100 comparators更能恢复T1 truth parent groups，同时保持leaf retention、低cross-rm-id false-fusion、boundary/topology。Truth仅给evaluator，assembler不能读取rm_id/parent boundary/class；未标空间不是negative。Whole-genome precision/F1禁止。

## Implementation/review state

- Independent full+delta review最终PASS：17/17 synthetic/static tests、Python/shell、15/15 implementation manifest hashes。
- Candidate joins不使用prediction-confidence、genomic-gap或test-tuned thresholds；fixed seed thresholds只形成consensus identity/strand/coordinate evidence。
- Resource contract: exact 8CPU/32GiB/2h/0GPU; preflight≤300s, payload5940s, publish headroom900s; scheduler TimeLimit exact.
- Frozen config runtime_code_files明确包含共享 `scripts/pre_submit_gate.py`，其SHA `4996364f...`。
- 主agent据review清单写machine `code_review_gate.json`时，reviewed_files列了15个exp-owned files，但遗漏该shared pre-submit script。Login-side `pre_submit_gate.py`仍PASS，因为它只验证gate列出的files；allocation-side `runtime_hashes.py`要求runtime_code_files都在reviewed_files，因而fail closed。

## Formal result

Job `11529694`, exact 8CPU/32GiB/2h/0GPU, private partition, State FAILED, ExitCode 1:0, elapsed 0 seconds.

Traceback唯一根因：
`RuntimeError: runtime path absent from independent reviewed_files: scripts/pre_submit_gate.py`

Execution boundary:

- No allocation-side contract tests completed.
- No env/scheduler snapshot completed.
- No Rice assembly, truth TSV or consensus library was read.
- No mapping, collinearity partition or evaluator ran.
- preview STATUS stayed IMPLEMENTED_NOT_RUN; only wrapper failure + temp preflight traceback exist.
- audited primary metric=null, semantic_success=false, validate_goal=`failed_run`.

Thus no scientific result or valid-negative exists. This was fail-closed review/runtime closure, not algorithm failure.

## Comparability/stop gates

- T1 permits positive recovery/boundary/topology/false-fusion proxies only.
- Even INFORMATION_SUFFICIENT only allows a separately reviewed bounded followup, never full F/GPU/whole-genome claim.
- No automatic retry is currently authorized. Any repair must go through fresh delta review and machine gate.

## Artifacts

- `outputs/FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1/result_semantic_audit.11529694.json`
- `metrics.audited.11529694.json`, `validate_goal.11529694.json`, `AUDITED_MANIFEST_11529694.sha256`
- `preflight_gate_and_tests_11529694.log.tmp.3520923`
- `preview/prepayload_failures/slurm-11529694.json`
- Code/config paths are in `preview/implementation_manifest.json`.

## Required output

### 1. Overall judgment
Choose exactly one: continue-current-route / scale-to-track-b / tune-only-if-near-sota / replace-component / change-backbone / change-objective-or-loss / run-sanity-check-first / comparability-blocker / abandon-route / return-to-literature.

### 2. SOTA gap interpretation
Use n/a where appropriate; state if tuning is justified.

### 3. Comparability/fairness audit
Table: dataset, split/truth tier, metric, preprocessing, external assets, resource claim eligibility.

### 4. Semantic success/reproducibility audit
Table: metrics parseable, finite, scientific payload executed, leakage, logs/manifests, fail-closed behavior.

### 5. Method assessment
Distinguish method hypothesis from gate installation failure; provide concrete structural alternatives only if evidence warrants them.

### 6. Track recommendation
State whether one narrow same-exp retry may be authorized after adding shared gate hash and fresh independent delta review, or whether a new exp is required. Set exact resource/no-override boundaries. Do not authorize GPU/full F.

### 7. Risks/blockers

### 8. Next action
Exactly one concrete action.

### 9. Confidence

