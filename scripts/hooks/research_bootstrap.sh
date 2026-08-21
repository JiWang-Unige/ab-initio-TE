#!/usr/bin/env bash
# SessionStart/SubagentStart hook: inject a compact, deterministic research
# bootstrap so startup/resume/compact/subagent threads do not rely on stale
# conversation memory. Driver-neutral: works for both the Claude shell
# (.claude/ + CLAUDE.md) and the Codex shell (.codex/ + AGENTS.md).
#
# Output contract: a single JSON object on stdout with
#   {"hookSpecificOutput": {"hookEventName": ..., "additionalContext": "..."}}
# additionalContext is injected into the (sub)agent context by the harness.
set -uo pipefail
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$ROOT" 2>/dev/null || exit 0

event="SessionStart"
source="unknown"
agent_type=""
input=$(cat)
read -r event source agent_type <<EOF
$(printf '%s' "$input" | python3 -c "import sys,json
try:
    d=json.load(sys.stdin)
    print(d.get('hook_event_name','SessionStart'), d.get('source','unknown'), d.get('agent_type',''))
except Exception:
    print('SessionStart unknown')" 2>/dev/null)
EOF

pack="$(python3 scripts/context_pack.py --purpose iterate --max-chars 4200 2>/dev/null || true)"

python3 - "$event" "$source" "$agent_type" "$pack" <<'PY'
import json, sys
event, source, agent_type, pack = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
header = "Auto-research bootstrap"
if event == "SubagentStart":
    header = f"Auto-research subagent bootstrap ({agent_type or 'default'})"
rules = f"""# {header}

This is an auto-research workflow (lwcr). The conversation may have been summarized — treat disk state as the authoritative background after startup/resume/compact, not memory.

Mandatory operating rules:
- Before planning or running an iteration, run `python3 scripts/context_pack.py --purpose iterate`; after a compaction, rebuild context from disk rather than relying on recollection.
- Read the active driver instruction file (`CLAUDE.md` for the Claude shell, `AGENTS.md` for the Codex shell), plus `ACTIVE_GOAL.json`, `docs/05_todo.md`, `docs/06_results_log.md`, `docs/08_pivot_decisions.md`, `docs/10_findings.md`, `docs/17_parallel_workspace.md`, `docs/18_runtime_playbook.md`, `docs/19_evaluator_contract.md`, `docs/20_baseline_reproduction.md`, `docs/21_code_review_log.md`, and `docs/22_upgrade_log.md` when more detail is needed.
- Real training runs go through the cluster: use `/smart-sbatch` (allocation-aware) to submit `sbatch`/`srun` jobs — never launch full/scale training as a bare foreground process. (If this install has no Slurm, that is declared in CLAUDE.md §12 and submit_guard will enforce it.)
- After implementation changes, run code-review-gate before smart-sbatch; BLOCKED code review means no real training submission.
- After any real run, close the chain: result-log -> validate_goal.py -> tri-review -> pivot -> docs/04+05+06+10+19+20+21 when relevant -> iter_ledger.py. Never silently continue after a failed/stale run.
- The `screen` profile can NEVER claim SOTA; `full`/`scale` may claim only after strict exceedance + tri-review + the first-run human gate.
- Parallelism: run at most `max_parallel_directions` orthogonal directions per round. Default isolation is `exp_id` directories; if parallel directions need shared-code edits, use `/workspace-matrix` optional git/worktrees. Each writing subagent owns ONLY its assigned `exp_id`/worktree scope.
- A subagent stays bounded and read-only unless the parent explicitly assigns an isolated write scope; subagents do not spawn subagents.

Current deterministic context (rebuilt from disk):

{pack}
"""
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": event,
        "additionalContext": rules
    }
}))
PY
