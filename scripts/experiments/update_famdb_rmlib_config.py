#!/usr/bin/env python3
"""Regenerate RepeatMasker FamDB rmlib.config from present Dfam h5 files."""

from __future__ import annotations

import argparse
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


def sort_key(path: Path) -> tuple[int, str]:
    match = re.match(r"dfam\d+_full\.(\d+)\.h5$", path.name)
    return (int(match.group(1)) if match else 10**9, path.name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--famdb-dir", required=True)
    parser.add_argument("--backup-suffix", default="")
    args = parser.parse_args()

    famdb_dir = Path(args.famdb_dir).resolve()
    files = sorted(famdb_dir.glob("dfam*_full.*.h5"), key=sort_key)
    if not files:
        raise SystemExit(f"No dfam*_full.*.h5 files found in {famdb_dir}")

    config = famdb_dir / "rmlib.config"
    if config.exists():
        suffix = args.backup_suffix or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = famdb_dir / f"rmlib.config.pre_fullpartition_{suffix}"
        if not backup.exists():
            shutil.copy2(config, backup)

    lines: list[str] = ["{", "  'famdb_files' => {"]
    for path in files:
        lines.append(f"    '{path.name}' => {{ 'size' => {path.stat().st_size} }},")
    lines.extend(["  },", "  'files' => ["])
    for path in files:
        lines.append(f"    '{path.name}',")
    lines.extend(["  ],", "}"])
    config.write_text("\n".join(lines) + "\n")
    print(f"wrote {config} with {len(files)} h5 files")


if __name__ == "__main__":
    main()
