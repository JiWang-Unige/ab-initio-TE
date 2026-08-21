#!/usr/bin/env python3
"""Prepare a run-scoped RepeatMasker library overlay for full-partition reruns."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeatmasker-libraries", required=True)
    parser.add_argument("--overlay", required=True)
    parser.add_argument("--famdb-dir", default="")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    source = Path(args.repeatmasker_libraries).resolve()
    overlay = Path(args.overlay).resolve()
    if args.force and overlay.exists():
        shutil.rmtree(overlay)
    overlay.mkdir(parents=True, exist_ok=True)
    (overlay / "CONS-Dfam_3.9").mkdir(exist_ok=True)

    for entry in source.iterdir():
        if entry.name in {"CONS-Dfam_3.9", "famdb"}:
            continue
        dest = overlay / entry.name
        if dest.exists() or dest.is_symlink():
            continue
        dest.symlink_to(entry)

    famdb_source = Path(args.famdb_dir).resolve() if args.famdb_dir else source / "famdb"
    famdb_dest = overlay / "famdb"
    if famdb_dest.exists() or famdb_dest.is_symlink():
        famdb_dest.unlink()
    famdb_dest.symlink_to(famdb_source)

    print(f"overlay={overlay}")
    print(f"source={source}")
    print(f"famdb={famdb_source}")


if __name__ == "__main__":
    main()
