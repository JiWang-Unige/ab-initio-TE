---
exp_id: FRAG-EVIDENCE-REGISTRY-20260811-R2
date: 2026-08-11
approach_family: evidence-registry
parent_exp: FRAG-PARENT-LATTICE-SCREEN-20260811-R1
motivated_by: "Close F identity/truth/comparator gates without reviving DEC-001/002"
track: publication-validation-support
profile: smoke
status: done
primary_metric: integrity_check_count_passed
value: 6
vs_anchor: "6/6 integrity checks; scientific gate remains blocked"
one_liner: "H0/truth/comparator audit closed; accepted postprocessor and lattice remain typed blockers"
---

# FRAG-EVIDENCE-REGISTRY-20260811-R2

- 当前状态：正式 CPU asset audit 已完成，终态 `FOUNDATIONAL_TYPED_BLOCK`。
- Job `11521393` 在 payload 前 1 秒失败；独立复审后的环境修复由 retry Job `11521479` 验证，后者 `COMPLETED 0:0`、14 秒、0 GPU。
- 本轮未运行 H0 inference、biological screen 或 scientific lattice；结果不可用于方法性能或 claim。

## 独立 review 修复

1. HMM2 只登记为 `historical_fixed_comparator`，`accepted=false`。当前没有真实 current accepted postprocessor，因此固定 blocker 为 `ACCEPTED_POSTPROCESSOR_UNFROZEN`，count=0。
2. `merge_typed_parents` 只是 MERGE_STRICT/MERGE_LOOSE comparator projection，不是 scientific lattice，也不是 re-entry implementation。scientific lattice 固定 blocker 为 `SCIENTIFIC_LATTICE_UNIMPLEMENTED`，count=0。
3. 补齐 same-input window semantics：RAW/HMM2 使用 `CONTIG_MEAN_FULL_V1`，CENTER70 使用 `CONTIG_MEAN_CENTER70_V1`（4096 window 的 `[615,3481)`），再由 `SOURCE_LEAF_RUNS_V1` 生成稳定 source leaves。overlap aggregation、source leaf、HMM2、MERGE 与 leaf retention 共 8 个 probes 均通过静态检查。
4. 正式 entrypoint 区分两类结局：资产/哈希/环境/真值/probe 都完整时，预期得到 `FOUNDATIONAL_TYPED_BLOCK`、`semantic_success=true`、exit 0；任何 integrity mismatch 得到 `INVALID_ASSET_INTEGRITY`、`semantic_success=false`、exit 2。
5. 登录节点 PREVIEW 已被正式 allocation 产物替换；正式 `metrics.json` 为 `semantic_success=true` 的预期 typed-block，且 `scientific_screen_executed=false`。
6. `command_manifest.tsv` 纳入 config、builder、semantics、sbatch、continuation protocol 与 `docs/19_evaluator_contract.md`；工作区显式记录 `NO_GIT_METADATA`。正式 entrypoint 会重建 input/command/output manifests。
7. sbatch 显式 `conda activate benchmark_core`，并原子记录 `env.txt`、Python/Conda 路径和版本。
8. `h0_directory_inventory.tsv` 在 PREVIEW 中只列文件名/bytes/`NOT_RUN_PREVIEW`；正式 entrypoint 使用 `FRAG_R2_DIR_INVENTORY_V1` 重算每文件 SHA-256 与聚合摘要。
9. T1 registry 仅界定 positive-only diagnostic evidence，绝不构成 scientific screen 授权。
10. 正式非 `--static-check` 路径在任何 `RUNNING`/结果写入前强制要求非空 `SLURM_JOB_ID`；登录节点直接调用返回 rc=2，且不改写 PREVIEW。
11. formal `metrics.json` 顶层包含 `integrity_check_count_passed=6`，由实际 `integrity_checks` 中 true 的数量动态求和；同值也保留在 nested `metrics`。

## Truth/metric 边界

- T0：只有 controlled synthetic complete truth，不能作 biological claim。
- T1：FlyBase curated positives 与 Rice reference-positive segments；`unlabeled_space_is_negative=false`。
- T2：空；real T0：空。
- T1-only 若未来获批，只允许 positive recovery、matched boundary error、truth fragmentation、truth topology preservation、false-fusion proxy。
- 禁止 whole-genome precision/recall/F1、bp precision/F1、segment precision/F1。

## 状态机

| 状态 | semantic_success | exit code | 含义 |
|---|---:|---:|---|
| `IMPLEMENTED_NOT_RUN` | false | n/a | 历史 PREVIEW；已被正式 run 取代 |
| `FOUNDATIONAL_TYPED_BLOCK` | true | 0 | 审计完整且复现预期 blocker；有效负证据，不授权 screen |
| `INVALID_ASSET_INTEGRITY` | false | 2 | 哈希、环境、truth 或 probe 损坏；结果不可解释 |

无论哪种状态，`scientific_screen_authorized=false`。

## 静态测试

执行命令：

```bash
python3 scripts/experiments/FRAG-EVIDENCE-REGISTRY-20260811-R2/build_registry.py --static-check
bash -n sbatch/FRAG-EVIDENCE-REGISTRY-20260811-R2.sbatch
```

结果：提交前 `PASS_STATIC_ONLY`；8/8 semantic probes PASS；Python 与 sbatch 语法 PASS。正式 allocation 重算了 H0 inventory 与全部 manifest，未读取大模型权重、未运行研究计算。

## 正式资产复核资源

- 入口：`sbatch/FRAG-EVIDENCE-REGISTRY-20260811-R2.sbatch`。
- 请求：1 CPU、4 GB RAM、0 GPU、30 分钟。
- 路由：`private-teodoro-gpu` CPU-only（无 `--gres`）；stdout/stderr 使用独立 `%j` 文件；环境从固定 `/opt/ebsofts/Mamba/23.1.0-4` bootstrap 后激活 `benchmark_core`。
- Job `11521393` 在 payload 前因 `set -u` 干扰 MKL/Conda activation 而失败；bounded repair 将开局改为 `set -eo pipefail`，仅在 `conda activate benchmark_core` 成功后启用 `set -u`。payload 前任一步骤失败时 EXIT trap 原子写 `STATUS=FAILED_ENV` 并在 stderr 记录 rc；payload 启动后不覆盖 builder 的正式状态机。
- 实际：retry Job `11521479` 用时 14 秒；主要工作为冻结文件哈希和 H0 per-file inventory，不包含模型推理。

## 正式结果

- `integrity_check_count_passed=6/6`；13/13 正式 output-manifest 条目通过哈希复核。
- `h0_directory_pin_pass=1`、`truth_registry_pass=1`、`same_input_comparator_gate_pass=1`。
- `accepted_postprocessor_count=0`、`scientific_lattice_implementation_count=0`、`scientific_execution_performed=0`。
- route-local `validate_goal.py` 返回 `progress`，只表示资产里程碑完成；通用 tuning/scaling 建议不适用于离散资产计数。
- 结果链：`docs/06_results_log.md` 已记录；Wave-1 cohort tri-review/pivot 等待 B 与 S0 收集后统一执行。

## Remaining blockers

- `ACCEPTED_POSTPROCESSOR_UNFROZEN`：尚无独立冻结的 current accepted postprocessor。
- `SCIENTIFIC_LATTICE_UNIMPLEMENTED`：MERGE comparator 不得冒充 lattice。
- 独立 code-review 和本次 asset-audit 授权已经闭合；它们不授权下一阶段 scientific screen。
- 实际 T1 screen 还需要两套 T1 same-input H0 probability tracks 及 SHA-256。
- 若要 whole-genome precision/F1，必须新增真实 complete T0；T1 永远不能升级解释。
