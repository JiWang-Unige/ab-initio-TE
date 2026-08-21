#!/usr/bin/env bash
# PreCompact hook: compaction is the framework's biggest chat-only-data-loss
# vector — anything discussed but never written to disk is gone after compaction.
# This emits an advisory reminder to flush durable info (/note-gate → docs/15+11,
# /master-plan) BEFORE the transcript is compressed. Non-blocking systemMessage.
# After compaction, SessionStart(compact) → research_bootstrap rebuilds context
# FROM DISK — so only on-disk state survives; this hook nudges you to get it there.
# stdin parsed via python3 (no jq).
set -uo pipefail
input=$(cat 2>/dev/null || true)
trigger=$(printf '%s' "$input" | python3 -c "import sys,json
try: print(json.load(sys.stdin).get('trigger',''))
except Exception: print('')" 2>/dev/null)
python3 - "$trigger" <<'PY'
import json, sys
trg = sys.argv[1] if len(sys.argv) > 1 else ""
msg = (f"🗜️ 即将压缩上下文(trigger={trg or '?'})。压缩只保留摘要——"
       "确保**讨论结论 / 用户偏好 / 决策 / 当前进度**已经 /note-gate 进 docs/15+11、"
       "导航 docs/11_master_plan.md 已更新。**若有 Slurm 作业在跑：确认 job_id 已写 docs/05 tracker + "
       "outputs/<exp>/STATUS=RUNNING**（作业独立于对话、压缩杀不掉它，但 job_id 没落盘就找不回，见 docs/18 §4.1）。"
       "压缩后 SessionStart 从磁盘重建上下文，**没写盘的聊天内容找不回**。")
print(json.dumps({"systemMessage": msg}))
PY
exit 0
