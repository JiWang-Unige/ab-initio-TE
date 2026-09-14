#!/usr/bin/env python3
"""Run the fixed-D external panel and the four bounded RC0 arms.

This runner is deliberately sequence-only at inference time.  It reads a fixed
panel manifest, applies the already frozen six-species CAL threshold, projects
model margins to base pairs, and only then maps the reverse-complement vector
back to the forward coordinates.  RepeatMasker output is used as a sparse
comparator; T1 is the primary endpoint and T0 is labelled comparator agreement.

The script is intended for a Slurm GPU/CPU job on the project checkout.  It does
not train, fit a threshold, choose regions from scores, or infer insertion IDs.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import time
import traceback
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[3]
ADAPTER_PATH = REPO_ROOT / "scripts/experiments/LEMMI-TE-BENCH-20260824-R1/adapter.py"
INFER_PATH = REPO_ROOT / "scripts/experiments/CROSS-SPECIES-L1-FASTA-INFERENCE-V1/infer_fasta.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load module {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = _load_module(ADAPTER_PATH, "te_omnibenchmark_adapter")
inference = _load_module(INFER_PATH, "l1_sequence_inference")

WINDOW_BP = int(inference.WINDOW_BP)
# This is the existing strict Label-A binary contract used by the frozen
# cross-species material evaluator.  Keep the raw class/family in the audit;
# the top-level class alone decides membership in the primary TE comparator.
STRICT_TE_CLASSES = {"LINE", "SINE", "LTR", "DNA", "RC", "Retroposon"}
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
IUPAC_RC = str.maketrans(
    "ACGTRYSWKMBDHVNacgtryswkmbdhvn",
    "TGCAYRSWMKVHDBNtgcayrswmkvhdbn",
)


def reverse_complement(sequence: str) -> str:
    """Return an IUPAC-aware reverse complement, preserving sequence length."""
    try:
        return sequence.translate(IUPAC_RC)[::-1]
    except ValueError as exc:
        raise ValueError("sequence contains a symbol without an IUPAC complement") from exc


def _sync(device: Any) -> None:
    if str(device).startswith("cuda"):
        import torch

        torch.cuda.synchronize(device)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _resolve_path(root: Path, value: str | None) -> Path | None:
    if value is None:
        return None
    path = Path(value)
    return path if path.is_absolute() else root / path


def _candidate(config: dict[str, Any], candidate_id: str) -> dict[str, Any]:
    candidates = config.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("config candidates must be a list")
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("id") == candidate_id:
            return candidate
    raise ValueError(f"candidate not found in panel config: {candidate_id}")


def _check_panel(config: dict[str, Any], candidate: dict[str, Any]) -> None:
    selection = config.get("selection_rule", {})
    if selection.get("score_or_label_selection") is not False:
        raise ValueError("panel must explicitly disable score/label selection")
    if int(selection.get("window_bp", WINDOW_BP)) != WINDOW_BP:
        raise ValueError("panel window differs from existing inference window")
    length = int(selection["length_bp"])
    if selection.get("start_policy") != "centered_from_assembly_length":
        raise ValueError("panel must use the fixed centered assembly-only start policy")
    if length % WINDOW_BP != 0:
        raise ValueError("panel interval is not a whole number of inference windows")
    regions = candidate.get("regions")
    if not isinstance(regions, list) or len(regions) != 4:
        raise ValueError("each candidate must contain exactly four fixed regions")
    seen = set()
    for row in regions:
        if not isinstance(row, dict):
            raise ValueError("malformed panel region")
        seqid = str(row["seqid"])
        if seqid in seen:
            raise ValueError(f"duplicate panel sequence: {seqid}")
        seen.add(seqid)
        row_length = int(row["length_bp"])
        expected_start = (row_length - length) // 2
        if int(row["start_bp"]) != expected_start or int(row["end_bp"]) != expected_start + length:
            raise ValueError(f"region does not use the fixed centered coordinates: {seqid}")
        if int(row["end_bp"]) > row_length or row_length < length:
            raise ValueError(f"region exceeds assembly report length: {seqid}")


def _selected_contigs(fasta: Path, selected: set[str]) -> dict[str, str]:
    found: dict[str, str] = {}
    for name, sequence in inference.read_fasta(fasta):
        if name in selected:
            found[name] = sequence
    missing = sorted(selected - set(found))
    if missing:
        raise ValueError(f"panel sequence IDs absent from FASTA: {missing}")
    return found


def _check_assembly_report(path: Path, candidate: dict[str, Any]) -> None:
    """Verify that the frozen IDs/lengths are the first report-selected rows."""
    column = candidate.get("fasta_accession_column")
    if column not in {"GenBank-Accession", "RefSeq-Accession"}:
        raise ValueError(f"unsupported assembly accession column: {column}")
    accession_index = 4 if column == "GenBank-Accession" else 6
    selected: list[tuple[str, str, str, int]] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            columns = line.rstrip("\n").split("\t")
            if len(columns) < 9 or columns[accession_index] == "na":
                continue
            selected.append((columns[accession_index], columns[1], columns[2], int(columns[8])))
            if len(selected) == 4:
                break
    expected = [
        (str(row["seqid"]), str(row.get("role")), str(row.get("molecule")), int(row["length_bp"]))
        for row in candidate["regions"]
    ]
    if selected != expected:
        raise ValueError(f"frozen panel does not match first four {column} report rows: {selected!r} != {expected!r}")


def _region_id(candidate_id: str, index: int, seqid: str, start: int, end: int) -> str:
    # Avoid a colon so the identifier remains easy to use in BED/TSV tools.
    return f"{candidate_id}__r{index:02d}__{seqid}__{start}_{end}"


def _material_runs(values: np.ndarray) -> list[tuple[int, int]]:
    values = np.asarray(values, dtype=bool)
    change = np.flatnonzero(values[1:] != values[:-1]) + 1 if len(values) > 1 else np.array([], dtype=int)
    boundaries = np.concatenate((np.array([0], dtype=int), change, np.array([len(values)], dtype=int)))
    runs: list[tuple[int, int]] = []
    for left, right in zip(boundaries[:-1], boundaries[1:]):
        if bool(values[left]):
            runs.append((int(left), int(right)))
    return runs


def _infer_sequence(
    sequence: str,
    model: Any,
    tokenizer: Any,
    device: Any,
    batch_size: int,
    slope: float,
    intercept: float,
) -> np.ndarray:
    values: list[np.ndarray] = []
    for offset in range(0, len(sequence), WINDOW_BP * batch_size):
        starts = list(range(offset, min(len(sequence), offset + WINDOW_BP * batch_size), WINDOW_BP))
        windows = [sequence[start : start + WINDOW_BP] for start in starts]
        margins = inference.core.infer_half_margins(model, tokenizer, device, windows, batch_size)
        if len(margins) != len(windows):
            raise ValueError("inference returned the wrong number of windows")
        for window, margin in zip(windows, margins):
            margin = np.asarray(margin)
            if margin.shape != (len(window),) or not np.isfinite(margin).all():
                raise ValueError("invalid projected margins")
            values.append(np.asarray(inference.core.sigmoid(slope * margin + intercept), dtype=np.float64))
    result = np.concatenate(values) if values else np.empty(0, dtype=np.float64)
    if len(result) != len(sequence) or not np.isfinite(result).all():
        raise ValueError("projected probability length or finiteness check failed")
    return result


def _write_probability_track(path: Path, regions: list[dict[str, Any]], values: dict[str, np.ndarray]) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        for region in regions:
            rid = str(region["id"])
            array = np.asarray(values[rid])
            change = np.flatnonzero(array[1:] != array[:-1]) + 1 if len(array) > 1 else np.array([], dtype=int)
            boundaries = np.concatenate((np.array([0], dtype=int), change, np.array([len(array)], dtype=int)))
            for left, right in zip(boundaries[:-1], boundaries[1:]):
                handle.write(f"{rid}\t{int(left)}\t{int(right)}\t{float(array[left]):.17g}\n")


def _write_material_bed(path: Path, regions: list[dict[str, Any]], values: dict[str, np.ndarray], threshold: float) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        for region in regions:
            rid = str(region["id"])
            for start, end in _material_runs(values[rid] >= threshold):
                writer.writerow((rid, start, end, "D_material", ".", "."))


def _write_panel_fasta(path: Path, regions: list[dict[str, Any]], sequences: dict[str, str]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for region in regions:
            rid = str(region["id"])
            handle.write(f">{rid}\n{sequences[rid]}\n")


def _truth_bucket(class_family: str) -> str:
    """Map a raw RepeatMasker class to the frozen D truth buckets.

    The positive bucket deliberately matches the pre-existing strict TE
    contract.  An unrecognised class is retained as unknown/ambiguous rather
    than silently becoming a negative or positive label.
    """
    value = str(class_family).strip()
    top = value.split("/", 1)[0]
    if top in STRICT_TE_CLASSES and "?" not in value:
        return "known_te"
    top_lower = top.lower()
    if "?" in value or any(top_lower.startswith(value) for value in UNKNOWN_CLASSES):
        return "unknown_or_ambiguous"
    if top_lower in HARD_NON_TE_CLASSES:
        return "hard_non_te"
    if top_lower in EXCLUDED_NON_TE_CLASSES:
        return "excluded_non_te"
    return "unknown_or_ambiguous"


def _class_family(row: dict[str, object]) -> str:
    attributes = str(row.get("attributes", ""))
    marker = "class_family="
    for item in attributes.split(";"):
        if item.startswith(marker):
            return item[len(marker):]
    return ""


def _union_bp(intervals_by_seqid: dict[str, list[tuple[int, int]]]) -> int:
    """Return the non-overlapping bp union of local half-open intervals."""
    total = 0
    for intervals in intervals_by_seqid.values():
        active_start = active_end = None
        for start, end in sorted(intervals):
            if active_start is None:
                active_start, active_end = start, end
            elif start > active_end:
                total += active_end - active_start
                active_start, active_end = start, end
            else:
                active_end = max(active_end, end)
        if active_start is not None:
            total += active_end - active_start
    return int(total)


def _make_truth(
    label_out: Path,
    regions: list[dict[str, Any]],
    output_dir: Path,
) -> tuple[Path, Path, dict[str, Any]]:
    by_seqid = {str(row["source_seqid"]): row for row in regions}
    bucket_paths = {
        "known_te": output_dir / "truth_repeatmasker_panel.bed",
        "unknown_or_ambiguous": output_dir / "truth_repeatmasker_panel_unknown_or_ambiguous.bed",
        "hard_non_te": output_dir / "truth_repeatmasker_panel_hard_non_te.bed",
        "excluded_non_te": output_dir / "truth_repeatmasker_panel_excluded_non_te.bed",
    }
    handles = {bucket: path.open("w", encoding="utf-8", newline="") for bucket, path in bucket_paths.items()}
    writers = {
        bucket: csv.writer(handle, delimiter="\t", lineterminator="\n")
        for bucket, handle in handles.items()
    }
    raw_rows = 0
    panel_rows = 0
    class_counts_raw: dict[str, int] = {}
    bucket_stats: dict[str, dict[str, Any]] = {
        bucket: {"rows": 0, "overlap_bp": 0, "union_bp": 0, "class_counts": {}}
        for bucket in bucket_paths
    }
    bucket_intervals: dict[str, dict[str, list[tuple[int, int]]]] = {
        bucket: {} for bucket in bucket_paths
    }
    try:
        for row in adapter.parse_repeatmasker_out(label_out):
            raw_rows += 1
            class_family = _class_family(row)
            class_counts_raw[class_family] = class_counts_raw.get(class_family, 0) + 1
            region = by_seqid.get(str(row["seqid"]))
            if region is None:
                continue
            left = max(int(row["start"]), int(region["start_bp"]))
            right = min(int(row["end"]), int(region["end_bp"]))
            if right <= left:
                continue
            bucket = _truth_bucket(class_family)
            overlap_bp = right - left
            panel_rows += 1
            stats = bucket_stats[bucket]
            stats["rows"] = int(stats["rows"]) + 1
            stats["overlap_bp"] = int(stats["overlap_bp"]) + overlap_bp
            bucket_intervals[bucket].setdefault(str(region["id"]), []).append(
                (left - int(region["start_bp"]), right - int(region["start_bp"]))
            )
            class_counts = stats["class_counts"]
            class_counts[class_family] = int(class_counts.get(class_family, 0)) + 1
            writers[bucket].writerow(
                (
                    region["id"],
                    left - int(region["start_bp"]),
                    right - int(region["start_bp"]),
                    row["name"],
                    row["score"],
                    row["strand"],
                )
            )
    finally:
        for handle in handles.values():
            handle.close()
    for bucket, stats in bucket_stats.items():
        stats["union_bp"] = _union_bp(bucket_intervals[bucket])
    canonical = output_dir / "truth_repeatmasker_panel.tsv"
    adapter.convert(bucket_paths["known_te"], canonical, "bed")
    canonical_paths = {"known_te": canonical}
    for bucket in ("unknown_or_ambiguous", "hard_non_te", "excluded_non_te"):
        path = output_dir / f"truth_repeatmasker_panel_{bucket}.tsv"
        adapter.convert(bucket_paths[bucket], path, "bed")
        canonical_paths[bucket] = path
    audit = {
        "raw_repeatmasker_rows_seen": raw_rows,
        "panel_rows_retained_all_buckets": panel_rows,
        "raw_class_counts": dict(sorted(class_counts_raw.items())),
        "panel_buckets": bucket_stats,
        "policy": {
            "strict_te_classes": sorted(STRICT_TE_CLASSES),
            "unknown_classes": sorted(UNKNOWN_CLASSES),
            "hard_non_te_classes": sorted(HARD_NON_TE_CLASSES),
            "excluded_non_te_classes": sorted(EXCLUDED_NON_TE_CLASSES),
            "unrecognised_classes": "unknown_or_ambiguous",
            "primary_truth": "known_te only",
        },
        "canonical_paths": {bucket: str(path.resolve()) for bucket, path in canonical_paths.items()},
    }
    (output_dir / "truth_repeatmasker_panel_class_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    return bucket_paths["known_te"], canonical, audit


def _truth_masks(canonical: Path, regions: list[dict[str, Any]]) -> dict[str, np.ndarray]:
    masks = {str(row["id"]): np.zeros(int(row["length_bp"]), dtype=bool) for row in regions}
    for seqid, start, end in adapter.read_canonical(canonical):
        if seqid not in masks:
            raise ValueError(f"truth contains unknown panel ID: {seqid}")
        masks[seqid][start:end] = True
    return masks


def _clip_canonical_to_callable(
    canonical: Path,
    regions: list[dict[str, Any]],
    sequences: dict[str, str],
    output_dir: Path,
    stem: str,
) -> Path:
    """Intersect canonical intervals with A/C/G/T bases and reconvert them."""
    callable_runs = {
        str(region["id"]): _material_runs(
            np.fromiter((base in "ACGT" for base in sequences[str(region["id"])]), dtype=bool, count=int(region["length_bp"]))
        )
        for region in regions
    }
    raw = output_dir / f"{stem}.callable.bed"
    with raw.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        for seqid, start, end in adapter.read_canonical(canonical):
            for run_start, run_end in callable_runs.get(seqid, []):
                left, right = max(start, run_start), min(end, run_end)
                if right > left:
                    writer.writerow((seqid, left, right, "callable", ".", "."))
    result = output_dir / f"{stem}.callable.tsv"
    adapter.convert(raw, result, "bed")
    return result


def _strata(sequence: str, truth: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict[str, Any]:
    positions = np.arange(len(sequence), dtype=np.int64)
    edge = (positions % WINDOW_BP < 16) | (positions % WINDOW_BP >= WINDOW_BP - 16)
    n_mask = np.fromiter((base not in "ACGT" for base in sequence.upper()), dtype=bool, count=len(sequence))
    callable_mask = ~n_mask
    masks = {
        "callable_ACGT": callable_mask,
        "window_edge_16bp_callable": edge & callable_mask,
        "N_or_IUPAC": n_mask,
        "all_region_including_noncallable": np.ones(len(sequence), dtype=bool),
    }
    masks["interior_ACGT"] = callable_mask & ~edge
    predicted = probabilities >= threshold
    result: dict[str, Any] = {}
    for name, mask in masks.items():
        truth_bp = int(np.count_nonzero(truth & mask))
        pred_bp = int(np.count_nonzero(predicted & mask))
        tp = int(np.count_nonzero(truth & predicted & mask))
        result[name] = {
            "bp_n": int(np.count_nonzero(mask)),
            "truth_positive_bp": truth_bp,
            "predicted_positive_bp": pred_bp,
            "overlap_bp": tp,
            "t1_recall": tp / truth_bp if truth_bp else None,
        }
    return result


def _correct_callable_metrics(
    metrics: dict[str, Any], callable_bp: int, truth_tier: str
) -> dict[str, Any]:
    """Correct the adapter denominator after masking non-ACGT coordinates.

    The shared adapter evaluates intervals in their original coordinates and
    receives the full panel lengths.  For a callable view, TP/FP/FN are already
    computed on the clipped intervals, but ``bp_n`` and the T0 TN counter would
    otherwise include N/IUPAC bases.  Keep all interval and segment metrics
    unchanged and repair only this callable denominator in the D wrapper.
    """
    result = dict(metrics)
    callable_bp = int(callable_bp)
    if callable_bp < 0:
        raise ValueError("callable bp denominator cannot be negative")
    result["bp_n"] = callable_bp
    if truth_tier == "T0":
        tp = int(result["bp_tp"])
        fp = int(result["bp_fp"])
        fn = int(result["bp_fn"])
        tn = callable_bp - tp - fp - fn
        if tn < 0:
            raise ValueError(
                "callable denominator is smaller than TP+FP+FN: "
                f"{callable_bp} < {tp}+{fp}+{fn}"
            )
        result["bp_tn"] = int(tn)
    return result


def _load_model(config: dict[str, Any], args: argparse.Namespace):
    remote_root = Path(args.remote_root or config["remote_root"])
    model_info = config["model"]
    model_dir = Path(args.model_dir) if args.model_dir else remote_root / model_info["model_relpath"]
    tokenizer_dir = Path(args.tokenizer_dir) if args.tokenizer_dir else model_dir
    model_code_dir = Path(args.model_code_dir) if args.model_code_dir else remote_root / model_info["model_code_relpath"]
    calibration_json = Path(args.calibration_json) if args.calibration_json else remote_root / model_info["calibration_relpath"]
    if not model_dir.is_dir():
        raise FileNotFoundError(f"model directory missing: {model_dir}")
    if not model_code_dir.is_dir():
        raise FileNotFoundError(f"model code directory missing: {model_code_dir}")
    if not calibration_json.is_file():
        raise FileNotFoundError(f"calibration JSON missing: {calibration_json}")
    load_args = argparse.Namespace(
        model_dir=model_dir,
        tokenizer_dir=tokenizer_dir,
        model_code_dir=model_code_dir,
        calibration_json=calibration_json,
    )
    calibration = inference.load_calibration(load_args)
    expected_seed = int(model_info["seed"])
    if int(calibration["seed"]) != expected_seed:
        raise ValueError("calibration seed differs from fixed D seed")
    load_start = time.perf_counter()
    model, tokenizer, device = inference.core.load_final_model(
        model_dir, tokenizer_dir, bool(args.cpu), model_code_dir
    )
    _sync(device)
    load_elapsed = time.perf_counter() - load_start
    return model, tokenizer, device, calibration, load_elapsed, {
        "model_dir": str(model_dir.resolve()),
        "tokenizer_dir": str(tokenizer_dir.resolve()),
        "model_code_dir": str(model_code_dir.resolve()),
        "calibration_json": str(calibration_json.resolve()),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    config_path = args.config.resolve()
    config = _read_json(config_path)
    candidate = _candidate(config, args.candidate)
    _check_panel(config, candidate)
    remote_root = Path(args.remote_root or config["remote_root"])
    fasta = _resolve_path(remote_root, str(candidate["fasta"]))
    assembly_report = _resolve_path(remote_root, str(candidate["assembly_report"]))
    label_out = _resolve_path(remote_root, str(candidate["label_out"]))
    assert fasta is not None and assembly_report is not None and label_out is not None
    for path in (fasta, assembly_report, label_out):
        if not path.is_file():
            raise FileNotFoundError(f"required panel input missing: {path}")
    _check_assembly_report(assembly_report, candidate)

    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"output directory already exists: {output_dir}")
    output_dir.mkdir(parents=True)
    start_wall = time.perf_counter()
    regions: list[dict[str, Any]] = []
    selected_ids = {str(row["seqid"]) for row in candidate["regions"]}
    contigs = _selected_contigs(fasta, selected_ids)
    region_sequences: dict[str, str] = {}
    for index, row in enumerate(candidate["regions"], 1):
        source_seqid = str(row["seqid"])
        start_bp, end_bp = int(row["start_bp"]), int(row["end_bp"])
        if len(contigs[source_seqid]) != int(row["length_bp"]):
            raise ValueError(
                f"FASTA/report length mismatch for {source_seqid}: "
                f"{len(contigs[source_seqid])} != {row['length_bp']}"
            )
        sequence = contigs[source_seqid][start_bp:end_bp]
        if len(sequence) != end_bp - start_bp:
            raise ValueError(f"panel slice has wrong length: {source_seqid}")
        rid = _region_id(args.candidate, index, source_seqid, start_bp, end_bp)
        region = {
            "id": rid,
            "source_seqid": source_seqid,
            "source_length_bp": int(row["length_bp"]),
            "start_bp": start_bp,
            "end_bp": end_bp,
            "length_bp": len(sequence),
            "assembly_role": row.get("role"),
            "assembly_molecule": row.get("molecule"),
        }
        regions.append(region)
        region_sequences[rid] = sequence
    _write_panel_fasta(output_dir / "panel_regions.fa", regions, region_sequences)
    (output_dir / "panel_lengths.json").write_text(
        json.dumps({str(row["id"]): int(row["length_bp"]) for row in regions}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "panel_regions.json").write_text(json.dumps(regions, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    truth_bed, truth_canonical, truth_audit = _make_truth(label_out, regions, output_dir)
    truth_masks = _truth_masks(truth_canonical, regions)
    panel_lengths = {str(row["id"]): int(row["length_bp"]) for row in regions}
    callable_lengths = {
        str(row["id"]): sum(base in "ACGT" for base in region_sequences[str(row["id"])])
        for row in regions
    }
    callable_panel_bp = int(sum(callable_lengths.values()))
    truth_callable = _clip_canonical_to_callable(
        truth_canonical, regions, region_sequences, output_dir, "truth_repeatmasker_panel"
    )

    model, tokenizer, device, calibration, load_seconds, model_paths = _load_model(config, args)
    slope = float(calibration["platt_slope"])
    intercept = float(calibration["platt_intercept"])
    threshold = float(calibration["threshold"])
    batch_size = int(args.batch_size)
    if batch_size < 1:
        raise ValueError("batch size must be positive")

    forward: dict[str, np.ndarray] = {}
    rc: dict[str, np.ndarray] = {}
    phase3: dict[str, np.ndarray] = {}
    timing: dict[str, float] = {}

    _sync(device)
    tic = time.perf_counter()
    for region in regions:
        rid = str(region["id"])
        forward[rid] = _infer_sequence(region_sequences[rid], model, tokenizer, device, batch_size, slope, intercept)
    _sync(device)
    timing["F_seconds"] = time.perf_counter() - tic

    _sync(device)
    tic = time.perf_counter()
    for region in regions:
        rid = str(region["id"])
        mapped = _infer_sequence(
            reverse_complement(region_sequences[rid]), model, tokenizer, device, batch_size, slope, intercept
        )[::-1]
        if len(mapped) != int(region["length_bp"]):
            raise ValueError("reverse-complement mapping changed region length")
        rc[rid] = mapped
    _sync(device)
    timing["RC_seconds"] = time.perf_counter() - tic

    phase_offset = int(config["selection_rule"].get("phase_offset_bp", 3))
    if phase_offset < 1:
        raise ValueError("phase offset must be positive")
    _sync(device)
    tic = time.perf_counter()
    for region in regions:
        rid = str(region["id"])
        source = contigs[str(region["source_seqid"])]
        start_bp = int(region["start_bp"])
        if start_bp < phase_offset:
            raise ValueError("phase context would run before sequence origin")
        shifted = source[start_bp - phase_offset : int(region["end_bp"])]
        projected = _infer_sequence(shifted, model, tokenizer, device, batch_size, slope, intercept)
        phase3[rid] = projected[phase_offset:]
        if len(phase3[rid]) != int(region["length_bp"]):
            raise ValueError("phase-shifted projection changed region length")
    _sync(device)
    timing["phase3_seconds"] = time.perf_counter() - tic

    arms: dict[str, dict[str, np.ndarray]] = {
        "F": forward,
        "RC": rc,
        "mean": {rid: (forward[rid] + rc[rid]) / 2.0 for rid in forward},
        "phase_mean": {rid: (forward[rid] + phase3[rid]) / 2.0 for rid in forward},
    }
    for arm_values in arms.values():
        for rid, values in arm_values.items():
            if values.shape != (int(next(row for row in regions if row["id"] == rid)["length_bp"]),):
                raise ValueError(f"arm length mismatch: {rid}")
            if not np.isfinite(values).all():
                raise ValueError(f"arm contains non-finite probabilities: {rid}")

    np.savez_compressed(
        output_dir / "probabilities.npz",
        **{f"{arm}__{rid}": values.astype(np.float32) for arm, mapping in arms.items() for rid, values in mapping.items()},
    )

    arm_results: dict[str, Any] = {}
    for arm, arm_values in arms.items():
        probability_track = output_dir / f"{arm}.probability.bedGraph.gz"
        material_bed = output_dir / f"{arm}.material.bed"
        canonical = output_dir / f"{arm}.canonical.tsv"
        _write_probability_track(probability_track, regions, arm_values)
        _write_material_bed(material_bed, regions, arm_values, threshold)
        adapter.convert(material_bed, canonical, "bed")
        # Create the callable view only after the prediction canonical file
        # exists; the same helper is used for truth and every arm.
        callable_canonical = _clip_canonical_to_callable(
            canonical, regions, region_sequences, output_dir, arm
        )
        t1_full = adapter.evaluate(truth_canonical, canonical, panel_lengths, truth_tier="T1")
        t0_full = adapter.evaluate(truth_canonical, canonical, panel_lengths, truth_tier="T0")
        t1_callable = adapter.evaluate(truth_callable, callable_canonical, panel_lengths, truth_tier="T1")
        t0_callable = adapter.evaluate(truth_callable, callable_canonical, panel_lengths, truth_tier="T0")
        t1_callable = _correct_callable_metrics(t1_callable, callable_panel_bp, "T1")
        t0_callable = _correct_callable_metrics(t0_callable, callable_panel_bp, "T0")
        per_region: dict[str, Any] = {}
        for region in regions:
            rid = str(region["id"])
            lengths = {rid: int(region["length_bp"])}
            # Evaluating one region gives a compact row for the report while
            # preserving the exact shared adapter semantics.
            one_truth = output_dir / f".truth_{rid}.tsv"
            one_pred = output_dir / f".{arm}_{rid}.tsv"
            with one_truth.open("w", encoding="utf-8") as handle:
                handle.write("seqid\tstart\tend\tname\tscore\tstrand\tsource\tattributes\n")
                for seqid, start, end in adapter.read_canonical(truth_callable):
                    if seqid == rid:
                        handle.write(f"{seqid}\t{start}\t{end}\t.\t.\t.\t.\t.\n")
            with one_pred.open("w", encoding="utf-8") as handle:
                handle.write("seqid\tstart\tend\tname\tscore\tstrand\tsource\tattributes\n")
                for seqid, start, end in adapter.read_canonical(callable_canonical):
                    if seqid == rid:
                        handle.write(f"{seqid}\t{start}\t{end}\t.\t.\t.\t.\t.\n")
            one_t1 = adapter.evaluate(one_truth, one_pred, lengths, truth_tier="T1")
            one_t0 = adapter.evaluate(one_truth, one_pred, lengths, truth_tier="T0")
            one_callable_bp = int(callable_lengths[rid])
            one_t1 = _correct_callable_metrics(one_t1, one_callable_bp, "T1")
            one_t0 = _correct_callable_metrics(one_t0, one_callable_bp, "T0")
            per_region[rid] = {
                "length_bp": int(region["length_bp"]),
                "callable_bp": int(one_callable_bp),
                "truth_positive_bp": int(np.count_nonzero(truth_masks[rid])),
                "strata": _strata(region_sequences[rid], truth_masks[rid], arm_values[rid], threshold),
                "t1": one_t1,
                "repeatmasker_comparator_t0": one_t0,
            }
            one_truth.unlink()
            one_pred.unlink()
        arm_results[arm] = {
            "probability_track": str(probability_track.resolve()),
            "material_bed": str(material_bed.resolve()),
            "canonical": str(canonical.resolve()),
            "callable_canonical": str(callable_canonical.resolve()),
            "primary_callable_t1_positive_recovery": t1_callable,
            "callable_repeatmasker_comparator_agreement_t0": t0_callable,
            "full_region_t1_positive_recovery": t1_full,
            "full_region_repeatmasker_comparator_agreement_t0": t0_full,
            "per_region": per_region,
            "callable_bp": callable_panel_bp,
            "predicted_positive_bp": int(sum(np.count_nonzero(values >= threshold) for values in arm_values.values())),
            "material_run_count": int(sum(len(_material_runs(values >= threshold)) for values in arm_values.values())),
            "short_material_run_count": int(sum(sum(end - start < 80 for start, end in _material_runs(values >= threshold)) for values in arm_values.values())),
        }

    abs_diff: list[np.ndarray] = []
    flips: list[np.ndarray] = []
    for rid in forward:
        abs_diff.append(np.abs(forward[rid] - rc[rid]))
        flips.append((forward[rid] >= threshold) != (rc[rid] >= threshold))
    phase_abs_diff = [np.abs(forward[rid] - phase3[rid]) for rid in forward]
    forward_windows = sum((int(row["length_bp"]) + WINDOW_BP - 1) // WINDOW_BP for row in regions)
    phase_windows = sum(
        (int(row["length_bp"]) + phase_offset + WINDOW_BP - 1) // WINDOW_BP for row in regions
    )
    summary = {
        "protocol": "D-EXTERNAL-RC0-20260914",
        "status": "COMPLETED",
        "scientific_scope": "fixed-D finite external comparator panel; no independent genome-wide accuracy claim",
        "candidate": candidate["id"],
        "species": candidate["species"],
        "assembly": candidate["assembly"],
        "assembly_report": str(assembly_report.resolve()),
        "input_fasta": str(fasta.resolve()),
        "label_out": str(label_out.resolve()),
        "label_id": candidate["label_id"],
        "label_status": candidate["label_status"],
        "panel_selection": config["selection_rule"],
        "regions": regions,
        "truth": {
            "primary_tier": "T1",
            "source": "RepeatMasker/Dfam-derived sparse comparator",
            "raw_repeatmasker_rows_seen": int(truth_audit["raw_repeatmasker_rows_seen"]),
            "panel_rows_retained": int(truth_audit["panel_buckets"]["known_te"]["rows"]),
            "panel_rows_retained_all_buckets": int(truth_audit["panel_rows_retained_all_buckets"]),
            "primary_known_te_overlap_bp": int(truth_audit["panel_buckets"]["known_te"]["overlap_bp"]),
            "primary_known_te_union_bp": int(truth_audit["panel_buckets"]["known_te"]["union_bp"]),
            "primary_endpoint_status": (
                "ELIGIBLE_KNOWN_TE_IN_PANEL"
                if int(truth_audit["panel_buckets"]["known_te"]["rows"]) > 0
                else "NOT_EVALUABLE_NO_KNOWN_TE_IN_PANEL"
            ),
            "class_audit": str((output_dir / "truth_repeatmasker_panel_class_audit.json").resolve()),
            "class_policy": truth_audit["policy"],
            "bucket_canonical_paths": truth_audit["canonical_paths"],
            "canonical": str(truth_canonical.resolve()),
            "callable_canonical": str(truth_callable.resolve()),
            "callable_panel_bp": callable_panel_bp,
            "callable_non_acgt_panel_bp": int(sum(panel_lengths.values()) - callable_panel_bp),
            "primary_callable_policy": "intersect truth and prediction with A/C/G/T before the primary T1/T0 endpoints",
            "t0_name": "repeatmasker_comparator_agreement_t0",
            "t0_is_independent_accuracy": False,
            "unlabelled_sequence_is_negative": False,
        },
        "model": {
            "seed": int(calibration["seed"]),
            "calibration_scope": calibration["calibration_scope"],
            "fit_split": calibration["fit_split"],
            "threshold": threshold,
            "platt_slope": slope,
            "platt_intercept": intercept,
            "paths": model_paths,
            "device": str(device),
            "batch_size": batch_size,
            "load_seconds": load_seconds,
        },
        "arms": arm_results,
        "rc_consistency": {
            "mean_abs_probability_difference": float(np.mean(np.concatenate(abs_diff))),
            "threshold_flip_rate": float(np.mean(np.concatenate(flips))),
            "phase3_mean_abs_probability_difference": float(np.mean(np.concatenate(phase_abs_diff))),
            "mapping": "project base-pair probabilities first; [s,e) -> [L-e,L-s) by vector reversal",
            "arithmetic_consistency_is_not_biological_accuracy": True,
        },
        "timing": {
            "inference_seconds": timing,
            "total_wall_seconds": time.perf_counter() - start_wall,
            "model_passes": {
                "F": {"passes": 1, "windows": forward_windows},
                "RC": {"passes": 1, "windows": forward_windows},
                "phase3": {"passes": 1, "windows": phase_windows, "input_extra_bp_per_region": phase_offset},
                "mean": {"passes": 0, "windows": 0, "reuses": ["F", "RC"]},
                "phase_mean": {"passes": 0, "windows": 0, "reuses": ["F", "phase3"]},
            },
            "phase3_extra_tail_windows": phase_windows - forward_windows,
            "strict_equal_cost_claim": False,
            "cpu_flag": bool(args.cpu),
        },
        "outputs": {
            "panel_fasta": str((output_dir / "panel_regions.fa").resolve()),
            "panel_lengths": str((output_dir / "panel_lengths.json").resolve()),
            "probabilities_npz": str((output_dir / "probabilities.npz").resolve()),
        },
        "feedback_audit": config["feedback_audit"],
        "status_denominator": "one candidate x four arms; a missing final summary is FAILED",
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--candidate", required=True, choices=["platypus", "sea_urchin", "c_briggsae"])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--remote-root", type=Path)
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--tokenizer-dir", type=Path)
    parser.add_argument("--model-code-dir", type=Path)
    parser.add_argument("--calibration-json", type=Path)
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--cpu", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = run(args)
    except Exception as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "STATUS.json").write_text(
            json.dumps({"status": "FAILED", "error": str(exc), "traceback": traceback.format_exc()}, indent=2)
            + "\n",
            encoding="utf-8",
        )
        raise
    (args.output_dir / "STATUS.json").write_text(
        json.dumps({"status": "COMPLETED", "summary": str((args.output_dir / "summary.json").resolve())}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": result["status"], "candidate": result["candidate"], "output_dir": str(args.output_dir.resolve())}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
