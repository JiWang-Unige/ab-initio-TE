#!/usr/bin/env bash
# Build matched eight-state labels on the exact D six-species windows.
# This reads the existing binary materialization and comparator BEDs only; it
# does not alter the frozen binary data or create a new sequence split.
#SBATCH --job-name=ntv2-matched-class-prep
#SBATCH --partition=shared-cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/ntv2-matched-class-prep-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/ntv2-matched-class-prep-%j.err

set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
export PYTHONUNBUFFERED=1

CODE="$ROOT/scripts/experiments/UNIFIED-NTV2-REPRESENTATION-20260918"
BINARY_DATA="$ROOT/outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202"
SOURCE_MANIFEST="$ROOT/software_outputs/repeatmasker_dfam/02_ready_by_design/B_animal_production/SPLIT_MANIFEST.tsv"
OUT="${MATCHED_CLASS_OUT:-$ROOT/outputs/UNIFIED-NTV2-REPRESENTATION-20260918/matched_class_data}"
WORM_OVERRIDE="$ROOT/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/materialization/12306000/TRAIN/c_elegans.jsonl.gz"

for required in "$CODE/prepare_matched_class_data.py" "$SOURCE_MANIFEST" "$WORM_OVERRIDE"; do
  [[ -e "$required" ]] || { echo "missing required asset: $required" >&2; exit 2; }
done

python3 "$CODE/prepare_matched_class_data.py" \
  --binary-data-root "$BINARY_DATA" \
  --source-manifest "$SOURCE_MANIFEST" \
  --out-dir "$OUT" \
  --source-override "c_elegans:TRAIN=$WORM_OVERRIDE"

printf '%s\n' "$SLURM_JOB_ID" > "$OUT/PREP_JOBID"
printf '%s\n' 'PASS' > "$OUT/PREP_STATUS"
