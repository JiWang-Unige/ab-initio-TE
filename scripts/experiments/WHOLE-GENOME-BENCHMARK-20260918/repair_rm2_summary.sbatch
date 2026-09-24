#!/bin/bash
# Rebuild only descriptive RM2 summaries from native annotation.out files.
# Native annotations, status files, and prior summaries are never recomputed.
#SBATCH --job-name=wg-rm2-summary
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=logs/wg-rm2-summary-%j.out
#SBATCH --error=logs/wg-rm2-summary-%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
base=/home/users/j/jwang/ab-initio-TE/outputs/WHOLE-GENOME-BENCHMARK-20260918/native
side=/home/users/j/jwang/ab-initio-TE/reports/WHOLE-GENOME-BENCHMARK-20260918/rm2-summary-repair-20260924
mkdir -p "$side"
python3 scripts/experiments/WHOLE-GENOME-BENCHMARK-20260918/repair_rm2_summary.py \
  --species chicken \
  --native-root "$base/chicken/RM2-mask-recovery-v2" \
  --sidecar "$side/chicken.json"
python3 scripts/experiments/WHOLE-GENOME-BENCHMARK-20260918/repair_rm2_summary.py \
  --species zebrafish \
  --native-root "$base/zebrafish/RM2-mask-recovery-v2" \
  --sidecar "$side/zebrafish.json"
