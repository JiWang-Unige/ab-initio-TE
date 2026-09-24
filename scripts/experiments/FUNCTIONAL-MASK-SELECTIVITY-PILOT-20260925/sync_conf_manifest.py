#!/usr/bin/env python3
"""Propagate the c01 confidence-arm repair into the species manifest.

The pre-repair species manifest is kept beside the updated manifest so the
coverage audit remains reconstructable.  No predictions or scores are run.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[3]
NAME = "FUNCTIONAL-MASK-SELECTIVITY-PILOT-20260925"
SPECIES = "chicken"
CORE_ID = "c01"
OUT = ROOT / "outputs" / NAME / SPECIES


def main():
    manifest = OUT / "manifest.json"
    cell_manifest = OUT / CORE_ID / "mask_manifest.json"
    backup = OUT / "manifest-pre-conf-repair.json"
    if not manifest.exists() or not cell_manifest.exists():
        raise RuntimeError("required manifest is missing")
    if not backup.exists():
        shutil.copy2(manifest, backup)
    data = json.loads(manifest.read_text())
    cell = json.loads(cell_manifest.read_text())
    matches = [row for row in data["cores"] if row["id"] == CORE_ID]
    if len(matches) != 1:
        raise RuntimeError(f"expected one {CORE_ID} row")
    matches[0].clear()
    matches[0].update(cell)
    data["manifest_repair"] = {
        "status": "COMPLETED_CONF_ONLY",
        "species": SPECIES,
        "core": CORE_ID,
        "backup": str(backup),
        "source": str(cell_manifest),
        "other_cores_rewritten": False,
    }
    manifest.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "COMPLETED", "species": SPECIES, "core": CORE_ID}), flush=True)


if __name__ == "__main__":
    main()
