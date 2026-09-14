#!/usr/bin/env bash
#SBATCH --job-name=p3-base-mask-score-r1
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=logs/p3-base-mask-score-r1_%j.out
#SBATCH --error=logs/p3-base-mask-score-r1_%j.err
set -euo pipefail

cd /home/users/j/jwang/ab-initio-TE
TASK_ROOT=$(pwd -P)
CFG=configs/P3-TIBERIUS-BASE-MASK-20260911-R1.json
RUN=full
REVISION=r1
SCRIPT=scripts/experiments/P3-TIBERIUS-BASE-MASK-20260911-R1/base_mask.py
OUT=outputs/P3-TIBERIUS-BASE-MASK-20260911-R1/${RUN}-${REVISION}

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
test "$(< "$OUT/STATUS")" = FULL_COMPLETED_NO_SCORE
python "$SCRIPT" score --config "$CFG" --run "$RUN" --revision "$REVISION"
