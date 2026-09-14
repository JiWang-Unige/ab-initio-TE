#!/usr/bin/env python3
"""
Module 5: Compute embeddings for TE fragments using various strategies.

Settings (2×2 + 2 baselines):
  A0: raw 6-mer frequency features (4096-d, no model)
  A1: pretrained GENERanno embeddings (no contrastive, no finetune)
  A2: multi-species-finetuned GENERanno embeddings (no contrastive)
  B0: 6-mer features + learned contrastive projection head (typically 128-d)
  B1: pretrained GENERanno + contrastive learning
  B2: multi-species-finetuned GENERanno + contrastive learning

Usage:
    python compute_embeddings.py \
        --fragments_file <te_fragments.jsonl> \
        --setting A1 \
        --model_path <path> \
        --output_dir <path>
"""
import argparse
import csv
import json
import numpy as np
import torch
from pathlib import Path
from collections import defaultdict, Counter
from sklearn.preprocessing import StandardScaler


def compute_kmer_features(sequences, k=6):
    """Compute k-mer frequency vectors."""
    from itertools import product
    bases = 'ACGT'
    all_kmers = [''.join(p) for p in product(bases, repeat=k)]
    kmer_to_idx = {kmer: i for i, kmer in enumerate(all_kmers)}
    n_kmers = len(all_kmers)

    features = np.zeros((len(sequences), n_kmers), dtype=np.float32)
    for i, seq in enumerate(sequences):
        seq = seq.upper()
        total = 0
        for j in range(len(seq) - k + 1):
            kmer = seq[j:j+k]
            if kmer in kmer_to_idx:
                features[i, kmer_to_idx[kmer]] += 1
                total += 1
        if total > 0:
            features[i] /= total  # Normalize to frequency

    return features


def compute_model_embeddings(sequences, model_path, batch_size=32, max_length=2048,
                             device='cuda', pooling='mean'):
    """Compute embeddings using a pretrained model."""
    from transformers import AutoTokenizer, AutoModel

    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    model = AutoModel.from_pretrained(model_path, trust_remote_code=True, dtype=torch.bfloat16)
    model.to(device)
    model.eval()

    hidden_size = model.config.hidden_size
    all_embeddings = np.zeros((len(sequences), hidden_size), dtype=np.float32)

    with torch.no_grad():
        for start in range(0, len(sequences), batch_size):
            batch_seqs = sequences[start:start + batch_size]
            # Truncate to max_length
            batch_seqs = [s[:max_length] for s in batch_seqs]

            encoded = tokenizer(batch_seqs, return_tensors='pt', padding=True,
                                truncation=True, max_length=max_length,
                                add_special_tokens=False)
            input_ids = encoded['input_ids'].to(device)
            attention_mask = encoded['attention_mask'].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            hidden_states = outputs.last_hidden_state  # (batch, seq_len, hidden)

            if pooling == 'mean':
                # Mean pooling with attention mask
                mask_expanded = attention_mask.unsqueeze(-1).expand(hidden_states.size()).float()
                sum_embeddings = torch.sum(hidden_states * mask_expanded, dim=1)
                sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
                embeddings = sum_embeddings / sum_mask
            elif pooling == 'cls':
                embeddings = hidden_states[:, 0, :]
            else:
                raise ValueError(f"Unknown pooling: {pooling}")

            all_embeddings[start:start + len(batch_seqs)] = embeddings.cpu().numpy()

            if (start // batch_size) % 10 == 0:
                print(f"  Processed {start + len(batch_seqs)}/{len(sequences)} sequences")

    return all_embeddings


def cluster_and_evaluate(embeddings, true_labels, n_clusters=None):
    """Run clustering and compute metrics."""
    from sklearn.cluster import KMeans
    from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score
    from sklearn.decomposition import PCA
    import umap

    if n_clusters is None:
        n_clusters = len(set(true_labels))

    # Standardize
    scaler = StandardScaler()
    embeddings_scaled = scaler.fit_transform(embeddings)

    # PCA first if high-dimensional
    if embeddings_scaled.shape[1] > 50:
        pca = PCA(n_components=50, random_state=42)
        embeddings_pca = pca.fit_transform(embeddings_scaled)
    else:
        embeddings_pca = embeddings_scaled

    # UMAP for visualization
    reducer = umap.UMAP(n_components=2, random_state=42, n_neighbors=15, min_dist=0.1)
    umap_coords = reducer.fit_transform(embeddings_pca)

    # Also 3D UMAP
    reducer_3d = umap.UMAP(n_components=3, random_state=42, n_neighbors=15, min_dist=0.1)
    umap_3d = reducer_3d.fit_transform(embeddings_pca)

    # K-Means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(embeddings_pca)

    # Metrics
    nmi = normalized_mutual_info_score(true_labels, cluster_labels)
    ari = adjusted_rand_score(true_labels, cluster_labels)

    return {
        'nmi': float(nmi),
        'ari': float(ari),
        'n_clusters': n_clusters,
        'umap_2d': umap_coords,
        'umap_3d': umap_3d,
        'cluster_labels': cluster_labels,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fragments_file", required=True)
    parser.add_argument("--setting", required=True, choices=['A0', 'A1', 'A2', 'B0', 'B1', 'B2'])
    parser.add_argument("--model_path", default=None, help="Model path (for A1/A2/B1/B2)")
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--max_fragments", type=int, default=None)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load fragments
    print(f"Loading fragments from {args.fragments_file}...")
    fragments = []
    with open(args.fragments_file) as f:
        for line in f:
            fragments.append(json.loads(line))

    if args.max_fragments and len(fragments) > args.max_fragments:
        import random
        random.seed(42)
        fragments = random.sample(fragments, args.max_fragments)

    sequences = [f['sequence'] for f in fragments]
    classes = [f['class'] for f in fragments]
    species = [f['species'] for f in fragments]
    families = [f['family'] for f in fragments]

    print(f"  {len(fragments)} fragments, {len(set(classes))} classes, {len(set(species))} species")

    # Compute embeddings based on setting
    setting = args.setting
    print(f"\n=== Computing embeddings: Setting {setting} ===")

    if setting in ('A0', 'B0'):
        # k-mer features
        print("  Computing 6-mer features...")
        embeddings = compute_kmer_features(sequences, k=6)
        print(f"  k-mer feature shape: {embeddings.shape}")
    else:
        # Model embeddings
        if args.model_path is None:
            args.model_path = "/srv/beegfs/scratch/shares/ds4dh/common/TE_benchmark/glm_models/generanno/GENERanno-eukaryote-0.5b-base"

        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"  Computing model embeddings ({args.model_path})...")
        embeddings = compute_model_embeddings(
            sequences, args.model_path, args.batch_size,
            max_length=2048, device=device
        )
        print(f"  Embedding shape: {embeddings.shape}")

    # For B settings: apply trained contrastive projection head
    if setting.startswith('B'):
        contrastive_path = Path(args.output_dir) / f"contrastive_head_{setting}.pt"
        if contrastive_path.exists():
            print(f"  Applying contrastive projection head: {contrastive_path}")
            checkpoint = torch.load(str(contrastive_path), map_location='cpu')
            # Standardize using saved scaler
            scaler_mean = checkpoint['scaler_mean']
            scaler_scale = checkpoint['scaler_scale']
            embeddings_scaled = (embeddings - scaler_mean) / (scaler_scale + 1e-12)
            # Build and load projection head (inline to avoid import path issues)
            import torch.nn.functional as F_proj
            class _ProjectionHead(torch.nn.Module):
                def __init__(self, input_dim, hidden_dim, output_dim):
                    super().__init__()
                    self.net = torch.nn.Sequential(
                        torch.nn.Linear(input_dim, hidden_dim),
                        torch.nn.ReLU(),
                        torch.nn.Linear(hidden_dim, output_dim),
                    )
                def forward(self, x):
                    return F_proj.normalize(self.net(x), dim=1)

            proj = _ProjectionHead(
                checkpoint['input_dim'],
                checkpoint['hidden_dim'],
                checkpoint['projection_dim'],
            )
            proj.load_state_dict(checkpoint['projection_head'])
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            proj.to(device).eval()
            with torch.no_grad():
                inp = torch.tensor(embeddings_scaled, dtype=torch.float32).to(device)
                projected = []
                for i in range(0, len(inp), 1024):
                    projected.append(proj(inp[i:i+1024]).cpu().numpy())
            embeddings = np.concatenate(projected, axis=0)
            print(f"  Projected embedding shape: {embeddings.shape}")
        else:
            print(f"  WARNING: No contrastive head found at {contrastive_path}")
            print(f"  Run train_contrastive.py first for setting {setting}")
            print(f"  Using raw embeddings as fallback.")

    # Save raw embeddings
    np.save(str(output_dir / f"embeddings_{setting}.npy"), embeddings)

    # Cluster by class
    print(f"\n=== Clustering by TE class ===")
    results_class = cluster_and_evaluate(embeddings, classes)
    print(f"  NMI={results_class['nmi']:.4f}, ARI={results_class['ari']:.4f}")

    # Cluster by species
    print(f"\n=== Clustering by species ===")
    results_species = cluster_and_evaluate(embeddings, species, n_clusters=len(set(species)))
    print(f"  NMI={results_species['nmi']:.4f}, ARI={results_species['ari']:.4f}")

    # Save UMAP coordinates
    umap_data = []
    for i in range(len(fragments)):
        umap_data.append({
            'species': species[i],
            'class': classes[i],
            'family': families[i],
            'length': fragments[i]['length'],
            'umap_x': float(results_class['umap_2d'][i, 0]),
            'umap_y': float(results_class['umap_2d'][i, 1]),
            'umap_3d_x': float(results_class['umap_3d'][i, 0]),
            'umap_3d_y': float(results_class['umap_3d'][i, 1]),
            'umap_3d_z': float(results_class['umap_3d'][i, 2]),
            'cluster': int(results_class['cluster_labels'][i]),
        })

    umap_path = output_dir / f"umap_coords_{setting}.tsv"
    with open(umap_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(umap_data[0].keys()), delimiter='\t')
        w.writeheader()
        for row in umap_data:
            w.writerow(row)

    # Save metrics
    metrics = {
        'setting': setting,
        'num_fragments': len(fragments),
        'num_classes': len(set(classes)),
        'num_species': len(set(species)),
        'embedding_dim': embeddings.shape[1],
        'class_clustering': {'nmi': results_class['nmi'], 'ari': results_class['ari']},
        'species_clustering': {'nmi': results_species['nmi'], 'ari': results_species['ari']},
    }
    with open(output_dir / f"metrics_{setting}.json", 'w') as f:
        json.dump(metrics, f, indent=2)

    print(f"\n=== Results saved to {output_dir} ===")
    print(f"  Embeddings: embeddings_{setting}.npy")
    print(f"  UMAP: umap_coords_{setting}.tsv")
    print(f"  Metrics: metrics_{setting}.json")


if __name__ == "__main__":
    main()
