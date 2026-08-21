#!/usr/bin/env bash
# PreToolUse(Bash) hook: enforce cluster-submission rules deterministically.
#  1) `sbatch`/`srun` on a machine WITHOUT Slurm installed -> DENY (use local
#     run-and-evaluate). Auto-adapts: on a real cluster (sbatch on PATH) it allows.
#  2) Best-effort clobber guard: a training command writing into runs/<exp_id>
#     whose outputs/<exp_id>/STATUS is already COMPLETED -> ASK (protects a
#     finished/parallel run from being silently overwritten).
#  3) baobab/HPC srun discipline: on a Slurm LOGIN node, heavy compute not wrapped
#     in srun/sbatch -> ASK (login nodes must not run compute; trivial tasks exempt).
#     Off-cluster (no srun) this never fires. Disable via AUTORESEARCH_SRUN_GUARD=0.
# stdin parsed via python3 (no jq). Emits a PreToolUse permission decision.
set -uo pipefail
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
input=$(cat)
cmd=$(printf '%s' "$input" | python3 -c "import sys,json
try: print(json.load(sys.stdin).get('tool_input',{}).get('command',''))
except Exception: print('')" 2>/dev/null)
[ -z "$cmd" ] && exit 0

# submission.mode (so remote_ssh — which legitimately runs `ssh host '... sbatch ...'`
# from a box WITHOUT local Slurm — is not hard-denied by rule 1). Read real cluster_config.yaml.
SUB_MODE=""
if [ -f "$ROOT/cluster_config.yaml" ]; then
  SUB_MODE=$(sed -n '/^submission:/,/^[^[:space:]#]/p' "$ROOT/cluster_config.yaml" \
    | grep -E '^[[:space:]]+mode:' | head -1 | sed -E 's/.*mode:[[:space:]]*//; s/[[:space:]]*#.*//; s/[[:space:]"'\'']*$//')
fi

emit() { # $1=decision(deny|ask|allow) $2=reason
  python3 - "$1" "$2" <<'PY'
import json, sys
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
      "permissionDecision": sys.argv[1], "permissionDecisionReason": sys.argv[2]}}))
PY
  exit 0
}

# 1) sbatch/srun/sinfo/squeue without Slurm installed -> deny.
# Match shell command positions, not arbitrary prose inside quoted prompts.
# EXCEPTION: submission.mode=remote_ssh legitimately runs `ssh <host> '... sbatch ...'`
# from a local box that has no Slurm — those Slurm verbs run REMOTELY, so don't deny when
# the command invokes ssh. (The inner exp_id still gets the code-review gate in rule 4.)
if printf '%s' "$cmd" | grep -qE '(^|[;&|(\n][[:space:]]*)(sbatch|srun|sinfo|squeue)([[:space:]]|$)'; then
  if ! command -v sbatch >/dev/null 2>&1; then
    if [ "$SUB_MODE" = "remote_ssh" ] && printf '%s' "$cmd" | grep -qE '(^|[[:space:];&|(])ssh[[:space:]]'; then
      : # remote_ssh: Slurm verbs run on the remote cluster via ssh — allow.
    else
      emit deny "🛑 本机无 Slurm（sbatch 不在 PATH），无法本地 sbatch/srun/sinfo/squeue。本地训练用 run-and-evaluate 直接 python（CLAUDE.md §12）；要提交到远程集群请设 cluster_config submission.mode=remote_ssh 并用 \`ssh <host> '... sbatch ...'\`（/smart-sbatch remote 分支）。/smart-sbatch 本地仅做显存/walltime sanity。"
    fi
  fi
fi

# 3) baobab/HPC discipline: on a Slurm LOGIN node (srun present, NOT inside an
#    allocation), heavy compute must go through srun/sbatch. Trivial tasks
#    (downloads, file ops, light framework scripts, inline -c) are exempt -> ASK on slip.
#    Disable with AUTORESEARCH_SRUN_GUARD=0. Never fires off-cluster (no srun on PATH).
if [ "${AUTORESEARCH_SRUN_GUARD:-1}" != "0" ] \
   && command -v srun >/dev/null 2>&1 \
   && [ -z "${SLURM_JOB_ID:-}${SLURM_JOBID:-}" ]; then
  if ! printf '%s' "$cmd" | grep -qE '(^|[;&|(\n][[:space:]]*)(srun|sbatch)([[:space:]]|$)' \
     && printf '%s' "$cmd" | grep -qE '(^|[[:space:];&|(])(python[0-9.]*|torchrun|accelerate|deepspeed|mpirun|Rscript|snakemake|nextflow|make)([[:space:]])|(^|[[:space:];&|(])(bash|sh|\./)[^;&|]*train' \
     && ! printf '%s' "$cmd" | grep -qE 'python[0-9.]*[[:space:]]+-c([[:space:]]|$)' \
     && ! printf '%s' "$cmd" | grep -qE 'scripts/(context_pack|validate_goal|iter_ledger|check_data|repair_advisor|lit_search|build_atlas|build_codex_skills|validate_codex_skills|sync_agents_md|job_watch|research_flow_guard|sota_failure_report|workspace_matrix|artifact_registry|next_evidence_id)\.'; then
    emit ask "🖥️ baobab 规约（登录节点禁跑重计算）：此命令像是在 login 节点直接跑计算。请用 srun 分配后再跑，例如：srun -p <partition> --time=<hh:mm> <你的命令>；批量/长任务用 /smart-sbatch → sbatch。仅下载数据/文件操作/轻量框架脚本可在登录节点直跑——确属轻量可放行；临时关闭：export AUTORESEARCH_SRUN_GUARD=0。"
  fi
fi

# 4) Pre-submit code-review gate: a REAL training submission must carry a PASS
#    /code-review-gate (outputs/<id>/code_review_gate.json). Makes code review a HARD
#    machine gate, not just a nudge — works even Codex-only (Codex reviews its own code
#    in a separate read-only process; see /code-review-gate). Extracts exp_id from
#    sbatch/<id>.sbatch, runs/<id>, configs/<id>. Disable via AUTORESEARCH_REVIEW_GATE=0.
if [ "${AUTORESEARCH_REVIEW_GATE:-1}" != "0" ] && [ -f "$ROOT/scripts/pre_submit_gate.py" ] \
   && printf '%s' "$cmd" | grep -qiE '(^|[;&|(\n][[:space:]]*)(sbatch|srun)([[:space:]]|$)|python[0-9.]*[[:space:]][^|;&]*train|--output[_-]dir'; then
  psg_ids=$(printf '%s' "$cmd" | grep -oE '(runs|configs|sbatch)/[A-Za-z0-9_.-]+' \
            | sed -E 's#^(runs|configs|sbatch)/##; s#\.(sbatch|ya?ml|json)$##' | sort -u)
  for id in $psg_ids; do
    [ -z "$id" ] && continue
    if ! python3 "$ROOT/scripts/pre_submit_gate.py" --exp-id "$id" "$ROOT" >"/tmp/_psg.$$" 2>/dev/null; then
      reason=$(head -c 700 "/tmp/_psg.$$" 2>/dev/null); rm -f "/tmp/_psg.$$"
      emit deny "🛑 提交前代码审未通过（$id）：$reason — **拒绝提交真实训练**。先跑 /code-review-gate（Codex 用 \$code-review-gate）产出 PASS（写 outputs/$id/code_review_gate.json，含 reviewed_files+sha256）。确需跳过必须**机器记录 waive**：写 outputs/$id/code_review_waived.json={\"reason\":\"...\"}（可审计，非口头确认）。整体临时关闭：AUTORESEARCH_REVIEW_GATE=0。"
    fi
    rm -f "/tmp/_psg.$$" 2>/dev/null
  done
fi

# 2) clobber guard — only inspect training-ish commands to avoid false positives on reads
if printf '%s' "$cmd" | grep -qiE 'python[0-9.]*[[:space:]].*train|--output[_-]dir|(^|[;&|(\n][[:space:]]*)(sbatch|srun)([[:space:]]|$)'; then
  ids=$(printf '%s' "$cmd" | grep -oE 'runs/[A-Za-z0-9_.-]+' | sed 's#runs/##' | sort -u)
  for id in $ids; do
    st="$ROOT/outputs/$id/STATUS"
    if [ -f "$st" ]; then
      cur=$(grep -oiE 'COMPLETED|RUNNING|PENDING' "$st" 2>/dev/null | head -1 | tr 'a-z' 'A-Z')
      if [ "$cur" = "RUNNING" ] || [ "$cur" = "PENDING" ]; then
        emit ask "🛑 runs/$id 的 outputs/$id/STATUS=$cur（作业正在跑/排队）。重提交会**覆盖正在运行的训练**（跑崩它 + 浪费算力）。若会话重启后想接管，应先 job_watch 对账而非重提交；确认新方向请换 exp_id。"
      elif [ "$cur" = "COMPLETED" ]; then
        emit ask "⚠️ runs/$id 已有 COMPLETED 结果（outputs/$id/STATUS）。重跑会覆盖已记录的实验。并行推进新方向请换一个 exp_id；确要重跑请确认。"
      fi
    fi
  done
fi
exit 0
