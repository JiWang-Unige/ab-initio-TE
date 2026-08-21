# Workflow Simplification Audit — 2026-08-13

## Verdict

当前项目已不适合继续作为日常执行工作区。它已冻结为历史证据仓；新的 `Publication-Validation lite` 项目已创建，只承载用户明确指定的少数补充结果。当前未删除、未移动旧项目中的任何研究资产。

## Backup

- 控制面冻结包：`../ab-initio-TE-archive/ab-initio-TE-control-plane-freeze-20260813T174101.tar.gz`
- 范围：hooks、skills、入口文件、docs、scripts、configs、sbatch、pipelines、wiki、handoffs。
- 明确排除：`reports/`、`outputs/`、`data/`、`software_outputs/`、缓存、临时目录与 secrets。
- SHA-256：`4b9073fa34b24a23515dc5bedc146fc1bf3897c9e6cedc06d3fa2e5f0f88ecc4`
- 抽取恢复 smoke：PASS（`AGENTS.md`、hooks、`docs/03`、`context_pack.py`）。

## Why not delete `docs/03` in place

`docs/03_benchmark_roadmap.md` 被 `pursue`、`implement`、`goal-prompt`、`code-review-gate`、`generalization` 等旧技能硬编码引用。单独删除会产生隐蔽断链，却不会真正减少旧框架复杂度。因此它与 `docs/00-24` 一起保留为历史材料，但不迁入新项目的活动上下文。

## Reclassification

| Existing element | Decision for new project |
|---|---|
| Discovery / Track A-B / `$pursue` 自循环 | suspend；默认不迁入 |
| 每个 run 的 result-log → validate → tri-review → pivot 全链 | downgrade；只用于 claim-bearing 或路线改变的里程碑 |
| `docs/03/04/05/07/08/15/21/24` 全量历史 | legacy-only；不复制全文 |
| `docs/11` 主张与当前状态 | extract 到一页 `PROJECT.md` |
| `docs/19_evaluator_contract.md` | 提炼到 `EVALUATION.md`，保留 split/metric/claim 可比性硬约束 |
| `docs/06_results_log.md` | 只抽取被接受、仍与补充结果有关的 evidence rows 到 `RESULTS.md` |
| `docs/09_decisions_log.md` | 只抽取不得重试的路线到 `DECISIONS.md` |
| 数据、checkpoints、reports、software outputs、refs | 留在旧项目；新项目使用明确路径索引，不整库复制 |
| hooks | 默认关闭；最多保留静默路径保护、精简 Slurm/覆盖保护、可选 PreCompact |

## Proposed minimal project

已创建于 `../ab-initio-TE-publication-lite/`；当前无项目级 hooks。

```text
<new-project>/
├── AGENTS.md          # <= 12–16 KB：HERO、科研硬约束、执行优先、长任务等待
├── PROJECT.md         # 一句话主张、当前模型/数据、旧项目路径
├── TASKS.md           # 仅 3–5 个用户指定补充结果
├── EVALUATION.md      # split / metric / comparator / claim contract
├── RESULTS.md         # 已接受结果索引，不复制长日志
├── DECISIONS.md       # 仍有效的 stop/no-retry 结论
├── scripts/           # 仅活动任务真正调用的脚本
├── configs/
├── sbatch/
├── reports/
└── outputs/
```

不创建编号式 `docs/00-24`，不安装完整 auto-research 架构，不自动生成 master-plan、todo、tri-review、pivot 或 evidence ledger。

## Human gate

新项目目录与相对存储策略已获用户确认。开始迁移活动代码和执行结果之前，仍需确认：

1. 按优先级排列的 3–5 个待补结果；
2. 哪些旧模型/checkpoint/report 是这些结果的输入。

收到确认后，只复制活动代码和配置；任何大数据/结果移动或旧项目删除需另行批准。
