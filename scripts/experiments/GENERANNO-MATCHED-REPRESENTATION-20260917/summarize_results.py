#!/usr/bin/env python3
"""Make a compact report from one completed matched GENERanno run."""

from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter
from pathlib import Path


LABEL_NAMES = (
    "BG",
    "SINE",
    "LINE",
    "LTR",
    "DNA",
    "KNOWN_OTHER_TE",
    "AMBIGUOUS_TE",
    "UNCLASSIFIED",
)
MODELS = ("pretrained", "binary_finetuned", "multiclass_finetuned")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-root", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    return ap.parse_args()


def sequence_quality(run_root: Path) -> dict:
    """Describe input symbols without changing any fixed-panel record or label."""

    manifest = load_json(run_root / "features" / "input_manifest.json")
    data_dir = Path(manifest["data_dir"])
    quality = {}
    for split in ("train", "val", "test"):
        path = data_dir / split / "data.jsonl.gz"
        n_records = 0
        total_bases = 0
        non_acgt_bases = 0
        non_acgt_records = 0
        all_n_records = 0
        all_n_labels: Counter[str] = Counter()
        non_acgt_labels: Counter[str] = Counter()
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                sequence = str(row.get("sequence", "")).upper()
                if len(sequence) != 512:
                    raise SystemExit(f"{path}:{line_no}: expected 512 bp, got {len(sequence)}")
                label_name = LABEL_NAMES[int(row["label"])]
                n_records += 1
                total_bases += len(sequence)
                n_non_acgt = sum(base not in "ACGT" for base in sequence)
                non_acgt_bases += n_non_acgt
                if n_non_acgt:
                    non_acgt_records += 1
                    non_acgt_labels[label_name] += 1
                if set(sequence) == {"N"}:
                    all_n_records += 1
                    all_n_labels[label_name] += 1
        quality[split] = {
            "n_records": n_records,
            "total_bases": total_bases,
            "non_acgt_bases": non_acgt_bases,
            "non_acgt_fraction": non_acgt_bases / total_bases if total_bases else None,
            "records_with_non_acgt": non_acgt_records,
            "all_n_records": all_n_records,
            "all_n_labels": dict(sorted(all_n_labels.items())),
            "records_with_non_acgt_by_label": dict(sorted(non_acgt_labels.items())),
        }
    return {"data_dir": str(data_dir), "by_split": quality}


def main() -> None:
    args = parse_args()
    if not (args.run_root / "STATUS").is_file():
        raise SystemExit(f"completed STATUS is missing: {args.run_root}")
    rows = []
    metadata = {}
    for model_id in MODELS:
        feature_root = args.run_root / "features" / model_id
        meta = load_json(feature_root / "metadata.json")
        metrics = load_json(args.run_root / "metrics" / model_id / "metrics.json")
        if meta.get("pooling") != "attention_mask_mean_excluding_padding_and_special_tokens":
            raise SystemExit(f"{model_id}: pooling contract mismatch")
        metadata[model_id] = meta
        knn = metrics["supervised_knn5"]
        km = metrics["unsupervised_kmeans"]
        rows.append(
            {
                "model_id": model_id,
                "model_kind": meta.get("model_kind"),
                "feature_dim": meta.get("feature_dim"),
                "known_five_knn_macro_f1": knn["known_five"]["macro_f1"],
                "full_eight_knn_macro_f1": knn["full_eight"]["macro_f1"],
                "conditional_te_four_knn_macro_f1": knn["conditional_te_four"]["macro_f1"],
                "binary_known_knn_macro_f1": knn["binary_te_vs_bg_known"]["macro_f1"],
                "known_five_kmeans_k5_ari": km["known_five"]["k5"]["ari"],
                "known_five_kmeans_k5_nmi": km["known_five"]["k5"]["nmi"],
                "full_eight_kmeans_k8_ari": km["full_eight"]["k8"]["ari"],
                "full_eight_kmeans_k8_nmi": km["full_eight"]["k8"]["nmi"],
                "conditional_te_four_kmeans_k4_ari": km["conditional_te_four"]["k4"]["ari"],
                "conditional_te_four_kmeans_k4_nmi": km["conditional_te_four"]["k4"]["nmi"],
                "binary_known_full_k2_ari": km["binary_te_vs_bg_known_from_full_k2"]["ari"],
                "binary_known_full_k2_nmi": km["binary_te_vs_bg_known_from_full_k2"]["nmi"],
                "test_labels": metrics["counts"]["test_labels"],
                "knn_by_species": {
                    endpoint: knn[endpoint].get("by_species", {})
                    for endpoint in ("known_five", "full_eight", "conditional_te_four")
                },
            }
        )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "status": "PASS_MATCHED_GENERANNO_REPRESENTATION",
        "run_root": str(args.run_root),
        "models": rows,
        "pooling": "attention_mask_mean_excluding_padding_and_special_tokens",
        "interpretation": {
            "knn": "supervised train-fitted 5-NN readout",
            "kmeans": "unsupervised train-fitted geometry diagnostic with predeclared K",
            "coordinate_split_check": "binary human-only training; SF5 train/test chromosomes disjoint by species",
            "homologous_copy_exposure": "unresolved",
            "independent_generalization": "not_claimed",
        },
        "feature_metadata": metadata,
        "input_sequence_quality": sequence_quality(args.run_root),
    }
    (args.out_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    lines = [
        "# GENERanno matched representation results",
        "",
        "Status: `PASS_MATCHED_GENERANNO_REPRESENTATION`",
        "",
        "The three frozen GENERanno checkpoints were evaluated on the same SIB",
        "train/validation/test panel with the same tokenizer and mean pooling",
        "excluding structural BOS/EOS/PAD/MASK while retaining N/UNK as sequence",
        "content. kNN is a supervised",
        "train-fitted readout; K-means is an",
        "annotation-filtered, train-fitted geometry diagnostic with K fixed in advance.",
        "These results are a paired representation diagnostic, not an independent",
        "biological truth or homologous-copy-free generalization test.",
        "",
        "| checkpoint | dim | known-5 kNN F1 | full-8 kNN F1 | TE-only kNN F1 | binary kNN F1 | known-5 K5 ARI | full-8 K8 ARI | TE-only K4 ARI | binary K2 ARI |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {model_id} | {feature_dim} | {known_five_knn_macro_f1:.4f} | {full_eight_knn_macro_f1:.4f} | "
            "{conditional_te_four_knn_macro_f1:.4f} | {binary_known_knn_macro_f1:.4f} | "
            "{known_five_kmeans_k5_ari:.4f} | {full_eight_kmeans_k8_ari:.4f} | "
            "{conditional_te_four_kmeans_k4_ari:.4f} | {binary_known_full_k2_ari:.4f} |".format(**row)
        )
    lines.extend(
        [
            "",
            "The saved split metadata finds no species-plus-chromosome overlap between",
            "the binary training source and this panel, and no overlap between SF5",
            "training chromosomes and the SIB test chromosomes. Homologous-copy exposure",
            "was not audited. `KNOWN_OTHER_TE`, `AMBIGUOUS_TE`, and `UNCLASSIFIED` remain",
            "separate full-eight states; they are not relabelled as BG.",
            "",
            "## Fixed-panel input symbol audit",
            "",
            "The audit below is descriptive and leaves every sequence and label in",
            "the frozen panel unchanged. `N` is retained as GENERanno sequence content",
            "because its tokenizer maps `N` to `unk_token`; this is distinct from",
            "structural BOS/EOS/PAD/MASK tokens. Non-ACGT fractions are computed over",
            "all 512-bp records in each split.",
            "",
            "| split | records | all-N windows | all-N labels | non-ACGT bases / total | records with non-ACGT |",
            "|---|---:|---:|---|---:|---:|",
        ]
    )
    quality = result["input_sequence_quality"]["by_split"]
    for split in ("train", "val", "test"):
        item = quality[split]
        label_text = ", ".join(
            f"{name}={count}" for name, count in item["all_n_labels"].items()
        ) or "none"
        lines.append(
            f"| {split} | {item['n_records']} | {item['all_n_records']} | {label_text} | "
            f"{item['non_acgt_bases']} / {item['total_bases']} ({item['non_acgt_fraction']:.6%}) | "
            f"{item['records_with_non_acgt']} |"
        )
    lines.extend(
        [
            "",
            "The all-N test windows are therefore retained observations, not dropped",
            "or relabelled failure cases. The symbol audit does not establish whether",
            "these windows are biologically representative of the broader species set.",
        ]
    )
    (args.out_dir / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "models": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
