#!/usr/bin/env bash
# PreToolUse(Bash) hook: block destructive `rm` against protected research-knowledge
# paths (refs/ wiki/ docs/ scripts/ ACTIVE_GOAL.json .git), and truncating redirect
# onto ACTIVE_GOAL.json. Everything else allowed silently. stdin parsed via python3
# (no jq dependency). Emits a PreToolUse deny.
set -uo pipefail
input=$(cat)
cmd=$(printf '%s' "$input" | python3 -c "import sys,json
try: print(json.load(sys.stdin).get('tool_input',{}).get('command',''))
except Exception: print('')" 2>/dev/null)
[ -z "$cmd" ] && exit 0

deny() {
  cat <<EOF
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"$1 若确属有意，请在 Claude Code 之外手动执行，或用 /hooks 临时停用该守卫。"}}
EOF
  exit 0
}

PROT='(^|[[:space:]/="'\''])(refs|wiki|docs|scripts|pipelines|configs|reports|runs|outputs|logs|software_outputs|external_runs|manuscript)(/|[[:space:]"'\'']|$)|(^|[[:space:]/="'\''])data/raw(/|[[:space:]"'\'']|$)|ACTIVE_GOAL\.json|PROJECT_STRUCTURE\.md|(^|[[:space:]/])\.git(/|[[:space:]"'\'']|$)'

# 1) rm with -r/-f flag (short cluster -rf/-fr OR GNU long --recursive/--force/-R)
#    hitting a protected path. Long options previously bypassed this guard.
if printf '%s' "$cmd" | grep -qiE 'rm[[:space:]]+([^|;&]*[[:space:]])?(-[a-z]*[rfR]|--(recursive|force))'; then
  if printf '%s' "$cmd" | grep -qE "$PROT"; then
    deny "🛑 拦截：破坏性 rm 命中受保护的研究知识/产物路径(refs/ wiki/ docs/ scripts/ configs/ pipelines/ reports/ runs/ software_outputs/ data/raw 等)。"
  fi
fi

# 2) truncating redirect onto ACTIVE_GOAL.json / PROJECT_STRUCTURE.md.
# Keep the protected filename inside the redirect pattern; otherwise harmless
# reads such as `sed PROJECT_STRUCTURE.md` are falsely denied.
if printf '%s' "$cmd" | grep -qE '>[[:space:]]*"?[^|;&]*(ACTIVE_GOAL\.json|PROJECT_STRUCTURE\.md)'; then
  deny "🛑 拦截：重定向覆盖 ACTIVE_GOAL.json 或 PROJECT_STRUCTURE.md（请用 Edit 或脚本修改，避免误清空关键合约）。"
fi

exit 0
