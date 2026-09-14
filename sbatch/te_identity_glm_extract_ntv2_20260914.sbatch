#!/bin/bash
# Inference-only native NTv2-500M embedding extraction for the audited panel.
# The model directory is required to be the native multi-species checkpoint;
# no download, fine-tuning, contrastive projection, or split change occurs.
#
# Example:
# sbatch --export=ALL,TE_IDENTITY_SOURCE_DIR=/path/src,TE_IDENTITY_MANIFEST=/path/panel/identity_manifest.jsonl,TE_NTV2_MODEL=/path/.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species,TE_IDENTITY_GLM_OUT=/path/glm \
#   sbatch/te_identity_glm_extract_ntv2_20260914.sbatch
#SBATCH --job-name=te_id_glm_ext
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=te_id_glm_ext_%j.out
#SBATCH --error=te_id_glm_ext_%j.err

set -euo pipefail

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark

source_dir="${TE_IDENTITY_SOURCE_DIR:-$PWD/scripts/experiments/TE-IDENTITY-RETRIEVAL-20260914}"
manifest_path="${TE_IDENTITY_MANIFEST:-}"
model_path="${TE_NTV2_MODEL:-$PWD/.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species}"
output_dir="${TE_IDENTITY_GLM_OUT:-}"

if [[ -z "$manifest_path" || -z "$output_dir" ]]; then
  echo "TE_IDENTITY_MANIFEST and TE_IDENTITY_GLM_OUT are required" >&2
  exit 2
fi
if [[ ! -f "$manifest_path" || ! -d "$model_path" ]]; then
  echo "manifest or native model path does not exist" >&2
  exit 2
fi
if [[ "$(basename "$model_path")" != "nucleotide-transformer-v2-500m-multi-species" ]]; then
  echo "refusing a non-native NTv2 model directory" >&2
  exit 2
fi
if [[ ! -f "$source_dir/extract_glm_embeddings.py" ]]; then
  echo "GLM extraction script does not exist under $source_dir" >&2
  exit 2
fi

export TRANSFORMERS_OFFLINE=1
export HF_HUB_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=1

python3 "$source_dir/extract_glm_embeddings.py" \
  --input-manifest "$manifest_path" \
  --model-path "$model_path" \
  --out-dir "$output_dir" \
  --batch-size 1 \
  --max-token-length 2048
