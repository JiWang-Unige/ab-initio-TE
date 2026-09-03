#!/usr/bin/env bash
# Engineering smoke for exactly the frozen H1/B1/B2 seed-42 set.
# Pass X0_MATERIALIZATION_ROOT as the completed TRAIN materialization path,
# including its materialization job id; primary/replication data are not used.
#SBATCH --job-name=te_l1_seed42_smoke
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --array=0-2%3
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/te_l1_seed42_smoke_%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/te_l1_seed42_smoke_%A_%a.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
: "${X0_MATERIALIZATION_ROOT:?set X0_MATERIALIZATION_ROOT to the completed train materialization directory, including its job id}"

case "${SLURM_ARRAY_TASK_ID:?SLURM_ARRAY_TASK_ID is required}" in
  0) ARM=H1 ;;
  1) ARM=B1 ;;
  2) ARM=B2 ;;
  *) echo "unexpected H1/B1/B2 array index: ${SLURM_ARRAY_TASK_ID}" >&2; exit 2 ;;
esac

RUN_ROOT="${ROOT}/outputs/CROSS-SPECIES-L1-SEED42-SMOKE-20260903/${ARM}/${SLURM_ARRAY_JOB_ID:?SLURM_ARRAY_JOB_ID is required}_${SLURM_ARRAY_TASK_ID}"
SCRIPT="${ROOT}/scripts/experiments/CROSS-SPECIES-L1-20260903/cross_species_token_task.py"

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
cd "${ROOT}"

python3 "${SCRIPT}" \
  --data-root "${X0_MATERIALIZATION_ROOT}" \
  --output-dir "${RUN_ROOT}" \
  --arm "${ARM}" \
  --seed 42 \
  --max-steps 2 \
  --warmup-steps 200
