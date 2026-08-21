# Independent Full-Scope Research Review — Job 11528885

你是独立外部科研 reviewer。请用专业简体中文输出，不依赖其他 reviewer，也不要修改任何文件。必须审阅完整范围，并给出最可能推进到可发表 TE-FM 结果的下一步。

## 1. Research question & scope

终极目标是建立 raw-genome TE foundation model，并在严格可比 benchmark 上超过传统工具。当前窄问题属于 direct-superfamily-first 数据合同：RepeatMasker raw class 直接映射 `BG/SINE/LINE/LTR/DNA/Unknown` 标签；Dfam accession/consensus 只用于 homology-blocked split，不能重写标签。

本实验 `SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1` 只是 6-record、CPU-only、claim-ineligible roundtrip smoke：比较 name-header 与 accession-header 两个完全同序列/同顺序/同 raw class 的 custom libraries，验证 RepeatMasker `.out` 是否保留 accession 且几何与 direct labels 不变。它不授权 representative/full DATA、homology、GPU S0 或 S1。

## 2. Method / component under test

六条 pinned Dfam 3.9 accessions通过官方 FamDB API exact fetch，导出成 name-header/control 与 accession-header/candidate FASTA；逐记录校验 accession、name、raw class、length、consensus SHA、record SHA；两臂各跑 pinned RepeatMasker 4.2.2，然后比较排除 repeat identifier 后的完整几何语义 hash。科学不等价应是 valid-negative；资产/API/runtime/完整性失败必须是 failed_run。

## 3. Current results trend

历史 post-hoc identity recovery 已穷尽并关闭：P3 exhaustive 0/279；Dfam curated/all-family exact relation仅50 unique、2 ambiguous、227 missing，73.229% occurrence mass无法权威绑定。于是转向 annotation-time accession-preserving新benchmark。

- 第一次 Job `11528744`: exact 1CPU/4GiB/20m/0GPU，2秒失败。33/33 tests通过，但旧资源guard错误依赖 `SLURM_TIMELIMIT`；任何FamDB/RM前失败。上次2/3 tri-review一致允许只修严格`scontrol` guard、fresh review、最多一次CPU retry；明确规定若retry仍在科学前失败则停止自动重试。
- 唯一repair retry Job `11528885`: exact同资源，10秒，FAILED `2:0`。fresh review PASS_WITH_WARNINGS；machine gate、37/37 tests、strict `scontrol` authority reconciliation均通过。随后构造pinned官方FamDB对象时抛出 `AttributeError: 'FamDBLeaf' object has no attribute 'added'`。RepeatMasker没有启动；没有primary metric、没有roundtrip geometry、不是valid-negative。
- `validate_goal.py`: `failed_run`, run_ok=false, semantic_ok=false。所有 representative/full DATA/homology/GPU/S1 authorization=false。

## 4. Known weaknesses & open conflicts

- 两次正式CPU smoke均为engineering failed_run；自动retry budget已耗尽。
- 当前错误显示实现假设了installed `FamDBLeaf`不存在的聚合bookkeeping属性。需要判断是停止此export route、用已安装leaf API替换aggregation component，还是返回官方FamDB实现/文档取证。
- 不得把失败解释为direct-superfamily或accession roundtrip的科学负结果。
- 不允许绕过exact accession/consensus identity，也不允许prefix/case/copy-derived fallback。

## 5. Comparability / claim contract

该profile永不claim。它只在 `PREFLIGHT_PASS` 后使另行审查的真实窗口CPU representative gate具备提案资格。旧S0来自RM4.2.2 `-species`+overlay；新Dfam-only custom library属于新benchmark，不能继承旧S0指标或分母。即使未来smoke成功，仍需 representative windows、旧ledger 6,432,583 occurrences exact-once reconciliation、label-blind homology component zero-overlap、CPU DATA/leakage gate，才可讨论GPU direct S0；S1还需S0数值门。

## 6. Abandoned cousin routes

- Dfam3.9 P3/curated/all-family post-hoc exact-name/alias recovery已按stop rule关闭，不得再搜同源source或降分母。
- 不得用genome-copy representatives为identity source；这是test-derived/circular leakage。
- S1 hierarchical/open-set不得在direct S0与homology/data gates前启动。

## 7. This round vs last round

本轮唯一改变是用bounded `scontrol show job -o`替换`SLURM_TIMELIMIT`资源假设，并增加strict fields/command/TRES/pre-pointer revalidation与37 tests。该修复确实通过。新的失败发生在下一层FamDB API integration，说明上次blocker已关闭，但科学payload仍未开始。

## Artifacts

- `outputs/SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1/result_semantic_audit.11528885.json`
- `outputs/SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1/metrics.audited.11528885.json`
- `outputs/SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1/validate_goal.11528885.json`
- `outputs/SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1/AUDITED_MANIFEST_11528885.sha256`
- `outputs/SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1/preview/logs/slurm-11528885.{out,err}`
- canonical state: `preview/states/slurm-11528885-preflight_failed-1786517698469204726/`
- config/runner/tests/sbatch hashes are frozen in that state's `RUN_MANIFEST.json`.

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
State metric/SOTA/gap as n/a where appropriate; say whether tuning is justified.

### 3. Comparability and benchmark fairness audit

| Dimension | Pass / Fail / Unknown | Notes |
|---|---|---|
| Dataset version | | |
| Official split / same split | | |
| Metric implementation | | |
| Preprocessing | | |
| External weights / tool versions | | |
| Test-time inference protocol | | |
| Resource profile supports claim? | | |

### 4. Semantic success and reproducibility audit

| Check | Pass / Fail / Unknown | Notes |
|---|---|---|
| Metrics file exists and is parseable | | |
| Values finite / no NaN or Inf | | |
| Scientific payload executed | | |
| No leakage signal | | |
| Logs/config/manifests sufficient | | |
| Stop rule honored | | |

### 5. Architecture/component assessment

说明结果对annotation-time accession-preserving假设本身意味着什么；区分科学假设与FamDB export component失败。给2–4个具体、非调参的component-level选择。

### 6. Track recommendation

明确是否允许第三次retry、是否只允许新exp的read-only/API probe、是否应替换FamDB aggregation为leaf-level exact access，或应停止路线。任何建议都要给re-entry条件和资源上限。

### 7. Risks and blockers

### 8. Next action

只给一个具体下一步。必须尊重上次“repair retry仍失败则停止自动重试”的stop rule；不得直接授权GPU/S1/full DATA。

### 9. Confidence

High / Medium / Low，并解释。
