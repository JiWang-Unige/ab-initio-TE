#!/usr/bin/env bash
#SBATCH --job-name=DNBEGBLD
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=2-00:00:00
#SBATCH --output=logs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/earlgrey_build_%j.out
#SBATCH --error=logs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/earlgrey_build_%j.err

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
CONTAINER_DIR="$RUN_ROOT/containers"
SANDBOX="$CONTAINER_DIR/earlgrey_sandbox"
SIF="$CONTAINER_DIR/earlgrey_configured_dfam39_0-16.sif"
CONFIG_DIR="$CONTAINER_DIR/earlgrey_dfam_config"

mkdir -p "$CONTAINER_DIR" "$CONFIG_DIR"

if [[ -s "$SIF" ]]; then
  echo "EarlGrey configured SIF already exists: $SIF"
  exit 0
fi

if [[ ! -d "$SANDBOX" ]]; then
  singularity build --sandbox "$SANDBOX" docker://tobybaril/earlgrey:latest-nodfam
fi

# First invocation generates configure_dfam39.sh. It may exit non-zero because
# libraries are not configured yet, so do not treat that first call as failure.
set +e
singularity exec -C --bind "$CONFIG_DIR:/data" --writable "$SANDBOX" bash -lc 'cd /data && earlGrey'
set -e

if [[ ! -s "$CONFIG_DIR/configure_dfam39.sh" ]]; then
  echo "configure_dfam39.sh was not generated in $CONFIG_DIR" >&2
  exit 2
fi

# Keep full Dfam 3.9 partitions for broad animal coverage unless the generated
# script has been manually narrowed before this job starts.
grep -n '^curl' "$CONFIG_DIR/configure_dfam39.sh" || true

singularity exec -C --bind "$CONFIG_DIR:/data" --writable "$SANDBOX" bash -lc 'cd /data && bash configure_dfam39.sh'
singularity build "$SIF" "$SANDBOX"

test -s "$SIF"
echo "Built $SIF"
