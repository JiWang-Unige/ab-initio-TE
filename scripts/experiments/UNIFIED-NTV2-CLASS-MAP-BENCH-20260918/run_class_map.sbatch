#!/usr/bin/env bash
# GPU class-map inference. Submit only after target preparation and the
# validation-selected class checkpoint are complete:
# sbatch --dependency=afterok:<prepare>:<class-checkpoint-tail> \
#   --export=ALL,CLASS_MODEL=/path/to/best_model run_class_map.sbatch
#SBATCH --job-name=classmap-ntv2
#SBATCH --array=0-1%1
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=04:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/classmap-ntv2-%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/classmap-ntv2-%A_%a.err
set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1 TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1
export TEFM_LOCAL_FILES_ONLY=1 WANDB_DISABLED=true PYTHONUNBUFFERED=1
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
export CLASS_MODEL="${CLASS_MODEL:?Set CLASS_MODEL to the validation-selected 12889091 best_model}"
SPECIES=(chicken zebrafish)
SPECIES_ID="${SPECIES[$SLURM_ARRAY_TASK_ID]}"
case "$SPECIES_ID" in
  chicken) ASSEMBLY=galGal6 ;;
  zebrafish) ASSEMBLY=danRer11 ;;
  *) exit 2 ;;
esac
FASTA="$ROOT/outputs/UNIFIED-NTV2-CLASS-MAP-BENCH-20260918/prepared/${SPECIES_ID}.fa"
BASE_MODEL="$ROOT/.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species"
OUT="$ROOT/outputs/UNIFIED-NTV2-CLASS-MAP-BENCH-20260918/ntv2/${SPECIES_ID}"
test -s "$FASTA"
test -d "$CLASS_MODEL"
python3 scripts/experiments/UNIFIED-NTV2-CLASS-MAP-BENCH-20260918/run_class_map.py \
  --fasta "$FASTA" --class-model "$CLASS_MODEL" --base-model "$BASE_MODEL" \
  --species "$SPECIES_ID" --assembly "$ASSEMBLY" --output-dir "$OUT" \
  --batch-size 8 --device cuda
