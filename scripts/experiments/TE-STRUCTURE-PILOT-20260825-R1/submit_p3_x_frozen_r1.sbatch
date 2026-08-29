#!/usr/bin/env bash
# P3-X frozen R1 transfer: Mouse T0 plus exact FlyBase r6.68 T1.
# Set ATTEMPT_TAG for every submission; each run owns one output directory.
# Create logs/TE-STRUCTURE-PILOT-20260825-R1 before submitting this file.
# FlyBase dummy labels are only an adapter for the legacy P3 evaluator.  The
# FlyBase claim output is produced separately by p3_x_flybase_t1_eval.py and
# contains recall/boundary/fragmentation metrics only.
#SBATCH --job-name=TE_P3_X
#SBATCH --partition=private-teodoro-gpu
#SBATCH --gres=gpu:nvidia_geforce_rtx_3090:1
#SBATCH --exclude=gpu023,gpu024,gpu036,gpu037,gpu038,gpu039,gpu040,gpu041,gpu042,gpu043
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=06:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/p3-x-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/p3-x-%j.err

set -euo pipefail

: "${ATTEMPT_TAG:?set ATTEMPT_TAG before submitting P3-X}"

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT_ROOT=${ROOT}/scripts/experiments/TE-STRUCTURE-PILOT-20260825-R1
MODEL_DIR=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-20260828-r2-12097867/unet
MOUSE_DATA=${ROOT}/software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/data/animal_fine_w8192/mouse/test/data.jsonl.gz
FLYBASE_ASSEMBLY=${ROOT}/data/raw/benchmark_v1/flybase/FB2026_02/dmel_r6.68/dmel-all-chromosome-r6.68.fasta.gz
FLYBASE_TRUTH=${ROOT}/data/raw/benchmark_v1/flybase/FB2026_02/dmel_r6.68/derived/curated_positive_truth_v1/flybase_r668_curated_positive_instances.bed
LEMMI_ATTEMPT=${ROOT}/outputs/LEMMI-TE-BENCH-20260824-R1/attempt-12066076
RUN_ROOT=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-x-${ATTEMPT_TAG}

if [[ -e "${RUN_ROOT}" ]]; then
  echo "refusing to reuse P3-X output directory: ${RUN_ROOT}" >&2
  exit 2
fi
for required_path in \
  "${MODEL_DIR}/model_state.pt" \
  "${MODEL_DIR}/training_meta.json" \
  "${MODEL_DIR}/tokenizer" \
  "${MOUSE_DATA}" \
  "${FLYBASE_ASSEMBLY}" \
  "${FLYBASE_TRUTH}" \
  "${LEMMI_ATTEMPT}/truth.canonical.tsv" \
  "${LEMMI_ATTEMPT}/contig_lengths.json"; do
  if [[ ! -e "${required_path}" ]]; then
    echo "missing frozen P3-X asset: ${required_path}" >&2
    exit 2
  fi
done

mkdir -p "${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1"
mkdir "${RUN_ROOT}"
mkdir -p "${RUN_ROOT}/mouse" "${RUN_ROOT}/flybase"

cd "${ROOT}"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark
export TRANSFORMERS_ALLOW_UNSAFE_TORCH_LOAD=1
export WANDB_DISABLED=true
export TEFM_LOCAL_FILES_ONLY=1
export HF_HOME=${ROOT}/.cache/huggingface

# Mouse: existing binary/unknown comparator labels, 1,200 windows, no tuning.
python "${SCRIPT_ROOT}/te_unet_segmentation.py" evaluate \
  --model-dir "${MODEL_DIR}" \
  --data-jsonl "${MOUSE_DATA}" \
  --prediction-tsv "${RUN_ROOT}/mouse/mouse.prediction.tsv" \
  --truth-tsv "${RUN_ROOT}/mouse/mouse.truth.tsv" \
  --lengths-json "${RUN_ROOT}/mouse/mouse.lengths.json" \
  --metrics-json "${RUN_ROOT}/mouse/mouse.metrics.json" \
  --threshold 0.5 \
  --weight-mode triangular \
  --max-windows 1200

# FlyBase: exact r6.68 assembly, all 1,870 contigs and 18,935 windows.
python "${SCRIPT_ROOT}/p3_x_prepare_inference.py" \
  --assembly "${FLYBASE_ASSEMBLY}" \
  --output-jsonl "${RUN_ROOT}/flybase/inference.jsonl.gz" \
  --manifest "${RUN_ROOT}/flybase/inference.manifest.json"

python - "${RUN_ROOT}/flybase/inference.manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1], encoding="utf-8"))
expected = {"contigs": 1870, "total_bp": 143726002, "windows": 18935}
for key, value in expected.items():
    if manifest.get(key) != value:
        raise SystemExit(f"unexpected exact FlyBase {key}: {manifest.get(key)!r} != {value}")
PY

# The legacy P3 evaluator needs labels to retain predictions.  Its dummy truth
# and metrics are inference diagnostics only; FlyBase claims use the next step.
python "${SCRIPT_ROOT}/te_unet_segmentation.py" evaluate \
  --model-dir "${MODEL_DIR}" \
  --data-jsonl "${RUN_ROOT}/flybase/inference.jsonl.gz" \
  --prediction-tsv "${RUN_ROOT}/flybase/inference.prediction.tsv" \
  --truth-tsv "${RUN_ROOT}/flybase/inference.dummy-truth.tsv" \
  --lengths-json "${RUN_ROOT}/flybase/inference.lengths.json" \
  --metrics-json "${RUN_ROOT}/flybase/inference.dummy-metrics.json" \
  --threshold 0.5 \
  --weight-mode triangular \
  --max-windows 18935

python "${SCRIPT_ROOT}/p3_x_flybase_t1_eval.py" \
  --truth "${LEMMI_ATTEMPT}/truth.canonical.tsv" \
  --prediction "${RUN_ROOT}/flybase/inference.prediction.tsv" \
  --lengths "${LEMMI_ATTEMPT}/contig_lengths.json" \
  --iou-threshold 0.8 \
  --boundary-tolerances 5 25 \
  --out-json "${RUN_ROOT}/flybase/flybase.t1.json"

python - "${RUN_ROOT}/flybase/flybase.t1.json" <<'PY'
import json
import sys

forbidden = ("precision", "f1")
payload = json.load(open(sys.argv[1], encoding="utf-8"))

def walk(value):
    if isinstance(value, dict):
        for key, item in value.items():
            lower = key.lower()
            if any(term in lower for term in forbidden) or lower.endswith(("_fp", "_tn")):
                raise SystemExit(f"forbidden FlyBase T1 metric field: {key}")
            walk(item)
    elif isinstance(value, list):
        for item in value:
            walk(item)

walk(payload)
if payload.get("truth_tier") != "T1":
    raise SystemExit("FlyBase result is not T1")
PY

printf 'PASS\n' > "${RUN_ROOT}/STATUS"
