---
exp_id: SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1
date: 2026-08-12
approach_family: superfamily_identity_provenance
parent_exp: SF-FAMDB-LEAF-CLOSE-ONLY-REPAIR-20260812-R1
track: S0_data_foundation
profile: component_smoke
status: COMPLETED_COMPONENT_PASS
primary_metric: materialized_record_count
value: 6
vs_anchor: 6/6 frozen targets
one_liner: Same-six-record accession-preserving FASTA/header syntax pass; no annotation or S0 evidence.
---

# SF-FAMDB-LEAF-ADAPTER-PREFLIGHT-20260812-R1

## 目标与边界

这是 Job 11534847 通过 post-result tri-review/pivot 后唯一获准的 CPU leaf-adapter syntactic preflight。它重新对同一冻结 6 accession × 12 FamDB leaf 做严格 72 次、case-sensitive `get_family_by_accession`，并在同一 allocation 内物化两个很小的 FASTA header view。它不调用 RepeatMasker/rmblast，不读取 genome，不构建 representative/full catalog、homology component、split 或 DATA，也不训练模型、不使用 GPU、不启动 S1。

父 Job 11534847 的 audited manifest、component result、validate-goal、machine gate、config 与 close-only runner 均逐文件 hash-pin。父结果只证明 exact leaf access 与 close-only lifecycle；本实验不会把父结果冒充新 adapter 结果，真实 formal 必须重新访问 72 次并从实际 Family consensus 构建输出。

## 两臂合同

固定顺序由父 config 的 6 records 决定。control header 为 `>{canonical_name if nonempty else unversioned_accession}#{raw_class}`；candidate header 为 `>{accession.version}#{raw_class}`。header 必须 ASCII、exact case、恰一个 `#`，不得含空白、控制符或描述字段；candidate 必须是 versioned DF/DR accession。`DR002419729.2` 的 canonical name 明确为空，因此 control identifier 必须回退为未版本化 `DR002419729`。这里只验证语法 adapter 合同，不声称 RepeatMasker-compatible/proven。

两库各严格 6 records、顺序相同；逐对 sequence bytes 与 raw class 必须完全相同。sequence 仅作冻结的 uppercase/U→T 规范化，并重新核父长度和 consensus SHA256。record manifest 从写出的两份 FASTA 回读生成，包含 index、两 header/identifier、unversioned/versioned accession、显式空 canonical name、raw class、partition、length/SHA、逐 record FASTA hash、DF/DR provenance namespace 与父 audited-manifest hash。全局 ordered sequence+class semantic hash必须相同。唯一允许差异是 identifier token；swap/omit/duplicate/extra、class canonicalization、sequence/换行/大小写、header collision 均为 typed scientific block。

## 生命周期、状态与原子性

formal 首先验证 positive numeric Slurm job 与 exact 1 CPU/4 GiB/10 min/0 GPU/private scheduler（Command、SubmitLine、ReqTRES、AllocTRES），随后才读取父证据、source stat 或打开 H5。新 exp 使用独立 owner、gate、attempt、log 和 state namespace。父 reviewed close-only module按 hash 导入：single outer lifecycle 在 constructor 前取得 cleanup 责任，观测及两 FASTA 在 cleanup 前冻结为 attempt-scoped immutable bundle，随后对 12 unique `leaf.file` exact-once close；cleanup 不调用科学 API。source/package/gate/owner/scheduler 在 terminal pointer 前重验。

canonical state 使用 immutable bundle、self-excluding payload manifest 和 pointer-last `CURRENT`。任何 partial/dirty/preexisting attempt、symlink/path/hash/schema/authority/lifecycle/cleanup 问题均不得 promote。

`CURRENT` 的最终 `os.replace` 紧前会直接重验待晋升 bundle，而非只信任构建阶段：验证 status-specific exact file set、manifest exact schema/唯一相对路径、逐文件 size/SHA256、STATUS/metrics/report identity，以及 PASS 两份 FASTA 与 6-row manifest 的 header/order/sequence/class/record hash/provenance 映射。`before_pointer` 之后发生的任何篡改都会拒绝 pointer replace，旧 CURRENT 字节保持不变。

preview 的所有既存祖先、`states`、待发布 bundle 及每个 entry 都必须无 symlink；resolved `states` 必须直接位于 resolved preview 下，resolved bundle 必须直接位于 states 下，每个 entry 必须直接位于 bundle 下。已有 `states` symlink、bundle symlink、path escape 或 traversal 均 fail-closed，不能在外部目录写状态。

sbatch EXIT trap 的 `--record-wrapper-failure` 首先严格验证同 attempt canonical terminal。若 runner 已发布可闭合重验的 PASS、typed block 或具体 FAILED，wrapper 以 rc0 返回且不改变 CURRENT；只有 runner 尚未发布同 attempt terminal 时，才在 owner/authority 闭合下形成 generic wrapper failure。因此具体 runtime/cleanup/integrity 证据不会被 wrapper 文案覆盖。

formal 在首次完整父证据校验后，从 `initial.parent_pins.parent_audited_manifest_sha256` 外层绑定父 observation hash，并与 config 中冻结的 Job 11534847 audited-manifest hash逐字核对。PASS 与 typed-block 的 observation pre-pointer 复验和 terminal bundle FASTA↔manifest 复验使用同一个外层冻结值；该值在调用 terminal `publish` 前已经存在，不依赖 closure 内赋值。完整 mock formal 控制流测试分别执行 PASS/typed-block 分支，断言两次 publish、terminal 参数、父 hash、rc0 与无 `NameError`；独立 scope 回归测试确保父 pin/config 不一致时在首次 publish 前 fail-closed。

- `LEAF_ADAPTER_PREFLIGHT_PASS`：6/6 syntactic contract set通过，semantic true/rc0；只使未来 representative CPU proposal 具备进入人闸资格（`representative_cpu_proposal_human_gate_eligible=true`）。
- `LEAF_ADAPTER_PREFLIGHT_TYPED_BLOCK`：完整 72-call 证据下的 missing/duplicate/identity/header/order/sequence/class block，semantic true/rc0，所有下游授权仍 false。
- `LEAF_ADAPTER_PREFLIGHT_FAILED`：runtime/hash/resource/lifecycle/cleanup/atomic/timeout失败，semantic false/rc2。
- `IMPLEMENTED_NOT_RUN`：当前静态预览；未打开真实 H5、未调用 FamDB API。

所有 report/metrics 明确：`denominator=6`、`representative=false`、`concordance_evidence=false`、`annotation_executed=false`、`RepeatMasker_executed=false`、`geometry_evaluated=false`、`claim_eligible=false`，且 DATA/GPU/S1=false。禁止把 6/6 称为 representative concordance、annotation round-trip、RM-compatible、catalog coverage 或 S0-ready。

## 资源与静态验证

资源固定 `private-teodoro-gpu`、1 CPU、4096 MiB、10 分钟、0 GPU；outer timeout 480 秒、kill-after 30 秒，为 cleanup/publish 保留至少 90 秒。conda activation 后启用 `set -u`，pre-submit 支持任意 CWD，日志目录在 schedule time 已预建。

当前只运行 synthetic/static tests。行为测试另覆盖 before-pointer metrics/FASTA tamper 保持旧 CURRENT、external `states` symlink 拒绝、wrapper 不覆盖同 attempt typed/FAILED terminal，以及 PASS/typed-block 的完整 mock formal terminal publish/hash作用域回归。没有新 exp code-review PASS gate、没有提交 Slurm、没有真实 H5/API 计算。

## 正式结果：Job 11535362

- Slurm：`COMPLETED 0:0`，20 秒，`private-teodoro-gpu`，1 CPU/4 GiB/10m/0GPU，MaxRSS `81,388 KiB`。
- 终态：`LEAF_ADAPTER_PREFLIGHT_PASS`，route-local `semantic_success=true`，`claim_eligible=false`。
- 输入/API：同一冻结六记录、72 次 exact case-sensitive accession calls、0 fallback；12/12 unique HDF5 handles 显式关闭。
- 输出：control/candidate 各6条；ordered sequence+raw-class semantic SHA 均为 `0b4b077b...a115`，唯一差异为 identifier。DR 空名回退为 control `DR002419729#RC/Helitron`，candidate 为 `DR002419729.2#RC/Helitron`。
- 完整性：terminal exact set 12/12、observation exact set 5/5、逐记录 FASTA/header/manifest mapping、source/scheduler/package pre/post 全通过独立重哈希；`AUDITED_MANIFEST_11535362.sha256` 逐项通过。
- 边界：这是 six-record syntactic adapter PASS，不是 RepeatMasker compatibility、annotation、representative concordance、geometry、catalog coverage、homology、DATA 或 S0/S1 result。
- 下一步：必须先 tri-review/pivot；最多只能让新的 representative CPU proposal 进入人闸，不能自动提交。

## Post-result review 与 pivot

- `2/3 DEGRADED_REVIEW`：Claude 与 separate Codex 均为 `PASS_WITH_WARNINGS`、`continue-current-route`、confidence High；Antigravity 三次无效，external Codex CLI 三次额度阻断。
- 两位有效 reviewer 均只接受 six-record syntactic component PASS，不接受任何 representative/RM/annotation/DATA/S0 解释。
- Pivot：下一 representative CPU gate 仅具 proposal eligibility；在实现前必须通过 `$revise-goal` 人闸解决 stale selector/decoder `ACTIVE_GOAL`。当前不自动修改 goal，不开放任何下游运行。
