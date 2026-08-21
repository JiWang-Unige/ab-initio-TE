#!/usr/bin/env python3
"""Strict TE fragment embedding diagnostics: dynamic sampling, family labels, and source panels."""
from __future__ import annotations

import argparse
import collections
import csv
import gzip
import json
import random
import re
import sys
from pathlib import Path

import numpy as np

SEG = Path("pipelines/PIPE-TEFM-SEG-SF-20260618").resolve()
sys.path.insert(0, str(SEG))
from embedding_cluster import (  # noqa: E402
    evaluate_embeddings,
    load_records,
    model_embeddings,
    plot_embeddings,
    seq_features,
    supervised_contrastive_project,
)
from prepare_superfamily_windows import ID2LABEL, map_class, opener, read_manifest  # noqa: E402


def clean_label(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.:/-]+", "_", text.strip())
    return text.strip("_") or "Unknown"


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


def fasta_index_path(path: str) -> Path | None:
    p = Path(path)
    for cand in [Path(str(p) + ".fai"), Path(str(p).removesuffix(".gz") + ".fai")]:
        if cand.exists():
            return cand
    return None


def fetch_interval(path: str, chrom: str, start: int, end: int, cache: dict[tuple[str, str], str]) -> str:
    # gzipped FASTA random access is not assumed in this project; cache one chromosome.
    key = (path, chrom)
    if key not in cache:
        cache[key] = read_fasta_chrom(path, chrom)
    seq = cache[key]
    start = max(0, min(start, len(seq)))
    end = max(start, min(end, len(seq)))
    return seq[start:end].upper()


def load_intervals(bed: str, label_level: str) -> list[dict]:
    out = []
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
            name = p[3] if len(p) > 3 else ""
            rep_class = p[6] if len(p) > 6 else ""
            rep_family = p[7] if len(p) > 7 else ""
            sf = map_class(rep_class, rep_family, name)
            if sf <= 0:
                continue
            if label_level == "superfamily":
                label_name = ID2LABEL.get(sf, "Unknown")
            else:
                fam = rep_family if rep_family and rep_family not in {".", "?"} else name
                label_name = clean_label(fam)
            out.append({
                "chrom": chrom,
                "start": start,
                "end": end,
                "superfamily_id": sf,
                "superfamily": ID2LABEL.get(sf, "Unknown"),
                "label_name": label_name,
                "rep_name": name,
                "rep_class": rep_class,
                "rep_family": rep_family,
            })
    return out


def choose_dynamic_starts(start: int, end: int, frag_len: int, source: str, rng: random.Random) -> list[int]:
    length = end - start
    if length < frag_len:
        return []
    if source == "genomic_boundary":
        return [start, max(start, end - frag_len)]
    if length <= frag_len * 2:
        return [start + (length - frag_len) // 2]
    # Internal long-TE sampling deliberately avoids using only the center.
    qs = [0.2, 0.4, 0.6, 0.8]
    starts = [int(start + q * length) - frag_len // 2 for q in qs]
    starts.append(rng.randint(start, end - frag_len))
    return [max(start, min(s, end - frag_len)) for s in starts]


def command_extract_genomic(args) -> None:
    rng = random.Random(args.seed)
    rows = [r for r in read_manifest(args.manifest) if r.get("split") == args.split]
    candidates = []
    label_counts = collections.Counter()
    species_filter = set(args.species) if args.species else None
    # First pass: determine top families from intervals only. Fetching every
    # candidate sequence is unnecessarily slow on gzipped genome FASTA files.
    for row in rows:
        if species_filter and row.get("species_code") not in species_filter:
            continue
        genome = row.get("genome", "")
        bed = row.get("comparator_strict", "")
        if not genome or not bed or not Path(genome).exists() or not Path(bed).exists():
            continue
        for item in load_intervals(bed, args.label_level):
            starts = choose_dynamic_starts(item["start"], item["end"], args.length, args.source, rng)
            if not starts:
                continue
            label_counts[item["label_name"]] += len(starts)
            candidates.append((row, genome, item, starts))
    keep = [label for label, n in label_counts.most_common(args.top_labels) if n >= args.min_per_label]
    keep_set = set(keep)
    grouped = collections.defaultdict(list)
    for row, genome, item, starts in candidates:
        if item["label_name"] in keep_set:
            grouped[item["label_name"]].append((row, genome, item, starts))
    label_to_id = {label: i + 1 for i, label in enumerate(sorted(grouped))}
    cache: dict[tuple[str, str], str] = {}
    records = []
    for label, vals in grouped.items():
        rng.shuffle(vals)
        for row, genome, item, starts in vals:
            starts = list(starts)
            rng.shuffle(starts)
            for frag_start in starts:
                seq = fetch_interval(genome, item["chrom"], frag_start, frag_start + args.length, cache)
                if len(seq) != args.length or seq.count("N") / max(1, len(seq)) > args.max_n_frac:
                    continue
                rec = {
                    "sequence": seq,
                    "source": args.source,
                    "label_name": item["label_name"],
                    "superfamily": item["superfamily"],
                    "species": row["species_code"],
                    "chrom": item["chrom"],
                    "start": frag_start,
                    "end": frag_start + args.length,
                    "rep_name": item["rep_name"],
                    "rep_class": item["rep_class"],
                    "rep_family": item["rep_family"],
                    "label": label_to_id[label],
                }
                records.append(rec)
                if sum(1 for r in records if r["label_name"] == label) >= args.max_per_label:
                    break
            if sum(1 for r in records if r["label_name"] == label) >= args.max_per_label:
                break
    rng.shuffle(records)
    write_records(args.out_jsonl, args.out_meta, records, {
        "mode": "genomic_extract",
        "source": args.source,
        "label_level": args.label_level,
        "length": args.length,
        "label_to_id": label_to_id,
        "raw_label_counts": dict(label_counts.most_common(50)),
        "sampling": "top_family_interval_first",
    })


def parse_consensus_fasta(path: str, length: int, label_level: str, max_n_frac: float) -> list[dict]:
    records = []
    name = None
    seq_parts = []

    def flush():
        if name is None:
            return
        seq = "".join(seq_parts).upper()
        if len(seq) < length:
            return
        header = name
        rep = header.split()[0]
        if "#" in rep:
            rep_name, clsfam = rep.split("#", 1)
        else:
            rep_name, clsfam = rep, header
        fields = re.split(r"[/|;:,\s]+", clsfam)
        sf = fields[0] if fields else "Unknown"
        fam = fields[1] if len(fields) > 1 else rep_name
        label_name = clean_label(fam if label_level == "family" else sf)
        for start in range(0, max(1, len(seq) - length + 1), length):
            piece = seq[start:start + length]
            if len(piece) == length and piece.count("N") / length <= max_n_frac:
                records.append({
                    "sequence": piece,
                    "source": "dfam_consensus",
                    "label_name": label_name,
                    "superfamily": sf,
                    "species": "dfam_consensus",
                    "chrom": rep_name,
                    "start": start,
                    "end": start + length,
                    "rep_name": rep_name,
                    "rep_class": sf,
                    "rep_family": fam,
                })

    with opener(path) as handle:
        for raw in handle:
            line = raw.rstrip()
            if line.startswith(">"):
                flush()
                name = line[1:]
                seq_parts = []
            else:
                seq_parts.append(line)
        flush()
    return records


def command_extract_consensus(args) -> None:
    if not args.consensus_fasta or not Path(args.consensus_fasta).exists():
        write_records(args.out_jsonl, args.out_meta, [], {
            "mode": "consensus_extract",
            "source": "dfam_consensus",
            "skipped": True,
            "reason": "consensus FASTA not provided or not found",
            "consensus_fasta": args.consensus_fasta or "",
        })
        return
    rng = random.Random(args.seed)
    raw_records = parse_consensus_fasta(args.consensus_fasta, args.length, args.label_level, args.max_n_frac)
    counts = collections.Counter(r["label_name"] for r in raw_records)
    keep = [label for label, n in counts.most_common(args.top_labels) if n >= args.min_per_label]
    by_label = collections.defaultdict(list)
    for rec in raw_records:
        if rec["label_name"] in keep:
            by_label[rec["label_name"]].append(rec)
    label_to_id = {label: i + 1 for i, label in enumerate(sorted(by_label))}
    records = []
    for label, vals in by_label.items():
        rng.shuffle(vals)
        for rec in vals[:args.max_per_label]:
            rec = dict(rec)
            rec["label"] = label_to_id[label]
            records.append(rec)
    rng.shuffle(records)
    write_records(args.out_jsonl, args.out_meta, records, {
        "mode": "consensus_extract",
        "source": "dfam_consensus",
        "label_level": args.label_level,
        "length": args.length,
        "label_to_id": label_to_id,
        "raw_label_counts": dict(counts.most_common(50)),
    })


def write_records(out_jsonl: str, out_meta: str, records: list[dict], meta: dict) -> None:
    out = Path(out_jsonl)
    out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out, "wt") as handle:
        for rec in records:
            handle.write(json.dumps(rec) + "\n")
    meta = dict(meta)
    meta["out_jsonl"] = str(out)
    meta["n"] = len(records)
    meta["counts"] = dict(collections.Counter(r.get("label_name", "") for r in records))
    Path(out_meta).parent.mkdir(parents=True, exist_ok=True)
    Path(out_meta).write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2))


def command_cluster(args) -> None:
    import torch

    random.seed(args.seed)
    np.random.seed(args.seed)
    records = load_records(args.fragments, args.max_records)
    if not records:
        out = Path(args.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "metrics.json").write_text(json.dumps({"status": "skipped", "reason": "empty fragments", "fragments": args.fragments}, indent=2) + "\n")
        print(json.dumps({"status": "skipped", "reason": "empty fragments"}))
        return
    y = np.asarray([int(r["label"]) for r in records], dtype=np.int64)
    if args.setting in {"C0", "C1"}:
        x = seq_features(records, args.kmer)
    else:
        if not args.model_path:
            raise SystemExit("--model-path required for A/B settings")
        device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
        x = model_embeddings(records, args.model_path, args.model_kind, args.batch_size, device)
    tr_idx = te_idx = None
    if args.setting.endswith("1"):
        from embedding_cluster import choose_split
        tr_idx, te_idx = choose_split(y, args.seed)
        x = supervised_contrastive_project(x, y, args.seed, tr_idx, args.contrastive_epochs)
    metric, clusters = evaluate_embeddings(x, y, args.seed, tr_idx, te_idx)
    metric.update({
        "setting": args.setting,
        "fragments": args.fragments,
        "model_path": args.model_path or "",
        "model_kind": args.model_kind,
        "label_level": args.label_level,
        "source": args.source,
    })
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metrics.json").write_text(json.dumps(metric, indent=2) + "\n")
    with (out_dir / "assignments.tsv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["idx", "species", "label", "label_name", "cluster", "source", "rep_name"], delimiter="\t")
        writer.writeheader()
        for i, (rec, cluster) in enumerate(zip(records, clusters)):
            writer.writerow({
                "idx": i,
                "species": rec.get("species", ""),
                "label": rec["label"],
                "label_name": rec["label_name"],
                "cluster": int(cluster),
                "source": rec.get("source", ""),
                "rep_name": rec.get("rep_name", ""),
            })
    plot_embeddings(x, y, clusters, out_dir / "embedding_plot.png", args.seed)
    print(json.dumps(metric, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("extract-genomic")
    p.add_argument("--manifest", required=True)
    p.add_argument("--out-jsonl", required=True)
    p.add_argument("--out-meta", required=True)
    p.add_argument("--source", choices=["genomic_internal", "genomic_boundary"], required=True)
    p.add_argument("--label-level", choices=["superfamily", "family"], default="family")
    p.add_argument("--split", default="fine_tune")
    p.add_argument("--species", nargs="*")
    p.add_argument("--length", type=int, required=True)
    p.add_argument("--top-labels", type=int, default=8)
    p.add_argument("--min-per-label", type=int, default=30)
    p.add_argument("--max-per-label", type=int, default=180)
    p.add_argument("--max-n-frac", type=float, default=0.1)
    p.add_argument("--seed", type=int, default=42)
    p = sub.add_parser("extract-consensus")
    p.add_argument("--consensus-fasta")
    p.add_argument("--out-jsonl", required=True)
    p.add_argument("--out-meta", required=True)
    p.add_argument("--label-level", choices=["superfamily", "family"], default="family")
    p.add_argument("--length", type=int, required=True)
    p.add_argument("--top-labels", type=int, default=8)
    p.add_argument("--min-per-label", type=int, default=30)
    p.add_argument("--max-per-label", type=int, default=180)
    p.add_argument("--max-n-frac", type=float, default=0.1)
    p.add_argument("--seed", type=int, default=42)
    p = sub.add_parser("cluster")
    p.add_argument("--fragments", required=True)
    p.add_argument("--setting", choices=["A0", "A1", "C0", "C1"], required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--model-path")
    p.add_argument("--model-kind", choices=["base", "token"], default="base")
    p.add_argument("--source", default="")
    p.add_argument("--label-level", default="")
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--max-records", type=int, default=1500)
    p.add_argument("--contrastive-epochs", type=int, default=120)
    p.add_argument("--kmer", type=int, default=3)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--cpu", action="store_true")
    args = ap.parse_args()
    if args.cmd == "extract-genomic":
        command_extract_genomic(args)
    elif args.cmd == "extract-consensus":
        command_extract_consensus(args)
    elif args.cmd == "cluster":
        command_cluster(args)


if __name__ == "__main__":
    main()
