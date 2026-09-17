#!/usr/bin/env python3
"""Fixed long sequence panels and positive-only, callable-base recovery.

Reference BED is in original assembly coordinates, prediction BED in panel
coordinates. Unannotated sequence remains unknown: no TN, precision or F1.
"""
from __future__ import annotations

import argparse
import gzip
import json
import shutil
import urllib.request
from pathlib import Path

import numpy as np


def open_text(path):
    path = Path(path)
    return gzip.open(path, "rt") if path.suffix == ".gz" else path.open()


def fasta(path):
    name, parts = None, []
    with open_text(path) as handle:
        for line in handle:
            if line.startswith(">"):
                if name is not None:
                    yield name, "".join(parts).upper()
                name, parts = line[1:].split()[0], []
            elif line.strip():
                if name is None:
                    raise ValueError("sequence before FASTA header")
                parts.append(line.strip())
    if name is not None:
        yield name, "".join(parts).upper()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def prepare(args):
    config = json.loads(args.config.read_text())
    spec = config["species"][args.species]
    for filename, url in spec.get("downloads", {}).items():
        destination = Path(spec["fasta"]).parent / filename
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            partial = destination.with_suffix(destination.suffix + ".partial")
            with urllib.request.urlopen(url, timeout=120) as response, partial.open("wb") as handle:
                shutil.copyfileobj(response, handle)
            partial.rename(destination)
    target = args.output
    target.mkdir(parents=True, exist_ok=True)
    if (target / "panel.fa").exists():
        raise FileExistsError(target / "panel.fa")
    lengths = {}
    for name, sequence in fasta(spec["fasta"]):
        if name in lengths:
            raise ValueError(f"duplicate FASTA id: {name}")
        lengths[name] = len(sequence)
    width = int(config["panel"]["length_bp"])
    count = int(config["panel"]["contigs"])
    eligible = [(name, length) for name, length in lengths.items() if length >= width]
    selected = sorted(eligible, key=lambda item: (-item[1], item[0]))[:count]
    if len(selected) != count:
        raise ValueError("too few sufficiently long contigs; do not silently change panel")
    regions = []
    for index, (name, length) in enumerate(selected):
        start = (length - width) // 2
        regions.append({"panel_id": f"p{index:02d}", "seqid": name,
                        "assembly_length_bp": length, "start": start, "end": start + width})
    sequences = {}
    wanted = {row["seqid"]: row for row in regions}
    for name, sequence in fasta(spec["fasta"]):
        if name in wanted:
            row = wanted[name]
            sequences[row["panel_id"]] = sequence[row["start"]:row["end"]]
    with (target / "panel.fa").open("x") as handle:
        for row in regions:
            sequence = sequences[row["panel_id"]]
            handle.write(f">{row['panel_id']}\n")
            for offset in range(0, len(sequence), 80):
                handle.write(sequence[offset:offset + 80] + "\n")
    result = {"status": "PREPARED", "species": args.species, "source": spec,
              "selection": config["panel"], "regions": regions,
              "total_bp": width * count, "labels_used_in_selection": False,
              "scores_used_in_selection": False}
    dump(target / "panel.json", result)
    return result


def bed_rows(path):
    with open_text(path) as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip() or line.startswith(("#", "track", "browser")):
                continue
            fields = line.split()
            name, start, end = fields[0], int(fields[1]), int(fields[2])
            if start < 0 or end <= start:
                raise ValueError(f"invalid BED interval at {path}:{number}")
            yield name, start, end


def counts(callable_mask, positive, predicted):
    labelled = positive & callable_mask
    prediction = predicted & callable_mask
    denom = int(labelled.sum())
    recovered = int((labelled & prediction).sum())
    predicted_bp = int(prediction.sum())
    callable_bp = int(callable_mask.sum())
    return {"callable_bp": callable_bp, "reference_positive_bp": denom,
            "recovered_positive_bp": recovered,
            "positive_recovery": recovered / denom if denom else None,
            "predicted_bp": predicted_bp,
            "predicted_fraction_of_callable": predicted_bp / callable_bp if callable_bp else None,
            "predicted_bp_without_this_reference_support": int((prediction & ~positive).sum()),
            "unknown_bp": int((callable_mask & ~positive).sum())}


def evaluate(args):
    panel = json.loads((args.panel / "panel.json").read_text())
    sequence = dict(fasta(args.panel / "panel.fa"))
    regions = {row["seqid"]: row for row in panel["regions"]}
    positive = {key: np.zeros(len(seq), dtype=bool) for key, seq in sequence.items()}
    predicted = {key: np.zeros(len(seq), dtype=bool) for key, seq in sequence.items()}
    matched_contigs, panel_rows = set(), 0
    for name, start, end in bed_rows(args.reference):
        if name not in regions:
            continue
        row = regions[name]
        matched_contigs.add(name)
        if end > row["assembly_length_bp"]:
            raise ValueError(f"reference exceeds assembly contig {name}")
        left, right = max(start, row["start"]), min(end, row["end"])
        if right > left:
            positive[row["panel_id"]][left - row["start"]:right - row["start"]] = True
            panel_rows += 1
    if not matched_contigs:
        raise ValueError("reference has no matching selected assembly contig ids")
    for name, start, end in bed_rows(args.prediction):
        if name not in predicted or end > len(predicted[name]):
            raise ValueError(f"prediction outside fixed panel: {name}:{start}-{end}")
        predicted[name][start:end] = True
    per_region = []
    callables, positives, predictions = [], [], []
    for row in panel["regions"]:
        key = row["panel_id"]
        callable_mask = np.isin(np.frombuffer(sequence[key].encode("ascii"), dtype="S1"),
                               [b"A", b"C", b"G", b"T"])
        per_region.append({**row, **counts(callable_mask, positive[key], predicted[key])})
        callables.append(callable_mask)
        positives.append(positive[key])
        predictions.append(predicted[key])
    result = {"status": "COMPLETED_POSITIVE_ONLY", "species": panel["species"],
              "reference": str(args.reference), "reference_layer": args.layer,
              "prediction": str(args.prediction), "coordinates": "0-based half-open",
              "reference_rows_overlapping_panel": panel_rows,
              "reference_contigs_matched": sorted(matched_contigs),
              "primary": counts(np.concatenate(callables), np.concatenate(positives),
                                np.concatenate(predictions)),
              "per_region": per_region,
              "claim_boundary": "Recovery of this documented positive layer on a fixed regional panel. "
              "Unannotated sequence is unknown, not negative; neither whole-genome biological "
              "precision/F1 nor biological insertion recovery is estimated."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    dump(args.output, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--config", type=Path, required=True)
    prep.add_argument("--species", required=True)
    prep.add_argument("--output", type=Path, required=True)
    score = sub.add_parser("evaluate")
    score.add_argument("--panel", type=Path, required=True)
    score.add_argument("--reference", type=Path, required=True)
    score.add_argument("--layer", required=True)
    score.add_argument("--prediction", type=Path, required=True)
    score.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args) if args.command == "prepare" else evaluate(args), indent=2))


if __name__ == "__main__":
    main()
