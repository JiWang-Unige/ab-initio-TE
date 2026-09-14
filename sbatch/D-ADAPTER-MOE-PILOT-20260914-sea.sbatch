#!/usr/bin/env bash
# Fixed four-region sea-urchin materialization followed by supervised
# region1+2 TRAIN / region3 CAL / region4 EVAL adaptation.  EVAL is extracted
# only after CAL epoch/threshold selection.  This is not zero-shot.
#
# The six-species main pilot should be submitted first; this job reuses the
# same frozen D checkpoint but has its own finite output directory.

#SBATCH --job-name=d_adapter_sea
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/d_adapter_sea_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/d_adapter_sea_%j.err

set -euo pipefail

ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TRANSFORMERS_OFFLINE=1
export HF_HUB_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1

cd "$ROOT"
CONFIG="$ROOT/configs/D-ADAPTER-MOE-PILOT-20260914.json"
MATERIALIZED="$ROOT/outputs/D-ADAPTER-MOE-PILOT-20260914/sea-materialized"
SOURCE="$ROOT/scripts/experiments/D-ADAPTER-MOE-PILOT-20260914"
OUT="$ROOT/outputs/D-ADAPTER-MOE-PILOT-20260914/sea-seed42/slurm-${SLURM_JOB_ID}"

test -s "$CONFIG"
test -s "$SOURCE/sea_materialize.py"
test -s "$SOURCE/sea_pilot.py"
mkdir -p "$MATERIALIZED" "$OUT"
python3 "$SOURCE/sea_materialize.py" --config "$CONFIG" --output-dir "$MATERIALIZED"
python3 "$SOURCE/sea_pilot.py" --config "$CONFIG" --output-dir "$OUT"
