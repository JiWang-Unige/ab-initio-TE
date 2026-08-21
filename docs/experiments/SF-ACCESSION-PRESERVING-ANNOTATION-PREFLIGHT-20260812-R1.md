# SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1

## 目的与边界

这是一个 6-record、CPU-only 的 annotation-time provenance **roundtrip smoke**，不是 representative concordance。它回答：在保持相同 consensus sequence 与相同 RepeatMasker raw class 的前提下，把 custom library 的 repeat identifier 从 canonical name 换成 Dfam versioned accession，是否能使 `.out` 保留 accession，同时不改变命中几何或 direct superfamily 标签。它不做全目录、同源 component、DATA、GPU 或 S1 授权，也不构成模型结果。

六条冻结记录覆盖 direct P1–P5；LINE/L1 用 `L1HS_3end` 与 `L1HS_5end` 两条 accession；`DR002419729.2` 覆盖无 canonical name 的 DR/RC 路径。exact fetch 命令模板和两臂 header grammar 均冻结在 config；formal 使用 pinned FamDB API 按 config order exact accession 获取记录，control header 为 `canonical_name#raw_class`（无 name 时用 unversioned accession），candidate header 为 `versioned_accession#raw_class`。export 后逐记录冻结 identifier、order、class、length、consensus SHA256 和整条 FASTA record SHA256；程序硬验 sequence/order/class 完全相同，唯一允许差异是 identifier。

## 输入、运行和输出合同

- 输入：pinned FamDB 3.9 partition 3/7、FamDB parser、RepeatMasker 4.2.2、RMBlast 2.14.1+、矩阵、S0 direct labeler、ontology 与当前 `docs/19_evaluator_contract.md` hash。大 H5 通过已冻结 layout/rmlib、symlink 与 resolved inode/mtime/mode/size，以及逐条 accession/consensus hash 绑定；本 preflight 不声称计算 60GB 分区全文件 SHA。
- formal 前必须通过 `scripts/pre_submit_gate.py`，并由 fresh `code_review_gate.json` 覆盖 config、runner、tests、sbatch、本文档的精确 hash。
- 资源严格为 private partition、1 CPU、4096 MiB、20 分钟、0 GPU；仅允许无资源 override 的 `sbatch sbatch/SF-ACCESSION-PRESERVING-ANNOTATION-PREFLIGHT-20260812-R1.sbatch`。
- direct labeler 的唯一科学输入是 `.out` 的 raw class；name/accession 只用于 provenance join，不能进入标签函数。
- pass 要求六条 candidate accession 全部唯一回连、raw class/label 全匹配、两侧语义几何 hash 和 direct-label payload hash 相同。几何 payload 按 canonical JSON 排序；字段包含 query/start/end/strand、score/div/del/ins、repeat begin/end/left、raw class、RepeatMasker fragment/group ID 与 overlap `*` 语义，只排除 repeat identifier。任一科学不等价是 `PREFLIGHT_VALID_NEGATIVE`（semantic success, rc0）；资产、parser、程序或资源失败是 `PREFLIGHT_FAILED`（semantic false, rc2）。
- 终态写入不可变 versioned bundle，逐文件 hash 后最后原子切换 `CURRENT`；manifest 外额外文件、symlink 或 payload tamper 均拒绝。
- 两臂命令各由 GNU `timeout` 约束为 300 秒，15 秒后强杀，runner 另设 330 秒 process-group kill/wait 兜底。formal runner 绑定非 symlink owner lock 与 numeric Slurm job；在切 terminal pointer 紧前重验 lock、标准 code-review gate、完整 reviewed package、source/stat/layout 和六条 family payload。
- Job 11528744 是 engineering failed run：allocation 实际为 1 CPU/4 GiB/20 分钟/0 GPU，但集群未导出 runner 旧逻辑依赖的 `SLURM_TIMELIMIT`，因此在 H5/RM 前 rc2；canonical `CURRENT` 未变，细节位于 `preview/attempt_failures/slurm-11528744.json`。修复后环境仅做 numeric job、CPU、memory、partition、0 GPU 快速检查；walltime 不再依赖可选环境变量。
- 权威资源合同改由 allocation 内 bounded `/usr/bin/scontrol show job <numeric-job-id> -o` 提供。runner pin `scontrol` 与 sbatch SHA，要求 rc0、空 stderr、单条 bounded 输出，并精确核验 JobId、Partition、TimeLimit=00:20:00、NumCPUs=1、ReqTRES/AllocTRES=`cpu=1,mem=4G,node=1,billing=2`、固定 Command/WorkDir 和无 override 的 SubmitLine。任何 unknown job、短/长时间、TRES/command/submit-line 漂移均 fail-closed。该合同在任何 H5 前、第一条 RM 命令前、publish 前和 terminal pointer hook 中复验；正式 bundle 输出 `SLURM_AUTHORITY.json`。
- 科学未通过时发布 `PREFLIGHT_VALID_NEGATIVE`，仍闭合两臂真实 `.out`、命令、export/hit/source/post-source manifests，rc0；runtime、signal、timeout、integrity failure 均为 semantic false、rc2。
- canonical failure 也受 owner capability 约束：只有 formal resources 已验证且同一 numeric job 当前仍持有原 owner-lock hash 时才能切 `PREFLIGHT_FAILED` pointer。owner 缺失、换主或在 publish hook 中变化时，仅写 `preview/attempt_failures/<attempt>.json` 并保持旧 `CURRENT` 不变；sbatch wrapper 使用同一规则。`--static-preview` 只允许 `CURRENT` 不存在或仍为 `IMPLEMENTED_NOT_RUN`，绝不能覆盖 PASS、valid-negative、FAILED 或 RUNNING 等正式状态。
- static、formal、failure 与 wrapper 的 canonical pointer writer 共享 `preview/.state-writer.lock` 非阻塞 `flock`。sbatch 创建/删除 formal owner 也受同一锁保护。static 在一段锁定临界区内读取初始 `CURRENT`、拒绝 owner、构建 bundle，并在 pointer replace 紧前同时重验初始 `CURRENT` 字节与 owner 不存在；CAS 失败只留下不可达 bundle，不覆盖并发 formal 状态。

## 当前状态

首次 formal Job `11528744` 为 `FAILED_RUN_RESOURCE_GUARD`：机器 gate 与 33/33 allocation-side tests 均通过，但 runner 随后因依赖非可移植的 `SLURM_TIMELIMIT` 环境表示而退出 `2:0`。Slurm authoritative record 显示资源本身确为 1CPU/4GiB/20m/0GPU。失败发生在任何 FamDB record 读取和 RepeatMasker 命令前；canonical `CURRENT` 未改变，仅写 attempt-local failure。旧 code-review 授权已消费，禁止原样重提；修复、fresh review 和新 gate 前没有 retry 授权。

唯一授权的 repair retry Job `11528885` 随后通过机器 gate、37/37 tests 和 strict `scontrol` authority reconciliation，但在构造 pinned official FamDB 对象时因 `FamDBLeaf` 不存在 `added` 属性而退出 `2:0`。RepeatMasker 未启动，未产生 roundtrip geometry 或 valid-negative。canonical `CURRENT` 指向 `PREFLIGHT_FAILED`，并由 `AUDITED_MANIFEST_11528885.sha256` 闭合。一次修复重试预算已耗尽；必须先走 result tri-review/pivot，禁止自动第三次重试。

## Stop gates

`full_catalog_stage_authorized=false`、`homology_split_authorized=false`、`data_stage_authorized=false`、`gpu_authorized=false`、`s1_authorized=false` 始终不被本实验解除。即使 `PREFLIGHT_PASS`，也只允许后续**真实窗口 CPU representative gate**，不能自动晋升。

旧 canonical S0 来自 RepeatMasker 4.2.2 `-species` 与 overlay 形状；本 smoke 使用 Dfam-only custom library，因此属于新 benchmark，不能继承旧 S0 的可比性或指标。future gates 必须依次补：真实窗口 representative concordance；与旧 ledger 类别 exact-once 对账和 6,432,583 occurrence 守恒；冻结 accession+consensus 作为 homology split-only 输入并验证 component zero-overlap；最后才可讨论 DATA/GPU。任何前置 gate 未闭合都不得跳序。
