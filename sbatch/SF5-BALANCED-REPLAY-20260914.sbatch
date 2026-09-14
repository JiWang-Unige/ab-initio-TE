#!/usr/bin/env bash
# Inference-only replay of a fixed subset of the already scored SF5 prefix.
# No training command is invoked.  Raw per-position predictions remain on
# Baobab; only compact metrics are copied back to the repository.
#SBATCH --job-name=sf5-balanced-replay
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/sf5_balanced_replay_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/sf5_balanced_replay_%j.err
set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
DATA_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
CONFIG="$ROOT/configs/SF5-BALANCED-REPLAY-20260914.json"
SCRIPT="$ROOT/scripts/experiments/SF5-BALANCED-REPLAY-20260914/replay.py"
OUT="$DATA_ROOT/outputs/SF5-BALANCED-REPLAY-20260914/replay-${SLURM_JOB_ID}"

mkdir -p "$ROOT/logs"
for path in "$CONFIG" "$SCRIPT"; do
    test -s "$path"
done
if [[ -e "$OUT" ]]; then
    echo "refusing to overwrite existing output: $OUT" >&2
    exit 2
fi

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export MKL_NUM_THREADS=4
cd "$ROOT"

python3 "$SCRIPT" \
    --config "$CONFIG" \
    --project-root "$ROOT" \
    --output-dir "$OUT" \
    --job-id "$SLURM_JOB_ID"
