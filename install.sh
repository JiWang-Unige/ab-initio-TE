#!/usr/bin/env bash
# Install the Auto-Research (lwcr+) portable framework into a target project.
# Single-repo dual-shell: --driver claude|codex|both (default both).
#
# IDEMPOTENT & SAFE TO RE-RUN. Three intents, one command:
#   • fresh install        → seeds everything (templates + requested shell).
#   • add a shell mid-run  → `./install.sh --driver claude <proj>` on a codex-only
#                            project ADDS the claude shell, PRESERVES docs/research
#                            progress AND the existing codex shell.
#   • upgrade framework     → refreshes scripts/shells/ARCHITECTURE/README; preserves
#                            docs/goals/refs/wiki/CLAUDE.md/ACTIVE_GOAL/cluster_config/secrets.
# Research content is seed-if-absent (never wiped); framework code is refreshed;
# only the requested shell(s) are (re)installed. Everything is backed up first
# (.backup-<timestamp>). The latest CLAUDE template lands as CLAUDE.md.example.
# Does NOT make commits. Optional git/worktree isolation is handled later by /workspace-matrix and is human-gated.
set -euo pipefail

DRIVER="both"; TARGET=""
while [ $# -gt 0 ]; do
  case "$1" in
    --driver) DRIVER="${2:-}"; shift 2;;
    --driver=*) DRIVER="${1#*=}"; shift;;
    -h|--help) echo "Usage: ./install.sh [--driver claude|codex|both] /path/to/your/project"; exit 0;;
    *) TARGET="$1"; shift;;
  esac
done
if [ -z "$TARGET" ]; then echo "Usage: ./install.sh [--driver claude|codex|both] /path/to/your/project"; exit 1; fi
case "$DRIVER" in
  claude) want_claude=1; want_codex=0;;
  codex)  want_claude=0; want_codex=1;;
  both)   want_claude=1; want_codex=1;;
  *) echo "bad --driver: '$DRIVER' (expect claude|codex|both)"; exit 1;;
esac

SRC="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$TARGET"
stamp="$(date +%Y%m%d-%H%M%S)"

# === Install model (idempotent + safe to re-run): PRESERVE research content, ===
# === REFRESH framework code, install ONLY the requested shell(s). So you can  ===
# === add a shell mid-project or move to a new machine WITHOUT wiping docs or   ===
# === the other already-installed shell. Everything is backed up first.         ===
backup()      { if [ -e "$TARGET/$1" ] || [ -L "$TARGET/$1" ]; then cp -R "$TARGET/$1" "$TARGET/$1.backup-$stamp" 2>/dev/null || true; fi; }
refresh_dir() { backup "$1"; rm -rf "$TARGET/$1"; cp -R "$SRC/$1" "$TARGET/$1"; }
refresh_file(){ backup "$1"; mkdir -p "$(dirname "$TARGET/$1")"; cp "$SRC/$1" "$TARGET/$1"; }
seed_dir()    { [ -e "$TARGET/$1" ] || cp -R "$SRC/$1" "$TARGET/$1"; }
seed_file()   { [ -e "$TARGET/$1" ] || { mkdir -p "$(dirname "$TARGET/$1")"; cp "$SRC/$1" "$TARGET/$1"; }; }

refresh_scripts() {
  # Refresh EVERY framework script shipped in SRC/scripts (overwrite in place),
  # but NEVER delete target-only files → user scripts placed in scripts/ are
  # preserved. Iterating SRC (instead of a hand-maintained allowlist) means new
  # framework scripts can't be silently dropped on install/upgrade.
  mkdir -p "$TARGET/scripts/hooks"
  while IFS= read -r f; do
    mkdir -p "$(dirname "$TARGET/$f")"
    cp "$SRC/$f" "$TARGET/$f"
  done < <(cd "$SRC" && find scripts -type f ! -name '*.pyc' -not -path '*/__pycache__/*')
}

reinstall=0
if [ -e "$TARGET/.claude" ] || [ -e "$TARGET/.codex" ] || [ -e "$TARGET/docs/00_active_goal.md" ]; then reinstall=1; fi
[ "$reinstall" = 1 ] && echo "↻ 检测到已有安装：保留研究内容(docs/goals/refs/wiki/CLAUDE/ACTIVE_GOAL/cluster_config/secrets/.mcp.json) + 已有的另一壳，仅刷新框架代码并安装所请求的壳。"

# --- A. Framework code: refresh known framework files; preserve user scripts. ---
refresh_scripts
refresh_file ARCHITECTURE.md
refresh_file README.auto-research.md
refresh_file PROJECT_STRUCTURE.md
refresh_file cluster_config.yaml.example
refresh_file .mcp.json.example
refresh_file secrets.env.example
# CLAUDE.md is the AGENTS.md source AND holds user config after /configure-project.
# Ship the latest template as CLAUDE.md.example (diff reference); PRESERVE user's CLAUDE.md.
cp "$SRC/CLAUDE.md" "$TARGET/CLAUDE.md.example"
seed_file CLAUDE.md
cp "$SRC/ACTIVE_GOAL.json" "$TARGET/ACTIVE_GOAL.json.example"
seed_file ACTIVE_GOAL.json

# --- B. Research content + user config: SEED IF ABSENT (never wipe progress) ---
seed_dir docs
# v4.0+ seeds docs/11-22 into existing projects without overwriting user progress.
for f in docs/11_master_plan.md docs/12_publication_strategy.md docs/13_pipeline_blueprint.md \
         docs/14_validation_matrix.md docs/15_evidence_register.md docs/16_artifact_registry.md \
         docs/17_parallel_workspace.md docs/18_runtime_playbook.md docs/19_evaluator_contract.md \
         docs/20_baseline_reproduction.md docs/21_code_review_log.md docs/22_upgrade_log.md; do
  seed_file "$f"
done
seed_dir goals
seed_dir refs
seed_dir wiki
seed_file .mcp.json                                    # pre-enabled retrieval MCP (keys via ${VAR}/secrets.env)
if [ ! -e "$TARGET/secrets.env" ]; then                # API keys travel WITH the framework
  { [ -f "$SRC/secrets.env" ] && cp "$SRC/secrets.env" "$TARGET/secrets.env"; } || cp "$SRC/secrets.env.example" "$TARGET/secrets.env"
  chmod 600 "$TARGET/secrets.env" 2>/dev/null || true
fi
if [ -f "$TARGET/.gitignore" ]; then
  grep -qxF 'secrets.env' "$TARGET/.gitignore" 2>/dev/null || printf '\n# auto-research secrets (never commit)\nsecrets.env\n.env\n' >> "$TARGET/.gitignore"
else
  cp "$SRC/.gitignore" "$TARGET/.gitignore"
fi

# --- C. Shells: install/refresh ONLY the requested driver (preserve the other) ---
if [ "$want_claude" = 1 ]; then refresh_dir .claude; fi
if [ "$want_codex" = 1 ]; then
  refresh_dir .codex
  refresh_dir agents
  refresh_file RUN_PROMPT.codex.md
  # .agents = codex entrypoint: pre-built SHORT-desc skills + subagents (a REAL dir,
  # NOT a symlink to .claude — symlinking blew codex's ~8000-char skill-list budget).
  backup .agents; rm -rf "$TARGET/.agents"; mkdir -p "$TARGET/.agents"
  cp -R "$SRC/.agents/skills" "$TARGET/.agents/skills"   # pre-built short-desc codex/cross-agent skills
  cp -R "$SRC/.claude/agents" "$TARGET/.agents/agents"   # subagents (not in the skill-list budget)
  # Some Codex builds load project skills from .codex/skills rather than .agents/skills; keep a mirror.
  rm -rf "$TARGET/.codex/skills"
  if [ -d "$SRC/.codex/skills" ]; then cp -R "$SRC/.codex/skills" "$TARGET/.codex/skills"; else cp -R "$SRC/.agents/skills" "$TARGET/.codex/skills"; fi
fi

# --- Regenerate codex layer & AGENTS.md from the (possibly user-edited) CLAUDE.md ---
# both-shell present → rebuild codex skills from .claude/skills (zero drift); codex-only keeps shipped.
if [ -d "$TARGET/.claude/skills" ] && [ -d "$TARGET/.agents/skills" ] && [ -f "$TARGET/scripts/build_codex_skills.py" ]; then
  (cd "$TARGET" && python3 scripts/build_codex_skills.py . >/dev/null 2>&1) \
    && echo "✓ codex skills regenerated (short YAML-safe desc) to .agents/skills + .codex/skills"
fi
if [ -d "$TARGET/.agents/skills" ] && [ -d "$TARGET/.codex/skills" ] && [ -f "$TARGET/scripts/validate_codex_skills.py" ]; then
  (cd "$TARGET" && python3 scripts/validate_codex_skills.py . >/dev/null 2>&1) \
    && echo "✓ codex skill frontmatter validated" || echo "⚠️  WARN: codex skill validation failed; run python3 scripts/validate_codex_skills.py ." >&2
fi
# AGENTS.md from CLAUDE.md whenever a codex shell is present (or AGENTS already exists).
if [ -e "$TARGET/.codex" ] || [ -e "$TARGET/.agents" ] || [ -e "$TARGET/AGENTS.md" ]; then
  (cd "$TARGET" && bash scripts/sync_agents_md.sh >/dev/null 2>&1) && echo "✓ AGENTS.md generated from CLAUDE.md"
fi

# --- Project skeleton (empty placeholders) ---------------------------------
mkdir -p "$TARGET/docs/experiments" "$TARGET/docs/inputs" "$TARGET/outputs" "$TARGET/sbatch" "$TARGET/templates" "$TARGET/configs"          "$TARGET/configs/pipelines" "$TARGET/configs/sota_randomized" "$TARGET/runs" "$TARGET/reports" "$TARGET/logs"          "$TARGET/pipelines" "$TARGET/external_runs" "$TARGET/software_outputs"          "$TARGET/data/raw" "$TARGET/data/interim" "$TARGET/data/processed" "$TARGET/analysis/notebooks" "$TARGET/manuscript" "$TARGET/worktrees" "$TARGET/refs/supp"
for d in docs/inputs docs/experiments outputs sbatch templates configs configs/pipelines configs/sota_randomized runs reports logs pipelines external_runs software_outputs data/raw data/interim data/processed analysis analysis/notebooks manuscript worktrees refs/supp; do touch "$TARGET/$d/.gitkeep"; done
chmod +x "$TARGET"/scripts/*.sh "$TARGET"/scripts/*.py "$TARGET"/scripts/hooks/*.sh \
         "$TARGET"/refs/*.sh "$TARGET"/wiki/*.sh 2>/dev/null || true

# --- Post-install sanity ---------------------------------------------------
missing=0
for s in scripts/validate_goal.py scripts/check_data.py scripts/repair_advisor.py \
         scripts/iter_ledger.py scripts/context_pack.py scripts/job_watch.sh \
         scripts/lit_search.py scripts/sota_seed_matrix.py scripts/note_gate.py scripts/artifact_registry.py \
         scripts/validate_stage_c.py scripts/next_evidence_id.py \
         scripts/build_codex_skills.py scripts/validate_codex_skills.py scripts/build_atlas.py scripts/sync_agents_md.sh \
         scripts/research_flow_guard.py scripts/sota_failure_report.py scripts/workspace_matrix.py \
         scripts/hooks/session_status.sh scripts/hooks/research_bootstrap.sh \
         scripts/hooks/wiki_reindex.sh scripts/hooks/guard_paths.sh \
         scripts/hooks/submit_guard.sh scripts/hooks/iter_record_nudge.sh \
         scripts/hooks/loop_ledger.sh scripts/hooks/precompact_flush.sh scripts/hooks/stage_flow_nudge.sh refs/archive_source.sh wiki/wiki.sh; do
  if [ ! -x "$TARGET/$s" ]; then echo "⚠️  WARN: missing or non-executable: $s" >&2; missing=1; fi
done
# reviewer C wrapper lives under whichever skill dir got installed
rev=""
[ "$want_claude" = 1 ] && rev=".claude/skills/tri-review/scripts/reviewer_c_antigravity.sh"
[ "$want_claude" = 0 ] && [ "$want_codex" = 1 ] && rev=".agents/skills/tri-review/scripts/reviewer_c_antigravity.sh"
if [ -n "$rev" ]; then
  chmod +x "$TARGET/$rev" 2>/dev/null || true
  [ -x "$TARGET/$rev" ] || { echo "⚠️  WARN: missing reviewer wrapper: $rev" >&2; missing=1; }
fi
[ "$missing" -eq 0 ] && echo "✓ key scripts present & executable"

cat <<EOF

✅ Installed Auto-Research (lwcr+) into $TARGET  [driver: $DRIVER]
Backups (if any): suffix .backup-$stamp

下一步（推荐：不必开局手填——诉求澄清后交给 AI 填）：
  1. 直接开跑段A（CLAUDE.md §0-2 已预设基因组DL方向，足够起步）：
       Claude 壳：/research-interview → /research-synthesize → /sota-inventory → /grill
       Codex  壳：粘贴 RUN_PROMPT.codex.md 开局，用 \$skill-name 调用（.agents/skills/）。
  2. grill 澄清诉求后 → /configure-project：AI 据澄清上下文 + 探测集群(sinfo)/conda
       自动填 CLAUDE.md §0-2/§12-15 + cluster_config.yaml + ACTIVE_GOAL.json（提议 diff→你确认才写），并重生成 AGENTS.md。
       —— 免开局手填易疏漏；挪集群/换方向后随时可重调 /configure-project。
  3. 确认配置 → /benchmark-roadmap → /reproduce-baselines → 段B /pursue 或 /goal-prompt。
     若已有强候选/完整思路，不要强行探索：走段C /master-plan → /publication-plan；
     若是 raw data / 生信流程：走段C /master-plan → /pipeline-blueprint → /artifact-registry。
  4. 外部 CLI：codex / Antigravity(agy，需 'agy -p "hi"' 完成 Google 登录) 在 PATH。统一三 CLI（claude/codex/agy），无 cursor-agent 兜底。
  5. 检索 MCP 已预启用（.mcp.json：anysearch/exa/context7/mcp-deepwiki）：首次进会话 Claude Code 会让你批准这些项目级 MCP。
       anysearch=通用网页+academic学术(找论文)+批量+URL提取(治常规检索不好用)；exa=neural网页；deepwiki=读懂仓库；context7=库文档。
       【API key 跟着框架走，不必每台机器重输】把 key 填进 \`secrets.env\`（已 chmod600+gitignore，随 install/tar 走）：
         - S2_API_KEY  → lit_search.py 自动从 secrets.env 读，零额外操作；
         - EXA / ANYSEARCH_API_KEY → 给 MCP 用，需进环境：在框架根跑一次  echo "source \$(pwd)/secrets.env" >> ~/.bashrc （之后每个 shell 自动加载）。
       context7/deepwiki 免 key；anysearch 不填走匿名；未设的 key 对应源自动降级(退回 lit_search+WebFetch)。
  6. （可选·手填）也可自己填 CLAUDE §0-2/§12-15 + cp cluster_config.yaml.example cluster_config.yaml + 改 ACTIVE_GOAL status→active；改完 CLAUDE 跑 \`bash scripts/sync_agents_md.sh\` 重生成 AGENTS.md。
  注：并行多线默认靠 exp_id 目录隔离；若多方向同时改共享代码，可选用 /workspace-matrix 建 git/worktree（人闸，最多3线）。本框架建议用 git 版本化框架/轻量记录，但安装脚本不自动 commit。

  ★ 中途换驱动 / 补装壳 / 挪机器（你的研究进度不会丢）：
    - 只装了 codex、想加 claude 来跑某步：重跑 \`./install.sh --driver claude $TARGET\`
      —— 会**保留 docs/研究进度 + 已有 codex 壳**，仅补上 .claude 壳并重生成 AGENTS.md。反之亦然。
    - 两壳共享同一份 docs/refs/wiki/scripts，故可在任意 skill 边界中断、换驱动接力（如 codex 做完
      research-interview，换 claude 跑 research-synthesize）——都从磁盘 docs 续接，不丢上下文。
    - 挪到新机器/集群：scp tar → install（同样保留内容）→ 跑 \`/configure-project\` 让 AI 重新探测
      新环境(集群/conda/提交方式)并改写 CLAUDE §12 + cluster_config（含 submission_mode：on_cluster 直接
      sbatch / remote_ssh 经 ssh 提交 / local_direct 本地直跑）。框架代码已更新处见 CLAUDE.md.example 可 diff。
EOF
