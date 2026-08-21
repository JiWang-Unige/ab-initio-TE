---
name: code-review-gate
description: "B1.5· Mandatory read-only pre-submit code review gate after /implement and before /smart-sbatch/full training."
---
> Codex/Antigravity note: this generated skill is mirrored from the Claude skill. When the body mentions a `/skill-name` command, Codex users should invoke `$skill-name`; Claude users keep `/skill-name`.


# Code-Review-Gate: 实现后、提交前的独立审查

本 skill 把“写完代码就跑，跑完才发现 evaluator/label/split 写错”的问题前移。它位于 `/implement` 之后、`/smart-sbatch` 或真实训练提交之前。CRITICAL blocker 未修完，不能提交 full/scale/screen 训练。

## Step 0 · 用户可读摘要

先用通俗语言说明：

```markdown
这一步不是看代码风格，而是防止结果作废。
我们要确认：标签没用错、split 没泄漏、metric 和 SOTA 可比、输出能被 validate_goal 读取、训练不会覆盖别的 run。
```

## Step 1 · 收集审查包

对每个 `exp_id` 收集：
- 实现计划或 `docs/03` path 描述。
- 变更文件列表（训练脚本、模型、数据加载、评估器、配置、job 脚本）。
- `configs/<exp_id>.yaml`
- evaluator 入口与 metrics JSON schema。
- `docs/19_evaluator_contract.md`
- `docs/20_baseline_reproduction.md`
- `docs/03_benchmark_roadmap.md` comparability contract。
- `docs/09_decisions_log.md` cousin list。
- `docs/05_todo.md` run tracker，避免输出路径冲突。

## Step 1.5 · 构建 pre-submit pack（喂给独立 reviewer，自足）
把 Step 1 收集物整理成一份**自足的审查包** `/tmp/pre_submit_<exp_id>.md`，让 reviewer 不必再爬全仓即可判断：
- 变更文件**清单 + 内容/diff**（训练/模型/数据加载/evaluator/config/job 脚本）；
- `docs/19` primary metric/split/schema 合约（**逐条**，供比对）；`docs/20` 已核实 baseline 事实；
- `configs/<exp_id>.yaml`、evaluator 入口 + metrics JSON 期望 schema；
- `docs/05` run tracker（防输出路径冲突）。

## Step 2 · 选择 reviewer 路径（**独立性分级**——codex-only 也要做到尽量独立）
> 现实：本项目后续可能**只剩 Codex 一个 CLI**（agy 不稳、claude 可能停订阅）。所以默认不依赖"换个模型来审"，而是用**独立进程 + 新鲜上下文 + 对抗视角**把 Codex 自审做硬。按可得性择优，**并在产物里如实记 `independence` 级别**：

1. **`external_cli`（最强，可得才用）**：另一个模型的 CLI 当审稿（claude `-p --append-system-prompt` 中立 / agy）。跨模型、盲点不共享。**不是必须**。
2. **`separate_codex`（默认·codex-only 推荐）**：**新开一个 `codex exec --sandbox read-only --skip-git-repo-check - < /tmp/pre_submit_<exp_id>.md` 进程**当 reviewer——它**只看 pre-submit pack + 对抗 checklist，看不到作者那次实现的推理上下文**，所以是"新鲜上下文 + 独立进程"，能避开同一会话里"自己给自己找理由"的合理化。Claude 壳等价物 = read-only `code-plan-reviewer` subagent（fork 新鲜上下文）。**对抗指令**喂给它：「你是对抗性审稿人，**默认作者写错了**，专挑 label/split/metric/output schema/path 会让结果作废的 bug；不确定按 BLOCKED」。
3. **`host_self`（最弱·兜底）**：主 agent 在**同一上下文**切 reviewer 视角自查（盲点共享、易合理化）。仅当无法另起进程时用；`pre_submit_gate.py` 会对 full/scale 的 host_self **告警**。

> 关键不是"谁的模型"，而是 **②的"独立进程+新鲜上下文+对抗视角"**——这才是 codex-only 下把"自己审自己"从作秀变成真审的办法。≥2 候选/claim 时优先 ①或②，别用 ③。

Reviewer 输出必须**同时**写两处：人读的 `docs/21_code_review_log.md` + 机器读的 `outputs/<exp_id>/code_review_gate.json`（见 Step 4），后者是 `pre_submit_gate.py` / `submit_guard` 的硬闸依据。

## Step 3 · 审查清单（HARD）

| Category | Blocker 条件 |
|---|---|
| Label / ground truth | 标签列、正负类定义、mask、padding 或 token/window 对齐不明或疑似错 |
| Metric / evaluator | primary metric 名称、average、阈值、粒度、方向与 SOTA/evaluator contract 不一致 |
| Split / leakage | train/val/test 边界、同源/染色体/物种分组、preprocessing fit-on-train 不可证明 |
| Dataset/version | 数据版本、hash、预处理、外部权重 revision 未钉死但要比较 |
| Output schema | `reports/<exp_id>.json` 不含 `primary_metric` 或 validate_goal 无法解析 |
| Path conflict | 写入共享 `runs/outputs/reports/logs`，可能覆盖已有/运行中 run |
| Reproducibility | seed/config/git state/commit or no-git state 未记录，无法复现 |
| Runtime sanity | GPU 数、worker、checkpoint、resume、walltime 与代码假设冲突 |

**强制项（HARD，G12）· evaluator 代码 vs `docs/19` 逐行比对**：`check_data.py` 只盖 split/ID 泄漏，但 metric 的 **averaging（macro/micro/weighted）、阈值、mask、粒度、方向**这些"代码里写的"是否与 `docs/19_evaluator_contract.md §1` 声明的一致，必须**逐行核对 eval 代码并列出证据**（哪行实现了哪个口径）。任一不一致（如 docs/19 写 weighted 而 `eval.py` 硬编码 macro）→ **BLOCKED**：结果会"能跑出数但不可比"，是最隐蔽的作废源。

## Step 4 · 修复与复审

输出：

```markdown
## Code Review Gate: <exp_id>
- Reviewer mode:
- Scope:
- Verdict: PASS / PASS_WITH_WARNINGS / BLOCKED

### Blockers
- [ ] <file:line> <why invalidates result>

### Warnings
- ...

### Confirmed OK
- ...

### Required fixes before submit
- ...
```

主 agent 修复 blocker 后必须复审，直到：
- `Verdict: PASS` 或 `PASS_WITH_WARNINGS`
- 所有 blocker 勾选完成
- 复审记录追加到 `docs/21_code_review_log.md`

**机器闸产物（HARD，不可省）**：复审定案后写 `outputs/<exp_id>/code_review_gate.json`，供 `pre_submit_gate.py` / `submit_guard` 做硬拦截：
```json
{
  "exp_id": "<exp_id>",
  "verdict": "PASS | PASS_WITH_WARNINGS | BLOCKED",
  "reviewer_backend": "codex(separate) | claude | agy | host",
  "independence": "external_cli | separate_codex | host_self",
  "profile": "smoke | screen | full | scale",
  "reviewed_files": {"<rel/path.py>": "<sha256>", "...": "..."},
  "blockers_open": 0,
  "timestamp": "<date>"
}
```
- `reviewed_files` 必须填**本次实际审过的文件 + 其 sha256**——这样审完再改代码（"审 v1 交 v2"）会被 `pre_submit_gate` 判**过期**拦下（hash 不符）。可用 `sha256sum <files>` 生成。
- `independence` 如实填（别把 host_self 写成 separate_codex 骗闸）。

## Step 5 · 交接给 `/smart-sbatch`

通过后，在对话内给出：
- 审查结论。
- 剩余 warning 是否影响 claim。
- 允许提交的 exp_id/profile。
- metrics/evaluator contract 路径。

并把 evidence 经 `/note-gate` 登记到 `docs/15`（type=`artifact_path` 或 `discussion_decision`）。

## 边界

- 不替代 `/implement` 的自审、`check_data.py`、smoke；它是额外独立门。
- 不替代实验后的 `/tri-review`；tri-review 仍在结果后判断科学结论。
- 不为了赶进度跳过 blocker；若用户强行 waive，必须在 `docs/21` 写 `WAIVED_BY_USER` 和风险。
- 不让 reviewer 修改文件；主 agent 修。

## Handoff

- **Inputs from**: `/implement`、`docs/03`、`docs/19`、`docs/20`、`configs/<exp_id>.yaml`、训练/eval/job 脚本。
- **Uses**: read-only `code-plan-reviewer` subagent when available; otherwise host read-only checklist.
- **Outputs to**: `docs/21_code_review_log.md`、`docs/15_evidence_register.md`。
- **Next**: `/smart-sbatch` only after PASS/PASS_WITH_WARNINGS。
