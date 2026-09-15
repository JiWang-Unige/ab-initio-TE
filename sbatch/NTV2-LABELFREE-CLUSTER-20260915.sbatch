#!/bin/bash
# Bounded family-label-free NTv2 SSL experiment.  The runner performs the
# new copy/homology/locus split, frozen feature extraction, three projection
# controls, and a real last-two-encoder-block update in one reproducible job.
# It writes only compact reports plus remote cache/checkpoint artifacts.
#SBATCH --job-name=ntv2_lf_cluster
#SBATCH --partition=shared-gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=ntv2_lf_cluster_%j.out
#SBATCH --error=ntv2_lf_cluster_%j.err

set -euo pipefail

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark

repo_root="${NTV2_LF_REPO_ROOT:-/home/users/j/jwang/ab-initio-TE}"
source_path="${NTV2_LF_SOURCE:-$repo_root/scripts/experiments/NTV2-LABELFREE-CLUSTER-20260915/ntv2_label_free_cluster.py}"
manifest_path="${NTV2_LF_MANIFEST:-/srv/beegfs/scratch/users/j/jwang/TE_identity_retrieval_20260914/run_exact/panel/identity_manifest.jsonl}"
prior_query_path="${NTV2_LF_PRIOR_QUERY:-/srv/beegfs/scratch/users/j/jwang/TE_identity_retrieval_improve_20260914/run1/per_query.tsv}"
model_path="${NTV2_LF_MODEL:-/home/users/j/jwang/ab-initio-TE/.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species}"
output_root="${NTV2_LF_OUTPUT_ROOT:-/srv/beegfs/scratch/users/j/jwang/NTV2_LABELFREE_CLUSTER_20260915}"
output_path="${NTV2_LF_OUTPUT:-$output_root/run_${SLURM_JOB_ID}}"

if [[ ! -f "$source_path" || ! -f "$manifest_path" || ! -f "$prior_query_path" || ! -f "$model_path/config.json" || ! -f "$model_path/model.safetensors" ]]; then
  echo "required source, manifest, or native model asset is missing" >&2
  exit 2
fi

export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"
export MKL_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"
export TOKENIZERS_PARALLELISM=false
export PYTHONUNBUFFERED=1

mkdir -p "$output_path"
python3 "$source_path" \
  --manifest "$manifest_path" \
  --model-dir "$model_path" \
  --out-dir "$output_path" \
  --seed 42 \
  --locus-block-bp 50000 \
  --exclude-query-tsv "$prior_query_path" \
  --max-train-view-bp 2048 \
  --max-tokens 2050 \
  --embedding-batch-size 8 \
  --batch-size 4 \
  --max-updates 2000 \
  --temperature 0.07 \
  --head-learning-rate 0.001 \
  --encoder-learning-rate 0.00001 \
  --weight-decay 0.01 \
  --kmer-length 6 \
  --k-grid 20,30,40,50 \
  --kmer-head-hidden 256 \
  --ntv2-head-hidden 256 \
  --capacity-head-hidden 938
