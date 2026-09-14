# OmniBenchmark 0.6.0：TE benchmark 最小接入与方法矩阵

**日期：** 2026-09-14

**状态：** ENGINEERING_ONLY / 设计审阅和最小 synthetic smoke 已完成；没有提交作业、训练或启动真实工具。

**目的：** 给后续公平 benchmark 提供一个最小、可运行、可保留失败分母的 OmniBenchmark 接入合同。toy full-truth 通过后仍只代表工程连通性，不能作为科学结果。

## 1. 本地 API 审阅结论

本地独立环境为 `/Users/jiwang/Desktop/TE/manuscript-review-20260914/omnibenchmark-venv`，Python 3.12，`ob --version` 为 **0.6.0**。本节依据该环境的 Pydantic model 和 CLI 源码，而不是假定旧版 YAML。

| 组件 | 0.6.0 实际接口 | 接入决定 |
|---|---|---|
| Benchmark 顶层 | 必填 `id`、`benchmarker`、`version`、`software_backend`、`software_environments`、`stages`；`metric_collectors`、`storage` 可选 | toy 使用 `api_version: "0.5.0"`、`software_backend: host`，省略 storage |
| `software_environments` | model 是带 `id` 的 list；`from_yaml` 兼容 dict 并转换 | 配置用 canonical list，避免隐式转换；host 只用于本机 toy，Baobab 以后再选 envmodules/apptainer |
| Repository | `url` 和 `commit` 必填；`entrypoint` 是 module 仓库 `omnibenchmark.yaml` 中的**命名键**，默认 `default` | 复用现有项目 Git 仓库和一个固定 commit；第一阶段只用一个 named entrypoint，不用五个 repository、branch 或 unpinned |
| Module | `id`、Repository 必填；`parameters` 支持 dict grid；`exclude/requires/resources` 可选 | 参数显式给 `id`，不要旧 `values` CLI 格式；模块级 outputs 不作为主要路径接口 |
| Stage | `id`、`modules`、`outputs` 必填；简单 `inputs: [id, ...]` 会转为 InputCollection；输入必须逐字匹配已声明的 output `id` | 用单一 `data`→`methods`→`metrics` 主链；output ID 使用全局名（如 `data.truth_source`），path 使用简单文件名 |
| MetricCollector | `inputs`、`outputs`、Repository 必填；会收集所引用 stage 的**全部 output files** | 一个 collector 收集所有 score/status JSON；不让 collector 重算科学指标 |
| Resources | `cores/mem_mb/disk_mb/runtime/gpu` 任一正值即可；generator 未指定时默认 2 cores | 为每类方法显式写 cores/mem/runtime；GPU 只给当前 D 的 GPU cell |
| storage | 可选；host/local benchmark 不需要 S3 | 第一阶段不引入远程 storage 或新 artifact/hash 框架 |
| CLI | `ob validate plan`、`ob run --dry`、`--continue-on-error`、`--cores`、`--module`、`ob describe` | 先做 plan validation 和 dry generation；真实执行需另有批准 |

本地源码入口：`omnibenchmark/model/benchmark.py` 中 `Repository`、`Stage`、`MetricCollector`、`Benchmark`；`backend/resolver.py:291-310,728-815` 负责 named entrypoint；`backend/snakemake.py:132-148` 在 API ≥0.5 为普通节点自动写 `performance.txt`。输出路径含 `/` 会产生 0.6.0 FutureWarning，故使用短文件名让 Omni 自动按 stage/module/parameter 嵌套。

### 两个执行拓扑约束

1. 0.6.0 的执行 resolver 对 divergent branches 的 re-join 仍有限制；一个 stage 同时从两个互不祖先的 branch 取 input 会被 diamond guard 拒绝或无法解析。将 genome、truth、lengths、library manifest 都由**同一个 data stage**产生，所有方法放在同一个 methods stage，metrics 只沿该线消费，避免这个问题。
2. `MetricCollector` 只在上游节点可解析后收集文件。若 native job 硬失败导致 collector 无法运行，最终状态汇总必须读取预先冻结的 `cell_registry`、已写 status sidecar 和 `.logs`；不能因 collector 缺上游而删除该 cell。失败、超时、unsupported、输入非法都保留在预期分母中。

## 2. 现有脚本能复用什么、第一阶段只接什么

### `LEMMI-TE-BENCH-20260824-R1/adapter.py`

现有 adapter 已提供稳定的核心转换/评价：

- `convert` 支持 BED、GFF3、RepeatMasker `.out`，输出 canonical TSV：`seqid,start,end,name,score,strand,source,attributes`，统一为 zero-based half-open；
- `evaluate` 接受 canonical truth/prediction 和 contig lengths，支持 `T0/T1`、IoU、boundary tolerance、`flat_union/require_nonoverlap`；
- `T1` 会将 precision/F1 置空，只保留 positive recall、boundary、fragmentation 相关读数；评估不从 caller 自己的 Dfam 输出推断 truth；
- 目前没有 `T2` 分支，也不恢复 biological instance identity，故 T2 需独立 diagnostic entrypoint，insertion 级指标不能凭 binary fragment 构造。

Omni 普通节点会自动执行类似 `entrypoint --output_dir ... --name ... --<input> ... [params]`。因此不能把 `adapter.py` 直接设为 entrypoint：它要求 positional subcommand `convert`/`evaluate`，且参数是 `--output`、`--prediction` 等。第一阶段只需在现有项目内放一个很薄的 bridge，将 synthetic source 交给原 adapter 的 `convert`，再把其 canonical 输出交给原 adapter 的 `evaluate`；原 adapter 逻辑和旧评分器不改。这个 bridge 是接口适配，不是新的评分器，也不接入模型或外部 caller。

### `CROSS-SPECIES-L1-FASTA-INFERENCE-V1/infer_fasta.py`

该脚本是 sequence-only material inference，输入为 `--fasta`、model/tokenizer/calibration 路径，输出固定的 probability/material/ambiguity/summary 文件；它的 `--output-dir` 与 Omni 的 `--output_dir` 不同，也没有 Omni 的 `--name` 参数。源码已经提供真实的 `--cpu` 开关（`infer_fasta.py:206`），后续成本 cell 应原样传递这个开关，不另设计一个同名或替代参数。当前 D wrapper 属于后续扩展：将 stage input 映射成 `--fasta`，将固定模型/校准参数作为 benchmark parameters，转换 output dir，并将 material runs 转成 canonical prediction TSV；它不进入第一阶段的 fixture smoke，也不改变模型、校准或推理协议。

### 第一阶段的仓库边界（本轮只设计）

```yaml
entrypoints:
  default: benchmarks/te_omnibenchmark/te_smoke.py
  rc0: benchmarks/te_omnibenchmark/rc0_fixture.py
```

本轮已在现有 `ab-initio-TE` 内增加一个小 benchmark 目录和根级 `omnibenchmark.yaml` 的 named `default`/`rc0` 入口（0.6.0 metadata 要求模块引用命名入口），并用 synthetic fixture 实际跑通 adapter、T0/T1 evaluator 和 collector；不新建 benchmark repository，不为尚未接入的工具放置空 wrapper、CITATION/license 体系或额外仓库。default 证据见 [OMNIBENCHMARK-SMOKE-20260914.md](OMNIBENCHMARK-SMOKE-20260914.md)，RC0 证据与命令见本文件上方的 RC0 小节。

## 3. 最小可运行 DAG（仅工程 smoke）

```text
data/fixture
  ├─ data.genome              toy FASTA
  ├─ data.truth_source        synthetic truth in source format
  ├─ data.prediction_source   synthetic prediction in source format
  ├─ data.truth_t0            complete synthetic truth view
  ├─ data.truth_t1            positive subset view
  ├─ data.lengths             contig lengths
  └─ data.cell_registry       every method × task × device expected cell
          │
          ▼
methods/adapter_convert
  ├─ methods.truth_canonical
  └─ methods.prediction_canonical
          │
          ▼
metrics/{eval_T0,eval_T1}
  └─ metrics.score             adapter JSON with tier-specific nulls
          │
          ▼
collector
  └─ benchmark.summary         gathered scores, statuses and expected/realized denominator
```

工程 smoke 的顺序固定为 **fixture → 现有 adapter convert → 现有 adapter T0/T1 evaluate → collector**。synthetic source 只代表 BED/GFF/RepeatMasker 等输入格式和坐标转换，不代表 HiTE、RM、EDTA 或当前 D 的科学运行。T2 本轮不运行；如需接入，只先单独验证 diagnostic schema，不填充绝对准确率。为避免 Omni 的 diamond guard，data stage 一次输出 fixture 所需的 truth、prediction、lengths 和 registry；真实方法后续仍只能接收 genome/callable input，不能看到 truth。

### toy full-truth fixture 的验收范围

只用小型 synthetic FASTA 和 synthetic source files，至少包含：两个 contig、相邻独立 insertion、一个 fragmentary/overlap case、已知边界和一个 T1 positive view。toy 运行要验证：named entrypoint、BED/GFF3 坐标转换、T0 完整 precision/recall/F1、T1 precision/F1 空值、自动 `performance.txt`、collector 汇总和失败状态保留。RepeatMasker `.out` 仍是后续 adapter cell 的接口，不在本轮 toy 验收中。T2 仅保留未来 schema 检查项，不是本轮运行验收项。toy 的所有结果标为 `ENGINEERING_ONLY`，不进入论文数值或方法排名。

`cell_registry` 预先列出每个 profile 期待的 method/task/device cell。每个 wrapper 都写 `{status, method, task, input_id, output_schema, runtime_mode}`；允许值至少为 `COMPLETED`、`FAILED`、`TIMEOUT`、`UNSUPPORTED`、`INVALID_INPUT`、`BLOCKED`。最小 smoke 使用名称明确的 `synthetic_status_unsupported` 和 `synthetic_status_blocked` 占位 cell，避免把未运行的真实方法误读为能力结论。科学汇总按 registry 分母统计，缺文件不转成零分，也不静默剔除。

### RC0 的单模块接入

`benchmarks/te_omnibenchmark/rc0.yaml` 和 named `rc0` entrypoint 提供一个
同样很小的工程 fixture：data stage 产生固定 synthetic genome/truth，methods
stage 产生 F、映回 RC、mean 和 phase-mean 四个 source-format BED，metrics
stage 将 4×2（arm×T0/T1）展开交给现有 adapter，collector 同时保留一个
`UNSUPPORTED` 和一个 `BLOCKED` 状态。它检查的是 RC0 的参数展开、坐标合同、
T1 空 precision/F1 和失败分母；没有真实模型、RepeatMasker 或生物学数据，
不能进入论文结果。

在 macOS arm64 上，Snakemake 默认 CBC 调度器会因缓存的 x86_64 solver
返回 `Bad CPU type in executable`；使用 `--scheduler greedy` 可绕过这一环境
问题。实际验收命令为：

```bash
ob run benchmarks/te_omnibenchmark/rc0.yaml --dirty \
  --out-dir /tmp/te-omnibenchmark-rc0-20260914-c --cores 1 \
  -- --scheduler greedy
```

该 run 于 2026-09-14 完成 12 个 jobs；collector 的 10 个 registry cells 为
8 `COMPLETED`、1 `UNSUPPORTED`、1 `BLOCKED`。这只是工程连通性证据；真实 D
external runner 位于 `scripts/experiments/D-EXTERNAL-RC0-20260914/rc0.py`，
不由这个 synthetic profile 偷换为已完成的外部科学评价。

## 4. 完整方法 × 任务 × 成本矩阵

### 方法角色

| 方法 | 输入/角色 | 适用定位 | CPU/GPU 成本 cell | 当前证据状态 |
|---|---|---|---|---|
| raw RepeatMasker + frozen library | library-guided；固定 Dfam/RepeatMasker library | 必要 baseline，报告碎片和材料覆盖 | CPU；同 FASTA、同 callable bp | 已有历史/局部资产；同一最终实例仍需统一重包 |
| 当前 D | FASTA-only direct GLM material/segment output | candidate model；不称 library discovery | CPU 与 GPU 各一格；固定 model/calibration | 入口存在；与传统完整 workflow 的同输入比较未完成 |
| HiTE 3.3.3 | de novo + structural/homology annotation | 外部 de novo comparator | CPU；GPU `UNSUPPORTED` | FlyBase T1 有有效历史 cell；其余 profile 需统一重跑 |
| RepeatModeler2 2.0.9 + RepeatMasker 4.2.4 | de novo library discovery → library-guided masking | 独立传统端到端 workflow | CPU；GPU `UNSUPPORTED` | runtime/version 资产有记录；同输入科学 cell 待完成 |
| EDTA 2.3.0 | de novo library + annotation | plant primary；animal 仅 conditional | CPU；GPU `UNSUPPORTED` | Rice/部分历史结果存在；不能与当前 D 直接混为全矩阵 |
| EarlGrey 7.3.0 | de novo RepeatModeler/BEAT/RepeatMasker workflow | broad eukaryote comparator | CPU；GPU `UNSUPPORTED` | 有部分物种工程/历史结果；最终同实例 cell 待冻结 |
| TEtrimmer 1.7.4 | candidate/library-guided consensus curation | library/seed curation；不是独立 whole-genome discovery | CPU；GPU `UNSUPPORTED` | 版本/runtime provenance 仍需按最终 cell 固定 |

`RM2+RM` 是一个端到端方法 cell；不得把 RM2 library discovery 的中间 library 与其他方法的 library 混用。TEtrimmer 只有在候选 library/seed 输入存在时才计为 applicable；unsupported 应保留状态而非伪造零指标。

### 任务合同

| 任务 | 真实含义 | 可计算指标 | 不能计算/不能宣称 |
|---|---|---|---|
| T0 | controlled complete truth；当前仅 toy full-truth | bp/segment precision、recall、F1；boundary；fragment/fusion/topology；calibration | toy 不代表 biological truth；real T0 尚未冻结 |
| T1 | curated/reference positive subset（如 FlyBase/Rice） | positive bp/segment recall、boundary recall、fragmentation/split/missed、ontology-conditioned recall | unlabelled genome 不是 negative；whole-genome precision/F1、FP/TN 不可报 |
| T2 | partial/unknown/revision diagnostic | coverage、cross-release concordance、independent evidence overlap、candidate counts、qualitative cases | absolute accuracy、precision/F1、模型 confidence universalization |
| Cost | 与 T0/T1/T2 正交的可用性任务 | CPU/GPU walltime、callable bp/s、RSS/VRAM、cold/warm、线程/型号、失败/超时状态 | 用 8,206 bp smoke 外推整基因组耗时；把 inference cost 与 de novo+annotation cost 混为一项 |

### Cell matrix

| 方法 | T0 toy | T1 positive-only | T2 diagnostic/revision | Cost |
|---|---|---|---|---|
| raw RepeatMasker | `APPLICABLE` engineering | `APPLICABLE` recall/fragmentation | `APPLICABLE` concordance | CPU |
| 当前 D | `APPLICABLE` engineering | `APPLICABLE`（需当前 D 同输入） | `APPLICABLE` candidate/revision support | CPU + GPU |
| HiTE | `APPLICABLE` adapter schema only | `APPLICABLE`，优先 FlyBase | `APPLICABLE` evidence | CPU |
| RM2+RM | `APPLICABLE` adapter schema only | `APPLICABLE` after same input/runtime freeze | `APPLICABLE` library/revision | CPU |
| EDTA | `APPLICABLE` adapter schema only | `PLANT_PRIMARY`；animal `CONDITIONAL` | `APPLICABLE` plant/selected species | CPU |
| EarlGrey | `APPLICABLE` adapter schema only | `APPLICABLE` after same input freeze | `APPLICABLE` | CPU |
| TEtrimmer | `CONDITIONAL`（需要 seed/library） | `CONDITIONAL`（不作 standalone caller） | `APPLICABLE` curation/retrieval | CPU |

T0/T1/T2 同一方法仍使用同一 query genome 和版本化 input；只有 truth view 与 metric contract 改变。每个 cell 的 failure/unsupported status 进入 denominator，metric JSON 对不适用 tier 写 `null` 并写明原因。

## 5. 公平性与输出 schema

### 统一 input/output

- 同一 assembly、同一 callable contig/bp、同一 FASTA 版本；方法不得看到评估 truth；
- raw output 保留在该 cell 目录，另写一个 canonical prediction TSV 供 adapter 使用；原始 family、strand、source row 和 topology/group ID 另存 metadata；
- 预测与 truth 统一 zero-based half-open；GFF 1-based inclusive 和 RepeatMasker `.out` 的转换只能发生在 adapter wrapper；
- `metrics.json` 至少包含 `method`、`task`、`status`、`truth_tier`、`input_id`、`evaluator_version/path`、`coordinates`、`claim_scope`、`metrics`、`failure_reason`；T1/T2 不填虚假 precision/F1；
- 同一 cell 的 `performance.txt` 只作为执行成本证据，不能替代 method output schema validation。

### 失败分母

`expected_cells = registry 行数`，`completed_cells` 只统计 output 和 schema 都通过的行。`FAILED`、`TIMEOUT`、`UNSUPPORTED`、`INVALID_INPUT`、`BLOCKED` 分别保留，并在 summary 同时报告 `expected/completed/failed/unsupported`。当 native 工具返回非零时，launcher 应写 status sidecar 并保留 stderr；若上游失败阻止 Omni collector，沿用 registry + `.logs` 做 post-run 状态汇总。禁止用“无 score 文件”直接删除 cell。

### 不混淆的比较层

1. **library-guided：** fixed RM、RM2+RM 的最终 RM step、TEtrimmer 的 seed/candidate curation；
2. **de novo+annotate：** HiTE、RM2+RM 全流程、EDTA、EarlGrey；
3. **model direct：** 当前 D；它不因输出 family-like score 就自动等于 de novo library discovery；
4. **annotation vs retrieval：** candidate/family retrieval、interval annotation、boundary、fragment/insertion topology 分开写，不能用 retrieval hit 替代正确边界或 biological instance recovery。

## 6. CPU/GPU 成本实验的最小公平口径

成本测试只在当前 D 已有适配器和至少一个合格传统完整 workflow 后执行。固定 input、callable bp、输出 contract、thread count 和结果写盘规则；分别记录：

- raw inference walltime 与 callable bp/s；
- de novo library construction + annotation 的分阶段 walltime 与端到端 walltime；
- CPU 型号/cores/RSS，GPU 型号/显存/VRAM；
- cold cache 与 warm cache，超时和失败状态；
- `performance.txt`、launcher status、stdout/stderr 和最终 output schema。

当前 D 的 CPU cell 要由 wrapper 原样传递现有 `infer_fasta.py --cpu` 开关；GPU cell 只使用同一冻结模型/校准，不在 cost run 中调 threshold。传统工具没有 GPU 需求时记 `UNSUPPORTED`，不拿 CPU 时间和缺失 GPU 时间比较。

## 7. 后续实施顺序与停止条件

1. **工程准备：** 已在现有 `ab-initio-TE` 增加一个小 benchmark 目录和根级 named `default`/`rc0` 入口；两份 plan 的 `ob validate plan` 和实际 host run 均通过（macOS arm64 运行 RC0 时需 `--scheduler greedy`）。第一阶段只调用现有 converter/evaluator 和 synthetic source fixture，不创建外部方法的空 wrapper；后续失败仍只修 schema/bridge，不改旧评分器。
2. **toy full-truth：** 已验收 canonical conversion、T0/T1 输出、collector 和 status denominator；T2 只另行做 schema 检查，终态只能写 `ENGINEERING_ONLY`。
3. **同输入外部矩阵：** 下一阶段再选择当前 D + 已有 HiTE + RM2+RM 一个完整传统 workflow，在同一 FlyBase/Rice profile 冻结 input/runtime/truth tier；EDTA/EarlGrey/TEtrimmer 按适用性加入。
4. **T1/T2 解释：** T1 只报 positive recovery；T2 用于 cross-release/independent evidence 候选支持，不把 label revision 直接当 gold truth。human hg19→hg38→hs1 的 rescue 仍需 unique mapping、序列存在和独立 annotation。
5. **成本矩阵：** 仅当同一输入质量比较可解释时补 CPU/GPU throughput；小 smoke 不外推全基因组。

停止条件：真实 T0 未冻结则停止 whole-genome precision/F1；方法 runtime 或 input provenance 不一致则该 cell `BLOCKED`；T1/T2 缺 negative/complete instance identity 则停止 corresponding claim；Omni topology/collector 无法保留失败分母则先做离线 status aggregation，不绕过失败。

## 8. 关键来源与本地证据入口

- OmniBenchmark 0.6.0 package metadata：`manuscript-review-20260914/omnibenchmark-venv/lib/python3.12/site-packages/omnibenchmark-0.6.0.dist-info/METADATA`；官方文档：[tutorial](https://docs.omnibenchmark.org/latest/tutorial/)、[CLI reference](https://docs.omnibenchmark.org/latest/reference/)。
- Model schema：`omnibenchmark/model/benchmark.py`（Repository、Parameter、Resources、SoftwareEnvironment、Module、MetricCollector、Stage、Benchmark）。
- Named entrypoints：`omnibenchmark/backend/resolver.py` 的 `_read_entrypoint`；所有 declared entrypoints 会被 resolver 尝试设为 executable。
- Snakefile command/resource/performance：`omnibenchmark/backend/snakemake.py` 的 `SnakemakeGenerator`。
- Existing canonical converter/evaluator：`scripts/experiments/LEMMI-TE-BENCH-20260824-R1/adapter.py`；现有 T1 合同：[LEMMI-TE-BENCH-20260824-R1.md](LEMMI-TE-BENCH-20260824-R1.md)。
- Existing sequence-only inference：`scripts/experiments/CROSS-SPECIES-L1-FASTA-INFERENCE-V1/infer_fasta.py`。
- Truth tiers：[BENCHMARK_DATA_FREEZE_V0_2_20260808.md](../BENCHMARK_DATA_FREEZE_V0_2_20260808.md)；评估边界：[19_evaluator_contract.md](../19_evaluator_contract.md)。
- 方法版本/角色：[02_sota_model_inventory.md](../02_sota_model_inventory.md)；现有有限比较：[DIRECT-ANNOTATION-CLOSURE-20260824.md](DIRECT-ANNOTATION-CLOSURE-20260824.md)。

**本方案不代表 OmniBenchmark 已接入或任何方法已完成公平比较；它只把接入面、任务合同、适用角色、成本读数和失败分母先固定下来。**
