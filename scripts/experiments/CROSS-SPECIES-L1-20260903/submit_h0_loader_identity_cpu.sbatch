#!/usr/bin/env bash
# CPU FP32 identity gate for the direct H0 checkpoint and continuation loader.
# Submit only after the smart-sbatch policy gate has passed.
#SBATCH --job-name=te_l1_h0_identity
#SBATCH --partition=private-teodoro-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_l1_h0_identity_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_l1_h0_identity_%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
: "${X0_MATERIALIZATION_ROOT:?set X0_MATERIALIZATION_ROOT to the completed train materialization directory, including its job id}"
RUN_ROOT="${ROOT}/outputs/CROSS-SPECIES-L1-H0-IDENTITY-20260903/${SLURM_JOB_ID:?SLURM_JOB_ID is required}"
SCRIPT="${ROOT}/scripts/experiments/CROSS-SPECIES-L1-20260903/h0_loader_identity.py"

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
cd "${ROOT}"

python3 "${SCRIPT}" \
  --cal-jsonl "${X0_MATERIALIZATION_ROOT}/CAL/human.jsonl.gz" \
  --output-json "${RUN_ROOT}/identity.json"
