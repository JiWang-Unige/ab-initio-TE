---
exp_id: FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1
date: 2026-08-12
approach_family: global-biological-fragment-assembly
parent_exp: FRAG-EVIDENCE-REGISTRY-20260811-R2
motivated_by: "DEC-001/002 re-entry permitted only immutable leaves plus richer global evidence"
track: F
profile: screen
status: done
primary_metric: information_sufficiency_gate_pass
value: 0.0
vs_anchor: "exact recovery -0.2328 vs GAP100; bootstrap interval wholly negative"
one_liner: "Consensus coordinates beat shuffle but are insufficient as a standalone parent-copy assembler"
---

# FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1

> Final retry Job `11531090` completed the scientific payload as `VALID_NEGATIVE_INFORMATION_INSUFFICIENT`. Consensus collinearity is measurably above shuffle but below the registered positive-only comparators and fails coverage/false-fusion/promotion gates. `2/3 DEGRADED_REVIEW` has two valid `abandon-route` judgments; pivot and DEC-004 close this standalone assembler. No further F run is authorized.

## 状态

`IMPLEMENTED_NOT_RUN`。本实验仅完成可复现合同、实现与 synthetic/static tests；尚未经过独立 code review，未提交 Slurm，未读取或处理真实 Rice 大数据，也没有 code-review PASS gate。

## 研究问题

在 Rice RGAP7/EDTA v2.3.0 的 T1 positive-only multirow RepeatMasker groups 中，仅凭每个 immutable leaf 的实际 DNA 序列到冻结 consensus library 的 identity、strand 和 consensus coordinates，能否通过 chromosome-wide global collinear partition 恢复 parent-copy grouping？

这是 information-sufficiency audit，而不是 whole-genome TE accuracy、工具排名、模型训练或论文主张。未标注基因组空间始终是 unknown，不是 negative。

## 与 DEC-001/002 的正交性

- candidate join 不使用 prediction-confidence、genomic-gap 或 test-tuned threshold，也不使用 HMM、CRF、duration/survival loss、local fragment graph 或 frozen/lightweight interval head；固定 exact-seed evidence thresholds 仅用于形成 consensus identity/strand/coordinate evidence，不直接构成 join 规则。
- assembler 不读取 `rm_id`、truth parent boundary、class、repeat name 或 overlap marker。
- 新证据来自 leaf sequence 到 official frozen EDTA Rice consensus 的固定 seed-chain mapping。
- partition 是 chromosome-wide consensus-collinearity DAG 的 deterministic minimum path cover；兼容性只看 consensus identity、strand 和单调 coordinates，不使用 genomic gap。
- 每个 leaf immutable 且恰好属于一个输出 parent；parent 只引用 leaves，不删除、裁剪或覆盖 leaf。

## 冻结输入

| 资产 | SHA-256 | 用途 |
|---|---|---|
| RGAP7 `all.con` | `db8b7efb4df6ae33195143f3444b8816917441e1b964d150663ceeb2249506c4` | 仅提取已采样 leaf sequence |
| Rice EDTA v2.3.0 positive TSV | `06ac8f7cb0976aeae2a061f6c184779aebb5caf0b162b9755967985a0a89c6bf` | sampler 与 evaluator truth；truth 字段物理隔离 |
| `rice7.0.0.liban` | `bb470806821d8ba990fc0e89ae61cba2341dcde7cc72cfbcd264a1adf6abef2b` | frozen consensus evidence |

配置在 `configs/FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1.yaml`。所有输入在 payload 前必须 exact hash match。

## 采样合同

- denominator 仅为 `Chr1`–`Chr12` 且 `2–12` rows 的 truth `rm_id` groups。
- 按 `class_root × row_count_bin(2 / 3–4 / 5–12)` 分层。
- 每层最多 48 groups、总计最多 768 groups。
- 使用 `sha256(seed, seqid, rm_id)` 预先排序，seed=`20260812`；不看 mapping 或 evaluator outcome。
- public bundle 只含 `leaf_id/seqid/start0/end0/length/sequence hash` 与 leaf FASTA。
- `rm_id`、truth parent boundaries、class、repeat name、truth strand、overlap marker 只存在于 `evaluator_only/truth.tsv`。

## 固定机制

1. 使用 `k=13`、query stride 4 的 exact seed postings。
2. 过滤 posting count >64 的 repetitive k-mer。
3. 以中心 diagonal 的 `±32 bp`（实现判定为 `abs(diagonal-center) <= 32`）筛 inlier seed；至少 3 个 unique query-seed start positions。`seed_coverage` 是这些 inlier 13-mer 在 query 上区间并集的 bp 数除以 query length；要求该比例 ≥0.08，且第一与第二候选的该比例相差至少 `0.02`（2 个百分点），才记为 `MAPPED`。`0.08/0.02` 均不是 percent identity、alignment identity 或 consensus-coordinate coverage 阈值。
4. 按 `seqid × consensus_id × strand` 构造 global DAG；正链 consensus coordinates 单调递增，负链单调递减。
5. 用 deterministic bipartite maximum matching 得到 minimum path cover；不使用 genome gap 或 truth。

`identity` 在本审计中特指“由上述冻结 exact seed-chain evidence 选择的 exact consensus identifier”，不是估计的 percent sequence identity。

## 对照

- `RAW_SINGLETON`：每个 leaf 独立。
- `POSITIVE_ONLY_GAP20`：仅在本轮已采样 T1 positive leaves 上按 genomic gap ≤20 bp 合并。
- `POSITIVE_ONLY_GAP100`：仅在本轮已采样 T1 positive leaves 上按 genomic gap ≤100 bp 合并。
- `EVIDENCE_SHUFFLE_NULL`：在不读取 evaluator truth 的前提下，将完整 evidence records 在 public leaves 间做 seed=`20260813` 的确定性置换。

这两个 gap 对照是 experiment-local positive-only comparator，不声称 byte/semantic 等同历史 `MERGE_STRICT/LOOSE`，不构成 accepted production postprocessor，也不重开 DEC-001/002。

## T1 指标与 stop gates

允许报告的 metric allowlist 与 method exact schema 完全相同：mapped-leaf coverage、exact/complete known-positive group recovery、pairwise same-parent purity/recall/harmonic、known-positive boundary-error/5–50 bp curves、truth fragmentation count、cross-`rm_id` false-fusion proxy、known-positive topology preservation 和 leaf retention（以及这些量的必要有限计数/安全变换）；额外字段和非有限数都 fail closed。按 class、row-count bin、chromosome 另报分层表。

全部 promotion metrics 都用 sampled primary chromosome 作 paired block bootstrap（1,000 replicates）。每次 replicate 先对抽中的 chromosome blocks（允许重复）汇总 numerator/denominator sufficient statistics，再重建 pooled estimand；绝不平均 chromosome-level ratios。对每个需要 comparator 的 metric，每次 replicate 都重新在 `POSITIVE_ONLY_GAP20/100` 中选该 replicate pooled metric 的最大值。没有 registered-overlap topology truth 的 chromosome 不给 preservation=`1`，只对该 replicate 的 topology numerator/denominator 作零贡献；如果一次抽样完全没有 topology truth，该 replicate 对 topology uncertainty 是 unevaluable 并被显式排除、记录 valid replicate count。

严禁 whole-genome/bp/segment precision、recall 或 F1。

只有同时满足以下条件，结果才可标为 `INFORMATION_SUFFICIENT_FOR_BOUNDED_FOLLOWUP`：

- mapped leaf fraction ≥0.60；
- exact-group recovery 和 pairwise harmonic 分别比各自 comparator max 高至少 0.05；
- exact-group recovery 比 evidence-shuffle null 高至少 0.10；
- cross-`rm_id` false-fusion proxy ≤0.05；
- false-fusion safety 不低于该指标的 comparator max；
- boundary-within-5/10/25/50bp 每一项均不低于各自 comparator max；
- 至少存在 1 个 registered-overlap topology truth group，topology preservation ≥0.95 且不低于其 comparator max；
- leaf retention 精确为 1。

否则是 `VALID_NEGATIVE_INFORMATION_INSUFFICIENT`。两种终态只回答“该冻结采样的已知 Rice T1 positive multirow groups 中，consensus-collinearity evidence 是否值得进入下一次 bounded 验证”，不能外推 whole genome、所有 Rice TE 或生物学 parent-copy precision。两种终态均 claim-ineligible，且均不自动授权 GPU 或 capability promotion。

## 资源与执行边界

- `8 CPU / 32 GiB / 02:00:00 / 0 GPU`，private partition。
- 整个 preflight（reviewed-runtime pre-hash、gate、synthetic tests、environment snapshot、`scontrol` scheduler snapshot）由外层 `timeout --kill-after=5s 295s` 机器限时，最坏 300 秒。payload wrapper timeout 5,940 秒、kill-after 30 秒；仍保留至少 900 秒用于 manifest、publish 和 cleanup，总预算不超过 7,200 秒。
- 必须有 positive numeric `SLURM_JOB_ID`；runner 从 job-scoped `scontrol show job -o` snapshot 精确要求 `TimeLimit=02:00:00`（missing、short、long、unparseable 均 fail closed），并精确核 CPU/memory/partition/0-GPU。
- preflight 的第一个 child command 用固定 `benchmark_core` Python 将 config、sbatch、shared gate 和所有 exp-local runtime 文件逐项对照新鲜独立 review 的 `reviewed_files` hash；此前不读取科学资产。runner 在任何科学资产/子进程前复核并记录 pre-hash；canonical pointer 发布前再次逐项计算，pre/post（含 gate 自身 hash）必须完全一致。
- sbatch 从任意 cwd 切换到固定 project root；environment activation、gate、tests 与 snapshots 都在上述 machine-bounded preflight 内。payload 的环境激活也处于 5,940 秒 payload wrapper 内。
- 独立 owner-token lock、attempt namespace、atomic `RUNNING → terminal`、失败状态、runtime environment/scheduler snapshots、pre-submit/test receipt、reviewed-runtime pre/post hashes、exact argv command manifest、run/payload manifest 和 canonical latest/metrics 均由 exp-local runner 管理。wrapper 只有在 token 仍归自己且 canonical state 仍是自己的 `RUNNING` 时才能写 `FAILED_WRAPPER`；不能覆盖 runner 已写的终态。

## Static/synthetic tests

测试覆盖 preflight ≤300 秒总上界、exact 2h Slurm walltime（含 missing/short/long 拒绝）、reviewed-runtime pre/post drift、metric allowlist/exact schema、chromosome-block pooled bootstrap/replicate 内 comparator 重选/无 topology truth 排除，以及此前的资源、数据隔离、边界、partition、owner-token 与 atomic runtime 合同。测试不读取真实 Rice payload。

## 下一闸门

独立 reviewer 必须审查 sampling leakage、sequence evidence semantics、global partition、T1 evaluator、stop gates、atomic publication 和资源预算。只有 reviewer 生成新鲜的非 BLOCKED gate 后，才可进入 `$smart-sbatch`；本实现者不自行写 PASS。

## 正式结果 — Job 11531090

- Slurm: `COMPLETED 0:0`, 25 秒，8 CPU/32 GiB/2h/0GPU；17/17 tests、全部输入/命令/环境/调度器与 17-file payload manifest 通过。
- Sample: 756 T1 positive groups、2,450 immutable leaves、304 topology groups；leaf retention=`1.0`。
- Candidate: mapped=`0.555102`, exact recovery=`0.138889`, pairwise harmonic=`0.308188`, topology=`0.105263`, false fusion=`0.075862`, boundary@5/10/25/50=`0.186508/0.189153/0.195767/0.227513`。
- GAP100: exact=`0.371693`, harmonic=`0.669109`, topology=`0.473684`, boundary curves=`0.376984`；GAP20 false fusion=`0.051622`。
- Shuffle null: exact=`0.001323`, harmonic=`0.000540`, false fusion=`0.988095`。因此共识证据有信息，但不够形成有竞争力且安全的 parent join。
- Bootstrap candidate-minus-best-comparator: exact mean=`-0.232150`, 95% interval=`[-0.280093,-0.173410]`; harmonic=`-0.359041`, `[-0.448915,-0.273644]`; topology=`-0.371362`, `[-0.452308,-0.274306]`。
- Terminal: `VALID_NEGATIVE_INFORMATION_INSUFFICIENT`; claim/full/genome/GPU/Fly/H0/follow-up authorization 全为 false。旧 ACTIVE_GOAL validator 因 selector/decoder schema 不兼容返回 hard-stop `failed_run`，不改变 route-local valid-negative。
- Evidence: `outputs/FRAG-CONSENSUS-COLLINEARITY-AUDIT-20260812-R1/`，审计闭包 `AUDITED_MANIFEST_11531090.sha256` 逐项校验通过。

## Decision

- Tri-review: Claude=`abandon-route`, Codex=`abandon-route`, Antigravity failed three bounded CLI attempts; quorum=`2/3 DEGRADED_REVIEW`.
- Pivot: abandon the exact standalone seed-chain consensus-collinearity + monotonic DAG/path-cover family, not the broader fragmentation problem.
- Durable route record: `docs/09_decisions_log.md` DEC-004. Consensus evidence may only reappear as an auxiliary channel inside a genuinely different, independently pre-registered mechanism satisfying the listed re-entry criteria.
