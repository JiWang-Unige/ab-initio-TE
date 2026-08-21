#!/usr/bin/env bash
#SBATCH --job-name=TEFM-G-P1
#SBATCH --partition=private-teodoro-gpu
#SBATCH --time=04:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/tefm_transfer_r2_asset/PIPE-TEFM-TRANSFER-R2-P1-20260809-R1_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/tefm_transfer_r2_asset/PIPE-TEFM-TRANSFER-R2-P1-20260809-R1_%j.err

set -Eeuo pipefail
umask 027

PROJECT_ROOT=/home/users/j/jwang/ab-initio-TE
RUN_ID=PIPE-TEFM-TRANSFER-R2-P1-20260809-R1
STAGE_ROOT="${PROJECT_ROOT}/software_outputs/tefm_transfer_r2_asset/${RUN_ID}"
BUNDLE_ROOT="${STAGE_ROOT}/bundle"
CODE_ROOT="${BUNDLE_ROOT}/g2/pipelines/PIPE-TEFM-TRANSFER-R2-ASSET-20260809"
PREREQ_REPORT_REL="software_outputs/tefm_transfer_r2_asset/${RUN_ID}/bundle/prereq/feasibility_report.json"
PREREQ_MANIFEST_REL="software_outputs/tefm_transfer_r2_asset/${RUN_ID}/bundle/prereq/artifact_manifest.tsv"
OUTPUT_REL="reports/tefm_transfer_r2_asset/${RUN_ID}"
OUTPUT_DIR="${PROJECT_ROOT}/${OUTPUT_REL}"
SUMMARY_PATH="${STAGE_ROOT}/SLURM_RUN_SUMMARY.json"
OUTPUT_HASHES="${STAGE_ROOT}/OUTPUT_SHA256.tsv"

EXPECTED_REPORT_SHA=2107172a2c92961de98e0ede1cdb3744d8a204f4d5b9d8983642b0b785d1a6d5
EXPECTED_MANIFEST_SHA=8623362dffd9534afc6904373eeab9af697420a7f3096747a304c3167952cfb7
EXPECTED_CONTRACT_SHA=d8aba5cac716db3b94c1f0a8d283165279e1b25e58167ff9da4a4f6327a975d8

test -d "${PROJECT_ROOT}"
test -d "${BUNDLE_ROOT}/g2"
test -f "${BUNDLE_ROOT}/g2/FILE_MANIFEST_SHA256.tsv"
test ! -L "${STAGE_ROOT}"
test ! -L "${BUNDLE_ROOT}"
test ! -e "${OUTPUT_DIR}"

python3 - <<'PY'
import sys
if sys.version_info < (3, 9):
    raise SystemExit("Python >=3.9 required")
print(sys.version)
PY

python3 - "${BUNDLE_ROOT}/g2" <<'PY'
from pathlib import Path
import hashlib
import sys

root = Path(sys.argv[1]).resolve()
manifest = root / "FILE_MANIFEST_SHA256.tsv"
rows = manifest.read_text(encoding="utf-8").splitlines()
if not rows or rows[0] != "sha256\tbytes\tpath":
    raise SystemExit("invalid source manifest header")
seen = set()
for line in rows[1:]:
    digest, size_text, rel = line.split("\t")
    path = (root / rel).resolve()
    if root not in path.parents or path.is_symlink() or not path.is_file():
        raise SystemExit("unsafe or missing source object: %s" % rel)
    if rel in seen:
        raise SystemExit("duplicate source manifest path: %s" % rel)
    seen.add(rel)
    data = path.read_bytes()
    if len(data) != int(size_text) or hashlib.sha256(data).hexdigest() != digest:
        raise SystemExit("source identity mismatch: %s" % rel)
print("verified_source_objects=%d" % len(seen))
PY

REPORT_SHA=$(sha256sum "${PROJECT_ROOT}/${PREREQ_REPORT_REL}" | awk '{print $1}')
MANIFEST_SHA=$(sha256sum "${PROJECT_ROOT}/${PREREQ_MANIFEST_REL}" | awk '{print $1}')
CONTRACT_SHA=$(sha256sum "${CODE_ROOT}/FROZEN_P1_CONTRACT_V1.json" | awk '{print $1}')
test "${REPORT_SHA}" = "${EXPECTED_REPORT_SHA}"
test "${MANIFEST_SHA}" = "${EXPECTED_MANIFEST_SHA}"
test "${CONTRACT_SHA}" = "${EXPECTED_CONTRACT_SHA}"

cd "${CODE_ROOT}"
python3 -m unittest discover -s tests -v

cd "${PROJECT_ROOT}"
set +e
python3 "${CODE_ROOT}/reconstruct_provenance.py" run \
  --project-root "${PROJECT_ROOT}" \
  --search-root configs \
  --search-root sbatch \
  --search-root pipelines \
  --search-root reports \
  --search-root logs \
  --search-root docs \
  --search-root software_outputs/tefm_supp/PIPE-TEFM-SUPP-20260617 \
  --search-root software_outputs/tefm_repair/PIPE-TEFM-REPAIR-20260618 \
  --search-root software_outputs/tefm_calib/PIPE-TEFM-CALIB-20260621 \
  --prereq-report "${PREREQ_REPORT_REL}" \
  --prereq-artifact-manifest "${PREREQ_MANIFEST_REL}" \
  --output-dir "${OUTPUT_REL}" \
  >"${STAGE_ROOT}/run_stdout.json" \
  2>"${STAGE_ROOT}/run_stderr.txt"
RUN_RC=$?
set -e
if [[ "${RUN_RC}" -ne 0 && "${RUN_RC}" -ne 2 ]]; then
  exit "${RUN_RC}"
fi

set +e
python3 "${CODE_ROOT}/reconstruct_provenance.py" verify \
  --project-root "${PROJECT_ROOT}" \
  --prereq-report "${PREREQ_REPORT_REL}" \
  --prereq-artifact-manifest "${PREREQ_MANIFEST_REL}" \
  --output-dir "${OUTPUT_REL}" \
  >"${STAGE_ROOT}/verify_stdout.json" \
  2>"${STAGE_ROOT}/verify_stderr.txt"
VERIFY_RC=$?
set -e
if [[ "${VERIFY_RC}" -ne 0 && "${VERIFY_RC}" -ne 2 ]]; then
  exit "${VERIFY_RC}"
fi
test "${RUN_RC}" -eq "${VERIFY_RC}"

python3 - "${OUTPUT_DIR}" "${RUN_RC}" "${VERIFY_RC}" "${SLURM_JOB_ID}" "${SUMMARY_PATH}" <<'PY'
from pathlib import Path
import json
import sys

output_dir = Path(sys.argv[1])
run_rc = int(sys.argv[2])
verify_rc = int(sys.argv[3])
job_id = sys.argv[4]
summary_path = Path(sys.argv[5])
expected = {
    "FIXED_ANCHOR_PROVENANCE_V1.json",
    "CANDIDATE_EVIDENCE_LEDGER_V1.tsv",
    "PROVENANCE_FAILURE_REPORT_V1.tsv",
    "P1_READINESS_SEAL_V1.json",
}
actual = {p.name for p in output_dir.iterdir() if p.is_file()}
if actual != expected:
    raise SystemExit("unexpected output file set: %r" % sorted(actual))
records = json.loads((output_dir / "FIXED_ANCHOR_PROVENANCE_V1.json").read_text(encoding="utf-8"))
anchors = records.get("anchors")
if not isinstance(anchors, list) or len(anchors) != 5:
    raise SystemExit("expected exactly five anchor records")
seal = json.loads((output_dir / "P1_READINESS_SEAL_V1.json").read_text(encoding="utf-8"))
if seal.get("next_stage_authorized") is not False:
    raise SystemExit("P1 must never authorize the next scientific stage")
all_valid = all(item.get("status") == "PROV_VALID" for item in anchors)
if (run_rc == 0) != all_valid:
    raise SystemExit("run exit code disagrees with anchor semantics")
expected_readiness = "P1_PROVENANCE_READY" if all_valid else "P1_PROVENANCE_BLOCKED"
if seal.get("readiness") != expected_readiness:
    raise SystemExit("readiness seal disagrees with anchor semantics")
summary = {
    "schema_version": "TRACK_G_P1_SLURM_RUN_SUMMARY_V1",
    "job_id": job_id,
    "run_id": "PIPE-TEFM-TRANSFER-R2-P1-20260809-R1",
    "run_rc": run_rc,
    "verify_rc": verify_rc,
    "anchor_count": len(anchors),
    "anchor_statuses": {item.get("anchor_id"): item.get("status") for item in anchors},
    "all_five_prov_valid": all_valid,
    "p1_readiness_status": seal.get("readiness"),
    "next_stage_authorized": False,
    "scientific_execution_performed": False,
}
summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(summary, sort_keys=True))
PY

find "${OUTPUT_DIR}" -maxdepth 1 -type f -print0 | sort -z | xargs -0 sha256sum >"${OUTPUT_HASHES}"
sha256sum "${SUMMARY_PATH}" "${STAGE_ROOT}/run_stdout.json" "${STAGE_ROOT}/run_stderr.txt" \
  "${STAGE_ROOT}/verify_stdout.json" "${STAGE_ROOT}/verify_stderr.txt" >>"${OUTPUT_HASHES}"

exit 0
