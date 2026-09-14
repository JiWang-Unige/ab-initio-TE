#!/usr/bin/env python3
"""Export completed native/D interval outputs to a compact Omni bundle.

The exporter is intentionally separate from the Omni module entrypoint.  Run
it after the native Slurm array has finished, on the host where the native and
saved-D outputs are visible.  It copies only canonical interval TSVs, status
sidecars, panel coordinates, and callable runs.  FASTA and probability arrays
remain at their source paths.

The resulting bundle is suitable for the local OmniBenchmark T2 concordance
replay.  It contains no independent truth, so downstream metrics are coverage,
intersection, Jaccard, and candidate-fragment counts only.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path
from typing import Any, Iterable


SPECIES = ("platypus", "sea_urchin", "c_briggsae")
METHODS = ("fixed_rm", "hite", "rm2_rm")
CANONICAL_FIELDS = [
    "seqid",
    "start",
    "end",
    "name",
    "score",
    "strand",
    "source",
    "attributes",
]


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def read_fasta(path: Path) -> dict[str, str]:
    sequences: dict[str, str] = {}
    current: str | None = None
    pieces: list[str] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if line.startswith(">"):
                if current is not None:
                    sequences[current] = "".join(pieces).upper()
                current = line[1:].split()[0]
                pieces = []
            elif current is not None:
                pieces.append(line.strip())
        if current is not None:
            sequences[current] = "".join(pieces).upper()
    return sequences


def callable_runs(sequence: str) -> list[list[int]]:
    runs: list[list[int]] = []
    start: int | None = None
    for index, base in enumerate(sequence.upper() + "N"):
        if base in "ACGT" and start is None:
            start = index
        elif base not in "ACGT" and start is not None:
            runs.append([start, index])
            start = None
    return runs


def _region_map(d_panel_dir: Path) -> tuple[dict[str, str], dict[str, Any]]:
    regions_path = d_panel_dir / "panel_regions.json"
    fasta_path = d_panel_dir / "panel_regions.fa"
    for path in (regions_path, fasta_path):
        if not path.is_file():
            raise FileNotFoundError(f"fixed D panel input missing: {path}")
    regions = json.loads(regions_path.read_text(encoding="utf-8"))
    if not isinstance(regions, list) or len(regions) != 4:
        raise ValueError(f"expected four D regions in {regions_path}")
    sequences = read_fasta(fasta_path)
    frozen_to_short: dict[str, str] = {}
    compact_regions: list[dict[str, Any]] = []
    for index, row in enumerate(regions, 1):
        frozen_id = str(row["id"])
        short_id = f"r{index:02d}"
        if frozen_id not in sequences:
            raise ValueError(f"D panel FASTA is missing {frozen_id}")
        sequence = sequences[frozen_id]
        expected = int(row["length_bp"])
        if len(sequence) != expected or expected != 1048576:
            raise ValueError(f"D panel length mismatch for {frozen_id}: {len(sequence)} != {expected}")
        frozen_to_short[frozen_id] = short_id
        runs = callable_runs(sequence)
        compact_regions.append(
            {
                "short_id": short_id,
                "frozen_region_id": frozen_id,
                "length_bp": expected,
                "callable_bp": sum(end - start for start, end in runs),
                "callable_intervals": runs,
            }
        )
    panel = {
        "schema": "te_real_panel_compact_panel_v1",
        "regions": compact_regions,
        "input_bp": sum(int(row["length_bp"]) for row in compact_regions),
        "callable_bp": sum(int(row["callable_bp"]) for row in compact_regions),
        "source_panel_regions": str(regions_path.resolve()),
        "source_panel_fasta": str(fasta_path.resolve()),
        "fasta_copied": False,
    }
    return frozen_to_short, panel


def _canonical_rows(path: Path, frozen_to_short: dict[str, str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != CANONICAL_FIELDS:
            raise ValueError(f"canonical fields differ in {path}: {reader.fieldnames!r}")
        rows: list[dict[str, str]] = []
        for line_no, row in enumerate(reader, 2):
            source_id = str(row["seqid"])
            short_id = source_id if source_id.startswith("r") and source_id[1:].isdigit() else frozen_to_short.get(source_id)
            if short_id is None:
                raise ValueError(f"unknown panel ID at {path}:{line_no}: {source_id}")
            try:
                start = int(row["start"])
                end = int(row["end"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid interval at {path}:{line_no}") from exc
            if start < 0 or end <= start or end > 1048576:
                raise ValueError(f"interval outside 1-MiB panel at {path}:{line_no}: {start}-{end}")
            rows.append({
                "seqid": short_id,
                "start": str(start),
                "end": str(end),
                "name": str(row.get("name") or "."),
                "score": str(row.get("score") or "."),
                "strand": str(row.get("strand") or "."),
                "source": str(row.get("source") or "."),
                "attributes": str(row.get("attributes") or "."),
            })
    return rows


def write_canonical(path: Path, rows: Iterable[dict[str, str]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANONICAL_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, ".") for field in CANONICAL_FIELDS})
            count += 1
    return count


def _normal_status(raw: str | None) -> str:
    value = str(raw or "NOTRUN")
    if value == "BLOCKED_NO_LIBRARY":
        return "BLOCKED"
    if value in {"COMPLETED", "FAILED", "TIMEOUT", "BLOCKED", "UNSUPPORTED", "INVALID_INPUT", "NOTRUN", "RUNNING"}:
        return value
    return "FAILED"


def _safe_cell_id(value: str) -> str:
    return value.replace("|", "__").replace("/", "_")


def _status_record(path: Path, cell_id: str, method: str, species: str, role: str) -> dict[str, Any]:
    if not path.is_file():
        return {
            "schema": "te_real_panel_cell_status_v1",
            "cell_id": cell_id,
            "method": method,
            "species": species,
            "status": "NOTRUN",
            "reason": "status.json absent when compact bundle was exported",
            "role": role,
        }
    value = read_json(path)
    raw_status = str(value.get("status", "NOTRUN"))
    result = dict(value)
    result.update({
        "schema": "te_real_panel_cell_status_v1",
        "cell_id": cell_id,
        "method": method,
        "species": species,
        "status": _normal_status(raw_status),
        "source_status": raw_status,
        "role": role,
    })
    return result


def _panel_for_species(root: Path, species: str) -> tuple[Path, dict[str, str], dict[str, Any]]:
    d_index = SPECIES.index(species)
    panel_dir = root / "outputs/D-EXTERNAL-RC0-20260914" / species / f"slurm-12696615_{d_index}"
    frozen_to_short, panel = _region_map(panel_dir)
    return panel_dir, frozen_to_short, panel


def export_bundle(root: Path, native_array_id: str, output: Path) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite compact bundle: {output}")
    output.mkdir(parents=True)
    panels_dir = output / "panels"
    cells_dir = output / "cells"
    panels_dir.mkdir()
    cells_dir.mkdir()
    registry_rows: list[dict[str, Any]] = []
    cell_records: list[dict[str, Any]] = []
    panel_records: dict[str, dict[str, Any]] = {}
    for species_index, species in enumerate(SPECIES):
        d_panel_dir, frozen_to_short, panel = _panel_for_species(root, species)
        panel["species"] = species
        panel["assembly"] = {
            "platypus": "GCF_004115215.2",
            "sea_urchin": "GCF_000002235.5",
            "c_briggsae": "GCA_000004555.3",
        }[species]
        panel_path = panels_dir / f"{species}.json"
        write_json(panel_path, panel)
        panel_records[species] = panel

        native_task_base = species_index * len(METHODS)
        for method_index, method in enumerate(METHODS):
            cell_id = f"{species}|{method}"
            native_dir = root / "outputs/TE-REAL-PANEL-BENCH-20260914" / species / method / f"slurm-{native_array_id}_{native_task_base + method_index}"
            cell_dir = cells_dir / _safe_cell_id(cell_id)
            cell_dir.mkdir()
            status = _status_record(native_dir / "status.json", cell_id, method, species, "native_slurm")
            prediction_path = native_dir / "predictions.tsv"
            if status["status"] == "COMPLETED":
                try:
                    if not prediction_path.is_file():
                        raise FileNotFoundError(f"completed cell prediction missing: {prediction_path}")
                    rows = _canonical_rows(prediction_path, frozen_to_short)
                    write_canonical(cell_dir / "predictions.tsv", rows)
                    status["prediction_rows"] = len(rows)
                except Exception as exc:
                    status["status"] = "INVALID_INPUT"
                    status["reason"] = str(exc)
            write_json(cell_dir / "status.json", status)
            write_json(
                cell_dir / "provenance.json",
                {
                    "cell_id": cell_id,
                    "method": method,
                    "species": species,
                    "role": "native_slurm",
                    "native_output_dir": str(native_dir.resolve()),
                    "native_prediction_source": str(prediction_path.resolve()),
                    "canonical_copied": bool((cell_dir / "predictions.tsv").is_file()),
                    "raw_fasta_copied": False,
                    "probabilities_copied": False,
                },
            )
            registry_rows.append(
                {
                    "cell_id": cell_id,
                    "species": species,
                    "method": method,
                    "task": "T2",
                    "device": "cpu",
                    "role": "native_slurm",
                    "expected_status": "COMPLETED",
                }
            )
            cell_records.append(
                {
                    "cell_id": cell_id,
                    "status": status["status"],
                    "status_path": str((cell_dir / "status.json").relative_to(output)),
                    "prediction_path": str((cell_dir / "predictions.tsv").relative_to(output)) if (cell_dir / "predictions.tsv").is_file() else None,
                }
            )

        d_cell_id = f"{species}|D_F_cache"
        d_index = SPECIES.index(species)
        d_dir = root / "outputs/D-EXTERNAL-RC0-20260914" / species / f"slurm-12696615_{d_index}"
        d_status = _status_record(d_dir / "STATUS.json", d_cell_id, "D_F_cache", species, "completed_D_replay")
        if d_status["status"] == "NOTRUN":
            d_status["status"] = "FAILED"
            d_status["reason"] = "saved D STATUS.json absent"
        d_cell_dir = cells_dir / _safe_cell_id(d_cell_id)
        d_cell_dir.mkdir()
        d_prediction = d_dir / "F.canonical.tsv"
        if d_status["status"] == "COMPLETED":
            try:
                if not d_prediction.is_file():
                    raise FileNotFoundError(f"saved D F canonical prediction missing: {d_prediction}")
                rows = _canonical_rows(d_prediction, frozen_to_short)
                write_canonical(d_cell_dir / "predictions.tsv", rows)
                d_status["prediction_rows"] = len(rows)
            except Exception as exc:
                d_status["status"] = "INVALID_INPUT"
                d_status["reason"] = str(exc)
        write_json(d_cell_dir / "status.json", d_status)
        write_json(
            d_cell_dir / "provenance.json",
            {
                "cell_id": d_cell_id,
                "method": "D_F_cache",
                "species": species,
                "role": "completed_D_replay",
                "source_prediction_dir": str(d_dir.resolve()),
                "saved_D_prediction_source": str(d_prediction.resolve()),
                "native_runtime_replayed": False,
                "raw_fasta_copied": False,
                "probabilities_copied": False,
            },
        )
        registry_rows.append(
            {
                "cell_id": d_cell_id,
                "species": species,
                "method": "D_F_cache",
                "task": "T2",
                "device": "gpu_saved_replay",
                "role": "completed_D_replay",
                "expected_status": "COMPLETED",
            }
        )
        cell_records.append(
            {
                "cell_id": d_cell_id,
                "status": d_status["status"],
                "status_path": str((d_cell_dir / "status.json").relative_to(output)),
                "prediction_path": str((d_cell_dir / "predictions.tsv").relative_to(output)) if (d_cell_dir / "predictions.tsv").is_file() else None,
            }
        )

    registry = {
        "schema": "te_real_panel_registry_v1",
        "protocol": "TE-REAL-PANEL-BENCH-20260914",
        "scope": "REAL_REGION_FEASIBILITY_AND_T2_CONCORDANCE_ONLY",
        "denominator_policy": "all 12 native plus saved-D cells remain; non-completed cells have null metrics",
        "truth_available": False,
        "absolute_precision": None,
        "absolute_f1": None,
        "expected_cells": registry_rows,
    }
    write_json(output / "cell_registry.json", registry)
    manifest = {
        "schema": "te_real_panel_compact_bundle_v1",
        "protocol": "TE-REAL-PANEL-BENCH-20260914",
        "native_array_id": str(native_array_id),
        "source_root": str(root.resolve()),
        "bundle_root": str(output.resolve()),
        "cells": cell_records,
        "panels": {species: str((panels_dir / f"{species}.json").relative_to(output)) for species in SPECIES},
        "cell_registry": "cell_registry.json",
        "raw_fasta_copied": False,
        "probabilities_copied": False,
        "independent_truth": False,
        "metrics_scope": ["callable_bp_coverage", "callable_intersection", "callable_jaccard", "candidate_fragment_count"],
    }
    write_json(output / "manifest.json", manifest)
    write_json(
        output / "STATUS.json",
        {
            "status": "COMPLETED",
            "schema": "te_real_panel_compact_export_status_v1",
            "native_array_id": str(native_array_id),
            "expected_cell_count": len(registry_rows),
            "completed_cell_count": sum(row["status"] == "COMPLETED" for row in cell_records),
            "noncompleted_cell_count": sum(row["status"] != "COMPLETED" for row in cell_records),
        },
    )
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="project/data root where outputs/ is visible")
    parser.add_argument("--native-array-id", required=True, help="completed native Slurm array ID, e.g. 12708424")
    parser.add_argument("--output", type=Path, required=True, help="new compact bundle directory")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    manifest = export_bundle(args.root.resolve(), args.native_array_id, args.output.resolve())
    print(json.dumps({"status": "COMPLETED", "bundle": manifest["bundle_root"], "cells": len(manifest["cells"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
