#!/usr/bin/env python3
"""
Phase 7 Experiment Runner

Unified entry point for running TE embedding experiments.
Supports data preparation, training, and evaluation stages.

Usage:
    python run_experiment.py --config configs/experiments/exp001_real_100bp.yaml --stage prepare
    python run_experiment.py --config configs/experiments/exp001_real_100bp.yaml --stage train
    python run_experiment.py --config configs/experiments/exp001_real_100bp.yaml --stage evaluate
    python run_experiment.py --config configs/experiments/exp001_real_100bp.yaml --stage all
"""

import os
import sys
import argparse
import yaml
import json
from pathlib import Path
from typing import Dict

# Add parent directory to path
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR.parent))


def load_config(config_path: str) -> Dict:
    """Load and merge configuration files"""
    config_path = Path(config_path)

    if not config_path.exists():
        # Try relative to project directory
        config_path = PROJECT_DIR / config_path

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Load base config if specified
    base_config_path = PROJECT_DIR / "configs" / "base.yaml"
    if base_config_path.exists():
        with open(base_config_path, 'r') as f:
            base_config = yaml.safe_load(f)

        # Deep merge: experiment config overrides base config
        config = deep_merge(base_config, config)

    # Resolve relative paths
    if 'paths' in config:
        for key, value in config['paths'].items():
            if isinstance(value, str) and not value.startswith('/'):
                config['paths'][key] = str(PROJECT_DIR / value)

    return config


def deep_merge(base: Dict, override: Dict) -> Dict:
    """Deep merge two dictionaries"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def run_prepare(config: Dict):
    """Run data preparation stage"""
    from data_sources import RealGenomeDataSource, ConsensusDataSource, HardNegativeDataSource

    print("\n" + "="*60)
    print("Stage: Data Preparation")
    print("="*60)

    data_config = config.get('data', {})
    genome_config = config.get('genome', {})
    paths_config = config.get('paths', {})

    source_type = data_config.get('source', 'real_genome')
    data_dir = Path(paths_config.get('data_dir', 'data'))
    data_dir.mkdir(parents=True, exist_ok=True)

    print(f"  Source type: {source_type}")
    print(f"  Output dir: {data_dir}")

    seed = config.get('training', {}).get('seed', 42)

    # Initialize data source
    if source_type == 'real_genome':
        data_source = RealGenomeDataSource(
            config=data_config,
            genome_fasta=genome_config.get('fasta'),
            annotation_bed=genome_config.get('annotation'),
            chromosomes=data_config.get('chromosomes', ['chr1']),
            seed=seed
        )
    elif source_type == 'consensus':
        data_source = ConsensusDataSource(
            config=data_config,
            consensus_fasta=genome_config.get('consensus'),
            balance_classes=data_config.get('balance_classes', True),
            max_sequences_per_class=data_config.get('max_sequences_per_class'),
            seed=seed
        )
    elif source_type == 'hard_negative':
        # Hard Negative Mining: wrap RealGenomeDataSource
        hard_neg_config = data_config.get('hard_negative', {})
        base_source = RealGenomeDataSource(
            config=data_config,
            genome_fasta=genome_config.get('fasta'),
            annotation_bed=genome_config.get('annotation'),
            chromosomes=data_config.get('chromosomes', ['chr1']),
            seed=seed
        )
        data_source = HardNegativeDataSource(
            config=data_config,
            base_source=base_source,
            hard_negative_ratio=hard_neg_config.get('hard_negative_ratio', 0.3),
            family_positive_ratio=hard_neg_config.get('family_positive_ratio', 0.5),
            min_family_samples=hard_neg_config.get('min_family_samples', 10),
            seed=seed
        )
    else:
        raise ValueError(f"Unknown source type: {source_type}")

    # Get TE sequences
    sequences = data_source.get_te_sequences()

    if not sequences:
        raise RuntimeError("No sequences extracted!")

    # Split sequences into train/val/test sets
    # This ensures no sequence appears in multiple sets (avoiding data leakage)
    import random
    random.seed(config.get('training', {}).get('seed', 42))
    random.shuffle(sequences)

    # Split ratios: 70% train, 15% val, 15% test
    n_sequences = len(sequences)
    n_train = int(n_sequences * 0.7)
    n_val = int(n_sequences * 0.15)

    train_sequences = sequences[:n_train]
    val_sequences = sequences[n_train:n_train + n_val]
    test_sequences = sequences[n_train + n_val:]

    print(f"\n  Sequence split:")
    print(f"    Train: {len(train_sequences):,} sequences")
    print(f"    Val: {len(val_sequences):,} sequences")
    print(f"    Test: {len(test_sequences):,} sequences")

    # Save all sequences for embedding extraction (but mark split)
    for seq in train_sequences:
        seq.metadata['split'] = 'train'
    for seq in val_sequences:
        seq.metadata['split'] = 'val'
    for seq in test_sequences:
        seq.metadata['split'] = 'test'

    data_source.save_sequences_to_csv(
        sequences,  # Save all but with split metadata
        str(data_dir / "sequences.csv")
    )

    # Save split sequences separately
    data_source.save_sequences_to_csv(train_sequences, str(data_dir / "train_sequences.csv"))
    data_source.save_sequences_to_csv(val_sequences, str(data_dir / "val_sequences.csv"))
    data_source.save_sequences_to_csv(test_sequences, str(data_dir / "test_sequences.csv"))

    # Generate contrastive pairs from separate sets
    fragment_range = (
        data_config.get('fragment_size_min', 100),
        data_config.get('fragment_size_max', 300)
    )

    train_pairs = data_source.generate_contrastive_pairs(
        train_sequences,  # Use only train sequences
        num_pairs=data_config.get('num_train_pairs', 10000),
        positive_ratio=data_config.get('positive_ratio', 0.5),
        fragment_size_range=fragment_range
    )

    val_pairs = data_source.generate_contrastive_pairs(
        val_sequences,  # Use only val sequences
        num_pairs=data_config.get('num_val_pairs', 1000),
        positive_ratio=data_config.get('positive_ratio', 0.5),
        fragment_size_range=fragment_range
    )

    # Save pairs
    data_source.save_pairs_to_csv(train_pairs, str(data_dir / "train.csv"))
    data_source.save_pairs_to_csv(val_pairs, str(data_dir / "val.csv"))

    # Save metadata
    metadata = data_source.get_metadata()
    metadata['experiment'] = config.get('experiment', {})
    metadata['num_sequences'] = len(sequences)
    metadata['num_train_pairs'] = len(train_pairs)
    metadata['num_val_pairs'] = len(val_pairs)

    data_source.save_metadata(metadata, str(data_dir / "metadata.json"))

    # Analyze length distribution
    if hasattr(data_source, 'analyze_length_distribution'):
        data_source.analyze_length_distribution(
            sequences,
            str(data_dir / "length_distribution.json")
        )

    print(f"\n  Data preparation completed!")
    print(f"  Sequences: {len(sequences):,}")
    print(f"  Train pairs: {len(train_pairs):,}")
    print(f"  Val pairs: {len(val_pairs):,}")


def run_train(config: Dict):
    """Run training stage"""
    import torch
    from torch.utils.data import DataLoader
    from torch.utils.data.distributed import DistributedSampler
    from torch.optim import AdamW
    from torch.optim.lr_scheduler import CosineAnnealingLR
    from torch.cuda.amp import GradScaler

    from models.te_generanno import TE_GENERanno
    from training.train_contrastive import (
        ContrastiveDataset, ContrastiveTrainer,
        collate_fn, set_seed, setup_distributed, cleanup_distributed
    )
    from training.loss import HardConLoss

    print("\n" + "="*60)
    print("Stage: Training")
    print("="*60)

    # Setup distributed
    rank, world_size, local_rank = setup_distributed()
    is_main_process = (rank == 0)

    # Extract config
    model_config = config.get('model', {})
    train_config = config.get('training', {})
    paths_config = config.get('paths', {})

    # Mixed precision settings
    use_bf16 = train_config.get('bf16', False)
    use_fp16 = train_config.get('fp16', False)

    # Set seed
    set_seed(train_config.get('seed', 42) + rank)

    # Device
    if world_size > 1:
        device = f'cuda:{local_rank}'
    else:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'

    if is_main_process:
        print(f"  Model: {model_config.get('name', 'GENERanno')}")
        print(f"  Device: {device}")
        print(f"  World size: {world_size}")
        print(f"  Epochs: {train_config.get('num_epochs', 5)}")
        print(f"  Batch size: {train_config.get('batch_size', 16)}")
        print(f"  Mixed precision: bf16={use_bf16}, fp16={use_fp16}")

    # Load data
    data_dir = Path(paths_config.get('data_dir'))
    train_dataset = ContrastiveDataset(str(data_dir / "train.csv"))
    val_dataset = ContrastiveDataset(str(data_dir / "val.csv"))

    # Initialize model
    model = TE_GENERanno(
        model_name_or_path=model_config.get('path'),
        feat_dim=model_config.get('feat_dim', 128),
        max_length=model_config.get('max_length', 512),
        pooling=model_config.get('pooling', 'mean')
    )
    model = model.to(device)

    # Wrap with DDP
    if world_size > 1:
        from torch.nn.parallel import DistributedDataParallel as DDP
        model = DDP(model, device_ids=[local_rank], output_device=local_rank)

    # Get tokenizer
    tokenizer = model.module.tokenizer if hasattr(model, 'module') else model.tokenizer

    # Create samplers
    train_sampler = DistributedSampler(train_dataset, num_replicas=world_size, rank=rank, shuffle=True) if world_size > 1 else None
    val_sampler = DistributedSampler(val_dataset, num_replicas=world_size, rank=rank, shuffle=False) if world_size > 1 else None

    # Create data loaders
    max_length = model_config.get('max_length', 512)
    train_loader = DataLoader(
        train_dataset,
        batch_size=train_config.get('batch_size', 16),
        shuffle=(train_sampler is None),
        sampler=train_sampler,
        num_workers=train_config.get('num_workers', 4),
        collate_fn=lambda batch: collate_fn(batch, tokenizer, max_length),
        pin_memory=True
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=train_config.get('batch_size', 16),
        shuffle=False,
        sampler=val_sampler,
        num_workers=train_config.get('num_workers', 4),
        collate_fn=lambda batch: collate_fn(batch, tokenizer, max_length),
        pin_memory=True
    )

    # Loss function
    criterion = HardConLoss(
        temperature=train_config.get('temperature', 0.05),
        margin=train_config.get('margin', 0.5)
    )

    # Optimizer
    actual_model = model.module if hasattr(model, 'module') else model
    optimizer = AdamW([
        {'params': actual_model.generanno.parameters(), 'lr': train_config.get('learning_rate_backbone', 3e-6)},
        {'params': actual_model.contrast_head.parameters(), 'lr': train_config.get('learning_rate_head', 3e-4)}
    ], weight_decay=train_config.get('weight_decay', 0.01))

    # Scheduler
    scheduler = CosineAnnealingLR(
        optimizer,
        T_max=train_config.get('num_epochs', 5),
        eta_min=1e-7
    )

    # Trainer with mixed precision support
    output_dir = paths_config.get('checkpoint_dir', paths_config.get('output_dir'))
    trainer = ContrastiveTrainer(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        criterion=criterion,
        optimizer=optimizer,
        scheduler=scheduler,
        device=device,
        output_dir=output_dir,
        max_length=max_length,
        is_main_process=is_main_process,
        rank=rank,
        world_size=world_size,
        use_bf16=use_bf16,
        use_fp16=use_fp16
    )

    # Train
    trainer.train(num_epochs=train_config.get('num_epochs', 5))

    # Cleanup
    cleanup_distributed()


def run_evaluate(config: Dict):
    """Run evaluation stage"""
    import torch
    import numpy as np
    import pandas as pd

    from evaluation.extract_embeddings import EmbeddingExtractor
    from evaluation.clustering import ClusteringEvaluator

    print("\n" + "="*60)
    print("Stage: Evaluation")
    print("="*60)

    paths_config = config.get('paths', {})
    eval_config = config.get('evaluation', {})

    checkpoint_dir = Path(paths_config.get('checkpoint_dir', paths_config.get('output_dir')))
    data_dir = Path(paths_config.get('data_dir'))
    embedding_dir = Path(paths_config.get('embedding_dir', checkpoint_dir / 'embeddings'))
    clustering_dir = Path(paths_config.get('clustering_dir', checkpoint_dir / 'clustering'))

    embedding_dir.mkdir(parents=True, exist_ok=True)
    clustering_dir.mkdir(parents=True, exist_ok=True)

    # Auto-detect device (CUDA if available, else CPU)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"  Device: {device}")

    # Load best checkpoint
    best_checkpoint = checkpoint_dir / "checkpoint-best"
    if not best_checkpoint.exists():
        # Try to find latest checkpoint
        checkpoints = list(checkpoint_dir.glob("checkpoint-epoch*"))
        if checkpoints:
            best_checkpoint = sorted(checkpoints)[-1]
        else:
            raise FileNotFoundError(f"No checkpoints found in {checkpoint_dir}")

    print(f"  Loading model from: {best_checkpoint}")

    # Extract embeddings
    extractor = EmbeddingExtractor.from_checkpoint(
        str(best_checkpoint),
        device=device,  # Use auto-detected device
        max_length=config.get('model', {}).get('max_length', 512),
        batch_size=32 if device == 'cuda' else 8  # Smaller batch for CPU
    )

    # Load TEST sequences for evaluation (not train/val to avoid leakage)
    test_sequences_file = data_dir / "test_sequences.csv"
    if test_sequences_file.exists():
        sequences_file = test_sequences_file
        print(f"  Using TEST split for evaluation (no data leakage)")
    else:
        # Fallback to all sequences if split not available
        sequences_file = data_dir / "sequences.csv"
        print(f"  WARNING: Using all sequences (test split not found)")

    print(f"  Loading sequences from: {sequences_file}")

    embeddings, metadata_df = extractor.extract_from_csv(
        str(sequences_file),
        sequence_column='sequence',
        id_column='id',
        output_file=str(embedding_dir / "embeddings.npy")
    )

    print(f"  Extracted embeddings shape: {embeddings.shape}")

    # Run clustering evaluation
    true_labels = metadata_df['te_class'].values

    evaluator = ClusteringEvaluator(
        embeddings=embeddings,
        true_labels=true_labels
    )

    # Run all clustering methods
    num_clusters = eval_config.get('num_clusters', [4])[0]
    results = evaluator.run_all_methods(
        num_clusters=num_clusters,
        output_dir=str(clustering_dir),
        hdbscan_min_cluster_size=eval_config.get('hdbscan_min_cluster_size', 100),
        hdbscan_min_samples=eval_config.get('hdbscan_min_samples', 50)
    )

    print(f"\n  Evaluation completed!")
    print(f"  Results saved to: {clustering_dir}")


def main():
    parser = argparse.ArgumentParser(description='Phase 7 Experiment Runner')
    parser.add_argument('--config', type=str, required=True,
                        help='Path to experiment config file')
    parser.add_argument('--stage', type=str, required=True,
                        choices=['prepare', 'train', 'evaluate', 'all'],
                        help='Stage to run')
    parser.add_argument('--gpu', type=int, default=None,
                        help='GPU device ID')

    args = parser.parse_args()

    # Set GPU if specified
    if args.gpu is not None:
        os.environ['CUDA_VISIBLE_DEVICES'] = str(args.gpu)

    # Load config
    config = load_config(args.config)

    print("="*60)
    print(f"Phase 7 Experiment: {config.get('experiment', {}).get('name', 'unknown')}")
    print("="*60)
    print(f"Config: {args.config}")
    print(f"Stage: {args.stage}")

    # Run stages
    if args.stage == 'prepare' or args.stage == 'all':
        run_prepare(config)

    if args.stage == 'train' or args.stage == 'all':
        run_train(config)

    if args.stage == 'evaluate' or args.stage == 'all':
        run_evaluate(config)

    print("\n" + "="*60)
    print("Experiment completed!")
    print("="*60)


if __name__ == '__main__':
    main()
