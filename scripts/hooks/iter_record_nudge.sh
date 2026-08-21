#!/usr/bin/env bash
# PostToolUse(Write|Edit) hook: when a run report reports/<id>.json is written,
# nudge to record the iteration — closes the gap where /pursue's autonomous
# rounds produced runs but forgot to update docs/04+05+06.
# stdin parsed via python3 (no jq). Injects advisory via additionalContext.
set -uo pipefail
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
  *ACTIVE_GOAL.json)
    # Goalpost-move guard: ACTIVE_GOAL changes should go through /revise-goal
    # (propose diff → tri-review comparability → human confirm), not a silent edit.
    python3 - <<'PY'
import json
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
  "additionalContext": ("⚖️ ACTIVE_GOAL.json 刚被写。若改动了 success_criteria / sota_benchmark / "
    "screen_anchor（= 移动球门），应经 /revise-goal（提议 diff → tri-review 复核可比性 → 人确认），"
    "不要直接改；只有 /configure-project 初次填充或 /ingest-existing 草案属正常。validate_goal 以本文件为准。")}}))
PY
    ;;
  */reports/*.json)
    id=$(basename "$fp" .json)
    gate_json=""
    if [ -f scripts/note_gate.py ]; then
      gate_json=$(python3 scripts/note_gate.py --report "$fp" 2>/dev/null | head -c 2000 || true)
    fi
    python3 - "$id" "$gate_json" <<'PY'
import json, sys
eid = sys.argv[1]
gate = sys.argv[2] if len(sys.argv) > 2 else ""
msg = (f"📊 reports/{eid}.json 刚写入（一次 run 完成）。下一步：(1) /result-log "
       f"先验语义成功，同步 docs/06+04+05；(2) /note-gate 记录指标/失败原因/投稿证据到 docs/15，必要时同步 docs/11/14；"
       f"(3) /exp-log 写 docs/experiments/{eid}.md "
       f"(**为什么做/动机** + 思路/架构/数据/结果/父实验/触发来源) 并刷新 docs/experiments/ATLAS.md 分类总览。"
       f"否则自主多轮会丢记录。随时 `python3 scripts/iter_ledger.py` 对账自查。")
if gate:
    msg += "\n\nnote_gate.py 初步路由建议（agent 仍需正式落盘）：\n" + gate
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
      "additionalContext": msg}}))
PY
    ;;
  */configs/*.yaml|configs/*.yaml|*/sbatch/*.sbatch|sbatch/*.sbatch|*/pipelines/*|pipelines/*)
    python3 - "$fp" <<'PY'
import json, sys
fp = sys.argv[1]
msg = ("🧪 训练/流程配置或提交脚本刚被修改：若下一步会启动真实 run，"
       "请先跑 /code-review-gate（Codex 用 $code-review-gate），"
       "把 label/metric/split/output path/evaluator schema 审查写入 docs/21_code_review_log.md；"
       "BLOCKED 未修不得进入 /smart-sbatch。涉及 evaluator 时同步 docs/19_evaluator_contract.md。"
       f"\nChanged path: {fp}")
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
      "additionalContext": msg}}))
PY
    ;;
esac
exit 0
