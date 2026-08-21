#!/usr/bin/env bash
#SBATCH --job-name=DNBTOOLS_PC
#SBATCH --partition=public-cpu
#SBATCH --array=1,3,6-17,19-20,22-24%6
#SBATCH --cpus-per-task=16
#SBATCH --mem=80G
#SBATCH --time=4-00:00:00
#SBATCH --output=logs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/tool_publiccpu_rerun_%A_%a.out
#SBATCH --error=logs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/tool_publiccpu_rerun_%A_%a.err

set -euo pipefail

PROJECT_ROOT=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE
CONTAINER_VISIBLE_PROJECT=/home/users/j/jwang/ab-initio-TE
if [[ "$(readlink -f "$CONTAINER_VISIBLE_PROJECT")" != "$PROJECT_ROOT" ]]; then
  echo "Project path alias mismatch: $CONTAINER_VISIBLE_PROJECT does not resolve to $PROJECT_ROOT" >&2
  exit 10
fi

cd "$PROJECT_ROOT"
mkdir -p logs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620

MATRIX="$CONTAINER_VISIBLE_PROJECT/software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/manifests/tool_task_matrix_publiccpu_rerun_20260621.tsv"
srun --cpu-bind=cores scripts/experiments/denovo_benchmark/run_task_from_matrix.sh "$MATRIX" "$SLURM_ARRAY_TASK_ID" tool
