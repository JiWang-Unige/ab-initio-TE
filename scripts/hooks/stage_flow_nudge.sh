#!/usr/bin/env bash
# PostToolUse hook: after critical stage docs are edited, surface the next
# expected step and SOTA source failures. Advisory only; never edits files.
set -uo pipefail
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
input=$(cat)
fp=$(printf '%s' "$input" | python3 -c "import sys,json,re
try:
    obj=json.load(sys.stdin); ti=obj.get('tool_input',{})
    fp=ti.get('file_path','') or ti.get('path','') or ''
    if not fp:
        patch=ti.get('patch','') or ti.get('input','') or ''
        m=re.search(r'^\*\*\* (?:Update|Add) File: (.+)$', patch, re.M)
        fp=m.group(1).strip() if m else ''
    print(fp)
except Exception: print('')" 2>/dev/null)
case "$fp" in
  */docs/02_sota_model_inventory.md|docs/02_sota_model_inventory.md|*/docs/03_benchmark_roadmap.md|docs/03_benchmark_roadmap.md|*/ACTIVE_GOAL.json|ACTIVE_GOAL.json)
    flow=$(python3 "$ROOT/scripts/research_flow_guard.py" "$ROOT" --format markdown 2>/dev/null || true)
    fail=""
    case "$fp" in *02_sota_model_inventory.md) fail=$(python3 "$ROOT/scripts/sota_failure_report.py" "$ROOT" --format markdown 2>/dev/null || true);; esac
    python3 - "$flow" "$fail" <<'PY'
import json, sys
msg = (sys.argv[1] or '').strip()
fail = (sys.argv[2] or '').strip()
if fail and '未发现' not in fail:
    msg = (msg + "\n\n" + fail).strip()
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}}))
PY
    ;;
esac
exit 0
