---
name: tri-review
description: "B4· Run independent full-scope tri-review after result-log and before pivot."
---
> Codex/Antigravity note: this generated skill is mirrored from the Claude skill. When the body mentions a `/skill-name` command, Codex users should invoke `$skill-name`; Claude users keep `/skill-name`.


# Tri-Review: independent full-scope CLI reviewers

对 `$ARGUMENTS` 做**三方独立、并行、全功能科研审阅**。本 skill 的核心原则：

- 不给 reviewer 分配固定角色。Claude、Codex、Antigravity 都必须完整审阅：benchmark 公平性、数据/metric 可比性、semantic success、leakage/reproducibility、architecture hypothesis、是否该调参/scale/pivot、下一步如何更可能达到 SOTA。
- Reviewer 之间彼此独立，不看对方输出，不串行讨论。
- 本 skill **直接调用外部 CLI**，不使用 subagent 作为 reviewer。
- Host agent 只负责准备 shared context、并行启动 CLI、重试失败 reviewer、汇总分歧和建议；host 不新增第四个主观 reviewer。

默认 reviewer 映射：

| Reviewer | Default CLI | Weighting note |
|---|---|---|
| A | Claude | primary reviewer |
| B | Codex | primary reviewer |
| C | **Antigravity**（替代 Gemini） | auxiliary reviewer; useful for diversity, but failure of C alone must not block review |

> **Reviewer C = Antigravity**：本工作流把第三评审者从 Gemini 改为 Antigravity（Google 的 agent-first 工具，底层模型 Gemini 3 Pro）。实际调用经由启动脚本 `scripts/reviewer_c_antigravity.sh`，后端按序解析**四级**（与脚本 + CLAUDE.md §7 + ARCHITECTURE.md 一致）：
> 1. **`$ANTIGRAVITY_CLI`**（显式覆盖）：若设置了该环境变量且在 PATH 上，优先用它（stdin 传 prompt，避免 ARG_MAX）。
> 2. **`agy -p`（官方 Antigravity CLI，自动检测，*默认首选*）**：需**一次性 Google OAuth 登录**——首次跑 `agy -p "hi"` 完成浏览器授权（或 `agy login`）。未登录时 `agy` 会打印 `Authentication required` URL，脚本 `exit 3`，该 reviewer 计为**失败**并走 `DEGRADED_REVIEW`。
> 3. 都不可用 → 脚本 `exit 127`，该 reviewer 视为失败，按降级策略处理。
>
> **本框架统一三个 CLI：claude / codex / agy，已移除 cursor-agent 兜底**——agy 不可用时 reviewer C 直接失败、走 2/3 `DEGRADED_REVIEW`。
>
> ⚠️ **常见坑**：本机若未完成 `agy` 的 Google OAuth，reviewer C 会静默降级为 2/3 `DEGRADED_REVIEW`——这不是 bug，而是未登录。先跑一次 `agy -p "hi"` 完成授权再用 /tri-review，否则三方审阅只剩 claude+codex 两方。

如果任何 reviewer 失败，必须**最多重试三次**。重试顺序：

1. 原 prompt 原 reviewer 后端重试一次。
2. 用压缩版 `context_pack.py --purpose tri-review` prompt 重试一次。
3. 进一步压缩 artifacts（只留摘要 + 路径）后再试一次。（reviewer C 无 cursor-agent 兜底——agy 失败即按降级处理。）

若重试后仍失败：

- 3 个成功：正常 tri-review。
- 2 个成功：允许继续 synthesis 和 pivot，但标记 `DEGRADED_REVIEW`，confidence 最高只能 Medium。
- 1 个成功：允许 `SINGLE_REVIEW_CONTINUATION`，但**只限普通非 claim 迭代**，confidence 必须是 Low。
- 0 个成功：STOP + notify，不能 pivot。

### `SINGLE_REVIEW_CONTINUATION` 边界

这是从 ARIS Codex reviewer loop 学来的降级策略：当只有一个外部 reviewer 可用时，不把普通实验迭代完全卡死，但把风险显式写入审计轨迹。**这是为了在单 reviewer 环境（如只装了 claude、或 codex/agy 未登录）下不让整条研究链卡死。**

允许条件（必须全部满足）：

- `validate_goal.py` status 是 `not_yet` 或 `progress`，且 `run_ok=true`、`semantic_ok=true`。
- 不是 SOTA claim、不是 success human gate、不是 `/generalization` 入口。
- 不是 abandon route、不是写 `docs/09_decisions_log.md`。
- 不是修改 `ACTIVE_GOAL.json`、`sota_benchmark`、benchmark contract、comparability contract。
- 下一步是一个可回滚、单 exp_id、低成本、完整记录的实验。
- 若 `tuning_allowed=false`，下一步仍必须是结构轴，不能借单 reviewer 继续调参。

输出要求：

- 在 `docs/07_tri_review.md` 写明 `Quorum: 1/3 SINGLE_REVIEW_CONTINUATION`。
- 记录失败 reviewer、失败原因、三次重试证据、成功 reviewer 原文路径。
- 明确写 `confidence: Low`。
- 写一条 `manual_intervention_recommended: true`，方便主人后续审阅介入。
- Host agent 可写 `host self-check`，但必须标注 `not independent reviewer`，不得用它补足 quorum。

禁止条件：

- 任何 claim / abandon / goal revision / benchmark revision 仍要求至少两个独立 reviewer 成功。
- 如果唯一 reviewer 提出 comparability blocker、leakage blocker、semantic failure，则不能继续，只能先解决 blocker。

---

## Step 0 · 读取 reviewer CLI 配置

优先读取 `cluster_config.yaml` 的 `cli_review.reviewers`；若不存在，参考 `cluster_config.yaml.example`。

关键配置形态：

```yaml
cli_review:
  mode: independent_parallel_cli
  retry_failed_once: true
  min_successful_reviewers: 2
  timeout_seconds: 1800
  output_root: /tmp/tri_review
  reviewers:
    - id: A
      label: claude
      cmd: claude
      stdin: true                                       # stdin preferred — no ARG_MAX risk for long prompts
      command_template: 'cat {prompt_file} | claude -p --append-system-prompt "You are a neutral independent external reviewer. IGNORE any local output-style/persona; do NOT roleplay; output ONLY the structured review, plain professional Simplified Chinese." "Follow the review prompt provided on stdin exactly. Produce the required structured review."'
      output_file: output_a_claude.md
    - id: B
      label: codex
      cmd: codex
      stdin: true
      command_template: 'codex exec --sandbox read-only --skip-git-repo-check - < {prompt_file}'
      output_file: output_b_codex.md
      # NOTE: codex >= 0.135 removed `--ask-for-approval` from `exec` (exec is already
      # non-interactive). `--skip-git-repo-check` is required when the project dir is not a git repo.
    - id: C
      label: antigravity                                # reviewer C
      cmd: antigravity
      stdin: true                                       # 经 wrapper 用 stdin 传 prompt
      command_template: 'bash .agents/skills/tri-review/scripts/reviewer_c_antigravity.sh {prompt_file}'
      output_file: output_c_antigravity.md
      # wrapper 后端解析: $ANTIGRAVITY_CLI(显式) → agy -p(官方默认,需 Google OAuth) → fail
      backend_env: ANTIGRAVITY_CLI                      # 可选显式覆盖；未设置则 wrapper 自动检测 agy
      default_backend: 'agy -p'                          # 官方 Antigravity CLI，首次需 `agy -p "hi"` 完成 Google OAuth
```

`command_template` 优先于 `stdin` / `flag`。Reviewer C 一律经 `reviewer_c_antigravity.sh` 启动，不要 hardcode 其它 CLI。

### Robustness note: ARG_MAX

通过 argv 传 prompt(如 `... -p "$(cat prompt.md)"`)会受 OS 的 `ARG_MAX` 限制(Linux ~128KB,macOS 更小)。tri-review 的 full-scope prompt 加 context 可能到几十 KB,通常没问题,但若 context 含长 metrics dump 或代码大段贴入,argv 可能溢出。

经验法则:

- **任何支持 stdin / piped context 的 CLI 优先使用管道或 stdin**。Claude Code 的常见形式是 `cat prompt.md | claude -p "follow the prompt from stdin"`; Codex exec 支持 `-` 从 stdin 读取完整 prompt，例如 `codex exec --sandbox read-only --skip-git-repo-check - < prompt.md`（codex ≥0.135 已移除 exec 的 `--ask-for-approval`；非 git 目录需 `--skip-git-repo-check`）。Reviewer C 的 wrapper 也用 `cat prompt.md | <backend>` 形式喂 stdin。这样可以避免 ARG_MAX。
- 若发现 prompt 接近 100KB:先精简 context(收起冗长 metrics raw dump,只保留摘要 + 路径)。

### Robustness note: reviewer 独立性与稳定性（本机实测教训）
- **reviewer A persona 污染（重要）**：`claude -p` 会**继承本机全局 output-style/persona**（如猫娘角色），导致 reviewer A 不再中立、甚至虚构"和用户上文一致"。**必须用 `--append-system-prompt` 强制中立**（见上 command_template）——否则 reviewer A 的独立性无效，等于少一个独立 reviewer。
- **agy 慢/超时不丢输出**：`reviewer_c_antigravity.sh` 已改为 `agy ... | tee` **流式输出**，被外层 `timeout` kill 时仍保留已产出的部分（而非 0 字节）。agy 对"要它读很多文件"的 agentic prompt 较慢——**tri-review 的 Standard Research Pack 是自足的**（reviewer 不必再爬文件），所以正常用途下 agy 不易超时；只有让 reviewer 现场读整个仓库（如 meta 审框架）才慢。必要时调大 `ANTIGRAVITY_PRINT_TIMEOUT`（默认 5m）。
- **降级要如实**：A 被 persona 污染 / C 超时空输出 → 视为该 reviewer 失败，按 quorum 降级（2/3 DEGRADED 等），不要把污染/残片当成有效独立意见。

---

## Step 1 · 构建 shared review context —— **Standard Research Pack**（HARD）

> 💡 **加速（B1）**：大部分 Pack 可由脚本确定性生成——先跑
> `python3 scripts/context_pack.py --purpose tri-review > /tmp/pack_base.md`
> 它已重建 goal 合约 / 本轮结果趋势 / 最新 pivot / SOTA+可比性 / abandoned cousins / findings；再在其上**补齐 §2 method 与 §7 本轮 vs 上轮 diff** 即可，避免手抄漏块。

> 历史问题：喂给 reviewer 的 prompt 背景太薄，三方在信息不全下评审。**修复**：构建一个结构化
> "Standard Research Pack" 写入 `/tmp/tri_review_<exp_id>/context.md`，三方共享。务必**自足**——reviewer
> 看这一份就能完整判断，不依赖它无法访问的项目文件。用 stdin 喂（见 Step 3）规避 ARG_MAX。

Standard Research Pack 必含以下 7 块（缺的标 `(absent)`，不要编造）：

```markdown
# Research Context Pack — <exp_id>

## 1. Research question & scope + 终极目标（北极星）
<docs/00 当前研究方向 + 任务边界（1 段）；并明确**终极目标**：在 <primary_metric> 上严格超越 <sota_benchmark>
 且达到可发表水平。要求 reviewer 的"下一步建议"对齐这个北极星——不只做局部审计，更要回答"怎样最可能走到超 SOTA">

## 2. Method / architecture under test
<本实验的架构与机制（来自 docs/04 该 ITER 的 architecture changes + orthogonality declaration）；
 这是 what changed 及 why structural>

## 3. Current results trend (not just this run)
<本实验 docs/06 result entry 的 metrics + semantic-success；
 并给出**同路线最近 2-3 次**的指标轨迹（docs/04/06），让 reviewer 看趋势而非孤点>

## 4. Known weaknesses & open conflicts
<docs/01 §6 gaps + §8 conflicts(CF-*) + docs/02 needs_primary_source 中与本实验相关者>

## 5. SOTA target & comparability contract
<docs/03 SOTA reference table（含目标值）+ comparability contract 6 维；
 **附相关 SOTA 的 dossier 摘要**：refs/dossiers/<slug>.md 的 dataset源/metric实现/split（一句话各）>

## 6. Abandoned cousin routes
<docs/09 中与本实验相关的 abandoned route + re-entry criteria（避免 reviewer 建议复活已否决路线）>

## 7. This round vs last round (diff)
<相对上一次同路线实验改了什么、上次 reviewer/ pivot 怎么说、本次是否回应了上次 blocker>

## Artifacts (paths only)
<metrics file / config / sbatch log / training curve summary / prediction artifact 路径>
```

数据来源映射：docs/00(§1)、docs/04(§2,§7)、docs/06(§3)、docs/01+02(§4,§5)、refs/dossiers(§5)、docs/03(§5)、docs/09(§6)、docs/07+08 上一轮(§7)。

若缺少 result entry，停止并要求先运行 result-log。

---

## Step 2 · 给三方写**同一个 full-scope prompt**

写入：

```text
/tmp/tri_review_<exp_id>/prompt_full_scope.md
```

然后复制或传给 A/B/C。三方收到的 prompt 必须相同，只在开头注明 reviewer identity：`You are Reviewer A=Claude` / `B=Codex` / `C=Antigravity`。

Prompt 内容必须要求每一方完整回答：

```markdown
# Independent Full-Scope Research Review

You are Reviewer <A/B/C> (<Claude/Codex/Antigravity>). You are independent from the other reviewers.
Do not assume a special role. Review all dimensions below and recommend the next step most likely to reach or exceed SOTA.

## Inputs
<paste shared context>

## Required output

### 1. Overall judgment
Choose exactly one:
- continue-current-route
- scale-to-track-b
- tune-only-if-near-sota
- replace-component
- change-backbone
- change-objective-or-loss
- run-sanity-check-first
- comparability-blocker
- abandon-route
- return-to-literature

### 2. SOTA gap interpretation
- Current metric:
- SOTA metric:
- Absolute gap:
- Relative gap:
- Is tuning justified? yes/no/only-if-near-sota. Explain.

### 3. Comparability and benchmark fairness audit
| Dimension | Pass / Fail / Unknown | Notes |
|---|---|---|
| Dataset version | | |
| Official split / same split | | |
| Metric implementation | | |
| Preprocessing | | |
| External weights / pretrained backbone version | | |
| Test-time inference protocol | | |
| Resource profile supports claim? | | |

### 4. Semantic success and reproducibility audit
| Check | Pass / Fail / Unknown | Notes |
|---|---|---|
| Metrics file exists and is parseable | | |
| Values finite / no NaN or Inf | | |
| Loss trend or expected pattern is sane | | |
| Seed variance known or not needed for screen | | |
| No suspiciously high jump / leakage signal | | |
| Logs/config/checkpoints sufficient to reproduce | | |

### 5. Architecture assessment
- What does the result imply about the architecture hypothesis?
- Is the current failure/success likely due to architecture, data scale, objective/loss, decoder/head, backbone, or optimization?
- Name 2-4 concrete architecture moves, not generic tuning.

### 6. Track A / Track B recommendation
- If Track A screen: should this candidate be promoted to Track B? why?
- If Track B/full/scale: should it continue scaling, pivot, or become claim candidate?
- If large gap remains: what architecture replacement is most justified?

### 7. Risks and blockers
- ...

### 8. Next action
Give one concrete next experiment or blocker-resolution step.

### 9. Confidence
High / Medium / Low, with reason.
```

---

## Step 3 · 并行调用 CLI reviewer，并失败重试一次

用 Bash 直接调用 CLI。不要使用 subagent 作为 reviewer。执行前先检查 CLI 是否存在；缺失时该 reviewer 视为失败并按重试/降级策略处理。

```bash
EXP_ID="<exp_id>"
ROOT="/tmp/tri_review_${EXP_ID}"
mkdir -p "$ROOT"

PROMPT="$ROOT/prompt_full_scope.md"

command -v claude  >/dev/null 2>&1 || echo "WARN: claude CLI not found" >&2
command -v codex   >/dev/null 2>&1 || echo "WARN: codex CLI not found" >&2
# Reviewer C = Antigravity (wrapper resolves $ANTIGRAVITY_CLI → agy)
{ [ -n "${ANTIGRAVITY_CLI:-}" ] && command -v "$ANTIGRAVITY_CLI" >/dev/null 2>&1; } \
  || command -v agy >/dev/null 2>&1 \
  || echo "WARN: Antigravity CLI not found (set ANTIGRAVITY_CLI or install agy) — reviewer C will fail → 2/3 DEGRADED" >&2

run_reviewer() {
  local id="$1"
  local label="$2"
  local cmd="$3"
  local out="$4"
  local status_file="$5"

  echo "RUNNING reviewer ${id}/${label}" > "$status_file"
  bash -lc "$cmd" > "$out" 2>&1
  local status=$?

  if [ $status -ne 0 ] || [ ! -s "$out" ] || ! grep -qi "Overall judgment" "$out"; then
    echo "RETRY reviewer ${id}/${label}" >> "$status_file"
    bash -lc "$cmd" > "$out.retry" 2>&1
    local status2=$?
    if [ $status2 -eq 0 ] && [ -s "$out.retry" ] && grep -qi "Overall judgment" "$out.retry"; then
      mv "$out.retry" "$out"
      echo "SUCCESS_AFTER_RETRY" >> "$status_file"
      return 0
    fi
    echo "FAILED_AFTER_RETRY" >> "$status_file"
    return 1
  fi

  echo "SUCCESS" >> "$status_file"
  return 0
}
# ⚠️ 上面 run_reviewer 只示意"原命令重试一次"。**完整策略是上文的 3 段重试**（见开头
#   "若任何 reviewer 失败，必须最多重试三次"）：① 原后端原 prompt 重试 → ② 换压缩版
#   `context_pack.py --purpose tri-review` prompt 重试 → ③ 进一步压缩 artifacts 再试。
#   实现时按 3 段来，别照抄这个单次示例就过早判 FAILED。

# Expand these from cluster_config.yaml command_template.
CMD_A='<claude command_template with {prompt_file} replaced>'
CMD_B='<codex command_template with {prompt_file} replaced>'
CMD_C='bash .agents/skills/tri-review/scripts/reviewer_c_antigravity.sh '"$PROMPT"   # antigravity (agy)

run_reviewer A claude      "$CMD_A" "$ROOT/output_a_claude.md"      "$ROOT/status_a.txt" & PID_A=$!
run_reviewer B codex       "$CMD_B" "$ROOT/output_b_codex.md"       "$ROOT/status_b.txt" & PID_B=$!
run_reviewer C antigravity "$CMD_C" "$ROOT/output_c_antigravity.md" "$ROOT/status_c.txt" & PID_C=$!

wait $PID_A; STATUS_A=$?
wait $PID_B; STATUS_B=$?
wait $PID_C; STATUS_C=$?

SUCCESS_COUNT=0
[ $STATUS_A -eq 0 ] && SUCCESS_COUNT=$((SUCCESS_COUNT+1))
[ $STATUS_B -eq 0 ] && SUCCESS_COUNT=$((SUCCESS_COUNT+1))
[ $STATUS_C -eq 0 ] && SUCCESS_COUNT=$((SUCCESS_COUNT+1))

echo "SUCCESS_COUNT=$SUCCESS_COUNT" > "$ROOT/quorum.txt"
```

---

## Step 4 · 汇总三方，不新增第四个 review

Host 只做 aggregator：读取成功 reviewer 的 raw outputs，提取 judgment、comparability blockers、architecture moves、next action、confidence。不要把 host 自己的想法伪装成 reviewer。

必须写入 `docs/07_tri_review.md`：

```markdown
# Tri-Review: <exp_id>

## Review mode
- Mode: independent_parallel_cli
- Prompt: one identical full-scope prompt for all reviewers
- Reviewer A: Claude CLI · <success / success_after_retry / failed>
- Reviewer B: Codex CLI · <success / success_after_retry / failed>
- Reviewer C: Antigravity CLI · <success / success_after_retry / failed> · backend=<antigravity(agy)>
- Quorum: <3/3, 2/3 degraded, or insufficient>

## Inputs
- Experiment:
- Track: <A-screen / B-scale / full / scale / generalization>
- Resource profile:
- Current metric:
- SOTA metric:
- Gap:

## Reviewer A · Claude
<judgment + compact summary; preserve key quoted recommendation if useful>

## Reviewer B · Codex
<judgment + compact summary>

## Reviewer C · Antigravity
<judgment + compact summary, or failed-after-retry; note backend if fallback used>

## Cross-reviewer agreement
- ...

## Disagreements
- Claude says ...
- Codex says ...
- Antigravity says ...
- Why the disagreement matters:

## Aggregated recommendation to pivot
Choose exactly one:
- [ ] Continue current route
- [ ] Tune current architecture
- [ ] Scale to Track B
- [ ] Replace component: <which>
- [ ] Change backbone
- [ ] Change objective / loss
- [ ] Sanity check first
- [ ] Comparability blocker first
- [ ] Abandon route → decisions-log
- [ ] Return to literature

## Required prerequisites before next run
- [ ] ...

## Confidence
High / Medium / Low. If only 2 reviewers succeeded, confidence cannot exceed Medium. If only 1 succeeded, confidence must be Low and the entry is a `SINGLE_REVIEW_CONTINUATION` (non-claim only, `Quorum: 1/3`).

## Raw outputs
- /tmp/tri_review_<exp_id>/output_a_claude.md
- /tmp/tri_review_<exp_id>/output_b_codex.md
- /tmp/tri_review_<exp_id>/output_c_antigravity.md
```

---

## Decision rules for aggregation

- If 0 reviewers succeed: stop + notify; do not pivot. If exactly 1 succeeds: only `SINGLE_REVIEW_CONTINUATION` is allowed (ordinary reversible non-claim iteration, confidence Low, mark `Quorum: 1/3`); claim / abandon / goal-revision still require ≥2 independent reviewers.
- If Claude and Codex agree, use that as primary recommendation; Antigravity can add risks or alternatives.
- If Claude and Codex disagree, mark high-disagreement and require pivot to explicitly resolve the conflict.
- If Antigravity is the only failed reviewer, proceed with Claude+Codex and mark `DEGRADED_REVIEW`.
- If any successful reviewer raises a comparability blocker or leakage suspicion, pivot cannot claim SOTA and must choose sanity/comparability first unless the concern is explicitly rebutted.
- If all successful reviewers agree gap is large and sanity passes, default away from tuning and toward architecture replacement.

---

## Don'ts

- 不要给 A/B/C 分配不同审稿角色。
- 不要用 subagent 代替 CLI reviewer。
- 不要把主对话 host 当 reviewer。
- 不要 hardcode 其它 CLI；Reviewer C 一律走 `reviewer_c_antigravity.sh`（Antigravity=agy；无 cursor-agent 兜底）。
- 不要把 `exit code 0` 当成功；必须输出非空且包含 `Overall judgment`。
- 不要在只有一个 reviewer 成功时做 claim / abandon / goal-revision 级 pivot；普通可逆非 claim 迭代可走 `SINGLE_REVIEW_CONTINUATION`（confidence=Low，须在 docs/07+08 标 `Quorum: 1/3`）。

---

## Handoff

- **Inputs from**: result-log, benchmark-roadmap, experiment_iterations, decisions-log
- **Outputs to**: `docs/07_tri_review.md`, `/tmp/tri_review_<exp_id>/`
- **Next skill**: pivot
