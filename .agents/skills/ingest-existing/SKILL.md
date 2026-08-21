---
name: ingest-existing
description: "A0· Onboard a half-finished EXTERNAL research project into the framework."
---
> Codex/Antigravity note: this generated skill is mirrored from the Claude skill. When the body mentions a `/skill-name` command, Codex users should invoke `$skill-name`; Claude users keep `/skill-name`.


# Ingest-Existing: 把"做了一半"的研究系统梳理进框架

场景：你已经探索过一阵（有代码、跑过的结果、笔记、读过的论文，甚至半截手稿），现在想**系统迭代或投稿**，于是导入本框架。本 skill 用 **subagent 并行系统梳理**已有材料 → **汇报给你** → **一起定目标/建流程** → **回填进框架 docs**，让项目正式"进到框架里"继续推进。

**与 `/research-interview` CONTINUATION 的区别**：CONTINUATION 重新接续**已在框架内**（已有 docs/00-10）的项目；本 skill 是**冷导入**——已有材料还没进框架，要先"考古"重建再纳入。

## Step 0 · 定位已有材料（不猜，先问 + 浅扫）
- 问用户：旧工作在哪——repo/code 路径、笔记目录、结果/日志目录、旧手稿、数据位置。
- **浅扫成分区清单**（只列不深读，省上下文）：
```bash
rg --files <path> 2>/dev/null | sed 's#.*/##' | sort | uniq -c | sort -rn | head -40   # 文件类型概览
find <path> -maxdepth 2 -type d 2>/dev/null | head -40                                  # 目录结构
```
据此把材料分成 6 个分区：**代码/模型 · 结果/指标 · 笔记/思路/决策 · 数据 · 文献/refs · 旧手稿/claim**。

## Step 1 · subagent 并行系统梳理（核心 · 防主上下文爆炸）
**按分区并行派 read-only subagent**（优先使用 `.agents/agents/project-cartographer`；每个只读一类材料，**只返回结构化摘要、不返回原文**；主对话只接收摘要表）：

| 分区 | subagent 要抽取 |
|---|---|
| 代码/模型 | 试过哪些架构/方法、训练&评估脚本结构、关键超参、依赖、入口命令 |
| 结果/指标 | 已得到的数值、**最好结果**、失败的尝试 + **为什么失败** |
| 笔记/思路/决策 | 记录过的假设、**为什么做某选择**、放弃过什么 + 理由、待办 |
| 数据 | 数据集/来源/split/规模/预处理；**有无泄漏隐患**（随机 split？同源未去冗余？） |
| 文献/refs | 已收集的论文/SOTA/baseline 主张（用 `refs/archive_source.sh` 归档 PDF/repo） |
| 旧手稿/claim | 已声称的贡献、图表、对比对象（**默认未核实**） |

每个 subagent 返回固定字段：`做了什么 | 结论 | 证据路径 | 存疑/缺口`。不 spawn 嵌套 subagent。

## Step 2 · 合成"前序工作摘要"并汇报用户
host 合并各 subagent 摘要 → inline 给用户一份**结构化数字摘要**（不是文件堆）：
- **已完成探索**：架构/方法 × 结果矩阵（含最好结果 + 失败教训）；
- **已记录的关键思路/决策/放弃路线**（+ 为什么）；
- **当前真实状态**：什么能用、什么没验证、什么是猜测；
- **缺口与风险**：split 泄漏？指标口径不明？可比性？复现性？数据/代码缺失？
- **候选下一步**：继续迭代 / 投稿验证 / 流程化分析。

## Step 3 · 与用户共定目标 + 工作流模式
和用户一起确定：**研究目标**、**工作流模式**（Discovery-Iteration / Publication-Validation / Pipeline-Execution）、以及前序结论的 **carry-forward 处置**（借 `/reframe` 账本：TRANSFER 迁移 / PARK 暂存带 re-entry / ABANDON 弃用）。

## Step 4 · 回填框架 docs（人闸落盘）
把重建结果**结构化提议 diff → 用户确认才写**（绝不覆盖、未核实的不当事实写）：
- `docs/00`(意图 + 前序状态)、`docs/01`(已收集文献 → 综述骨架)、`docs/02`(已知 SOTA/baseline，标"待 /sota-inventory 实访核实")、`docs/06`(已得结果回填)、`docs/10`(已知 findings/教训)、`docs/09`(已放弃路线 + cousin)；
- `docs/11_master_plan.md §0`：初始化导航（模式 / 当前阶段 / 最终产物 / now）；
- `refs/`：归档已有论文；`ACTIVE_GOAL.json`：草案（`status: draft`，待 grill/council 后定）。
- 未核实项一律标 `⏳ 待 /reproduce-baselines | /sota-inventory 核实`。

## Step 4.5 · 目录规整提案（把乱架构对齐框架契约，人闸 · 治"乱目录"）
旧项目常是一堆散乱目录。把它**规整到框架的产物契约**（`docs/16_artifact_registry.md` / `PROJECT_STRUCTURE.md`），但**绝不就地破坏原项目**：
```bash
python3 scripts/artifact_registry.py --init          # 建标准目录骨架(scripts/configs/runs/reports/software_outputs/data/...)
```
- **提议迁移映射表**（旧路径 → 框架路径 + 动作），人闸确认才执行：

  | 旧的散乱位置（示例） | 框架契约位置 | 默认动作 |
  |---|---|---|
  | 各处 `*.py` 训练/评估脚本 | `scripts/` | copy（保留原件） |
  | 散落的 `*.yaml/*.json` 超参 | `configs/<exp_id>.yaml` | copy |
  | `checkpoints/`、`*.pt`、训练态 | `runs/<exp_id>/` | **leave-in-place + 记位置**（大文件不搬） |
  | metric/日志 | `reports/<exp_id>.json`、`logs/` | copy 摘要、原始 leave |
  | 外部软件输出（bedtools/blast…） | `software_outputs/<tool>/<run_id>/`（补 6 件套） | copy/leave |
  | PDF/repo | `refs/pdfs|repos/`（经 archive_source.sh） | archive |
  | raw data | `data/raw/`（**只读，绝不改**） | leave-in-place + 软链/记路径 |

- **安全铁律**：大文件/数据默认 **leave-in-place + 在 docs/16 记真实位置**（不搬动，除非用户明确要）；需要移动时用 **copy 或带备份**，原目录绝不就地删/覆盖；全部走人闸确认。
- 规整后 `python3 scripts/artifact_registry.py --audit-run <exp_id>` / `--audit-external <tool> <run_id>` 校验 bundle 齐全，缺项写 docs/05。

## 边界
- read-only 梳理阶段**绝不改旧项目文件**；回填框架 docs 与目录规整都走**人闸**，大文件默认不搬动。
- 旧结果/旧主张**默认未核实**——可比性/泄漏/指标口径必须经 `/sota-inventory` + `/reproduce-baselines` 重核，不能直接当事实。
- subagent 只回摘要不灌全文；不 spawn 嵌套 subagent。
- 数据分区发现疑似泄漏 → 立刻标红，进 docs/10，建议 `check_data.py` 复核。

## Hand-off
- **Inputs from**: 用户指定的外部项目材料（repo/notes/results/data/manuscript）
- **Uses**: `.agents/agents/project-cartographer` read-only survey subagents（并行）、`scripts/artifact_registry.py`（建目录骨架 + 规整审计）、`refs/archive_source.sh`（归档已有论文）、`scripts/check_data.py`（数据泄漏初查）
- **Outputs to**: `docs/00/01/02/06/09/10/11` + `refs/` + `ACTIVE_GOAL.json`(draft)（均经人闸）
- **Next**: `/grill` 或 `/council`（辩穿重建的方向）→ `/sota-inventory` + `/reproduce-baselines`（核实旧主张）→ `/configure-project`（定模式+配置）→ 对应段推进
