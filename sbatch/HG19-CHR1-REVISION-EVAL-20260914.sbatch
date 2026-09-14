#!/usr/bin/env bash
#SBATCH --job-name=te-hg19-eval
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=logs/te-hg19-eval_%j.out
#SBATCH --error=logs/te-hg19-eval_%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
DATA_DIR=${1:?prepared data path required}
TRAIN_DIR=${2:?completed training directory required}
MODE=${3:-full}
EXTRA=()
if [[ "$MODE" == smoke ]]; then EXTRA=(--engineering-smoke)
elif [[ "$MODE" != full ]]; then exit 2
fi
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=8
python scripts/experiments/HG19-CHR1-REVISION-20260914/evaluate.py \
  --config configs/HG19-CHR1-REVISION-20260914.json --data "$DATA_DIR" \
  --training "$TRAIN_DIR" --output "outputs/HG19-CHR1-REVISION-20260914/eval-${MODE}-${SLURM_JOB_ID}" "${EXTRA[@]}"
