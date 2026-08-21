# ACTIVE_GOAL revision proposal — direct-superfamily data foundation

Status: proposal only; `ACTIVE_GOAL.json` is unchanged.

## Trigger

The active selector/decoder milestone is stale for the bounded direct-superfamily route. Jobs 11534847 and 11535362 are route-local semantic-successful components, yet `validate_goal.py` deterministically returns `failed_run` because it expects `selector_top2_contains_best`. Two post-result reviewers require goal reconciliation before the next representative CPU proposal.

## Minimal logical diff

- Replace goal id `TEFM_PUBLICATION_SUPPORT_DECAY_STRUCTDEC` with `TEFM_S_ACCESSION_DATA_FOUNDATION_R1`.
- Replace selector/decoder success criteria with six ordered data-foundation gates.
- Use strict integer primary `data_foundation_gate_count_passed`, threshold `==6`; Jobs 11534847 and 11535362 now form independently reattested, authoritative 2/6 carry-forward evidence.
- Require every future metrics file to emit all six numeric gate flags; unexecuted gates are `0`, not missing.
- Keep claim, GPU, training and S1 forbidden.
- After 6/6, require another user-approved goal revision to the already frozen direct-S0 numerical contract (`main4 conditional macro-F1 >=0.80`, TE-detect F1 >=0.85, Unknown recall >=0.30, false-Unknown <=0.02, eligible coverage >=0.70, minimum-clade macro-F1 >=0.60, zero homology overlap).

## Validator safety layer

新逻辑只有 proposal 显式声明 `validation_mode=ordered_evidence_milestone_v1` 才启用；没有 discriminator 的旧 goal 完整走 legacy 路径。primary 声明为 `integer_count`，只在该模式允许合法的 `0`/`1` 计数绕过旧 fraction-degenerate heuristic。六个 flag 必须是 strict integer `0/1`、按固定顺序形成单调前缀，且 primary 必须等于 flag 求和；bool、float、缺失、99、乱序和后闸越级均为 `failed_run`。

当前 2/6 不来自手写 metrics。审查曾发现两份原 `code_review_gate.json` 的 config/runner/tests/sbatch hash 仍一致，而 experiment doc 因 post-result append 改变；系统没有设例外或伪造 PASS。`CARRY_FORWARD_REVIEW_REQUEST.json` 冻结了两项当前文件、旧 gate、result audit、AUDITED_MANIFEST 与 drift 原因，随后独立 reviewer 逐项重算并在 `CARRY_FORWARD_REATTESTATION.json` 给出 PASS；该 artifact 还严格记录 reviewer backend/independence/timestamp 和仅授权 carry-forward genesis 的 authorization。builder 以批准的 request/reattestation 字节 SHA 为常量，在写前与 pointer 前双重复核，据此生成新 content-addressed genesis `6e7e24...` 和 authoritative `CURRENT`。旧 `6eecb7...`、`2d6a7d...` snapshot/metrics 仅保留作 superseded 审计历史，validator 不接受其作为当前进度。

后续 3..6/6 不改已安装 goal：`build_progress.py --advance-evidence` 每次只允许附加紧邻的下一个 gate，生成新的 content-addressed snapshot 与 versioned metrics，并以原子 `CURRENT` 指针指定唯一权威 tip；snapshot 记录 previous path/hash/count和批准的 reattestation pin，validator 从 `CURRENT` 反向走完整权威链直到固定 genesis。writer mutex 覆盖 validate→stage→publish；CURRENT CAS loser不能发布。pointer 前崩溃留下的非权威 orphan child 不参与 CURRENT ancestry、不会使旧 CURRENT 失效；后续合法 writer 仍以 CURRENT 和 CAS 决定唯一权威进展。旧 row 改写、跳闸、重复 job/evidence、symlink/traversal 或用旧 snapshot metrics 验证均 fail-closed。typed scientific block 追加同 count 的 stop event，不把失败 gate 记为 pass、不改变 flags；一旦 stop child 成为 CURRENT，旧父 snapshot 只能审计、不能恢复 continuation。每个 passed row 必须绑定独立 `code_review_gate.json`、semantic result audit 和 `AUDITED_MANIFEST` exact closure：reviewed_files 逐项重算，manifest 必须精确锚定 result audit 与 gate；`--check` 只读重验整链、CURRENT、路径与 closure。

`SCIENTIFIC_GATE_CONTRACT.json` 单独 hash-pin 六闸语义和 gate→execution 映射。当前前两组件各有自己的 executed flag。gate 3 必须实际执行 paired RepeatMasker、annotation 和 geometry；gate 4 必须执行 representative annotation 并证明 windows test 前冻结、旧 occurrence category exact-once；gate 5 必须完成 accession dataset/data stage、守恒 6,432,583 P occurrences、每个 P 有唯一 versioned accession 和 official consensus SHA、raw RepeatMasker class 是唯一 direct label，10 个 excluded identifiers 维持 U/ignore、X13_LINE audit-only；gate 6 必须完成 label-blind all-species homology、先 component 后 split、zero overlap 和 conflict typed-block。copy-derived proxy、prefix/case/fuzzy guess、缩分母均被明文禁止。未通过 gate 的对应 execution flag 必须为 0，已通过 gate 的全部 required execution flags 必须为 1。

四态保持不变：合法 0..5/6 为 `not_yet` rc1；scientific typed block 追加同 count stop event并同样返回 `not_yet`，但 `route_stop_required=true` 且禁止继续；完整性/运行失败为 `failed_run` rc3；exact 6/6 为 `success` rc0，同时强制 `claim_achieved=false`、`human_gate_required=true`、`automatic_continuation_allowed=false`、`next_action=stop_for_goal_revision`。passed result 极性固定为 PASS、semantic success、非 valid-negative、非 claim；每闸只允许其唯一 proposal eligibility 为 true，training/GPU/direct-S0/S1/full-scale/claim authorization 在 result/transition/aggregate 均不得为 true。未完成且未blocked时也保持 `automatic_continuation_allowed=false`，仅给出 `design_next_ordered_cpu_gate_for_fresh_review`，不能自动提交。旧 selector screen/SOTA anchors 连同 ACTIVE_GOAL hash仅作为 `parked_metadata` 保留，validator 报 `comparison_anchor=none`、`anchors_evaluated=false`，不计算 claim/gap/tuning。

## Six-dimensional comparability review

- Dataset version: changed; old annotation/S0 values are not directly comparable.
- Split: new label-blind homology/clade split is not yet built; old chromosome/species splits cannot be inherited.
- Metric implementation: current goal is deterministic gate counting, not model performance.
- Preprocessing: accession-preserving annotation pipeline must be frozen before DATA gate.
- Weights: none under this goal; training forbidden.
- Test-time inference: none under this goal; RepeatMasker CPU gates are engineering/data evidence only.

No published SOTA or screen-anchor value is revised. This milestone is non-claim. `ACTIVE_GOAL.json` remains unchanged; this directory is still proposal-only. Carry-forward reattestation is closed, but installation still requires explicit user approval.

安装批准与作业授权严格分离：安装此 goal 最多允许设计/实现下一个 paired-RM CPU gate；真实提交仍要求独立 exp contract、fresh code-review gate、smart-sbatch 与完整 result-log→validate-goal→note-gate→tri-review→pivot→iter-ledger 链。2/6 只表示两个有序组件完成，不表示 33% representative/data concordance readiness。
