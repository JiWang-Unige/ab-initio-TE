#!/usr/bin/env python3
"""Allocate the next Evidence ID (E<NNN>) for docs/15_evidence_register.md.

/note-add and /note-gate append rows to the SAME evidence table; without one
allocator they can collide on IDs across concurrent or cross-session writes.
This scans docs/15 for the highest existing E<NNN> and prints the next one
(zero-padded to 3 digits). E000 is the template placeholder → first real id is
E001. Pure stdlib; never raises on a malformed/missing file.
"""
from __future__ import annotations
import os, re, sys
from pathlib import Path


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    reg = root / "docs" / "15_evidence_register.md"
    mx = 0
    if reg.exists():
        try:
            for m in re.finditer(r"\bE(\d{3,})\b", reg.read_text(encoding="utf-8", errors="ignore")):
                mx = max(mx, int(m.group(1)))
        except Exception:
            pass
    print(f"E{mx + 1:03d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
