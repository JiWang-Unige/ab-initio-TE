#!/bin/bash
# Audit-only launcher.  It does not extract FASTA, train a model, or submit a
# dependent job.  Supply an identity-aware manifest explicitly at submission.
# Example: sbatch --export=ALL,TE_IDENTITY_MANIFEST=/path/manifest.tsv,TE_IDENTITY_OUT=/path/out this_file
#SBATCH --job-name=te_identity_audit
#SBATCH --time=00:20:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --output=te_identity_audit_%j.out
#SBATCH --error=te_identity_audit_%j.err

set -euo pipefail

project_root="${TE_PROJECT_ROOT:-$PWD}"
manifest_path="${TE_IDENTITY_MANIFEST:-}"
output_dir="${TE_IDENTITY_OUT:-$project_root/reports/TE-IDENTITY-RETRIEVAL-20260914/slurm_%j}"

if [[ -z "$manifest_path" ]]; then
  echo "TE_IDENTITY_MANIFEST is required; refusing an implicit dataset scan" >&2
  exit 2
fi
if [[ ! -f "$manifest_path" ]]; then
  echo "identity manifest does not exist: $manifest_path" >&2
  exit 2
fi

python3 "$project_root/scripts/experiments/TE-IDENTITY-RETRIEVAL-20260914/identity_retrieval.py" \
  --input-manifest "$manifest_path" \
  --out-dir "$output_dir"
