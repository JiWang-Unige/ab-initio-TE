#!/usr/bin/env bash
# PostToolUse(Write|Edit) hook: if a wiki idea/note was written, rebuild wiki/INDEX.md.
# Reads hook JSON on stdin (parsed via python3 — no jq dependency). No-op for
# non-wiki files. Never fails the tool.
set -uo pipefail
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
input=$(cat)
f=$(printf '%s' "$input" | python3 -c "import sys,json
try:
    d=json.load(sys.stdin); ti=d.get('tool_input',{}) or {}; tr=d.get('tool_response',{}) or {}
    print(ti.get('file_path') or tr.get('filePath') or '')
except Exception: print('')" 2>/dev/null)
case "$f" in
  *wiki/ideas/*|*wiki/notes/*)
    bash "$ROOT/wiki/wiki.sh" index >/dev/null 2>&1 || true
    echo '{"suppressOutput": true, "systemMessage": "wiki INDEX 已自动刷新"}'
    ;;
  *) : ;;
esac
exit 0
