#!/bin/bash
# Read-only post-run audit of actual layer-27/28 NTv2 parameter changes.
# This job never retrains or reads evaluation labels.
#SBATCH --job-name=ntv2_lf_update_audit
#SBATCH --partition=public-short-cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=01:00:00
#SBATCH --output=ntv2_lf_update_audit_%j.out
#SBATCH --error=ntv2_lf_update_audit_%j.err

set -euo pipefail

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark

repo_root="${NTV2_LF_REPO_ROOT:-/home/users/j/jwang/ab-initio-TE}"
audit_source="$repo_root/scripts/experiments/NTV2-LABELFREE-CLUSTER-20260915/audit_last_two_update.py"
state_path="${NTV2_LF_STATE:-/srv/beegfs/scratch/users/j/jwang/NTV2_LABELFREE_CLUSTER_20260915/run_12732191/last_two_ntv2_ssl_state.pt}"
model_path="${NTV2_LF_MODEL:-/home/users/j/jwang/ab-initio-TE/.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species}"
output_path="${NTV2_LF_UPDATE_AUDIT_OUTPUT:-/srv/beegfs/scratch/users/j/jwang/NTV2_LABELFREE_CLUSTER_20260915/run_12732191/weight_update_audit.json}"

if [[ ! -f "$audit_source" || ! -f "$state_path" || ! -f "$model_path/model.safetensors" ]]; then
  echo "required audit source, saved state, or native model is missing" >&2
  exit 2
fi

export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-4}"
export MKL_NUM_THREADS="${SLURM_CPUS_PER_TASK:-4}"
export PYTHONUNBUFFERED=1

python3 "$audit_source" \
  --state "$state_path" \
  --model-dir "$model_path" \
  --output "$output_path"
