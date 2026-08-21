#!/usr/bin/env python3
"""Deterministic helper for /note-gate.

It extracts obvious durable evidence from a report JSON or free-text stdin and
prints a conservative routing suggestion. The skill/agent performs final writes.
"""
from __future__ import annotations
import argparse, json, os, re, sys
from pathlib import Path

ROUTES = {
    "metric": "docs/06_results_log.md; docs/14_validation_matrix.md if publication-relevant; docs/15_evidence_register.md",
    "failure_reason": "docs/10_findings.md; docs/06_results_log.md; docs/15_evidence_register.md",
    "discussion_decision": "docs/11_master_plan.md (§3 已确定 / §4 待议分支); docs/15_evidence_register.md",
    "user_preference": "docs/11_master_plan.md (§3); docs/12_publication_strategy.md if venue/contribution; docs/15_evidence_register.md",
    "insight": "docs/10_findings.md; wiki/notes; docs/15_evidence_register.md",
    "artifact_path": "docs/16_artifact_registry.md; docs/21_code_review_log.md if pre-submit review; docs/15_evidence_register.md",
    "evaluator_contract": "docs/19_evaluator_contract.md; docs/15_evidence_register.md",
    "baseline_reproduction": "docs/20_baseline_reproduction.md; refs/dossiers; docs/15_evidence_register.md",
    "code_review": "docs/21_code_review_log.md; docs/15_evidence_register.md",
    "framework_upgrade": "docs/22_upgrade_log.md; docs/15_evidence_register.md",
    "review_board": "docs/23_review_board.md; docs/15_evidence_register.md",
    "sprint_pursue": "docs/24_sprint_pursue_ledger.md; docs/15_evidence_register.md",
    "paper": "/note-add kind=paper → refs/; docs/01; docs/05",
    "idea": "/note-add kind=idea → wiki/ideas; docs/15",
    "pipeline_output": "docs/13_pipeline_blueprint.md; software_outputs/ manifest; docs/15",
}

# Types that are durable by nature (a discussion conclusion / preference / insight
# must not die in chat). If inferred, they are recorded even at score 1.
DURABLE_DISCUSSION = {"discussion_decision", "user_preference", "insight"}


def score_candidate(text: str) -> int:
    score = 0
    # Numeric metrics / seed information should almost always be durable.
    if re.search(r"\b(seed|metric|accuracy|f1|auc|auprc|loss|mean|std|p-value|ci)\b|[A-Za-z0-9_-]+\s*=\s*[-+]?[0-9.]+|seed\s*[=:]\s*\d+", text, re.I):
        score += 1
    # User decisions in Chinese often do not satisfy ASCII word-boundary rules, so keep these separate.
    if re.search(r"\b(decision|choose|support|oppose|prefer)\b|用户|选择|支持|反对|确定|赞成|否决|保留|继续讨论", text, re.I):
        score += 1
    if re.search(r"\b(error|failed|oom|timeout|nan|leak|bug)\b|失败|泄漏|报错|错误|超时|显存|崩溃", text, re.I):
        score += 1
    if re.search(r"\b(sota|benchmark|split|dataset|baseline|claim|figure|table)\b|投稿|图表|下游|泛化|验证|基线", text, re.I):
        score += 1
    if re.search(r"(reports/|runs/|outputs/|software_outputs/|refs/|https?://|doi|arxiv|EXP-[A-Z]-\d+|SOTA-[A-Za-z0-9_-]+|PIPE-[A-Za-z0-9_-]+)", text, re.I):
        score += 1
    return score


def infer_types(text: str) -> list[str]:
    types: list[str] = []
    if re.search(r"(reports/|metric|accuracy|f1|auc|auprc|loss|mean|std|seed|[A-Za-z0-9_-]+\s*=\s*[-+]?[0-9.]+)", text, re.I):
        types.append("metric")
    if re.search(r"(failed|oom|timeout|nan|bug|error|失败|泄漏|报错|错误|超时|崩溃)", text, re.I):
        types.append("failure_reason")
    # user_preference is more specific than discussion_decision (risk tolerance / target venue / "don't do X")
    if re.search(r"(prefer|risk tolerance|target (journal|venue)|偏好|风险偏好|目标期刊|目标会议|更倾向|希望投|不想做|不做这个方向)", text, re.I):
        types.append("user_preference")
    if re.search(r"(support|oppose|choose|decision|decide|用户|支持|反对|确定|选择|赞成|否决|继续讨论|决定|采用)", text, re.I):
        types.append("discussion_decision")
    # mechanism-level insight (a conclusion from discussion, not a number)
    if re.search(r"(mechanism|because|root cause|hypothesis|insight|机制|根因|原因是|因为|导致|说明了|意味着)", text, re.I):
        types.append("insight")
    # an artifact path: a script/config/output location to register (痛点#6)
    if re.search(r"(scripts/|configs/|sbatch/|software_outputs/|runs/|\.py\b|\.yaml\b|\.sh\b|输出到|存到|放在|output[s]?\s+(to|in|at))", text, re.I):
        types.append("artifact_path")
    if re.search(r"(evaluator contract|metric schema|metrics json schema|primary_metric|评估器|指标合约|可比性合约)", text, re.I):
        types.append("evaluator_contract")
    if re.search(r"(baseline reproduction|reproduce-baselines|reported metric|reproduced metric|复现|基线复现|SOTA 复现)", text, re.I):
        types.append("baseline_reproduction")
    if re.search(r"(code-review-gate|code review gate|docs/21|BLOCKED|WAIVED_BY_USER|代码审查|审前闸)", text, re.I):
        types.append("code_review")
    if re.search(r"(framework upgrade|v3|v4|upgrade log|框架升级|兼容升级|迁移)", text, re.I):
        types.append("framework_upgrade")
    if re.search(r"(review board|review-board|tripartite review|评审板|会诊|独立盲审)", text, re.I):
        types.append("review_board")
    if re.search(r"(sprint|pursue ledger|capability pursue|capability-pursue|短跑|分层推进)", text, re.I):
        types.append("sprint_pursue")
    if re.search(r"(software_outputs|qc gate|pipeline stage|外部软件|流程阶段)", text, re.I):
        types.append("pipeline_output")
    if re.search(r"(arxiv|doi|https?://|github.com)", text, re.I):
        types.append("paper")
    return types or ["idea"]

def from_report(path: Path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return [{"candidate": str(path), "type": "failure_reason", "score": 2, "verdict": "record", "reason": f"report JSON unreadable: {e}"}]
    text = json.dumps(data, ensure_ascii=False)
    score = max(2, score_candidate(text))
    status = str(data.get("status") or data.get("STATUS") or "").lower()
    t = "failure_reason" if any(k in status for k in ("fail", "error", "timeout", "oom", "nan", "stale")) else "metric"
    reason = ("report STATUS indicates failure → route to findings/results" if t == "failure_reason"
              else "report JSON contains metrics/status and must be routed")
    return [{"candidate": str(path), "type": t, "score": score, "verdict": "record",
             "route": ROUTES[t], "reason": reason}]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default="", help="Path to reports/<id>.json")
    ap.add_argument("--text", default="", help="Free text candidate evidence")
    args = ap.parse_args()

    candidates = []
    if args.report:
        candidates.extend(from_report(Path(args.report)))
    text = args.text or (sys.stdin.read() if not sys.stdin.isatty() else "")
    if text.strip():
        s = score_candidate(text)
        types = infer_types(text)
        verdict = "record" if s >= 2 else ("index-only" if s == 1 else "skip")
        reason = "deterministic checklist"
        # Discussion conclusions / user preferences / mechanism insights are durable
        # by nature — never let them drop to index-only/skip (痛点#4: 讨论别死在对话里).
        if set(types) & DURABLE_DISCUSSION and verdict != "record":
            verdict, reason = "record", "durable discussion/preference/insight → always recorded"
        primary = types[0]
        for t in types:
            candidates.append({"candidate": text.strip()[:300], "type": t, "score": s,
                               "verdict": verdict, "primary_type": primary,
                               "also": [x for x in types if x != t] or None,
                               "reason": reason})
    for c in candidates:
        c["route"] = ROUTES.get(c["type"], "docs/15_evidence_register.md")
    print(json.dumps({"candidates": candidates}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
