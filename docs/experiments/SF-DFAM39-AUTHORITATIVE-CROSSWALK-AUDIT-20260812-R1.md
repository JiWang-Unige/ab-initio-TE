# SF-DFAM39-AUTHORITATIVE-CROSSWALK-AUDIT-20260812-R1

## 问题与边界

本实验只回答：冻结的 Dfam 3.9 curated EMBL 是否能通过官方 exact relation，为父实验留下的 279 个 RepeatMasker family identifier（总 occurrence mass 6,432,583）建立 100% 唯一、带版本 accession 与 consensus SHA256 的 provenance。它不建 split、不聚类、不训练，也不授权 GPU、S1 或 homology 阶段。

Direct-superfamily 标签合同保持不变：10 个 label-contract-excluded identifier（43,728 records）继续 U/ignore；`X13_LINE`（686 records）只作 audit；homology 未来也只可用于 leakage-safe split component，不能替代预测标签。

## 官方输入与实际导出方言

唯一 identity source 是归档的 Dfam 3.9 curated EMBL `refs/supp/dfam39-authoritative-alias/supp-1.gz`。正式作业同时核 SHA256、文件大小、MD5 sidecar、release notes 与 CC0 声明。导出实际方言按文件本身冻结：`ID` 给 accession、SV 和序列长度，`NM` 才是 canonical name，`AC` 是 accession，`SQ`/body 是 consensus。字段形状为 records/ID/AC/SQ=26,279，NM=22,937，DR=3,570，PI/SN=0；缺 NM 的记录合法，但不能产生 NM match，且若由其他 alias 命中仍因缺 canonical name 标为 invalid metadata。

Exact relation 字段为 `NM/PI/SN/DR/AC/ID`。其中 `NM/PI/SN/DR` 是 exact alias；`AC/ID` 仅在冻结 target 本身逐字等于 accession/versioned accession 时作为 exact identity，严禁 prefix、case-fold、substring、当前 API、RepBase 本地 metadata、taxonomy 或 genome-copy fallback。

## IO 与 label-blind 门禁

解析器流式读取 gzip，标准化 `SQ` 为大写 DNA（U→T），核 declared length 与 IUPAC 后计算 consensus SHA256。`authoritative_candidates.tsv` 与 `identity_resolution.tsv` 只含 identifier、occurrences、官方 relation/identity 与 resolution，不读取或嵌入 direct label、species 或 split。之后才生成 `species_audit.tsv` 与 `label_conflict_audit.tsv`；任何同一 identity 的 direct-label conflict 都是 blocker。

279 identifier/6,432,583 occurrence 的两重守恒、ambiguous/missing/invalid/conflict 均为门禁。静态 probe 的 52 hit、50 unique、`L1HS`/`L1PREC2` 两个 ambiguous 只是对固定 source+parser 的回归 oracle；`scientific_result_precomputed=false` 表示 preview 不发布科学结果，正式 Slurm 作业必须从官方 gzip 重新解析并计算。按当前冻结资产，预期正式终态是语义成功的 `IDENTITY_SOURCE_TYPED_BLOCK`，而不是 recovery complete。

## 状态、闭包与资源

Preview/正式终态使用不可变 state bundle 与原子 `CURRENT_STATE.json` pointer。正式 attempt 另有 exact-file-set payload manifest，闭合 source、run、environment、candidate/resolution/audit、metrics/report 和 output index；package hash 覆盖 config、runner、tests、sbatch 与本实验文档，正式运行另钉独立 code-review gate。失败发布 `AUDIT_FAILED_INTEGRITY` 或 `AUDIT_FAILED_RESOURCE`，不会把 valid-negative 当 runtime failure。

资源严格固定为 1 CPU、恰好 2 GiB（2048 MiB）、20 分钟、0 GPU，单进程流式扫描；4096 MiB/4 GiB 等超配同样 fail-closed。只允许 positive numeric Slurm job id，使用 schedule-time 已存在的日志目录和 owner lock。

Slurm 没有跨版本可靠的 allocation walltime 环境变量，因此 runner 不伪造 runtime walltime 核验；正式授权只绑定独立 code-review 中逐字哈希过的 `sbatch/SF-DFAM39-AUTHORITATIVE-CROSSWALK-AUDIT-20260812-R1.sbatch`。唯一授权提交形状是 `sbatch sbatch/SF-DFAM39-AUTHORITATIVE-CROSSWALK-AUDIT-20260812-R1.sbatch`，禁止 `sbatch` CLI 的 `--time/--mem/--cpus-per-task/--gres/--gpus/--partition` 等资源覆盖。Smart-sbatch 必须使用该无 override 命令。当前状态仅 `IMPLEMENTED_NOT_RUN`，没有提交 Slurm，也没有写 PASS gate。
# Formal result — Job 11527999

The reviewed bounded CPU audit completed `0:0` in 14 seconds. The official Dfam 3.9 curated EMBL source is internally valid, but exact authoritative relations resolve only 50/279 identifiers; two are ambiguous and 227 remain unresolved. Terminal status is `IDENTITY_SOURCE_TYPED_BLOCK` with semantic success and valid-negative semantics. This result does not authorize homology split, DATA, GPU S0 or S1.
