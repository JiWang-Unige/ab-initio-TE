---
name: result-log
description: "B3· Fill a structured experiment result entry after training/eval completes, starting with semantic-success validation (metrics file exists, parseable, finite, sane, loss trend reasonable) before recording metrics, SOTA gap, failure modes, and recommended next action. Exit code 0 alone is never accepted as success. Use after training finishes, before /tri-review."
argument-hint: "<experiment_id, logs/metrics paths, SOTA target>"
---

# Result Log

把 `$ARGUMENTS` 的实验结果固化到 `docs/06_results_log.md`。**前置: 必须先过 semantic success 验证**。

## Step 0 · Semantic success(不能跳)

| Check | Pass? | Evidence |
|---|---|---|
| metrics file exists | ✅/❌ | path |
| metrics file parseable as JSON | ✅/❌ | first 3 keys |
| primary metric key present | ✅/❌ | key name |
| primary metric value finite | ✅/❌ | value |
| value within sane range (not 0.0, not 1.0, not exactly constant) | ✅/❌ | distribution check |
| loss shows meaningful downward trend or expected pattern for this objective | ✅/❌ | first / mid / last epoch loss; warmup / curriculum / multi-task losses don't need strict monotonic |
| no CUDA OOM / NaN / inf in last 10% of training | ✅/❌ | grep results |
| checkpoint file exists and loadable | ✅/❌ | path + size |

Note: warmup / curriculum / multi-task / mixed-precision curves often non-monotonic. Only flag as failure if loss is flat or rising **in the final segment**, or becomes NaN / inf.

任何 ❌ → 不要继续,先 debug。常见排查表见 v2.1 老 skill,这里精简到:

| Symptom | Likely cause | Quick check |
|---|---|---|
| metric = 0.0 exactly | label/pred 都 0 | class balance |
| metric = 1.0 exactly | leakage / metric bug | split overlap |
| metric NaN | numerical overflow / loss NaN | loss curve |
| metric 比 SOTA 高 0.1+ | leakage | split + metric impl |
| loss flat at start | lr 太高 / 数据问题 | first 100 step loss |

## 输出格式(append to docs/06_results_log.md)

```markdown
## Result: <exp_id>

### Meta
- Date (UTC):
- Resource profile: <smoke / screen / full / scale>
- Claim eligibility: <can / cannot claim SOTA from this profile>
- Git commit / branch:
- Code review gate: <docs/21 entry / not required / WAIVED_BY_USER>
- Evaluator contract: <docs/19 status + version/date>

### Dataset / split
- Dataset + version:
- Split scheme:
- Sizes: train= val= test=

### Config
- Architecture (one-line):
- Key hyperparams: lr= bs= epochs= seed=
- Full config path:

### Paths
- Log:
- Checkpoint:
- Metrics:
- Predictions:
- Meta:

### Command

\`\`\`bash
<command>
\`\`\`

### Semantic success
- All 8 checks passed: ✅/❌
- Failed (if any):

### Metrics

| Metric | Value | SOTA | Gap | Direction | Strict exceedance? |
|---|---:|---:|---:|---|---|

### Loss curve
- First epoch loss:
- Mid epoch loss:
- Last epoch loss:
- Pattern: <smooth decreasing / warmup then descent / curriculum / multi-task — describe>

### Gates check
- primary_progress_gate: pass / fail
- sota_claim_gate (strict >): pass / fail
- review_decision_gate triggered? yes / no

### Comparability audit
- Required (claiming SOTA)? yes / no
- Done? yes / no / pending
- Verdict: ✅ comparable / ❌ blocked / 🟡 conditional
- Evaluator contract checked? yes / no / pending
- Baseline reproduction evidence: docs/20 / waived / absent

### Interpretation
<3-5 sentences>

### What worked / What failed
- ...

### Is tuning justified?
- ✅ gap < 0.02 and looks optimization-related
- ❌ gap ≥ 0.05 → architecture change needed
- 🟡 unknown → sanity check first

### Recommended next action
- One of: /tri-review, /pivot, /comparability check (inline), scale to full, abandon

### TODO update
- [ ] update docs/05_todo.md with: ...
```

## Multi-doc linked update (MANDATORY)

`/result-log` 写完 `docs/06_results_log.md` 主条目后，必须**同一轮内**完成下列联动更新。任一遗漏视为 result-log 未完成。

### 1. Append ITER entry to `docs/04_experiment_iterations.md`

按 docs/04 的 ITER-N 模板写一行 / 一块，至少包含:

- exp_id / Track / Path / Milestone
- Execution mode (run-and-evaluate / submit-and-handoff)
- Hypothesis (one line: 这次想测什么结构性问题)
- Architecture change (具体 head/backbone/objective/data_view 的 mechanism_delta)
- Sbatch + run status (job_id, partition, walltime used)
- Result summary (primary metric value + gap)
- Tri-review consensus (pending / consensus / disagreement; 完成后回填)
- Pivot decision (pending / 具体决策; 完成后回填)
- Links: docs/06 entry, sbatch script, output_dir

如果是 submit-and-handoff 模式，把 Result / Tri-review / Pivot 段标 `pending: result-processing goal`，等结果出来再回填。

### 2. Update relevant items in `docs/05_todo.md`

- 勾选已完成的 TODO 项（实验完成 / 已 evaluate / 已 result-log）。
- 添加 follow-up TODO，例如:
  - `[ ] /tri-review for <exp_id>` (若 result-log 推荐 review)
  - `[ ] /pivot for <exp_id>` (在 tri-review 完成后)
  - `[ ] comparability check for <exp_id>` (若 result-log 标 pending)
  - `[ ] retrospective if 5 iterations since last` (触发条件检查)
- 若实验失败 / 异常，添加 debug TODO 并写 evidence 路径。

### 3. Update top of `docs/00_active_goal.md`

在文件顶部 `## last_result_summary` 段（不存在则创建）写:

```markdown
## last_result_summary
- exp_id: <id>
- date: <YYYY-MM-DD UTC>
- track: <Track A screen | Track B scale-up | baseline | generalization>
- primary_metric: <name = value>
- SOTA: <value>
- gap: <signed value, "+" means we exceeded>
- semantic_success: <pass / fail>
- tri_review_status: <pending / completed: consensus|disagreement|degraded>
- pivot_status: <pending / completed: continue|tune|scale|replace_component|change_backbone|change_objective|abandon|literature|sanity_check>
- recommended_next: <one of: /tri-review, /pivot, /comparability check, /generalization, /retrospective, abandon route>
```

### 3.5 Distill findings to `docs/10_findings.md`

提炼本轮值得跨会话记住的发现（**不写流水账**，只写有迁移价值的）：
- **Research Finding**（若有）：方法层洞察，影响 /pivot（如"CRF 在 5% 数据无显著增益"）。
- **Engineering Finding**（若有）：调试/环境经验，下一轮 /implement 复用（如"8192 长序列需 grad checkpoint 否则 OOM"）。
一行一条，带 `<date> <exp_id>`。无新发现可不写。

### 3.6 Update Run tracker in `docs/05_todo.md`

把本 run 在 `## Run tracker` 表的状态更新为 DONE/FAILED，补 metrics path。

### 4. DO NOT write `docs/09_decisions_log.md`

`docs/09` 只在 `/pivot` 决定 **abandon route**（整条 path 放弃，不只是本次 iteration 失败）后才写。`/result-log` 永远不直接 touch docs/09。这是 anti-repeat 纪律。

### 5. DO NOT write `docs/03_benchmark_roadmap.md`

roadmap 改动属于 segment A，必须用户参与，不由 result-log 触发。

---

## Gap-based decision (must follow)

| Gap (abs, higher-is-better) | Default next |
|---|---|
| Gap ≥ 0.1 or rel > 20% | /tri-review,默认 replacement |
| 0.05 ≤ Gap < 0.1 | /tri-review,默认 architecture change |
| 0.02 ≤ Gap < 0.05 | /tri-review,可能 tweak / careful tune |
| Gap < 0.02,未严格超越 | /tri-review (review_decision_gate) |
| 严格超越 | comparability check inline,通过后可 claim |
| 异常高(SOTA + 0.1+) | leakage suspect,先 inline data contract checklist |
| screen 档结果好于 SOTA | 安排 full 档复跑,不能 claim |

## Don'ts

- Exit code = 0 不等于成功
- 不要在 ❌ semantic check 后填 Metrics 表（先 debug）
- Gap ≥ 0.05 时不要写"只是参数没调好"
- screen 档不能 claim,在 entry 顶部明说

## Hand-off

- **Inputs from**: 训练完成后的 outputs/<exp_id>/
- **Outputs to (mandatory)**:
  1. `docs/06_results_log.md` (append main entry)
  2. `docs/04_experiment_iterations.md` (append ITER entry, fields per "Multi-doc linked update" section)
  3. `docs/05_todo.md` (mark completed, add follow-up: /tri-review, /pivot, retrospective trigger check)
  4. `docs/00_active_goal.md` (top `## last_result_summary` block)
  5. `docs/15_evidence_register.md` via `/note-gate`
  6. `docs/11_master_plan.md` if current step/decision changed
  7. `docs/19_evaluator_contract.md` / `docs/21_code_review_log.md` references if evaluator or code-review status affects claim eligibility
- **Do NOT touch**: `docs/03_benchmark_roadmap.md`, `docs/09_decisions_log.md`
- **Next skill**: `/tri-review` then `/pivot`. If retrospective trigger fires (≥5 ITER since last retro, or same-path 3-no-progress, or Track-B fail ×2), additionally recommend `/retrospective`.
