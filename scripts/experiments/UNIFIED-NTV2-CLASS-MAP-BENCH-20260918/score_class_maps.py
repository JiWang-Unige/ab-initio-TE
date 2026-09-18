#!/usr/bin/env python3
"""Score the class map and native annotations on the fixed chr10/chr20 panel.

The comparison is deliberately separate from the binary WHOLE benchmark.  It
uses one source label array and one callable mask for every method, keeps
source Unknown/ambiguous states explicit, and never uses the source labels to
choose a prediction class or resolve native overlaps.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import re
import time
from pathlib import Path
from typing import Iterable

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = ROOT / "configs/UNIFIED-NTV2-CLASS-MAP-BENCH-20260918.json"
LABEL_NAMES = [
    "BG",
    "SINE",
    "LINE",
    "LTR",
    "DNA",
    "KNOWN_OTHER_TE",
    "AMBIGUOUS_TE",
    "UNCLASSIFIED",
]
LABEL2ID = {name: index for index, name in enumerate(LABEL_NAMES)}
MAIN4 = {"SINE": 1, "LINE": 2, "LTR": 3, "DNA": 4}
KNOWN_OTHER = {"RC": 5, "RETROPOSON": 5}
UNKNOWN = {"", "?", "-", "UNKNOWN", "UNCLASSIFIED", "UNSPECIFIED", "NA", "NONE", "."}
NON_TE = {
    "SIMPLE_REPEAT",
    "LOW_COMPLEXITY",
    "SATELLITE",
    "RNA",
    "RRNA",
    "SCRNA",
    "SNRNA",
    "SRPRNA",
    "TRNA",
    "OTHER",
    "CENTROMERE",
    "TELOMERE",
}
NONCALLABLE = "NONCALLABLE"
# Rows that are definitely not a sequence-level TE call.  Structural LTR/TIR
# rows are kept in a separate set below: they can be useful diagnostics, but
# they must not displace a complete parent TE body merely because they carry a
# Parent attribute.
NON_TE_FEATURES = {"region", "chromosome", "contig", "supercontig", "sequence", "gene", "mrna", "exon", "target_site_duplication"}
STRUCTURAL_FEATURES = {
    "long_terminal_repeat", "terminal_inverted_repeat", "inverted_repeat",
    "five_prime_ltr", "three_prime_ltr", "protein_match", "coding_sequence",
}
COMPLETE_TE_FEATURES = {
    "repeat", "repeat_region", "transposable_element", "mobile_element",
    "retrotransposon", "ltr_retrotransposon", "line", "sine", "dna_transposon",
    "rc", "retroposon", "helitron", "tir", "mite",
}
FEATURE_LABELS = {
    "ltr_retrotransposon": LABEL2ID["LTR"],
    "line": LABEL2ID["LINE"],
    "sine": LABEL2ID["SINE"],
    "dna_transposon": LABEL2ID["DNA"],
    "rc": LABEL2ID["KNOWN_OTHER_TE"],
    "retroposon": LABEL2ID["KNOWN_OTHER_TE"],
    "helitron": LABEL2ID["KNOWN_OTHER_TE"],
    "tir": LABEL2ID["DNA"],
    "mite": LABEL2ID["DNA"],
}


def open_text(path: Path):
    return gzip.open(path, "rt", encoding="utf-8", errors="replace") if path.suffix.lower() == ".gz" else path.open("rt", encoding="utf-8", errors="replace")


def merge(intervals: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[list[int]] = []
    for left, right in sorted(intervals):
        if right <= left:
            continue
        if not merged or left > merged[-1][1]:
            merged.append([left, right])
        else:
            merged[-1][1] = max(merged[-1][1], right)
    return [(left, right) for left, right in merged]


def fasta_records(path: Path):
    name = None
    chunks: list[str] = []
    with open_text(path) as handle:
        for line_no, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    yield name, "".join(chunks).upper()
                fields = line[1:].split()
                if not fields:
                    raise ValueError(f"empty FASTA header at {path}:{line_no}")
                name, chunks = fields[0], []
            else:
                if name is None:
                    raise ValueError(f"sequence before FASTA header at {path}:{line_no}")
                chunks.append(line)
    if name is not None:
        yield name, "".join(chunks).upper()


def split_class(raw: str, family: str = "", *, native: bool = False) -> int | None:
    """Map a raw class without consulting reference labels.

    For source labels, explicit non-TE RepeatMasker classes are BG.  For
    native predictions they are skipped, because an annotation row for a
    simple repeat is not a TE call.  Unknown and question-mark classes remain
    explicit ontology states in both cases.
    """
    raw_value = str(raw or "").strip().replace(" ", "_")
    family_value = str(family or "").strip().replace(" ", "_")
    upper_raw = raw_value.upper()
    upper_family = family_value.upper()
    if "?" in upper_raw or "?" in upper_family:
        return LABEL2ID["AMBIGUOUS_TE"]
    pieces = [piece for piece in re.split(r"[/|:]", upper_raw) if piece]
    base = pieces[0] if pieces else ""
    if base in MAIN4:
        return MAIN4[base]
    if base in {"TIR", "MITE", "TRANSPOSON"}:
        return LABEL2ID["DNA"]
    if base in {"HELITRON", "RC"}:
        return LABEL2ID["KNOWN_OTHER_TE"]
    if base in KNOWN_OTHER:
        return KNOWN_OTHER[base]
    if base in UNKNOWN or (family_value and upper_family in UNKNOWN):
        return LABEL2ID["UNCLASSIFIED"]
    if base in NON_TE:
        return None if native else LABEL2ID["BG"]
    # Native output may use a valid TE name that is outside the four main
    # classes. Preserve it as an explicit unresolved class instead of turning
    # it into BG. The raw value is retained in parser statistics.
    return LABEL2ID["UNCLASSIFIED"]


def paint(length: int, intervals: Iterable[tuple[int, int, int]]) -> np.ndarray:
    """Paint intervals with a deterministic method-local overlap rule."""
    values = np.zeros(length, dtype=np.int8)
    ordered = sorted(intervals, key=lambda item: (item[0], item[1], item[2]))
    for left, right, label in ordered:
        if not (0 <= left < right <= length):
            raise ValueError(f"interval out of bounds: {left}-{right}/{length}")
        values[left:right] = label
    return values


def callable_mask(sequence: str) -> np.ndarray:
    return np.frombuffer(sequence.encode("ascii"), dtype="S1").astype("U1") .__ne__("N") & np.isin(
        np.frombuffer(sequence.encode("ascii"), dtype="S1"), [b"A", b"C", b"G", b"T"]
    )


def parse_source(path: Path, sequences: dict[str, str]) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    intervals: dict[str, list[tuple[int, int, int]]] = collections.defaultdict(list)
    raw_counts: collections.Counter[str] = collections.Counter()
    class_counts: collections.Counter[str] = collections.Counter()
    class_rows: collections.Counter[str] = collections.Counter()
    rows = 0
    target_rows = 0
    with open_text(path) as handle:
        for raw in handle:
            fields = raw.split()
            if len(fields) < 13:
                continue
            try:
                chrom, start, end = fields[5], int(fields[6]), int(fields[7])
            except (ValueError, IndexError):
                continue
            if end <= start:
                continue
            rows += 1
            raw_class, family = fields[11], fields[12]
            raw_counts[raw_class] += 1
            if chrom not in sequences:
                continue
            target_rows += 1
            left, right = max(0, start), min(len(sequences[chrom]), end)
            if right > left:
                label_id = split_class(raw_class, family, native=False)
                label_name = LABEL_NAMES[label_id] if label_id is not None else "BG"
                class_counts[label_name] += right - left
                class_rows[label_name] += 1
                intervals[chrom].append((left, right, int(label_id if label_id is not None else 0)))
    arrays = {chrom: paint(len(sequence), intervals.get(chrom, [])) for chrom, sequence in sequences.items()}
    return arrays, {
        "path": str(path),
        "rows_seen": rows,
        "target_rows": target_rows,
        "raw_class_rows": dict(sorted(raw_counts.items())),
        "painted_class_rows": dict(sorted(class_rows.items())),
        "painted_class_interval_bp_before_union": dict(sorted(class_counts.items())),
        "source_unknown_bp": int(sum(class_counts[name] for name in ("UNCLASSIFIED", "AMBIGUOUS_TE") if name in class_counts)),
        "policy": "UCSC fields 11/12 mapped with frozen SF5 ontology; explicit simple/low-complexity/RNA-like source rows are BG, Unknown is UNCLASSIFIED, '?' is AMBIGUOUS_TE, and unrecognized classes remain UNCLASSIFIED",
    }


def parse_attrs(value: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in value.split(";"):
        raw = raw.strip()
        if not raw:
            continue
        if "=" in raw:
            key, val = raw.split("=", 1)
        else:
            fields = raw.split(None, 1)
            if len(fields) != 2:
                continue
            key, val = fields
        result[key.strip().lower()] = val.strip().strip('"')
    return result


def empty_native_stats(path: Path, fmt: str) -> dict[str, object]:
    return {"path": str(path), "format": fmt, "rows_seen": 0, "target_rows": 0, "included_rows": 0,
            "skipped_non_te_rows": 0, "skipped_parent_or_missing_class_rows": 0,
            "unknown_rows": 0, "ambiguous_rows": 0, "raw_class_rows": {}, "unresolved_class_rows": {}}


def parse_rm2(path: Path, sequences: dict[str, str]) -> tuple[dict[str, list[tuple[int, int, int]]], dict[str, object]]:
    stats = empty_native_stats(path, "RepeatMasker_out")
    raw_counts: collections.Counter[str] = collections.Counter()
    unresolved: collections.Counter[str] = collections.Counter()
    intervals: dict[str, list[tuple[int, int, int]]] = collections.defaultdict(list)
    with open_text(path) as handle:
        for raw in handle:
            fields = raw.split()
            if len(fields) < 11 or not fields[0].isdigit():
                continue
            try:
                chrom, start, end = fields[4], int(fields[5]) - 1, int(fields[6])
            except ValueError:
                continue
            stats["rows_seen"] += 1
            raw_class = fields[10]
            raw_counts[raw_class] += 1
            if chrom not in sequences:
                continue
            stats["target_rows"] += 1
            label_id = split_class(raw_class, native=True)
            if label_id is None:
                stats["skipped_non_te_rows"] += 1
                continue
            if label_id == LABEL2ID["UNCLASSIFIED"]:
                stats["unknown_rows"] += 1
                unresolved[raw_class] += 1
            elif label_id == LABEL2ID["AMBIGUOUS_TE"]:
                stats["ambiguous_rows"] += 1
            left, right = max(0, start), min(len(sequences[chrom]), end)
            if right <= left:
                continue
            intervals[chrom].append((left, right, label_id))
            stats["included_rows"] += 1
    stats["raw_class_rows"] = dict(sorted(raw_counts.items()))
    stats["unresolved_class_rows"] = dict(sorted(unresolved.items()))
    return intervals, stats


def parse_edta(path: Path, sequences: dict[str, str]) -> tuple[dict[str, list[tuple[int, int, int]]], dict[str, object]]:
    stats = empty_native_stats(path, "EDTA_GFF3")
    raw_counts: collections.Counter[str] = collections.Counter()
    unresolved: collections.Counter[str] = collections.Counter()
    feature_counts: collections.Counter[str] = collections.Counter()
    retained_feature_counts: collections.Counter[str] = collections.Counter()
    intervals: dict[str, list[tuple[int, int, int]]] = collections.defaultdict(list)
    class_keys = ("classification", "class_family", "repeat_class", "class", "repclass")
    # EDTA's TEanno GFF3 has appeared in two relevant shapes in the pinned
    # releases: a repeat_region container with a complete TE child, and a
    # complete TE row with structural LTR/TIR children.  A generic
    # ``parent-with-any-child`` deletion is wrong for the latter because it
    # would retain only terminal LTRs and erase the internal TE body.  Keep all
    # rows first, then suppress only a container that is replaced by a complete
    # child or by explicit match-part evidence.
    rows: list[dict[str, object]] = []
    ids_with_children: dict[str, list[dict[str, object]]] = collections.defaultdict(list)
    with path.open("rt", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            if not raw.strip() or raw.startswith("#"):
                continue
            fields = raw.rstrip("\n").split("\t")
            if len(fields) < 5:
                continue
            feature = fields[2].strip().lower() if len(fields) >= 3 else ""
            try:
                chrom, start, end = fields[0], int(fields[3]) - 1, int(fields[4])
            except (ValueError, IndexError):
                continue
            stats["rows_seen"] += 1
            if chrom not in sequences:
                continue
            stats["target_rows"] += 1
            attrs = parse_attrs(fields[8] if len(fields) >= 9 else "")
            raw_class = next((attrs[key] for key in class_keys if attrs.get(key)), "")
            feature_counts[feature] += 1
            row: dict[str, object] = {
                "chrom": chrom,
                "left": max(0, start),
                "right": min(len(sequences[chrom]), end),
                "feature": feature,
                "attrs": attrs,
                "raw_class": raw_class,
                "label_id": None,
                "candidate": False,
                "skip_reason": None,
            }
            row_id = attrs.get("id", "")
            parents = [token.strip() for token in attrs.get("parent", "").split(",") if token.strip()]
            row["id"] = row_id
            row["parents"] = parents
            if feature in NON_TE_FEATURES:
                row["skip_reason"] = "non_te_feature"
            elif feature in STRUCTURAL_FEATURES:
                row["skip_reason"] = "structural_child"
            elif not raw_class and feature not in COMPLETE_TE_FEATURES:
                row["skip_reason"] = "missing_class"
            elif not raw_class and feature in COMPLETE_TE_FEATURES:
                # A complete feature without a classification is retained as
                # an unresolved native call only when the final parser can
                # identify it from the feature name.  The common generic
                # repeat_region container is handled after child inspection.
                if feature == "repeat_region":
                    row["skip_reason"] = "container_without_class"
                elif feature in FEATURE_LABELS:
                    row["label_id"] = FEATURE_LABELS[feature]
                    row["raw_class"] = feature
                    row["candidate"] = True
                else:
                    row["raw_class"] = feature
                    row["candidate"] = True
            else:
                label_id = split_class(raw_class, native=True)
                row["label_id"] = label_id
                if label_id is None:
                    row["skip_reason"] = "explicit_non_te_class"
                else:
                    row["candidate"] = True
            rows.append(row)
            if row_id:
                for parent in parents:
                    ids_with_children[parent].append(row)

    suppressed_parent_ids: set[str] = set()
    suppressed_parent_reasons: collections.Counter[str] = collections.Counter()
    for row in rows:
        if not row["candidate"]:
            continue
        row_id = str(row.get("id") or "")
        if not row_id:
            continue
        children = ids_with_children.get(row_id, [])
        if not children:
            continue
        feature = str(row["feature"])
        child_features = {str(child["feature"]) for child in children}
        complete_children = child_features & COMPLETE_TE_FEATURES
        evidence_children = {feature_name for feature_name in child_features if feature_name in {"match", "match_part", "repeat", "repeat_region", "transposable_element"}}
        if feature == "repeat_region" and (complete_children or evidence_children):
            suppressed_parent_ids.add(row_id)
            suppressed_parent_reasons["container_replaced_by_child"] += 1
        elif feature in {"match", "match_part"} and evidence_children:
            suppressed_parent_ids.add(row_id)
            suppressed_parent_reasons["match_container_replaced_by_child"] += 1

    for row in rows:
        if row["skip_reason"] is not None:
            stats["skipped_non_te_rows"] += int(row["skip_reason"] == "explicit_non_te_class")
            stats["skipped_parent_or_missing_class_rows"] += int(row["skip_reason"] != "explicit_non_te_class")
            continue
        row_id = str(row.get("id") or "")
        if row_id and row_id in suppressed_parent_ids:
            stats["skipped_parent_or_missing_class_rows"] += 1
            continue
        raw_class = str(row["raw_class"])
        label_id = row["label_id"]
        if label_id is None:
            label_id = split_class(raw_class, native=True)
        if label_id is None:
            stats["skipped_non_te_rows"] += 1
            continue
        raw_counts[raw_class] += 1
        retained_feature_counts[str(row["feature"])] += 1
        if label_id == LABEL2ID["UNCLASSIFIED"]:
            stats["unknown_rows"] += 1
            unresolved[raw_class] += 1
        elif label_id == LABEL2ID["AMBIGUOUS_TE"]:
            stats["ambiguous_rows"] += 1
        left, right = int(row["left"]), int(row["right"])
        if right <= left:
            continue
        intervals[str(row["chrom"])].append((left, right, label_id))
        stats["included_rows"] += 1
    stats["raw_class_rows"] = dict(sorted(raw_counts.items()))
    stats["unresolved_class_rows"] = dict(sorted(unresolved.items()))
    stats["feature_rows"] = dict(sorted(feature_counts.items()))
    stats["retained_feature_rows"] = dict(sorted(retained_feature_counts.items()))
    stats["suppressed_parent_rows"] = int(len(suppressed_parent_ids))
    stats["suppressed_parent_reasons"] = dict(sorted(suppressed_parent_reasons.items()))
    stats["parent_policy"] = (
        "suppress repeat_region only when replaced by a complete TE child or explicit match-part evidence; "
        "retain complete TE bodies such as LTR_retrotransposon even when they have structural LTR/TIR children"
    )
    return intervals, stats


def native_method(method: str, root: Path, sequences: dict[str, str]) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    status_path = root / "status.json"
    if not status_path.is_file():
        raise FileNotFoundError(f"native status missing: {status_path}")
    status = json.loads(status_path.read_text(encoding="utf-8"))
    if status.get("status") != "COMPLETED":
        raise RuntimeError(f"native cell is not terminal-success: {root} ({status.get('status')})")
    summary_path = root / "annotation_summary.json"
    if not summary_path.is_file():
        raise FileNotFoundError(f"native annotation_summary.json missing: {summary_path}")
    if method == "RM2":
        annotation = root / "annotation.out"
        if not annotation.is_file() or annotation.stat().st_size == 0:
            raise FileNotFoundError(f"RM2 native annotation.out missing or empty: {annotation}")
        intervals, stats = parse_rm2(annotation, sequences)
    elif method == "EDTA":
        annotation = root / "annotation.gff3"
        if not annotation.is_file() or annotation.stat().st_size == 0:
            raise FileNotFoundError(f"EDTA native annotation.gff3 missing or empty: {annotation}")
        intervals, stats = parse_edta(annotation, sequences)
    else:
        raise ValueError(method)
    arrays = {chrom: paint(len(sequence), intervals.get(chrom, [])) for chrom, sequence in sequences.items()}
    stats["annotation"] = str(annotation)
    stats["whole_cell_status"] = {
        "status": status.get("status"),
        "wall_seconds": status.get("wall_seconds"),
        "stages": status.get("stages", []),
        "annotation_summary": str(summary_path),
    }
    return arrays, stats


def load_class_map(path: Path, sequences: dict[str, str]) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    if not path.is_file():
        raise FileNotFoundError(f"NTv2 class map missing: {path}")
    intervals: dict[str, list[tuple[int, int, str]]] = collections.defaultdict(list)
    with open_text(path) as handle:
        for line_no, raw in enumerate(handle, 1):
            fields = raw.split()
            if len(fields) < 4:
                continue
            chrom, left, right, label = fields[0], int(fields[1]), int(fields[2]), fields[3]
            if chrom not in sequences:
                continue
            if label not in LABEL2ID and label != NONCALLABLE:
                raise ValueError(f"unknown NTv2 class label at {path}:{line_no}: {label}")
            if not (0 <= left < right <= len(sequences[chrom])):
                raise ValueError(f"NTv2 class-map interval out of bounds at {path}:{line_no}")
            intervals[chrom].append((left, right, label))
    arrays: dict[str, np.ndarray] = {}
    for chrom, sequence in sequences.items():
        values = np.full(len(sequence), -2, dtype=np.int8)
        for left, right, label in sorted(intervals.get(chrom, []), key=lambda item: (item[0], item[1], LABEL2ID.get(item[2], -1))):
            values[left:right] = -1 if label == NONCALLABLE else LABEL2ID[label]
        callable_values = np.asarray([base in "ACGT" for base in sequence], dtype=bool)
        if np.any(values[callable_values] < 0):
            raise RuntimeError(f"NTv2 class map does not cover every callable base on {chrom}")
        if np.any(values[~callable_values] != -1):
            raise RuntimeError(f"NTv2 class map does not mark every non-callable base on {chrom}")
        arrays[chrom] = values
    return arrays, {"path": str(path), "format": "per_base_class_runs", "prediction_source": "frozen class checkpoint argmax; no threshold or calibration"}


def write_runs(path: Path, arrays: dict[str, np.ndarray], sequences: dict[str, str]) -> dict[str, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    counts: collections.Counter[str] = collections.Counter()
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for chrom, sequence in sequences.items():
            values = arrays[chrom]
            if values.shape != (len(sequence),):
                raise ValueError(f"prediction shape differs from sequence on {chrom}")
            labels = np.asarray([NONCALLABLE if base not in "ACGT" else LABEL_NAMES[int(value)] for base, value in zip(sequence, values)], dtype=object)
            boundaries = np.r_[0, np.flatnonzero(labels[1:] != labels[:-1]) + 1, len(labels)]
            for left, right in zip(boundaries[:-1], boundaries[1:]):
                label = str(labels[left])
                handle.write(f"{chrom}\t{int(left)}\t{int(right)}\t{label}\n")
                counts[label] += int(right - left)
    return dict(sorted(counts.items()))


def confusion(reference: np.ndarray, prediction: np.ndarray, mask: np.ndarray, rows: list[int] | None = None) -> np.ndarray:
    if reference.shape != prediction.shape or reference.shape != mask.shape:
        raise ValueError("reference, prediction and mask shapes differ")
    valid = mask & (prediction >= 0)
    if rows is not None:
        valid &= np.isin(reference, rows)
    matrix = np.zeros((len(LABEL_NAMES) if rows is None else len(rows), len(LABEL_NAMES)), dtype=np.int64)
    row_index = {value: index for index, value in enumerate(rows)} if rows is not None else None
    true_values = reference[valid].astype(np.int64)
    pred_values = prediction[valid].astype(np.int64)
    if rows is None:
        np.add.at(matrix, (true_values, pred_values), 1)
    else:
        np.add.at(matrix, ([row_index[int(value)] for value in true_values], pred_values), 1)
    return matrix


def metrics_from_confusion(matrix: np.ndarray, row_labels: list[int]) -> dict[str, object]:
    per_class: dict[str, dict[str, object]] = {}
    f1_values: list[float] = []
    precision_values: list[float] = []
    recall_values: list[float] = []
    for row_index, label_id in enumerate(row_labels):
        tp = int(matrix[row_index, label_id])
        fp = int(matrix[:, label_id].sum() - tp)
        fn = int(matrix[row_index, :].sum() - tp)
        support = int(matrix[row_index, :].sum())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[LABEL_NAMES[label_id]] = {"support_bp": support, "tp_bp": tp, "fp_bp": fp, "fn_bp": fn, "precision": precision, "recall": recall, "f1": f1}
        if support:
            precision_values.append(precision)
            recall_values.append(recall)
            f1_values.append(f1)
    return {
        "row_labels": [LABEL_NAMES[label_id] for label_id in row_labels],
        "predicted_columns": LABEL_NAMES,
        "confusion_rows_true_cols_pred_bp": matrix.tolist(),
        "per_class": per_class,
        "macro_precision": float(np.mean(precision_values)) if precision_values else 0.0,
        "macro_recall": float(np.mean(recall_values)) if recall_values else 0.0,
        "macro_f1": float(np.mean(f1_values)) if f1_values else 0.0,
        "support_total_bp": int(matrix.sum()),
    }


def method_metrics(reference: dict[str, np.ndarray], prediction: dict[str, np.ndarray], sequences: dict[str, str]) -> dict[str, object]:
    ref = np.concatenate([reference[chrom] for chrom in sequences])
    pred = np.concatenate([prediction[chrom] for chrom in sequences])
    callable_values = np.concatenate([np.asarray([base in "ACGT" for base in sequences[chrom]], dtype=bool) for chrom in sequences])
    full = metrics_from_confusion(confusion(ref, pred, callable_values), list(range(len(LABEL_NAMES))))
    known_rows = [0, 1, 2, 3, 4]
    known_mask = callable_values & np.isin(ref, known_rows)
    known = metrics_from_confusion(confusion(ref, pred, known_mask, known_rows), known_rows)
    true_te_rows = [1, 2, 3, 4]
    true_te_mask = callable_values & np.isin(ref, true_te_rows)
    true_te_matrix = confusion(ref, pred, true_te_mask, true_te_rows)
    true_te = metrics_from_confusion(true_te_matrix, true_te_rows)
    any_te = ((pred >= 0) & np.isin(pred, true_te_rows) & true_te_mask)
    true_te["any_main4_te_recovery_bp"] = int(any_te.sum())
    true_te["any_main4_te_recall"] = float(any_te.sum() / true_te_mask.sum()) if true_te_mask.sum() else None
    return {
        "callable_bp": int(callable_values.sum()),
        "source_class_bp": {LABEL_NAMES[i]: int((ref[callable_values] == i).sum()) for i in range(len(LABEL_NAMES))},
        "source_unknown_unclassified_bp": int(((ref == LABEL2ID["UNCLASSIFIED"]) & callable_values).sum()),
        "source_ambiguous_bp": int(((ref == LABEL2ID["AMBIGUOUS_TE"]) & callable_values).sum()),
        "source_known_other_bp": int(((ref == LABEL2ID["KNOWN_OTHER_TE"]) & callable_values).sum()),
        "primary_known_reference_mask": "source BG/SINE/LINE/LTR/DNA only; source KNOWN_OTHER_TE/AMBIGUOUS_TE/UNCLASSIFIED excluded",
        "primary_known": known,
        "full8": full,
        "true_te_conditional": true_te,
    }


def load_sequences(path: Path, target_names: list[str]) -> dict[str, str]:
    all_records = {name: seq for name, seq in fasta_records(path)}
    missing = sorted(set(target_names) - set(all_records))
    if missing:
        raise FileNotFoundError(f"target chromosomes missing from {path}: {missing}")
    return {name: all_records[name] for name in target_names}


def run(args: argparse.Namespace) -> dict[str, object]:
    config = json.loads(args.config.resolve().read_text(encoding="utf-8"))
    out = args.output_dir.resolve()
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"refusing to replace non-empty score output: {out}")
    out.mkdir(parents=True, exist_ok=True)
    species_results: dict[str, object] = {}
    started = time.time()
    for species, species_cfg in config["species"].items():
        target_names = list(species_cfg["target_chromosomes"])
        sequences = load_sequences((ROOT / "outputs/UNIFIED-NTV2-CLASS-MAP-BENCH-20260918/prepared" / f"{species}.fa").resolve(), target_names)
        source, source_stats = parse_source((ROOT / species_cfg["source_labels"]).resolve(), sequences)
        ntv2_path = ROOT / "outputs/UNIFIED-NTV2-CLASS-MAP-BENCH-20260918/ntv2" / species / "predicted_classes.bed.gz"
        ntv2, ntv2_stats = load_class_map(ntv2_path, sequences)
        method_arrays: dict[str, dict[str, np.ndarray]] = {"NTv2_class": {chrom: np.where(values < 0, 0, values) for chrom, values in ntv2.items()}}
        method_stats: dict[str, object] = {"NTv2_class": ntv2_stats}
        normalized_root = ROOT / "outputs/UNIFIED-NTV2-CLASS-MAP-BENCH-20260918/native" / species
        for method in ("EDTA", "RM2"):
            arrays, stats = native_method(method, (ROOT / species_cfg["native_root"] / method).resolve(), sequences)
            method_arrays[method] = arrays
            native_out = normalized_root / method / "predicted_classes.bed.gz"
            method_stats[method] = {**stats, "normalized_output": str(native_out), "normalized_label_counts": write_runs(native_out, arrays, sequences)}
        method_results: dict[str, object] = {}
        for method, arrays in method_arrays.items():
            method_results[method] = method_metrics(source, arrays, sequences)
        method_results["D_binary"] = {"status": "N/A", "reason": "WHOLE D output is binary material-only and has no class prediction; it is not remapped"}
        species_results[species] = {
            "scientific_name": species_cfg["scientific_name"],
            "assembly": species_cfg["assembly"],
            "target_chromosomes": target_names,
            "target_lengths_bp": {chrom: len(sequences[chrom]) for chrom in target_names},
            "source": source_stats,
            "methods": method_results,
            "method_outputs": method_stats,
        }
    result = {
        "protocol": "UNIFIED-NTV2-CLASS-MAP-BENCH-20260918",
        "status": "COMPLETED_COMPARATOR_RELATIVE_CLASS_MAP",
        "quality_only": True,
        "scope": "chicken chr10/chr20 and zebrafish chr10/chr20; fixed before native score inspection",
        "elapsed_seconds": time.time() - started,
        "model_contract": config["backbone"],
        "evaluation_contract": config["evaluation"],
        "species": species_results,
        "native_timing_boundary": "Native EDTA/RM2 timing fields are whole-genome cell metadata from WHOLE-GENOME-BENCHMARK; this result does not present them as class-map or full-genome CPU timing.",
        "truth_boundary": config["evaluation"]["truth_boundary"],
    }
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (out / "metrics.tsv").open("w", encoding="utf-8") as handle:
        handle.write("species\tmethod\tendpoint\tmacro_f1\tmacro_precision\tmacro_recall\tsupport_bp\n")
        for species, species_result in species_results.items():
            for method, metrics in species_result["methods"].items():
                if "primary_known" not in metrics:
                    continue
                for endpoint in ("primary_known", "full8", "true_te_conditional"):
                    value = metrics[endpoint]
                    handle.write(f"{species}\t{method}\t{endpoint}\t{value.get('macro_f1')}\t{value.get('macro_precision')}\t{value.get('macro_recall')}\t{value.get('support_total_bp')}\n")
    print(json.dumps({"status": result["status"], "species": list(species_results), "output": str(out)}, sort_keys=True))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/UNIFIED-NTV2-CLASS-MAP-BENCH-20260918/score")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
