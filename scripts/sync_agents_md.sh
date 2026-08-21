#!/usr/bin/env bash
# Generate AGENTS.md (Codex driver shell) DETERMINISTICALLY from CLAUDE.md
# (Claude driver shell). Single-repo dual-shell, zero drift: edit CLAUDE.md,
# rerun this, AGENTS.md regenerates. install.sh --driver both also calls it.
#
# Transform: same body as CLAUDE.md, with driver bindings rewritten —
#   .claude/skills  -> .agents/skills ; .claude/agents -> .agents/agents ;
#   .claude/settings.json -> .codex/hooks.json ; /skill-name -> $skill-name
# (skill-call rewrite uses lookbehind so it never touches path segments like
#  ".agents/skills/tri-review"). A Codex header + a "Codex Hook Fallback"
# footer are wrapped around it.
set -euo pipefail
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ROOT"
[ -f CLAUDE.md ] || { echo "CLAUDE.md not found" >&2; exit 1; }

# SKILLS alternation derived DYNAMICALLY from .claude/skills/ (single source of
# truth — no hardcoded list to drift when a skill is added/removed). Longest
# names first so the /skill→$skill rewrite never partially matches a prefix.
SKILLS="$(find .claude/skills -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null \
  | awk '{ print length, $0 }' | sort -rn | cut -d' ' -f2- | paste -sd'|' -)"
[ -z "$SKILLS" ] && { echo "no skills found under .claude/skills/" >&2; exit 1; }
export SKILLS

{
  cat <<'HEADER'
# <Your Project> Guide — Codex driver (AGENTS.md)

> **回答语言：始终用简体中文**（代码注释跟随现有代码库语言）。
>
> **THIS FILE IS THE AUTHORITATIVE INSTRUCTION FOR THE CODEX DRIVER.**
> Auto-generated from `CLAUDE.md` by `scripts/sync_agents_md.sh` (single-repo dual-shell, zero drift — edit CLAUDE.md, then rerun the script). If a legacy `CLAUDE.md` differs, Codex follows THIS file.
> Driver bindings differ from the Claude shell: invoke skills as `$skill-name` (not `/skill-name`); skills live in `.agents/skills/`（并镜像 `.codex/skills/` 以兼容不同 Codex/Antigravity loader）； subagents in `.agents/agents/` (+ `.codex/agents/*.toml` sandbox shells); hooks in `.codex/hooks.json`. Everything else (workflow, gates, scripts, docs) is identical. See §16b for the Codex hook fallback.

---

HEADER

  # Body: CLAUDE.md minus its own title/banner block (lines 1..first '---'),
  # with driver path + skill-call rewrites applied.
  awk 'NR==1{skip=1} skip && /^---[[:space:]]*$/{skip=0; next} !skip' CLAUDE.md \
    | sed -e 's,\.claude/skills,.agents/skills,g' \
          -e 's,\.claude/agents,.agents/agents,g' \
          -e 's,\.claude/settings\.json,.codex/hooks.json,g' \
    | perl -pe 's{(?<![\w./])/($ENV{SKILLS})(?![\w/])}{\$$1}g' \
    | sed -e 's#从 .agents/skills 生成精简 `\.agents/skills`#从 canonical skills 层生成/校验精简 `.agents/skills`#g' \
          -e 's#`\.agents/agents` 复制 `\.agents/agents`#`.agents/agents` 复制/镜像 subagents#g' \
          -e 's#从 `scripts/build_codex_skills.py` 从 `.agents/skills` 生成#从 `scripts/build_codex_skills.py` 从 canonical skill source 生成#g' \
          -e 's#从 `.agents/skills` 生成的短描述真实目录#从 canonical skill source 生成的短描述真实目录#g'

  cat <<'FOOTER'

---

## 16b. Codex Hook Fallback（驱动差异说明）

Claude 壳的 hooks 在 `.claude/settings.json`；Codex 壳的等价 hooks 在 `.codex/hooks.json`（SessionStart `startup|resume|compact` + SubagentStart + PreToolUse + PostToolUse + Stop + **PreCompact**），调用**同一批** `scripts/hooks/*.sh`。两壳共享 `scripts/`、`docs/`、`refs/`、`wiki/`。PreCompact → `precompact_flush.sh` 在压缩前提醒先 /note-gate 落盘（聊天内容压缩后丢，docs 才留得住）。

- `.codex/config.toml` 预设 `multi_agent=true / max_threads=4 / max_depth=1`；Codex 没有 Claude 的内存级 fork 开关，实际上下文继承由 SubagentStart hook 从磁盘重注入来保障。
- Codex 无内存级 fork：subagent 启动时的上下文由 `SubagentStart` hook → `scripts/hooks/research_bootstrap.sh` 从磁盘确定性重注入（`context_pack.py`），等价实现"subagent 启动即有父上下文"。
- 四个 Codex 原生 subagent shell：`.codex/agents/{research-scout,iteration-auditor,project-cartographer,source-artifact-archivist}.toml`；其中 cartographer/scout/auditor 为 read-only，archivist 只写 `refs/`。
- **关键边界：hook 只能"提醒/拦截"，不能"执行 skill"** —— 它无法替你跑 `$tri-review`，只能在被跳过时报出来；实际执行 result-log/tri-review/pivot 仍由 agent 调用 skill。
- 若某 hook 事件在你的 Codex 版本不可用，则以 `RUN_PROMPT.codex.md` 的开局纪律为兜底：每轮先跑 `context_pack.py`，run 后闭环 result-log→validate_goal→tri-review→pivot→docs→iter_ledger。
FOOTER
} > AGENTS.md

echo "AGENTS.md regenerated from CLAUDE.md ($(wc -l < AGENTS.md) lines)"
