#!/usr/bin/env bash
# Evaluate the completed P2 CE artifact after Job 12098772 failed on stdout flush.
#SBATCH --job-name=TE_P2_EVAL_R
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=01:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/p2-eval-rescue-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/p2-eval-rescue-%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
DATA_DIR=${ROOT}/software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/data/human_h0_w8192
MODEL_DIR=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p2-ce-rescue-12098772/ce
RUN_ROOT=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p2-eval-rescue-${SLURM_JOB_ID}

mkdir "${RUN_ROOT}"
cd "${ROOT}"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1
export WANDB_DISABLED=true
export TEFM_LOCAL_FILES_ONLY=1
export HF_HOME=${ROOT}/.cache/huggingface

python "${ROOT}/pipelines/PIPE-TEFM-FINAL-20260623/strict_segment_eval.py" \
  --exp-id TE-STRUCTURE-PILOT-20260825-R1-P2-H-R2-EVAL-RESCUE \
  --model-dir "${MODEL_DIR}" \
  --data-jsonl "${DATA_DIR}/test/data.jsonl.gz" \
  --out-tsv "${RUN_ROOT}/human.tsv" \
  --out-json "${RUN_ROOT}/human.json" \
  --window 8192 \
  --stride 8192 \
  --weight-mode triangular \
  --threshold 0.5 \
  --iou-thresholds 0.5 0.7 0.8 0.9 \
  --boundary-tolerances 5 10 25 50 100 \
  --max-windows 1200 \
  > /dev/null 2> "${RUN_ROOT}/eval.stderr"

touch "${RUN_ROOT}/COMPLETED"
