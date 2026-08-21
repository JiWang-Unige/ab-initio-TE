#!/usr/bin/env python3
"""Create/audit the auto-research artifact directory contract."""
from __future__ import annotations
import argparse, json, os
from pathlib import Path

DIRS = [
    "scripts", "scripts/experiments", "pipelines", "configs", "configs/pipelines", "configs/sota_randomized",
    "sbatch", "runs", "reports", "outputs", "logs", "external_runs", "software_outputs",
    "data/raw", "data/interim", "data/processed", "analysis/notebooks", "manuscript",
    "refs/pdfs", "refs/repos", "refs/dossiers", "refs/supp", "wiki/ideas", "wiki/notes", "docs/experiments", "worktrees",
]

RUN_EXPECT = [
    "configs/{id}.yaml",
    "sbatch/{id}.sbatch",
    "outputs/{id}/STATUS",
    "reports/{id}.json",
    "runs/{id}",
    "docs/experiments/{id}.md",
]

EXT_EXPECT = ["command.txt", "version.txt", "stdout.log", "stderr.log", "inputs.sha256", "outputs_manifest.tsv"]


def touch_gitkeep(root: Path, d: str):
    p = root / d
    p.mkdir(parents=True, exist_ok=True)
    g = p / ".gitkeep"
    if not any(p.iterdir()) and not g.exists():
        g.write_text("", encoding="utf-8")


def audit_run(root: Path, run_id: str):
    rows = []
    for pat in RUN_EXPECT:
        p = root / pat.format(id=run_id)
        rows.append({"artifact": pat.format(id=run_id), "exists": p.exists()})
    # docs/06 mention
    results = root / "docs/06_results_log.md"
    mentioned = False
    if results.exists():
        mentioned = run_id in results.read_text(encoding="utf-8", errors="ignore")
    rows.append({"artifact": f"docs/06_results_log.md contains {run_id}", "exists": mentioned})
    code_review = root / "docs/21_code_review_log.md"
    reviewed = False
    if code_review.exists():
        reviewed = run_id in code_review.read_text(encoding="utf-8", errors="ignore")
    rows.append({"artifact": f"docs/21_code_review_log.md contains {run_id}", "exists": reviewed})
    return rows


def audit_external(root: Path, tool: str, run_id: str):
    base = root / "software_outputs" / tool / run_id
    return [{"artifact": str(base / name), "exists": (base / name).exists()} for name in EXT_EXPECT]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true", help="Create standard directories")
    ap.add_argument("--audit-run", default="", help="Audit an EXP/SOTA/PIPE run bundle")
    ap.add_argument("--audit-external", nargs=2, metavar=("TOOL", "RUN_ID"), help="Audit software_outputs/<tool>/<run_id>")
    ap.add_argument("--list-contract", action="store_true", help="Print the directory contract without modifying files")
    ap.add_argument("root", nargs="?", default=os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    args = ap.parse_args()
    root = Path(args.root)

    out = {"root": str(root), "created_dirs": [], "audits": []}
    if args.list_contract:
        out["directory_contract"] = DIRS
    if args.init:
        for d in DIRS:
            existed = (root / d).exists()
            touch_gitkeep(root, d)
            if not existed:
                out["created_dirs"].append(d)
    if args.audit_run:
        out["audits"].append({"type": "run", "id": args.audit_run, "items": audit_run(root, args.audit_run)})
    if args.audit_external:
        tool, run_id = args.audit_external
        out["audits"].append({"type": "external", "tool": tool, "id": run_id, "items": audit_external(root, tool, run_id)})

    print(json.dumps(out, ensure_ascii=False, indent=2))
    bad = any(not item["exists"] for audit in out["audits"] for item in audit["items"])
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
