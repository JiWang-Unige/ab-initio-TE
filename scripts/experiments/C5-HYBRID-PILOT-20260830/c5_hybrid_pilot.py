#!/usr/bin/env python3
"""C5-H Human seed/copy pilot.

``a0`` calibrates one frozen P3 checkpoint on chr11 and exports the selected
chr17 seeds.  ``a1`` searches the full hs1 assembly with minimap2 and adds
qualified non-self chr17-prefix copy hits.  The two canonical outputs can be
passed to the existing Human masked evaluator through ``evaluate``.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[3]
WINDOW = 8192
CHROM = "chr17"
CANONICAL_FIELDS = ["seqid", "start", "end", "name", "score", "strand", "source", "attributes"]
SEED_FIELDS = [
    "seed_id", "seqid", "start", "end", "length", "mean_probability",
    "body_threshold", "min_length", "mean_probability_threshold",
]
EVIDENCE_FIELDS = [
    "seed_id", "source_seqid", "source_start", "source_end", "qname",
    "qlen", "qstart", "qend", "strand", "target_seqid", "target_length",
    "target_start", "target_end", "matches", "alignment_length",
    "query_coverage", "identity", "target_span", "self_hit",
    "copy_evidence", "emitted_to_chr17_prefix",
]


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _te_module():
    return _load_module(
        ROOT / "scripts/experiments/TE-STRUCTURE-PILOT-20260825-R1/te_unet_segmentation.py",
        "c5_te_unet_segmentation",
    )


def _strict_module():
    return _load_module(
        ROOT / "pipelines/PIPE-TEFM-FINAL-20260623/strict_segment_eval.py",
        "c5_strict_segment_eval",
    )


def _adapter_module():
    return _load_module(
        ROOT / "scripts/experiments/LEMMI-TE-BENCH-20260824-R1/adapter.py",
        "c5_lemmi_adapter",
    )


def _open_text(path: Path):
    return gzip.open(path, "rt", encoding="ascii") if str(path).endswith(".gz") else path.open("rt", encoding="ascii")


def fasta_records(path: Path) -> Iterator[tuple[str, str]]:
    name: str | None = None
    chunks: list[str] = []
    with _open_text(path) as handle:
        for line_no, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    yield name, "".join(chunks).upper()
                name = line[1:].split()[0]
                if not name:
                    raise ValueError(f"empty FASTA name at line {line_no}")
                chunks = []
            elif name is None:
                raise ValueError(f"FASTA sequence precedes header at line {line_no}")
            else:
                chunks.append(line)
        if name is not None:
            yield name, "".join(chunks).upper()


def fasta_sequence(path: Path, seqid: str) -> str:
    for name, sequence in fasta_records(path):
        if name == seqid:
            return sequence
    raise ValueError(f"FASTA has no record named {seqid}")


def jsonl_records(path: Path, limit: int | None = None) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if limit is not None and index >= limit:
                break
            yield json.loads(line)


def runs(mask: np.ndarray) -> list[tuple[int, int]]:
    values = [bool(value) for value in mask]
    output: list[tuple[int, int]] = []
    start: int | None = None
    for index, value in enumerate(values):
        if value and start is None:
            start = index
        elif not value and start is not None:
            output.append((start, index))
            start = None
    if start is not None:
        output.append((start, len(values)))
    return output


def load_p3_model(model_dir: Path):
    import torch
    from transformers import AutoTokenizer

    metadata = json.loads((model_dir / "training_meta.json").read_text(encoding="utf-8"))
    if metadata.get("schema") != "comparator_run_four_state_unet_v1":
        raise ValueError("C5 A0 requires the frozen four-state P3-R1 checkpoint")
    te = _te_module()
    local = True
    tokenizer = AutoTokenizer.from_pretrained(
        model_dir / "tokenizer", trust_remote_code=True, local_files_only=local,
    )
    model = te.model_class()(metadata["checkpoint"], int(metadata["width"]))
    model.load_state_dict(torch.load(model_dir / "model_state.pt", map_location="cpu"))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device).eval()
    return model, tokenizer, metadata, device, te


def infer_probability(model, tokenizer, sequence: str, device, te) -> np.ndarray:
    import torch

    encoded = tokenizer(
        sequence[:WINDOW], add_special_tokens=False, truncation=True,
        max_length=WINDOW, padding="max_length", return_tensors="pt",
    )
    inputs = {key: value.to(device) for key, value in encoded.items() if key in {"input_ids", "attention_mask"}}
    with torch.no_grad():
        probability = te.te_probability(model(**inputs).logits)[0].detach().cpu().numpy()
    return probability[:len(sequence)]


def assemble_track(
    data_jsonl: Path,
    model_dir: Path,
    max_windows: int,
    weight_mode: str,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    import numpy as np

    model, tokenizer, _metadata, device, te = load_p3_model(model_dir)
    strict = _strict_module()
    weights = strict.center_weights(WINDOW, weight_mode)
    sums: dict[str, np.ndarray] = {}
    weight_sums: dict[str, np.ndarray] = {}
    truths: dict[str, np.ndarray] = {}
    for index, row in enumerate(jsonl_records(data_jsonl, max_windows)):
        sequence = str(row["sequence"])
        start, end = int(row["start"]), int(row["end"])
        if end - start != len(sequence) or len(sequence) > WINDOW:
            raise ValueError(f"row {index} does not match frozen sequence coordinates")
        labels = np.asarray(row["labels"], dtype=np.int8)
        if labels.shape != (len(sequence),) or not np.isin(labels, [-100, 0, 1]).all():
            raise ValueError(f"row {index} labels are not a {-100, 0, 1} vector")
        probability = infer_probability(model, tokenizer, sequence, device, te)
        if row["chr"] not in sums or sums[row["chr"]].size < end:
            old_sum = sums.get(row["chr"])
            old_weight = weight_sums.get(row["chr"])
            old_truth = truths.get(row["chr"])
            sums[row["chr"]] = np.zeros(end, dtype=np.float32)
            weight_sums[row["chr"]] = np.zeros(end, dtype=np.float32)
            truths[row["chr"]] = np.full(end, -100, dtype=np.int8)
            if old_sum is not None:
                sums[row["chr"]][:old_sum.size] = old_sum
                weight_sums[row["chr"]][:old_weight.size] = old_weight
                truths[row["chr"]][:old_truth.size] = old_truth
        sums[row["chr"]][start:end] += probability * weights[:len(sequence)]
        weight_sums[row["chr"]][start:end] += weights[:len(sequence)]
        truths[row["chr"]][start:end] = labels
    probabilities: dict[str, np.ndarray] = {}
    for seqid, total in sums.items():
        valid = weight_sums[seqid] > 0
        if not valid.all():
            raise ValueError(f"{seqid} has uncovered coordinates in the frozen input")
        probabilities[seqid] = total / weight_sums[seqid]
    return probabilities, truths


def scored_segments(
    probability: np.ndarray,
    truth: np.ndarray,
    body_threshold: float,
    min_length: int,
    mean_probability: float,
) -> list[dict[str, Any]]:
    mask = [float(value) >= body_threshold for value in probability]
    mask = [value and truth[index] >= 0 for index, value in enumerate(mask)]
    segments: list[dict[str, Any]] = []
    for start, end in runs(mask):
        mean = sum(float(value) for value in probability[start:end]) / (end - start)
        if end - start >= min_length and mean >= mean_probability:
            segments.append({"start": start, "end": end, "length": end - start, "mean_probability": mean})
    return segments


def canonical_rows(rows: list[tuple[str, int, int]], source: str) -> list[dict[str, Any]]:
    return [
        {"seqid": seqid, "start": start, "end": end, "name": source,
         "score": ".", "strand": ".", "source": source, "attributes": "."}
        for seqid, start, end in rows
    ]


def write_canonical(path: Path, rows: list[tuple[str, int, int]], source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANONICAL_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(canonical_rows(rows, source))


def write_fasta(path: Path, sequence: str, segments: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="ascii") as handle:
        for segment in segments:
            start, end = segment["start"], segment["end"]
            seed_id = segment["seed_id"]
            handle.write(f">{seed_id}\n")
            piece = sequence[start:end]
            for offset in range(0, len(piece), 80):
                handle.write(piece[offset:offset + 80] + "\n")


def evaluate_rule(probability: np.ndarray, truth: np.ndarray, rule: dict[str, Any]) -> dict[str, Any]:
    import numpy as np

    strict = _strict_module()
    segments = scored_segments(
        probability, truth, float(rule["body_threshold"]),
        int(rule["min_length"]), float(rule["mean_probability"]),
    )
    mask = np.zeros(probability.size, dtype=bool)
    for segment in segments:
        mask[segment["start"]:segment["end"]] = True
    known = truth >= 0
    truth_mask = truth == 1
    truth_mask[~known] = False
    metrics = strict.strict_segment_metrics(truth_mask, mask, 0.8, 5)
    metrics.update({
        "min_length": int(rule["min_length"]),
        "mean_probability": float(rule["mean_probability"]),
        "body_threshold": float(rule["body_threshold"]),
        "seed_segments": len(segments),
        "raw_seed_segments": len(runs((probability >= float(rule["body_threshold"])) & known)),
        "eligible": len(segments) >= 100,
    })
    return metrics


def a0_tune(args: argparse.Namespace) -> dict[str, Any]:
    probabilities, truths = assemble_track(args.validation_jsonl, args.model_dir, args.max_validation_windows, args.weight_mode)
    if set(probabilities) != {args.validation_chrom}:
        raise ValueError(f"validation input must contain only {args.validation_chrom}")
    probability, truth = probabilities[args.validation_chrom], truths[args.validation_chrom]
    rows: list[dict[str, Any]] = []
    for min_length in (500, 1000):
        for mean_probability in (0.8, 0.9):
            rule = {"body_threshold": args.body_threshold, "min_length": min_length, "mean_probability": mean_probability}
            rows.append(evaluate_rule(probability, truth, rule))
    eligible = [row for row in rows if row["eligible"]]
    if not eligible:
        raise ValueError("no A0 rule has at least 100 selected seed segments")
    selected = max(eligible, key=lambda row: (
        row["segment_precision"], row["segment_recall"],
        row["mean_probability"], row["min_length"],
    ))
    result = {
        "schema": "c5_a0_selection_v1",
        "status": "PASS",
        "selection": {
            "body_threshold": selected["body_threshold"],
            "min_length": selected["min_length"],
            "mean_probability": selected["mean_probability"],
        },
        "grid": rows,
        "seed_requirement": 100,
        "validation": {
            "chrom": args.validation_chrom,
            "jsonl": str(args.validation_jsonl),
            "windows": args.max_validation_windows,
            "weight_mode": args.weight_mode,
            "truth_used_for_rule_selection": True,
        },
    }
    args.selection_json.parent.mkdir(parents=True, exist_ok=True)
    args.selection_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def a0_export(args: argparse.Namespace) -> dict[str, Any]:
    selection = json.loads(args.selection_json.read_text(encoding="utf-8"))
    if selection.get("schema") != "c5_a0_selection_v1" or selection.get("status") != "PASS":
        raise ValueError("invalid A0 selection manifest")
    rule = selection["selection"]
    probabilities, truths = assemble_track(args.test_jsonl, args.model_dir, args.max_test_windows, args.weight_mode)
    if set(probabilities) != {args.chrom}:
        raise ValueError(f"test input must contain only {args.chrom}")
    probability = probabilities[args.chrom][:args.prefix_end]
    truth = truths[args.chrom][:args.prefix_end]
    if probability.size != args.prefix_end:
        raise ValueError("test input does not cover the requested chr17 prefix")
    segments = scored_segments(
        probability, truth, float(rule["body_threshold"]),
        int(rule["min_length"]), float(rule["mean_probability"]),
    )
    for index, segment in enumerate(segments, 1):
        segment["seed_id"] = f"A0_chr17_{segment['start']:09d}_{segment['end']:09d}_{index:06d}"
        segment["seqid"] = args.chrom
    assembly_sequence = fasta_sequence(args.assembly, args.chrom)
    if len(assembly_sequence) < args.prefix_end:
        raise ValueError("assembly chr17 is shorter than the requested prefix")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    rich_tsv = args.out_dir / "a0.seeds.tsv"
    with rich_tsv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SEED_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for segment in segments:
            writer.writerow({
                "seed_id": segment["seed_id"], "seqid": args.chrom,
                "start": segment["start"], "end": segment["end"],
                "length": segment["length"], "mean_probability": segment["mean_probability"],
                "body_threshold": rule["body_threshold"], "min_length": rule["min_length"],
                "mean_probability_threshold": rule["mean_probability"],
            })
    write_canonical(args.out_dir / "a0.canonical.tsv", [(args.chrom, row["start"], row["end"]) for row in segments], "C5_A0")
    write_fasta(args.out_dir / "a0.seeds.fa", assembly_sequence[:args.prefix_end], segments)
    result = {
        "schema": "c5_a0_export_v1", "status": "PASS", "chrom": args.chrom,
        "prefix_end": args.prefix_end, "rule": rule, "seed_count": len(segments),
        "segments_tsv": str(rich_tsv), "canonical_tsv": str(args.out_dir / "a0.canonical.tsv"),
        "seeds_fasta": str(args.out_dir / "a0.seeds.fa"),
    }
    (args.out_dir / "a0.manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def read_seed_rows(path: Path) -> dict[str, dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != SEED_FIELDS:
            raise ValueError(f"seed fields must be {SEED_FIELDS}")
        rows = {}
        for row in reader:
            seed_id = row["seed_id"]
            if seed_id in rows:
                raise ValueError(f"duplicate seed id: {seed_id}")
            rows[seed_id] = {
                "seed_id": seed_id, "seqid": row["seqid"],
                "start": int(row["start"]), "end": int(row["end"]),
            }
    return rows


def reciprocal_overlap(left_start: int, left_end: int, right_start: int, right_end: int) -> float:
    overlap = max(0, min(left_end, right_end) - max(left_start, right_start))
    return min(overlap / (left_end - left_start), overlap / (right_end - right_start))


def union_intervals(intervals: list[tuple[str, int, int]]) -> list[tuple[str, int, int]]:
    grouped: dict[str, list[tuple[int, int]]] = {}
    for seqid, start, end in intervals:
        grouped.setdefault(seqid, []).append((start, end))
    output: list[tuple[str, int, int]] = []
    for seqid in sorted(grouped):
        current_start, current_end = sorted(grouped[seqid])[0]
        for start, end in sorted(grouped[seqid])[1:]:
            if start <= current_end:
                current_end = max(current_end, end)
            else:
                output.append((seqid, current_start, current_end))
                current_start, current_end = start, end
        output.append((seqid, current_start, current_end))
    return output


def a1_run(args: argparse.Namespace) -> dict[str, Any]:
    seeds = read_seed_rows(args.seeds_tsv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    paf = args.out_dir / "a1.minimap2.paf"
    with paf.open("w", encoding="utf-8") as handle:
        subprocess.run(
            [args.minimap2, "-x", "asm20", "-c", str(args.assembly), str(args.seeds_fasta)],
            stdout=handle, check=True,
        )
    evidence: list[dict[str, Any]] = []
    target_keys: dict[str, set[tuple[str, int, int, str]]] = {seed_id: set() for seed_id in seeds}
    emitted: list[tuple[str, int, int]] = [(row["seqid"], row["start"], row["end"]) for row in seeds.values()]
    with paf.open(encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            fields = raw.rstrip("\n").split("\t")
            if len(fields) < 12:
                raise ValueError(f"PAF row {line_no} has fewer than 12 columns")
            qname, qlen = fields[0], int(fields[1])
            qstart, qend = int(fields[2]), int(fields[3])
            strand, target_seqid, target_length = fields[4], fields[5], int(fields[6])
            target_start, target_end = int(fields[7]), int(fields[8])
            matches, alignment_length = int(fields[9]), int(fields[10])
            if qname not in seeds:
                raise ValueError(f"PAF row {line_no} references unknown seed {qname}")
            source = seeds[qname]
            query_coverage = (qend - qstart) / qlen
            identity = matches / alignment_length
            target_span = target_end - target_start
            self_hit = (
                target_seqid == source["seqid"]
                and reciprocal_overlap(source["start"], source["end"], target_start, target_end) >= 0.9
            )
            copy_evidence = query_coverage >= 0.8 and identity >= 0.8 and target_span >= 500 and not self_hit
            emitted_to_prefix = (
                copy_evidence and target_seqid == args.prefix_seqid
                and target_start < args.prefix_end and target_end > 0
            )
            evidence.append({
                "seed_id": qname, "source_seqid": source["seqid"],
                "source_start": source["start"], "source_end": source["end"],
                "qname": qname, "qlen": qlen, "qstart": qstart, "qend": qend,
                "strand": strand, "target_seqid": target_seqid, "target_length": target_length,
                "target_start": target_start, "target_end": target_end, "matches": matches,
                "alignment_length": alignment_length, "query_coverage": query_coverage,
                "identity": identity, "target_span": target_span, "self_hit": self_hit,
                "copy_evidence": copy_evidence, "emitted_to_chr17_prefix": emitted_to_prefix,
            })
            if copy_evidence:
                target_keys[qname].add((target_seqid, target_start, target_end, strand))
            if emitted_to_prefix:
                emitted.append((target_seqid, max(0, target_start), min(args.prefix_end, target_end)))
    with (args.out_dir / "a1.evidence.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EVIDENCE_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(evidence)
    copy_rows = []
    for seed_id in sorted(seeds):
        count = len(target_keys[seed_id])
        copy_rows.append({"seed_id": seed_id, "copies": count, "at_least_two": count >= 2})
    with (args.out_dir / "a1.copies_per_seed.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["seed_id", "copies", "at_least_two"], delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(copy_rows)
    union = union_intervals(emitted)
    write_canonical(args.out_dir / "a1.canonical.tsv", union, "C5_A1")
    result = {
        "schema": "c5_a1_copy_refinement_v1", "status": "PASS",
        "search": {"assembly": str(args.assembly), "preset": "asm20", "query_coverage": 0.8, "identity": 0.8, "target_span": 500},
        "source_self_hit": "same source seqid and reciprocal overlap >=0.9; excluded from copy evidence",
        "seeds": len(seeds), "paf_rows": len(evidence),
        "qualified_nonself_hits": sum(row["copy_evidence"] for row in evidence),
        "seeds_with_at_least_two_copies": sum(row["at_least_two"] for row in copy_rows),
        "fraction_seeds_with_at_least_two_copies": sum(row["at_least_two"] for row in copy_rows) / len(copy_rows) if copy_rows else 0.0,
        "emitted_chr17_prefix_hits": sum(row["emitted_to_chr17_prefix"] for row in evidence),
        "canonical_intervals": len(union),
        "canonical_tsv": str(args.out_dir / "a1.canonical.tsv"),
    }
    (args.out_dir / "a1.manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def masked_evaluate(args: argparse.Namespace) -> dict[str, Any]:
    adapter = _adapter_module()
    from importlib.util import spec_from_file_location, module_from_spec
    run_path = Path(__file__).parents[1] / "TE-STRUCTURE-PILOT-20260825-R1" / "run_hite_chr17_pilot.py"
    spec = spec_from_file_location("c5_hite_pilot", run_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load masked evaluator: {run_path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    lengths = json.loads(args.lengths.read_text(encoding="utf-8"))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    methods = {}
    for name, prediction in (("a0", args.a0), ("a1", args.a1)):
        methods[name] = module.masked_evaluate(
            adapter, args.truth, prediction, args.unknown, lengths, args.out_dir,
        )
    result = {
        "schema": "c5_masked_comparison_v1", "status": "PASS",
        "claim_scope": "RepeatMasker-style comparator agreement only",
        "same_truth_and_unknown_mask": True, "methods": methods,
    }
    args.result_json.parent.mkdir(parents=True, exist_ok=True)
    args.result_json.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    tune = sub.add_parser("a0-tune")
    tune.add_argument("--model-dir", type=Path, required=True)
    tune.add_argument("--validation-jsonl", type=Path, required=True)
    tune.add_argument("--validation-chrom", default="chr11")
    tune.add_argument("--max-validation-windows", type=int, default=800)
    tune.add_argument("--body-threshold", type=float, default=0.5)
    tune.add_argument("--weight-mode", choices=["flat", "triangular", "cosine"], default="triangular")
    tune.add_argument("--selection-json", type=Path, required=True)
    export = sub.add_parser("a0-export")
    export.add_argument("--model-dir", type=Path, required=True)
    export.add_argument("--test-jsonl", type=Path, required=True)
    export.add_argument("--max-test-windows", type=int, default=1200)
    export.add_argument("--selection-json", type=Path, required=True)
    export.add_argument("--assembly", type=Path, required=True)
    export.add_argument("--chrom", default=CHROM)
    export.add_argument("--prefix-end", type=int, required=True)
    export.add_argument("--weight-mode", choices=["flat", "triangular", "cosine"], default="triangular")
    export.add_argument("--out-dir", type=Path, required=True)
    a1 = sub.add_parser("a1")
    a1.add_argument("--seeds-tsv", type=Path, required=True)
    a1.add_argument("--seeds-fasta", type=Path, required=True)
    a1.add_argument("--assembly", type=Path, required=True)
    a1.add_argument("--minimap2", default="minimap2")
    a1.add_argument("--prefix-seqid", default=CHROM)
    a1.add_argument("--prefix-end", type=int, required=True)
    a1.add_argument("--out-dir", type=Path, required=True)
    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--truth", type=Path, required=True)
    evaluate.add_argument("--unknown", type=Path, required=True)
    evaluate.add_argument("--lengths", type=Path, required=True)
    evaluate.add_argument("--a0", type=Path, required=True)
    evaluate.add_argument("--a1", type=Path, required=True)
    evaluate.add_argument("--out-dir", type=Path, required=True)
    evaluate.add_argument("--result-json", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "a0-tune":
        result = a0_tune(args)
    elif args.command == "a0-export":
        result = a0_export(args)
    elif args.command == "a1":
        result = a1_run(args)
    else:
        result = masked_evaluate(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
