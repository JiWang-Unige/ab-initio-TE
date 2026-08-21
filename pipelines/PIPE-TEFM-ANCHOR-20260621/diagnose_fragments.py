#!/usr/bin/env python3
"""Build background/Unknown/high-score fragments and SF5 diagnostics."""
from __future__ import annotations

import argparse
import collections
import csv
import gzip
import json
import random
import sys
from pathlib import Path

import numpy as np

SUPP = Path("pipelines/PIPE-TEFM-SUPP-20260617").resolve()
LOCK = Path("pipelines/PIPE-TEFM-LOCK-20260619").resolve()
sys.path.insert(0, str(SUPP))
sys.path.insert(0, str(LOCK))

from prepare_ucsc_windows import opener, read_manifest  # noqa: E402
from prepare_superfamily5_data import map_sf5  # noqa: E402

SF5 = {0: "BG", 1: "SINE", 2: "LINE", 3: "LTR", 4: "DNA", 5: "Unknown"}


def read_fasta_chrom(path: str, chrom: str) -> str:
    parts = []
    found = False
    with opener(path) as handle:
        for raw in handle:
            line = raw.rstrip()
            if line.startswith(">"):
                if found:
                    break
                found = line[1:].split()[0] == chrom
            elif found:
                parts.append(line.upper())
    if not parts:
        raise RuntimeError(f"chromosome {chrom} not found in {path}")
    return "".join(parts)


def fetch(path: str, chrom: str, start: int, end: int, cache: dict[tuple[str, str], str]) -> str:
    key = (path, chrom)
    if key not in cache:
        cache[key] = read_fasta_chrom(path, chrom)
    seq = cache[key]
    start = max(0, min(start, len(seq)))
    end = max(start, min(end, len(seq)))
    return seq[start:end].upper()


def strict_species_rows(manifests: list[str], species: set[str] | None) -> list[dict]:
    rows = []
    seen = set()
    for manifest in manifests:
        for row in read_manifest(manifest):
            sp = row.get("species_code", "")
            if species and sp not in species:
                continue
            key = (manifest, sp, row.get("split", ""))
            if key in seen:
                continue
            seen.add(key)
            if not row.get("genome") or not Path(row["genome"]).exists():
                continue
            bed = row.get("comparator_plus_unknown") or row.get("comparator_strict")
            if bed and Path(bed).exists():
                rows.append(row)
    return rows


def add_labeled_te(records: list[dict], rows: list[dict], frag_len: int, max_per_label: int, max_unknown: int,
                   max_n_frac: float, seed: int) -> None:
    rng = random.Random(seed)
    cache: dict[tuple[str, str], str] = {}
    counts = collections.Counter()
    candidates = []
    for row in rows:
        bed = row.get("comparator_plus_unknown") or row.get("comparator_strict")
        if not bed or not Path(bed).exists():
            continue
        with opener(bed) as handle:
            for line in handle:
                if not line or line.startswith("#"):
                    continue
                p = line.rstrip().split("\t")
                if len(p) < 3:
                    continue
                try:
                    chrom, start, end = p[0], int(p[1]), int(p[2])
                except ValueError:
                    continue
                if end - start < frag_len:
                    continue
                name = p[3] if len(p) > 3 else ""
                rep_class = p[6] if len(p) > 6 else ""
                rep_family = p[7] if len(p) > 7 else ""
                label = map_sf5(rep_class, rep_family, name)
                if label <= 0:
                    continue
                quota = max_unknown if label == 5 else max_per_label
                if counts[SF5[label]] >= quota * 6:
                    continue
                # Dynamic locations: boundaries plus internal quantiles for long elements.
                starts = [start, max(start, end - frag_len)]
                length = end - start
                if length >= frag_len * 3:
                    starts.extend([int(start + q * length) - frag_len // 2 for q in (0.25, 0.5, 0.75)])
                for s in starts:
                    s = max(start, min(s, end - frag_len))
                    candidates.append((row, chrom, s, s + frag_len, label, name, rep_class, rep_family))
                    counts[SF5[label]] += 1
    rng.shuffle(candidates)
    kept = collections.Counter()
    for row, chrom, start, end, label, name, rep_class, rep_family in candidates:
        label_name = SF5[label]
        quota = max_unknown if label == 5 else max_per_label
        if kept[label_name] >= quota:
            continue
        try:
            seq = fetch(row["genome"], chrom, start, end, cache)
        except Exception:
            continue
        if len(seq) != frag_len or seq.count("N") / frag_len > max_n_frac:
            continue
        source = "unknown_annotation" if label == 5 else "known_main4"
        records.append({
            "sequence": seq,
            "label_name": label_name,
            "source": source,
            "species": row.get("species_code", ""),
            "chrom": chrom,
            "start": start,
            "end": end,
            "rep_name": name,
            "rep_class": rep_class,
            "rep_family": rep_family,
        })
        kept[label_name] += 1


def add_background_from_eval(records: list[dict], eval_roots: list[str], frag_len: int, max_bg: int,
                             max_n_frac: float, seed: int) -> None:
    rng = random.Random(seed)
    candidates = []
    for root in eval_roots:
        for path in Path(root).rglob("test/data.jsonl.gz"):
            species = path.parent.parent.name
            with gzip.open(path, "rt") as handle:
                for line in handle:
                    rec = json.loads(line)
                    labels = rec.get("labels", [])
                    seq = rec.get("sequence", "").upper()
                    if len(seq) < frag_len or not labels:
                        continue
                    if sum(labels) / max(1, len(labels)) > 0.01:
                        continue
                    if seq.count("N") / max(1, len(seq)) > max_n_frac:
                        continue
                    for _ in range(2):
                        start = rng.randint(0, len(seq) - frag_len)
                        candidates.append((species, rec, start))
    rng.shuffle(candidates)
    for species, rec, start in candidates[:max_bg]:
        seq = rec["sequence"][start:start + frag_len].upper()
        records.append({
            "sequence": seq,
            "label_name": "BG",
            "source": "background_strict_negative",
            "species": species,
            "chrom": rec.get("chr", rec.get("chrom", "")),
            "start": int(rec.get("start", 0)) + start,
            "end": int(rec.get("start", 0)) + start + frag_len,
            "rep_name": "background",
            "rep_class": "BG",
            "rep_family": "BG",
        })


def add_high_score_unannotated(records: list[dict], eval_roots: list[str], model_dir: str, frag_len: int,
                               threshold: float, max_records: int, max_windows: int, seed: int) -> None:
    import torch

    sys.path.insert(0, str(SUPP))
    from te_token_task import WindowDataset, load_trained_model  # noqa: E402

    rng = random.Random(seed)
    model, tokenizer, meta = load_trained_model(model_dir)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()
    candidates = []
    scanned = 0
    for root in eval_roots:
        for path in Path(root).rglob("test/data.jsonl.gz"):
            species = path.parent.parent.name
            ds = WindowDataset(str(path), tokenizer, int(meta.get("window", 4096)), "single_nt", max_windows)
            for rec in ds.records:
                if scanned >= max_windows:
                    break
                scanned += 1
                labels = rec.get("labels", [])
                seq = rec.get("sequence", "").upper()
                if len(seq) < frag_len or not labels:
                    continue
                item = ds.encode_labels(seq[: ds.window], labels[: ds.window])[0]
                inputs = {
                    "input_ids": torch.tensor([item["input_ids"]], dtype=torch.long, device=device),
                    "attention_mask": torch.tensor([item.get("attention_mask", [1] * len(item["input_ids"]))], dtype=torch.long, device=device),
                }
                with torch.no_grad():
                    probs = torch.softmax(model(**inputs).logits, dim=-1)[0, :, 1].detach().cpu().numpy()
                nt_probs = probs[1:1 + min(len(labels), len(seq), len(probs) - 2)]
                for _ in range(4):
                    if len(nt_probs) < frag_len:
                        continue
                    s = rng.randint(0, len(nt_probs) - frag_len)
                    span_labels = labels[s:s + frag_len]
                    if sum(span_labels) > 0:
                        continue
                    score = float(np.mean(nt_probs[s:s + frag_len]))
                    if score >= threshold:
                        candidates.append((score, species, rec, s))
            if scanned >= max_windows:
                break
    candidates.sort(reverse=True, key=lambda x: x[0])
    for score, species, rec, s in candidates[:max_records]:
        records.append({
            "sequence": rec["sequence"][s:s + frag_len].upper(),
            "label_name": "HighScoreUnannotated",
            "source": "high_score_strict_bg",
            "species": species,
            "chrom": rec.get("chr", rec.get("chrom", "")),
            "start": int(rec.get("start", 0)) + s,
            "end": int(rec.get("start", 0)) + s + frag_len,
            "rep_name": f"binary_score_{score:.4f}",
            "rep_class": "strict_BG_high_score",
            "rep_family": "strict_BG_high_score",
            "binary_mean_prob": score,
        })


def write_records(path: str, meta_path: str, records: list[dict], include_labels: set[str]) -> None:
    selected = [dict(r) for r in records if r["label_name"] in include_labels]
    label_to_id = {label: i + 1 for i, label in enumerate(sorted(include_labels))}
    for rec in selected:
        rec["label"] = label_to_id[rec["label_name"]]
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out, "wt") as handle:
        for rec in selected:
            handle.write(json.dumps(rec) + "\n")
    meta = {
        "out_jsonl": str(out),
        "n": len(selected),
        "label_to_id": label_to_id,
        "counts": dict(collections.Counter(r["label_name"] for r in selected)),
        "source_counts": dict(collections.Counter(r["source"] for r in selected)),
    }
    Path(meta_path).write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2))


def command_extract(args) -> None:
    species = set(args.species) if args.species else None
    rows = strict_species_rows(args.manifest, species)
    records: list[dict] = []
    add_labeled_te(records, rows, args.frag_len, args.max_per_label, args.max_unknown, args.max_n_frac, args.seed)
    add_background_from_eval(records, args.eval_root, args.frag_len, args.max_bg, args.max_n_frac, args.seed)
    if args.binary_model:
        add_high_score_unannotated(records, args.eval_root, args.binary_model, args.frag_len, args.highscore_threshold,
                                   args.max_highscore, args.highscore_max_windows, args.seed)
    main_labels = {"BG", "SINE", "LINE", "LTR", "DNA"}
    explore_labels = set(r["label_name"] for r in records)
    write_records(args.out_bg_main4, args.out_bg_main4_meta, records, main_labels)
    write_records(args.out_explore, args.out_explore_meta, records, explore_labels)


def command_predict_sf5(args) -> None:
    import torch
    from transformers import AutoConfig, AutoModelForTokenClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(args.sf5_model, trust_remote_code=True, local_files_only=True)
    config = AutoConfig.from_pretrained(args.sf5_model, trust_remote_code=True, local_files_only=True)
    model = AutoModelForTokenClassification.from_config(config, trust_remote_code=True)
    model_dir = Path(args.sf5_model)
    bin_path = model_dir / "pytorch_model.bin"
    safe_path = model_dir / "model.safetensors"
    if bin_path.exists():
        state = torch.load(bin_path, map_location="cpu")
    elif safe_path.exists():
        from safetensors.torch import load_file

        state = load_file(str(safe_path))
    else:
        raise FileNotFoundError(f"No pytorch_model.bin or model.safetensors found in {model_dir}")
    missing, unexpected = model.load_state_dict(state, strict=False)
    if missing or unexpected:
        print(f"[warn] sf5 checkpoint loaded with missing={len(missing)} unexpected={len(unexpected)}", flush=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()
    rows = []
    with gzip.open(args.fragments, "rt") as handle:
        for i, line in enumerate(handle):
            rec = json.loads(line)
            if args.sources and rec.get("source") not in set(args.sources):
                continue
            seq = rec["sequence"]
            enc = tokenizer(seq, truncation=True, max_length=len(seq) + 2, padding="max_length")
            inputs = {
                "input_ids": torch.tensor([enc["input_ids"]], dtype=torch.long, device=device),
                "attention_mask": torch.tensor([enc.get("attention_mask", [1] * len(enc["input_ids"]))], dtype=torch.long, device=device),
            }
            with torch.no_grad():
                pred = torch.argmax(model(**inputs).logits, dim=-1)[0].detach().cpu().numpy().tolist()
            body = pred[1:1 + len(seq)]
            counts = collections.Counter(SF5.get(int(x), str(x)) for x in body)
            total = max(1, sum(counts.values()))
            main4 = {k: counts.get(k, 0) / total for k in ["SINE", "LINE", "LTR", "DNA"]}
            best = max(main4, key=main4.get)
            rows.append({
                "idx": i,
                "source": rec.get("source", ""),
                "true_label_name": rec.get("label_name", ""),
                "species": rec.get("species", ""),
                "chrom": rec.get("chrom", ""),
                "start": rec.get("start", ""),
                "end": rec.get("end", ""),
                "sf5_best_main4": best,
                "sf5_best_main4_frac": main4[best],
                "sf5_unknown_frac": counts.get("Unknown", 0) / total,
                "sf5_bg_frac": counts.get("BG", 0) / total,
                "binary_mean_prob": rec.get("binary_mean_prob", ""),
            })
    out = Path(args.out_tsv)
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["idx", "source", "true_label_name", "species", "chrom", "start", "end",
              "sf5_best_main4", "sf5_best_main4_frac", "sf5_unknown_frac", "sf5_bg_frac", "binary_mean_prob"]
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    summary = {}
    for source in sorted(set(r["source"] for r in rows)):
        vals = [r for r in rows if r["source"] == source]
        summary[source] = {
            "n": len(vals),
            "best_main4_counts": dict(collections.Counter(r["sf5_best_main4"] for r in vals)),
            "mean_best_main4_frac": float(np.mean([float(r["sf5_best_main4_frac"]) for r in vals])) if vals else 0.0,
            "mean_unknown_frac": float(np.mean([float(r["sf5_unknown_frac"]) for r in vals])) if vals else 0.0,
            "mean_bg_frac": float(np.mean([float(r["sf5_bg_frac"]) for r in vals])) if vals else 0.0,
        }
    Path(args.out_summary).write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("extract")
    p.add_argument("--manifest", nargs="+", required=True)
    p.add_argument("--eval-root", nargs="+", required=True)
    p.add_argument("--species", nargs="*")
    p.add_argument("--binary-model")
    p.add_argument("--frag-len", type=int, default=512)
    p.add_argument("--max-per-label", type=int, default=220)
    p.add_argument("--max-bg", type=int, default=260)
    p.add_argument("--max-unknown", type=int, default=260)
    p.add_argument("--max-highscore", type=int, default=260)
    p.add_argument("--highscore-threshold", type=float, default=0.85)
    p.add_argument("--highscore-max-windows", type=int, default=700)
    p.add_argument("--max-n-frac", type=float, default=0.1)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out-bg-main4", required=True)
    p.add_argument("--out-bg-main4-meta", required=True)
    p.add_argument("--out-explore", required=True)
    p.add_argument("--out-explore-meta", required=True)
    p = sub.add_parser("predict-sf5")
    p.add_argument("--fragments", required=True)
    p.add_argument("--sf5-model", required=True)
    p.add_argument("--sources", nargs="*")
    p.add_argument("--out-tsv", required=True)
    p.add_argument("--out-summary", required=True)
    args = ap.parse_args()
    if args.cmd == "extract":
        command_extract(args)
    elif args.cmd == "predict-sf5":
        command_predict_sf5(args)


if __name__ == "__main__":
    main()
