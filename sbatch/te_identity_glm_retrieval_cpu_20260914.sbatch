#!/bin/bash
# CPU-only scoring of the native NTv2 embedding matrix with the exact same
# identity, prototype IDs, CAL budget, and EVAL rows as the k-mer comparison.
# Submit after successful GPU extraction, for example with
# --dependency=afterok:<embedding_job_id>.
#
# Example:
# sbatch --dependency=afterok:JOBID --export=ALL,TE_IDENTITY_SOURCE_DIR=/path/src,TE_IDENTITY_MANIFEST=/path/panel/identity_manifest.jsonl,TE_IDENTITY_GLM_OUT=/path/glm,TE_IDENTITY_GLM_RETRIEVAL_OUT=/path/glm_retrieval \
#   sbatch/te_identity_glm_retrieval_cpu_20260914.sbatch
#SBATCH --job-name=te_id_glm_ret
#SBATCH --partition=public-longrun-cpu
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=te_id_glm_ret_%j.out
#SBATCH --error=te_id_glm_ret_%j.err

set -euo pipefail

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark

source_dir="${TE_IDENTITY_SOURCE_DIR:-$PWD/scripts/experiments/TE-IDENTITY-RETRIEVAL-20260914}"
manifest_path="${TE_IDENTITY_MANIFEST:-}"
embedding_dir="${TE_IDENTITY_GLM_OUT:-}"
output_dir="${TE_IDENTITY_GLM_RETRIEVAL_OUT:-}"

if [[ -z "$manifest_path" || -z "$embedding_dir" || -z "$output_dir" ]]; then
  echo "TE_IDENTITY_MANIFEST, TE_IDENTITY_GLM_OUT, and TE_IDENTITY_GLM_RETRIEVAL_OUT are required" >&2
  exit 2
fi
for path in "$manifest_path" "$embedding_dir/embeddings.npy" "$embedding_dir/embedding_ids.json" "$embedding_dir/embedding_meta.json"; do
  if [[ ! -f "$path" ]]; then
    echo "required GLM input does not exist: $path" >&2
    exit 2
  fi
done
if [[ ! -f "$source_dir/glm_retrieval.py" ]]; then
  echo "GLM retrieval script does not exist under $source_dir" >&2
  exit 2
fi

python3 "$source_dir/glm_retrieval.py" \
  --input-manifest "$manifest_path" \
  --embeddings "$embedding_dir/embeddings.npy" \
  --embedding-ids "$embedding_dir/embedding_ids.json" \
  --embedding-meta "$embedding_dir/embedding_meta.json" \
  --out-dir "$output_dir"
