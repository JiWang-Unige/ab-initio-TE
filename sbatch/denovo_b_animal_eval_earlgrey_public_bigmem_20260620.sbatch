#!/usr/bin/env bash
#SBATCH --job-name=DNBEG_PBM
#SBATCH --partition=public-bigmem
#SBATCH --array=1-8%2
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=4-00:00:00
#SBATCH --output=logs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/earlgrey_public_bigmem_%A_%a.out
#SBATCH --error=logs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/earlgrey_public_bigmem_%A_%a.err

set -euo pipefail

PROJECT_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
CONTAINER_VISIBLE_PROJECT=/home/users/j/jwang/ab-initio-TE
if [[ "$(readlink -f "$CONTAINER_VISIBLE_PROJECT")" != "$PROJECT_ROOT" ]]; then
  echo "Project path alias mismatch: $CONTAINER_VISIBLE_PROJECT does not resolve to $PROJECT_ROOT" >&2
  exit 10
fi

cd "$PROJECT_ROOT"
mkdir -p logs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620

RUN_ROOT="$CONTAINER_VISIBLE_PROJECT/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620"
CONTAINER="$RUN_ROOT/containers/earlgrey_configured_dfam39_0-16.sif"
if [[ ! -s "$CONTAINER" ]]; then
  echo "Missing EarlGrey configured SIF: $CONTAINER" >&2
  exit 11
fi

MATRIX="$RUN_ROOT/manifests/earlgrey_task_matrix.tsv"
srun --cpu-bind=cores scripts/experiments/denovo_benchmark/run_earlgrey_from_matrix.sh "$MATRIX" "$SLURM_ARRAY_TASK_ID"
