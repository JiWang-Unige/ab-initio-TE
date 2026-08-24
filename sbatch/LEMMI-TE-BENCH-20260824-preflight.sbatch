#!/usr/bin/env bash
# CPU-only frozen-input preflight. Resource flags are supplied by sbatch.
# This script never launches a caller and never submits a nested job.
set -Eeuo pipefail
umask 022

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=${PROJECT_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}
CONFIG=${CONFIG:-$PROJECT_ROOT/configs/LEMMI-TE-BENCH-20260824-R1.yaml}
ADAPTER=${ADAPTER:-$PROJECT_ROOT/scripts/experiments/LEMMI-TE-BENCH-20260824-R1/adapter.py}
OUTPUT_ROOT=${OUTPUT_ROOT:-$PROJECT_ROOT/outputs/LEMMI-TE-BENCH-20260824-R1}

JOB_ID=${SLURM_JOB_ID:-}
if [[ ! "$JOB_ID" =~ ^[0-9]+$ || "$JOB_ID" == 0 ]]; then
  echo "BLOCKED: must run inside an allocation with a numeric SLURM_JOB_ID" >&2
  exit 3
fi

ATTEMPT="$OUTPUT_ROOT/attempt-$JOB_ID"
mkdir -p "$OUTPUT_ROOT"
if ! mkdir "$ATTEMPT"; then
  echo "BLOCKED: output attempt already exists: $ATTEMPT" >&2
  exit 3
fi
LOG="$ATTEMPT/preflight.log"
exec >"$LOG" 2>&1

FINAL_STATUS=FAILED
FAIL_REASON=""
BLOCK_REASON=""
write_status() {
  local value=$1
  printf '%s\n' "$value" >"$ATTEMPT/STATUS.tmp"
  mv -f "$ATTEMPT/STATUS.tmp" "$ATTEMPT/STATUS"
}
on_exit() {
  local rc=$?
  if [[ "$FINAL_STATUS" == FAILED && -z "$FAIL_REASON" ]]; then
    FAIL_REASON="unexpected preflight failure (rc=$rc)"
  fi
  if [[ "$FINAL_STATUS" != PASS ]]; then
    printf '%s\n' "${BLOCK_REASON:-$FAIL_REASON}" >"$ATTEMPT/failure.txt"
  fi
  write_status "$FINAL_STATUS"
  exit "$rc"
}
trap on_exit EXIT
write_status RUNNING

block() {
  BLOCK_REASON=$1
  FINAL_STATUS=BLOCKED
  echo "BLOCKED: $BLOCK_REASON" >&2
  exit 3
}

[[ -r "$CONFIG" ]] || block "missing config: $CONFIG"
[[ -r "$ADAPTER" ]] || block "missing adapter: $ADAPTER"

config_value() {
  local expression=$1
  python3 - "$CONFIG" "$expression" <<'PY'
import json
import sys
cfg = json.loads(open(sys.argv[1], encoding="utf-8").read())
value = cfg
for part in sys.argv[2].split("."):
    value = value[part]
if not isinstance(value, (str, int, float, bool)):
    raise SystemExit(f"expected scalar config value: {sys.argv[2]}")
print(value)
PY
}

TRUTH=$(config_value frozen_instance.truth_path)
ASSEMBLY=$(config_value frozen_instance.assembly_path)
EXPECTED_TRUTH_SHA=$(config_value frozen_instance.truth_sha256)
EXPECTED_ASSEMBLY_SHA=$(config_value frozen_instance.assembly_sha256)
TRUTH_TIER=$(config_value frozen_instance.truth_tier)
COORDINATES=$(config_value coordinate_convention)
OVERLAP_POLICY=$(config_value evaluator.overlap_policy)

[[ "$TRUTH_TIER" == T1 ]] || block "preflight is restricted to configured T1 truth, got $TRUTH_TIER"
[[ "$COORDINATES" == zero_based_half_open ]] || block "unexpected coordinate convention: $COORDINATES"
[[ -r "$TRUTH" ]] || block "missing frozen truth: $TRUTH"
[[ -r "$ASSEMBLY" ]] || block "missing frozen assembly: $ASSEMBLY"

actual_truth_sha=$(sha256sum "$TRUTH" | awk '{print $1}')
actual_assembly_sha=$(sha256sum "$ASSEMBLY" | awk '{print $1}')
[[ "$actual_truth_sha" == "$EXPECTED_TRUTH_SHA" ]] || block "truth SHA256 mismatch: expected $EXPECTED_TRUTH_SHA got $actual_truth_sha"
[[ "$actual_assembly_sha" == "$EXPECTED_ASSEMBLY_SHA" ]] || block "assembly SHA256 mismatch: expected $EXPECTED_ASSEMBLY_SHA got $actual_assembly_sha"

TRUTH_CANONICAL="$ATTEMPT/truth.canonical.tsv"
python3 "$ADAPTER" convert --input "$TRUTH" --output "$TRUTH_CANONICAL" --format bed

LENGTHS_TSV="$ATTEMPT/contig_lengths.tsv"
LENGTHS_JSON="$ATTEMPT/contig_lengths.json"
python3 - "$ASSEMBLY" "$LENGTHS_TSV" "$LENGTHS_JSON" <<'PY'
import gzip
import json
import sys
from pathlib import Path

assembly, tsv_path, json_path = map(Path, sys.argv[1:])
lengths = {}
name = None
count = 0
with gzip.open(assembly, "rt", encoding="ascii", errors="strict") as handle:
    for line_no, line in enumerate(handle, 1):
        if line.startswith(">"):
            if name is not None:
                lengths[name] = count
            name = line[1:].strip().split()[0]
            if not name or name in lengths:
                raise SystemExit(f"invalid/duplicate FASTA header at line {line_no}")
            count = 0
        elif name is not None:
            count += len("".join(line.split()))
if name is not None:
    lengths[name] = count
if not lengths or any(value < 1 for value in lengths.values()):
    raise SystemExit("assembly has no non-empty FASTA records")
with tsv_path.open("w", encoding="utf-8") as handle:
    handle.write("seqid\tlength\n")
    for seqid in sorted(lengths):
        handle.write(f"{seqid}\t{lengths[seqid]}\n")
json_path.write_text(json.dumps(lengths, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

AUDIT="$ATTEMPT/interval_audit.json"
python3 - "$ADAPTER" "$TRUTH_CANONICAL" "$AUDIT" "$LENGTHS_JSON" <<'PY'
import importlib.util
import json
import sys
from pathlib import Path

adapter_path, canonical_path, audit_path, lengths_path = map(Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location("lemmi_adapter", adapter_path)
if spec is None or spec.loader is None:
    raise SystemExit("cannot import adapter")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
rows = adapter.read_canonical(canonical_path)
lengths = json.loads(lengths_path.read_text(encoding="utf-8"))
adapter._mask(rows, lengths)
audit = adapter._interval_audit(rows)
audit.update({"contig_count": len(lengths), "truth_tier": "T1", "coordinate_convention": "zero_based_half_open"})
audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

CONFIG_SHA=$(sha256sum "$CONFIG" | awk '{print $1}')
ADAPTER_SHA=$(sha256sum "$ADAPTER" | awk '{print $1}')
export ATTEMPT CONFIG ADAPTER CONFIG_SHA ADAPTER_SHA TRUTH ASSEMBLY EXPECTED_TRUTH_SHA EXPECTED_ASSEMBLY_SHA actual_truth_sha actual_assembly_sha TRUTH_CANONICAL LENGTHS_TSV LENGTHS_JSON AUDIT TRUTH_TIER COORDINATES OVERLAP_POLICY
python3 - "$ATTEMPT/preflight_manifest.json" <<'PY'
import json
import os
import socket
import sys
from pathlib import Path

out = Path(sys.argv[1])
manifest = {
    "exp_id": "LEMMI-TE-BENCH-20260824-R1",
    "profile": "frozen_truth_preflight",
    "status": "PASS",
    "claim_eligible": False,
    "host": socket.gethostname(),
    "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
    "slurm_resources": {key: os.environ.get(key) for key in ("SLURM_CPUS_PER_TASK", "SLURM_MEM_PER_NODE", "SLURM_JOB_PARTITION", "SLURM_JOB_NODELIST")},
    "config": {"path": os.environ["CONFIG"], "sha256": os.environ["CONFIG_SHA"]},
    "adapter": {"path": os.environ["ADAPTER"], "sha256": os.environ["ADAPTER_SHA"]},
    "assembly": {"path": os.environ["ASSEMBLY"], "expected_sha256": os.environ["EXPECTED_ASSEMBLY_SHA"], "observed_sha256": os.environ["actual_assembly_sha"]},
    "truth": {"path": os.environ["TRUTH"], "expected_sha256": os.environ["EXPECTED_TRUTH_SHA"], "observed_sha256": os.environ["actual_truth_sha"], "tier": os.environ["TRUTH_TIER"]},
    "outputs": {key: os.environ[key] for key in ("TRUTH_CANONICAL", "LENGTHS_TSV", "LENGTHS_JSON", "AUDIT")},
    "coordinate_convention": os.environ["COORDINATES"],
    "overlap_policy": os.environ["OVERLAP_POLICY"],
    "caller_executed": False,
}
out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

FINAL_STATUS=PASS
echo "PASS: frozen assembly/truth verified; contig lengths and truth adapter/audit written to $ATTEMPT"
