#!/usr/bin/env bash
# job_watch.sh — detect that a submitted job actually finished, stalled, or failed.
#
# Fixes the other half of "the agent didn't notice the run failed": after
# smart-sbatch submits, /pursue calls this to PASSIVELY reconcile the job's real
# state from Slurm (sacct/squeue), not from the agent's assumption. Lightweight
# port of Research OS TaskReconciler.
#
# Writes a STATUS file that validate_goal.py reads via --run-status:
#   COMPLETED | FAILED | TIMEOUT | OOM | CANCELLED | RUNNING | STALE | UNKNOWN
#
# Usage:
#   scripts/job_watch.sh --jobid <slurm_jobid> --status-out outputs/<exp>/STATUS [--log <err.log>]
#   scripts/job_watch.sh --jobid 12345 --status-out STATUS --poll 60 --max-wait 86400   # block until terminal
#
# With no Slurm (local machine), falls back to a sentinel/log heuristic so the
# pipeline still produces a STATUS instead of silently assuming success.
set -uo pipefail
JOBID="" OUT="STATUS" LOG="" POLL=0 MAXWAIT=0
while [ $# -gt 0 ]; do case "$1" in
  --jobid) JOBID="$2"; shift 2;; --status-out) OUT="$2"; shift 2;;
  --log) LOG="$2"; shift 2;; --poll) POLL="$2"; shift 2;; --max-wait) MAXWAIT="$2"; shift 2;;
  *) shift;; esac; done

# --- submission mode: a remote_ssh install has NO local Slurm but the real job
#     runs on a remote cluster — reconcile THERE via `ssh <host> sacct/squeue`,
#     not the local box (which would always fall through to UNKNOWN). Reads the
#     real cluster_config.yaml if present; absent/on_cluster/local_direct leave
#     RCMD empty => original local behavior, unchanged. ---
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
CFG="$ROOT/cluster_config.yaml"
SUB_MODE="" SSH_HOST="" RCMD=""
if [ -f "$CFG" ]; then
  sub_block=$(sed -n '/^submission:/,/^[^[:space:]#]/p' "$CFG")
  SUB_MODE=$(printf '%s\n' "$sub_block" | grep -E '^[[:space:]]+mode:' | head -1 | sed -E 's/.*mode:[[:space:]]*//; s/[[:space:]]*#.*//; s/[[:space:]"'\'']*$//')
  SSH_HOST=$(printf '%s\n' "$sub_block" | grep -E '^[[:space:]]+ssh_host:' | head -1 | sed -E 's/.*ssh_host:[[:space:]]*//; s/[[:space:]]*#.*//; s/["'\'' ]//g')
fi
[ "$SUB_MODE" = "remote_ssh" ] && [ -n "$SSH_HOST" ] && RCMD="ssh $SSH_HOST"

# Remote (RCMD set) counts as having Slurm — the cluster does, even if we don't.
have_slurm() { [ -n "$RCMD" ] || command -v sacct >/dev/null 2>&1 || command -v squeue >/dev/null 2>&1; }

# Map raw slurm state -> our STATUS vocabulary; inspect log for OOM refinement.
classify_state() {
  local st="$1"
  case "$st" in
    COMPLETED) echo COMPLETED;;
    TIMEOUT) echo TIMEOUT;;
    OUT_OF_ME*|OUT_OF_MEMORY) echo OOM;;
    CANCELLED*) echo CANCELLED;;
    FAILED|NODE_FAIL|BOOT_FAIL|DEADLINE|PREEMPTED) echo FAILED;;
    RUNNING|PENDING|COMPLETING|CONFIGURING|REQUEUED|RESIZING) echo RUNNING;;
    *) echo UNKNOWN;;
  esac
}

probe_once() {
  local raw=""
  [ -z "$JOBID" ] && { echo ""; return; }
  if [ -n "$RCMD" ]; then
    # remote_ssh: reconcile on the remote cluster
    raw=$($RCMD "sacct -j $JOBID -n -X -o State" 2>/dev/null | head -1 | tr -d ' ')
    if [ -z "$raw" ]; then
      raw=$($RCMD "squeue -j $JOBID -h -o %T" 2>/dev/null | head -1 | tr -d ' ')
      [ -z "$raw" ] && raw="COMPLETED"   # not in remote queue + sacct empty → likely finished
    fi
  else
    if command -v sacct >/dev/null 2>&1; then
      raw=$(sacct -j "$JOBID" -n -X -o State 2>/dev/null | head -1 | tr -d ' ')
    fi
    if [ -z "$raw" ] && command -v squeue >/dev/null 2>&1; then
      raw=$(squeue -j "$JOBID" -h -o "%T" 2>/dev/null | head -1 | tr -d ' ')
      [ -z "$raw" ] && raw="COMPLETED"   # not in queue + sacct empty → likely finished; refine via log below
    fi
  fi
  echo "$raw"
}

decide() {
  local status="$1"
  # refine FAILED/UNKNOWN with log signature (OOM/timeout hide in logs)
  if [ -n "$LOG" ] && [ -f "$LOG" ]; then
    if grep -qiE "CUDA out of memory|OutOfMemoryError" "$LOG"; then status=OOM; fi
    if grep -qiE "DUE TO TIME LIMIT" "$LOG"; then status=TIMEOUT; fi
  fi
  echo "$status"
}

if ! have_slurm; then
  # local_direct fallback: rely on a sentinel/log, never assume success silently.
  # BUT the canonical training template (CLAUDE §13) itself writes
  # `echo COMPLETED > outputs/<exp>/STATUS` on success, and a finished run leaves
  # reports/<exp>.json. Respect those FIRST so a genuinely successful local run is
  # not overwritten with UNKNOWN (which validate_goal would read as failed_run).
  if [ -f "$OUT" ] && grep -qiE '^[[:space:]]*COMPLETED' "$OUT" 2>/dev/null; then
    echo "[job_watch] no Slurm → STATUS already COMPLETED (template sentinel), kept"; exit 0
  fi
  eid_guess=$(basename "$(dirname "$OUT")" 2>/dev/null)
  if [ -n "$eid_guess" ] && [ -f "$ROOT/reports/$eid_guess.json" ]; then
    echo COMPLETED > "$OUT"
    echo "[job_watch] no Slurm → reports/$eid_guess.json exists → wrote COMPLETED to $OUT"; exit 0
  fi
  if [ -n "$LOG" ] && [ -f "$LOG" ]; then
    if grep -qiE "CUDA out of memory" "$LOG"; then echo OOM > "$OUT";
    elif grep -qiE "Traceback|Error|Exception" "$LOG"; then echo FAILED > "$OUT";
    else echo "UNKNOWN(no-slurm; inspect log)" > "$OUT"; fi
  else
    echo "UNKNOWN(no-slurm; no log)" > "$OUT"
  fi
  echo "[job_watch] no Slurm here → wrote '$(cat "$OUT")' to $OUT (do not assume success)"; exit 0
fi

# Slurm present:
if [ "$POLL" -gt 0 ]; then
  waited=0
  while :; do
    raw=$(probe_once); status=$(classify_state "$raw")
    if [ "$status" != "RUNNING" ]; then break; fi
    sleep "$POLL"; waited=$((waited+POLL))
    if [ "$MAXWAIT" -gt 0 ] && [ "$waited" -ge "$MAXWAIT" ]; then status=STALE; break; fi
  done
else
  raw=$(probe_once); status=$(classify_state "$raw")
fi
status=$(decide "$status")
echo "$status" > "$OUT"
echo "[job_watch] job=$JOBID raw='$raw' -> STATUS=$status (wrote $OUT)"
[ "$status" = "COMPLETED" ] && exit 0 || exit 1
