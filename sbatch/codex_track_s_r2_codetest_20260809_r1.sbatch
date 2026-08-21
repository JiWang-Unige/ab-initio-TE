#!/usr/bin/env bash
#SBATCH --job-name=TEFM-S-CODE
#SBATCH --partition=private-teodoro-gpu
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/codex_validation/PIPE-TEFM-SF-R2-CODETEST-20260809-R1_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/codex_validation/PIPE-TEFM-SF-R2-CODETEST-20260809-R1_%j.err

set -Eeuo pipefail
umask 027

PROJECT_ROOT=/home/users/j/jwang/ab-initio-TE
RUN_ID=PIPE-TEFM-SF-R2-CODETEST-20260809-R1
STAGE_ROOT="${PROJECT_ROOT}/software_outputs/codex_validation/${RUN_ID}"
SOURCE_ROOT="${STAGE_ROOT}/source"
PIPE_ROOT="${SOURCE_ROOT}/pipelines/PIPE-TEFM-SF-R2-ASSET-20260809"
OUTPUT_ROOT="${PROJECT_ROOT}/reports/codex_validation/${RUN_ID}"

test -d "${SOURCE_ROOT}"
test -f "${SOURCE_ROOT}/FILE_MANIFEST_SHA256.tsv"
test -f "${STAGE_ROOT}/source.zip"
test -f "${STAGE_ROOT}/CODE_REVIEW_GATE.md"
test ! -L "${STAGE_ROOT}"
test ! -e "${OUTPUT_ROOT}"
test "$(sha256sum "${STAGE_ROOT}/source.zip" | awk '{print $1}')" = 6544a0f3125c5cf2dddf80dc033cdff099c71d263aa1e8bab7d4603401f8c4b2
test "$(sha256sum "${STAGE_ROOT}/CODE_REVIEW_GATE.md" | awk '{print $1}')" = e9134b069a0d401d6263e5249617e10256bf57a6ff8f2ea3d0d7d15ed0633a39

mkdir -p "${OUTPUT_ROOT}"
export PYTHONDONTWRITEBYTECODE=1

python3 - "${SOURCE_ROOT}" <<'PY'
from pathlib import Path
import hashlib
import sys

root = Path(sys.argv[1]).resolve()
rows = (root / "FILE_MANIFEST_SHA256.tsv").read_text(encoding="utf-8").splitlines()
if not rows or rows[0] != "path\tbytes\tsha256":
    raise SystemExit("invalid S manifest header")
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
if len(declared) != 23:
    raise SystemExit("expected 23 declared source objects")
print("verified_manifest_objects=23")
PY

python3 - "${PIPE_ROOT}" <<'PY'
from pathlib import Path
import ast
import sys

root = Path(sys.argv[1])
files = sorted(root.rglob("*.py"))
if len(files) != 17:
    raise SystemExit("expected 17 Python files")
for path in files:
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=(3, 9))
print("python39_grammar_files=17")
PY

cd "${PIPE_ROOT}"
python3 -W error -m unittest discover -s tests -v >"${OUTPUT_ROOT}/unittest.log" 2>&1
grep -q '^Ran 51 tests ' "${OUTPUT_ROOT}/unittest.log"
grep -q '^OK$' "${OUTPUT_ROOT}/unittest.log"

python3 - "${OUTPUT_ROOT}" "${SLURM_JOB_ID}" <<'PY'
from pathlib import Path
import json
import sys

out = Path(sys.argv[1])
summary = {
    "schema_version": "TRACK_S_CODETEST_SUMMARY_V1",
    "run_id": "PIPE-TEFM-SF-R2-CODETEST-20260809-R1",
    "job_id": sys.argv[2],
    "python_runtime": sys.version,
    "manifest_objects_verified": 23,
    "python39_grammar_files": 17,
    "unit_tests_passed": 51,
    "unit_tests_failed": 0,
    "production_homology_allowlist_expected_empty": True,
    "scientific_execution_performed": False,
    "remote_real_assets_executed": False,
    "next_stage_authorized": False,
}
(out / "CODETEST_SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

find "${OUTPUT_ROOT}" -maxdepth 1 -type f -print0 | sort -z | xargs -0 sha256sum >"${STAGE_ROOT}/OUTPUT_SHA256.tsv"

