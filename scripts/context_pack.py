#!/usr/bin/env python3
"""context_pack.py — deterministic context rebuilder (B1).

Root-cause fix for "autonomous iteration loses context": instead of trusting the
LLM to remember across rounds or self-summarize after a compaction, rebuild a
self-contained "resume brief" DETERMINISTICALLY from disk every round.

Merges three ideas: pi-autoresearch compaction-rehydrate (lossless from disk),
ARIS research_wiki query_pack (budgeted summary), Research-OS context assembler
(priority blocks + staleness + next-files pointers).

Usage:
  python3 scripts/context_pack.py --purpose iterate|tri-review|pivot|plan \
      [--max-chars 8000] [--query "..."] [root]

Output: a markdown Research Context Pack on stdout. Pure stdlib, never edits.
Blocks are filled in priority order within the char budget; an over-budget or
dropped block is noted and its full path listed under next_files_to_open_if_needed.
Absent sources are marked (absent). Each block shows its source-file age.
"""
import os, re, sys, time, json, argparse, glob


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def age_str(path):
    try:
        return f"{(time.time() - os.path.getmtime(path)) / 86400:.1f}d old"
    except OSError:
        return "?"


def tail_sections(text, pat, n):
    """Last n sections; a section spans from a header matching pat to the next such header."""
    if not text:
        return None
    ms = list(re.finditer(pat, text, re.M))
    if not ms:
        return None
    out = []
    for k in range(max(0, len(ms) - n), len(ms)):
        s = ms[k].start()
        e = ms[k + 1].start() if k + 1 < len(ms) else len(text)
        out.append(text[s:e].strip())
    return "\n\n".join(out)


def sections_by_header(text, pat):
    """Return (match, section_text) pairs for headers matching pat."""
    if not text:
        return []
    ms = list(re.finditer(pat, text, re.M))
    out = []
    for i, m in enumerate(ms):
        s = m.start()
        e = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        out.append((m, text[s:e].strip()))
    return out


def exp_rank(exp_id):
    """Project-local ordering for experiment ids; unknown ids sort last by text."""
    if not exp_id:
        return (-1, -1, exp_id or "")
    m = re.search(r"EXP-([A-Z]+|M\d+)-(\d+)", exp_id)
    if not m:
        return (-1, -1, exp_id)
    family, num = m.group(1), int(m.group(2))
    fam_rank = {"M1": 0, "A": 1, "B": 2}.get(family, 9)
    return (fam_rank, num, exp_id)


def latest_n_result_sections(root, n=3):
    t = read(os.path.join(root, "docs", "06_results_log.md"))
    sections = []
    for m, sec in sections_by_header(t, r"(?m)^##\s*Result:\s*([A-Za-z0-9_.+-]+)"):
        exp_id = m.group(1)
        # Prefer formal runs over smoke when ranking, but keep smoke if it is all we have.
        smoke_penalty = -1 if exp_id.endswith("-smoke") else 0
        sections.append((exp_rank(exp_id), smoke_penalty, sec))
    if not sections:
        return None
    sections.sort(key=lambda x: (x[0], x[1]))
    return "\n\n".join(sec for _, _, sec in sections[-n:])


def latest_iter(root):
    t = read(os.path.join(root, "docs", "04_experiment_iterations.md"))
    sections = []
    for m, sec in sections_by_header(t, r"(?m)^##\s*ITER-(\d+)([A-Z]?)\b"):
        sections.append((int(m.group(1)), m.group(2), sec))
    if not sections:
        return None
    sections.sort(key=lambda x: (x[0], x[1]))
    return sections[-1][2]


def goal_block(root):
    t = read(os.path.join(root, "ACTIVE_GOAL.json"))
    if not t:
        return None
    try:
        d = json.loads(t)
    except Exception:
        return "(ACTIVE_GOAL.json unparseable — fix before /pursue)"
    L = [f"goal: {d.get('goal', '?')}",
         f"scope={d.get('scope', '?')} | status={d.get('status', '?')} | primary_metric={d.get('primary_metric', '?')} ({d.get('direction', '?')})"]
    sc = d.get("success_criteria", [])
    if sc:
        L.append("success_criteria: " + "; ".join(f"{r.get('metric')}{r.get('op')}{r.get('threshold')}" for r in sc))
    sa, so = d.get("screen_anchor") or {}, d.get("sota_benchmark") or {}
    if sa:
        L.append(f"screen_anchor={sa.get('value')} (screen 永不 claim; src: {sa.get('source', '?')})")
    if so:
        L.append(f"sota_benchmark={so.get('value')} (full/scale 才判 claim; src: {so.get('source', '?')})")
    L.append(f"tuning_gap_threshold={d.get('tuning_gap_threshold')} (gap≥此 → 禁调参换架构) | max_parallel_directions={d.get('max_parallel_directions')}")
    if str(d.get("status", "")).lower() == "draft":
        L.append("⚠️ status=draft → validate_goal 拒判 success；填好后改 active。")
    return "\n".join(L)


def tracker_block(root):
    t = read(os.path.join(root, "docs", "05_todo.md"))
    if t is None:
        return None
    rows = [ln for ln in t.splitlines()
            if ln.startswith("|") and re.search(r"\|\s*(RUNNING|FAILED|STALE|TODO)\s*\|", ln)]
    out = []
    if rows:
        out.append("Open runs:\n" + "\n".join(rows))
    tracked_ids = set(re.findall(r"^\|\s*(EXP-[^|\s]+)\s*\|", t, re.M))
    status_rows = []
    for st_path in sorted(glob.glob(os.path.join(root, "outputs", "*", "STATUS"))):
        exp_id = os.path.basename(os.path.dirname(st_path))
        status = (read(st_path) or "").strip().splitlines()[0:1]
        status = status[0] if status else "UNKNOWN"
        if status.upper() in {"RUNNING", "FAILED", "STALE", "TIMEOUT", "OOM", "UNKNOWN"}:
            flag = "not in docs/05 tracker" if exp_id not in tracked_ids else "tracker present"
            status_rows.append(f"- {exp_id}: STATUS={status} ({flag})")
    if status_rows:
        out.append("Open/noncompleted STATUS files on disk:\n" + "\n".join(status_rows[:12]))
    m = re.search(r"## Pending integration queue(.*?)(?:\n## |\Z)", t, re.S)
    if m:
        items = [l for l in m.group(1).splitlines() if l.strip().startswith("- [ ]") and "占位" not in l]
        if items:
            out.append("Pending integration:\n" + "\n".join(items))
    return "\n".join(out) if out else "(no open runs / pending)"


def findings_block(root):
    t = read(os.path.join(root, "docs", "10_findings.md"))
    if t is None:
        return None
    out = []
    for hdr in ("Research Findings", "Engineering Findings"):
        m = re.search(rf"## {hdr}(.*?)(?:\n## |\n---|\Z)", t, re.S)
        if m:
            bs = [l for l in m.group(1).splitlines() if l.strip().startswith("- ") and "(空)" not in l]
            if bs:
                out.append(f"{hdr}:\n" + "\n".join(bs))
    return "\n".join(out) if out else "(no findings)"


def ideas_block(root):
    fs = sorted(glob.glob(os.path.join(root, "wiki", "ideas", "*.md")))
    if not fs:
        return None
    L = []
    for f in fs[:8]:
        first = read(f) or ""
        title = next((l for l in first.splitlines() if l.strip()), os.path.basename(f))
        L.append(f"- {os.path.basename(f)}: {title.lstrip('# ').strip()[:80]}")
    return "\n".join(L)


def head_doc(path):
    def _f(root):
        t = read(os.path.join(root, *path))
        return t.strip() if t else None
    return _f


def latest_pivot(root):
    """Return the latest pivot by experiment id, not file position.

    docs/08 was repaired across sessions and is not strictly append-ordered, so
    file tail is unsafe after compaction.
    """
    t = read(os.path.join(root, "docs", "08_pivot_decisions.md"))
    sections = []
    for m, sec in sections_by_header(t, r"(?m)^#\s*Pivot Decision:\s*(.+)$"):
        label = m.group(1).strip()
        ids = re.findall(r"EXP-[A-Za-z0-9_.+-]+", label)
        rank = max((exp_rank(x) for x in ids), default=(-1, -1, label))
        sections.append((rank, sec))
    if not sections:
        return None
    sections.sort(key=lambda x: x[0])
    return sections[-1][1]


# key, title, purposes, fn, per-block budget, source-path-parts
BLOCKS = [
    ("master", "Master plan / user navigation", {"iterate", "tri-review", "pivot", "plan"},
     head_doc(("docs", "11_master_plan.md")), 1200, ("docs", "11_master_plan.md")),
    ("goal", "Active goal contract", {"iterate", "tri-review", "pivot", "plan"}, goal_block, 950, ("ACTIVE_GOAL.json",)),
    ("results", "Recent results (trend, not one point)", {"iterate", "tri-review", "pivot"},
     latest_n_result_sections, 1800, ("docs", "06_results_log.md")),
    ("iter", "Latest iteration", {"iterate", "pivot"},
     latest_iter, 1200, ("docs", "04_experiment_iterations.md")),
    ("pivot", "Latest pivot decision", {"iterate", "tri-review", "pivot"},
     latest_pivot, 900, ("docs", "08_pivot_decisions.md")),
    ("abandoned", "Abandoned routes — DO NOT retry", {"iterate", "tri-review", "pivot", "plan"},
     head_doc(("docs", "09_decisions_log.md")), 1000, ("docs", "09_decisions_log.md")),
    ("sota", "SOTA target & comparability contract", {"tri-review", "pivot", "plan"},
     head_doc(("docs", "03_benchmark_roadmap.md")), 1400, ("docs", "03_benchmark_roadmap.md")),
    ("evaluator", "Evaluator contract / metric truth source", {"iterate", "tri-review", "pivot", "plan"},
     head_doc(("docs", "19_evaluator_contract.md")), 800, ("docs", "19_evaluator_contract.md")),
    ("baseline_repro", "Baseline reproduction ledger", {"iterate", "tri-review", "pivot", "plan"},
     head_doc(("docs", "20_baseline_reproduction.md")), 800, ("docs", "20_baseline_reproduction.md")),
    ("code_review", "Code review gate log", {"iterate", "tri-review", "plan"},
     head_doc(("docs", "21_code_review_log.md")), 650, ("docs", "21_code_review_log.md")),
    ("findings", "Findings (avoid re-stepping)", {"iterate", "tri-review", "pivot", "plan"}, findings_block, 1400, ("docs", "10_findings.md")),
    ("tracker", "Run tracker & pending integration", {"iterate", "plan"}, tracker_block, 800, ("docs", "05_todo.md")),
    ("gaps", "Open gaps / conflicts", {"plan"}, head_doc(("docs", "01_literature_review.md")), 1200, ("docs", "01_literature_review.md")),
    ("publication", "Publication strategy / validation burden", {"iterate", "tri-review", "pivot", "plan"},
     head_doc(("docs", "12_publication_strategy.md")), 900, ("docs", "12_publication_strategy.md")),
    ("pipeline", "Pipeline blueprint / IO contracts", {"iterate", "plan"},
     head_doc(("docs", "13_pipeline_blueprint.md")), 900, ("docs", "13_pipeline_blueprint.md")),
    ("validation", "Validation matrix / downstream tasks", {"iterate", "tri-review", "pivot", "plan"},
     head_doc(("docs", "14_validation_matrix.md")), 900, ("docs", "14_validation_matrix.md")),
    ("evidence", "Evidence register / capture status", {"iterate", "plan"},
     head_doc(("docs", "15_evidence_register.md")), 700, ("docs", "15_evidence_register.md")),
    ("workspace", "Parallel workspace / optional worktrees", {"iterate", "plan"},
     head_doc(("docs", "17_parallel_workspace.md")), 650, ("docs", "17_parallel_workspace.md")),
    ("runtime", "Runtime playbook / migration + cluster rules", {"plan"},
     head_doc(("docs", "18_runtime_playbook.md")), 650, ("docs", "18_runtime_playbook.md")),
    ("upgrade", "Framework upgrade log", {"plan"},
     head_doc(("docs", "22_upgrade_log.md")), 650, ("docs", "22_upgrade_log.md")),
    ("review_board", "Review board audit log", {"iterate", "tri-review", "pivot", "plan"},
     head_doc(("docs", "23_review_board.md")), 700, ("docs", "23_review_board.md")),
    ("sprint_pursue", "Sprint and capability-pursue ledger", {"iterate", "tri-review", "pivot", "plan"},
     head_doc(("docs", "24_sprint_pursue_ledger.md")), 900, ("docs", "24_sprint_pursue_ledger.md")),
    ("ideas", "Unconsumed ideas (next directions)", {"iterate", "plan"}, ideas_block, 700, ("wiki", "ideas")),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--purpose", default="iterate", choices=["iterate", "tri-review", "pivot", "plan"])
    ap.add_argument("--max-chars", type=int, default=8000)
    ap.add_argument("--query", default=None)
    ap.add_argument("root", nargs="?", default=os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    args = ap.parse_args()
    root, purpose = args.root, args.purpose

    sections, next_files = [], []
    remaining = args.max_chars
    for key, title, purposes, fn, budget, pp in BLOCKS:
        if purpose not in purposes:
            continue
        path = os.path.join(root, *pp)
        try:
            content = fn(root)
        except Exception as e:
            content = f"(error reading: {e})"
        if content is None or content == "":
            sections.append(f"## {title}\n(absent)")
            continue
        content = content.strip()
        avail = min(budget, remaining)
        if avail < 200:
            sections.append(f"## {title}\n(omitted for budget — open {path})")
            next_files.append(path)
            continue
        if len(content) > avail:
            content = content[:avail].rstrip() + f"\n…(truncated, full: {path})"
            next_files.append(path)
        remaining -= len(content)
        sections.append(f"## {title}  ({age_str(path)})\n{content}")

    print(f"# Research Context Pack — purpose={purpose} (deterministic rebuild from disk)")
    print("> 脚本从磁盘 lossless 重建的续跑背景。对话历史可能已压缩——**以本 pack + 引用文件为唯一权威背景**，不要靠记忆。")
    if args.query:
        print(f"> focus query: {args.query}")
    print()
    print("\n\n".join(sections))
    if next_files:
        print("\n## next_files_to_open_if_needed")
        for p in dict.fromkeys(next_files):
            print(f"- {p}")


if __name__ == "__main__":
    main()
