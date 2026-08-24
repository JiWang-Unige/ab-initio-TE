#!/usr/bin/env bash
# Same-instance HiTE claim-screen runner. Resource flags are supplied by sbatch
# (recommended: --cpus-per-task=40 --mem=128G --time=12:00:00).
# No Dfam truth or nested submission is used by this cell.
set -Eeuo pipefail
umask 022

PROJECT_ROOT=${PROJECT_ROOT:-/home/users/j/jwang/ab-initio-TE}
CONFIG=${CONFIG:-$PROJECT_ROOT/configs/LEMMI-TE-BENCH-20260824-R1.yaml}
ADAPTER=${ADAPTER:-$PROJECT_ROOT/scripts/experiments/LEMMI-TE-BENCH-20260824-R1/adapter.py}
OUTPUT_ROOT=${OUTPUT_ROOT:-$PROJECT_ROOT/outputs/LEMMI-TE-BENCH-20260824-R1}
PREFLIGHT_ATTEMPT=${PREFLIGHT_ATTEMPT:-}
JOB_ID=${SLURM_JOB_ID:-}
if [[ ! "$JOB_ID" =~ ^[0-9]+$ || "$JOB_ID" == 0 ]]; then
  echo "BLOCKED: must run inside an allocation with a numeric SLURM_JOB_ID" >&2
  exit 3
fi

ATTEMPT="$OUTPUT_ROOT/hite-claim-attempt-$JOB_ID"
mkdir -p "$OUTPUT_ROOT"
if ! mkdir "$ATTEMPT"; then
  echo "BLOCKED: output attempt already exists: $ATTEMPT" >&2
  exit 3
fi
LOG="$ATTEMPT/hite-claim.log"
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
    FAIL_REASON="unexpected claim-screen failure (rc=$rc)"
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
fail() {
  FAIL_REASON=$1
  FINAL_STATUS=FAILED
  echo "FAILED: $FAIL_REASON" >&2
  exit 2
}

THREADS=${SLURM_CPUS_PER_TASK:-}
[[ "$THREADS" =~ ^[1-9][0-9]*$ ]] || block "SLURM_CPUS_PER_TASK must be a positive integer"

[[ -r "$CONFIG" ]] || block "missing config: $CONFIG"
[[ -r "$ADAPTER" ]] || block "missing adapter: $ADAPTER"
[[ -n "$PREFLIGHT_ATTEMPT" ]] || block "PREFLIGHT_ATTEMPT must be supplied by dependent submission"
[[ "$PREFLIGHT_ATTEMPT" == /* ]] || block "PREFLIGHT_ATTEMPT must be absolute"
[[ -r "$PREFLIGHT_ATTEMPT/STATUS" ]] || block "missing preflight STATUS: $PREFLIGHT_ATTEMPT"
[[ "$(tr -d '[:space:]' <"$PREFLIGHT_ATTEMPT/STATUS")" == PASS ]] || block "preflight is not PASS: $PREFLIGHT_ATTEMPT/STATUS"
PREFLIGHT_MANIFEST="$PREFLIGHT_ATTEMPT/preflight_manifest.json"
PREFLIGHT_LENGTHS="$PREFLIGHT_ATTEMPT/contig_lengths.json"
PREFLIGHT_TRUTH="$PREFLIGHT_ATTEMPT/truth.canonical.tsv"
[[ -r "$PREFLIGHT_MANIFEST" ]] || block "missing preflight manifest"
[[ -r "$PREFLIGHT_LENGTHS" ]] || block "missing preflight contig lengths"
[[ -r "$PREFLIGHT_TRUTH" ]] || block "missing preflight canonical truth"

config_value() {
  local expression=$1
  python3 - "$CONFIG" "$expression" <<'PY'
import json
import sys
value = json.loads(open(sys.argv[1], encoding="utf-8").read())
for part in sys.argv[2].split("."):
    value = value[part]
if not isinstance(value, (str, int, float, bool)):
    raise SystemExit(f"expected scalar config value: {sys.argv[2]}")
print(value)
PY
}

TRUTH_TIER=$(config_value frozen_instance.truth_tier)
[[ "$TRUTH_TIER" == T1 ]] || block "claim screen requires T1 truth tier, got $TRUTH_TIER"
ASSEMBLY=$(config_value frozen_instance.assembly_path)
EXPECTED_ASSEMBLY_SHA=$(config_value frozen_instance.assembly_sha256)
TRUTH=$(config_value frozen_instance.truth_path)
EXPECTED_TRUTH_SHA=$(config_value frozen_instance.truth_sha256)
SIF=$(config_value claim_screen.sif_path)
EXPECTED_SIF_SHA=$(config_value claim_screen.sif_sha256)
RUNTIME_CAP=$(config_value claim_screen.runtime_cap_seconds)
KILL_AFTER=$(config_value claim_screen.kill_after_seconds)
[[ -r "$ASSEMBLY" ]] || block "missing frozen assembly: $ASSEMBLY"
[[ -r "$TRUTH" ]] || block "missing frozen truth: $TRUTH"
[[ -r "$SIF" ]] || block "missing exact HiTE SIF: $SIF"

[[ "$(sha256sum "$ASSEMBLY" | awk '{print $1}')" == "$EXPECTED_ASSEMBLY_SHA" ]] || block "assembly SHA256 mismatch"
[[ "$(sha256sum "$TRUTH" | awk '{print $1}')" == "$EXPECTED_TRUTH_SHA" ]] || block "truth SHA256 mismatch"
[[ "$(sha256sum "$SIF" | awk '{print $1}')" == "$EXPECTED_SIF_SHA" ]] || block "HiTE SIF SHA256 mismatch"
if ! python3 - "$PREFLIGHT_MANIFEST" "$TRUTH" "$EXPECTED_TRUTH_SHA" "$ASSEMBLY" "$EXPECTED_ASSEMBLY_SHA" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected = {
    "truth_path": sys.argv[2], "truth_sha256": sys.argv[3],
    "assembly_path": sys.argv[4], "assembly_sha256": sys.argv[5],
}
if manifest.get("status") != "PASS" or manifest.get("profile") != "frozen_truth_preflight":
    raise SystemExit("preflight manifest is not a PASS frozen_truth_preflight")
truth = manifest.get("truth", {}); assembly = manifest.get("assembly", {})
if truth.get("path") != expected["truth_path"] or truth.get("expected_sha256") != expected["truth_sha256"] or truth.get("observed_sha256") != expected["truth_sha256"]:
    raise SystemExit("preflight truth identity does not match current config")
if assembly.get("path") != expected["assembly_path"] or assembly.get("expected_sha256") != expected["assembly_sha256"] or assembly.get("observed_sha256") != expected["assembly_sha256"]:
    raise SystemExit("preflight assembly identity does not match current config")
PY
then
  block "preflight manifest identity mismatch"
fi

WORK="$ATTEMPT/work"
mkdir -p "$WORK/input" "$WORK/hite" "$WORK/home" "$WORK/tmp"
gzip -cd "$ASSEMBLY" >"$WORK/input/hite.fa"
INPUT_SHA=$(sha256sum "$WORK/input/hite.fa" | awk '{print $1}')

COMMAND_LOG="$ATTEMPT/hite.command.log"
HELP_LOG="$ATTEMPT/hite.help.log"
set +e
timeout --foreground --kill-after=10s 60s \
  apptainer exec --cleanenv --bind "$WORK:/work" "$SIF" \
  env HOME=/work/home TMPDIR=/work/tmp \
    http_proxy=http://127.0.0.1:9 https_proxy=http://127.0.0.1:9 \
    ftp_proxy=http://127.0.0.1:9 all_proxy=socks5://127.0.0.1:9 \
    HTTP_PROXY=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 \
    FTP_PROXY=http://127.0.0.1:9 ALL_PROXY=socks5://127.0.0.1:9 \
    NO_PROXY=localhost,127.0.0.1 no_proxy=localhost,127.0.0.1 \
    python /HiTE/main.py -h >"$HELP_LOG" 2>&1
HELP_RC=$?
set -e
[[ "$HELP_RC" == 0 ]] || fail "HiTE help identity command failed (rc=$HELP_RC)"
grep -Eq '^#+[[:space:]]+HiTE, version 3\.3\.3[[:space:]]+#+[[:space:]]*$' "$HELP_LOG" || fail "HiTE help banner is not exact version 3.3.3"

set +e
timeout --foreground --kill-after="${KILL_AFTER}s" "${RUNTIME_CAP}s" \
  apptainer exec --cleanenv --bind "$WORK:/work" "$SIF" \
  env HOME=/work/home TMPDIR=/work/tmp \
    http_proxy=http://127.0.0.1:9 https_proxy=http://127.0.0.1:9 \
    ftp_proxy=http://127.0.0.1:9 all_proxy=socks5://127.0.0.1:9 \
    HTTP_PROXY=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 \
    FTP_PROXY=http://127.0.0.1:9 ALL_PROXY=socks5://127.0.0.1:9 \
    NO_PROXY=localhost,127.0.0.1 no_proxy=localhost,127.0.0.1 \
    python /HiTE/main.py --genome /work/input/hite.fa --thread "$THREADS" \
      --plant 0 --annotate 1 --out_dir /work/hite >"$COMMAND_LOG" 2>&1
RC=$?
set -e
[[ "$RC" == 0 ]] || fail "HiTE direct argv failed or timed out (rc=$RC)"

mapfile -t GFF_PATHS < <(find "$WORK" -type f -name 'HiTE.gff' -print | sort)
[[ "${#GFF_PATHS[@]}" == 1 ]] || fail "expected exactly one HiTE.gff, found ${#GFF_PATHS[@]}"
GFF_PATH=${GFF_PATHS[0]}
[[ -s "$GFF_PATH" ]] || fail "unique HiTE.gff is empty"

CANONICAL="$ATTEMPT/hite.canonical.tsv"
python3 "$ADAPTER" convert --input "$GFF_PATH" --output "$CANONICAL" --format gff3
[[ -s "$CANONICAL" ]] || fail "HiTE canonical adapter output is empty"

RAW_METRICS="$ATTEMPT/metrics.adapter.json"
python3 "$ADAPTER" evaluate \
  --truth "$PREFLIGHT_TRUTH" \
  --prediction "$CANONICAL" \
  --lengths "$PREFLIGHT_LENGTHS" \
  --truth-tier T1 \
  --iou-threshold 0.8 \
  --boundary-tol-bp 5 \
  --overlap-policy flat_union >"$RAW_METRICS"

METRICS="$ATTEMPT/metrics.json"
export CONFIG ADAPTER PREFLIGHT_ATTEMPT GFF_PATH CANONICAL RAW_METRICS METRICS SIF EXPECTED_SIF_SHA INPUT_SHA TRUTH_TIER JOB_ID THREADS
python3 - "$METRICS" <<'PY'
import json
import os
import socket
import sys
from pathlib import Path

raw = json.loads(Path(os.environ["RAW_METRICS"]).read_text(encoding="utf-8"))
if raw.get("truth_tier") != "T1":
    raise SystemExit("metrics truth_tier is not T1")
payload = {
    "exp_id": "LEMMI-TE-BENCH-20260824-R1",
    "profile": "hite_same_instance_claim_screen",
    "tool": "HiTE",
    "tool_version": "3.3.3",
    "claim_eligible": True,
    "claim_scope": "T1_positive_only_recall_boundary_fragmentation",
    "whole_genome_precision_f1_claim": False,
    "semantic_success": True,
    "caller_executed": True,
    "truth_source": "FlyBase FB2026_02 curated T1 positive-only truth",
    "truth_tier": "T1",
    "preflight_attempt": os.environ["PREFLIGHT_ATTEMPT"],
    "host": socket.gethostname(),
    "slurm_job_id": os.environ["JOB_ID"],
    "threads": int(os.environ["THREADS"]),
    "sif": {"path": os.environ["SIF"], "sha256": os.environ["EXPECTED_SIF_SHA"]},
    "input": {"assembly_fasta_uncompressed_sha256": os.environ["INPUT_SHA"]},
    "prediction": {"gff": os.environ["GFF_PATH"], "canonical": os.environ["CANONICAL"]},
    "metrics": raw,
}
Path(sys.argv[1]).write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
PY

MANIFEST="$ATTEMPT/claim_manifest.json"
export MANIFEST METRICS HELP_LOG COMMAND_LOG CONFIG_SHA256=$(sha256sum "$CONFIG" | awk '{print $1}') ADAPTER_SHA256=$(sha256sum "$ADAPTER" | awk '{print $1}') GFF_SHA256=$(sha256sum "$GFF_PATH" | awk '{print $1}') CANONICAL_SHA256=$(sha256sum "$CANONICAL" | awk '{print $1}') METRICS_SHA256=$(sha256sum "$METRICS" | awk '{print $1}')
python3 - "$MANIFEST" <<'PY'
import json
import os
import sys
from pathlib import Path

manifest = {
    "exp_id": "LEMMI-TE-BENCH-20260824-R1",
    "profile": "hite_same_instance_claim_screen",
    "status": "PASS",
    "claim_eligible": True,
    "claim_scope": "T1_positive_only_recall_boundary_fragmentation",
    "preflight_attempt": os.environ["PREFLIGHT_ATTEMPT"],
    "config": {"path": os.environ["CONFIG"], "sha256": os.environ["CONFIG_SHA256"]},
    "adapter": {"path": os.environ["ADAPTER"], "sha256": os.environ["ADAPTER_SHA256"]},
    "hite": {"sif": os.environ["SIF"], "sif_sha256": os.environ["EXPECTED_SIF_SHA"], "direct_argv": ["python", "/HiTE/main.py", "--genome", "/work/input/hite.fa", "--thread", os.environ["THREADS"], "--plant", "0", "--annotate", "1", "--out_dir", "/work/hite"]},
    "whole_genome_precision_f1_claim": False,
    "threads": int(os.environ["THREADS"]),
    "artifacts": {"gff": {"path": os.environ["GFF_PATH"], "sha256": os.environ["GFF_SHA256"]}, "canonical": {"path": os.environ["CANONICAL"], "sha256": os.environ["CANONICAL_SHA256"]}, "metrics": {"path": os.environ["METRICS"], "sha256": os.environ["METRICS_SHA256"]}},
    "logs": {"help": os.environ["HELP_LOG"], "minimum": os.environ["COMMAND_LOG"]},
    "resource_observation": {key: os.environ.get(key) for key in ("SLURM_CPUS_PER_TASK", "SLURM_MEM_PER_NODE", "SLURM_JOB_PARTITION", "SLURM_JOB_NODELIST")},
    "dfam_truth_used": False,
}
Path(sys.argv[1]).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

FINAL_STATUS=PASS
echo "PASS: HiTE 3.3.3 produced one GFF and T1 metrics at $ATTEMPT"
