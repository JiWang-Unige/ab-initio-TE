#!/usr/bin/env python3
"""Repair RM2 descriptive summaries from the native RepeatMasker ``.out``.

The original native annotations and status files are immutable scientific
outputs.  This utility versions the old GFF-derived summary, writes a
validated ``.out``-derived summary to the canonical summary path for future
consumers, and emits a compact provenance sidecar outside the native root.
"""
from __future__ import annotations

import argparse
import filecmp
import json
from pathlib import Path
from typing import Dict

from common import file_metadata, write_json
from summarize_native import summarize_repeatmasker_out


REVISION = "rm2-out-class-v1"
BACKUP_NAME = "annotation_summary.original-gff-20260924.json"


def compact_status(path: Path) -> Dict[str, object]:
    status = json.loads(path.read_text(encoding="utf-8"))
    keep = ("status", "method", "species", "slurm", "wall_seconds", "started_epoch",
            "finished_epoch", "recovery", "error")
    return {key: status[key] for key in keep if key in status}


def repair(species: str, native_root: Path, sidecar: Path) -> Dict[str, object]:
    native_root = native_root.resolve()
    sidecar = sidecar.resolve()
    status_path = native_root / "status.json"
    original_path = native_root / "annotation_summary.json"
    annotation_out = native_root / "annotation.out"
    if not status_path.is_file() or not original_path.is_file() or not annotation_out.is_file():
        raise FileNotFoundError("RM2 root is missing status, original summary, or annotation.out: %s" % native_root)
    status = json.loads(status_path.read_text(encoding="utf-8"))
    if status.get("status") != "COMPLETED":
        raise ValueError("refusing to repair a non-success RM2 root: %s" % status.get("status"))
    backup_path = native_root / BACKUP_NAME
    if backup_path.exists():
        if not filecmp.cmp(original_path, backup_path, shallow=False):
            raise RuntimeError("existing summary backup differs from current canonical summary: %s" % backup_path)
    else:
        backup_path.write_bytes(original_path.read_bytes())

    corrected_annotation = summarize_repeatmasker_out(annotation_out)
    original = json.loads(original_path.read_text(encoding="utf-8"))
    corrected = {
        "protocol": original.get("protocol", "WHOLE-GENOME-BENCHMARK-20260918"),
        "status": "COMPLETED",
        "species": species,
        "method": "RM2",
        "annotation": corrected_annotation,
        # The library section is carried forward unchanged; this repair is
        # specifically for the annotation source and does not reinterpret the
        # native RepeatModeler library.
        "library": original.get("library"),
        "unknown_policy": "RepeatMasker .out Unknown and unresolved class rows remain in descriptive counts; no native row is filtered.",
        "classification_scope": "RM2 descriptive class/family counts and unions are parsed from annotation.out; class intervals are merged independently within each contig.",
        "derived_summary_revision": REVISION,
        "provenance": {
            "canonical_summary_backup": str(backup_path),
            "original_summary_metadata": file_metadata(backup_path),
            "native_status_snapshot": compact_status(status_path),
            "native_outputs_unchanged": True,
            "source_annotation": "annotation.out",
            "source_annotation_metadata": file_metadata(annotation_out),
            "old_summary_source": "annotation.gff3 attributes (Target Motif), retained byte-for-byte at canonical_summary_backup",
        },
    }
    # The native root is a completed output, so canonical replacement is
    # allowed only after the original summary has been versioned above.
    write_json(original_path, corrected)
    if sidecar.exists():
        raise FileExistsError("refusing to replace an existing repair sidecar: %s" % sidecar)
    sidecar_record = {
        "protocol": corrected["protocol"],
        "status": "COMPLETED",
        "species": species,
        "method": "RM2",
        "revision": REVISION,
        "native_root": str(native_root),
        "canonical_summary": str(original_path),
        "canonical_summary_backup": str(backup_path),
        "annotation": corrected_annotation,
        "provenance": corrected["provenance"],
    }
    write_json(sidecar, sidecar_record)
    return {
        "species": species,
        "status": "COMPLETED",
        "revision": REVISION,
        "canonical_summary": str(original_path),
        "canonical_summary_backup": str(backup_path),
        "sidecar": str(sidecar),
        "rows": corrected_annotation["rows"],
        "union_bp": corrected_annotation["union_bp"],
        "class_rows": corrected_annotation["class_rows"],
        "class_union_bp": corrected_annotation["class_union_bp"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--species", required=True, choices=("chicken", "zebrafish"))
    parser.add_argument("--native-root", type=Path, required=True)
    parser.add_argument("--sidecar", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(repair(args.species, args.native_root, args.sidecar), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
