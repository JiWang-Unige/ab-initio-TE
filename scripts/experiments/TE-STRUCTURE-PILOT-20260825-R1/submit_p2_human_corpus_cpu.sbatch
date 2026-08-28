#!/usr/bin/env bash
#SBATCH --job-name=TE_P2_CORPUS
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/outputs/TE-STRUCTURE-PILOT-20260825-R1/p2-corpus-20260828-r2/logs/corpus-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/outputs/TE-STRUCTURE-PILOT-20260825-R1/p2-corpus-20260828-r2/logs/corpus-%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT_ROOT=${ROOT}/scripts/experiments/TE-STRUCTURE-PILOT-20260825-R1
RUN_ROOT=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p2-corpus-20260828-r2
INPUT=${ROOT}/software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/data/human_h0_w8192/train/data.jsonl.gz

mkdir -p "${RUN_ROOT}"
cd "${ROOT}"

python "${SCRIPT_ROOT}/build_annotation_span_corpus.py" \
  --input-jsonl "${INPUT}" \
  --output-jsonl "${RUN_ROOT}/human_chr1_reference_run_masks.jsonl.gz" \
  --metadata "${RUN_ROOT}/human_chr1_reference_run_masks.meta.json" \
  --max-records 3000 \
  >/dev/null

python "${SCRIPT_ROOT}/te_span_mlm.py" audit-corpus \
  --data-jsonl "${RUN_ROOT}/human_chr1_reference_run_masks.jsonl.gz" \
  --records 3000 \
  --out-json "${RUN_ROOT}/sampling_audit.json" \
  >/dev/null
