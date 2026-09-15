#!/bin/bash
#SBATCH --job-name=te-lib-noreuse-score
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=outputs/ANNOTATION-LIBRARY-CONTROL-20260915/no-reuse-score-%j.log

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
MAIN_RUN=run-12732075
ORTH_RUN=orthogonal-run-12732331
CONTROL=scripts/experiments/ANNOTATION-LIBRARY-CONTROL-20260915/control.py
CONFIG=configs/ANNOTATION-LIBRARY-CONTROL-20260915.json
BASE="$ROOT/outputs/ANNOTATION-LIBRARY-CONTROL-20260915/library-no-reuse-score-${SLURM_JOB_ID}"

test ! -e "$BASE"
test -s "$ROOT/outputs/ANNOTATION-LIBRARY-CONTROL-20260915/$MAIN_RUN/panel/panel.tsv"
test -s "$ROOT/outputs/ANNOTATION-LIBRARY-CONTROL-20260915/$ORTH_RUN/no-reuse/matched_controls_no_reuse.tsv"
test -s "$ROOT/outputs/ANNOTATION-LIBRARY-CONTROL-20260915/$MAIN_RUN/annotation-dfam2018/panel.fa.out"
test -s "$ROOT/outputs/ANNOTATION-LIBRARY-CONTROL-20260915/$MAIN_RUN/annotation-dfam39-curated/panel.fa.out"
mkdir "$BASE"
python3 - "$CONFIG" "$BASE/runtime-config.json" "$MAIN_RUN" "$ORTH_RUN" <<'PY'
import json
import sys

config_path, output_path, main_run, orth_run = sys.argv[1:]
with open(config_path, encoding="utf-8") as handle:
    config = json.load(handle)
base = "outputs/ANNOTATION-LIBRARY-CONTROL-20260915"
config["matched_controls"] = f"{base}/{orth_run}/no-reuse/matched_controls_no_reuse.tsv"
for library in config["libraries"]:
    directory = "annotation-dfam2018" if library["label"] == "dfam2018_consensus" else "annotation-dfam39-curated"
    library["annotation_out"] = f"{base}/{main_run}/{directory}/panel.fa.out"
config["execution_run_dir"] = f"{base}/{main_run}"
config["matching_variant"] = "NO_REUSE_SOURCE_ONLY"
with open(output_path, "w", encoding="utf-8") as handle:
    json.dump(config, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY
python3 "$CONTROL" score \
  --config "$BASE/runtime-config.json" \
  --root "$ROOT" \
  --panel-dir "$ROOT/outputs/ANNOTATION-LIBRARY-CONTROL-20260915/$MAIN_RUN/panel" \
  --output "$BASE/score"
cat > "$BASE/completion.json" <<EOF
{
  "status": "COMPLETED",
  "slurm_job_id": "$SLURM_JOB_ID",
  "main_library_run": "$MAIN_RUN",
  "matching_variant": "NO_REUSE_SOURCE_ONLY",
  "target_annotation_read": false,
  "same_base_f1_computed": false,
  "fp_rescue_claim": false
}
EOF
echo COMPLETED > "$BASE/STATUS"
