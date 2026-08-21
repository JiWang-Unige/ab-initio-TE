#!/usr/bin/env bash
#SBATCH --job-name=TEFM-F-CODE
#SBATCH --partition=private-teodoro-gpu
#SBATCH --time=01:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/codex_validation/PIPE-TEFM-FRAG-R2-CODETEST-20260809-R1_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/codex_validation/PIPE-TEFM-FRAG-R2-CODETEST-20260809-R1_%j.err

set -Eeuo pipefail
umask 027

PROJECT_ROOT=/home/users/j/jwang/ab-initio-TE
RUN_ID=PIPE-TEFM-FRAG-R2-CODETEST-20260809-R1
STAGE_ROOT="${PROJECT_ROOT}/software_outputs/codex_validation/${RUN_ID}"
SOURCE_ROOT="${STAGE_ROOT}/source"
PIPE_ROOT="${SOURCE_ROOT}/pipelines/PIPE-TEFM-FRAG-R2-ASSET-20260809"
OUTPUT_ROOT="${PROJECT_ROOT}/reports/codex_validation/${RUN_ID}"

test -d "${SOURCE_ROOT}"
test -f "${SOURCE_ROOT}/FILE_MANIFEST_SHA256.tsv"
test -f "${STAGE_ROOT}/source.zip"
test -f "${STAGE_ROOT}/CODE_REVIEW_GATE.md"
test ! -L "${STAGE_ROOT}"
test ! -e "${OUTPUT_ROOT}"
test "$(sha256sum "${STAGE_ROOT}/source.zip" | awk '{print $1}')" = c6c2892ea33a85063367993e28dab7f85c345c9c3beedbe8abd53776ab53508b
test "$(sha256sum "${STAGE_ROOT}/CODE_REVIEW_GATE.md" | awk '{print $1}')" = 15569f77790f6c72028441173f37a63422f20c36f393ec247a52e07c48cc6664

mkdir -p "${OUTPUT_ROOT}"
export PYTHONDONTWRITEBYTECODE=1

python3 - "${SOURCE_ROOT}" <<'PY'
from pathlib import Path
import hashlib
import os
import sys

root = Path(sys.argv[1]).resolve()
rows = (root / "FILE_MANIFEST_SHA256.tsv").read_text(encoding="utf-8").splitlines()
if not rows or rows[0] != "relative_path\tbytes\tsha256":
    raise SystemExit("invalid F manifest header")
declared = set()
for line in rows[1:]:
    rel, size_text, digest = line.split("\t")
    path = (root / rel).resolve()
    if root not in path.parents or path.is_symlink() or not path.is_file() or rel in declared:
        raise SystemExit("unsafe/duplicate/missing manifest object: %s" % rel)
    data = path.read_bytes()
    if len(data) != int(size_text) or hashlib.sha256(data).hexdigest() != digest:
        raise SystemExit("manifest identity mismatch: %s" % rel)
    declared.add(rel)
actual = {
    p.relative_to(root).as_posix()
    for p in root.rglob("*")
    if p.is_file() and p.name != "FILE_MANIFEST_SHA256.tsv"
}
if actual != declared:
    raise SystemExit("manifest file-set mismatch")
if len(declared) != 36:
    raise SystemExit("expected 36 declared source objects")
print("verified_manifest_objects=36")
PY

python3 - "${PIPE_ROOT}" <<'PY'
from pathlib import Path
import ast
import sys

root = Path(sys.argv[1])
files = sorted(root.rglob("*.py"))
if len(files) != 9:
    raise SystemExit("expected 9 Python files")
for path in files:
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=(3, 9))
print("python39_grammar_files=9")
PY

cd "${PIPE_ROOT}"
python3 -m unittest discover -s tests -v >"${OUTPUT_ROOT}/unittest.log" 2>&1
grep -q '^Ran 33 tests ' "${OUTPUT_ROOT}/unittest.log"
grep -q '^OK$' "${OUTPUT_ROOT}/unittest.log"

TMP_BASE=${SLURM_TMPDIR:-/tmp}
SYN_ROOT=$(mktemp -d "${TMP_BASE}/tefm_frag_r2_full17.XXXXXX")
python3 synthetic_t0.py generate \
  --config config/FRAG-T0-SYN-1.0.0.json \
  --output-dir "${SYN_ROOT}/panel" \
  >"${OUTPUT_ROOT}/full17_generate_stdout.json"
python3 synthetic_t0.py validate \
  --config config/FRAG-T0-SYN-1.0.0.json \
  --input-dir "${SYN_ROOT}/panel" \
  --out-report "${SYN_ROOT}/panel/A2_validation_report.json" \
  >"${OUTPUT_ROOT}/full17_validate_stdout.json"
cp -p "${SYN_ROOT}/panel/A2_validation_report.json" "${OUTPUT_ROOT}/A2_validation_report.json"
cp -p "${SYN_ROOT}/panel/generation_manifest.json" "${OUTPUT_ROOT}/generation_manifest.json"

python3 - "${OUTPUT_ROOT}" "${SLURM_JOB_ID}" <<'PY'
from pathlib import Path
import json
import sys

out = Path(sys.argv[1])
job_id = sys.argv[2]
report = json.loads((out / "A2_validation_report.json").read_text(encoding="utf-8"))
if report.get("status") != "PASS_SYNTHETIC_T0_SEMANTICS":
    raise SystemExit("full synthetic validation did not pass")
if report.get("full_frozen_panel") is not True or report.get("selected_genomes") != ["syn_g%03d" % i for i in range(17)]:
    raise SystemExit("full 17-genome contract mismatch")
if report.get("byte_identical_regeneration") is not True or report.get("frozen_table_recomputation_pass") is not True:
    raise SystemExit("regeneration/semantic recomputation gate failed")
summary = {
    "schema_version": "TRACK_F_CODETEST_SUMMARY_V1",
    "run_id": "PIPE-TEFM-FRAG-R2-CODETEST-20260809-R1",
    "job_id": job_id,
    "python_runtime": sys.version,
    "manifest_objects_verified": 36,
    "python39_grammar_files": 9,
    "unit_tests_passed": 33,
    "unit_tests_failed": 0,
    "full_synthetic_panel_generated": True,
    "full_frozen_panel": True,
    "byte_identical_regeneration": True,
    "scientific_execution_performed": False,
    "remote_real_assets_executed": False,
    "next_stage_authorized": False,
}
(out / "CODETEST_SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

find "${OUTPUT_ROOT}" -maxdepth 1 -type f -print0 | sort -z | xargs -0 sha256sum >"${STAGE_ROOT}/OUTPUT_SHA256.tsv"

