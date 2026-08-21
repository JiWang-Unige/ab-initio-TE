#!/usr/bin/env python3
"""Advisory completeness gate for Stage C (publication / pipeline).

Stage B has deterministic gates (validate_goal/check_data/iter_ledger); Stage C
used to rely purely on agent self-judgment. This closes that gap with a
deterministic *completeness* check (not a quality judge):

  --mode publication : scans docs/14_validation_matrix.md (§1 main / §2 downstream
                       / §5 randomized-SOTA) for data rows missing evidence/run/
                       status, and docs/12_publication_strategy.md readiness
                       checklist for unchecked boxes. Answers "is every claim
                       backed by a concrete run/figure before we submit?"
  --mode pipeline    : scans docs/13_pipeline_blueprint.md stage ledger for stages
                       missing status or QC, so no downstream stage is declared
                       done without its gate.

Advisory by default (exit 0 + report). With --strict, exits 2 when gaps exist so
it can act as a gate (e.g. before claiming submission-ready / before a stage).
Pure stdlib, tolerant markdown parsing — never raises on a malformed table.
"""
from __future__ import annotations
import argparse, os, re, sys
from pathlib import Path

PLACEHOLDER = {"", "todo", "tbd", "-", "—", "n/a", "na", "<run_id>", "..."}


def _section(text: str, header_pat: str) -> list[str]:
    """Lines under the first heading matching header_pat, until the next heading."""
    lines = text.splitlines()
    out, grab = [], False
    for ln in lines:
        if re.match(r"^#{1,6}\s", ln):
            if grab:
                break
            if re.search(header_pat, ln, re.I):
                grab = True
            continue
        if grab:
            out.append(ln)
    return out


def _rows(section_lines: list[str]) -> list[list[str]]:
    rows = []
    for ln in section_lines:
        s = ln.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells if c != ""):  # separator row
            if any(set(c) <= set("-: ") and c for c in cells):
                continue
        # skip header row (contains no data-ish content is hard to tell; keep all,
        # the caller flags by empty target cell — header cells are never "empty").
        rows.append(cells)
    return rows


def _empty(cell: str) -> bool:
    return cell.strip().lower() in PLACEHOLDER


def _looks_like_path(cell: str) -> bool:
    c = cell.strip().strip("`")
    return ("/" in c and " " not in c.strip("`")) or c.endswith(
        (".json", ".png", ".pdf", ".csv", ".tsv", ".svg", ".md", ".npy", ".pt"))


def _missing_path(root: Path, cell: str) -> bool:
    """True if the cell names a concrete artifact path that does NOT exist on disk.
    Tolerant: pulls the first path-ish token out of the cell (cells often read
    'reports/EXP.json (F1=.9)'); only flags when it clearly looks like a path."""
    c = cell.strip().strip("`")
    m = re.search(r"[\w./\-]+\.(?:json|png|pdf|csv|tsv|svg|md|npy|pt)\b|[\w\-]+/[\w./\-]+", c)
    if not m:
        return False
    return not (root / m.group(0)).exists()


def check_publication(root: Path) -> list[str]:
    gaps = []
    vm = root / "docs/14_validation_matrix.md"
    if vm.exists():
        txt = vm.read_text(encoding="utf-8", errors="ignore")
        # §1 main result: last cell = evidence path
        for r in _rows(_section(txt, r"Main result"))[1:]:
            if r and _empty(r[-1]):
                gaps.append(f"docs/14 §1 main-result 行缺 evidence path: {r[0] or '(空行)'}")
            elif r and _looks_like_path(r[-1]) and _missing_path(root, r[-1]):
                gaps.append(f"docs/14 §1 main-result 的 evidence path 在磁盘上不存在（claim 无实际产物支撑）: {r[-1]} [{r[0] or '行'}]")
        # §2 downstream: a 'Status' column should not be TODO/empty
        for r in _rows(_section(txt, r"Downstream"))[1:]:
            if r and (_empty(r[-1]) or any(c.strip().lower() == "todo" for c in r)):
                gaps.append(f"docs/14 §2 下游任务未完成/缺输出: {r[0] or '(空行)'}")
        # §5 randomized SOTA: need mean±std + comparable run (not placeholder)
        for r in _rows(_section(txt, r"Randomized SOTA"))[1:]:
            if r and (_empty(r[-1]) or _empty(r[-2])):
                gaps.append(f"docs/14 §5 randomized-SOTA 行缺 mean±std/comparable run: {r[0] or '(空行)'}")
    else:
        gaps.append("缺 docs/14_validation_matrix.md（投稿证据矩阵未建，先跑 /publication-plan）")
    # docs/12 readiness checklist unchecked boxes
    ps = root / "docs/12_publication_strategy.md"
    if ps.exists():
        unchecked = len(re.findall(r"^\s*-\s*\[ \]", ps.read_text(encoding="utf-8", errors="ignore"), re.M))
        if unchecked:
            gaps.append(f"docs/12 readiness checklist 还有 {unchecked} 项未勾选（- [ ]）")
    return gaps


def check_pipeline(root: Path) -> list[str]:
    gaps = []
    pb = root / "docs/13_pipeline_blueprint.md"
    if not pb.exists():
        return ["缺 docs/13_pipeline_blueprint.md（先跑 /pipeline-blueprint 把流程转成 DAG）"]
    txt = pb.read_text(encoding="utf-8", errors="ignore")
    # any stage ledger table: a row whose status or QC cell is empty/TODO
    for r in _rows(_section(txt, r"stage|ledger|DAG|阶段")):
        if len(r) >= 2 and any(_empty(c) for c in r) and not all(_empty(c) for c in r):
            gaps.append(f"docs/13 stage 行有空 status/QC: {r[0] or '(空行)'}")
    return gaps


def main() -> int:
    ap = argparse.ArgumentParser(description="Advisory completeness gate for Stage C")
    ap.add_argument("--mode", required=True, choices=["publication", "pipeline"])
    ap.add_argument("--strict", action="store_true", help="exit 2 if gaps exist (use as a gate)")
    ap.add_argument("root", nargs="?", default=os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    args = ap.parse_args()
    root = Path(args.root)

    gaps = check_publication(root) if args.mode == "publication" else check_pipeline(root)
    if not gaps:
        print(f"✓ stage-C {args.mode} completeness: no gaps found (advisory).")
        return 0
    print(f"⚠️ stage-C {args.mode} completeness — {len(gaps)} 处待补（advisory, agent 决定是否阻断）：")
    for g in gaps:
        print(f"  - {g}")
    return 2 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
