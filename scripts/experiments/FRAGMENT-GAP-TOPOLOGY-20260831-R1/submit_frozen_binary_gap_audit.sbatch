#!/usr/bin/env bash
# CPU-only descriptive audit of already-frozen binary prediction tracks.
# Null parameters are fitted in-sample and cannot select a rescue rule.
#SBATCH --job-name=TE_gap_topology
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:45:00
#SBATCH --array=0-4%5
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/FRAGMENT-GAP-TOPOLOGY-20260831-R1/frozen-binary-%A_%a.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/FRAGMENT-GAP-TOPOLOGY-20260831-R1/frozen-binary-%A_%a.err

set -euo pipefail

source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark

ROOT=/home/users/j/jwang/ab-initio-TE
: "${ATTEMPT_TAG:?set ATTEMPT_TAG to a unique output-directory name}"
RUN_ROOT=${ROOT}/outputs/FRAGMENT-GAP-TOPOLOGY-20260831-R1/${ATTEMPT_TAG}
SCRIPT_ROOT=${ROOT}/scripts/experiments/FRAGMENT-GAP-TOPOLOGY-20260831-R1
PREP=${SCRIPT_ROOT}/prepare_p3_gap_inputs.py
AUDIT=${SCRIPT_ROOT}/gap_topology_audit.py

HUMAN_ROOT=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/human-d1-12097785
HUMAN_DATA=${ROOT}/software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/data/human_h0_w8192/test/data.jsonl.gz
MOUSE_ROOT=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-x-20260829-x1/mouse
MOUSE_DATA=${ROOT}/software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/data/animal_fine_w8192/mouse/test/data.jsonl.gz
FLY_ROOT=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-x-flybase-shards-20260830-fly4-r1
FLY_TRUTH=${ROOT}/outputs/LEMMI-TE-BENCH-20260824-R1/attempt-12066076/truth.canonical.tsv
FLY_DATA=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-x-20260829-x1/flybase/inference.jsonl.gz
PACKAGES=${ROOT}/docs/experiments/manifests/FBTI-EXTANT-LOCUS-PHASE0-R1-V1.3/packages.tsv

case ${SLURM_ARRAY_TASK_ID} in
  0)
    NAME=human_base
    TRUTH=${HUMAN_ROOT}/truth.canonical.tsv
    PREDICTION=${HUMAN_ROOT}/base_ce.canonical.tsv
    JSONL=${HUMAN_DATA}
    MAX_WINDOWS=1200
    ;;
  1)
    NAME=human_dapt
    TRUTH=${HUMAN_ROOT}/truth.canonical.tsv
    PREDICTION=${HUMAN_ROOT}/dapt_ce.canonical.tsv
    JSONL=${HUMAN_DATA}
    MAX_WINDOWS=1200
    ;;
  2)
    NAME=human_p3
    TRUTH=${HUMAN_ROOT}/truth.canonical.tsv
    PREDICTION=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-20260828-r2-12097867/eval/human.prediction.tsv
    JSONL=${HUMAN_DATA}
    MAX_WINDOWS=1200
    ;;
  3)
    NAME=mouse_p3
    TRUTH=${MOUSE_ROOT}/mouse.truth.tsv
    PREDICTION=${MOUSE_ROOT}/mouse.prediction.tsv
    JSONL=${MOUSE_DATA}
    MAX_WINDOWS=1200
    ;;
  4)
    NAME=fly_p3_positive_only
    TRUTH=${FLY_TRUTH}
    PREDICTION=${FLY_ROOT}/prediction.tsv
    JSONL=${FLY_DATA}
    MAX_WINDOWS=0
    ;;
esac

TASK_ROOT=${RUN_ROOT}/${NAME}
mkdir "${TASK_ROOT}"

EXCLUDE_ARGS=()
TRUTH_ARGS=()
if [[ ${SLURM_ARRAY_TASK_ID} -eq 4 ]]; then
  EXCLUDE=${TASK_ROOT}/fbti_frozen_packages.bed
  awk -F '\t' 'NR > 1 {print $10 "\t" $13 "\t" $14}' "${PACKAGES}" > "${EXCLUDE}"
  EXCLUDE_ARGS=(--exclude-intervals "${EXCLUDE}")
  TRUTH_ARGS=(--union-truth)
fi

python "${PREP}" project-canonical \
  --truth "${TRUTH}" \
  --prediction "${PREDICTION}" \
  --output-dir "${TASK_ROOT}/prep" \
  "${TRUTH_ARGS[@]}" \
  "${EXCLUDE_ARGS[@]}"

WINDOW_ARGS=()
if [[ ${MAX_WINDOWS} -gt 0 ]]; then
  WINDOW_ARGS=(--max-windows "${MAX_WINDOWS}")
fi
python "${PREP}" windows \
  --data-jsonl "${JSONL}" \
  --output "${TASK_ROOT}/windows.tsv" \
  "${WINDOW_ARGS[@]}"

python "${AUDIT}" \
  --truth "${TRUTH}" \
  --prediction "${PREDICTION}" \
  --calibration "${TASK_ROOT}/prep/in_sample.calibration.tsv" \
  --windows "${TASK_ROOT}/windows.tsv" \
  --output-dir "${TASK_ROOT}/audit" \
  "${TRUTH_ARGS[@]}" \
  "${EXCLUDE_ARGS[@]}"

printf 'PASS\n' > "${TASK_ROOT}/STATUS"
