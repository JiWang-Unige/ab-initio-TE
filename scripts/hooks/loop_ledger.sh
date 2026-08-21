#!/usr/bin/env bash
# Stop hook: end-of-turn reconciliation sweep. If any run on disk (reports/runs)
# is NOT fully recorded in docs/04+05+06 — or lacks outputs/<id>/STATUS — surface
# an advisory systemMessage so the drift is caught immediately, not 5 rounds later.
# NON-blocking (uses systemMessage, not decision:block). Guards stop_hook_active.
# stdin parsed via python3 (no jq).
set -uo pipefail
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
input=$(cat)
active=$(printf '%s' "$input" | python3 -c "import sys,json
try: print(json.load(sys.stdin).get('stop_hook_active', False))
except Exception: print(False)" 2>/dev/null)
[ "$active" = "True" ] && exit 0
msgs=""

# 1) Ledger reconciliation (drift / chain gaps / ghost run).
if [ -f "$ROOT/scripts/iter_ledger.py" ]; then
  out=$(python3 "$ROOT/scripts/iter_ledger.py" "$ROOT" 2>/dev/null)
  if [ $? -ne 0 ]; then
    reminder=$(printf '%s' "$out" | python3 -c "import sys,json
try: print(json.load(sys.stdin).get('reminder',''))
except Exception: print('')" 2>/dev/null)
    [ -n "$reminder" ] && msgs="$reminder"
  fi
fi

# 2) Master-plan staleness (#5 导航兜底): if a pivot/result landed AFTER the last
#    master-plan update, the navigation map is likely stale → nudge /master-plan.
mp="$ROOT/docs/11_master_plan.md"
if [ -f "$mp" ]; then
  stale=""
  for f in docs/08_pivot_decisions.md docs/06_results_log.md docs/12_publication_strategy.md docs/13_pipeline_blueprint.md; do
    [ -f "$ROOT/$f" ] && [ "$ROOT/$f" -nt "$mp" ] && stale="$f"
  done
  [ -n "$stale" ] && msgs="${msgs:+$msgs$'\n'}导航可能过期：$stale 比 docs/11_master_plan.md 新 → 跑 /master-plan 更新「当前步/已确定/待议分支」，免得回来丢思路（#5）。"
fi

[ -z "$msgs" ] && exit 0
python3 - "$msgs" <<'PY'
import json, sys
print(json.dumps({"systemMessage": sys.argv[1]}))
PY
exit 0
