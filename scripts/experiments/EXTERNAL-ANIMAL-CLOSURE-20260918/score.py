#!/usr/bin/env python3
"""Score fixed D predictions against same-assembly source layers.

The positive-only quantities are the primary readout.  A separate
``source_comparator`` metric is emitted when the source layer has explicit
Unknown/ambiguous intervals: those intervals are removed from the denominator,
and all remaining callable non-positive sequence is treated as comparator
background.  This is a reproducible source-layer convention, not biological
truth.
"""
from __future__ import annotations

import argparse
import gzip
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


KNOWN = {"DNA", "LINE", "SINE", "LTR", "RC", "Retroposon"}
UNCERTAIN = {"Unknown", "ARTEFACT"}


def open_text(path: Path):
    return gzip.open(path, "rt") if path.suffix == ".gz" else path.open()


def fasta(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    name, parts = None, []
    with opener(path, "rt") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    yield name, "".join(parts).upper()
                name, parts = line[1:].split()[0], []
            else:
                if name is None:
                    raise ValueError("sequence before FASTA header")
                parts.append(line)
    if name is not None:
        yield name, "".join(parts).upper()


def bed(path: Path):
    with open_text(path) as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip() or line.startswith(("#", "track", "browser")):
                continue
            fields = line.split()
            if len(fields) < 3:
                raise ValueError(f"invalid BED row {path}:{number}")
            left, right = int(fields[1]), int(fields[2])
            if left < 0 or right <= left:
                raise ValueError(f"invalid BED coordinates {path}:{number}")
            yield fields[0], left, right


def repeat_intervals(path: Path, regions):
    by_panel = defaultdict(list)
    uncertain_by_panel = defaultdict(list)
    source_class_rows = defaultdict(int)
    rows_seen = 0
    selected_rows = 0
    selected_uncertain_rows = 0
    with open_text(path) as handle:
        for number, line in enumerate(handle, 1):
            fields = line.split()
            if len(fields) < 11 or not fields[0].isdigit():
                continue
            rows_seen += 1
            seqid = fields[4]
            # Strict layer: uncertain classes such as `DNA?` are excluded.
            broad = fields[10].split("/", 1)[0]
            source_class_rows[broad] += 1
            if seqid not in regions:
                continue
            start, end = int(fields[5]) - 1, int(fields[6])
            row = regions[seqid]
            left, right = max(start, row["start"]), min(end, row["end"])
            if right <= left:
                continue
            if broad in KNOWN:
                by_panel[row["panel_id"]].append((left - row["start"], right - row["start"], fields[10]))
                selected_rows += 1
            elif broad in UNCERTAIN or "?" in broad:
                uncertain_by_panel[row["panel_id"]].append(
                    (left - row["start"], right - row["start"], fields[10])
                )
                selected_uncertain_rows += 1
    return by_panel, uncertain_by_panel, {
        "rows_seen": rows_seen,
        "selected_known_te_rows": selected_rows,
        "selected_uncertain_rows": selected_uncertain_rows,
        "broad_class_rows": dict(source_class_rows),
    }


def merge_mask(width, intervals):
    mask = np.zeros(width, dtype=bool)
    for left, right, _ in intervals:
        if not (0 <= left < right <= width):
            raise ValueError(f"panel interval out of bounds: {left}-{right}/{width}")
        mask[left:right] = True
    return mask


def counts(callable_mask, positive, predicted, uncertain=None):
    labelled = positive & callable_mask
    prediction = predicted & callable_mask
    denominator = int(labelled.sum())
    recovered = int((labelled & prediction).sum())
    callable_bp = int(callable_mask.sum())
    prediction_bp = int(prediction.sum())
    result = {"callable_bp": callable_bp, "reference_positive_bp": denominator,
            "recovered_positive_bp": recovered,
            "positive_recovery": recovered / denominator if denominator else None,
            "predicted_bp": prediction_bp,
            "predicted_fraction_of_callable": prediction_bp / callable_bp if callable_bp else None,
            "predicted_bp_without_reference_support": int((prediction & ~positive).sum()),
            "unknown_or_unlabelled_callable_bp": int((callable_mask & ~positive).sum())}
    if uncertain is not None:
        if uncertain.shape != callable_mask.shape:
            raise ValueError("uncertain mask shape differs from callable mask")
        eligible = callable_mask & ~uncertain
        comparator_positive = positive & eligible
        comparator_prediction = predicted & eligible
        tp = int((comparator_positive & comparator_prediction).sum())
        fp = int((~comparator_positive & comparator_prediction).sum())
        fn = int((comparator_positive & ~comparator_prediction).sum())
        tn = int((~comparator_positive & ~comparator_prediction & eligible).sum())
        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / (tp + fn) if tp + fn else None
        f1 = (2 * precision * recall / (precision + recall)) if precision and recall else (0.0 if precision == 0.0 or recall == 0.0 else None)
        result["source_comparator"] = {
            "eligible_callable_bp": int(eligible.sum()),
            "excluded_uncertain_callable_bp": int((callable_mask & uncertain).sum()),
            "reference_positive_bp": int(comparator_positive.sum()),
            "reference_background_bp": int((~comparator_positive & eligible).sum()),
            "predicted_positive_bp": int(comparator_prediction.sum()),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "background_definition": "callable bases outside strict known positives and outside Unknown/ambiguous/ARTEFACT rows",
            "biological_truth_claim": False,
        }
    return result


def run(args):
    panel = json.loads((args.panel / "panel.json").read_text())
    regions = {row["source_seqid"]: row for row in panel["regions"]}
    panel_sequences = dict(fasta(args.panel / "panel.fa"))
    if set(panel_sequences) != {row["panel_id"] for row in panel["regions"]}:
        raise ValueError("panel FASTA IDs differ from panel manifest")
    inference = json.loads((args.inference / "summary.json").read_text())
    if inference.get("status") != "COMPLETED" or inference.get("total_bp") != panel["total_bp"]:
        raise ValueError("inference is incomplete or has a different denominator")
    positive_by_panel, uncertain_by_panel, source_info = repeat_intervals(Path(args.reference), regions)
    predictions = defaultdict(list)
    for seqid, left, right in bed(args.inference / "material_runs.bed"):
        predictions[seqid].append((left, right))
    per_region = []
    all_callable, all_positive, all_predicted, all_uncertain = [], [], [], []
    for row in panel["regions"]:
        panel_id = row["panel_id"]
        sequence = panel_sequences[panel_id]
        if len(sequence) != panel["selection"]["length_bp"]:
            raise ValueError(f"unexpected sequence length for {panel_id}")
        symbols = np.frombuffer(sequence.encode("ascii"), dtype="S1")
        callable_mask = np.isin(symbols, [b"A", b"C", b"G", b"T"])
        positive = merge_mask(len(sequence), positive_by_panel.get(panel_id, []))
        uncertain = merge_mask(len(sequence), uncertain_by_panel.get(panel_id, []))
        predicted = np.zeros(len(sequence), dtype=bool)
        for left, right in predictions.get(panel_id, []):
            if not (0 <= left < right <= len(sequence)):
                raise ValueError(f"prediction outside fixed panel: {panel_id}:{left}-{right}")
            predicted[left:right] = True
        value = {**row, **counts(callable_mask, positive, predicted, uncertain),
                 "source_positive_intervals": len(positive_by_panel.get(panel_id, [])),
                 "source_uncertain_intervals": len(uncertain_by_panel.get(panel_id, [])),
                 "prediction_intervals": len(predictions.get(panel_id, []))}
        per_region.append(value)
        all_callable.append(callable_mask)
        all_positive.append(positive)
        all_predicted.append(predicted)
        all_uncertain.append(uncertain)
    pooled = counts(
        np.concatenate(all_callable),
        np.concatenate(all_positive),
        np.concatenate(all_predicted),
        np.concatenate(all_uncertain),
    )
    result = {"status": "COMPLETED_POSITIVE_ONLY_WITH_SOURCE_COMPARATOR", "species": panel["species"],
              "assembly": panel["source"]["assembly"], "panel": panel,
              "inference": str(args.inference), "reference": str(args.reference),
              "source_info": source_info, "frozen_model": inference,
              "pooled": pooled, "per_region": per_region,
              "claim_boundary": "Recovery of a documented same-assembly source-dependent positive layer on a fixed 104.86-Mb panel. The optional source-comparator P/R/F1 excludes Unknown/ambiguous/ARTEFACT intervals and treats remaining callable non-positive sequence as comparator background; it is not biological truth. Unlabelled sequence is unknown for the primary positive-only readout, and no whole-genome claim is made."}
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--inference", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
