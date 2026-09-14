#!/usr/bin/env python3
"""Audit the SF5 ontology and stratify fixed-D external comparator errors.

This is a bounded retrospective analysis.  It does not load a model, alter a
threshold, choose regions, or change any frozen score.  Part A streams the
already materialised six-label windows and checks the mapper/denominators.
Part B reads saved D probabilities and the fixed comparator annotations for
the sea-urchin alternative library and platypus Label-A, then reports
row-level recovery strata.  RepeatMasker records are not treated as insertion
identities, and sparse comparator negatives remain unknown.
"""
from __future__ import annotations

import argparse
import ast
import collections
import csv
import gzip
import importlib.util
import json
import math
import time
import traceback
from pathlib import Path
from typing import Any, Iterable, Iterator

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[3]
ADAPTER_PATH = REPO_ROOT / "scripts/experiments/LEMMI-TE-BENCH-20260824-R1/adapter.py"

SF5_NAMES = {0: "BG", 1: "SINE", 2: "LINE", 3: "LTR", 4: "DNA", 5: "Unknown"}
MAIN4 = {"SINE", "LINE", "LTR", "DNA"}
STRICT_TE_CLASSES = {"LINE", "SINE", "LTR", "DNA", "RC", "RETROPOSON"}
UNKNOWN_CLASSES = {"unknown", "unclassified"}
HARD_NON_TE_CLASSES = {
    "low_complexity",
    "satellite",
    "scrna",
    "simple_repeat",
    "snrna",
    "srprna",
    "tandem_repeat",
    "trna",
    "rrna",
    "rna",
}
EXCLUDED_NON_TE_CLASSES = {"artefact", "artifact"}


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = _load_module(ADAPTER_PATH, "ontology_external_adapter")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def extract_mapper(path: Path):
    """Extract only the pure SF5 mapper from the recorded source file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    function = next(
        (node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
         and node.name == "map_sf5"),
        None,
    )
    if function is None:
        raise ValueError(f"map_sf5 not found in {path}")
    module = ast.Module(body=[function], type_ignores=[])
    namespace: dict[str, Any] = {}
    exec(compile(module, str(path), "exec"), namespace)
    return namespace["map_sf5"]


def _metadata_label_counts(class_bp: dict[str, Any]) -> dict[int, int]:
    reverse = {name: index for index, name in SF5_NAMES.items()}
    result: dict[int, int] = {}
    for name, value in class_bp.items():
        if name not in reverse:
            raise ValueError(f"metadata contains unexpected class {name!r}")
        result[reverse[name]] = int(value)
    return result


def stream_window_split(path: Path, expected_window: int) -> dict[str, Any]:
    counts: collections.Counter[int] = collections.Counter()
    species_counts: collections.Counter[str] = collections.Counter()
    record_count = 0
    length_bp = 0
    errors: list[str] = []
    opener = gzip.open if path.name.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            record_count += 1
            row = json.loads(line)
            sequence = str(row.get("sequence", ""))
            labels = row.get("labels")
            if not isinstance(labels, list):
                errors.append(f"line {line_no}: labels is not a list")
                continue
            if len(labels) != len(sequence) or len(labels) != expected_window:
                errors.append(
                    f"line {line_no}: sequence/label/window lengths "
                    f"{len(sequence)}/{len(labels)}/{expected_window}"
                )
            start = int(row.get("start", -1))
            end = int(row.get("end", -1))
            if end - start != len(labels):
                errors.append(f"line {line_no}: coordinate span {start}-{end} != {len(labels)}")
            bad = [value for value in labels if not isinstance(value, int) or value not in SF5_NAMES]
            if bad:
                errors.append(f"line {line_no}: unexpected labels {bad[:5]!r}")
            counts.update(value for value in labels if isinstance(value, int) and value in SF5_NAMES)
            length_bp += len(labels)
            species_counts[str(row.get("species_code", ""))] += 1
            if len(errors) >= 10:
                break
    if errors:
        raise ValueError(f"invalid window data in {path}: {errors}")
    return {
        "records": record_count,
        "length_bp": int(length_bp),
        "class_bp": {SF5_NAMES[key]: int(counts.get(key, 0)) for key in sorted(SF5_NAMES)},
        "species_windows": dict(sorted(species_counts.items())),
    }


def denominators(class_bp: dict[str, Any]) -> dict[str, int]:
    values = {name: int(class_bp.get(name, 0)) for name in SF5_NAMES.values()}
    return {
        "all6_bp": sum(values.values()),
        "bg_bp": values["BG"],
        "main4_bp": sum(values[name] for name in ("SINE", "LINE", "LTR", "DNA")),
        "unknown_bp": values["Unknown"],
        "main4_plus_unknown_te_like_bp": sum(values[name] for name in ("SINE", "LINE", "LTR", "DNA", "Unknown")),
    }


def pick_legacy_scores(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    fields = {
        "stage",
        "window",
        "unknown_support_bp",
        "unknown_recall",
        "unknown_precision",
        "unknown_f1",
        "main4_conditional_macro_f1",
        "macro_f1_all6",
        "te_detect_f1",
        "main4_false_unknown_rate",
        "unknown_to_main4_rate",
        "accuracy",
    }
    result: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", errors="replace", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            picked: dict[str, Any] = {}
            for key in fields:
                if key not in row:
                    continue
                value = row[key]
                if value in {"", "NA", "null", "None"}:
                    picked[key] = None
                else:
                    number = finite_float(value)
                    picked[key] = number if number is not None else value
            result.append(picked)
    return result


def audit_ontology(root: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    settings = cfg["ontology"]
    dataset = resolve(root, str(settings["dataset_relpath"]))
    mapper_path = resolve(root, str(settings["mapper_relpath"]))
    label_map_path = dataset / "label_map.json"
    metadata_path = dataset / "metadata.json"
    for path in (dataset, mapper_path, label_map_path, metadata_path):
        if not path.exists():
            raise FileNotFoundError(f"ontology input missing: {path}")
    expected_map = {str(key): value for key, value in settings["expected_label_map"].items()}
    observed_map = read_json(label_map_path)
    mapper = extract_mapper(mapper_path)
    probe_results = []
    for probe in settings["probe_rows"]:
        got_id = int(mapper(probe["rep_class"], probe.get("rep_family", ""), probe.get("rep_name", "")))
        got = SF5_NAMES.get(got_id, f"id:{got_id}")
        probe_results.append({
            "id": probe["id"],
            "semantic": probe["semantic"],
            "expected": probe["expected"],
            "observed": got,
            "pass": got == probe["expected"],
        })
    metadata = read_json(metadata_path)
    split_results: dict[str, Any] = {}
    all_counts: collections.Counter[str] = collections.Counter()
    consistency_errors: list[str] = []
    for split in settings["splits"]:
        split_path = dataset / split / "data.jsonl.gz"
        if not split_path.is_file():
            raise FileNotFoundError(f"ontology split missing: {split_path}")
        stream = stream_window_split(split_path, int(metadata.get("window", 4096)))
        split_meta = metadata.get("splits", {}).get(split, {})
        metadata_bp = {name: int(value) for name, value in split_meta.get("class_bp", {}).items()}
        class_match = stream["class_bp"] == {name: int(metadata_bp.get(name, 0)) for name in SF5_NAMES.values()}
        if not class_match:
            consistency_errors.append(f"{split}: stream class counts differ from metadata")
        expected_species = {
            species: int(row.get("windows", 0))
            for species, row in split_meta.get("per_species", {}).items()
        }
        species_match = stream["species_windows"] == dict(sorted(expected_species.items()))
        if not species_match:
            consistency_errors.append(f"{split}: stream species windows differ from metadata")
        split_results[split] = {
            "stream": stream,
            "metadata_class_bp": {name: int(metadata_bp.get(name, 0)) for name in SF5_NAMES.values()},
            "metadata_match": class_match,
            "species_metadata": dict(sorted(expected_species.items())),
            "species_match": species_match,
            "denominators": denominators(stream["class_bp"]),
        }
        all_counts.update(stream["class_bp"])
    known_other_probe = [row for row in probe_results if row["semantic"] == "known_other_te"]
    mapping_ok = all(row["pass"] for row in probe_results)
    observed_label_map_match = observed_map == expected_map
    historical_path = resolve(root, str(settings["historical_unknown_relpath"]))
    historical = read_json(historical_path) if historical_path.is_file() else None
    return {
        "status": "COMPLETED",
        "dataset": str(dataset),
        "mapper_source": str(mapper_path),
        "label_map_source": str(label_map_path),
        "metadata_source": str(metadata_path),
        "label_map": {
            "expected": expected_map,
            "observed": observed_map,
            "exact_match": observed_label_map_match,
        },
        "mapper_probe": {
            "rows": probe_results,
            "all_pass": mapping_ok,
            "known_other_te_examples_are_unknown": bool(known_other_probe) and all(
                row["observed"] == "Unknown" and row["pass"] for row in known_other_probe
            ),
            "known_other_te_to_bg": any(
                row["semantic"] == "known_other_te" and row["observed"] == "BG"
                for row in probe_results
            ),
        },
        "train_eval_ontology_consistency": {
            "all_splits_pass": not consistency_errors,
            "errors": consistency_errors,
            "encoded_label_set": sorted(all_counts),
            "aggregate_class_bp": {name: int(all_counts[name]) for name in SF5_NAMES.values()},
            "aggregate_denominators": denominators({name: int(all_counts[name]) for name in SF5_NAMES.values()}),
            "splits": split_results,
        },
        "legacy_scores": pick_legacy_scores(resolve(root, str(settings["legacy_summary_relpath"]))),
        "historical_unknown_sample": historical,
        "interpretation": {
            "legacy_unknown_is_not_one_biological_class": True,
            "known_other_te_is_encoded_as_unknown": True,
            "known_other_te_is_encoded_as_bg": False,
            "unlabelled_bases_are_painted_bg_by_window_builder": True,
            "raw_other_te_vs_true_unclassified_cannot_be_recovered_from_six_ids": True,
            "historical_unknown_sample_has_model_predictions": bool(
                historical and historical.get("model_predictions_used") is True
            ),
            "historical_unknown_sample_is_population_estimate": bool(
                historical and historical.get("representative_population_estimate") is True
            ),
        },
    }


def read_fasta(path: Path) -> dict[str, str]:
    sequences: dict[str, str] = {}
    current: str | None = None
    pieces: list[str] = []
    with gzip.open(path, "rt", encoding="utf-8") if path.name.endswith(".gz") else path.open(
        "rt", encoding="utf-8"
    ) as handle:
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


def iter_repeatmasker(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, 1):
            fields = line.split()
            if not fields or not fields[0].isdigit():
                continue
            if len(fields) < 11:
                raise ValueError(f"truncated RepeatMasker row {line_no} in {path}")
            if fields[8] not in {"C", "+", "-"}:
                raise ValueError(f"invalid RepeatMasker strand at {path}:{line_no}")
            try:
                start = int(fields[5]) - 1
                end = int(fields[6])
            except ValueError as exc:
                raise ValueError(f"invalid RepeatMasker coordinates at {path}:{line_no}") from exc
            divergence = finite_float(fields[1])
            yield {
                "seqid": fields[4],
                "start": start,
                "end": end,
                "name": fields[9],
                "class_family": fields[10],
                "divergence": divergence,
                "raw_length_bp": end - start,
            }


def truth_bucket(class_family: str) -> str:
    value = str(class_family).strip()
    top = value.split("/", 1)[0].strip()
    top_upper = top.upper()
    if top_upper in STRICT_TE_CLASSES and "?" not in value:
        return "known_te"
    lower = top.lower()
    if "?" in value or any(lower.startswith(item) for item in UNKNOWN_CLASSES):
        return "unknown_or_ambiguous"
    if lower in HARD_NON_TE_CLASSES:
        return "hard_non_te"
    if lower in EXCLUDED_NON_TE_CLASSES:
        return "excluded_non_te"
    return "unknown_or_ambiguous"


def class_top(class_family: str) -> str:
    value = str(class_family).strip()
    return value.split("/", 1)[0].strip() or "EMPTY"


def dimension_length(length_bp: int) -> str:
    if length_bp < 80:
        return "<80"
    if length_bp < 500:
        return "80-499"
    if length_bp < 1000:
        return "500-999"
    return ">=1000"


def dimension_divergence(value: float | None) -> str:
    if value is None:
        return "NA"
    if value < 5:
        return "<5"
    if value < 15:
        return "5-15"
    if value < 30:
        return "15-30"
    return ">=30"


def _prefix(values: np.ndarray) -> np.ndarray:
    return np.concatenate((np.array([0], dtype=np.int64), np.cumsum(values.astype(np.int64), dtype=np.int64)))


def _range_sum(prefix: np.ndarray, left: int, right: int) -> int:
    return int(prefix[right] - prefix[left])


def empty_arm_stat() -> dict[str, int]:
    return {
        "rows_with_callable": 0,
        "rows_any_recovered": 0,
        "rows_fully_recovered": 0,
        "rows_fully_missed": 0,
        "callable_bp": 0,
        "predicted_positive_callable_bp": 0,
        "missed_callable_bp": 0,
    }


def update_stat(stat: dict[str, Any], arm_prefix: dict[str, tuple[np.ndarray, np.ndarray]], left: int, right: int) -> None:
    stat["rows"] = int(stat.get("rows", 0)) + 1
    stat["panel_overlap_bp"] = int(stat.get("panel_overlap_bp", 0)) + right - left
    for arm, (callable_prefix, predicted_prefix) in arm_prefix.items():
        callable_bp = _range_sum(callable_prefix, left, right)
        predicted_bp = _range_sum(predicted_prefix, left, right)
        metrics = stat.setdefault("by_arm", {}).setdefault(arm, empty_arm_stat())
        metrics["callable_bp"] += callable_bp
        metrics["predicted_positive_callable_bp"] += predicted_bp
        metrics["missed_callable_bp"] += callable_bp - predicted_bp
        if callable_bp:
            metrics["rows_with_callable"] += 1
            if predicted_bp:
                metrics["rows_any_recovered"] += 1
            if predicted_bp == callable_bp:
                metrics["rows_fully_recovered"] += 1
            if predicted_bp == 0:
                metrics["rows_fully_missed"] += 1


def finalize_row_stat(stat: dict[str, Any]) -> dict[str, Any]:
    result = dict(stat)
    result["by_arm"] = {}
    for arm, values in stat.get("by_arm", {}).items():
        row = dict(values)
        denominator = int(row["callable_bp"])
        row["bp_recall"] = (
            int(row["predicted_positive_callable_bp"]) / denominator if denominator else None
        )
        row["any_recovery_rate"] = (
            int(row["rows_any_recovered"]) / int(row["rows_with_callable"])
            if int(row["rows_with_callable"])
            else None
        )
        row["full_recovery_rate"] = (
            int(row["rows_fully_recovered"]) / int(row["rows_with_callable"])
            if int(row["rows_with_callable"])
            else None
        )
        result["by_arm"][arm] = row
    return result


def _region_lookup(regions: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_source = {str(row["source_seqid"]): row for row in regions}
    by_id = {str(row["id"]): row for row in regions}
    return by_source, by_id


def map_panel_interval(
    row: dict[str, Any],
    by_source: dict[str, dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any] | None, int, int, str | None]:
    """Map a RepeatMasker row to local panel coordinates.

    Source assembly IDs use absolute assembly coordinates.  A lifted panel ID
    may carry either local panel coordinates or absolute coordinates; the
    choice is made only when one interpretation fits the frozen region.  A
    non-panel source contig is expected for a whole-assembly Label-A file and
    returns ``None`` without hiding its count in the caller.
    """
    seqid = str(row["seqid"])
    start, end = int(row["start"]), int(row["end"])
    region = by_source.get(seqid)
    mode = "source_assembly"
    if region is None:
        region = by_id.get(seqid)
        mode = "panel_id"
    if region is None:
        return None, 0, 0, None
    region_start = int(region["start_bp"])
    region_end = int(region["end_bp"])
    region_length = int(region["length_bp"])
    source_length = int(region.get("source_length_bp", region_length))
    if mode == "panel_id":
        fits_absolute = region_start <= start < end <= region_end
        fits_local = 0 <= start < end <= region_length
        if fits_absolute and not fits_local:
            abs_start, abs_end, mode = start, end, "panel_id_absolute"
        elif fits_local and not fits_absolute:
            abs_start, abs_end, mode = region_start + start, region_start + end, "panel_id_local"
        elif fits_absolute and fits_local:
            raise ValueError(
                f"ambiguous panel coordinate interpretation for {seqid}:{start}-{end}"
            )
        else:
            # A valid panel query may straddle a region edge.  Prefer the
            # coordinate system whose interval has any overlap with the
            # frozen region; otherwise it is a malformed selected query.
            abs_overlap = max(0, min(end, region_end) - max(start, region_start))
            local_overlap = max(0, min(end, region_length) - max(start, 0))
            if abs_overlap and not local_overlap:
                abs_start, abs_end, mode = start, end, "panel_id_absolute_partial"
            elif local_overlap and not abs_overlap:
                abs_start, abs_end, mode = region_start + start, region_start + end, "panel_id_local_partial"
            else:
                raise ValueError(f"selected panel coordinates outside region: {seqid}:{start}-{end}")
    else:
        abs_start, abs_end = start, end
    if abs_start < 0 or abs_end <= abs_start or abs_end > source_length:
        raise ValueError(f"coordinates outside source length for {seqid}: {abs_start}-{abs_end}/{source_length}")
    left = max(abs_start, region_start)
    right = min(abs_end, region_end)
    if right <= left:
        return region, 0, 0, mode
    return region, left - region_start, right - region_start, mode


def _load_prediction(candidate: dict[str, Any], root: Path, arms: list[str]) -> dict[str, Any]:
    prediction_dir = resolve(root, str(candidate["prediction_relpath"]))
    summary_path = prediction_dir / "summary.json"
    regions_path = prediction_dir / "panel_regions.json"
    fasta_path = prediction_dir / "panel_regions.fa"
    probabilities_path = prediction_dir / "probabilities.npz"
    for path in (summary_path, regions_path, fasta_path, probabilities_path):
        if not path.is_file():
            raise FileNotFoundError(f"prediction input missing: {path}")
    summary = read_json(summary_path)
    if summary.get("status") != "COMPLETED":
        raise ValueError(f"prediction source is not completed: {summary_path}")
    threshold = finite_float(summary.get("model", {}).get("threshold"))
    if threshold is None:
        raise ValueError(f"prediction threshold missing: {summary_path}")
    regions = json.loads(regions_path.read_text(encoding="utf-8"))
    if not isinstance(regions, list) or not regions:
        raise ValueError(f"invalid panel region list: {regions_path}")
    sequences = read_fasta(fasta_path)
    if set(sequences) != {str(row["id"]) for row in regions}:
        raise ValueError(f"panel FASTA IDs differ from panel_regions.json: {candidate['id']}")
    values: dict[str, dict[str, np.ndarray]] = {arm: {} for arm in arms}
    with np.load(probabilities_path, allow_pickle=False) as archive:
        for row in regions:
            rid = str(row["id"])
            expected_length = int(row["length_bp"])
            if len(sequences[rid]) != expected_length:
                raise ValueError(f"panel sequence length mismatch for {rid}")
            for arm in arms:
                key = f"{arm}__{rid}"
                if key not in archive:
                    raise ValueError(f"saved probabilities missing {key}")
                array = np.asarray(archive[key], dtype=np.float64)
                if array.shape != (expected_length,) or not np.isfinite(array).all():
                    raise ValueError(f"invalid saved probability array {key}")
                values[arm][rid] = array
    return {
        "prediction_dir": prediction_dir,
        "summary_path": summary_path,
        "summary": summary,
        "threshold": threshold,
        "regions": regions,
        "sequences": sequences,
        "values": values,
    }


def _union_stats(
    bucket_masks: dict[str, np.ndarray],
    sequences: dict[str, str],
    values: dict[str, dict[str, np.ndarray]],
    threshold: float,
    arms: list[str],
) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for bucket, masks in bucket_masks.items():
        bucket_result = {"union_bp": 0, "callable_union_bp": 0, "by_arm": {}}
        for rid, mask in masks.items():
            callable_mask = np.fromiter((base in "ACGT" for base in sequences[rid]), dtype=bool, count=len(mask))
            bucket_result["union_bp"] += int(mask.sum())
            bucket_result["callable_union_bp"] += int((mask & callable_mask).sum())
            for arm in arms:
                arm_values = values[arm][rid]
                pred = arm_values >= threshold
                arm_result = bucket_result["by_arm"].setdefault(
                    arm,
                    {"predicted_positive_callable_union_bp": 0, "bp_recall": None},
                )
                truth_bp = int((mask & callable_mask).sum())
                pred_bp = int((mask & callable_mask & pred).sum())
                arm_result["predicted_positive_callable_union_bp"] += pred_bp
                # The denominator is filled after all regions are added.
        for arm, arm_result in bucket_result["by_arm"].items():
            arm_result["bp_recall"] = (
                int(arm_result["predicted_positive_callable_union_bp"]) / int(bucket_result["callable_union_bp"])
                if bucket_result["callable_union_bp"]
                else None
            )
        summary[bucket] = bucket_result
    return summary


def _stratify_candidate_fast(candidate: dict[str, Any], root: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    """Stratify one candidate with cached callable/prediction prefixes."""
    external_cfg = cfg["external"]
    arms = [str(value) for value in external_cfg["arms"]]
    prediction = _load_prediction(candidate, root, arms)
    fixed_threshold = float(external_cfg["frozen_threshold"])
    if abs(float(prediction["threshold"]) - fixed_threshold) > 1e-12:
        raise ValueError(
            f"saved threshold differs from frozen contract for {candidate['id']}: "
            f"{prediction['threshold']} != {fixed_threshold}"
        )
    regions = prediction["regions"]
    sequences = prediction["sequences"]
    values = prediction["values"]
    by_source, by_id = _region_lookup(regions)
    label_path = resolve(root, str(candidate["label_relpath"]))
    if not label_path.is_file():
        raise FileNotFoundError(f"external label input missing: {label_path}")
    callable_masks: dict[str, np.ndarray] = {}
    arm_prefix: dict[str, dict[str, tuple[np.ndarray, np.ndarray]]] = {arm: {} for arm in arms}
    for region in regions:
        rid = str(region["id"])
        callable_mask = np.fromiter((base in "ACGT" for base in sequences[rid]), dtype=bool, count=len(sequences[rid]))
        callable_masks[rid] = callable_mask
        for arm in arms:
            pred_mask = (values[arm][rid] >= fixed_threshold) & callable_mask
            arm_prefix[arm][rid] = (_prefix(callable_mask), _prefix(pred_mask))
    bucket_names = ("known_te", "unknown_or_ambiguous", "hard_non_te", "excluded_non_te")
    bucket_masks: dict[str, dict[str, np.ndarray]] = {
        bucket: {str(row["id"]): np.zeros(int(row["length_bp"]), dtype=bool) for row in regions}
        for bucket in bucket_names
    }
    dimension_maps: dict[str, dict[str, dict[str, Any]]] = {
        "class": {},
        "length": {},
        "divergence": {},
        "source_region": {},
    }
    raw_class_counts: collections.Counter[str] = collections.Counter()
    bucket_counts: collections.Counter[str] = collections.Counter()
    bucket_panel_bp: collections.Counter[str] = collections.Counter()
    mode_counts: collections.Counter[str] = collections.Counter()
    nonpanel_rows = 0
    nonpanel_seqids: collections.Counter[str] = collections.Counter()
    raw_rows = 0
    panel_rows = 0
    coordinate_outside_rows = 0
    with label_path.open(encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, 1):
            fields = line.split()
            if not fields or not fields[0].isdigit():
                continue
            raw_rows += 1
            if len(fields) < 11:
                raise ValueError(f"truncated RepeatMasker row {line_no} in {label_path}")
            if fields[8] not in {"C", "+", "-"}:
                raise ValueError(f"invalid RepeatMasker strand at {label_path}:{line_no}")
            try:
                start = int(fields[5]) - 1
                end = int(fields[6])
            except ValueError as exc:
                raise ValueError(f"invalid coordinates at {label_path}:{line_no}") from exc
            row = {
                "seqid": fields[4],
                "start": start,
                "end": end,
                "class_family": fields[10],
                "divergence": finite_float(fields[1]),
            }
            region, left, right, mode = map_panel_interval(row, by_source, by_id)
            if region is None:
                nonpanel_rows += 1
                nonpanel_seqids[str(row["seqid"])] += 1
                continue
            if mode:
                mode_counts[mode] += 1
            if right <= left:
                coordinate_outside_rows += 1
                continue
            panel_rows += 1
            rid = str(region["id"])
            overlap_bp = right - left
            class_family = str(row["class_family"])
            bucket = truth_bucket(class_family)
            top = class_top(class_family)
            length_key = dimension_length(overlap_bp)
            divergence_key = dimension_divergence(row["divergence"])
            raw_class_counts[class_family] += 1
            bucket_counts[bucket] += 1
            bucket_panel_bp[bucket] += overlap_bp
            bucket_masks[bucket][rid][left:right] = True
            for dimension, key in (
                ("class", f"{bucket}|{top}"),
                ("length", f"{bucket}|{length_key}"),
                ("divergence", f"{bucket}|{divergence_key}"),
                ("source_region", rid),
            ):
                stat = dimension_maps[dimension].setdefault(key, {})
                update_stat(stat, {
                    arm: arm_prefix[arm][rid] for arm in arms
                }, left, right)
                class_counts = stat.setdefault("class_family_counts", {})
                class_counts[class_family] = int(class_counts.get(class_family, 0)) + 1
    dimension_results: dict[str, dict[str, Any]] = {}
    for dimension, rows in dimension_maps.items():
        dimension_results[dimension] = {
            key: finalize_row_stat(value) for key, value in sorted(rows.items())
        }
    bucket_summary: dict[str, Any] = {}
    union_summary = _union_stats(bucket_masks, sequences, values, fixed_threshold, arms)
    for bucket in bucket_names:
        bucket_summary[bucket] = {
            "rows": int(bucket_counts[bucket]),
            "panel_overlap_bp_row_sum": int(bucket_panel_bp[bucket]),
            "union_bp": int(union_summary[bucket]["union_bp"]),
            "callable_union_bp": int(union_summary[bucket]["callable_union_bp"]),
            "union_by_arm": union_summary[bucket]["by_arm"],
        }
    selected_seqids = sorted(by_source)
    nonpanel_seqid_preview = dict(nonpanel_seqids.most_common(20))
    return {
        "id": candidate["id"],
        "species": candidate["species"],
        "assembly": candidate["assembly"],
        "label_source": candidate["label_source"],
        "status": "COMPLETED",
        "prediction_output": str(prediction["prediction_dir"]),
        "prediction_summary": str(prediction["summary_path"]),
        "label_input": str(label_path),
        "threshold": float(prediction["threshold"]),
        "frozen_threshold_match": True,
        "regions": [
            {
                "id": str(row["id"]),
                "source_seqid": str(row["source_seqid"]),
                "start_bp": int(row["start_bp"]),
                "end_bp": int(row["end_bp"]),
                "length_bp": int(row["length_bp"]),
                "callable_bp": int(callable_masks[str(row["id"])].sum()),
            }
            for row in regions
        ],
        "raw_repeatmasker_rows_seen": int(raw_rows),
        "panel_rows_retained": int(panel_rows),
        "nonpanel_rows_skipped": int(nonpanel_rows),
        "nonpanel_seqid_count": int(len(nonpanel_seqids)),
        "nonpanel_seqid_preview": nonpanel_seqid_preview,
        "selected_source_seqids": selected_seqids,
        "coordinate_outside_selected_region_rows": int(coordinate_outside_rows),
        "coordinate_mapping_modes": dict(sorted(mode_counts.items())),
        "raw_class_counts_panel": dict(sorted(raw_class_counts.items())),
        "bucket_summary": bucket_summary,
        "strata": dimension_results,
        "contract": {
            "primary_positive_bucket": "known_te",
            "known_te_classes": sorted(STRICT_TE_CLASSES),
            "unknown_or_ambiguous_classes": sorted(UNKNOWN_CLASSES),
            "hard_non_te_classes": sorted(HARD_NON_TE_CLASSES),
            "excluded_non_te_classes": sorted(EXCLUDED_NON_TE_CLASSES),
            "unrecognised_classes": "unknown_or_ambiguous",
            "unlabelled_sequence_is_negative": False,
            "t0_independent_accuracy": False,
            "row_level_metrics_are_not_insertion_counts": True,
            "length_basis": "clipped overlap with the fixed panel region",
            "divergence_basis": "RepeatMasker .out column 2, percentage divergence",
            "overlap_policy": "row sums retain all comparator records; union summary is supplied separately",
            "threshold_adjustment": False,
            "prediction_cache_unchanged": True,
        },
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    config = read_json(args.config.resolve())
    root = Path(args.remote_root or config["remote_root"])
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"output directory already exists: {output_dir}")
    output_dir.mkdir(parents=True)
    start = time.perf_counter()
    ontology = audit_ontology(root, config)
    candidates = config["external"]["candidates"]
    external_results = [_stratify_candidate_fast(candidate, root, config) for candidate in candidates]
    result = {
        "protocol": config["protocol"],
        "status": "COMPLETED",
        "scientific_scope": "retrospective ontology and fixed-D comparator error stratification; no training or inference",
        "started_unix": time.time(),
        "runtime_seconds": time.perf_counter() - start,
        "ontology": ontology,
        "external": {
            "fixed_threshold": float(config["external"]["frozen_threshold"]),
            "arms": list(config["external"]["arms"]),
            "candidates": external_results,
            "comparison": [
                {
                    "id": row["id"],
                    "species": row["species"],
                    "assembly": row["assembly"],
                    "known_te_rows": row["bucket_summary"]["known_te"]["rows"],
                    "known_te_union_bp": row["bucket_summary"]["known_te"]["union_bp"],
                    "unknown_or_ambiguous_rows": row["bucket_summary"]["unknown_or_ambiguous"]["rows"],
                    "hard_non_te_rows": row["bucket_summary"]["hard_non_te"]["rows"],
                    "union_recall_by_arm": {
                        arm: row["bucket_summary"]["known_te"]["union_by_arm"][arm]["bp_recall"]
                        for arm in config["external"]["arms"]
                    },
                }
                for row in external_results
            ],
        },
        "interpretation_limits": [
            "The historical chrX 90-row Unknown diagnostic is a mapping sample without model predictions and is not a population annotation-error estimate.",
            "Known other TE classes are represented by the legacy Unknown ID; the six-ID windows cannot separate them from genuinely unclassified or non-TE unresolved records.",
            "The external annotations are comparator/sensitivity evidence. T1 precision and F1 remain undefined because unlabelled sequence is not a negative denominator.",
            "Rows are RepeatMasker records. No insertion identity or biological-instance recall is inferred from these aggregates.",
        ],
    }
    (output_dir / "ontology_audit.json").write_text(
        json.dumps(ontology, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    (output_dir / "external_strata.json").write_text(
        json.dumps(result["external"], indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    (output_dir / "summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    manifest = {
        "protocol": config["protocol"],
        "status": "COMPLETED",
        "config": str(args.config.resolve()),
        "output_dir": str(output_dir),
        "root": str(root),
        "threshold": float(config["external"]["frozen_threshold"]),
        "inference_rerun": False,
        "training": False,
        "candidates": [candidate["id"] for candidate in candidates],
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "STATUS.json").write_text(
        json.dumps({"status": "COMPLETED", "summary": str((output_dir / "summary.json").resolve())}, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--remote-root", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = run(args)
    except Exception as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "STATUS.json").write_text(
            json.dumps(
                {"status": "FAILED", "error": str(exc), "traceback": traceback.format_exc()},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        raise
    print(json.dumps({"status": result["status"], "runtime_seconds": result["runtime_seconds"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
