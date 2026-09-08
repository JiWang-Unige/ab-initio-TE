#!/usr/bin/env bash
#SBATCH --job-name=gap-a-coverage
#SBATCH --partition=private-teodoro-gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=02:00:00
#SBATCH --output=logs/gap-a-coverage_%j.out
#SBATCH --error=logs/gap-a-coverage_%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false
OUT=outputs/GAP-BRIDGE-A-COVERAGE-20260906-R1/audit-20260906-r1
test ! -e "$OUT"
python -m unittest discover -s scripts/experiments/GAP-BRIDGE-A-COVERAGE-20260906-R1 -p 'test_*.py' -v
python scripts/experiments/GAP-BRIDGE-A-COVERAGE-20260906-R1/audit_coverage.py \
  --candidate-manifest outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/candidate-manifest-20260902-r1/candidate_manifest.tsv \
  --region-root outputs/GAP-BRIDGE-PHASE0-R1/full-whole-20260901-r1 \
  --nt-model software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/runs/ntv2_250m_H0_w4096_seed42 \
  --output "$OUT"
printf '%s\n' "$SLURM_JOB_ID" > "$OUT/JOBID"
printf '%s\n' COMPLETED > "$OUT/STATUS"
