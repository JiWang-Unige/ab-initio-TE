#!/usr/bin/env bash
# SessionStart hook: print a short project orientation snapshot.
# stdout is injected into the session context (and shown to the user), so every
# session opens knowing: the active goal, open runs, recent findings, pending queue.
set -uo pipefail
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$ROOT" 2>/dev/null || exit 0

echo "=== auto-research 项目快照 ==="


# Master plan navigation (robust:精确匹配失败时回退，不静默丢导航)
if [ -f docs/11_master_plan.md ]; then
  mp=docs/11_master_plan.md
  mode=$(grep -m1 -iE '^[-*][[:space:]]*Mode:|^[-*][[:space:]]*当前模式' "$mp" 2>/dev/null | sed -E 's/^[-*][[:space:]]*(Mode|当前模式)[:：][[:space:]]*//I' | cut -c1-100)
  # 回退1: §0 当前模式 段下首个非空行
  [ -z "$mode" ] && mode=$(awk '/当前模式|Current mode/{f=1;next}/^## /{if(f)exit}f&&NF&&!/^#/{gsub(/^[-*][[:space:]]*/,"");print;exit}' "$mp" 2>/dev/null | cut -c1-100)
  now=$(awk '/现在该做|Now|下一步/{f=1;next}/^## /{f=0}f&&/当前动作|next action/{sub(/^[-*][[:space:]]*(当前动作|next action)[:：][[:space:]]*/,"");print;exit}' "$mp" 2>/dev/null | cut -c1-120)
  # 回退2: "现在该做"段下首个 bullet
  [ -z "$now" ] && now=$(awk '/现在该做|^## .*Now/{f=1;next}/^## /{f=0}f&&/^[-*][0-9]*\.?[[:space:]]/{gsub(/^[-*][0-9]*\.?[[:space:]]*/,"");print;exit}' "$mp" 2>/dev/null | cut -c1-120)
  echo "MASTER PLAN: mode=${mode:-?}; now=${now:-见 docs/11} (docs/11 — 全局导航，回来先读这个)"
fi

# ACTIVE_GOAL
if [ -f ACTIVE_GOAL.json ]; then
  python3 - <<'PY' 2>/dev/null || true
import json
try:
    d=json.load(open("ACTIVE_GOAL.json"))
    print(f"GOAL[{d.get('scope','?')}/{d.get('status','?')}]: {str(d.get('goal',''))[:120]}")
    sc=d.get("success_criteria",[])
    if sc: print("  success:", "; ".join(f"{r.get('metric')}{r.get('op')}{r.get('threshold')}" for r in sc))
except Exception: pass
PY
fi

# Open runs in tracker (RUNNING/FAILED/TODO)
if [ -f docs/05_todo.md ]; then
  open=$(grep -E '^\| .* \| (RUNNING|FAILED|STALE|TODO) \|' docs/05_todo.md 2>/dev/null | head -5)
  [ -n "$open" ] && { echo "OPEN runs (docs/05 tracker):"; echo "$open" | sed 's/^/  /'; }
  pend=$(awk '/## Pending integration queue/{f=1;next}/^## /{f=0}f&&/^- \[ \]/' docs/05_todo.md 2>/dev/null | head -3)
  [ -n "$pend" ] && { echo "PENDING /note-add 待整合:"; echo "$pend" | sed 's/^/  /'; }
fi

# Findings counts
if [ -f docs/10_findings.md ]; then
  rf=$(awk '/## Research Findings/{f=1;next}/## Engineering/{f=0}f&&/^- /&&!/\(空\)/' docs/10_findings.md 2>/dev/null | wc -l)
  ef=$(awk '/## Engineering Findings/{f=1;next}/## How to use|^---/{f=0}f&&/^- /&&!/\(空\)/' docs/10_findings.md 2>/dev/null | wc -l)
  echo "findings: research=$rf engineering=$ef (docs/10) — 迭代前先读"
fi
echo "=== 段A:/research-interview… | 段B:/pursue/goal-prompt | 段C:/publication-plan 或 /pipeline-blueprint ==="
