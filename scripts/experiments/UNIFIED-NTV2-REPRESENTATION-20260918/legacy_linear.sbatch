#!/usr/bin/env bash
# CPU-only train-to-test linear/composition diagnostic on completed caches.
#SBATCH --job-name=ntv2-legacy-linear
#SBATCH --partition=debug-cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:15:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/ntv2-legacy-linear-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/ntv2-legacy-linear-%j.err

set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
export MKL_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
export PYTHONUNBUFFERED=1

CODE="$ROOT/scripts/experiments/UNIFIED-NTV2-REPRESENTATION-20260918"
DATA="$ROOT/outputs/SIB-RETREAT-EMBED-REPLICATION-20260917/data_512"
OUT="${LEGACY_LINEAR_OUT:-$ROOT/outputs/UNIFIED-NTV2-REPRESENTATION-20260918/legacy-linear-${SLURM_JOB_ID}.json}"
python3 "$CODE/legacy_binary_linear_diagnostic.py" \
  --data-dir "$DATA" \
  --model "GENERanno_pretrained=$ROOT/outputs/GENERANNO-MATCHED-REPRESENTATION-20260917/run-12854214/features/pretrained" \
  --model "GENERanno_binary_FT=$ROOT/outputs/GENERANNO-MATCHED-REPRESENTATION-20260917/run-12854214/features/binary_finetuned" \
  --model "GENERanno_class_FT=$ROOT/outputs/GENERANNO-MATCHED-REPRESENTATION-20260917/run-12854214/features/multiclass_finetuned" \
  --model "NTv2_pretrained=$ROOT/outputs/EMBEDDING-INTERPRETABILITY-CLOSURE-20260917/run-12849477/features/pretrained" \
  --model "NTv2_binary_D=$ROOT/outputs/EMBEDDING-INTERPRETABILITY-CLOSURE-20260917/run-12849477/features/six_species_D" \
  --out-json "$OUT"
printf 'PASS\n' > "${OUT}.STATUS"
