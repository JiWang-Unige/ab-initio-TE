#!/bin/bash
# CPU-only natural-copy panel builder and annotation-level k-mer retrieval.
# This job is intentionally separate from GLM/HMM training and does not fill
# gaps or alter masks.  It is not submitted automatically.
#
# Example:
# sbatch --export=ALL,TE_PROJECT_ROOT=/path/to/ab-initio-TE,TE_IDENTITY_RUN=/path/run \
#   sbatch/te_identity_panel_and_sequence_retrieval_hg38_20260914.sbatch
#SBATCH --job-name=te_identity_hg38
#SBATCH --partition=public-cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=12G
#SBATCH --time=04:00:00
#SBATCH --output=te_identity_hg38_%j.out
#SBATCH --error=te_identity_hg38_%j.err

set -euo pipefail

project_root="${TE_PROJECT_ROOT:-$PWD}"
run_root="${TE_IDENTITY_RUN:-$project_root/reports/TE-IDENTITY-RETRIEVAL-20260914/hg38_panel_%j}"
te_final_root="${TE_FINAL_ROOT:-/srv/beegfs/scratch/shares/ds4dh/common/TE_benchmark/TE_final}"
consensus_fasta="${TE_CONSENSUS_FASTA:-/srv/beegfs/scratch/users/j/jwang/Pretrain/TE_Contrastive_Clean/data/Dfam38_curated.strict_te_only.fa}"

if [[ ! -d "$project_root" ]]; then
  echo "project root does not exist: $project_root" >&2
  exit 2
fi
if [[ ! -f "$consensus_fasta" ]]; then
  echo "Dfam consensus FASTA does not exist: $consensus_fasta" >&2
  exit 2
fi

source_dir="${TE_IDENTITY_SOURCE_DIR:-$project_root/scripts/experiments/TE-IDENTITY-RETRIEVAL-20260914}"
builder="$source_dir/build_natural_panel.py"
retriever="$source_dir/sequence_retrieval.py"
if [[ ! -f "$builder" || ! -f "$retriever" ]]; then
  echo "identity retrieval scripts are missing under $project_root" >&2
  exit 2
fi

mkdir -p "$run_root"
python3 "$builder" \
  --te-final-root "$te_final_root" \
  --assembly hg38 \
  --species human \
  --chromosomes chr1 chr11 chr13 \
  --consensus-fasta "$consensus_fasta" \
  --out-dir "$run_root/panel" \
  --max-families 40 \
  --target-per-family 40 \
  --min-intervals 30 \
  --max-divergence 20 \
  --min-length 80 \
  --max-length 10000 \
  --kmer-size 7 \
  --homology-jaccard 0.70 \
  --nearby-distance 25

python3 "$retriever" \
  --input-manifest "$run_root/panel/identity_manifest.jsonl" \
  --out-dir "$run_root/retrieval" \
  --kmer-size 6
