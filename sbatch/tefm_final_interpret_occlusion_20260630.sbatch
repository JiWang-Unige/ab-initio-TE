#!/usr/bin/env bash
#SBATCH --job-name=TFFIN_OCCL
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=80G
#SBATCH --time=02:00:00
#SBATCH --output=logs/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/occlusion_%j.out
#SBATCH --error=logs/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/occlusion_%j.err

set -euo pipefail
cd /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
mkdir -p logs/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630
eval "$(conda shell.bash hook)"
conda activate te_benchmark
export HF_TOKEN="$(cat /home/users/j/jwang/.cache/huggingface/token 2>/dev/null || true)"
export TEFM_LOCAL_FILES_ONLY=1
python3 pipelines/PIPE-TEFM-FINAL-INTERPRET-20260630/model_occlusion_smoke.py \
  --fragments software_outputs/tefm_anchor/PIPE-TEFM-ANCHOR-20260621/fragments/unknown_highscore_len512.jsonl.gz \
  --pairs reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/matched_control_pairs.tsv \
  --binary-model-dir software_outputs/tefm_repair/PIPE-TEFM-REPAIR-20260618/runs/TFREPAIR_invert_boost_animal_4096_seed42 \
  --sf5-model-dir software_outputs/tefm_extend/PIPE-TEFM-EXTEND-20260620/runs/sf5_base_pretrained/best_model \
  --out-dir reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/occlusion_smoke \
  --chunk 64 \
  --max-unknown 8 \
  --include-unknown-controls
