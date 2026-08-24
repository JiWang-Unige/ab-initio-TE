#!/usr/bin/env bash
# Same-instance Base-CE/DAPT-CE FlyBase screen.  No resource directives:
# callers provide --array=0-1%2, --gres, --cpus-per-task, --mem and --time.
set -Eeuo pipefail
umask 022

PROJECT_ROOT=${PROJECT_ROOT:-/home/users/j/jwang/ab-initio-TE}
CONFIG=${CONFIG:-$PROJECT_ROOT/configs/LEMMI-TE-BENCH-20260824-R1.yaml}
ADAPTER=${ADAPTER:-$PROJECT_ROOT/scripts/experiments/LEMMI-TE-BENCH-20260824-R1/adapter.py}
BRIDGE=${BRIDGE:-$PROJECT_ROOT/pipelines/PIPE-TEFM-FINAL-20260623/infer_fasta_to_bed.py}
OUTPUT_ROOT=${OUTPUT_ROOT:-$PROJECT_ROOT/outputs/LEMMI-TE-BENCH-20260824-R1}
PREFLIGHT_ATTEMPT=${PREFLIGHT_ATTEMPT:-}
TASK=${SLURM_ARRAY_TASK_ID:-}
JOB_ID=${SLURM_JOB_ID:-}
if [[ ! "$JOB_ID" =~ ^[0-9]+$ || "$JOB_ID" == 0 || ! "$TASK" =~ ^[01]$ ]]; then
  echo "BLOCKED: numeric SLURM_JOB_ID and array task 0/1 are required" >&2
  exit 3
fi

ATTEMPT="$OUTPUT_ROOT/fm-claim-attempt-$JOB_ID-$TASK"
mkdir -p "$OUTPUT_ROOT"
if ! mkdir "$ATTEMPT"; then
  echo "BLOCKED: output attempt already exists: $ATTEMPT" >&2
  exit 3
fi
exec >"$ATTEMPT/fm-claim.log" 2>&1
FINAL_STATUS=FAILED
REASON=""
write_status() { printf '%s\n' "$1" >"$ATTEMPT/STATUS.tmp"; mv -f "$ATTEMPT/STATUS.tmp" "$ATTEMPT/STATUS"; }
finish() {
  local rc=$?
  [[ "$FINAL_STATUS" == PASS ]] || printf '%s\n' "${REASON:-fm claim screen failed (rc=$rc)}" >"$ATTEMPT/failure.txt"
  write_status "$FINAL_STATUS"
  exit "$rc"
}
trap finish EXIT
write_status RUNNING
block() { FINAL_STATUS=BLOCKED; REASON=$1; echo "BLOCKED: $1" >&2; exit 3; }
fail() { FINAL_STATUS=FAILED; REASON=$1; echo "FAILED: $1" >&2; exit 2; }

[[ -r "$CONFIG" && -r "$ADAPTER" && -r "$BRIDGE" ]] || block "missing config, adapter, or bridge"
[[ -n "$PREFLIGHT_ATTEMPT" && "$PREFLIGHT_ATTEMPT" == /* ]] || block "absolute PREFLIGHT_ATTEMPT is required"
[[ "$(tr -d '[:space:]' <"$PREFLIGHT_ATTEMPT/STATUS" 2>/dev/null || true)" == PASS ]] || block "preflight is not PASS"
LENGTHS="$PREFLIGHT_ATTEMPT/contig_lengths.json"
TRUTH="$PREFLIGHT_ATTEMPT/truth.canonical.tsv"
[[ -r "$LENGTHS" && -r "$TRUTH" ]] || block "preflight lengths/truth canonical missing"

config_value() { python3 - "$CONFIG" "$1" <<'PY'
import json, sys
value = json.loads(open(sys.argv[1], encoding="utf-8").read())
for part in sys.argv[2].split("."):
    value = value[part]
if not isinstance(value, (str, int, float, bool)):
    raise SystemExit("non-scalar config value")
print(value)
PY
}
[[ "$(config_value frozen_instance.truth_tier)" == T1 ]] || block "configured truth tier is not T1"
ASSEMBLY=$(config_value frozen_instance.assembly_path)
TRUTH_SOURCE=$(config_value frozen_instance.truth_path)
EXPECTED_ASSEMBLY_SHA=$(config_value frozen_instance.assembly_sha256)
EXPECTED_TRUTH_SHA=$(config_value frozen_instance.truth_sha256)
[[ -r "$ASSEMBLY" && -r "$TRUTH_SOURCE" ]] || block "frozen assembly/truth missing"
[[ "$(sha256sum "$ASSEMBLY" | awk '{print $1}')" == "$EXPECTED_ASSEMBLY_SHA" ]] || block "assembly SHA256 mismatch"
[[ "$(sha256sum "$TRUTH_SOURCE" | awk '{print $1}')" == "$EXPECTED_TRUTH_SHA" ]] || block "truth SHA256 mismatch"

case "$TASK" in
  0) MODEL_NAME=base_ce; MODEL_DIR=${BASE_CE_MODEL_DIR:-} ;;
  1) MODEL_NAME=dapt_ce; MODEL_DIR=${DAPT_CE_MODEL_DIR:-} ;;
esac
[[ -n "$MODEL_DIR" && -d "$MODEL_DIR" ]] || block "missing $MODEL_NAME model dir; set ${MODEL_NAME^^}_MODEL_DIR"

PREDICTION="$ATTEMPT/$MODEL_NAME.prediction.bed"
PRED_MANIFEST="$ATTEMPT/$MODEL_NAME.prediction.manifest.json"
python3 "$BRIDGE" --assembly "$ASSEMBLY" --lengths "$LENGTHS" --model-dir "$MODEL_DIR" \
  --output-bed "$PREDICTION" --manifest "$PRED_MANIFEST" --model-name "$MODEL_NAME" \
  --window 8192 --stride 8192 --threshold 0.5 --device auto >"$ATTEMPT/bridge.json"
[[ -s "$PREDICTION" ]] || fail "prediction BED is empty"

CANONICAL="$ATTEMPT/$MODEL_NAME.canonical.tsv"
python3 "$ADAPTER" convert --input "$PREDICTION" --output "$CANONICAL" --format bed
[[ -s "$CANONICAL" ]] || fail "canonical prediction is empty"
RAW_METRICS="$ATTEMPT/metrics.adapter.json"
python3 "$ADAPTER" evaluate --truth "$TRUTH" --prediction "$CANONICAL" --lengths "$LENGTHS" \
  --truth-tier T1 --iou-threshold 0.8 --boundary-tol-bp 5 --overlap-policy flat_union >"$RAW_METRICS"

export MODEL_NAME MODEL_DIR ASSEMBLY LENGTHS TRUTH PREDICTION CANONICAL RAW_METRICS PRED_MANIFEST JOB_ID TASK
python3 - "$ATTEMPT/metrics.json" <<'PY'
import json, os, sys
from pathlib import Path
raw = json.loads(Path(os.environ["RAW_METRICS"]).read_text())
if raw.get("truth_tier") != "T1":
    raise SystemExit("adapter did not return T1 metrics")
payload = {
    "status": "PASS", "profile": "fm_same_instance_claim_screen",
    "method": os.environ["MODEL_NAME"], "claim_eligible": True,
    "claim_scope": "T1_positive_only_recall_boundary_fragmentation",
    "whole_genome_precision_f1_claim": False, "dfam_truth_used": False,
    "slurm_job_id": os.environ["JOB_ID"], "array_task_id": int(os.environ["TASK"]),
    "model_dir": os.environ["MODEL_DIR"], "assembly": os.environ["ASSEMBLY"],
    "contig_lengths": os.environ["LENGTHS"], "truth": os.environ["TRUTH"],
    "prediction_bed": os.environ["PREDICTION"], "prediction_canonical": os.environ["CANONICAL"],
    "prediction_manifest": os.environ["PRED_MANIFEST"], "metrics": raw,
}
Path(sys.argv[1]).write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")
PY
FINAL_STATUS=PASS
echo "PASS: $MODEL_NAME T1 metrics written under $ATTEMPT"
