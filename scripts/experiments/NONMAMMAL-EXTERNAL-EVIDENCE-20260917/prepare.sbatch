#!/usr/bin/env bash
#SBATCH --job-name=d_external_prepare
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:15:00
#SBATCH --output=logs/d_external_prepare_%j.log
set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
SPECIES=${1:?species is required}
python scripts/experiments/NONMAMMAL-EXTERNAL-EVIDENCE-20260917/panel.py prepare \
  --config configs/NONMAMMAL-EXTERNAL-EVIDENCE-20260917.json --species "$SPECIES" \
  --output "outputs/NONMAMMAL-EXTERNAL-EVIDENCE-20260917/$SPECIES/prepared"
