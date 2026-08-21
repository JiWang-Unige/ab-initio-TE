#!/usr/bin/env bash
# Reviewer C launcher for /tri-review.
#
# Reviewer C was switched from Gemini to **Antigravity** (Google's agent CLI,
# `agy`, Gemini 3 Pro under the hood). Backend resolution at runtime:
#
#   1. $ANTIGRAVITY_CLI (if set & on PATH) — explicit override; prompt via stdin.
#   2. `agy` (official Antigravity CLI, `agy -p`) — auto-detected default.
#      Requires a one-time Google OAuth login (run `agy -p "hi"` once and complete
#      the browser login, or `agy login` if available). Until then it prints an
#      "Authentication required" URL and this reviewer is treated as failed.
#   3. None available -> exit non-zero so /tri-review applies DEGRADED_REVIEW.
#
# (The framework standardizes on three CLIs: claude / codex / agy. There is no
#  cursor-agent fallback — if agy is unavailable, reviewer C simply fails and
#  the 2/3 DEGRADED_REVIEW path applies.)
#
# Usage: reviewer_c_antigravity.sh <prompt_file>
set -uo pipefail

PROMPT_FILE="${1:-}"
if [ -z "$PROMPT_FILE" ] || [ ! -s "$PROMPT_FILE" ]; then
  echo "ERROR: usage: reviewer_c_antigravity.sh <non-empty prompt_file>" >&2
  exit 2
fi

PRINT_TIMEOUT="${ANTIGRAVITY_PRINT_TIMEOUT:-5m}"

# 1) Explicit override.
ANTIGRAVITY_CLI="${ANTIGRAVITY_CLI:-}"
ANTIGRAVITY_ARGS="${ANTIGRAVITY_ARGS:-}"
if [ -n "$ANTIGRAVITY_CLI" ] && command -v "$ANTIGRAVITY_CLI" >/dev/null 2>&1; then
  echo "[reviewer-c backend: antigravity ($ANTIGRAVITY_CLI)]" >&2
  # shellcheck disable=SC2086
  cat "$PROMPT_FILE" | "$ANTIGRAVITY_CLI" $ANTIGRAVITY_ARGS
  exit $?
fi

# 2) Official Antigravity CLI `agy` (auto-detected default).
if command -v agy >/dev/null 2>&1; then
  echo "[reviewer-c backend: antigravity (agy --print)]" >&2
  # Stream to stdout AND tee to a temp file, instead of capturing into a variable.
  # Why: agy can be slow on agentic prompts; if an OUTER `timeout` kills it, a
  # variable-capture loses everything (0-byte output), whereas streaming preserves
  # the partial answer. The temp copy is only for the auth-failure check.
  tmp="$(mktemp)"
  # Feed prompt via STDIN (verified: `agy -p` reads stdin) — avoids ARG_MAX on long prompts.
  # tee preserves partial output if an outer `timeout` kills agy. PIPESTATUS[0] = agy's rc.
  agy -p --print-timeout "$PRINT_TIMEOUT" --dangerously-skip-permissions < "$PROMPT_FILE" 2>&1 | tee "$tmp"
  rc=${PIPESTATUS[0]}
  if grep -qi "Authentication required\|authentication timed out" "$tmp"; then
    echo "ERROR: agy needs login — run \`agy -p \"hi\"\` once and complete Google OAuth, then retry." >&2
    rm -f "$tmp"; exit 3
  fi
  rm -f "$tmp"; exit "$rc"
fi

# 3) Nothing available.
echo "ERROR: reviewer C unavailable — install Antigravity CLI (agy) or set ANTIGRAVITY_CLI. (cursor-agent fallback removed; framework standardizes on claude/codex/agy.)" >&2
exit 127
