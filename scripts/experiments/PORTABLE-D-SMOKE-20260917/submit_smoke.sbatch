#!/usr/bin/env bash
# Generic one-GPU portable-D parity smoke. Supply paths through --export or the
# environment; no cluster-specific root is embedded in this candidate script.
# Required: PORTABLE_ROOT, ORIGINAL_MODEL_DIR, ORIGINAL_CODE_DIR,
# ORIGINAL_HELPER, OUTPUT_DIR.
# Optional: ORIGINAL_TOKENIZER_DIR, DEVICE (cpu/cuda), PYTHON_BIN.
#SBATCH --job-name=portable_d_smoke
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:10:00
#SBATCH --output=portable_d_smoke_%j.out
#SBATCH --error=portable_d_smoke_%j.err

set -euo pipefail
: "${PORTABLE_ROOT:?PORTABLE_ROOT is required}"
: "${ORIGINAL_MODEL_DIR:?ORIGINAL_MODEL_DIR is required}"
: "${ORIGINAL_CODE_DIR:?ORIGINAL_CODE_DIR is required}"
: "${ORIGINAL_HELPER:?ORIGINAL_HELPER is required}"
: "${OUTPUT_DIR:?OUTPUT_DIR is required}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
DEVICE="${DEVICE:-cuda}"
if [[ -n "${CONDA_INIT:-}" ]]; then
  # Optional environment hook; the portable candidate does not assume a
  # particular cluster module or conda installation.
  source "$CONDA_INIT"
  if [[ -n "${CONDA_ENV:-}" ]]; then
    conda activate "$CONDA_ENV"
  fi
fi
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
  --output-dir "$OUTPUT_DIR" \
  --device "$DEVICE" \
  --batch-size "${BATCH_SIZE:-2}" \
  --cpu-threads "${CPU_THREADS:-4}"
