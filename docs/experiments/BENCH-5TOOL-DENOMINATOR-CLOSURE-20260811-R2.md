---
exp_id: BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2
date: 2026-08-11
status: FAILED_SEMANTIC_AUDIT
claim_eligible: false
parent_exp: BENCH-5TOOL-SMOKE-20260811-R1
---

# BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2

## 目的

这是 R1 valid-negative identity smoke 后的严格运行时闭合实现。它不运行生物学 benchmark、不读取或改写 R1，也不允许把 mutable tag、旧 HiTE 3.0、仅凭未固定来源的 EDTA `v2.3` banner，或 TEtrimmer 1.7.2 当成目标版本。

## 固定 gate

- Dfam：已归档的 `famdb/` legacy v1 虽可审计 bytes，但因没有 `preparation_slurm_job_id`，只能产生 provenance-limited typed block，绝不能驱动 RM/EG `ENGINEERING_PASS`，`prepare_famdb.py` 也绝不把它报告为 `ALREADY_PREPARED`。新的 v2 资产只允许原子创建在独立 `famdb-v2/` target，不覆盖旧目录；manifest 必须恰有两个 input rows 与两个 output rows，逐行固定 `full→dfam40.0.h5`、`curated_consensus→dfam40.curated.consensus.0.h5`，拒绝 duplicate/extra/mapping tamper。v2 就绪后，`famdb.py info`、`MIR3` query 才可运行并报告 Dfam 4.0。
- RepeatModeler2 + RepeatMasker：2.0.9/4.2.4 identity、FamDB query、`-species 'Homo sapiens'` tiny FASTA launch、canonical interval adapter 均为必需。
- Earl Grey：7.3.0 identity、容器内同一个 Dfam 4.0 query、tiny FASTA launch、adapter 均为必需。FamDB 精确 bind 在其官方期望的 `Libraries/famdb` 路径，不能只用 `-lib` 假装已配置数据库；唯一接受的坐标产物是 `r2_EarlGrey/r2_summaryFiles/r2.filteredRepeats.gff`。
- HiTE：仅允许 OCI digest `sha256:902c…e4ce` 获取的 3.3.3 SIF；v2 manifest 必含 SIF、runtime help、Apptainer inspect、source commit、preparation job/code/config/env hashes，且 runtime 重新执行 3.3.3 identity；脚本默认网络关闭，缺镜像是 `FOUNDATIONAL_TYPED_BLOCK`。
- EDTA：基础 SIF 单独打印 `v2.3` 不能证明 2.3.0。2.3.0 身份由 exact `v2.3.0` tag dereference、固定 commit `a9f7…9fc2`、完整 source-tree hash 与 `EDTA.pl` payload hash共同建立；runtime 只执行官方 `-h`，并严格接受其真实 banner `Extensive de-novo TE Annotator (EDTA) v2.3`。不要求 payload 源码字符串写成 `v2.3.0`，也不调用会非零退出的 `--version`。
- TEtrimmer：固定 1.7.4 source tar + Pfam-A.hmm、Pfam-A.hmm.dat、四个 hmmpress index 缺一不可。identity 只能从官方 `--help` 的精确 `Version: 1.7.4` 解析，绝不调用 `--version`。最终 library 精确固定为官方文档的 `TEtrimmer_consensus_merged.fasta`，随后必须由 hash-pinned RepeatMasker 4.2.4 `-lib` 运行并适配其 `.out`。当前只有 mutable `current_release` URL、没有两个官方 gzip SHA-256，因此该 cell 固定为 `PREPARATION_TYPED_BLOCK`，preparation sbatch **没有可提交的 pfam action**；禁止隐式下载和已知必失败提交。

## 运行与产物

所有 preparation 和 runtime 都只能在 Slurm CPU allocation 运行；登录节点不得执行。真实 runtime smoke 通过 `sbatch/BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2.sbatch` 提交。collector 在发布前取得 job ownership lock；release 只有在磁盘 lock payload 与本 job payload 完全相等时才删除。rerun 先原子把顶层 `STATUS` 切为 `RUNNING` 并在 archive 保存旧 status，再移动旧 metrics，避免任何 `COMPLETED` 但 metrics 已消失的观察窗口；新的四件套由 attempt staging 原子 rename，最后才写 `COMPLETED`。输出位于 `outputs/BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2/`，专属资产位于 `software_outputs/tefm_new_directions/BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2/`。

计划资源：CPU-only，8 CPU、96 GB、最多 4 小时；允许的 preparation 只有 `famdb|hite|edta`，必须经 `sbatch/BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2-preparation.sbatch` 的独立 CPU job并显式指定 `TEFM_PREP_ACTION`。每个 action 有独立 token lock；只有 `squeue` 成功且明确证明旧 owner 不活跃时才恢复 stale lock，scheduler unknown/error 一律 fail-closed；trap 只 compare-and-delete 自己的 token。主/prepare 两个 sbatch 都先激活 `benchmark_core`、写 job-specific explicit environment snapshot，并运行 `pre_submit_gate.py`。download-only 不属于生物学 benchmark。

## R2 review 修复（2026-08-11）

- 每个 cell 只消费自己的 fixture/component/license/database prerequisites；某个工具缺失不会连带阻塞无关 cell。每次 runtime 重算 fixtures、component、FamDB marker/HDF5/manifest 的 SHA-256；任何 mismatch 只阻塞对应 cell。
- 每条容器命令用 `--cleanenv` + dead proxy 封网，用独立 stdout 做 version regex，不允许合并日志搜版本；`/usr/bin/time -v` 记录 peak RSS。
- Earl Grey 绑定官方 FamDB `Libraries/famdb` 路径并使用 `-r 9606`；fixture 是冻结的官方 test FASTA，非人造 1.6kb 序列。
- HiTE、EDTA、TEtrimmer 在相应 manifest 完整时会实际跑 identity/help/minimum。EDTA 通过官方 tag dereference+commit/tree/payload 证明 2.3.0 source identity，并用 `-h` 的官方 `v2.3` banner做 runtime identity；TEtrimmer 只从 `--help` 解析 1.7.4。
- 指标由 config 的 `expected_cell_keys` 与实际 cell results 推导：`terminal_cell_count` 不再写死；缺失/多余 cell、`INVALID_RUN` 或 `ENGINEERING_PASS` 但 identity 未满足都会使 `semantic_success=false`，collector 返回非零。额外报告 `engineering_pass_fraction`、`invalid_cell_fraction` 和 `silent_substitution_count`，不会把 0–1 的工程比例错送给 goal validator。
- TEtrimmer readiness 后必须先得到唯一冻结 library，再在 RepeatMasker 4.2.4 中以 `-lib` 对冻结 genome 运行，唯一接受显式 `.out` 的 canonical interval adapter；不会把 library FASTA 假装成区间。
- input manifest hash 覆盖 config、runner、contract tests、全部 prep scripts、两个 sbatch、exp doc、evaluator contract、adapter、license dossiers 与 job-specific conda explicit environment；各可获取资产的 v2 manifest 另含 preparation code/config/env hashes。
- 当前 Pfam URL/release 已登记但压缩包 SHA-256 尚未冻结；config 明示 `preparation_submittable=false`，preparation sbatch 不提供该 action，runtime 稳定产出 typed block。

## 离线 contract tests

`test_contract.py` 不启动容器、不做研究计算，行为级验证：legacy v1 完整但仍被拒绝运行；v2 source→output mapping tamper 与 extra row 被拒绝；EDTA 官方 v2.3 help 接受而 v2.3.2 被拒；TEtrimmer 仅由 help 识别 1.7.4；main/prep lock 错 owner 不删除、`squeue` failure 不恢复；另覆盖 `Libraries/famdb` bind、expected-cell metrics、silent substitution、Earl Grey/TEtrimmer 最终路径、两 sbatch gate 与 Pfam non-submittable。

## 正式 bounded runtime 结果

- Preparation：Jobs `11522328`（FamDB-v2）、`11522329`（HiTE 3.3.3）、`11522330`（EDTA 2.3.0 source）均完成并原子发布；Pfam action 按合同未提交。
- Main：Job `11522405` 完成 collector 并写 `STATUS=COMPLETED`。`metrics.json` 与 `semantic_validation.json` 可解析、有限且相互一致；`artifact_manifest.json` 的 778/778 项重算 SHA-256 均匹配。
- 原始 collector 终态：`terminal_cell_count=5`、`ENGINEERING_PASS=0`、`FOUNDATIONAL_TYPED_BLOCK=5`、`INVALID_RUN=0`。独立结果审计拒绝该语义：四个已经启动后非零退出/集成失败的 cell 必须是 `INVALID_RUN`，只有未启动且缺不可变 Pfam 的 TEtrimmer 可保留 `FOUNDATIONAL_TYPED_BLOCK`。审计后为 `INVALID_RUN=4`、`FOUNDATIONAL_TYPED_BLOCK=1`、`semantic_success=false`、`FAILED_RUN`。

### 逐工具阻塞

- RepeatModeler2 2.0.9、FamDB 4.0、最小 discovery、RepeatMasker masking 与 43-row canonical adapter 实际成功；唯一失败是把 RepeatMasker 4.2.4 的不支持参数 `-version` 当 identity CLI，命令退出 1。因此是 identity-probe implementation block，不是 runtime/database block。
- Earl Grey 7.3.0 help 与直接 FamDB 4.0 query 成功；官方 `-r 9606` 路径仍报 `FamDB data directory not found`。直接 wrapper 可见数据库不等于 Earl Grey 内部 `getRepeatMaskerFasta` 可发现数据库。
- HiTE 镜像/manifest 是 exact 3.3.3，但在 `apptainer exec --cleanenv ... bash -lc` 中 `python` 不在 PATH，identity 和 minimum 均退出 127；需要冻结容器真实解释器/entrypoint，而不是换镜像版本。
- EDTA 2.3.0 source identity 与官方 `v2.3` help 均通过；最小 fixture 在 TIR-Learner 的 pandas indexing 处 `KeyError: 0`，随后缺少 TIR 产物并退出 2。该问题是 fixture/TIR runtime incompatibility，不是 timeout 或版本替换。
- TEtrimmer 1.7.4 source tar 身份可用，但不可变 Pfam release、gzip hashes、checksum manifest/index 仍缺失，因此未执行，按预注册基础资产门 typed block。

### 独立语义审计与解释边界

- 原始 `STATUS=COMPLETED` 与 `semantic_success=true` 只证明 collector 完成写盘，不能作为结果有效性结论。权威覆盖层为 `result_semantic_audit.json`、`metrics.audited.json`、`AUDITED_STATUS` 和 `validate_goal.json`；validator 确定性返回 `failed_run`。
- 不允许据此声称任何 workflow 科学性能差，也不允许用旧版本或结果后换版本填格。
- Slurm accounting DB 在结果归档时不可用；未伪造 elapsed/MaxRSS。每条子命令的 `/usr/bin/time` 证据仍保留，观测的最大单命令 RSS 为 EDTA `768112 KB`。
- 下一步是 failed-run 硬停。必须修复 cell 分类器以及 RM identity、Earl Grey FamDB discovery、HiTE launcher、EDTA runtime integration，再重新代码审查；TEtrimmer 继续保持合法 Pfam typed block。当前不直接重跑。
