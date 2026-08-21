#!/usr/bin/env python3
"""Summarize PIPE-TEFM-SUPP-20260617 screen results.

This is intentionally read-only over experiment outputs. It tolerates missing
JSON files so it can be rerun while Slurm arrays are still completing.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path


METRIC_KEYS = [
    "te_f1",
    "te_precision",
    "te_recall",
    "te_auprc",
    "macro_f1",
    "bg_f1",
    "n_windows",
    "n_labeled_tokens",
]

GROUP = {
    "human": "vertebrate",
    "mouse": "vertebrate",
    "zebrafish": "vertebrate",
    "chicken": "vertebrate",
    "western_clawed_frog": "vertebrate",
    "c_elegans": "invertebrate",
    "fruit_fly": "invertebrate",
    "rice": "plant",
    "maize": "plant",
    "sorghum": "plant",
    "brachypodium": "plant",
    "thale_cress": "plant",
    "pig": "vertebrate",
    "cattle": "vertebrate",
    "horse": "vertebrate",
    "opossum": "vertebrate",
    "lizard": "vertebrate",
    "x_laevis": "vertebrate",
    "western_honey_bee": "invertebrate",
    "red_flour_beetle": "invertebrate",
}

# Coarse divergence ordering used only for a screen-level decay sanity check.
# Values are ordinal anchors, not calibrated evolutionary distances.
DISTANCE_FROM_HUMAN = {
    "human": 0.0,
    "mouse": 1.0,
    "pig": 1.2,
    "cattle": 1.2,
    "horse": 1.2,
    "opossum": 2.0,
    "lizard": 2.5,
    "chicken": 2.7,
    "western_clawed_frog": 3.0,
    "x_laevis": 3.0,
    "zebrafish": 3.5,
    "fruit_fly": 5.0,
    "western_honey_bee": 5.0,
    "red_flour_beetle": 5.0,
    "c_elegans": 5.5,
    "rice": 6.0,
    "maize": 6.0,
    "sorghum": 6.0,
    "brachypodium": 6.0,
    "thale_cress": 6.0,
}


def read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def write_tsv(path: Path, rows: list[dict], keys: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: "" if row.get(k) is None else row.get(k) for k in keys})


def as_float(value) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out):
        return None
    return out


def mean(values: list[float]) -> float | None:
    vals = [v for v in values if v is not None and not math.isnan(v)]
    return sum(vals) / len(vals) if vals else None


def median(values: list[float]) -> float | None:
    vals = [v for v in values if v is not None and not math.isnan(v)]
    return statistics.median(vals) if vals else None


def collect_json_metrics(report_root: Path) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(report_root.rglob("*.json")):
        if "_tmp_eval" in path.parts or path.name.endswith("_summary.json"):
            continue
        data = read_json(path)
        if not isinstance(data, dict):
            continue
        if not any(k in data for k in ("te_f1", "te_auprc", "macro_f1")):
            continue
        row = {
            "path": str(path),
            "stage": data.get("stage") or infer_stage(path),
            "model_key": data.get("model_key") or infer_model(path),
            "model": data.get("model"),
            "window": data.get("window"),
            "species": data.get("species") or infer_species(path),
            "group": GROUP.get(data.get("species") or infer_species(path), "unknown"),
        }
        for key in METRIC_KEYS:
            row[key] = data.get(key)
        rows.append(row)
    return rows


def infer_stage(path: Path) -> str:
    for part in path.parts:
        if part.startswith("transfer_") or part.startswith("downstream_"):
            return part
    return ""


def infer_model(path: Path) -> str:
    parts = list(path.parts)
    for i, part in enumerate(parts):
        if part.startswith("transfer_") and i + 1 < len(parts):
            return parts[i + 1]
        if part.startswith("downstream_") and i + 1 < len(parts):
            return parts[i + 1]
    return ""


def infer_species(path: Path) -> str:
    return path.stem


def collect_window_results(runs_root: Path) -> list[dict]:
    rows = []
    for result in sorted(runs_root.glob("TFSUPP_*_H0_w*_seed42/test_results.json")):
        data = read_json(result)
        if not data:
            continue
        run = result.parent.name
        parts = run.split("_")
        model = "_".join(parts[1:-3])
        window = int(parts[-2].lstrip("w"))
        row = {
            "path": str(result),
            "stage": "human_H0_window_sweep",
            "model_key": model,
            "window": window,
            "species": "human",
            "group": "vertebrate",
        }
        for key in METRIC_KEYS:
            row[key] = data.get(key)
        rows.append(row)
    return rows


def collect_edge_rows(report_root: Path) -> list[dict]:
    rows = []
    edge_root = report_root / "edge_H0_window"
    if not edge_root.exists():
        return rows
    for path in sorted(edge_root.glob("*.tsv")):
        with path.open(newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                row["path"] = str(path)
                rows.append(row)
    return rows


def summarize_edges(rows: list[dict]) -> list[dict]:
    buckets: dict[tuple, dict[str, dict]] = {}
    for row in rows:
        key = (row.get("stage"), row.get("model_key"), row.get("window"), row.get("species"))
        buckets.setdefault(key, {})[row.get("position_bin")] = row
    out = []
    for key, by_bin in sorted(buckets.items()):
        center = by_bin.get("center_25_75")
        left = by_bin.get("edge_left_10")
        right = by_bin.get("edge_right_10")
        if not center or not left or not right:
            continue
        center_f1 = as_float(center.get("te_f1"))
        left_f1 = as_float(left.get("te_f1"))
        right_f1 = as_float(right.get("te_f1"))
        edge_mean = mean([left_f1, right_f1])
        out.append({
            "stage": key[0],
            "model_key": key[1],
            "window": key[2],
            "species": key[3],
            "center_te_f1": center_f1,
            "left_edge_te_f1": left_f1,
            "right_edge_te_f1": right_f1,
            "mean_edge_te_f1": edge_mean,
            "edge_minus_center_te_f1": None if edge_mean is None or center_f1 is None else edge_mean - center_f1,
            "center_te_auprc": as_float(center.get("te_auprc")),
            "edge_left_te_auprc": as_float(left.get("te_auprc")),
            "edge_right_te_auprc": as_float(right.get("te_auprc")),
            "interpretation": "negative means window edges underperform center",
        })
    return out


def aggregate(rows: list[dict], group_keys: list[str]) -> list[dict]:
    buckets: dict[tuple, list[dict]] = {}
    for row in rows:
        buckets.setdefault(tuple(row.get(k) for k in group_keys), []).append(row)
    out = []
    for key, vals in sorted(buckets.items()):
        item = dict(zip(group_keys, key))
        item["n_species"] = len({v.get("species") for v in vals if v.get("species")})
        item["n_rows"] = len(vals)
        for metric in ["te_f1", "te_auprc", "macro_f1", "te_precision", "te_recall"]:
            nums = [as_float(v.get(metric)) for v in vals]
            item[f"mean_{metric}"] = mean(nums)
            item[f"median_{metric}"] = median(nums)
        out.append(item)
    return out


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    deny = math.sqrt(sum((y - my) ** 2 for y in ys))
    if denx == 0 or deny == 0:
        return None
    return num / (denx * deny)


def decay_rows(rows: list[dict]) -> list[dict]:
    out = []
    for stage in sorted({r.get("stage") for r in rows if r.get("stage")}):
        stage_rows = [r for r in rows if r.get("stage") == stage]
        for model in sorted({r.get("model_key") for r in stage_rows if r.get("model_key")}):
            vals = []
            for row in stage_rows:
                if row.get("model_key") != model:
                    continue
                species = row.get("species")
                f1 = as_float(row.get("te_f1"))
                dist = DISTANCE_FROM_HUMAN.get(species)
                if f1 is not None and dist is not None:
                    vals.append((dist, f1, species))
            if len(vals) < 3:
                continue
            vals.sort()
            xs = [v[0] for v in vals]
            ys = [v[1] for v in vals]
            corr = pearson(xs, ys)
            # Least-squares slope for f1 ~ a + b * distance.
            mx = sum(xs) / len(xs)
            my = sum(ys) / len(ys)
            denom = sum((x - mx) ** 2 for x in xs)
            slope = None if denom == 0 else sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom
            out.append({
                "stage": stage,
                "model_key": model,
                "n": len(vals),
                "pearson_distance_vs_f1": corr,
                "linear_slope_f1_per_distance_unit": slope,
                "note": "ordinal-distance screen only; abandon as claim formula if correlation is weak or sign-inconsistent",
            })
    return out


def is_downstream_stage(stage: str | None) -> bool:
    text = str(stage or "")
    return (
        text.startswith("downstream_")
        or text.startswith("mouse_to_")
        or text.startswith("mixedA2_to_")
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-root", default="reports/tefm_supp/PIPE-TEFM-SUPP-20260617")
    ap.add_argument("--runs-root", default="software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617/runs")
    ap.add_argument("--out-dir", default="reports/tefm_supp/PIPE-TEFM-SUPP-20260617/summaries")
    args = ap.parse_args()

    report_root = Path(args.report_root)
    runs_root = Path(args.runs_root)
    out_dir = Path(args.out_dir)
    rows = collect_json_metrics(report_root) + collect_window_results(runs_root)
    rows = sorted(rows, key=lambda r: (str(r.get("stage")), str(r.get("model_key")), int(r.get("window") or 0), str(r.get("species"))))

    metric_keys = ["path", "stage", "model_key", "model", "window", "species", "group", *METRIC_KEYS]
    write_tsv(out_dir / "all_metrics.tsv", rows, metric_keys)

    transfer = [r for r in rows if str(r.get("stage")).startswith("transfer_")]
    downstream = [r for r in rows if is_downstream_stage(r.get("stage"))]
    window = [r for r in rows if r.get("stage") == "human_H0_window_sweep"]

    write_tsv(out_dir / "window_sweep.tsv", window, metric_keys)
    write_tsv(out_dir / "transfer_by_species.tsv", transfer, metric_keys)
    write_tsv(out_dir / "downstream_by_species.tsv", downstream, metric_keys)

    agg_keys = [
        "stage", "model_key", "window", "group", "n_species", "n_rows",
        "mean_te_f1", "median_te_f1", "mean_te_auprc", "median_te_auprc",
        "mean_macro_f1", "median_macro_f1", "mean_te_precision", "mean_te_recall",
    ]
    transfer_agg = aggregate(transfer, ["stage", "model_key", "window", "group"])
    downstream_agg = aggregate(downstream, ["stage", "model_key", "window", "group"])
    transfer_all = aggregate(transfer, ["stage", "model_key", "window"])
    downstream_all = aggregate(downstream, ["stage", "model_key", "window"])
    write_tsv(out_dir / "transfer_summary.tsv", transfer_agg + transfer_all, agg_keys)
    write_tsv(out_dir / "downstream_summary.tsv", downstream_agg + downstream_all, agg_keys)

    decay = decay_rows(transfer + downstream)
    write_tsv(out_dir / "decay_screen.tsv", decay, [
        "stage", "model_key", "n", "pearson_distance_vs_f1",
        "linear_slope_f1_per_distance_unit", "note",
    ])

    edge_rows = collect_edge_rows(report_root)
    if edge_rows:
        write_tsv(out_dir / "edge_position_bins.tsv", edge_rows, [
            "path", "stage", "model_key", "window", "species", "position_bin",
            "te_f1", "te_precision", "te_recall", "te_auprc", "macro_f1",
            "bg_f1", "n_labeled_tokens", "te_positive_rate", "n_windows",
            "model_dir", "data_dir",
        ])
        edge_summary = summarize_edges(edge_rows)
        write_tsv(out_dir / "edge_summary.tsv", edge_summary, [
            "stage", "model_key", "window", "species", "center_te_f1",
            "left_edge_te_f1", "right_edge_te_f1", "mean_edge_te_f1",
            "edge_minus_center_te_f1", "center_te_auprc", "edge_left_te_auprc",
            "edge_right_te_auprc", "interpretation",
        ])

    best_window = sorted(
        [r for r in window if as_float(r.get("te_f1")) is not None],
        key=lambda r: as_float(r.get("te_f1")),
        reverse=True,
    )[:5]
    best_transfer = sorted(
        [r for r in transfer_all if as_float(r.get("mean_te_f1")) is not None],
        key=lambda r: as_float(r.get("mean_te_f1")),
        reverse=True,
    )[:5]
    status = {
        "n_metric_rows": len(rows),
        "n_window_rows": len(window),
        "n_transfer_rows": len(transfer),
        "n_downstream_rows": len(downstream),
        "n_edge_rows": len(edge_rows),
        "best_window_by_te_f1": best_window,
        "best_transfer_by_mean_te_f1": best_transfer,
        "screen_limitations": [
            "single seed=42",
            "token-level proxy metrics, not final bp-level claim",
            "quick max_windows truncation samples first eligible chromosome per split/species",
            "one-chromosome transfer evaluation",
            "strict UCSC comparator labels can under-cover non-human TE positives",
        ],
    }
    (out_dir / "current_status.json").write_text(json.dumps(status, indent=2, default=str) + "\n")
    print(json.dumps(status, indent=2, default=str))


if __name__ == "__main__":
    main()
