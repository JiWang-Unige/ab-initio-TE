# SF-DFAM39-ALLFAMILY-TARGET-CROSSWALK-AUDIT-20260812-R1

## 问题与科学边界

本 sibling gate 只回答：冻结的 Dfam 3.9 all-family EMBL 对既有 279 个 RepeatMasker family identifier（6,432,583 occurrence mass）提供了什么额外 exact-name 证据。它不建立全 catalog、不构造 homology component、不改 direct-superfamily 标签，也不授权 full-catalog、homology、DATA、GPU 或 S1。

父 curated Job 11527999 的 50 个唯一 identity 和 2 个 ambiguity（`L1HS`、`L1PREC2`）是权威基线。All-family 文件中 accession 为 `DF...` 的记录必须与该 curated payload 的 target candidate 逐项完全一致；任何遗漏、增加或 accession/consensus 漂移都是 integrity failure。`DR...` raw 记录只能报告 `RAW_ONLY_SUPPORT`：不得覆盖 50 个 curated resolution，也不得消解 2 个 curated ambiguity。因此，即使完整扫描成功，权威 crosswalk 仍不足时是 rc=0 的 valid-negative typed block，而不是 downstream authorization。

Direct label、10 个 U/ignore identifier（43,728 mass）及 `X13_LINE` audit-only（686 mass）保持冻结。Candidate selection 与 identity resolution 不读取 label/species；这些字段只在 resolution 完成后写入独立 audit 表。

## 输入与流式算法

正式源固定为：

- `refs/supp/dfam39-full-embl/Dfam-1.embl.gz`，size 2,677,249,806 bytes，SHA256 `5497d435...6467c`，MD5 `eafeb77c...585`；
- 官方 MD5 sidecar；
- `SOURCE_MANIFEST.json`，含 Dfam 3.9、CC0、gzip CRC 与 raw-only authorization。

正式 compute 在解析前从头重算 compressed SHA256 和 MD5，并在完整 gzip read 中验证 EOF/CRC。源的 device/inode/size/mtime/mode 在 hash 后、解压后、pointer 前必须与 pre-stat 一致。

解压只有一遍。解析器始终只保留当前一条记录；对约 4.1M 全记录仅计数，不 materialize record 或 consensus catalog。只有 exact target hit 才保留 relation 并规范化/哈希该条 consensus；candidate rows 另有 100,000 硬上限。

Repair 后 alias grammar 按字段严格区分：`NM/SN` 是一个非空 exact value，标点属于值而不是通用 terminator；`PI` 是一个或多个非空、分号分隔且以分号结束的 exact alias tokens；`DR` 是 `Database; Primary-id`，并接受、区分且只剥一个合法尾 `;` 或 `.`。匹配严格区分大小写；`AC/ID` 仅对符合 `^(DF|DR)[0-9]+(\.[0-9]+)?$` 的 target。严禁 prefix、case-fold、substring、空 token 或 heuristic。正式输出在 scan metrics、report 和 source manifest 中记录 DF/DR × NM/PI/SN/DR 的 line、token、terminator（含符号分层）与 target-hit counts。

## IO、状态与门禁

正式 payload 包含 14 个文件：13 个被 `PAYLOAD_MANIFEST.json` 哈希的成员，加上自排除的 manifest 自身。主要科学输出是 `allfamily_target_candidates.tsv`、label-blind `identity_resolution.tsv`、后 join 的 species/label audits、metrics/report 和 source/run/env manifests。

状态通过不可变 state bundle 与最后原子切换的 `CURRENT_STATE.json` 发布。完整但权威证据不足为 `ALLFAMILY_TARGET_CROSSWALK_TYPED_BLOCK`、`semantic_success=true`、rc=0；source/hash/CRC/reconciliation/conservation/runtime/resource 失败为 `AUDIT_FAILED_*`、semantic false、rc=2。Preview 只做小文件 pin 和 2.68GB source 的 topology/size stat，绝不读取正式大文件内容。

## 资源与提交合同

正式资源严格为 1 CPU、恰好 4096 MiB、2 小时、0 GPU，private partition。正式 runner 核 positive numeric Slurm job、CPU、memory 与 0-GPU，并绑定独立 code-review 哈希过的 sbatch。唯一授权提交命令：

`sbatch sbatch/SF-DFAM39-ALLFAMILY-TARGET-CROSSWALK-AUDIT-20260812-R1.sbatch`

禁止任何 sbatch CLI resource override。Grammar repair 后只生成新的 `IMPLEMENTED_NOT_RUN_REPAIR` immutable static state；旧 `slurm-11528157` attempt 保持不可变。未提交、未扫描正式 full source、未写 PASS gate。
# Superseded raw terminal — Job 11528157

The CPU-only job completed `0:0` in 3 minutes 13 seconds and its raw runner terminal was `ALLFAMILY_TARGET_CROSSWALK_TYPED_BLOCK`. It scanned 4,121,397 complete Dfam 3.9 records, including 4,095,118 raw DR records, and its DF candidates reconcile exactly to Job 11527999. Post-result tri-review found incomplete official PI/DR grammar handling, so the canonical semantic audit supersedes that raw terminal as `FAILED_RUN_GRAMMAR_COMPARABILITY`, with `semantic_success=false` and `valid_negative=false`. The observed zero raw target rows is not accepted as an exhaustive scientific conclusion; only a fresh grammar-repair attempt may re-evaluate it. No downstream stage is authorized.

# Final grammar-repair result — Job 11528267

The only authorized repair completed `0:0` in 3 minutes 13 seconds. Raw DR has 2,795 NM lines with zero target hits and no PI/SN/DR relation lines. Curated DF has 3,570 period-terminated DR references with 56 hits plus one NM hit, exactly reproducing the frozen 57 candidates. The final result is `ALLFAMILY_TARGET_CROSSWALK_TYPED_BLOCK`, semantic-successful and valid-negative. It leaves 50 unique, 2 ambiguous and 227 missing identifiers; all downstream authorizations remain false and no same-source retry is allowed.
