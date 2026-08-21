#!/usr/bin/env bash
#SBATCH --job-name=hite_iso_r1
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=01:00:00
#SBATCH --output=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/logs/BENCH-HITE-ISOLATED-20260811-R1_slurm_%j.out
#SBATCH --error=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/logs/BENCH-HITE-ISOLATED-20260811-R1_slurm_%j.err

set -eo pipefail

PROJECT_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
EXP_ID=BENCH-HITE-ISOLATED-20260811-R1
OUTPUT_DIR="$PROJECT_ROOT/outputs/$EXP_ID"
mkdir -p "$OUTPUT_DIR"
cd "$PROJECT_ROOT"

environment_failure() {
  rc=$?
  if [[ $rc -ne 0 ]]; then
    printf '%s\n' FAILED_ENVIRONMENT > "$OUTPUT_DIR/STATUS.tmp.$$"
    mv "$OUTPUT_DIR/STATUS.tmp.$$" "$OUTPUT_DIR/STATUS"
  fi
  exit "$rc"
}
trap environment_failure EXIT

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate benchmark_core
trap - EXIT
set -u

python scripts/pre_submit_gate.py --exp-id "$EXP_ID" "$PROJECT_ROOT"
ENV_SNAPSHOT="$OUTPUT_DIR/environment_conda_explicit_${SLURM_JOB_ID}.txt"
ENV_SNAPSHOT_TMP="$ENV_SNAPSHOT.tmp.$$"
conda list --explicit > "$ENV_SNAPSHOT_TMP" || environment_failure
mv "$ENV_SNAPSHOT_TMP" "$ENV_SNAPSHOT" || environment_failure
python scripts/experiments/$EXP_ID/run_hite_isolated.py \
  --root "$PROJECT_ROOT" \
  --config "$PROJECT_ROOT/configs/$EXP_ID.yaml" \
  --environment-snapshot "$ENV_SNAPSHOT"
