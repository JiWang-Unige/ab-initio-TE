#!/usr/bin/env python3
"""Measure whether GENERanno and NTv2 make complementary chr17 TE gaps."""
from __future__ import annotations

import argparse
import csv
import gc
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[3]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


strict = load_module(
    ROOT / "pipelines/PIPE-TEFM-FINAL-20260623/strict_segment_eval.py",
    "tefm_ensemble_strict_segment",
)


def infer_track(model_dir: Path, data_jsonl: Path, window: int, max_windows: int):
    model, tokenizer, meta = strict.load_trained_model(str(model_dir))
    device = torch.device("cuda")
    model.to(device)
    model.eval()
    label_mode = str(meta.get("token_label_mode", ""))
    weights = strict.center_weights(window, "triangular")
    probability_sum: dict[str, np.ndarray] = {}
    weight_sum: dict[str, np.ndarray] = {}
    truth: dict[str, np.ndarray] = {}
    started = time.time()
    n_windows = 0
    for record in strict.read_jsonl(data_jsonl, max_windows):
        n_windows += 1
        chrom = record["chr"]
        start, end = int(record["start"]), int(record["end"])
        if chrom not in probability_sum or probability_sum[chrom].size < end:
            old_probability = probability_sum.get(chrom)
            old_weight = weight_sum.get(chrom)
            old_truth = truth.get(chrom)
            probability_sum[chrom] = np.zeros(end, dtype=np.float32)
            weight_sum[chrom] = np.zeros(end, dtype=np.float32)
            truth[chrom] = np.zeros(end, dtype=np.int8)
            if old_probability is not None:
                probability_sum[chrom][: old_probability.size] = old_probability
                weight_sum[chrom][: old_weight.size] = old_weight
                truth[chrom][: old_truth.size] = old_truth
        probability = strict.infer_probs_for_label_mode(
            model, tokenizer, record["sequence"][:window], window, device, label_mode,
        )
        probability_sum[chrom][start:end] += probability * weights
        weight_sum[chrom][start:end] += weights
        truth[chrom][start:end] = np.asarray(record["labels"][:window], dtype=np.int8)
        if n_windows % 100 == 0:
            print(f"{model_dir.name}: {n_windows} windows", flush=True)
    tracks = {}
    for chrom in probability_sum:
        valid = weight_sum[chrom] > 0
        probability = probability_sum[chrom][valid] / weight_sum[chrom][valid]
        tracks[chrom] = (probability, truth[chrom][valid])
    elapsed = time.time() - started
    model.to("cpu")
    del model, tokenizer
    gc.collect()
    torch.cuda.empty_cache()
    return tracks, {"label_mode": label_mode, "n_windows": n_windows, "seconds": elapsed}


def bridge_complete_gaps(anchor: np.ndarray, donor: np.ndarray, max_gap: int = 512) -> np.ndarray:
    result = anchor.copy()
    for start, end in strict.runs_from_bool(~anchor):
        if start == 0 or end == anchor.size or end - start > max_gap:
            continue
        if donor[start:end].all():
            result[start:end] = True
    return result


def internal_gap_mask(truth: np.ndarray, prediction: np.ndarray) -> np.ndarray:
    result = np.zeros(truth.size, dtype=bool)
    for start, end in strict.runs_from_bool(truth):
        positive = np.flatnonzero(prediction[start:end])
        if positive.size > 1:
            left, right = start + int(positive[0]), start + int(positive[-1]) + 1
            result[left:right] = ~prediction[left:right]
    return result


def multi_truth_fusions(truth: np.ndarray, prediction: np.ndarray) -> int:
    truth_runs = strict.runs_from_bool(truth)
    count = 0
    truth_index = 0
    for pred_start, pred_end in strict.runs_from_bool(prediction):
        while truth_index < len(truth_runs) and truth_runs[truth_index][1] <= pred_start:
            truth_index += 1
        overlaps = 0
        index = truth_index
        while index < len(truth_runs) and truth_runs[index][0] < pred_end:
            overlaps += int(min(pred_end, truth_runs[index][1]) > max(pred_start, truth_runs[index][0]))
            index += 1
        count += int(overlaps > 1)
    return count


def mask_metrics(name: str, truth: np.ndarray, known: np.ndarray, mask: np.ndarray) -> dict[str, object]:
    mask = mask.copy()
    mask[~known] = False
    row: dict[str, object] = {"strategy": name}
    row.update(strict.binary_metrics(truth[known], mask[known].astype(np.float32), 0.5))
    row.update(strict.strict_segment_metrics(truth, mask, 0.8, 5))
    row.update(strict.fragmentation_truth_diagnostics(truth, mask))
    row["short_prediction_rate"] = row["short_pred_segments"] / row["pred_segments"] if row["pred_segments"] else 0.0
    gaps = internal_gap_mask(truth, mask)
    row["internal_gap_runs"] = len(strict.runs_from_bool(gaps))
    row["internal_gap_bp"] = int(gaps.sum())
    row["multi_truth_fusion_runs"] = multi_truth_fusions(truth, mask)
    return row


def gap_rescue(source_gaps: np.ndarray, donor: np.ndarray) -> dict[str, object]:
    runs = strict.runs_from_bool(source_gaps)
    return {
        "source_gap_runs": len(runs),
        "source_gap_bp": int(source_gaps.sum()),
        "fully_covered_runs": sum(bool(donor[start:end].all()) for start, end in runs),
        "partly_covered_runs": sum(bool(donor[start:end].any()) for start, end in runs),
        "covered_bp": int((source_gaps & donor).sum()),
    }


def complementarity(truth: np.ndarray, known: np.ndarray, generanno: np.ndarray, nt: np.ndarray) -> dict[str, object]:
    true_known = truth & known
    gen_fn = true_known & ~generanno
    nt_fn = true_known & ~nt
    shared_fn = gen_fn & nt_fn
    fn_union = gen_fn | nt_fn
    gen_gap = internal_gap_mask(truth, generanno)
    nt_gap = internal_gap_mask(truth, nt)
    shared_gap = gen_gap & nt_gap
    union_gap = gen_gap | nt_gap
    return {
        "false_negative_bp": {
            "generanno": int(gen_fn.sum()),
            "ntv2_250m": int(nt_fn.sum()),
            "shared": int(shared_fn.sum()),
            "jaccard": float(shared_fn.sum() / fn_union.sum()) if fn_union.any() else 0.0,
            "generanno_fn_rescued_by_nt_bp": int((gen_fn & nt).sum()),
            "nt_fn_rescued_by_generanno_bp": int((nt_fn & generanno).sum()),
        },
        "internal_gap_bp": {
            "generanno": int(gen_gap.sum()),
            "ntv2_250m": int(nt_gap.sum()),
            "shared": int(shared_gap.sum()),
            "jaccard": float(shared_gap.sum() / union_gap.sum()) if union_gap.any() else 0.0,
        },
        "generanno_gaps_read_by_nt": gap_rescue(gen_gap, nt),
        "nt_gaps_read_by_generanno": gap_rescue(nt_gap, generanno),
    }


def write_tsv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run(args: argparse.Namespace) -> None:
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=False)
    gen_tracks, gen_runtime = infer_track(args.generanno_model, args.data_jsonl, args.window, args.max_windows)
    nt_tracks, nt_runtime = infer_track(args.nt_model, args.data_jsonl, args.window, args.max_windows)
    rows = []
    diagnostics = {}
    for chrom in sorted(gen_tracks):
        gen_probability, labels = gen_tracks[chrom]
        nt_probability, _ = nt_tracks[chrom]
        known = labels >= 0
        truth = labels == 1
        generanno = (gen_probability >= 0.5) & known
        nt = (nt_probability >= 0.5) & known
        strategies = {
            "GENERanno": generanno,
            "NTv2_250m": nt,
            "OR_union": generanno | nt,
            "AND_intersection": generanno & nt,
            "mean_probability": ((gen_probability + nt_probability) / 2 >= 0.5) & known,
            "GENERanno_plus_NT_complete_gap_bridge_le512": bridge_complete_gaps(generanno, nt, 512),
        }
        rows.extend(mask_metrics(name, truth, known, mask) | {"chrom": chrom} for name, mask in strategies.items())
        diagnostics[chrom] = complementarity(truth, known, generanno, nt)
    write_tsv(output_dir / "ensemble_metrics.tsv", rows)
    summary = {
        "status": "PASS",
        "scope": "retrospective engineering diagnostic on previously consumed Human chr17 H0 test windows",
        "threshold": 0.5,
        "window": args.window,
        "max_windows": args.max_windows,
        "generanno_runtime": gen_runtime,
        "ntv2_250m_runtime": nt_runtime,
        "metrics": rows,
        "complementarity": diagnostics,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (output_dir / "STATUS").write_text("PASS\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generanno-model", required=True, type=Path)
    parser.add_argument("--nt-model", required=True, type=Path)
    parser.add_argument("--data-jsonl", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--window", type=int, default=4096)
    parser.add_argument("--max-windows", type=int, default=1200)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
