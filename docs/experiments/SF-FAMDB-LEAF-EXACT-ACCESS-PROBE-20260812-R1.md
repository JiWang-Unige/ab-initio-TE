---
exp_id: SF-FAMDB-LEAF-EXACT-ACCESS-PROBE-20260812-R1
date: 2026-08-12
approach_family: accession-preserving-superfamily-data
parent_exp: SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1
motivated_by: "replace failing aggregate FamDB export with a leaf-level exact-access probe"
track: S
profile: smoke
status: failed
primary_metric: leaf_exact_access_pass
one_liner: "Exact-access observations remain unknown because read-mode cleanup failed before publication"
---

# SF-FAMDB-LEAF-EXACT-ACCESS-PROBE-20260812-R1

## 问题与范围

这是 Job 11528885 tri-review/pivot 授权的独立 CPU probe，只回答 installed FamDB 3.9 的 leaf-level exact accession API 能否稳定取得六个已冻结 family。它不运行 RepeatMasker、不导出 annotation benchmark、不扫描 genome、不解析 name/prefix/alias，也不创建 homology split。

六个 target 为 `DF000000002.4`、`DF000000225.4`、`DF000000226.4`、`DF000000416.4`、`DF000000859.4`、`DR002419729.2`。formal 对每个 unversioned accession 依 config 顺序调用全部 12 个 leaf 的 `FamDBLeaf.get_family_by_accession`，因此形成精确 6×12=72 调用矩阵。每个 target 必须只在一个 partition 命中，且命中的 partition、versioned accession、canonical name、raw class、consensus length 与 consensus SHA256 全部等于冻结值。

## 禁止项和终态

- 禁止 `get_family_by_name`、prefix/case/alias/copy fallback；禁止 top-level convenience resolver 掩盖 leaf 行为。
- `LEAF_EXACT_ACCESS_PASS`：六个 target 均 exact-once 且字段全匹配；只允许提出新的 leaf-adapter preflight 人闸，不能直接进入 annotation、catalog、homology、DATA、GPU 或 S1。
- `LEAF_EXACT_ACCESS_TYPED_BLOCK`：missing、跨 partition duplicate 或冻结 identity/version/sequence 漂移；semantic success、rc0、`route_stop=true`。
- `LEAF_EXACT_ACCESS_FAILED`/attempt-local failure：API/schema、asset、runtime、Slurm、gate 或 manifest integrity 失败；semantic false、rc2。

## 运行与完整性合同

formal 资源固定为 private partition、1 CPU、4096 MiB、10 分钟、0 GPU。环境负责 positive numeric JobId/CPU/memory/partition/GPU 快速检查；bounded pinned `scontrol show job -o` 精确核 JobId、TimeLimit、NumCPUs、TRES、Command 与无 override SubmitLine。正式运行前需标准 fresh `code_review_gate.json` 覆盖本 exp 的 config、runner、tests、sbatch 和本文档。

source 闭包包含 rmlib config、12-partition layout、FamDB parser modules、docs/19 hash，以及 12 个 resolved H5 的 filename/size/inode/mtime/mode。source/package 在 probe 前后和 terminal pointer 前复验；科学 payload 在唯一一次 72-call probe 后冻结并写入 manifest。输出采用 immutable bundle、exact payload manifest、共享 writer mutex、owner job binding与最后原子 `CURRENT` 切换。

正式科学调用严格只有一次 6×12=72-call leaf probe；metrics 的 `probe_call_count=72` 与真实 API 调用数一致。terminal hook 不再调用任何 FamDB API，只复验初始 owner、review gate、package、source/stat 与 scheduler authority，避免把 144 次调用误报为 72 次。

`ReqTRES` 与 `AllocTRES` 使用严格 token parser：仅允许且必须恰好出现一次 `cpu=1,mem=4G,node=1,billing=2`；duplicate/conflict、空 token、缺键、未知键、GRES/GPU 或其它形状全部 integrity fail。canonical failure 只有在 formal 已取得完整 initial authority context，且发布前与 pointer hook 中两次重验同一 owner/gate/package/source/scheduler 均通过时才能切换；上下文不完整或任一 authority 漂移则只写 attempt-local rc2 证据，不改变 canonical `CURRENT`。

## 当前状态

Job `11533175` 已运行并判定为 `FAILED_RUN_FAMDB_READ_MODE_FINALIZE_API`。精确资源、机器 gate 和 23/23 allocation-side tests 均通过；唯一一次内存 72-call probe 返回后，cleanup 调用 `FamDB.finalize()`，read-mode leaf 因没有写模式 bookkeeping 属性 `added` 而抛出 `AttributeError`。观察尚未冻结/发布，因此 exact-access 结果未知，不能判 PASS 或 typed block。

完整审计由 `outputs/SF-FAMDB-LEAF-EXACT-ACCESS-PROBE-20260812-R1/AUDITED_MANIFEST_11533175.sha256` 闭合。one-shot 代码审授权已消耗；当前等待 tri-review/pivot，所有下游授权保持 false。

Post-result chain 已关闭：`2/3 DEGRADED_REVIEW`，Claude=`run-sanity-check-first`、Codex=`replace-component`，两者行动一致，允许一个新 namespace 的最终 close-only lifecycle repair；Antigravity 三次 retry均无有效评审。Pivot=`replace-component`，旧 exp 不再提交。任何下一次 API/lifecycle/integrity failure 或 semantic typed block 都永久关闭该 access/export 路线。
