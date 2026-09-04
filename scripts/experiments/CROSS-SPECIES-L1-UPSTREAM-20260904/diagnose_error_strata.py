#!/usr/bin/env python3
"""CPU-only D0-S strata for the frozen seed42 inference caches."""

from __future__ import annotations

import argparse
import bisect
import csv
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "CROSS-SPECIES-L1-20260903"))
import calibrate_evaluate_x0 as ev  # noqa: E402


SPLITS = ("TRAIN", "CAL", "DEV", "SCREEN")
ARMS = ("B0", "B1")
TILE_BP, HALF_BP, KMER_BP = 8192, 4096, 6
RADIUS = 6
BINS = ("<80", "80-499", "500-999", ">=1000")
CLASSES = ("LINE", "SINE", "LTR", "DNA", "RC", "Retroposon")
BITS = {name: 1 << i for i, name in enumerate(CLASSES)}
LOCATION_BUCKETS = (
    "mixed_6bp_token",
    "tail_single_bp",
    "boundary_transition_within_6bp",
    "half_or_tile_seam_within_6bp",
    "interior_outside_boundary_seam",
)


def _ratio(n, d):
    return n / d if d else 0.0


def _f1(tp, fp, fn):
    return _ratio(2 * tp, 2 * tp + fp + fn)


def load_cache(path: Path) -> dict[str, np.ndarray]:
    """Consume the audited cache shape emitted by ``cache_tiles``."""
    with np.load(path, allow_pickle=False) as data:
        return {name: data[name] for name in ("margin", "truth", "callable", "hard_negative", "tile_id", "chrom", "start")}


def read_records(path: Path) -> dict[str, dict[str, object]]:
    grouped = defaultdict(dict)
    for record in ev.read_jsonl(path):
        grouped[str(record["tile_id"])][int(record["half"])] = record
    return {
        tile_id: {
            "chrom": str(halves[0]["chrom"]),
            "start": int(halves[0]["start"]),
            "sequence": str(halves[0]["sequence"]).upper() + str(halves[1]["sequence"]).upper(),
        }
        for tile_id, halves in grouped.items()
    }


def attach_records(cache, records):
    return [
        {"tile_id": str(tile_id), "chrom": records[str(tile_id)]["chrom"], "start": records[str(tile_id)]["start"], "sequence": records[str(tile_id)]["sequence"], "margin": cache["margin"][i], "truth": cache["truth"][i], "callable": cache["callable"][i], "hard_negative": cache["hard_negative"][i]}
        for i, tile_id in enumerate(cache["tile_id"])
    ]


def read_raw_classes(path: Path, desired_chroms: set[str]):
    """Read RepeatMasker parts[4], parts[5], parts[6], and parts[10]."""
    intervals = defaultdict(list)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt") as handle:
        for line in handle:
            parts = line.split()
            if len(parts) < 11 or not parts[0].isdigit() or parts[4] not in desired_chroms:
                continue
            bit = BITS.get(parts[10].split("/", 1)[0])
            if bit:
                intervals[parts[4]].append((int(parts[5]) - 1, int(parts[6]), bit))
    return {
        chrom: (tuple(sorted(rows)), tuple(row[0] for row in sorted(rows)))
        for chrom, rows in intervals.items()
    }


def class_mask_for_tile(chrom, start, intervals, length=TILE_BP):
    mask = np.zeros(length, dtype=np.uint8)
    entry = intervals.get(chrom, ((), ()))
    if entry and entry[0] and isinstance(entry[0][0], (int, np.integer)):
        rows = tuple(entry)
        starts = tuple(row[0] for row in rows)
    else:
        rows, starts = entry
    index = max(0, bisect.bisect_right(starts, start) - 1)
    end = start + length
    for row_start, row_end, bit in rows[index:]:
        if row_start >= end:
            break
        left, right = max(start, row_start) - start, min(end, row_end) - start
        if right > left:
            mask[left:right] |= np.uint8(bit)
    return mask


def token_spans(length=TILE_BP):
    spans = []
    for half in range(0, length, HALF_BP):
        full_end = half + ((min(length, half + HALF_BP) - half) // KMER_BP) * KMER_BP
        spans.extend((s, s + KMER_BP) for s in range(half, full_end, KMER_BP))
        spans.extend((s, s + 1) for s in range(full_end, min(length, half + HALF_BP)))
    return spans


def mixed_6bp_token_mask(truth, callable_mask):
    truth, callable_mask = np.asarray(truth, bool), np.asarray(callable_mask, bool)
    result = np.zeros(truth.shape, bool)
    for left, right in token_spans(len(truth)):
        if right - left == KMER_BP:
            c = callable_mask[left:right]
            if np.any(truth[left:right] & c) and np.any(~truth[left:right] & c):
                result[left:right] = True
    return result


def _near(mask, boundary, radius=RADIUS):
    mask[max(0, boundary - radius):min(len(mask), boundary + radius)] = True


def boundary_transition_mask(truth, callable_mask, radius=RADIUS):
    base = np.asarray(truth, bool) & np.asarray(callable_mask, bool)
    result = np.zeros(base.shape, bool)
    for boundary in np.flatnonzero(base[1:] != base[:-1]) + 1:
        _near(result, int(boundary), radius)
    return result


def location_masks(truth, callable_mask):
    boundary = boundary_transition_mask(truth, callable_mask)
    seam = np.zeros(len(truth), bool)
    for point in (0, HALF_BP, len(truth)):
        _near(seam, point)
    tail = np.zeros(len(truth), bool)
    for left, right in token_spans(len(truth)):
        if right - left == 1:
            tail[left:right] = True
    return {"mixed_6bp_token": mixed_6bp_token_mask(truth, callable_mask), "tail_single_bp": tail, "boundary_transition_within_6bp": boundary, "half_or_tile_seam_within_6bp": seam, "interior_outside_boundary_seam": ~(boundary | seam)}


def truth_length_strata(tiles, predictions):
    result = {name: {"positive_bp": 0, "fn_bp": 0, "truth_runs": 0, "missed_runs": 0} for name in BINS}
    for tile, predicted in zip(tiles, predictions):
        truth = np.asarray(tile["truth"], bool) & np.asarray(tile["callable"], bool)
        for left, right in ev.runs_from_bool(truth):
            length = right - left
            name = "<80" if length < 80 else "80-499" if length < 500 else "500-999" if length < 1000 else ">=1000"
            row = result[name]
            row["positive_bp"] += length
            row["fn_bp"] += int(np.sum(truth[left:right] & ~predicted[left:right]))
            row["truth_runs"] += 1
            row["missed_runs"] += int(not np.any(predicted[left:right]))
    for row in result.values():
        row["tp_bp"] = row["positive_bp"] - row["fn_bp"]
        row["recall"] = _ratio(row["tp_bp"], row["positive_bp"])
        row["missed_rate"] = _ratio(row.pop("missed_runs"), row["truth_runs"])
    return result


def te_top_class_strata(tiles, predictions, class_masks):
    counts = defaultdict(lambda: [0, 0, 0])
    for tile, predicted, classes in zip(tiles, predictions, class_masks):
        truth = np.asarray(tile["truth"], bool) & np.asarray(tile["callable"], bool)
        for bitmask in np.unique(classes[truth]):
            selected = truth & (classes == bitmask)
            row = counts[int(bitmask)]
            row[0] += int(np.sum(selected))
            row[1] += int(np.sum(selected & predicted))
            row[2] += int(np.sum(selected & ~predicted))
    by_bitmask, mixed = {}, []
    for bitmask, (positive, tp, fn) in sorted(counts.items()):
        names = [name for name, bit in BITS.items() if bitmask & bit]
        label = "unclassified" if not names else names[0] if len(names) == 1 else "mixed"
        by_bitmask[str(bitmask)] = {"bitmask": bitmask, "label": label, "classes": names, "positive_bp": positive, "tp_bp": tp, "fn_bp": fn, "recall": _ratio(tp, positive)}
        if label == "mixed":
            mixed.append(bitmask)
    return {"class_bit_order": list(CLASSES), "by_bitmask": by_bitmask, "mixed_bitmasks": mixed, "false_positive_allocation": "none"}


def _conf(truth, callable_mask, predicted, selected=None):
    selected = callable_mask if selected is None else selected & callable_mask
    return {"callable_bp": int(np.sum(selected)), "positive_bp": int(np.sum(selected & truth)), "tp_bp": int(np.sum(selected & truth & predicted)), "fp_bp": int(np.sum(selected & ~truth & predicted)), "fn_bp": int(np.sum(selected & truth & ~predicted))}


def error_location_strata(tiles, predictions):
    counts = {name: {key: 0 for key in ("callable_bp", "tp_bp", "fp_bp", "fn_bp")} for name in LOCATION_BUCKETS}
    global_counts = {key: 0 for key in ("tp_bp", "fp_bp", "fn_bp")}
    memberships, pairs = defaultdict(int), defaultdict(int)
    for tile, predicted in zip(tiles, predictions):
        truth, callable_mask = np.asarray(tile["truth"], bool), np.asarray(tile["callable"], bool)
        base = _conf(truth, callable_mask, predicted)
        for key in global_counts:
            global_counts[key] += base[key]
        masks = location_masks(truth, callable_mask)
        names, matrix = list(masks), np.stack(list(masks.values()))
        for n in np.sum(matrix[:, callable_mask], axis=0):
            memberships[int(n)] += 1
        for i, name in enumerate(names):
            row = counts[name]
            for key, value in _conf(truth, callable_mask, predicted, masks[name]).items():
                row[key] += value
            for other in names[i + 1:]:
                overlap = masks[name] & masks[other] & callable_mask
                if np.any(overlap):
                    pairs[f"{name}&{other}"] += int(np.sum(overlap))
    total_errors = global_counts["fp_bp"] + global_counts["fn_bp"]
    buckets = {}
    for name, row in counts.items():
        errors = row["fp_bp"] + row["fn_bp"]
        buckets[name] = {**row, "error_bp": errors, "error_mass_fraction": _ratio(errors, total_errors), "fp_error_mass_fraction": _ratio(row["fp_bp"], global_counts["fp_bp"]), "fn_error_mass_fraction": _ratio(row["fn_bp"], global_counts["fn_bp"])}
    return {"buckets": buckets, "global": {**global_counts, "error_bp": total_errors}, "overlap": {"masks_are_nonexclusive": True, "callable_bp_by_membership_count": {str(k): v for k, v in sorted(memberships.items())}, "multiple_bucket_callable_bp": sum(v for k, v in memberships.items() if k > 1), "pair_callable_bp": dict(sorted(pairs.items()))}}


def spatial_strata(tiles, predictions):
    blocks = defaultdict(lambda: {key: 0 for key in ("callable_bp", "positive_bp", "tp_bp", "fp_bp", "fn_bp")})
    for tile, predicted in zip(tiles, predictions):
        key = f'{tile["chrom"]}:{int(tile["start"]) // (512 * 1024)}'
        for name, value in _conf(np.asarray(tile["truth"], bool), np.asarray(tile["callable"], bool), predicted).items():
            blocks[key][name] += value
    return {key: {**row, "precision": _ratio(row["tp_bp"], row["tp_bp"] + row["fp_bp"]), "recall": _ratio(row["tp_bp"], row["tp_bp"] + row["fn_bp"]), "f1": _f1(row["tp_bp"], row["fp_bp"], row["fn_bp"])} for key, row in sorted(blocks.items())}


def non_acgt_strata(tiles, predictions, global_counts):
    row = {key: 0 for key in ("non_acgt_bp", "non_acgt_callable_bp", "non_acgt_positive_bp", "tp_bp", "fp_bp", "fn_bp")}
    for tile, predicted in zip(tiles, predictions):
        non_acgt = np.fromiter((base not in "ACGT" for base in tile["sequence"]), bool, TILE_BP)
        truth, callable_mask = np.asarray(tile["truth"], bool), np.asarray(tile["callable"], bool)
        selected = non_acgt & callable_mask
        row["non_acgt_bp"] += int(np.sum(non_acgt))
        row["non_acgt_callable_bp"] += int(np.sum(selected))
        row["non_acgt_positive_bp"] += int(np.sum(selected & truth))
        row["tp_bp"] += int(np.sum(selected & truth & predicted))
        row["fp_bp"] += int(np.sum(selected & ~truth & predicted))
        row["fn_bp"] += int(np.sum(selected & truth & ~predicted))
    errors = row["fp_bp"] + row["fn_bp"]
    return {**row, "positive_overlap_fraction": _ratio(row["non_acgt_positive_bp"], global_counts["positive_bp"]), "error_bp": errors, "error_mass_fraction": _ratio(errors, global_counts["fp_bp"] + global_counts["fn_bp"]), "priority": "P>U>N; P-overlapping non-ACGT bases remain P"}


def panel_report(tiles, calibration, raw_classes):
    slope, intercept, threshold = map(float, (calibration["platt_slope"], calibration["platt_intercept"], calibration["threshold"]))
    predictions = [(ev.sigmoid(slope * np.asarray(tile["margin"], float) + intercept) >= threshold) & tile["callable"] for tile in tiles]
    global_counts = {key: 0 for key in ("callable_bp", "positive_bp", "tp_bp", "fp_bp", "fn_bp")}
    for tile, predicted in zip(tiles, predictions):
        for key, value in _conf(np.asarray(tile["truth"], bool), np.asarray(tile["callable"], bool), predicted).items():
            global_counts[key] += value
    global_counts.update({"precision": _ratio(global_counts["tp_bp"], global_counts["tp_bp"] + global_counts["fp_bp"]), "recall": _ratio(global_counts["tp_bp"], global_counts["tp_bp"] + global_counts["fn_bp"]), "f1": _f1(global_counts["tp_bp"], global_counts["fp_bp"], global_counts["fn_bp"]), "positive_prevalence": _ratio(global_counts["positive_bp"], global_counts["callable_bp"])})
    class_masks = [class_mask_for_tile(tile["chrom"], tile["start"], raw_classes) for tile in tiles]
    return {"tiles": len(tiles), "calibration": {"platt_slope": slope, "platt_intercept": intercept, "threshold": threshold}, "natural_metrics": global_counts, "truth_positive_run_length": truth_length_strata(tiles, predictions), "te_top_class": te_top_class_strata(tiles, predictions, class_masks), "error_location": error_location_strata(tiles, predictions), "spatial_blocks_512kb": spatial_strata(tiles, predictions), "non_acgt": non_acgt_strata(tiles, predictions, global_counts)}


def raw_rm_path(root):
    table = root / "scripts/experiments/CROSS-SPECIES-L1-20260903/species_x0_r2.tsv"
    with table.open(newline="") as handle:
        row = next(row for row in csv.DictReader(handle, delimiter="\t") if row["species_code"] == "c_elegans")
    return Path(row["self_out"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnostic-root", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--upstream-root", type=Path, required=True)
    args = parser.parse_args()
    diagnostic_path = args.diagnostic_root / "diagnostic.json"
    diagnostic = json.loads(diagnostic_path.read_text())
    data_root = args.root / "outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202"
    records = {split: read_records((args.upstream_root if split == "SCREEN" else data_root) / split / "c_elegans.jsonl.gz") for split in SPLITS}
    desired = {str(row["chrom"]) for values in records.values() for row in values.values()}
    raw_path = raw_rm_path(args.root)
    raw_classes = read_raw_classes(raw_path, desired)
    output = {"role": "retrospective_diagnostic", "protocol": "CROSS-SPECIES-L1-UPSTREAM-D0-S", "seed": 42, "source": {"diagnostic_json": str(diagnostic_path), "raw_repeatmasker": str(raw_path), "desired_panel_chroms": sorted(desired), "natural_prevalence": True}, "arms": {}, "notes": {"class_overlap": "exact raw top-class bitmasks; multi-class is mixed", "location_overlap": "buckets are non-exclusive", "non_acgt": "frozen P>U>N; do not relabel", "tokenization": "each 4096-bp half resets 6-bp tokens and has single-base tails"}}
    for arm in ARMS:
        calibration_path = Path(diagnostic["arms"][arm]["calibration"])
        calibration = json.loads(calibration_path.read_text())
        output["arms"][arm] = {"calibration_path": str(calibration_path), "splits": {}}
        for split in SPLITS:
            cache = load_cache(args.diagnostic_root / f"{arm}_{split}_margins.npz")
            output["arms"][arm]["splits"][split] = panel_report(attach_records(cache, records[split]), calibration, raw_classes)
    ev.write_json(args.diagnostic_root / "error_strata.json", output)
    print(json.dumps({"output": str(args.diagnostic_root / "error_strata.json")}, sort_keys=True))


if __name__ == "__main__":
    main()
