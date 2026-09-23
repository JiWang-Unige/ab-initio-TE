#!/bin/bash
# Fresh mask-only retry after a successful classifier and a failed mask stage.
# The source root is immutable; this job never reruns RepeatClassifier.
#SBATCH --job-name=wg-rm2-mask
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=5-21:06:48
#SBATCH --output=logs/wg-rm2-mask-%j.out
#SBATCH --error=logs/wg-rm2-mask-%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
python3 scripts/experiments/WHOLE-GENOME-BENCHMARK-20260918/recover_rm2_mask_only.py \
  --species "${SPECIES:?set SPECIES}" \
  --mask-source "${MASK_SOURCE:?set MASK_SOURCE}" \
  --output-suffix "${OUTPUT_SUFFIX:-mask-recovery-v2}"
