#!/usr/bin/env bash
# CPU-only real-sequence parity smoke. All research paths are supplied by the
# submission environment; the release candidate itself contains no Baobab path.
# Required: PORTABLE_ROOT, ORIGINAL_MODEL_DIR, ORIGINAL_CODE_DIR,
# ORIGINAL_HELPER, INPUT_FASTA, OUTPUT_DIR.
# Optional: ORIGINAL_TOKENIZER_DIR, PYTHON_BIN, CPU_THREADS, BATCH_SIZE.
#SBATCH --job-name=portable_d_cpu
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --output=portable_d_cpu_%j.out
#SBATCH --error=portable_d_cpu_%j.err

set -euo pipefail
: "${PORTABLE_ROOT:?PORTABLE_ROOT is required}"
: "${ORIGINAL_MODEL_DIR:?ORIGINAL_MODEL_DIR is required}"
: "${ORIGINAL_CODE_DIR:?ORIGINAL_CODE_DIR is required}"
: "${ORIGINAL_HELPER:?ORIGINAL_HELPER is required}"
: "${INPUT_FASTA:?INPUT_FASTA is required}"
: "${OUTPUT_DIR:?OUTPUT_DIR is required}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
CPU_THREADS="${CPU_THREADS:-16}"
BATCH_SIZE="${BATCH_SIZE:-1}"
if [[ -z "${CONDA_INIT:-}" ]]; then
  CONDA_INIT=/opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
fi
source "$CONDA_INIT"
conda activate "${CONDA_ENV:-te_benchmark}"

TOKENIZER_ARG=()
if [[ -n "${ORIGINAL_TOKENIZER_DIR:-}" ]]; then
  TOKENIZER_ARG=(--original-tokenizer-dir "$ORIGINAL_TOKENIZER_DIR")
fi

"$PYTHON_BIN" "$PORTABLE_ROOT/../scripts/experiments/PORTABLE-D-SMOKE-20260917/smoke_compare.py" \
  --portable-root "$PORTABLE_ROOT" \
  --original-model-dir "$ORIGINAL_MODEL_DIR" \
  "${TOKENIZER_ARG[@]}" \
  --original-code-dir "$ORIGINAL_CODE_DIR" \
  --original-helper "$ORIGINAL_HELPER" \
  --input-fasta "$INPUT_FASTA" \
  --output-dir "$OUTPUT_DIR" \
  --device cpu \
  --batch-size "$BATCH_SIZE" \
  --cpu-threads "$CPU_THREADS"
