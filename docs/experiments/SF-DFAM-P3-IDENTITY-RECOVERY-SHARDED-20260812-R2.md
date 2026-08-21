---
exp_id: SF-DFAM-P3-IDENTITY-RECOVERY-SHARDED-20260812-R2
date: 2026-08-12
approach_family: data-identity-audit
parent_exp: SF-DFAM-P3-IDENTITY-RECOVERY-20260812-R1
motivated_by: "docs/08 pivot after serial resource mismatch and cross-node source guard repair"
track: S0-predata
profile: smoke
status: done
primary_metric: recovered_identifier_coverage
value: 0.0
vs_anchor: "valid negative; 0/279 exact-name recovery"
one_liner: "35-unit exhaustive Dfam p3 exact-name scan closes recovery hypothesis"
---

# SF-DFAM-P3-IDENTITY-RECOVERY-SHARDED-20260812-R2

## 唯一科学问题与边界

本实验是父 R0 的可恢复、四 worker 正式执行形状，只回答：Dfam 3.9 partition 3 的全量 canonical `Families` metadata 是否能用 case-sensitive exact `name` 恢复冻结的 279 个 missing identifiers（occurrence mass 恰为 6,432,583）。科学语义直接 pin 并复用父 R0 evaluator；`X13_LINE`（686 occurrences）仅保留在 audit-only stratum，不进入 279 targets。

严禁 prefix、case-fold、genome-copy、copy-derived consensus、聚类或模型 fallback。完整扫描后若仍有 missing/ambiguous/invalid metadata，输出语义成功的 `IDENTITY_RECOVERY_TYPED_BLOCK`；只有 279 个目标全部唯一 recovered，且下面所有结构守恒同时通过，才可输出 `RECOVERY_COMPLETE` 并进入 full-catalog 人闸。full-catalog stage、homology split、GPU 与 S1 不会由本作业自动授权。

## 冻结输入与 source identity 限制

- 绑定父 R0 config/code、已审 R0 telemetry、identity config/evaluator/layout/payload/identifier TSV、docs/19 与 `rmlib.config` SHA256。
- 项目根只接受封闭的两个等价 spelling：`/home/users/j/jwang/ab-initio-TE` 与 `/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE`，且前者必须解析到后者；任何其它 raw absolute alias 都拒绝。source asset 必须由冻结的 root-relative path 定位，并精确匹配冻结 normalized realpath。
- source 固定为 canonical p3 symlink，硬绑定 symlink target SHA256、resolved inode/size/mtime_ns/mode、H5 Dfam/FamDB/partition metadata、layout 与 rmlib。`st_dev` 仅为 expected/observed audit：登录节点 42 与计算节点 65 的差异不会使 unit checkpoint 失效，但两者均写入 audit。
- 64 GB H5 没有现成 full-content SHA256，本实验不在登录节点新增该负担。因此 inode+mtime+size+metadata/layout/rmlib 可拒绝普通的 same-size attr mutation，但不是对抗“修改内容后伪造 inode/mtime”的密码学证明；报告和 metrics 必须保留此限制。
- 静态 preview 只读 pins 和 35 个浅层 topology roots，不枚举真实 datasets。

## 单遍四 worker 执行

冻结 topology 为 35 个互不为祖先、无重复的 ordered units：`Families/Aux/<bin>` 和 `Families/DR/<prefix1>/<prefix2>`。321,856 total 仅生成透明的 uniform scheduling prior；它不是科学 evidence。largest-estimate-first greedy plan 给每个 unit 一个 preferred worker，运行时四 worker 使用共享原子 dynamic queue，优先拿自己的 unit、空闲后允许 steal，降低 elephant/tail 风险。

每个 worker 独立以只读模式打开一次 H5。每个 unit 只遍历一遍，同时完成：canonical dataset path + HDF5 object address inventory、consensus/model/name/accession/version attr presence counts、279 target exact-name candidates。不得先 inventory 再 scan 造成双 I/O。parent cutoff 或 SIGTERM 后，worker 完成当前 unit，但绝不 claim 新 unit。

parent 只在 worker outputs 的 rc/hash/schema 全部通过后聚合，并强制：

- 35/35 COMPLETE units；
- 321,856 dataset rows、321,856 unique paths、321,856 unique HDF5 object addresses；
- 321,856 consensus attrs、321,818 model attrs；
- topology 无 ancestor overlap，global hardlink duplicate、path duplicate、34/35、以及 duplicate+omission 抵消均拒绝；
- candidates 保留所有 source rows并 canonical sort；resolver identity 仍为 `(versioned_accession, consensus_sha256)`，跨 unit 同 identity 可归为同一 identity，异 identity 为 ambiguous，坏 metadata 为 invalid。

最终写出 canonical full inventory TSV、candidate rows、resolution、metrics/report 与 manifests。运行 telemetry 单独存放，不进入 scientific semantic payload；因此 1-worker oracle、4-worker out-of-order 和 half-resume 的 semantic payload 应逐字节一致。

## Unit checkpoint 与恢复

每个 unit 先写独立 `.tmp.<attempt>.<worker>.<pid>`：inventory、candidates、deterministic summary、payload manifest、pin contract 和 COMPLETE manifest；所有文件与目录 fsync 后，最后以 directory `os.replace` 原子晋升为 `<unit-hash>.COMPLETE`。source identity 在 initial validation、每个 unit 扫描前后、resume、final collect 前后与最终 publish 前均重新读取并与 config expected identity 比较；unit pin 同时保存 expected 与 observed identity。若 unit read 后、COMPLETE publish 前发生 same-size attr/inode/mtime mutation，unit 只能留下 `.tmp`，不能形成 COMPLETE。

Resume 只接受 payload hashes、source identity、layout/rmlib/docs19、config/code、unit 全部匹配的 COMPLETE。残留 `.tmp` 会被隔离后重算；局部 payload tamper、坏 JSON/TSV/schema parse 仅隔离并重算坏 unit；source/global pin drift 是全局 integrity failure，不会静默复用或重算。任何 incomplete run 都禁止发布 partial identity 结论。

跨节点 resume 只允许 `source_device_audit.observed_resolved_device` 的合法非负整数值变化。stored/current audit 都必须恰有 `binding/expected_resolved_device/observed_resolved_device/device_match` 四字段，`binding=audit_only`、expected 必须等于 config、bool 不得冒充 int，且 match 必须与相等关系自洽。audit 缺失、额外字段、伪 binding/expected/observed/match 均是 local checkpoint corruption，会隔离该 COMPLETE 后重算；不会被“忽略 device”逻辑吞掉。UNIT COMPLETE 与 payload manifest 同时采用 exact-field schema。

prepare/formal validation 的具体异常（含 source alias、realpath、stable identity 或 HDF5 pin drift）会先原子写入同 attempt 的 canonical metrics/report；随后 sbatch generic EXIT trap 只能保留该终态，不能用泛化的 exit-code 文本覆盖根因。

## 终态、并发与资源

终态包括 `FORMAL_RUNNING`、`FORMAL_INCOMPLETE_RETRYABLE`（nonsemantic，rc75）、`FORMAL_FAILED_INTEGRITY`（rc2）、`FORMAL_FAILED_RESOURCE`（rc70）、`IDENTITY_RECOVERY_TYPED_BLOCK` 和 `RECOVERY_COMPLETE`。每次状态发布都创建新的 content-addressed、不可变 `preview/states/<state-id>/`。verifier 要求 bundle 恰好只有七个已列出的 payload 文件和一个非自引用 `STATE_MANIFEST.sha256`；manifest 相对路径必须唯一、无 traversal，任何额外文件、目录、symlink、缺项或重复项都拒绝。它还绑定外部 payload hashes，旧 bundle 永不覆盖。唯一 canonical truth 是最后原子替换的 `preview/CURRENT_STATE.json`。在 pointer 切换前发生中断，旧 RUNNING pointer 及旧 manifest 仍逐行有效；完整新 bundle 验证后才允许切换。

owner lock 用 `squeue` 三态处理：LIVE 拒绝，DEAD 原子隔离旧 lock 后接管，UNKNOWN fail-closed。child monitor 每轮先检查已完成 nonzero，再判断 timeout；发现 nonzero 会立即 TERM/KILL+wait 其余 hang children。若 kill 后仍不能确认所有 child 已 reap，则标记 hard failure 但禁止发布新 terminal pointer，保留当前 RUNNING truth 供外部审计。sbatch 用 `#SBATCH --signal=B:TERM@900`，把 SIGTERM 转发给 Python parent。

资源为 private partition、4 CPU、48 GiB、3 小时、0 GPU。attempt absolute epoch 在 sbatch 主入口一次冻结，因此 prepare、tests、validation、resume/quarantine、queue 和 workers 全部计时。25% headroom completion cutoff 是 8,100 秒；其中显式保留最后 120 秒 publish reserve，所以 7,980 秒后不再 claim/launch 新 unit，且 final collect 完成后与 immutable attempt publish 前都必须仍早于该 claim deadline。只有最后的已冻结 attempt/state bundle 校验和 pointer 切换可使用 120 秒 reserve；source identity revalidation hook 返回后，程序在 `CURRENT_STATE.json` 原子替换的紧前一行再次读取 completion deadline。hook 将时钟从 8,099 推到 8,100 或 8,100.0001 秒时都保留旧 canonical pointer，绝不发布 `RECOVERY_COMPLETE`。已审 serial bound 15,878 秒意味着至少需要 1.9603× parallel speedup；BeeGFS speedup 未知且不作保证，unit checkpoint 只降低重试损失。

## 当前状态

当前为 `IMPLEMENTED_NOT_RUN` 静态实现；未提交 Slurm、未真实枚举 H5 datasets、未写 PASS gate。下一步必须由 fresh 独立 code review 决定是否允许提交。
# Run result: Job 11526687

The single reviewed attempt started on `gpu034` and failed after 4 seconds, before tests or any recursive H5 dataset enumeration. The source guard rejected `resolved_device=65` on the compute node because the login-frozen value was 42; symlink-target hash, inode, size, mtime and mode all matched. This is classified as a pre-scan execution-environment identity failure, not source mutation and not a scientific identity result. The canonical immutable state is `FORMAL_FAILED_INTEGRITY`, and no checkpoint unit exists. Automatic retry and every downstream stage remain prohibited until result tri-review and pivot.

# Repair result: Job 11526905

The narrow `st_dev` audit-only repair passed fresh independent review and the final authorized retry completed on `gpu034` in `01:40:52` (`COMPLETED`, `0:0`, 4 CPU/48 GiB/0 GPU). All 35 units completed with no temp state. The final denominator is 321,856 unique Families paths/objects, 321,856 consensus attrs and 321,818 model attrs.

The frozen 279 identifiers and 6,432,583 occurrences have exact conservation. The exhaustive case-sensitive exact-name scan produced zero candidates: recovered=0, ambiguous=0, invalid=0, missing=279. `X13_LINE` remains a separate 686-occurrence ambiguity audit. The canonical terminal is the semantic-successful valid negative `IDENTITY_RECOVERY_TYPED_BLOCK`; it does not mean the biological families are absent.

Post-run audit independently verified the immutable seven-file state, 64-file attempt payload, all 35 two-level checkpoint payloads, unique inventory and resolution rows. Three external CLI reviewers accept the result and close the partition-3 exact-name subroute. Pivot=`replace-component`: another official accession-backed identity source requires a human-gated contract and fresh code review; no retry, homology construction, DATA/GPU S0 or S1 is authorized.
