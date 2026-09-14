#!/usr/bin/env python3
"""Replay the real TE panel as an OmniBenchmark T2 module.

The native callers are run outside OmniBenchmark on Slurm.  This entrypoint
only consumes the compact bundle produced by ``real_panel_export.py`` and
computes interval coverage/concordance summaries.  The bundle has no
independent truth, so this module deliberately does not emit precision, F1,
or a biological accuracy claim.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SPECIES = ("platypus", "sea_urchin", "c_briggsae")
METHODS = ("fixed_rm", "hite", "rm2_rm", "D_F_cache")
CANONICAL_FIELDS = (
    "seqid",
    "start",
    "end",
    "name",
    "score",
    "strand",
    "source",
    "attributes",
)
STATUSES = {
    "COMPLETED",
    "FAILED",
    "TIMEOUT",
    "BLOCKED",
    "UNSUPPORTED",
    "INVALID_INPUT",
    "NOTRUN",
    "RUNNING",
}
BUCKETS = ("known_te", "unknown_or_ambiguous", "non_te")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def path_arg(parser: argparse.ArgumentParser, option: str, *, many: bool = False) -> None:
    parser.add_argument(
        option,
        dest=option[2:].replace(".", "_"),
        type=Path,
        nargs="+" if many else None,
    )


def first_path(value: Path | list[Path] | None) -> Path | None:
    if isinstance(value, list):
        return value[0] if value else None
    return value


def normal_status(value: object) -> str:
    raw = str(value or "NOTRUN")
    if raw == "BLOCKED_NO_LIBRARY":
        return "BLOCKED"
    return raw if raw in STATUSES else "FAILED"


def merge_intervals(intervals: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping or directly adjacent half-open intervals."""
    ordered = sorted((int(start), int(end)) for start, end in intervals if end > start)
    if not ordered:
        return []
    merged: list[tuple[int, int]] = []
    active_start, active_end = ordered[0]
    for start, end in ordered[1:]:
        if start <= active_end:
            active_end = max(active_end, end)
        else:
            merged.append((active_start, active_end))
            active_start, active_end = start, end
    merged.append((active_start, active_end))
    return merged


def interval_length(intervals: Iterable[tuple[int, int]]) -> int:
    return sum(end - start for start, end in intervals)


def intersection_length(
    first: Sequence[tuple[int, int]], second: Sequence[tuple[int, int]]
) -> int:
    """Return the intersection length of two sorted, merged interval lists."""
    total = 0
    left = right = 0
    while left < len(first) and right < len(second):
        start = max(first[left][0], second[right][0])
        end = min(first[left][1], second[right][1])
        if end > start:
            total += end - start
        if first[left][1] <= second[right][1]:
            left += 1
        else:
            right += 1
    return total


def intersect_by_region(
    intervals: Mapping[str, Sequence[tuple[int, int]]],
    callable_by_region: Mapping[str, Sequence[tuple[int, int]]],
) -> dict[str, list[tuple[int, int]]]:
    result: dict[str, list[tuple[int, int]]] = {}
    for seqid, values in intervals.items():
        callables = callable_by_region.get(seqid, ())
        clipped: list[tuple[int, int]] = []
        for start, end in values:
            for c_start, c_end in callables:
                if c_end <= start:
                    continue
                if c_start >= end:
                    break
                clipped.append((max(start, c_start), min(end, c_end)))
        result[seqid] = merge_intervals(clipped)
    return result


def _panel_regions(panel: Mapping[str, Any]) -> tuple[dict[str, int], dict[str, list[tuple[int, int]]]]:
    rows = panel.get("regions")
    if not isinstance(rows, list) or not rows:
        raise ValueError("compact panel has no regions")
    lengths: dict[str, int] = {}
    callable_by_region: dict[str, list[tuple[int, int]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("compact panel region is not an object")
        seqid = str(row.get("short_id") or row.get("id") or "")
        if not seqid:
            raise ValueError("compact panel region has no short_id")
        length = int(row["length_bp"])
        if length <= 0 or seqid in lengths:
            raise ValueError(f"invalid compact panel region: {seqid}")
        values: list[tuple[int, int]] = []
        for pair in row.get("callable_intervals", []):
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                raise ValueError(f"invalid callable interval for {seqid}")
            start, end = int(pair[0]), int(pair[1])
            if start < 0 or end <= start or end > length:
                raise ValueError(f"callable interval outside {seqid}: {start}-{end}")
            values.append((start, end))
        lengths[seqid] = length
        callable_by_region[seqid] = merge_intervals(values)
    return lengths, callable_by_region


def read_canonical(path: Path, lengths: Mapping[str, int]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if tuple(reader.fieldnames or ()) != CANONICAL_FIELDS:
            raise ValueError(f"canonical fields differ in {path}: {reader.fieldnames!r}")
        rows: list[dict[str, str]] = []
        for line_no, source in enumerate(reader, 2):
            seqid = str(source.get("seqid") or "")
            if seqid not in lengths:
                raise ValueError(f"unknown panel ID at {path}:{line_no}: {seqid}")
            try:
                start, end = int(source["start"]), int(source["end"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid interval at {path}:{line_no}") from exc
            if start < 0 or end <= start or end > lengths[seqid]:
                raise ValueError(f"interval outside {seqid} at {path}:{line_no}: {start}-{end}")
            rows.append({field: str(source.get(field) or ".") for field in CANONICAL_FIELDS})
    return rows


def classify_bucket(row: Mapping[str, str]) -> str:
    """Coarsely preserve KnownTE/unknown/nonTE labels carried by callers.

    This is an annotation bucket for stratification, not an independent truth
    assignment.  A missing or unrecognized class stays unknown.
    """
    # Parse the explicit class, not substrings of names or subtype labels:
    # SINE/tRNA is a TE, while a top-level tRNA annotation is non-TE.
    match = re.search(
        r"(?:^|;)\s*(?:class_family|class|family)=([^;\s]+)",
        str(row.get("attributes", "")), re.IGNORECASE,
    )
    if match is None:
        return "unknown_or_ambiguous"
    value = match.group(1)
    top = value.split("/", 1)[0].upper()
    if "?" in value or top in {"UNKNOWN", "UNCLASSIFIED", "AMBIGUOUS", "AMBIG", "PLE"}:
        return "unknown_or_ambiguous"
    if top in {"SINE", "LINE", "LTR", "DNA", "RC", "RETROPOSON"}:
        return "known_te"
    if top in {"SIMPLE_REPEAT", "LOW_COMPLEXITY", "SATELLITE", "RNA", "RRNA", "TRNA", "SNRNA", "SCRNA", "SRPRNA"}:
        return "non_te"
    return "unknown_or_ambiguous"


def _bucket_metrics(rows: Iterable[dict[str, str]], callable_by_region: Mapping[str, Sequence[tuple[int, int]]]) -> dict[str, dict[str, int]]:
    grouped: dict[str, dict[str, list[tuple[int, int]]]] = {
        bucket: defaultdict(list) for bucket in BUCKETS
    }
    counts = Counter()
    for row in rows:
        bucket = classify_bucket(row)
        counts[bucket] += 1
        grouped[bucket][row["seqid"]].append((int(row["start"]), int(row["end"])))
    result: dict[str, dict[str, int]] = {}
    for bucket in BUCKETS:
        merged = {seqid: merge_intervals(values) for seqid, values in grouped[bucket].items()}
        callable_merged = intersect_by_region(merged, callable_by_region)
        result[bucket] = {
            "candidate_fragment_count": int(counts[bucket]),
            "merged_fragment_count": sum(len(values) for values in merged.values()),
            "coverage_bp": sum(interval_length(values) for values in merged.values()),
            "callable_coverage_bp": sum(interval_length(values) for values in callable_merged.values()),
        }
    return result


def _resolve_bundle_path(bundle_root: Path, value: object) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else bundle_root / path


def load_bundle(bundle_manifest: Path, cell_registry: Path | None = None) -> tuple[dict[str, Any], dict[str, Any], Path]:
    manifest = read_json(bundle_manifest)
    bundle_root_value = manifest.get("bundle_root")
    bundle_root = Path(str(bundle_root_value)) if bundle_root_value else bundle_manifest.parent
    if not bundle_root.is_absolute():
        bundle_root = (bundle_manifest.parent / bundle_root).resolve()
    registry_path = cell_registry or _resolve_bundle_path(bundle_root, manifest.get("cell_registry"))
    if registry_path is None or not registry_path.is_file():
        raise FileNotFoundError(f"compact cell registry missing: {registry_path}")
    registry = read_json(registry_path)
    expected = registry.get("expected_cells")
    if not isinstance(expected, list) or not all(isinstance(row, dict) for row in expected):
        raise ValueError("cell registry expected_cells must be a list of objects")
    ids = [str(row.get("cell_id") or "") for row in expected]
    if any(not cell_id for cell_id in ids) or len(ids) != len(set(ids)):
        raise ValueError("cell registry cell IDs must be present and unique")
    return manifest, registry, bundle_root


def _manifest_cells(manifest: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for row in manifest.get("cells", []):
        if isinstance(row, dict) and isinstance(row.get("cell_id"), str):
            result[row["cell_id"]] = row
    return result


def _panel_paths(manifest: Mapping[str, Any], bundle_root: Path) -> dict[str, Path]:
    panels = manifest.get("panels")
    if not isinstance(panels, dict):
        raise ValueError("compact manifest has no panels map")
    result: dict[str, Path] = {}
    for species in SPECIES:
        path = _resolve_bundle_path(bundle_root, panels.get(species))
        if path is None or not path.is_file():
            raise FileNotFoundError(f"compact panel missing for {species}: {path}")
        result[species] = path
    return result


def _cell_paths(cell_row: Mapping[str, Any], bundle_root: Path) -> tuple[Path | None, Path | None]:
    status = _resolve_bundle_path(bundle_root, cell_row.get("status_path"))
    prediction = _resolve_bundle_path(bundle_root, cell_row.get("prediction_path"))
    return status, prediction


def _base_cell_row(expected: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "cell_id": str(expected["cell_id"]),
        "species": expected.get("species"),
        "method": expected.get("method"),
        "task": expected.get("task"),
        "device": expected.get("device"),
        "role": expected.get("role"),
        "expected_status": expected.get("expected_status"),
    }


def score_bundle(bundle_manifest: Path, cell_registry: Path | None, output_dir: Path) -> dict[str, Any]:
    manifest, registry, bundle_root = load_bundle(bundle_manifest, cell_registry)
    panel_paths = _panel_paths(manifest, bundle_root)
    panel_by_species: dict[str, dict[str, Any]] = {}
    panel_lengths: dict[str, dict[str, int]] = {}
    callable_by_species: dict[str, dict[str, list[tuple[int, int]]]] = {}
    for species, path in panel_paths.items():
        panel = read_json(path)
        lengths, callable_by_region = _panel_regions(panel)
        panel_by_species[species] = panel
        panel_lengths[species] = lengths
        callable_by_species[species] = callable_by_region

    cells_by_id = _manifest_cells(manifest)
    prepared: dict[str, dict[str, Any]] = {}
    cell_results: list[dict[str, Any]] = []
    for expected in registry["expected_cells"]:
        cell = _base_cell_row(expected)
        cell_id = cell["cell_id"]
        species = str(cell.get("species") or "")
        status_path, prediction_path = _cell_paths(cells_by_id.get(cell_id, {}), bundle_root)
        status_value = None
        if status_path is not None and status_path.is_file():
            status_value = read_json(status_path)
        elif isinstance(cells_by_id.get(cell_id), Mapping):
            status_value = cells_by_id[cell_id].get("status")
        if isinstance(status_value, Mapping):
            status = normal_status(status_value.get("status"))
            reason = status_value.get("reason") or status_value.get("failure_reason")
        else:
            status = normal_status(status_value)
            reason = "status sidecar absent" if status == "NOTRUN" else None
        cell["status"] = status
        if reason:
            cell["reason"] = str(reason)
        cell["metrics"] = None
        prepared[cell_id] = {"status": status, "species": species, "merged": {}}

        try:
            if species not in panel_lengths:
                raise ValueError(f"unknown species in registry: {species}")
            if status == "COMPLETED":
                if prediction_path is None or not prediction_path.is_file():
                    raise FileNotFoundError(f"completed cell prediction missing: {prediction_path}")
                rows = read_canonical(prediction_path, panel_lengths[species])
                by_region = defaultdict(list)
                for row in rows:
                    by_region[row["seqid"]].append((int(row["start"]), int(row["end"])))
                merged = {seqid: merge_intervals(values) for seqid, values in by_region.items()}
                callable_merged = intersect_by_region(merged, callable_by_species[species])
                panel_callable_bp = sum(
                    interval_length(values) for values in callable_by_species[species].values()
                )
                callable_coverage_bp = sum(interval_length(values) for values in callable_merged.values())
                union_bp = sum(interval_length(values) for values in merged.values())
                metrics = {
                    "candidate_fragment_count": len(rows),
                    "merged_fragment_count": sum(len(values) for values in merged.values()),
                    "coverage_bp": union_bp,
                    "callable_coverage_bp": callable_coverage_bp,
                    "panel_callable_bp": panel_callable_bp,
                    "callable_coverage_fraction": (
                        callable_coverage_bp / panel_callable_bp if panel_callable_bp else None
                    ),
                    "by_bucket": _bucket_metrics(rows, callable_by_species[species]),
                }
                cell["metrics"] = metrics
                prepared[cell_id]["merged"] = merged
                cell["prediction_rows"] = len(rows)
        except Exception as exc:
            cell["status"] = "INVALID_INPUT"
            cell["reason"] = str(exc)
            prepared[cell_id]["status"] = "INVALID_INPUT"
            prepared[cell_id]["merged"] = {}
        cell_results.append(cell)

    pairwise: list[dict[str, Any]] = []
    by_species: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cell in cell_results:
        by_species[str(cell.get("species") or "")].append(cell)
    for species, rows in sorted(by_species.items()):
        for first, second in combinations(sorted(rows, key=lambda row: row["cell_id"]), 2):
            first_id, second_id = first["cell_id"], second["cell_id"]
            pair: dict[str, Any] = {
                "pair_id": f"{first_id}__{second_id}",
                "species": species,
                "cell_a": first_id,
                "cell_b": second_id,
                "status": "NOT_SCORED",
                "metrics": None,
            }
            left = prepared[first_id]
            right = prepared[second_id]
            if left["status"] == "COMPLETED" and right["status"] == "COMPLETED":
                # The two comprehensions below keep sequence boundaries
                # explicit; flattening is safe because each region is separate.
                left_callable = intersect_by_region(left["merged"], callable_by_species[species])
                right_callable = intersect_by_region(right["merged"], callable_by_species[species])
                left_callable_bp = sum(interval_length(values) for values in left_callable.values())
                right_callable_bp = sum(interval_length(values) for values in right_callable.values())
                intersection_bp = sum(
                    intersection_length(left_callable.get(seqid, []), right_callable.get(seqid, []))
                    for seqid in set(left_callable) | set(right_callable)
                )
                union_bp = left_callable_bp + right_callable_bp - intersection_bp
                pair["status"] = "SCORED"
                pair["metrics"] = {
                    "callable_coverage_a_bp": left_callable_bp,
                    "callable_coverage_b_bp": right_callable_bp,
                    "callable_intersection_bp": intersection_bp,
                    "callable_union_bp": union_bp,
                    "callable_jaccard": intersection_bp / union_bp if union_bp else None,
                }
            else:
                pair["reason"] = {
                    "cell_a_status": left["status"],
                    "cell_b_status": right["status"],
                }
            pairwise.append(pair)

    status_counts = Counter(str(cell["status"]) for cell in cell_results)
    result = {
        "schema": "te_real_panel_t2_metrics_v1",
        "protocol": manifest.get("protocol", "TE-REAL-PANEL-BENCH-20260914"),
        "status": "COMPLETED",
        "scope": "REAL_REGION_FEASIBILITY_AND_T2_CONCORDANCE_ONLY",
        "truth_available": False,
        "absolute_precision": None,
        "absolute_f1": None,
        "metric_scope": [
            "callable_bp_coverage",
            "callable_intersection",
            "callable_jaccard",
            "candidate_fragment_count",
        ],
        "expected_cell_count": len(cell_results),
        "status_counts": dict(sorted(status_counts.items())),
        "cells": cell_results,
        "pairwise": pairwise,
        "source_bundle_manifest": str(bundle_manifest.resolve()),
    }
    write_json(output_dir / "metrics.json", result)
    return result


def collect_summary(
    metrics_paths: Iterable[Path], registry_paths: Iterable[Path], output_dir: Path
) -> dict[str, Any]:
    registry_values = []
    for path in registry_paths:
        if path.is_file():
            try:
                value = read_json(path)
            except (OSError, json.JSONDecodeError, ValueError):
                continue
            if isinstance(value.get("expected_cells"), list):
                registry_values.append(value)
    if len(registry_values) != 1:
        raise ValueError(f"expected one registry, found {len(registry_values)}")
    registry = registry_values[0]

    metric_values: list[dict[str, Any]] = []
    for path in metrics_paths:
        if path.is_file():
            try:
                metric_values.append(read_json(path))
            except (OSError, json.JSONDecodeError, ValueError):
                continue
    observed: dict[str, Mapping[str, Any]] = {}
    for value in metric_values:
        cells = value.get("cells")
        if isinstance(cells, list):
            for row in cells:
                if isinstance(row, dict) and isinstance(row.get("cell_id"), str):
                    observed[row["cell_id"]] = row

    rows: list[dict[str, Any]] = []
    for expected in registry["expected_cells"]:
        cell_id = str(expected["cell_id"])
        evidence = observed.get(cell_id)
        if evidence is None:
            # A missing output is explicitly NOTRUN in this collector.  It is
            # retained in the denominator and is never converted to a zero.
            status = "NOTRUN"
            evidence_state = "registry_only"
            reason = "no metrics evidence for registry cell"
            metrics = None
        else:
            status = normal_status(evidence.get("status"))
            evidence_state = "observed"
            reason = evidence.get("reason")
            metrics = evidence.get("metrics")
        row = {
            "cell_id": cell_id,
            "species": expected.get("species"),
            "method": expected.get("method"),
            "task": expected.get("task"),
            "device": expected.get("device"),
            "expected_status": expected.get("expected_status"),
            "status": status,
            "evidence": evidence_state,
            "reason": reason,
            "metrics": metrics,
        }
        rows.append(row)
    status_counts = Counter(str(row["status"]) for row in rows)
    result = {
        "schema": "te_real_panel_t2_collector_v1",
        "protocol": "TE-REAL-PANEL-BENCH-20260914",
        "scope": "REAL_REGION_FEASIBILITY_AND_T2_CONCORDANCE_ONLY",
        "truth_available": False,
        "absolute_precision": None,
        "absolute_f1": None,
        "expected_cell_count": len(rows),
        "observed_cell_count": sum(row["evidence"] == "observed" for row in rows),
        "scored_cell_count": sum(row["status"] == "COMPLETED" and row["metrics"] is not None for row in rows),
        "status_counts": dict(sorted(status_counts.items())),
        "cells": rows,
        "metric_files": [str(path) for path in metrics_paths],
    }
    write_json(output_dir / "collector_summary.json", result)
    return result


def run_data(args: argparse.Namespace) -> None:
    bundle = args.bundle
    if bundle is None:
        raw = os.environ.get("TE_REAL_PANEL_BUNDLE")
        if not raw:
            raise ValueError("set TE_REAL_PANEL_BUNDLE or pass --bundle to the data module")
        bundle = Path(raw)
    bundle = bundle.resolve()
    manifest_path = bundle / "manifest.json"
    registry_path = bundle / "cell_registry.json"
    manifest, registry, _ = load_bundle(manifest_path, registry_path)
    if manifest.get("raw_fasta_copied") or manifest.get("probabilities_copied"):
        raise ValueError("compact bundle unexpectedly contains raw FASTA/probability material")
    # The Slurm exporter records its source-side absolute root for provenance.
    # Omni replays a copied compact bundle on another host, so stage paths must
    # resolve from the local bundle supplied to this data module.
    materialized_manifest = {
        **manifest,
        "bundle_root_source": manifest.get("bundle_root"),
        "bundle_root": str(bundle),
        "stage_source_manifest": str(manifest_path),
    }
    write_json(
        args.output_dir / "bundle_manifest.json",
        materialized_manifest,
    )
    write_json(args.output_dir / "cell_registry.json", registry)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--bundle", type=Path)
    path_arg(parser, "--data.bundle_manifest")
    path_arg(parser, "--data.cell_registry", many=True)
    path_arg(parser, "--metrics.score", many=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.name == "bundle":
        run_data(args)
    elif args.name == "score":
        bundle_manifest = args.data_bundle_manifest
        registry = first_path(args.data_cell_registry)
        if bundle_manifest is None:
            raise ValueError("score requires data.bundle_manifest")
        score_bundle(bundle_manifest, registry, args.output_dir)
    elif args.name == "summary":
        collect_summary(args.metrics_score or [], args.data_cell_registry or [], args.output_dir)
    else:
        raise ValueError(f"unexpected real-panel module name: {args.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
