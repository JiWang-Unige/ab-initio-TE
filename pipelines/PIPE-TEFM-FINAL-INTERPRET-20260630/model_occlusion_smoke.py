#!/usr/bin/env python3
"""Bounded model-level occlusion smoke for TE fragment interpretability."""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import sys
from pathlib import Path

import numpy as np
import torch

SUPP = Path("pipelines/PIPE-TEFM-SUPP-20260617").resolve()
sys.path.insert(0, str(SUPP))

from te_token_task import load_trained_model  # noqa: E402


SF5 = {0: "BG", 1: "SINE", 2: "LINE", 3: "LTR", 4: "DNA", 5: "Unknown"}
MAIN4 = ["SINE", "LINE", "LTR", "DNA"]


def read_fragment_sequences(path: Path) -> dict[int, dict]:
    out: dict[int, dict] = {}
    with gzip.open(path, "rt") as handle:
        for idx, line in enumerate(handle):
            rec = json.loads(line)
            rec["idx"] = idx
            out[idx] = rec
    return out


def select_indices(pairs_path: Path, max_unknown: int, include_controls: bool) -> list[tuple[str, int]]:
    rows = []
    with pairs_path.open() as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            rows.append(row)
    selected: list[tuple[str, int]] = []
    seen: set[int] = set()
    for row in rows:
        contrast = row["contrast"]
        if contrast == "high_score_strict_bg_vs_matched_bg":
            for key, role in [("case_idx", "case"), ("control_idx", "control")]:
                idx = int(row[key])
                if idx not in seen:
                    selected.append((f"{contrast}:{role}", idx))
                    seen.add(idx)
        elif contrast == "unknown_main4like_vs_matched_known_main4":
            case_count = sum(1 for label, _ in selected if label.startswith(contrast + ":case"))
            if case_count >= max_unknown:
                continue
            for key, role in [("case_idx", "case"), ("control_idx", "control")]:
                if role == "control" and not include_controls:
                    continue
                idx = int(row[key])
                if idx not in seen:
                    selected.append((f"{contrast}:{role}", idx))
                    seen.add(idx)
    return selected


def occlude(seq: str, start: int, width: int, base: str) -> str:
    end = min(len(seq), start + width)
    return seq[:start] + (base * (end - start)) + seq[end:]


def binary_scores(model, tokenizer, meta: dict, seqs: list[str], device: torch.device) -> list[float]:
    # This smoke is fragment-level attribution. Use fragment length rather than
    # the 4096 bp training window to keep occlusion bounded and interpretable.
    max_len = max(len(seq) for seq in seqs) + 2
    enc = tokenizer(seqs, truncation=True, max_length=max_len, padding="max_length")
    inputs = {
        "input_ids": torch.tensor(enc["input_ids"], dtype=torch.long, device=device),
        "attention_mask": torch.tensor(
            enc.get("attention_mask", [[1] * len(x) for x in enc["input_ids"]]),
            dtype=torch.long,
            device=device,
        ),
    }
    with torch.no_grad():
        probs = torch.softmax(model(**inputs).logits, dim=-1)[..., 1].detach().float().cpu().numpy()
    scores = []
    for seq, row in zip(seqs, probs):
        body = row[1 : 1 + min(len(seq), max(0, len(row) - 2))]
        scores.append(float(np.mean(body)) if body.size else float("nan"))
    return scores


def load_sf5(sf5_model_dir: Path, device: torch.device):
    from transformers import AutoConfig, AutoModelForTokenClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(str(sf5_model_dir), trust_remote_code=True, local_files_only=True)
    config = AutoConfig.from_pretrained(str(sf5_model_dir), trust_remote_code=True, local_files_only=True)
    model = AutoModelForTokenClassification.from_config(config, trust_remote_code=True)
    bin_path = sf5_model_dir / "pytorch_model.bin"
    safe_path = sf5_model_dir / "model.safetensors"
    if bin_path.exists():
        state = torch.load(bin_path, map_location="cpu")
    elif safe_path.exists():
        from safetensors.torch import load_file

        state = load_file(str(safe_path))
    else:
        raise FileNotFoundError(f"No SF5 weights found under {sf5_model_dir}")
    model.load_state_dict(state, strict=False)
    model.to(device)
    model.eval()
    return model, tokenizer


def sf5_scores_batch(model, tokenizer, seqs: list[str], device: torch.device) -> list[dict[str, float]]:
    max_len = max(len(seq) for seq in seqs) + 2
    enc = tokenizer(seqs, truncation=True, max_length=max_len, padding="max_length")
    inputs = {
        "input_ids": torch.tensor(enc["input_ids"], dtype=torch.long, device=device),
        "attention_mask": torch.tensor(
            enc.get("attention_mask", [[1] * len(x) for x in enc["input_ids"]]),
            dtype=torch.long,
            device=device,
        ),
    }
    with torch.no_grad():
        pred = torch.argmax(model(**inputs).logits, dim=-1).detach().cpu().numpy().tolist()
    out = []
    for seq, row in zip(seqs, pred):
        body = row[1 : 1 + len(seq)]
        counts = {name: 0 for name in SF5.values()}
        for val in body:
            counts[SF5.get(int(val), str(val))] = counts.get(SF5.get(int(val), str(val)), 0) + 1
        total = max(1, sum(counts.values()))
        main4 = {name: counts.get(name, 0) / total for name in MAIN4}
        best = max(main4, key=main4.get)
        out.append(
            {
                "sf5_best_main4": best,
                "sf5_best_main4_frac": float(main4[best]),
                "sf5_bg_frac": float(counts.get("BG", 0) / total),
                "sf5_unknown_frac": float(counts.get("Unknown", 0) / total),
            }
        )
    return out


def summarize(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str, str], list[dict]] = {}
    for row in rows:
        if row["chunk_start"] == "original":
            continue
        key = (row["contrast_role"], row["source"], row["model"])
        grouped.setdefault(key, []).append(row)
    out = []
    for (contrast_role, source, model), vals in sorted(grouped.items()):
        deltas = [float(v["delta_score"]) for v in vals if math.isfinite(float(v["delta_score"]))]
        if not deltas:
            continue
        out.append(
            {
                "contrast_role": contrast_role,
                "source": source,
                "model": model,
                "n_occluded_chunks": len(deltas),
                "mean_delta_score": float(np.mean(deltas)),
                "max_delta_score": float(np.max(deltas)),
                "min_delta_score": float(np.min(deltas)),
                "mean_abs_delta_score": float(np.mean(np.abs(deltas))),
            }
        )
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fragments", required=True)
    parser.add_argument("--pairs", required=True)
    parser.add_argument("--binary-model-dir", required=True)
    parser.add_argument("--sf5-model-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--chunk", type=int, default=64)
    parser.add_argument("--max-unknown", type=int, default=8)
    parser.add_argument("--occlusion-base", default="N")
    parser.add_argument("--include-unknown-controls", action="store_true")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    fragments = read_fragment_sequences(Path(args.fragments))
    selected = select_indices(Path(args.pairs), args.max_unknown, args.include_unknown_controls)

    binary_model, binary_tokenizer, binary_meta = load_trained_model(args.binary_model_dir)
    binary_model.to(device)
    binary_model.eval()
    sf5_model, sf5_tokenizer = load_sf5(Path(args.sf5_model_dir), device)

    rows = []
    for contrast_role, idx in selected:
        rec = fragments[idx]
        seq = rec["sequence"].upper()
        print(f"[occlusion] idx={idx} role={contrast_role} source={rec.get('source', '')}", flush=True)
        chunk_starts = list(range(0, len(seq), args.chunk))
        variant_seqs = [seq] + [occlude(seq, s, args.chunk, args.occlusion_base) for s in chunk_starts]
        binary_variant_scores = binary_scores(binary_model, binary_tokenizer, binary_meta, variant_seqs, device)
        sf5_variant_scores = sf5_scores_batch(sf5_model, sf5_tokenizer, variant_seqs, device)
        binary_orig = binary_variant_scores[0]
        sf5_orig = sf5_variant_scores[0]
        original_scores = {
            "binary_te_mean": binary_orig,
            "sf5_best_main4_frac": sf5_orig["sf5_best_main4_frac"],
            "sf5_bg_frac": sf5_orig["sf5_bg_frac"],
            "sf5_unknown_frac": sf5_orig["sf5_unknown_frac"],
        }
        for model_name, score_name, score in [
            ("binary", "binary_te_mean", binary_orig),
            ("sf5", "sf5_best_main4_frac", sf5_orig["sf5_best_main4_frac"]),
        ]:
            rows.append(
                {
                    "idx": idx,
                    "contrast_role": contrast_role,
                    "source": rec.get("source", ""),
                    "species": rec.get("species", ""),
                    "chrom": rec.get("chrom", ""),
                    "start": rec.get("start", ""),
                    "end": rec.get("end", ""),
                    "label_name": rec.get("label_name", ""),
                    "model": model_name,
                    "score_name": score_name,
                    "chunk_start": "original",
                    "chunk_end": "original",
                    "original_score": score,
                    "occluded_score": score,
                    "delta_score": 0.0,
                    "sf5_best_main4": sf5_orig["sf5_best_main4"],
                }
            )
        for variant_i, chunk_start in enumerate(chunk_starts, start=1):
            chunk_end = min(len(seq), chunk_start + args.chunk)
            binary_mut = binary_variant_scores[variant_i]
            sf5_mut = sf5_variant_scores[variant_i]
            for model_name, score_name, orig, mut in [
                ("binary", "binary_te_mean", original_scores["binary_te_mean"], binary_mut),
                ("sf5", "sf5_best_main4_frac", original_scores["sf5_best_main4_frac"], sf5_mut["sf5_best_main4_frac"]),
            ]:
                rows.append(
                    {
                        "idx": idx,
                        "contrast_role": contrast_role,
                        "source": rec.get("source", ""),
                        "species": rec.get("species", ""),
                        "chrom": rec.get("chrom", ""),
                        "start": rec.get("start", ""),
                        "end": rec.get("end", ""),
                        "label_name": rec.get("label_name", ""),
                        "model": model_name,
                        "score_name": score_name,
                        "chunk_start": chunk_start,
                        "chunk_end": chunk_end,
                        "original_score": orig,
                        "occluded_score": mut,
                        "delta_score": orig - mut,
                        "sf5_best_main4": sf5_orig["sf5_best_main4"],
                    }
                )

    detail_path = out_dir / "occlusion_detail.tsv"
    with detail_path.open("w", newline="") as handle:
        fieldnames = list(rows[0].keys()) if rows else []
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    summary_rows = summarize(rows)
    summary_path = out_dir / "occlusion_summary.tsv"
    with summary_path.open("w", newline="") as handle:
        fieldnames = list(summary_rows[0].keys()) if summary_rows else [
            "contrast_role",
            "source",
            "model",
            "n_occluded_chunks",
            "mean_delta_score",
            "max_delta_score",
            "min_delta_score",
            "mean_abs_delta_score",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(summary_rows)

    status = {
        "ok": True,
        "device": str(device),
        "n_fragments": len(selected),
        "n_detail_rows": len(rows),
        "chunk": args.chunk,
        "binary_context": "fragment_length_plus_special_tokens",
        "sf5_context": "fragment_length_plus_special_tokens",
        "outputs": {
            "detail": str(detail_path),
            "summary": str(summary_path),
        },
    }
    (out_dir / "occlusion_status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
