#!/usr/bin/env bash
# Twenty-step B1 engineering run used only to estimate full-cohort wall time.
# Pass X0_MATERIALIZATION_ROOT as the completed TRAIN materialization path.
#SBATCH --job-name=te_l1_b1_tput20
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_l1_b1_tput20_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_l1_b1_tput20_%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
: "${X0_MATERIALIZATION_ROOT:?set X0_MATERIALIZATION_ROOT to the completed train materialization directory, including its job id}"

RUN_ROOT="${ROOT}/outputs/CROSS-SPECIES-L1-B1-THROUGHPUT20-20260903/${SLURM_JOB_ID:?SLURM_JOB_ID is required}"
SCRIPT="${ROOT}/scripts/experiments/CROSS-SPECIES-L1-20260903/cross_species_token_task.py"

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
cd "${ROOT}"

python3 "${SCRIPT}" \
  --data-root "${X0_MATERIALIZATION_ROOT}" \
  --output-dir "${RUN_ROOT}" \
  --arm B1 \
  --seed 42 \
  --max-steps 20 \
  --warmup-steps 200
