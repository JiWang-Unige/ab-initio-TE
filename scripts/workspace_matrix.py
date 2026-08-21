#!/usr/bin/env python3
"""Optional git/worktree helper for parallel experiment directions.

The framework's default safety is exp_id directory isolation. This helper adds an
OPTIONAL git worktree layer for users who want 2-3 parallel code branches without
cross-contaminating shared code. It is human-gated by design: no action happens
unless an explicit subcommand is used.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path


def run(cmd, cwd: Path, check=True):
    p = subprocess.run(cmd, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and p.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed: {p.stderr.strip()}")
    return p


def is_git(root: Path) -> bool:
    return (root / ".git").exists() or run(["git", "rev-parse", "--is-inside-work-tree"], root, check=False).returncode == 0


def has_commit(root: Path) -> bool:
    return run(["git", "rev-parse", "--verify", "HEAD"], root, check=False).returncode == 0


def status(root: Path):
    out = {"root": str(root), "git": is_git(root), "has_head_commit": False, "branch": None, "worktrees": []}
    if out["git"]:
        out["has_head_commit"] = has_commit(root)
        p = run(["git", "branch", "--show-current"], root, check=False)
        out["branch"] = p.stdout.strip() or None
        p = run(["git", "worktree", "list", "--porcelain"], root, check=False)
        cur = {}
        for line in p.stdout.splitlines():
            if line.startswith("worktree "):
                if cur:
                    out["worktrees"].append(cur)
                cur = {"path": line.split(" ", 1)[1]}
            elif line.startswith("branch "):
                cur["branch"] = line.split(" ", 1)[1]
            elif line.startswith("HEAD "):
                cur["head"] = line.split(" ", 1)[1]
        if cur:
            out["worktrees"].append(cur)
    return out


def safe_branch(exp_id: str) -> str:
    if not re.match(r"^[A-Za-z0-9_.-]+$", exp_id):
        raise ValueError(f"bad exp_id: {exp_id}")
    return "exp/" + exp_id.replace("_", "-")


def init(root: Path):
    if is_git(root):
        return {"action": "init", "changed": False, "message": "already a git repo"}
    run(["git", "init"], root)
    excl = root / ".git" / "info" / "exclude"
    with excl.open("a", encoding="utf-8") as f:
        f.write("\n# auto-research heavy/private artifacts\nsecrets.env\n.env\ndata/\nruns/\noutputs/\nlogs/\nsoftware_outputs/\nexternal_runs/\nworktrees/\n*.pt\n*.pth\n*.ckpt\n*.h5\n")
    return {"action": "init", "changed": True, "message": "git initialized; make a lightweight initial commit before worktree create"}


def create(root: Path, exp_ids: list[str], base: str, worktree_root: str, max_parallel: int):
    if len(exp_ids) > max_parallel:
        raise RuntimeError(f"requested {len(exp_ids)} worktrees > max_parallel {max_parallel}")
    if not is_git(root):
        raise RuntimeError("not a git repo; run `python3 scripts/workspace_matrix.py init --yes` then make an initial commit")
    if not has_commit(root):
        raise RuntimeError("git repo has no HEAD commit; make a lightweight initial commit before creating worktrees")
    wr = root / worktree_root
    wr.mkdir(parents=True, exist_ok=True)
    rows = []
    for eid in exp_ids:
        branch = safe_branch(eid)
        path = wr / eid
        if path.exists():
            rows.append({"exp_id": eid, "branch": branch, "path": str(path), "status": "exists"})
            continue
        p = run(["git", "worktree", "add", "-b", branch, str(path), base], root, check=False)
        if p.returncode != 0 and "already exists" in p.stderr:
            p = run(["git", "worktree", "add", str(path), branch], root, check=False)
        if p.returncode != 0:
            rows.append({"exp_id": eid, "branch": branch, "path": str(path), "status": "failed", "stderr": p.stderr.strip()})
        else:
            rows.append({"exp_id": eid, "branch": branch, "path": str(path), "status": "created"})
    return {"action": "create", "items": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["status", "init", "create", "plan"])
    ap.add_argument("exp_ids", nargs="*")
    ap.add_argument("--root", default=os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    ap.add_argument("--base", default="HEAD")
    ap.add_argument("--worktree-root", default="worktrees")
    ap.add_argument("--max-parallel", type=int, default=3)
    ap.add_argument("--yes", action="store_true", help="required for init/create actions")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    if args.cmd == "status":
        out = status(root)
    elif args.cmd == "plan":
        out = {"action": "plan", "max_parallel": args.max_parallel, "items": [{"exp_id": e, "branch": safe_branch(e), "path": str(root / args.worktree_root / e)} for e in args.exp_ids]}
    elif args.cmd == "init":
        if not args.yes:
            raise SystemExit("init is human-gated: rerun with --yes after reviewing")
        out = init(root)
    elif args.cmd == "create":
        if not args.yes:
            raise SystemExit("create is human-gated: rerun with --yes after reviewing")
        out = create(root, args.exp_ids, args.base, args.worktree_root, args.max_parallel)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
