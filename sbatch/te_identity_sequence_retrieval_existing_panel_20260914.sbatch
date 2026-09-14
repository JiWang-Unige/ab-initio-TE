#!/bin/bash
# Re-run the light-weight sequence retrieval comparison on an already audited
# exact-repName panel.  This adds the matched single-TRAIN-medoid arm without
# rebuilding the panel or training a model.  The panel manifest must come from
# build_natural_panel.py and must already have passed identity auditing.
#
# Example:
# sbatch --export=ALL,TE_IDENTITY_SOURCE_DIR=/path/src,TE_IDENTITY_MANIFEST=/path/panel/identity_manifest.jsonl,TE_IDENTITY_OUT=/path/out \
#   sbatch/te_identity_sequence_retrieval_existing_panel_20260914.sbatch
#SBATCH --job-name=te_identity_seq
#SBATCH --partition=public-cpu
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=te_identity_seq_%j.out
#SBATCH --error=te_identity_seq_%j.err

set -euo pipefail

source_dir="${TE_IDENTITY_SOURCE_DIR:-$PWD/scripts/experiments/TE-IDENTITY-RETRIEVAL-20260914}"
manifest_path="${TE_IDENTITY_MANIFEST:-}"
output_dir="${TE_IDENTITY_OUT:-}"

if [[ -z "$manifest_path" || -z "$output_dir" ]]; then
  echo "TE_IDENTITY_MANIFEST and TE_IDENTITY_OUT are required" >&2
  exit 2
fi
if [[ ! -f "$manifest_path" ]]; then
  echo "identity manifest does not exist: $manifest_path" >&2
  exit 2
fi
if [[ ! -f "$source_dir/sequence_retrieval.py" ]]; then
  echo "sequence retrieval script does not exist under $source_dir" >&2
  exit 2
fi

python3 "$source_dir/sequence_retrieval.py" \
  --input-manifest "$manifest_path" \
  --out-dir "$output_dir" \
  --kmer-size 6
