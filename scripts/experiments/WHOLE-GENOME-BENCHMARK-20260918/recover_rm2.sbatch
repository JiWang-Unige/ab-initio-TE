#!/bin/bash
# RM2 continuation: terminal discovery products -> fixed classifier -> fixed masker.
# Submit with a species-specific --time equal to seven days minus the parent
# discovery wall, and do not reuse the parent native output directory.
#SBATCH --job-name=wg-rm2-recovery
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=5-20:53:48
#SBATCH --output=logs/wg-rm2-recovery-%j.out
#SBATCH --error=logs/wg-rm2-recovery-%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
python3 scripts/experiments/WHOLE-GENOME-BENCHMARK-20260918/recover_rm2.py \
  --species "${SPECIES:?set SPECIES}" \
  --output-suffix "${OUTPUT_SUFFIX:-recovery-v2}"
