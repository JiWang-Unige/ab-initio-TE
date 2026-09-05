#!/usr/bin/env bash
#SBATCH --job-name=GAPTAILDEV
#SBATCH --partition=private-teodoro-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:15:00
#SBATCH --output=logs/GAP-BRIDGE-TAIL-DIAGNOSTIC-20260905-%j.out
#SBATCH --error=logs/GAP-BRIDGE-TAIL-DIAGNOSTIC-20260905-%j.err

set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source_base=outputs/GAP-BRIDGE-NEURAL-STAGE1-R1
srun python3 scripts/experiments/GAP-BRIDGE-TAIL-DIAGNOSTIC-20260905/gap_tail_diagnostic.py \
  --manifest "$source_base/candidate-manifest-20260902-r1/candidate_manifest.tsv" \
  --scores "$source_base/score-20260904-r1/chr13_stage1_raw_logits.tsv" \
  --evaluation-summary "$source_base/evaluate-20260905-r1/evaluation_summary.json" \
  --output-dir "${1:-outputs/GAP-BRIDGE-TAIL-DIAGNOSTIC-20260905/dev-r1}"
