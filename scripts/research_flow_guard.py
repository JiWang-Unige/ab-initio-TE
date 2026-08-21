#!/usr/bin/env python3
"""Advisory stage-order guard for the auto-research workflow.

Purpose: prevent the common drift where the agent jumps from /sota-inventory
straight to /benchmark-roadmap or /goal-prompt, skipping /grill,
/configure-project, SOTA local reproduction, or screen-anchor construction.

It never edits files; hooks can surface its JSON/Markdown output as a nudge.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def placeholder_heavy(text: str) -> bool:
    if not text:
        return True
    hits = len(re.findall(r"<[^>]{1,80}>|TODO|待填|未建立|status\s*[:=]\s*draft", text, re.I))
    return hits >= 5


def has_candidate_inventory(txt: str) -> bool:
    if not re.search(r"(?m)^## Candidate models", txt):
        return False
    in_sec = False
    for line in txt.splitlines():
        if line.startswith("## Candidate models"):
            in_sec = True
            continue
        if in_sec and line.startswith("## "):
            break
        if in_sec and line.strip().startswith("|"):
            low = line.lower()
            if "model | paper" in low or re.match(r"^\|\s*-+", line.strip()):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells and cells[0] and "<" not in cells[0]:
                return True
    return False


def has_verified_refs(root: Path) -> bool:
    return any((root / "refs" / "dossiers").glob("*.md")) or any((root / "refs" / "pdfs").glob("*.pdf"))


def has_grill_marker(root: Path) -> bool:
    blobs = "\n".join(read(root / f) for f in ["docs/00_active_goal.md", "docs/11_master_plan.md", "docs/15_evidence_register.md"])
    return bool(re.search(r"direction_clarified|grill|拷问|council|辩论|foundation.*locked", blobs, re.I))


def has_configured(root: Path) -> bool:
    claude = read(root / "CLAUDE.md")
    goal = read(root / "ACTIVE_GOAL.json")
    cluster = read(root / "cluster_config.yaml")
    return (not placeholder_heavy(claude[:9000])) and ("draft" not in goal.lower()) and bool(cluster.strip())


def has_roadmap(root: Path) -> bool:
    txt = read(root / "docs/03_benchmark_roadmap.md")
    return "Path 1:" in txt and not placeholder_heavy(txt)


def explicit_reproduce_waiver(txt: str) -> bool:
    """Recognize only intentional waivers, not template prose mentioning the token."""
    return bool(re.search(r'(?im)^\s*(?:[-*]\s*)?"?reproduce_waived"?\s*[:=]\s*\S', txt))


def has_reproduction_ledger_entry(txt: str) -> bool:
    if re.search(r"(?m)^##\s+Baseline Reproduction Report:\s*(?!<).+\S", txt):
        return True
    in_runs = False
    for line in txt.splitlines():
        if line.startswith("## 1. Reproduction Runs"):
            in_runs = True
            continue
        if in_runs and line.startswith("## "):
            break
        if not in_runs or not line.strip().startswith("|"):
            continue
        low = line.lower()
        if " id |" in low or re.match(r"^\|\s*-+", line.strip()):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 10:
            continue
        entry_id, model, report_path, verdict = cells[0], cells[2], cells[8], cells[9]
        if all(x and "<" not in x for x in [entry_id, model, report_path, verdict]):
            return True
    return False


def has_baseline_repro(root: Path) -> bool:
    docs20 = read(root / "docs/20_baseline_reproduction.md")
    results = read(root / "docs/06_results_log.md")
    waiver_scope = read(root / "docs/03_benchmark_roadmap.md") + "\n" + read(root / "ACTIVE_GOAL.json")
    return (
        has_reproduction_ledger_entry(docs20)
        or has_reproduction_ledger_entry(results)
        or explicit_reproduce_waiver(waiver_scope)
    )


def table_value(txt: str, field: str) -> str:
    pattern = r"(?m)^\|\s*" + re.escape(field) + r"\s*\|\s*([^|]+?)\s*\|"
    m = re.search(pattern, txt)
    return m.group(1).strip() if m else ""


def chosen_value(value: str) -> bool:
    if not value or "<" in value:
        return False
    if "/" in value and " or " not in value.lower():
        return False
    return True


def has_dataset_contract_row(txt: str) -> bool:
    in_sec = False
    for line in txt.splitlines():
        if line.startswith("## 3. Dataset And Split Contract"):
            in_sec = True
            continue
        if in_sec and line.startswith("## "):
            break
        if not in_sec or not line.strip().startswith("|"):
            continue
        low = line.lower()
        if "dataset | version" in low or re.match(r"^\|\s*-+", line.strip()):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 5 and all(c and "<" not in c for c in cells[:4]):
            return True
    return False


def has_evaluator_contract(root: Path) -> bool:
    txt = read(root / "docs/19_evaluator_contract.md")
    if not txt:
        return False
    status = table_value(txt, "- Status")
    if not status:
        m = re.search(r"(?im)^\s*-\s*Status:\s*(.+?)\s*$", txt)
        status = m.group(1).strip() if m else ""
    if not status or re.search(r"\b(draft|incomplete|todo|待填)\b", status, re.I):
        return False
    metric_name = table_value(txt, "Metric name")
    direction = table_value(txt, "Direction")
    granularity = table_value(txt, "Prediction granularity")
    label_mapping = table_value(txt, "Positive class / label mapping")
    our_evaluator = re.search(r"(?m)^\|\s*Our evaluator script\s*\|\s*([^|]+?)\s*\|", txt)
    our_evaluator_path = our_evaluator.group(1).strip() if our_evaluator else ""
    schema_ready = all(x in txt for x in ['"exp_id"', '"primary_metric"', '"semantic_success"'])
    return (
        chosen_value(metric_name)
        and direction in {"higher_is_better", "lower_is_better"}
        and chosen_value(granularity)
        and chosen_value(label_mapping)
        and bool(our_evaluator_path and "<" not in our_evaluator_path)
        and has_dataset_contract_row(txt)
        and schema_ready
    )


def has_screen_anchor(root: Path) -> bool:
    goal_txt = read(root / "ACTIVE_GOAL.json")
    try:
        g = json.loads(goal_txt)
        sa = g.get("screen_anchor") or {}
        value = sa.get("value")
        source = str(sa.get("source") or "")
        metric = str(sa.get("metric") or "")
        if value not in (None, 0, 0.0, "0", "0.0") and "<" not in source + metric:
            return True
    except Exception:
        pass
    docs14 = read(root / "docs/14_validation_matrix.md")
    for line in docs14.splitlines():
        low = line.lower()
        if line.strip().startswith("|") and ("sota-" in low or "screen_anchor" in low or "exp-" in low):
            if any(x in low for x in ["done", "complete", "✅", "mean±std", "mean+-std"]):
                if "status" not in low and "model" not in low:
                    return True
    return False


def compute(root: Path):
    inv = read(root / "docs/02_sota_model_inventory.md")
    out = {"ok_to_goal": False, "recommended_next": [], "blockers": [], "warnings": [], "facts": {}}
    out["facts"] = {
        "candidate_inventory": has_candidate_inventory(inv),
        "verified_refs": has_verified_refs(root),
        "grill_or_council_marker": has_grill_marker(root),
        "configured": has_configured(root),
        "roadmap_ready": has_roadmap(root),
        "evaluator_contract_ready": has_evaluator_contract(root),
        "baseline_reproduced_or_waived": has_baseline_repro(root),
        "screen_anchor_present": has_screen_anchor(root),
    }
    f = out["facts"]

    if not f["candidate_inventory"]:
        out["recommended_next"].append("/sota-inventory")
        out["blockers"].append("docs/02 尚无可用 Candidate models；不能进入 benchmark-roadmap。")
        return out
    if not f["verified_refs"]:
        out["recommended_next"].append("/sota-inventory --archive-missing")
        out["blockers"].append("SOTA 表存在但 refs/dossiers 或 refs/pdfs 为空；需要先归档/核实一手证据。")
        return out
    if not f["grill_or_council_marker"]:
        out["recommended_next"].extend(["/grill", "可选 /council（重大争议方向）"])
        out["blockers"].append("完成 SOTA inventory 后应先 grill/council 拷问研究方向，而不是直接 benchmark-roadmap。")
        return out
    if not f["configured"]:
        out["recommended_next"].append("/configure-project")
        out["blockers"].append("方向澄清后应先把 CLAUDE/AGENTS、cluster_config、ACTIVE_GOAL 固化；否则后续命令会依赖模糊上下文。")
        return out
    if not f["roadmap_ready"]:
        out["recommended_next"].append("/benchmark-roadmap")
        out["blockers"].append("尚无完成的 benchmark contract / technical roadmap。")
        return out
    if not f["evaluator_contract_ready"]:
        out["recommended_next"].append("/benchmark-roadmap 更新 docs/19_evaluator_contract.md")
        out["blockers"].append("尚无可用 evaluator_contract；写训练/评估代码前必须固化 primary metric、split、metrics JSON schema。")
        return out
    if not f["screen_anchor_present"]:
        out["recommended_next"].append("/sota-randomized 或 /reproduce-baselines 建 screen_anchor")
        out["warnings"].append("还没有公平小样本 screen_anchor；Track A 可设计但不能公平比较/晋升。")
    if not f["baseline_reproduced_or_waived"]:
        out["recommended_next"].append("/reproduce-baselines")
        out["blockers"].append("写自己模型前必须先本地运行/复现 SOTA 或显式 reproduce_waived；否则指标/数据口径可能错。")
        return out
    out["ok_to_goal"] = True
    if not out["recommended_next"]:
        out["recommended_next"].append("/goal-prompt 或 /pursue")
    return out


# "先想清再动手"类步骤：建议在 plan 模式下跑（只读勘查 + 反复细聊 + 批准后落盘）。
PLAN_WORTHY = ("/grill", "/council", "/configure-project", "/benchmark-roadmap", "/implement")


def markdown(out) -> str:
    lines = ["### Auto-research flow guard"]
    if out["blockers"]:
        lines.append("阻断/强提醒：")
        lines += [f"- {x}" for x in out["blockers"]]
    if out["warnings"]:
        lines.append("警告：")
        lines += [f"- {x}" for x in out["warnings"]]
    nxt = out["recommended_next"]
    lines.append("建议下一步：" + " → ".join(nxt))
    # Plan-mode recommendation when the next step is a "think-first-then-act" step.
    hit = [s for s in PLAN_WORTHY if any(s in n for n in nxt)]
    if hit:
        lines.append("💡 下一步（" + " ".join(hit) + "）属\"先想清再动手\"类——**建议先切 plan 模式**"
                     "（只读勘查 docs/refs + 和用户反复细聊，`ExitPlanMode` 批准后再落盘），比直接动手更稳。")
    lines.append("事实：" + ", ".join(f"{k}={v}" for k, v in out["facts"].items()))
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    ap.add_argument("--format", choices=["json", "markdown"], default="json")
    args = ap.parse_args()
    out = compute(Path(args.root))
    if args.format == "markdown":
        print(markdown(out))
    else:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["ok_to_goal"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
