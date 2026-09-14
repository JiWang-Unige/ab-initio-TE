#!/usr/bin/env python3
"""
Module 5: Supervised contrastive learning for TE embeddings.

Trains a projection head using SupCon loss on top of:
  B0: k-mer features
  B1: Pretrained GENERanno embeddings (frozen)
  B2: Multi-species finetuned GENERanno embeddings (frozen)

The trained projection head is saved and used by compute_embeddings.py for B settings.

Usage:
    python train_contrastive.py \
        --fragments_file <te_fragments.jsonl> \
        --setting B1 \
        --model_path <path> \
        --output_dir <path>
"""
import argparse
import json
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from pathlib import Path
from collections import Counter


class SupConLoss(nn.Module):
    """Supervised Contrastive Loss (Khosla et al., 2020)."""

    def __init__(self, temperature=0.07):
        super().__init__()
        self.temperature = temperature

    def forward(self, features, labels):
        """
        Args:
            features: (batch_size, projection_dim) L2-normalized
            labels: (batch_size,) integer class labels
        """
        device = features.device
        batch_size = features.shape[0]

        # Similarity matrix
        similarity = torch.matmul(features, features.T) / self.temperature

        # Mask: 1 for same class (excluding self)
        labels = labels.unsqueeze(1)
        mask = (labels == labels.T).float().to(device)
        mask.fill_diagonal_(0)

        # For numerical stability
        logits_max, _ = similarity.max(dim=1, keepdim=True)
        logits = similarity - logits_max.detach()

        # Exclude self from denominator
        logits_mask = torch.ones_like(mask) - torch.eye(batch_size, device=device)
        exp_logits = torch.exp(logits) * logits_mask

        # Log-prob
        log_prob = logits - torch.log(exp_logits.sum(dim=1, keepdim=True) + 1e-12)

        # Mean log-prob over positives
        mask_sum = mask.sum(dim=1)
        # Avoid division by zero (samples with no same-class partner in batch)
        valid = mask_sum > 0
        if valid.sum() == 0:
            return torch.tensor(0.0, device=device, requires_grad=True)

        mean_log_prob = (mask * log_prob).sum(dim=1) / (mask_sum + 1e-12)
        loss = -mean_log_prob[valid].mean()

        return loss


class ProjectionHead(nn.Module):
    """MLP projection head for contrastive learning."""

    def __init__(self, input_dim, hidden_dim=256, output_dim=128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, x):
        z = self.net(x)
        return F.normalize(z, dim=1)


class FragmentDataset(Dataset):
    """Dataset for TE fragment embeddings."""

    def __init__(self, embeddings, labels):
        self.embeddings = torch.tensor(embeddings, dtype=torch.float32)
        self.labels = torch.tensor(labels, dtype=torch.long)

    def __len__(self):
        return len(self.embeddings)

    def __getitem__(self, idx):
        return self.embeddings[idx], self.labels[idx]


def precompute_embeddings(fragments, setting, model_path, batch_size, device):
    """Precompute base embeddings for training."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sequences = [f['sequence'] for f in fragments]

    if setting == 'B0':
        from compute_embeddings import compute_kmer_features
        embeddings = compute_kmer_features(sequences, k=6)
    else:
        from compute_embeddings import compute_model_embeddings
        embeddings = compute_model_embeddings(
            sequences, model_path, batch_size,
            max_length=2048, device=device
        )

    return embeddings


def train_projection_head(embeddings, labels, input_dim,
                           hidden_dim=256, projection_dim=128,
                           epochs=50, batch_size=512, lr=1e-3,
                           temperature=0.07, device='cuda'):
    """Train contrastive projection head."""

    dataset = FragmentDataset(embeddings, labels)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True,
                        drop_last=True, num_workers=4)

    model = ProjectionHead(input_dim, hidden_dim, projection_dim).to(device)
    criterion = SupConLoss(temperature=temperature)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    best_loss = float('inf')
    best_state = None

    for epoch in range(epochs):
        model.train()
        total_loss = 0
        n_batches = 0

        for batch_emb, batch_labels in loader:
            batch_emb = batch_emb.to(device)
            batch_labels = batch_labels.to(device)

            projected = model(batch_emb)
            loss = criterion(projected, batch_labels)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            n_batches += 1

        scheduler.step()
        avg_loss = total_loss / max(n_batches, 1)

        if avg_loss < best_loss:
            best_loss = avg_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

        if (epoch + 1) % 10 == 0:
            print(f"  Epoch {epoch+1}/{epochs}: loss={avg_loss:.4f} (best={best_loss:.4f})")

    model.load_state_dict(best_state)
    return model, best_loss


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fragments_file", required=True)
    parser.add_argument("--setting", required=True, choices=['B0', 'B1', 'B2'])
    parser.add_argument("--model_path", default=None)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--batch_size", type=int, default=32,
                        help="Batch size for embedding computation")
    parser.add_argument("--contrastive_batch_size", type=int, default=512,
                        help="Batch size for contrastive training")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--temperature", type=float, default=0.07)
    parser.add_argument("--hidden_dim", type=int, default=256)
    parser.add_argument("--projection_dim", type=int, default=128)
    parser.add_argument("--max_fragments", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    import random
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    # Load fragments
    print(f"Loading fragments from {args.fragments_file}...")
    fragments = []
    with open(args.fragments_file) as f:
        for line in f:
            fragments.append(json.loads(line))

    if args.max_fragments and len(fragments) > args.max_fragments:
        fragments = random.sample(fragments, args.max_fragments)

    classes = [f['class'] for f in fragments]
    class_counts = Counter(classes)
    print(f"  {len(fragments)} fragments, {len(class_counts)} classes")
    for cls, cnt in class_counts.most_common():
        print(f"    {cls}: {cnt}")

    # Convert class strings to integer labels
    class_to_id = {c: i for i, c in enumerate(sorted(set(classes)))}
    labels = np.array([class_to_id[c] for c in classes])

    # Step 1: Precompute base embeddings
    print(f"\n=== Step 1: Precomputing base embeddings ({args.setting}) ===")
    embeddings = precompute_embeddings(fragments, args.setting, args.model_path,
                                        args.batch_size, device)
    print(f"  Base embedding shape: {embeddings.shape}")

    # Standardize
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    embeddings_scaled = scaler.fit_transform(embeddings)

    # Step 2: Train contrastive projection head
    print(f"\n=== Step 2: Training contrastive projection head ===")
    print(f"  Epochs: {args.epochs}, LR: {args.lr}, Temp: {args.temperature}")
    print(f"  Hidden: {args.hidden_dim}, Projection: {args.projection_dim}")

    model, best_loss = train_projection_head(
        embeddings_scaled, labels,
        input_dim=embeddings.shape[1],
        hidden_dim=args.hidden_dim,
        projection_dim=args.projection_dim,
        epochs=args.epochs,
        batch_size=args.contrastive_batch_size,
        lr=args.lr,
        temperature=args.temperature,
        device=device,
    )
    print(f"  Best contrastive loss: {best_loss:.4f}")

    # Step 3: Get projected embeddings
    print(f"\n=== Step 3: Computing projected embeddings ===")
    model.eval()
    dataset = FragmentDataset(embeddings_scaled, labels)
    loader = DataLoader(dataset, batch_size=1024, shuffle=False, num_workers=4)

    all_projected = []
    with torch.no_grad():
        for batch_emb, _ in loader:
            projected = model(batch_emb.to(device))
            all_projected.append(projected.cpu().numpy())
    projected_embeddings = np.concatenate(all_projected, axis=0)

    # Save
    print(f"\n=== Saving results ===")
    # Save projection head
    torch.save({
        'projection_head': model.state_dict(),
        'scaler_mean': scaler.mean_,
        'scaler_scale': scaler.scale_,
        'input_dim': embeddings.shape[1],
        'hidden_dim': args.hidden_dim,
        'projection_dim': args.projection_dim,
        'class_to_id': class_to_id,
    }, str(output_dir / f"contrastive_head_{args.setting}.pt"))

    # Save projected embeddings
    np.save(str(output_dir / f"embeddings_{args.setting}.npy"), projected_embeddings)

    # Save training config
    config = {
        'setting': args.setting,
        'model_path': args.model_path,
        'epochs': args.epochs,
        'lr': args.lr,
        'temperature': args.temperature,
        'hidden_dim': args.hidden_dim,
        'projection_dim': args.projection_dim,
        'best_loss': best_loss,
        'num_fragments': len(fragments),
        'num_classes': len(class_to_id),
        'base_embedding_dim': embeddings.shape[1],
        'projected_dim': args.projection_dim,
    }
    with open(output_dir / f"contrastive_config_{args.setting}.json", 'w') as f:
        json.dump(config, f, indent=2)

    print(f"  Projection head: contrastive_head_{args.setting}.pt")
    print(f"  Projected embeddings: embeddings_{args.setting}.npy ({projected_embeddings.shape})")
    print(f"  Config: contrastive_config_{args.setting}.json")
    print(f"\n=== Done ===")


if __name__ == "__main__":
    main()
