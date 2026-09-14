#!/bin/bash
#SBATCH --job-name=p7_prep_cons
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=logs/phase7_prep_consensus_%j.out
#SBATCH --error=logs/phase7_prep_consensus_%j.err

# Phase 7: Prepare Consensus TE Data
# Experiment 002: Consensus fragments (100bp minimum)

echo "=========================================="
echo "Phase 7: Prepare Consensus TE Data"
echo "=========================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "Start time: $(date)"
echo ""

# Load modules and activate environment
module load GCCcore/12.3.0
source ~/.bashrc
mamba activate te_benchmark

# Change to project directory
cd /srv/beegfs/scratch/shares/ds4dh/common/TE_benchmark/TE_final

# Create logs directory if needed
mkdir -p te_foundation/phase7_embedding/logs

# Run data preparation
echo "Running data preparation..."
python -m te_foundation.phase7_embedding.scripts.run_experiment \
    --config te_foundation/phase7_embedding/configs/experiments/exp002_consensus_100bp.yaml \
    --stage prepare

echo ""
echo "=========================================="
echo "Data preparation completed!"
echo "End time: $(date)"
echo "=========================================="
