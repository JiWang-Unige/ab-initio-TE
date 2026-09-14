#!/bin/bash
# Bounded CPU k-mer-length and frozen-NTv2 projection study.
# The embedding matrix and identity manifest must already exist; this job
# does not download data, retrain the NTv2 backbone, or alter the split.
#
# Example:
# sbatch --export=ALL,TE_IDENTITY_IMPROVE_SOURCE_DIR=/path/improve,TE_IDENTITY_SUPPORT_DIR=/path/identity-src,TE_IDENTITY_MANIFEST=/path/panel/identity_manifest.jsonl,TE_IDENTITY_EMBEDDINGS=/path/embeddings.npy,TE_IDENTITY_EMBEDDING_IDS=/path/embedding_ids.json,TE_IDENTITY_EMBEDDING_META=/path/embedding_meta.json,TE_IDENTITY_IMPROVE_OUT=/path/output \
#   sbatch/te_identity_retrieval_improve_cpu_20260914.sbatch
#SBATCH --job-name=te_id_improve
#SBATCH --partition=public-longrun-cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=te_id_improve_%j.out
#SBATCH --error=te_id_improve_%j.err

set -euo pipefail

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark

source_dir="${TE_IDENTITY_IMPROVE_SOURCE_DIR:-$PWD/scripts/experiments/TE-IDENTITY-RETRIEVAL-IMPROVE-20260914}"
support_dir="${TE_IDENTITY_SUPPORT_DIR:-$PWD/scripts/experiments/TE-IDENTITY-RETRIEVAL-20260914}"
manifest_path="${TE_IDENTITY_MANIFEST:-}"
embedding_path="${TE_IDENTITY_EMBEDDINGS:-}"
embedding_ids_path="${TE_IDENTITY_EMBEDDING_IDS:-}"
embedding_meta_path="${TE_IDENTITY_EMBEDDING_META:-}"
output_dir="${TE_IDENTITY_IMPROVE_OUT:-}"

if [[ -z "$manifest_path" || -z "$embedding_path" || -z "$embedding_ids_path" || -z "$embedding_meta_path" || -z "$output_dir" ]]; then
  echo "all identity manifest, embedding, and output paths are required" >&2
  exit 2
fi
for path in "$manifest_path" "$embedding_path" "$embedding_ids_path" "$embedding_meta_path"; do
  if [[ ! -f "$path" ]]; then
    echo "required input does not exist: $path" >&2
    exit 2
  fi
done
if [[ ! -f "$source_dir/improve_retrieval.py" || ! -f "$support_dir/identity_retrieval.py" || ! -f "$support_dir/sequence_retrieval.py" ]]; then
  echo "improvement or identity support source is incomplete" >&2
  exit 2
fi

export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
export TOKENIZERS_PARALLELISM=false

python3 "$source_dir/improve_retrieval.py" \
  --input-manifest "$manifest_path" \
  --embeddings "$embedding_path" \
  --embedding-ids "$embedding_ids_path" \
  --embedding-meta "$embedding_meta_path" \
  --support-source-dir "$support_dir" \
  --out-dir "$output_dir" \
  --epochs 50 \
  --projection-dim 128 \
  --temperature 0.1 \
  --learning-rate 0.001 \
  --weight-decay 0.0001
