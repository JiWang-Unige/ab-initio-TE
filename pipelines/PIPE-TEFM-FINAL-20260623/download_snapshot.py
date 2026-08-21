#!/usr/bin/env python3
"""Download a HuggingFace snapshot when the local checkpoint is missing."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-id", required=True)
    ap.add_argument("--local-dir", required=True)
    ap.add_argument("--out-json", required=True)
    args = ap.parse_args()

    out = Path(args.out_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    local = Path(args.local_dir)
    before = local.exists()
    try:
        from huggingface_hub import snapshot_download

        path = snapshot_download(
            repo_id=args.repo_id,
            local_dir=str(local),
            local_dir_use_symlinks=False,
            resume_download=True,
        )
        status = {"ok": True, "repo_id": args.repo_id, "local_dir": str(path), "already_existed": before}
    except Exception as exc:
        status = {"ok": False, "repo_id": args.repo_id, "local_dir": str(local), "error": repr(exc)}
    out.write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(status, indent=2), flush=True)
    if not status["ok"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
