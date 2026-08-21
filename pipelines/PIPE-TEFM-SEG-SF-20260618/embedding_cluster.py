#!/usr/bin/env python3
"""TE superfamily fragment embedding and clustering screen."""
from __future__ import annotations

import argparse
import collections
import csv
import gzip
import json
import math
import os
import random
import sys
from pathlib import Path

os.environ.setdefault("TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD", "1")
os.environ.setdefault("WANDB_DISABLED", "true")

import numpy as np
import torch
import torch.nn as nn
from transformers import AutoModel, AutoModelForTokenClassification, AutoTokenizer

try:
    from sklearn.cluster import KMeans as SkKMeans
    from sklearn.decomposition import PCA as SkPCA
    from sklearn.manifold import TSNE as SkTSNE
    from sklearn.metrics import adjusted_rand_score as sk_ari
    from sklearn.metrics import f1_score as sk_f1_score
    from sklearn.metrics import normalized_mutual_info_score as sk_nmi
    from sklearn.metrics import silhouette_score as sk_silhouette
    from sklearn.model_selection import train_test_split as sk_train_test_split
    SKLEARN_AVAILABLE = True
except Exception:
    SkKMeans = SkPCA = SkTSNE = None
    sk_ari = sk_f1_score = sk_nmi = sk_silhouette = sk_train_test_split = None
    SKLEARN_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception:  # plotting is useful but should not block numeric results
    plt = None

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from prepare_superfamily_windows import ID2LABEL, map_class, opener, read_manifest  # noqa: E402


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
        raise RuntimeError(f"chrom {chrom} not found in {path}")
    return "".join(parts)


def fasta_index_path(path: str) -> Path | None:
    p = Path(path)
    candidates = [Path(str(p) + ".fai")]
    if str(p).endswith(".fa"):
        candidates.append(Path(str(p) + ".gz.fai"))
    for cand in candidates:
        if cand.exists():
            return cand
    return None


def fetch_fasta_interval(path: str, chrom: str, start: int, end: int,
                         chrom_cache: dict[tuple[str, str], str]) -> str:
    """Fetch 0-based half-open interval.

    Uses a normal FASTA .fai when available. Invalid placeholder fai files
    with zero line sizes are ignored.
    """
    fai = fasta_index_path(path)
    if fai is not None and not str(path).endswith(".gz"):
        with fai.open() as handle:
            for line in handle:
                parts = line.rstrip().split("\t")
                if len(parts) < 5 or parts[0] != chrom:
                    continue
                length, offset, line_bases, line_width = map(int, parts[1:5])
                if line_bases <= 0 or line_width <= 0:
                    break
                start = max(0, min(start, length))
                end = max(start, min(end, length))
                byte_start = offset + (start // line_bases) * line_width + (start % line_bases)
                n_bases = end - start
                n_lines = (start % line_bases + n_bases + line_bases - 1) // line_bases
                n_bytes = n_bases + n_lines + 2
                with open(path, "rb") as fasta:
                    fasta.seek(byte_start)
                    raw = fasta.read(n_bytes).decode()
                return "".join(raw.split()).upper()[:n_bases]
    key = (path, chrom)
    if key not in chrom_cache:
        chrom_cache[key] = read_fasta_chrom(path, chrom)
    return chrom_cache[key][start:end].upper()


def load_intervals(bed: str):
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
            cls = map_class(rep_class, rep_family, name)
            if cls > 0:
                out.append((chrom, start, end, cls, name, rep_class, rep_family))
    return out


def command_extract(args) -> None:
    random.seed(args.seed)
    rows = [r for r in read_manifest(args.manifest) if r.get("split") == "fine_tune"]
    by_cls = collections.defaultdict(list)
    chrom_cache: dict[tuple[str, str], str] = {}
    for row in rows:
        species = row["species_code"]
        genome = row["genome"]
        bed = row["comparator_strict"]
        if not genome or not bed or not Path(genome).exists() or not Path(bed).exists():
            print(f"[skip] {species}: missing genome or comparator_strict", flush=True)
            continue
        if not Path(genome).exists() or not Path(bed).exists():
            continue
        for chrom, start, end, cls, name, rep_class, rep_family in load_intervals(bed):
            if end - start < args.length:
                continue
            if len(by_cls[cls]) >= args.max_per_class:
                continue
            offset_space = end - start - args.length
            frag_start = start + (offset_space // 2)
            try:
                seq = fetch_fasta_interval(genome, chrom, frag_start, frag_start + args.length, chrom_cache)
            except Exception as exc:
                print(f"[skip] {species} {chrom}: {exc}", flush=True)
                continue
            if len(seq) != args.length or seq.count("N") / max(1, len(seq)) > args.max_n_frac:
                continue
            by_cls[cls].append({
                "sequence": seq, "label": cls, "label_name": ID2LABEL[cls],
                "species": species, "chrom": chrom, "start": frag_start, "end": frag_start + args.length,
                "rep_name": name, "rep_class": rep_class, "rep_family": rep_family,
            })
            if all(len(by_cls[c]) >= args.max_per_class for c in range(1, 6)):
                break
        if all(len(by_cls[c]) >= args.max_per_class for c in range(1, 6)):
            break
    records = []
    for cls in range(1, 6):
        vals = by_cls.get(cls, [])
        random.shuffle(vals)
        records.extend(vals[:args.max_per_class])
    random.shuffle(records)
    out = Path(args.out_jsonl)
    out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out, "wt") as handle:
        for rec in records:
            handle.write(json.dumps(rec) + "\n")
    meta = {
        "out_jsonl": str(out), "n": len(records), "length": args.length,
        "counts": collections.Counter(r["label_name"] for r in records),
        "manifest": args.manifest,
    }
    Path(args.out_meta).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_meta).write_text(json.dumps(meta, indent=2, default=dict) + "\n")
    print(json.dumps(meta, indent=2, default=dict))


def load_records(path: str, max_records: int | None = None):
    rows = []
    with gzip.open(path, "rt") as handle:
        for i, line in enumerate(handle):
            if max_records is not None and i >= max_records:
                break
            rows.append(json.loads(line))
    return rows


def seq_features(records: list[dict], k: int = 3) -> np.ndarray:
    alphabet = "ACGT"
    kmers = [""]
    for _ in range(k):
        kmers = [p + c for p in kmers for c in alphabet]
    idx = {kmer: i for i, kmer in enumerate(kmers)}
    feats = []
    for rec in records:
        seq = rec["sequence"].upper()
        vec = np.zeros(len(kmers) + 4, dtype=np.float32)
        for i in range(0, max(0, len(seq) - k + 1)):
            kmer = seq[i:i + k]
            if kmer in idx:
                vec[idx[kmer]] += 1
        if vec[:len(kmers)].sum() > 0:
            vec[:len(kmers)] /= vec[:len(kmers)].sum()
        gc = (seq.count("G") + seq.count("C")) / max(1, len(seq))
        vec[-4:] = [gc, seq.count("A") / len(seq), seq.count("C") / len(seq), seq.count("G") / len(seq)]
        feats.append(vec)
    return np.vstack(feats)


def standardize(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    mean = x.mean(axis=0, keepdims=True)
    std = x.std(axis=0, keepdims=True)
    std[std < 1e-6] = 1.0
    return (x - mean) / std


def pca_numpy(x: np.ndarray, n_components: int = 2) -> np.ndarray:
    x = standardize(x)
    _, _, vt = np.linalg.svd(x, full_matrices=False)
    return x @ vt[:n_components].T


def stratified_split_indices(y: np.ndarray, test_size: float, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    train = []
    test = []
    for label in sorted(set(y.tolist())):
        idx = np.flatnonzero(y == label)
        rng.shuffle(idx)
        n_test = max(1, int(round(len(idx) * test_size))) if len(idx) > 1 else 0
        test.extend(idx[:n_test].tolist())
        train.extend(idx[n_test:].tolist())
    return np.asarray(train, dtype=np.int64), np.asarray(test, dtype=np.int64)


class NumpyKMeans:
    def __init__(self, n_clusters: int, random_state: int = 42, n_init: int = 10, max_iter: int = 100):
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.n_init = n_init
        self.max_iter = max_iter
        self.centers = None

    def fit_predict(self, x: np.ndarray) -> np.ndarray:
        rng = np.random.default_rng(self.random_state)
        best_labels = None
        best_inertia = float("inf")
        for _ in range(self.n_init):
            if x.shape[0] < self.n_clusters:
                labels = np.arange(x.shape[0]) % self.n_clusters
                centers = np.vstack([x[labels == k].mean(axis=0) if np.any(labels == k) else x[0] for k in range(self.n_clusters)])
            else:
                centers = x[rng.choice(x.shape[0], self.n_clusters, replace=False)].copy()
                labels = np.zeros(x.shape[0], dtype=np.int64)
                for _iter in range(self.max_iter):
                    dist = ((x[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
                    new_labels = dist.argmin(axis=1)
                    if np.array_equal(new_labels, labels) and _iter > 0:
                        break
                    labels = new_labels
                    for k in range(self.n_clusters):
                        if np.any(labels == k):
                            centers[k] = x[labels == k].mean(axis=0)
            inertia = float(((x - centers[labels]) ** 2).sum())
            if inertia < best_inertia:
                best_inertia = inertia
                best_labels = labels.copy()
                self.centers = centers.copy()
        return best_labels

    def predict(self, x: np.ndarray) -> np.ndarray:
        dist = ((x[:, None, :] - self.centers[None, :, :]) ** 2).sum(axis=2)
        return dist.argmin(axis=1)


def contingency(labels_true: np.ndarray, labels_pred: np.ndarray) -> np.ndarray:
    true_vals = sorted(set(labels_true.tolist()))
    pred_vals = sorted(set(labels_pred.tolist()))
    ti = {v: i for i, v in enumerate(true_vals)}
    pi = {v: i for i, v in enumerate(pred_vals)}
    mat = np.zeros((len(true_vals), len(pred_vals)), dtype=np.int64)
    for t, p in zip(labels_true, labels_pred):
        mat[ti[int(t)], pi[int(p)]] += 1
    return mat


def comb2(x):
    x = np.asarray(x, dtype=np.float64)
    return x * (x - 1) / 2


def ari_numpy(labels_true: np.ndarray, labels_pred: np.ndarray) -> float:
    mat = contingency(labels_true, labels_pred)
    n = mat.sum()
    if n < 2:
        return 0.0
    sum_comb = comb2(mat).sum()
    row_comb = comb2(mat.sum(axis=1)).sum()
    col_comb = comb2(mat.sum(axis=0)).sum()
    total_comb = comb2(n)
    expected = row_comb * col_comb / total_comb if total_comb else 0.0
    max_index = 0.5 * (row_comb + col_comb)
    denom = max_index - expected
    return float((sum_comb - expected) / denom) if denom else 0.0


def nmi_numpy(labels_true: np.ndarray, labels_pred: np.ndarray) -> float:
    mat = contingency(labels_true, labels_pred).astype(np.float64)
    n = mat.sum()
    if n <= 0:
        return 0.0
    pij = mat / n
    pi = pij.sum(axis=1, keepdims=True)
    pj = pij.sum(axis=0, keepdims=True)
    nz = pij > 0
    mi = float((pij[nz] * np.log(pij[nz] / (pi @ pj)[nz])).sum())
    hi = float(-(pi[pi > 0] * np.log(pi[pi > 0])).sum())
    hj = float(-(pj[pj > 0] * np.log(pj[pj > 0])).sum())
    return mi / math.sqrt(hi * hj) if hi > 0 and hj > 0 else 0.0


def macro_f1_numpy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    vals = sorted(set(y_true.tolist()))
    f1s = []
    for v in vals:
        tp = int(((y_true == v) & (y_pred == v)).sum())
        fp = int(((y_true != v) & (y_pred == v)).sum())
        fn = int(((y_true == v) & (y_pred != v)).sum())
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * p * r / (p + r) if p + r else 0.0)
    return float(np.mean(f1s)) if f1s else 0.0


def model_embeddings(records: list[dict], model_path: str, model_kind: str, batch_size: int, device: torch.device) -> np.ndarray:
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True, local_files_only=True)
    if model_kind == "token":
        model = AutoModelForTokenClassification.from_pretrained(model_path, trust_remote_code=True, local_files_only=True)
    else:
        model = AutoModel.from_pretrained(model_path, trust_remote_code=True, local_files_only=True)
    model.to(device)
    model.eval()
    vecs = []
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        seqs = [r["sequence"] for r in batch]
        max_len = max(len(s) for s in seqs) + 2
        enc = tokenizer(seqs, truncation=True, max_length=max_len, padding=True, return_tensors="pt")
        enc = {k: v.to(device) for k, v in enc.items() if k in {"input_ids", "attention_mask"}}
        with torch.no_grad():
            out = model(**enc, output_hidden_states=True)
        hidden = out.hidden_states[-1] if getattr(out, "hidden_states", None) is not None else out[0]
        mask = enc.get("attention_mask", torch.ones(hidden.shape[:2], device=device)).unsqueeze(-1).float()
        pooled = (hidden * mask).sum(dim=1) / torch.clamp(mask.sum(dim=1), min=1.0)
        vecs.append(pooled.detach().cpu().numpy())
        print(f"embedded {min(i + batch_size, len(records))}/{len(records)}", flush=True)
    return np.vstack(vecs)


class Projection(nn.Module):
    def __init__(self, in_dim: int, out_dim: int = 64):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(in_dim, 256), nn.ReLU(), nn.Linear(256, out_dim))

    def forward(self, x):
        z = self.net(x)
        return nn.functional.normalize(z, dim=-1)


def supervised_contrastive_project(x: np.ndarray, y: np.ndarray, seed: int,
                                   train_idx: np.ndarray | None = None,
                                   epochs: int = 80) -> np.ndarray:
    torch.manual_seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    x_t = torch.tensor(standardize(x), dtype=torch.float32, device=device)
    y_t = torch.tensor(y, dtype=torch.long, device=device)
    if train_idx is None:
        train_idx = np.arange(len(y), dtype=np.int64)
    train_idx_t = torch.tensor(train_idx, dtype=torch.long, device=device)
    model = Projection(x.shape[1]).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    temp = 0.07
    n = train_idx_t.shape[0]
    for _ in range(epochs):
        perm = train_idx_t[torch.randperm(n, device=device)]
        for start in range(0, n, 256):
            take = perm[start:start + 256]
            xb = x_t[take]
            yb = y_t[take]
            z = model(xb)
            sim = z @ z.T / temp
            eye = torch.eye(z.shape[0], dtype=torch.bool, device=device)
            pos = (yb[:, None] == yb[None, :]) & ~eye
            sim = sim.masked_fill(eye, -1e9)
            logp = sim - torch.logsumexp(sim, dim=1, keepdim=True)
            denom = pos.sum(dim=1).clamp(min=1)
            loss = -(logp.masked_fill(~pos, 0.0).sum(dim=1) / denom)
            loss = loss[pos.sum(dim=1) > 0].mean()
            if torch.isfinite(loss):
                opt.zero_grad()
                loss.backward()
                opt.step()
    with torch.no_grad():
        return model(x_t).detach().cpu().numpy()


def majority_map(train_y: np.ndarray, train_clusters: np.ndarray) -> dict[int, int]:
    mapping = {}
    for c in sorted(set(train_clusters.tolist())):
        labels = train_y[train_clusters == c]
        if labels.size:
            mapping[int(c)] = int(collections.Counter(labels.tolist()).most_common(1)[0][0])
    return mapping


def choose_split(y: np.ndarray, seed: int) -> tuple[np.ndarray, np.ndarray]:
    if SKLEARN_AVAILABLE:
        return sk_train_test_split(np.arange(len(y)), test_size=0.25, random_state=seed, stratify=y)
    return stratified_split_indices(y, 0.25, seed)


def evaluate_embeddings(x: np.ndarray, y: np.ndarray, seed: int,
                        tr_idx: np.ndarray | None = None,
                        te_idx: np.ndarray | None = None) -> tuple[dict, np.ndarray]:
    x = standardize(x)
    labels = sorted(set(y.tolist()))
    n_clusters = len(labels)
    if tr_idx is None or te_idx is None:
        tr_idx, te_idx = choose_split(y, seed)
    km = SkKMeans(n_clusters=n_clusters, n_init=20, random_state=seed) if SKLEARN_AVAILABLE else NumpyKMeans(n_clusters=n_clusters, n_init=20, random_state=seed)
    train_clusters = km.fit_predict(x[tr_idx])
    clusters = km.predict(x)
    mapping = majority_map(y[tr_idx], train_clusters)
    pred = np.array([mapping.get(int(c), labels[0]) for c in clusters], dtype=np.int64)
    metrics = {
        "n": int(len(y)),
        "n_clusters": int(n_clusters),
        "ari": float(sk_ari(y, clusters) if SKLEARN_AVAILABLE else ari_numpy(y, clusters)),
        "nmi": float(sk_nmi(y, clusters) if SKLEARN_AVAILABLE else nmi_numpy(y, clusters)),
        "holdout_accuracy": float((pred[te_idx] == y[te_idx]).mean()),
        "holdout_macro_f1": float(sk_f1_score(y[te_idx], pred[te_idx], average="macro", zero_division=0) if SKLEARN_AVAILABLE else macro_f1_numpy(y[te_idx], pred[te_idx])),
        "silhouette": float(sk_silhouette(x, clusters)) if SKLEARN_AVAILABLE and len(set(clusters.tolist())) > 1 and len(y) > n_clusters else math.nan,
        "sklearn_available": SKLEARN_AVAILABLE,
    }
    return metrics, clusters


def plot_embeddings(x: np.ndarray, y: np.ndarray, clusters: np.ndarray, out_png: Path, seed: int) -> None:
    if plt is None:
        out_png.parent.mkdir(parents=True, exist_ok=True)
        (out_png.with_suffix(".plot_warning.txt")).write_text("matplotlib unavailable; skipped embedding plot\n")
        return
    x_std = standardize(x)
    if x_std.shape[1] > 2:
        if SKLEARN_AVAILABLE:
            pca = SkPCA(n_components=min(20, x_std.shape[1]), random_state=seed).fit_transform(x_std)
        else:
            pca = pca_numpy(x_std, min(20, x_std.shape[1]))
        if SKLEARN_AVAILABLE and len(y) >= 50:
            coords = SkTSNE(n_components=2, random_state=seed, init="pca", learning_rate="auto", perplexity=min(30, max(5, len(y) // 20))).fit_transform(pca)
        else:
            coords = pca[:, :2]
    else:
        coords = x_std
    fig, ax = plt.subplots(1, 2, figsize=(10, 4), dpi=140)
    sc0 = ax[0].scatter(coords[:, 0], coords[:, 1], c=y, s=10, cmap="tab10", alpha=0.8)
    ax[0].set_title("True superfamily")
    ax[1].scatter(coords[:, 0], coords[:, 1], c=clusters, s=10, cmap="tab10", alpha=0.8)
    ax[1].set_title("KMeans cluster")
    for a in ax:
        a.set_xticks([])
        a.set_yticks([])
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)


def command_cluster(args) -> None:
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    records = load_records(args.fragments, args.max_records)
    y = np.asarray([int(r["label"]) for r in records], dtype=np.int64)
    if args.setting in {"C0", "C1"}:
        x = seq_features(records, args.kmer)
    else:
        if args.model_path is None:
            raise SystemExit("--model-path is required for A/B model embedding settings")
        device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
        x = model_embeddings(records, args.model_path, args.model_kind, args.batch_size, device)
    tr_idx = te_idx = None
    if args.setting.endswith("1"):
        tr_idx, te_idx = choose_split(y, args.seed)
        x = supervised_contrastive_project(x, y, args.seed, tr_idx, args.contrastive_epochs)
    metrics, clusters = evaluate_embeddings(x, y, args.seed, tr_idx, te_idx)
    metrics.update({
        "setting": args.setting,
        "fragments": args.fragments,
        "model_path": args.model_path or "",
        "model_kind": args.model_kind,
        "length": len(records[0]["sequence"]) if records else 0,
    })
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    with (out_dir / "assignments.tsv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["idx", "species", "label", "label_name", "cluster", "rep_name"], delimiter="\t")
        writer.writeheader()
        for i, (rec, c) in enumerate(zip(records, clusters)):
            writer.writerow({"idx": i, "species": rec["species"], "label": rec["label"],
                             "label_name": rec["label_name"], "cluster": int(c), "rep_name": rec.get("rep_name", "")})
    plot_embeddings(x, y, clusters, out_dir / "embedding_plot.png", args.seed)
    print(json.dumps(metrics, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("extract")
    p.add_argument("--manifest", required=True)
    p.add_argument("--length", type=int, required=True)
    p.add_argument("--out-jsonl", required=True)
    p.add_argument("--out-meta", required=True)
    p.add_argument("--max-per-class", type=int, default=120)
    p.add_argument("--max-n-frac", type=float, default=0.1)
    p.add_argument("--seed", type=int, default=42)
    p = sub.add_parser("cluster")
    p.add_argument("--fragments", required=True)
    p.add_argument("--setting", choices=["A0", "A1", "B0", "B1", "C0", "C1"], required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--model-path")
    p.add_argument("--model-kind", choices=["base", "token"], default="base")
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--max-records", type=int, default=1200)
    p.add_argument("--contrastive-epochs", type=int, default=80)
    p.add_argument("--kmer", type=int, default=3)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--cpu", action="store_true")
    args = ap.parse_args()
    if args.cmd == "extract":
        command_extract(args)
    elif args.cmd == "cluster":
        command_cluster(args)


if __name__ == "__main__":
    main()
