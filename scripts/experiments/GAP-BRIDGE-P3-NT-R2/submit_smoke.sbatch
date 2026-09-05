#!/usr/bin/env bash
#SBATCH --job-name=gap-a-r2-smoke
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=01:00:00
#SBATCH --output=logs/gap-a-r2-smoke_%j.out
#SBATCH --error=logs/gap-a-r2-smoke_%j.err
set -euo pipefail
cd /home/users/j/jwang/ab-initio-TE
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TEFM_LOCAL_FILES_ONLY=1
export HF_HOME=/home/users/j/jwang/ab-initio-TE/.cache/huggingface
export PYTHONUNBUFFERED=1 WANDB_DISABLED=true
SCRIPT=scripts/experiments/GAP-BRIDGE-P3-NT-R2/prepare_pair.py
MANIFEST=outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/candidate-manifest-20260902-r1/candidate_manifest.tsv
OUT=outputs/GAP-BRIDGE-P3-NT-R2/smoke-20260905-r1
test ! -e "$OUT"
mkdir "$OUT"
python "$SCRIPT" fit-stats --candidate-manifest "$MANIFEST" --output "$OUT/nt_scalar_stats.json"
python "$SCRIPT" smoke --candidate-manifest "$MANIFEST" \
  --p3-scalar-stats outputs/GAP-BRIDGE-NEURAL-STAGE1-R1/train-20260902-r1/scalar_stats.json \
  --nt-scalar-stats "$OUT/nt_scalar_stats.json" \
  --region outputs/GAP-BRIDGE-PHASE0-R1/full-whole-20260901-r1/chr3/region.jsonl.gz --seqid chr3 \
  --nt-model software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/runs/ntv2_250m_H0_w4096_seed42 \
  --p3-model outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-20260828-r2-12097867/unet \
  --max-candidates 8 --output-dir "$OUT/inference"
printf '%s\n' "$SLURM_JOB_ID" > "$OUT/JOBID"
printf '%s\n' COMPLETED > "$OUT/STATUS"
