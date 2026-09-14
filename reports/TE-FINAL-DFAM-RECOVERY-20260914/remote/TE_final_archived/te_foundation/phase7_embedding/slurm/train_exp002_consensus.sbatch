#!/bin/bash
#SBATCH --job-name=p7_train_cons
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --output=logs/phase7_train_consensus_%j.out
#SBATCH --error=logs/phase7_train_consensus_%j.err

# Phase 7: Train Consensus Experiment
# Experiment 002: Consensus fragments (100bp minimum)

echo "=========================================="
echo "Phase 7: Train Consensus Experiment"
echo "=========================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "GPU: $CUDA_VISIBLE_DEVICES"
echo "Start time: $(date)"
echo ""

# Load modules and activate environment
module load CUDA/12.1.1
source ~/.bashrc
mamba activate te_benchmark

# Change to project directory
cd /srv/beegfs/scratch/shares/ds4dh/common/TE_benchmark/TE_final

# Create logs directory if needed
mkdir -p te_foundation/phase7_embedding/logs

# Check GPU
echo "GPU Information:"
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv
echo ""

# Run training
echo "Running training..."
python -m te_foundation.phase7_embedding.scripts.run_experiment \
    --config te_foundation/phase7_embedding/configs/experiments/exp002_consensus_100bp.yaml \
    --stage train

echo ""
echo "=========================================="
echo "Training completed!"
echo "End time: $(date)"
echo "=========================================="
