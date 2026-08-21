# BENCH-RM-HITE-VALIDITY-20260811-R1

## Job 11523819 result

- Overall `FAILED_RUN`: 4 CPU/48 GiB/0 GPU, about 18m32s; `semantic_success=false`, deterministic validator failed-run.
- RM cell passed exact runtime identity/minimum/adapter: RepeatModeler 2.0.9, RepeatMasker 4.2.4, Dfam 4.0, 43 canonical rows.
- HiTE cell proved exact 3.3.3 identity and launched correctly, but hit the 600-second cap during step 3.3 before `HiTE.gff`; status `INVALID_RUN`, not version mismatch.
- Artifact manifest verifies 334/334 files. No biological benchmark or tool-quality conclusion is permitted.
- Stop pending tri-review/pivot; no automatic paired retry or other workflow expansion.
- 3/3 external tri-review closed the failed run. Pivot freezes this RM cell as reusable runtime-validity evidence and selects one separately reviewed HiTE-only continuation with a preregistered 1800s cap. The original aggregate remains failed; any reconciliation must cite both jobs and exact shared hashes.

状态：`IMPLEMENTED_NOT_RUN`；code-review gate：`BLOCKED`；禁止提交直至独立复审写入 PASS。

## 研究问题与边界

这是从 `BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2` 派生的、claim-ineligible、offline bounded CPU validity smoke。它只回答两个已修复 cell 是否能达到完整 `ENGINEERING_PASS`：

- `repeatmodeler2_repeatmasker`：RepeatModeler 2.0.9、RepeatMasker 4.2.4、Dfam 4.0 的 identity、最小输入和 RepeatMasker `.out` adapter。
- `hite`：digest-pinned HiTE 3.3.3/source commit 的 help identity、direct-argv 最小输入和最终 `HiTE.gff` adapter。

runner 没有 Earl Grey、EDTA 或 TEtrimmer handler，也没有动态 fallback dispatch；`expected_cell_keys` 和 handler namespace 均被运行时断言为上述两个 exact keys。父 config、父 runner、adapter、两项 preparation code 和所有复用输入/容器/manifest 均 hash-pin；父文件漂移会在任何 cell 执行前 fail closed。

RepeatModeler/RepeatMasker 复用的 FASTA 字节来自 EDTA 官方 test repository，但这里只把它当作 hash-pinned 输入 fixture；不会调用 EDTA 代码、容器或 cell。

## 语义与成功合同

- `ENGINEERING_PASS`、`FOUNDATIONAL_TYPED_BLOCK`、`VERSION_MISMATCH`、`INVALID_RUN` 是 terminal states。
- 只有尚未执行任何命令时发现 immutable fixture/component/manifest/license 缺失或不匹配，才允许 `FOUNDATIONAL_TYPED_BLOCK`。
- 已执行命令 nonzero/timeout，或已执行 minimum/adapter 失败，必须是 `INVALID_RUN`；此时 `semantic_success=false` 且进程返回 2。
- HiTE help rc0 但实际 banner 不匹配时，有意不运行 minimum/adapter，记 `VERSION_MISMATCH`。该分支严格断言 exactly one `hite_help_identity`、rc0、非 timeout、实际 mismatch、adapter 未尝试；observed identity 只保存实际 stdout path/hash/banner。
- `VERSION_MISMATCH` 可以是语义完整的有效 terminal，因此可令 `semantic_success=true`；但本 repair goal 只有 exact 2/2 `ENGINEERING_PASS` 才令 `repair_goal_success=true`。
- missing/unexpected cell key、任何 `INVALID_RUN` 或 silent identity substitution 都令 semantic failure。

## 资源与产物

- Slurm：`private-teodoro-gpu`，4 CPU，48 GiB，1 小时，0 GPU。
- bounded runtime：identity 60 秒、DB probe 60 秒、minimum 600 秒；8 个命令 timeout 总和 2100 秒，每个 timeout 均有 10 秒强杀 grace。计入 300 秒资产哈希预算和 120 秒发布预算后，静态最坏预算仍保留 900 秒 headroom 和额外 100 秒未分配余量；运行时全局 deadline 还会按已耗时缩短后续命令，防止 4.7 GB 资产哈希或收尾挤掉余量。
- 网络：容器内 proxy 固定到 loopback discard endpoint；不允许下载或准备新资产。
- 独立输出：`outputs/BENCH-RM-HITE-VALIDITY-20260811-R1/attempts/attempt-$SLURM_JOB_ID/`。
- 独立 ownership lock：`outputs/.../.collector.lock`，squeue unknown/error fail closed，只有确认 inactive 且超龄才回收，release 只删除自身 token。
- canonical publish：`metrics.json`、`semantic_validation.json`、`command_manifest.json`、`artifact_manifest.json` 经 attempt staging 后原子发布；`STATUS` 最后更新。

## 提交门禁

`sbatch/BENCH-RM-HITE-VALIDITY-20260811-R1.sbatch` 在执行 runner 前调用 `scripts/pre_submit_gate.py`。当前 `outputs/.../code_review_gate.json` 是明确的预览 `BLOCKED`，不是 PASS，也没有 waive。静态测试不得运行容器或研究计算。
