# Results log

## Result: EVSPRINT-CLAIM-ANCHORS-20260809A

### Meta

- Date (UTC): 2026-08-09
- Resource profile: smoke / evidence sprint
- Claim eligibility: cannot claim SOTA or biological validation from this profile
- Git commit / branch: remote `/home/users/j/jwang/ab-initio-TE` is not a Git worktree; frozen package and input hashes are the baseline
- Code review gate: `PASS_WITH_WARNINGS`, host-self independence, zero open blockers
- Evaluator contract: `experiment_contract.yaml` plus `claim_anchor_manifest.json`, frozen in package SHA-256 `6033CBC4ADF7A82BFE06B8CD7A982DF14C5588B29D70D7D5059D1647B4C6779C`

### Dataset / split

- Dataset: 18 SHA-256-pinned historical TSV/JSON results covering four claim tracks
- Split scheme: not applicable; this was a read-only provenance/denominator audit
- Independent biological denominator visible in the audited decay/router tables: 22 species, not 156/244 independent units

### Config

- Architecture: no estimator; standard-library TSV/JSON audit with hash, schema, missingness, duplicate and metric-identity gates
- Compute: 4 CPUs, 16 GB, zero GPUs, 10-minute limit
- Full config: `codex_pro_collaboration/scientific_evidence/EVSPRINT-CLAIM-ANCHORS-20260809A/experiment_contract.yaml`

### Paths

- Successful log: remote `software_outputs/scientific_evidence/EVSPRINT-CLAIM-ANCHORS-20260809A/logs/EVS-4ANCH_11468096.out`
- Metrics: remote `.../run_11468096/results/audit_report.json`
- Local report: `codex_pro_collaboration/evidence/EVSPRINT-CLAIM-ANCHORS-20260809A_run11468096/run_11468096/results/audit_report.md`
- Frozen evidence archive: `codex_pro_collaboration/deliveries/EVSPRINT-CLAIM-ANCHORS-20260809A_run11468096_evidence.tar.gz`

### Command

```bash
sbatch --export=ALL,FROZEN_INPUT_DIR=/home/users/j/jwang/ab-initio-TE/software_outputs/scientific_evidence/EVSPRINT-CLAIM-ANCHORS-20260809A/frozen/input_6033CBC4ADF7A82B /home/users/j/jwang/ab-initio-TE/software_outputs/scientific_evidence/EVSPRINT-CLAIM-ANCHORS-20260809A/frozen/input_6033CBC4ADF7A82B/run_evidence_audit.sbatch
```

### Semantic success

| Check | Result | Evidence |
|---|---|---|
| Root Slurm state | PASS | Job 11468096 `COMPLETED`, `ExitCode=0:0` |
| Audit JSON exists and parses | PASS | `audit_report.json`, schema 1.0 |
| Primary audit outcome present | PASS | `verdict=PASS`; this is categorical, not a model metric |
| Numeric values finite | PASS | all declared numeric inputs and JSON leaves passed the nonfinite gate |
| Metric implementation sane | PASS | every applicable F1/deletion identity matched at tolerance 1e-9 |
| Runtime error/NaN/OOM | PASS | empty stderr; no training was performed |
| Checkpoint/loadability | N/A | no model or checkpoint was produced |
| Output integrity | PASS | five result hashes passed remotely and locally; archive SHA-256 matched |

### Audit results

| Track / object | Audited denominator | Key result |
|---|---:|---|
| Current broad-class head | 2 rows | two initialization screens only; not family→superfamily evidence |
| Embedding objective | 6 rows | single-screen representation settings only |
| Extended decay | 244 rows, 22 species | 9 exact duplicate rows; 86 duplicate declared-key rows |
| Anchor decay | 268 rows, 22 species | 9 exact duplicate rows; 47 duplicate declared-key rows |
| Selector matrix | 156 rows, 22 species | ragged anchor coverage, not a balanced species×anchor cube |
| Strict segmentation | 1,200 rows | 2 models, 6 data JSONLs, 5 chromosomes, repeated threshold/metric grid |
| FRAGARCH | 122 rows, 3 panels | two historical non-comparable rows retained as missingness, not identity-tested |
| FRAGGRAPH | 96 rows, 2 panels | capability screen only |
| Post-processing | 242 rows, 2 panels | 121 variants; threshold-family screen only |

### Failed attempts retained

- Job 11468033: failed after 8 seconds because unige Python 3.9 does not support `Path.write_text(newline=...)`; outputs invalid.
- Job 11468053: auditor correctly failed on two explicitly non-comparable historical FRAGARCH rows; manifest applicability semantics were corrected without imputing/removing values; outputs invalid.
- Job 11468096: successful after both fixes.

### Gates check

- primary_progress_gate: pass for evidence availability only
- sota_claim_gate: fail / prohibited by smoke profile
- review_decision_gate: four external Pro design reviews captured; independent feasibility audit required before implementation

### Comparability audit

- Required for SOTA claim: not applicable; no SOTA claim
- Evaluator contract checked: yes, within the audit's declared scope
- Baseline reproduction: absent; historical result tables only

### Interpretation

The run establishes exact file identities, row/species denominators, missingness, duplicates and checkable metric consistency. It does not establish that any of the four scientific claims is true. The most important result is structural: the apparent sample sizes 156–268 collapse to 22 species for the decay/router problem, while current fragmentation and embedding work remains small-panel/single-screen evidence. The next action is an asset/provenance feasibility sprint, not model tuning.

### Recommended next action

- Run `EVSPRINT-PILOT-FEASIBILITY-20260809B` through implement → code-review-gate → smart-sbatch.
- Do not implement any Pro candidate until required truth/ontology/identity/provenance assets are verified.

## Result: EVSPRINT-PILOT-FEASIBILITY-20260809B

### Meta

- Date (UTC): 2026-08-09
- Resource profile: evidence sprint / read-only asset feasibility
- Claim eligibility: no model, biological or publication claim
- Git commit / branch: remote project root is not a Git worktree; exact v10 ZIP and member hashes define the code baseline
- Code review gate: Codex `PASS` plus fresh exact-byte Pro `PASS`; remote authorization limited to this asset audit
- Slurm: job `11473644`, node `gpu034`, root `FAILED 2:0`, elapsed 2m24s

### Frozen command

```bash
sbatch --parsable \
  --export=ALL,FROZEN_INPUT_DIR=/home/users/j/jwang/ab-initio-TE/software_outputs/scientific_evidence/EVSPRINT-PILOT-FEASIBILITY-20260809B/frozen_v10_7087a667cb5b2f40/input,FROZEN_MANIFEST_SHA256=00A0C62762664CA95E49D597989FEC981E4D688455D591B8E78F055A07C9F5F2 \
  /home/users/j/jwang/ab-initio-TE/software_outputs/scientific_evidence/EVSPRINT-PILOT-FEASIBILITY-20260809B/frozen_v10_7087a667cb5b2f40/input/run_feasibility_audit.sbatch
```

### Semantic success

| Check | Result | Evidence |
|---|---|---|
| Slurm root exit | expected fail-closed | `FAILED 2:0`; audit deliberately returns 2 for a hard asset error |
| Frozen preflight/snapshot | PASS | frozen, snapshot and immutability exits all 0 |
| Audit JSON exists/parses | PASS | `execution_verdict=FAIL`, one explicit hard error, four typed track gates |
| Expected results complete | PASS | all nine exist; `MISSING_RESULTS.txt` empty |
| Post-run frozen identity | PASS | 18/18; report script and manifest identities match |
| Output integrity | PASS | 41/41 `artifact_sha256.tsv` entries pass remotely and locally; manifest SHA `8623362D...52CFB7` |
| Runtime/OOM | PASS | no OOM/NaN/model runtime; Python MaxRSS about 55 MiB |
| Scientific claim | PROHIBITED | asset feasibility only |

### Results

- Hard error: `label_a_ready_directory` contains a symlink. The ready annotation tree contains 105 symlinks; the example link resolves to a regular file inside the same project, but exact inventory correctly refuses symlink-followed bytes.
- Fragmentation: blocked by absent validated T0 generator and strict-evaluator contracts.
- Direct superfamily: blocked by Label-A schema (`species` absent), ontology TBD, no machine crosswalk, incomplete old-SF5 identity fields and symlinked ready data; Dfam 3.9 itself is valid with 26,292 records.
- Generalization: blocked because Mash/sourmash is unavailable, five anchor training manifests/bindings are null/empty, no balanced provenance-validated held-out panel exists, and the matrix is not a complete eligible cube.
- Embedding: blocked because 2,000 genomic and 2,200 Dfam records lack sealed family/copy identity; duplicate canonical sequences are 26 and 1, respectively.

### Interpretation and next action

This is a valid negative readiness result, not evidence against the ideas. No model pilot is permitted. Feed exact blocker evidence to the four separate Pro conversations and request one bounded asset-remediation/pilot contract each. Any remediation that materializes symlink targets, constructs identity/crosswalk tables, freezes training provenance or adds Mash must itself be hash-pinned, reviewed and run through `smart-sbatch` before scientific implementation.

### Paths

- Remote: `software_outputs/scientific_evidence/EVSPRINT-PILOT-FEASIBILITY-20260809B/run_11473644`
- Local: `codex_pro_collaboration/evidence/EVSPRINT-PILOT-FEASIBILITY-20260809B_run11473644`
- Independent validation: `RUN_VALIDATION.md`
- Evidence archive: `codex_pro_collaboration/deliveries/EVSPRINT-PILOT-FEASIBILITY-20260809B_run11473644_evidence.tar.gz`, 97,438 bytes, SHA-256 `385392748EC61705570E7F5C36EBA1770F893D5CF95704F182B77B3900F0AA9D`

## Result: PIPE-TEFM-FRAG-R2-CODETEST-20260809-R1

- Slurm job `11475001` completed `0:0` on Teodoro Python 3.9.25 with a CPU-only
  `smart-sbatch` profile.
- Frozen source objects: 36/36; Python-3.9 grammar: 9/9; unit tests: 33/33.
- The exact 17-genome synthetic T0 panel regenerated byte-for-byte and the frozen
  table recomputation passed.
- Six fetched result objects independently matched the remote SHA-256 manifest;
  local manifest-copy SHA-256 is
  `94FFDD806E2DCE4870EF3871F03AA554F00307D2128EC63BDFD12647A3489FD1`.
- Semantic verdict: **PASS_CODE_GATE_ONLY**. No real asset, biological inference,
  comparator benchmark, model training or publication-performance claim occurred;
  `next_stage_authorized=false`.
- Dedicated log:
  `docs/experiments/PIPE-TEFM-FRAG-R2-CODETEST-20260809-R1.md`.

## Result: PIPE-TEFM-SF-R2-CODETEST-20260809-R2

- Slurm job `11475199` completed `0:0` on Teodoro Python 3.9.25.
- 23/23 source identities, 17/17 Python-3.9 grammar files and 51/51 tests
  passed; the prior non-root rename-fixture failure is closed.
- Both fetched outputs independently matched the remote hash manifest; manifest
  SHA-256 is
  `43693D54E81CACC92EE76C8A95E9B0E7AE8070C54A6923C962474DEF4162E9A6`.
- Semantic verdict: **PASS_CODE_GATE_ONLY**. The production homology allowlist
  remains empty; no real S0–S4 asset or scientific execution occurred and
  `next_stage_authorized=false`.
- Dedicated log: `docs/experiments/PIPE-TEFM-SF-R2-CODETEST-20260809-R2.md`.

## Result: PIPE-TEFM-TRANSFER-R2-P1-20260809-R1

- Slurm job `11474614` ran for 17m04s on Teodoro Python 3.9.25 and failed
  `1:0` during the first read-only real-project provenance scan.
- The reviewed pre-run suite passed 20/20 and 11/11 source identities matched,
  but a real TSV field exceeded Python's default 131,072-character CSV limit.
- The resulting `_csv.Error` escaped the typed P1 ledger/report path; therefore
  no complete four-object bundle or provenance seal is accepted.
- Semantic verdict: **VALID_RUNTIME_FAILURE**. This is implementation evidence,
  not a five-anchor readiness result, decay model result or publication claim.
- The exact traceback (SHA-256
  `0EE47C35DFFFE74EC1CEF69F0713EFED2E3A797B73A29D34B76CF414BA98F20D`)
  was returned to the same Pro conversation. A bounded parser correction passed
  static review and is running once as job `11475198`; no P2 authorization.
- Dedicated log:
  `docs/experiments/PIPE-TEFM-TRANSFER-R2-P1-20260809-R1.md`.

## Result: PIPE-TEFM-EMBED-R2-CODETEST-20260809-R1

- Slurm job `11475322` completed `0:0` in one second on Teodoro Python 3.9.25.
- 23/23 source identities, 9/9 actual-runtime grammar files, 30/30 tests and
  6/6 CLI help smokes passed.
- All three official Parasail backend pins remain empty; no real R1-R4 asset,
  Parasail execution, embedding, PCA, clustering, training or scientific metric
  occurred.
- Five fetched result hashes matched; output-manifest SHA-256 is
  `012C9CFF1D8B387E1972C5207AAD923CCAC938FB7CB5A8EAA9C8BA7797EC23E8`.
- Semantic verdict: **PASS_CODE_GATE_ONLY**;
  `next_stage_authorized=false` and no publication claim is permitted.
- Dedicated log:
  `docs/experiments/PIPE-TEFM-EMBED-R2-CODETEST-20260809-R1.md`.

## Result: PIPE-TEFM-TRANSFER-R2-P1-20260809-R2

- Corrected Slurm job `11475198` completed `0:0` in 22m38s on Teodoro Python
  3.9.25; 11/11 source identities and 23/23 tests passed.
- Inner run and independent verify both returned the accepted fail-closed code
  `2`; the exact four P1 objects were emitted, all stderr files are empty and
  10/10 fetched hashes match (manifest SHA-256
  `C2C66EB77AFCDB12FE967E67232A7198302943F708752927E44A2C479B8556A2`).
- Every fixed anchor (`human_h0`, `animal`, `cross`, `plant`, `insect`) is
  `PROV_RUN_RECORD_MISSING`; the candidate ledger has no qualifying row.
- Semantic verdict: **VALID_FAIL_CLOSED / P1_PROVENANCE_BLOCKED**. Historical
  checkpoints cannot yet support the transfer experiment; this is not a decay
  result and P2 remains unauthorized.
- Dedicated log:
  `docs/experiments/PIPE-TEFM-TRANSFER-R2-P1-20260809-R2.md`.

## Result: PIPE-TEFM-FRAG-R2-REAL-A0-A6-20260809-R3

- Slurm job `11475540` completed `0:0` in 5m05s on Teodoro Python 3.9.25.
- The handoff verified 44/44 package-manifest rows, 12/12 grammar files,
  63/63 tests, exact parent-ZIP plus extraction-root binding, and 38/38
  retrieved payload identities.
- A2 reproduced the full 17-genome synthetic T0 byte-for-byte and A3 passed all
  nine evaluator golden cases.
- A0 is blocked because the observed H0 checkpoint directory digest is not
  independently pinned; A4 has no admissible real complete-truth candidate; A5
  lacks frozen `CENTER70`, `MERGE_STRICT`, and `MERGE_LOOSE` comparators.
- Original and fresh recheck both report `PASS_VERIFIED_BLOCKED`; A6 is
  `BLOCKED_A6_NOT_READY`. No H0/lattice/change-point/scientific run occurred and
  `scientific_run_authorized=false`.
- Dedicated log:
  `docs/experiments/PIPE-TEFM-FRAG-R2-REAL-A0-A6-20260809-R3.md`.

## Result: PIPE-TEFM-SF-R2-REAL-S0-S4-20260809-R1

- Slurm job `11475541` passed 29/28 ZIP/manifest checks, 19/19 grammar
  files and 64/64 tests, then stopped at P0A with typed
  `E_MAT_DEST_UNSAFE`: the `/home/users/.../ab-initio-TE` project root is a
  symlink rather than a physical directory.
- No 105-file annotation or 15-genome materialization occurred; S1-S4 and all
  model/scientific work remained unexecuted.
- A canonical-root wrapper retry is invalid: the frozen manifest contains 120
  old-alias absolute path values and the ready tree contains 120 symlinks with
  old-alias absolute targets. The accepted lexical/no-follow gate would correctly
  reject them under `/srv/...`.
- Semantic verdict: **VALID_FAIL_CLOSED / PATH_PROVENANCE_BLOCKED**. A reviewed
  create-only pre-S0 canonical snapshot is required; original assets and safety
  code remain unchanged.
- Dedicated log:
  `docs/experiments/PIPE-TEFM-SF-R2-REAL-S0-S4-20260809-R1.md`.

## Result: PIPE-TEFM-EMBED-R2-A0-A3-CODEGATE-20260809-R2

- Slurm job `11476228` ran on Teodoro Python 3.9.25 and failed `1:0` after
  27 seconds during the focused unit-test gate.
- Safe extraction, 23/23 source identities, 12/12 Python-3.9 grammar files,
  forbidden-import scanning and credential scanning all passed.
- The suite completed 39 tests successfully and raised one error at
  `tests/test_a0_a3_handoff.py:196`: Python 3.9 rejects the test-only call
  `Path.write_text(..., newline="")`.
- CLI smoke, terminal summary and output manifest were not reached. No real
  A0-A3 assets, Parasail, R4, embedding, PCA, clustering, training or scientific
  metric ran.
- Semantic verdict: **VALID_RUNTIME_FAILURE / CODE GATE REJECTED**;
  `next_stage_authorized=false`. The exact traceback was returned to Pro for a
  minimal Python-3.9 test compatibility replacement.
- Dedicated log:
  `docs/experiments/PIPE-TEFM-EMBED-R2-A0-A3-CODEGATE-20260809-R2.md`.

## Result: PIPE-TEFM-EMBED-R2-A0-A3-CODEGATE-20260809-R3

- Corrected Slurm job `11476763` completed `0:0` in 30 seconds on Teodoro Python 3.9.25.
- Safe extraction, 23/23 source identities, 12/12 Python-3.9 grammar files, boundary scans, 40/40 tests and 7/7 CLI help smokes passed.
- All 14 result-manifest rows independently rehashed after fetch; manifest SHA-256 is `55F4D16E9D069CF15A053BC9CEEEE11344ECF399759086FDA12D0C7A1FAA3D41`; Slurm stderr is empty.
- Semantic verdict: **PASS_CODE_GATE_ONLY**. No real A0–A3 asset, Parasail/R4, embedding, PCA, clustering, training or scientific metric ran; `next_stage_authorized=false`.
- Dedicated log: `docs/experiments/PIPE-TEFM-EMBED-R2-A0-A3-CODEGATE-20260809-R3.md`.

## Result: PIPE-TEFM-SF-R2-PRE-S0-CODEGATE-20260809-R3

- Slurm job `11476764` completed `0:0` in 12 seconds on Teodoro Python 3.9.25.
- Safe extraction, 35/35 source identities, 23/23 Python-3.9 grammar files, boundary scans, 83/83 tests and 2/2 CLI help smokes passed.
- Both full-chain permutation regressions passed: the independent verifier rejected producer-consistent swaps for different-byte and identical-byte assets.
- All 14 result-manifest rows independently rehashed after fetch; manifest SHA-256 is `273E20F780C3131D0A4ED374F8F9D29F98CD4DA731AAD230EEA30D3F369E6B7E`; Slurm stderr is empty.
- Semantic verdict: **PASS_CODE_GATE_ONLY**. No live 105+15 asset was read/copied, no real pre-S0 snapshot was built and no S0–S4/model/scientific work ran; `next_stage_authorized=false`.
- Dedicated log: `docs/experiments/PIPE-TEFM-SF-R2-PRE-S0-CODEGATE-20260809-R3.md`.

## Result: PIPE-TEFM-SF-R2-PRE-S0-REAL-20260809-R1

- Slurm job `11476928` completed `0:0` after the real preflight confirmed all 120 source links and 15 manifest rows.
- The builder then returned typed `E_PRE0_MANIFEST_BINDING`: its mapping is keyed by manifest target paths but queried with different ready-link paths. The cited C. elegans link text is exactly equal to its MANIFEST cell and resolves correctly, proving an implementation/fixture defect rather than missing data.
- No snapshot, independent verification, S0-S4 or scientific/model execution occurred. All 14 fetched result hashes pass; output-manifest SHA-256 is `D906A77F...6E54`.
- Semantic verdict: **VALID_FAIL_CLOSED / IMPLEMENTATION DEFECT**; a minimal correction is active in the same Pro conversation.
- Dedicated log: `docs/experiments/PIPE-TEFM-SF-R2-PRE-S0-REAL-20260809-R1.md`.

## Result: EVSPRINT-E-COORD-ASSET-CENSUS-20260809-R1

- Slurm job `11477126` completed `0:0` in 11 seconds on Python 3.9.25; three frozen input identities and all 12 fetched output hashes pass.
- `zero_based_half_open` reproduced all 2,200 Dfam fragment sequences exactly; `one_based_closed` reproduced 0/2,200 (375 invalid intervals and 1,825 length mismatches).
- One hashed generator-source line was found. The bounded search was non-truncated but found zero exact-schema accession-crosswalk and zero exact-schema genomic-binding candidates.
- Semantic verdict: **COORDINATE CONTRACT PASS / OPTIONAL ASSETS BLOCKED**. No A0-A3, Parasail, embedding, PCA, clustering, training or scientific metric ran; `next_stage_authorized=false`.
- Dedicated log: `docs/experiments/EVSPRINT-E-COORD-ASSET-CENSUS-20260809-R1.md`.

## Result: PIPE-TEFM-FRAG-R4-CODEGATE-20260809-R1

- Slurm job `11477349` completed `0:0` in 2 seconds on CPython 3.9.25.
- Safe extraction, 27/27 source identities, 10/10 Python-3.9 grammar files, 55/55 unit/security tests, five CLI surfaces and the package self-audit passed.
- All 14 result hashes revalidated; output-manifest SHA-256 is `EFE5B6EC38602DACAA17989E3CFB11333FDCB50A63AFC6F609E4CA2E1C2A0AFF`; Slurm stderr is empty.
- Semantic verdict: **PASS_CODE_GATE_ONLY**. No real H0/A5 asset, model, inference, threshold selection or scientific metric ran; `next_stage_authorized=false`.
- Dedicated log: `docs/experiments/PIPE-TEFM-FRAG-R4-CODEGATE-20260809-R1.md`.

## Result: PIPE-TEFM-FRAG-R4-REAL-A0-A5-20260809-R1

- Job `11477415` passed 55/55 tests and completed the real A0 producer/terminal pair: 9 files, 1,973,418,475 bytes and aggregate `4942f175...dea35a2` reproduced exactly.
- Codex froze the 829-byte nine-leaf external pin registry, SHA-256 `801ED8CF...AB4C7`.
- A5 verified two source identities, nine literal rows and 20 semantic probes, then producer and terminal both typed-blocked on an ineligible `.bed` symlink; no threshold/performance work ran.
- Semantic verdict: **A0 IDENTITY PASS / A5 VALID FAIL-CLOSED**; 39/39 output hashes pass and scientific authorization remains false.
- Dedicated log: `docs/experiments/PIPE-TEFM-FRAG-R4-REAL-A0-A5-20260809-R1.md`.

## Result: EVSPRINT-F-CENTER70-SYMLINK-CENSUS-20260810-R1

- Metadata-only job `11477481` scanned all five frozen roots: 924 directories, 4,442 regular files and exactly 48 symlinks, with zero regular-file content reads.
- All 48 links are ineligible `.bed` leaves to existing regular targets inside the project; there are no eligible-text, directory, dangling, outside-root or special-target links.
- Semantic verdict: **PASS COMPLETE METADATA CENSUS**. Exact external exception registry SHA-256 is `A18AA196...24477`; any unregistered/changed link remains blocking.
- Dedicated log: `docs/experiments/EVSPRINT-F-CENTER70-SYMLINK-CENSUS-20260810-R1.md`.

## Result: PIPE-TEFM-SF-R2-PRE-S0-CODEGATE-20260810-R4

- Corrected v3 job `11477775` completed `0:0` in 12 seconds on CPython 3.9.25.
- Safe extraction, 35/35 source identities, 23/23 Python-3.9 grammar files, eight accepted production-module identities, boundary scans, 87/87 tests and two CLI checks passed.
- The exact real-layout positive/mismatch/duplicate/race regressions and both different-byte and identical-byte full-chain permutation attacks passed.
- All 16 result objects independently rehashed after fetch; output-manifest SHA-256 is `FFC38442976A2BD7FC1C0B0AFBFA58701A09953BEE2D7D36ADB934694B19AD64`; Slurm stderr is empty.
- Semantic verdict: **PASS_CODE_GATE_ONLY**. No live 105+15 object was read or copied, no real snapshot or S0–S4 stage ran, and no direct-superfamily scientific result exists.
- Dedicated log: `docs/experiments/PIPE-TEFM-SF-R2-PRE-S0-CODEGATE-20260810-R4.md`.

## Result: PIPE-TEFM-SF-R2-PRE-S0-REAL-20260810-R2

- Real snapshot job `11477914` completed `0:0` in 13m37s; builder, independent verifier and wrapper all returned zero with empty stderr.
- The create-only canonical snapshot contains 120 frozen regular payload files and 120 ready symlinks: 105 annotations plus 15 genomes, 120 provenance rows and 37,567,650,960 frozen bytes. The complete census is 25 directories, 126 regular files, 120 symlinks and zero other entries.
- The verifier returned `VERIFIED_CANONICAL_SNAPSHOT_READY_FOR_S0_INPUT_REVIEW`; source and rewritten manifest hashes, six group counts and all one-to-one source/ready/frozen bindings passed. All model, inference, scientific-performance, S5 and further-submission authorization flags remain false.
- Remote and fetched checks passed all 25 result members; output-manifest SHA-256 is `C5DDFA7B9B66FABCDC4543EA5473CF42D8E2E62E7E3952A9BAB033CE56B1238B`. The detached/copy verifier reports are byte-identical at SHA-256 `F8277630...61370`.
- Semantic verdict: **PASS_VERIFIED_ASSET_SNAPSHOT_ONLY**. S0-S4, training, inference and direct-superfamily scientific metrics did not run and require a new execution-envelope review.
- Dedicated log: `docs/experiments/PIPE-TEFM-SF-R2-PRE-S0-REAL-20260810-R2.md`.

## Result: EVSPRINT-BENCH-TOOL-CENSUS-20260810-R1

- Slurm job `11486982` completed `0:0` on `gpu035` under CPython 3.9.25; the payload completed in 53.355034 seconds.
- The frozen-scope census visited 26,514 project entries and 252,552 Conda entries, emitting 1,049 and 306 matched rows respectively without exhausting a frozen budget.
- Local candidates were found for RepeatModeler2/RepeatMasker, EDTA, Earl Grey, HiTE and TEtrimmer; no MCHelper pathname match was found. Candidate discovery is not an execution/readiness result.
- All six fetched terminal-output identities pass. Output-manifest SHA-256 is `FEB7B53D...5862`; the exact executed 7,925-byte contract is preserved at SHA-256 `09C05449...7506`.
- Semantic verdict: **PASS_COMPLETE_CENSUS_ONLY**. No tool was invoked; `claim_eligible=false`, `scientific_result=false` and `benchmark_authorized=false` remain closed.
- Dedicated result companion: `docs/experiments/EVSPRINT-BENCH-TOOL-CENSUS-20260810-R1_RESULT.md`.
