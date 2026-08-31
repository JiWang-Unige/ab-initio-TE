#!/usr/bin/env python3
"""Summarize completed fragment-gap audits without changing their outputs.

The audit itself is the source of all measurements.  This command only joins
its existing ``truth_summary.tsv``, ``gap_records.tsv``, ``summary.tsv``, and
``run_summary.json`` files into compact overall/length-stratum tables.  It
never computes false positives or precision/F1: those quantities are not
identified by a truth-positive audit.  Every input has an explicit
interpretation field; use ``--positive-only`` for FlyBase-style inputs.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Iterable


BINS = ("overall", "<80", "80-499", "500-999", ">=1000")
RELATIVE_BINS = (
    ("lt_0_10", 0.0, 0.10),
    ("0_10_0_25", 0.10, 0.25),
    ("0_25_0_50", 0.25, 0.50),
    ("0_50_0_75", 0.50, 0.75),
    ("0_75_0_90", 0.75, 0.90),
    ("ge_0_90", 0.90, 1.0000000001),
)
SEAM_LIMITS = (0, 5, 25, 100)
GAP_LENGTH_LIMITS = (1, 2, 5, 10, 25, 100)
QUANTILES = ("p50", "p90", "p95", "p99", "max")


def _rows(path: Path) -> Iterable[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"missing header: {path}")
        yield from reader


def _number(value: str, label: str) -> float:
    try:
        return float(value)
    except ValueError as error:
        raise ValueError(f"invalid number for {label}: {value!r}") from error


def _integer(value: str, label: str) -> int:
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"invalid integer for {label}: {value!r}") from error


def _percentile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _quantiles(values: list[float]) -> dict[str, float | None]:
    return {
        "p50": _percentile(values, 0.50),
        "p90": _percentile(values, 0.90),
        "p95": _percentile(values, 0.95),
        "p99": _percentile(values, 0.99),
        "max": max(values) if values else None,
    }


def _ratio(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def _label_path(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise ValueError(f"expected LABEL=PATH, got {value!r}")
    label, path = value.split("=", 1)
    if not label or not path:
        raise ValueError(f"expected non-empty LABEL=PATH, got {value!r}")
    return label, Path(path)


def _manifest(path: Path) -> list[tuple[str, Path, str | None]]:
    entries: list[tuple[str, Path, str | None]] = []
    with path.open(encoding="utf-8") as handle:
        lines = [line.rstrip("\r\n") for line in handle if line.strip() and not line.lstrip().startswith("#")]
    if not lines:
        raise ValueError(f"empty manifest: {path}")
    first = lines[0].split("\t")
    has_header = {field.strip().lower() for field in first} >= {"label", "path"}
    data = lines[1:] if has_header else lines
    for line in data:
        fields = line.split("\t")
        if len(fields) == 1 and "=" in fields[0]:
            label, audit_path = _label_path(fields[0])
            mode = None
        elif len(fields) in (2, 3):
            label, audit_path = fields[:2]
            mode = fields[2] if len(fields) == 3 and fields[2] else None
            if not label or not audit_path:
                raise ValueError(f"invalid manifest row: {line!r}")
        else:
            raise ValueError(f"manifest rows need label, path[, interpretation]: {line!r}")
        entries.append((label, Path(audit_path), mode))
    return entries


def _parse_mode(values: list[str], option: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"{option} expects LABEL=VALUE, got {value!r}")
        label, mode = value.split("=", 1)
        if not label or not mode:
            raise ValueError(f"{option} expects non-empty LABEL=VALUE, got {value!r}")
        if label in result:
            raise ValueError(f"duplicate label in {option}: {label}")
        result[label] = mode
    return result


def _float_field(row: dict[str, str], field: str, label: str) -> float:
    value = row.get(field, "")
    if value == "":
        raise ValueError(f"missing {field} for {label}")
    return _number(value, f"{label}.{field}")


def _int_field(row: dict[str, str], field: str, label: str) -> int:
    value = row.get(field, "")
    if value == "":
        raise ValueError(f"missing {field} for {label}")
    return _integer(value, f"{label}.{field}")


def _empty_stratum() -> dict[str, object]:
    return {
        "truth_intervals": 0,
        "truth_bp": 0,
        "covered_bp": 0,
        "truth_with_positive": 0,
        "missed_truth_intervals": 0,
        "split_truth_intervals": 0,
        "observed_fragments": 0,
        "internal_gap_truth_intervals": 0,
        "observed_internal_gaps": 0,
        "internal_gap_bp": 0,
        "terminal_gap_records": 0,
        "left_terminal_gap_records": 0,
        "right_terminal_gap_records": 0,
        "terminal_gap_bp": 0,
        "left_terminal_gap_bp": 0,
        "right_terminal_gap_bp": 0,
        "iid_expected_fragments": 0.0,
        "iid_expected_internal_gaps": 0.0,
        "iid_expected_any_positive": 0.0,
        "iid_expected_split": 0.0,
        "markov_expected_fragments": 0.0,
        "markov_expected_internal_gaps": 0.0,
        "markov_expected_any_positive": 0.0,
        "markov_expected_split": 0.0,
        "gap_lengths": [],
        "before_run_lengths": [],
        "after_run_lengths": [],
        "between_gap_spacings": [],
        "relative_position_counts": {name: 0 for name, _, _ in RELATIVE_BINS},
        "seam_values": [],
    }


def _add_truth(row: dict[str, str], strata: dict[str, dict[str, object]], label: str) -> None:
    length_bin = row.get("truth_length_bin", "")
    if length_bin not in BINS[1:]:
        raise ValueError(f"unknown truth_length_bin for {label}: {length_bin!r}")
    target = (strata["overall"], strata[length_bin])
    for item in target:
        item["truth_intervals"] = int(item["truth_intervals"]) + 1
        item["truth_bp"] = int(item["truth_bp"]) + _int_field(row, "truth_length", label)
        item["covered_bp"] = int(item["covered_bp"]) + _int_field(row, "covered_bp", label)
        item["truth_with_positive"] = int(item["truth_with_positive"]) + int(not _int_field(row, "missed", label))
        item["missed_truth_intervals"] = int(item["missed_truth_intervals"]) + _int_field(row, "missed", label)
        item["split_truth_intervals"] = int(item["split_truth_intervals"]) + _int_field(row, "split", label)
        item["observed_fragments"] = int(item["observed_fragments"]) + _int_field(row, "positive_runs_overlapping", label)
        item["internal_gap_truth_intervals"] = int(item["internal_gap_truth_intervals"]) + int(_int_field(row, "internal_gap_count", label) > 0)
        item["observed_internal_gaps"] = int(item["observed_internal_gaps"]) + _int_field(row, "internal_gap_count", label)
        item["internal_gap_bp"] = int(item["internal_gap_bp"]) + _int_field(row, "internal_gap_bp", label)
        item["iid_expected_fragments"] = float(item["iid_expected_fragments"]) + _float_field(row, "iid_expected_positive_runs", label)
        item["iid_expected_internal_gaps"] = float(item["iid_expected_internal_gaps"]) + _float_field(row, "iid_expected_internal_gaps", label)
        item["iid_expected_any_positive"] = float(item["iid_expected_any_positive"]) + _float_field(row, "iid_expected_any_positive", label)
        item["iid_expected_split"] = float(item["iid_expected_split"]) + _float_field(row, "iid_expected_split", label)
        item["markov_expected_fragments"] = float(item["markov_expected_fragments"]) + _float_field(row, "markov_expected_positive_runs", label)
        item["markov_expected_internal_gaps"] = float(item["markov_expected_internal_gaps"]) + _float_field(row, "markov_expected_internal_gaps", label)
        item["markov_expected_any_positive"] = float(item["markov_expected_any_positive"]) + _float_field(row, "markov_expected_any_positive", label)
        item["markov_expected_split"] = float(item["markov_expected_split"]) + _float_field(row, "markov_expected_split", label)


def _add_gap(row: dict[str, str], strata: dict[str, dict[str, object]], label: str) -> None:
    event = row.get("event_type", "")
    length_bin = row.get("truth_length_bin", "")
    if length_bin not in BINS[1:]:
        raise ValueError(f"unknown truth_length_bin in gap record for {label}: {length_bin!r}")
    targets = (strata["overall"], strata[length_bin])
    if event != "internal":
        gap_length = _int_field(row, "gap_length", label)
        for item in targets:
            item["terminal_gap_records"] = int(item["terminal_gap_records"]) + 1
            item["terminal_gap_bp"] = int(item["terminal_gap_bp"]) + gap_length
            if event == "left_terminal":
                item["left_terminal_gap_records"] = int(item["left_terminal_gap_records"]) + 1
                item["left_terminal_gap_bp"] = int(item["left_terminal_gap_bp"]) + gap_length
            elif event == "right_terminal":
                item["right_terminal_gap_records"] = int(item["right_terminal_gap_records"]) + 1
                item["right_terminal_gap_bp"] = int(item["right_terminal_gap_bp"]) + gap_length
        return
    gap_length = _int_field(row, "gap_length", label)
    before = row.get("before_positive_run_length", "")
    after = row.get("after_positive_run_length", "")
    seam = row.get("nearest_window_seam_abs_distance", "")
    relative = _float_field(row, "relative_mid", label)
    relative_name = next(name for name, lower, upper in RELATIVE_BINS if lower <= relative < upper)
    for item in targets:
        item["gap_lengths"].append(float(gap_length))
        if before != "":
            item["before_run_lengths"].append(_number(before, f"{label}.before_positive_run_length"))
        if after != "":
            item["after_run_lengths"].append(_number(after, f"{label}.after_positive_run_length"))
        item["relative_position_counts"][relative_name] += 1
        if seam not in ("", "NA"):
            item["seam_values"].append(_number(seam, f"{label}.nearest_window_seam_abs_distance"))


def _row(label: str, path: Path, interpretation: str, stratum: str, value: dict[str, object], run_summary: dict[str, object]) -> dict[str, object]:
    count = int(value["truth_intervals"])
    truth_bp = int(value["truth_bp"])
    internal_gaps = int(value["observed_internal_gaps"])
    gap_bp = int(value["internal_gap_bp"])
    seam_values = value["seam_values"]
    gap_lengths = value["gap_lengths"]
    before_lengths = value["before_run_lengths"]
    after_lengths = value["after_run_lengths"]
    between_gap_spacings = value["between_gap_spacings"]
    row: dict[str, object] = {
        "label": label,
        "audit_path": str(path),
        "truth_interpretation": interpretation,
        "precision_f1_reportable": "0" if interpretation == "positive-only" else "NA",
        "stratum": stratum,
        "truth_intervals": count,
        "truth_bp": truth_bp,
        "covered_bp": int(value["covered_bp"]),
        "bp_recall": _ratio(int(value["covered_bp"]), truth_bp),
        "truth_with_positive": int(value["truth_with_positive"]),
        "truth_with_positive_rate": _ratio(int(value["truth_with_positive"]), count),
        "missed_truth_intervals": int(value["missed_truth_intervals"]),
        "missed_rate": _ratio(int(value["missed_truth_intervals"]), count),
        "split_truth_intervals": int(value["split_truth_intervals"]),
        "split_rate": _ratio(int(value["split_truth_intervals"]), count),
        "observed_fragments": int(value["observed_fragments"]),
        "fragments_per_truth": _ratio(int(value["observed_fragments"]), count),
        "internal_gap_truth_intervals": int(value["internal_gap_truth_intervals"]),
        "internal_gap_truth_rate": _ratio(int(value["internal_gap_truth_intervals"]), count),
        "observed_internal_gaps": internal_gaps,
        "internal_gaps_per_kb_truth": _ratio(internal_gaps * 1000.0, truth_bp),
        "internal_gap_bp": gap_bp,
        "internal_gap_bp_per_truth_bp": _ratio(gap_bp, truth_bp),
        "terminal_gap_records": int(value["terminal_gap_records"]),
        "left_terminal_gap_records": int(value["left_terminal_gap_records"]),
        "right_terminal_gap_records": int(value["right_terminal_gap_records"]),
        "terminal_gap_bp": int(value["terminal_gap_bp"]),
        "left_terminal_gap_bp": int(value["left_terminal_gap_bp"]),
        "right_terminal_gap_bp": int(value["right_terminal_gap_bp"]),
        "terminal_gap_bp_per_truth_bp": _ratio(int(value["terminal_gap_bp"]), truth_bp),
        "iid_expected_fragments": value["iid_expected_fragments"],
        "markov_expected_fragments": value["markov_expected_fragments"],
        "iid_expected_internal_gaps": value["iid_expected_internal_gaps"],
        "markov_expected_internal_gaps": value["markov_expected_internal_gaps"],
        "iid_expected_any_positive_rate": _ratio(float(value["iid_expected_any_positive"]), count),
        "markov_expected_any_positive_rate": _ratio(float(value["markov_expected_any_positive"]), count),
        "iid_expected_split_rate": _ratio(float(value["iid_expected_split"]), count),
        "markov_expected_split_rate": _ratio(float(value["markov_expected_split"]), count),
        "observed_over_iid_fragments": _ratio(float(value["observed_fragments"]), float(value["iid_expected_fragments"])),
        "observed_over_markov_fragments": _ratio(float(value["observed_fragments"]), float(value["markov_expected_fragments"])),
        "observed_over_iid_internal_gaps": _ratio(internal_gaps, float(value["iid_expected_internal_gaps"])),
        "observed_over_markov_internal_gaps": _ratio(internal_gaps, float(value["markov_expected_internal_gaps"])),
        "observed_over_iid_any_positive": _ratio(float(value["truth_with_positive"]), float(value["iid_expected_any_positive"])),
        "observed_over_markov_any_positive": _ratio(float(value["truth_with_positive"]), float(value["markov_expected_any_positive"])),
        "observed_over_iid_split": _ratio(float(value["split_truth_intervals"]), float(value["iid_expected_split"])),
        "observed_over_markov_split": _ratio(float(value["split_truth_intervals"]), float(value["markov_expected_split"])),
        "internal_gap_length_count": len(gap_lengths),
        "before_run_length_count": len(before_lengths),
        "after_run_length_count": len(after_lengths),
        "between_gap_spacing_count": len(between_gap_spacings),
        "seam_observed_count": len(seam_values),
    }
    for prefix, values in (
        ("internal_gap_length", gap_lengths),
        ("before_run_length", before_lengths),
        ("after_run_length", after_lengths),
        ("between_gap_spacing", between_gap_spacings),
    ):
        for quantile, quantile_value in _quantiles(values).items():
            row[f"{prefix}_{quantile}"] = quantile_value
    for limit in GAP_LENGTH_LIMITS:
        row[f"internal_gap_length_le_{limit}_fraction"] = _ratio(
            sum(length <= limit for length in gap_lengths), len(gap_lengths),
        )
    relative_counts = value["relative_position_counts"]
    relative_total = sum(relative_counts.values())
    for name, _, _ in RELATIVE_BINS:
        row[f"relative_{name}_count"] = relative_counts[name]
        row[f"relative_{name}_fraction"] = _ratio(relative_counts[name], relative_total)
    for limit in SEAM_LIMITS:
        row[f"seam_le_{limit}_fraction"] = _ratio(sum(distance <= limit for distance in seam_values), len(seam_values))
    global_info = run_summary.get("global", {})
    row["truth_intervals_before_exclusion"] = global_info.get("truth_intervals_before_exclusion", "NA") if stratum == "overall" else "NA"
    row["excluded_truth_intervals"] = global_info.get("excluded_truth_intervals", "NA") if stratum == "overall" else "NA"
    row["excluded_truth_bp"] = global_info.get("excluded_truth_bp", "NA") if stratum == "overall" else "NA"
    row["truth_union_applied"] = run_summary.get("truth_union_applied", "NA") if stratum == "overall" else "NA"
    row["windows_supplied"] = global_info.get("windows_supplied", "NA") if stratum == "overall" else "NA"
    return row


def summarize(label: str, path: Path, interpretation: str) -> list[dict[str, object]]:
    truth_path = path / "truth_summary.tsv"
    gap_path = path / "gap_records.tsv"
    summary_path = path / "summary.tsv"
    run_path = path / "run_summary.json"
    for required in (truth_path, gap_path, summary_path, run_path):
        if not required.is_file():
            raise FileNotFoundError(f"audit output missing {required}")
    with run_path.open(encoding="utf-8") as handle:
        run_summary = json.load(handle)
    # Reading the stratum table validates that the completed audit contains its
    # expected bin artifact; all values below are recomputed from row-level
    # outputs so overall values remain explicit and auditable.
    list(_rows(summary_path))
    strata = {name: _empty_stratum() for name in BINS}
    for truth_row in _rows(truth_path):
        _add_truth(truth_row, strata, label)
    gap_rows = list(_rows(gap_path))
    for gap_row in gap_rows:
        _add_gap(gap_row, strata, label)
    internal_by_truth: dict[str, list[dict[str, str]]] = {}
    for gap_row in gap_rows:
        if gap_row.get("event_type") == "internal":
            internal_by_truth.setdefault(gap_row["truth_id"], []).append(gap_row)
    for rows in internal_by_truth.values():
        rows.sort(key=lambda row: _int_field(row, "gap_start", label))
        for left, right in zip(rows, rows[1:]):
            spacing = _int_field(right, "gap_start", label) - _int_field(left, "gap_end", label)
            length_bin = left["truth_length_bin"]
            strata["overall"]["between_gap_spacings"].append(float(spacing))
            strata[length_bin]["between_gap_spacings"].append(float(spacing))
    return [_row(label, path, interpretation, name, strata[name], run_summary) for name in BINS if strata[name]["truth_intervals"]]


FIELDS = [
    "label", "audit_path", "truth_interpretation", "precision_f1_reportable", "stratum",
    "truth_intervals", "truth_bp", "covered_bp", "bp_recall", "truth_with_positive",
    "truth_with_positive_rate", "missed_truth_intervals", "missed_rate", "split_truth_intervals",
    "split_rate", "observed_fragments", "fragments_per_truth", "internal_gap_truth_intervals",
    "internal_gap_truth_rate", "observed_internal_gaps", "internal_gaps_per_kb_truth",
    "internal_gap_bp", "internal_gap_bp_per_truth_bp", "terminal_gap_records",
    "left_terminal_gap_records", "right_terminal_gap_records", "terminal_gap_bp", "left_terminal_gap_bp",
    "right_terminal_gap_bp", "terminal_gap_bp_per_truth_bp", "iid_expected_fragments",
    "markov_expected_fragments", "iid_expected_internal_gaps", "markov_expected_internal_gaps",
    "iid_expected_any_positive_rate", "markov_expected_any_positive_rate", "iid_expected_split_rate",
    "markov_expected_split_rate", "observed_over_iid_fragments", "observed_over_markov_fragments",
    "observed_over_iid_internal_gaps", "observed_over_markov_internal_gaps", "observed_over_iid_any_positive",
    "observed_over_markov_any_positive", "observed_over_iid_split", "observed_over_markov_split",
    "internal_gap_length_count", "before_run_length_count", "after_run_length_count",
    "between_gap_spacing_count", "seam_observed_count",
]
for _prefix in ("internal_gap_length", "before_run_length", "after_run_length", "between_gap_spacing"):
    FIELDS.extend(f"{_prefix}_{quantile}" for quantile in QUANTILES)
FIELDS.extend(f"internal_gap_length_le_{limit}_fraction" for limit in GAP_LENGTH_LIMITS)
for _name, _, _ in RELATIVE_BINS:
    FIELDS.extend((f"relative_{_name}_count", f"relative_{_name}_fraction"))
FIELDS.extend(f"seam_le_{limit}_fraction" for limit in SEAM_LIMITS)
FIELDS.extend(("truth_intervals_before_exclusion", "excluded_truth_intervals", "excluded_truth_bp", "truth_union_applied", "windows_supplied"))


def _format(value: object) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.12g}"
    return str(value)


def _write_tsv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _format(row.get(field)) for field in FIELDS})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", action="append", default=[], metavar="LABEL=PATH", help="completed audit directory; repeatable")
    parser.add_argument("--manifest", type=Path, help="TSV with label, path, and optional interpretation columns")
    parser.add_argument("--truth-mode", action="append", default=[], metavar="LABEL=MODE", help="explicit interpretation override")
    parser.add_argument("--positive-only", action="append", default=[], metavar="LABEL", help="mark LABEL as positive-only (no precision/F1)")
    parser.add_argument("--output-tsv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()
    if not args.audit and not args.manifest:
        parser.error("provide --audit or --manifest")
    entries: list[tuple[str, Path, str | None]] = []
    entries.extend((*_label_path(value), None) for value in args.audit)
    if args.manifest:
        entries.extend(_manifest(args.manifest))
    labels: set[str] = set()
    for label, _, _ in entries:
        if label in labels:
            raise ValueError(f"duplicate audit label: {label}")
        labels.add(label)
    modes = _parse_mode(args.truth_mode, "--truth-mode")
    positive_only = set(args.positive_only)
    unknown_modes = (set(modes) | positive_only) - labels
    if unknown_modes:
        raise ValueError(f"interpretation supplied for unknown label(s): {', '.join(sorted(unknown_modes))}")
    all_rows: list[dict[str, object]] = []
    for label, path, manifest_mode in entries:
        if label in positive_only and label in modes:
            raise ValueError(f"both --positive-only and --truth-mode supplied for {label}")
        interpretation = "positive-only" if label in positive_only else modes.get(label, manifest_mode or "unspecified")
        all_rows.extend(summarize(label, path, interpretation))
    _write_tsv(args.output_tsv, all_rows)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "fragment_gap_topology_summary_v1",
            "interpretation_policy": "unspecified unless supplied; positive-only never permits precision/F1",
            "relative_position_bins": [name for name, _, _ in RELATIVE_BINS],
            "gap_length_limits_bp": list(GAP_LENGTH_LIMITS),
            "seam_limits_bp": list(SEAM_LIMITS),
            "rows": all_rows,
        }
        args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
