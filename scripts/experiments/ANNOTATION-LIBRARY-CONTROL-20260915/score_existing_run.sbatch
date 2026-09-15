#!/bin/bash
# Re-score the two already completed RepeatMasker annotations from the
# preserved 12732075 run.  This job never invokes RepeatMasker.
#SBATCH --job-name=te-lib-existing-score
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --output=outputs/ANNOTATION-LIBRARY-CONTROL-20260915/library-score-existing-%j.log

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"

MAIN_RUN=run-12732075
BASE="outputs/ANNOTATION-LIBRARY-CONTROL-20260915/library-score-existing-${SLURM_JOB_ID}"
CONFIG="configs/ANNOTATION-LIBRARY-CONTROL-20260915.json"
CONTROL="scripts/experiments/ANNOTATION-LIBRARY-CONTROL-20260915/control.py"
PANEL="outputs/ANNOTATION-LIBRARY-CONTROL-20260915/${MAIN_RUN}/panel"

test ! -e "$BASE"
test -s "$PANEL/panel.tsv"
test -s "outputs/ANNOTATION-LIBRARY-CONTROL-20260915/${MAIN_RUN}/annotation-dfam2018/panel.fa.out"
test -s "outputs/ANNOTATION-LIBRARY-CONTROL-20260915/${MAIN_RUN}/annotation-dfam39-curated/panel.fa.out"
mkdir "$BASE"

python3 - "$CONFIG" "$BASE/runtime-config.json" <<'PY'
import json
import sys

config_path, output_path = sys.argv[1:]
with open(config_path, encoding="utf-8") as handle:
    config = json.load(handle)
base = "outputs/ANNOTATION-LIBRARY-CONTROL-20260915/run-12732075"
for library in config["libraries"]:
    directory = "annotation-dfam2018" if library["label"] == "dfam2018_consensus" else "annotation-dfam39-curated"
    library["annotation_out"] = f"{base}/{directory}/panel.fa.out"
config["execution_run_dir"] = base
with open(output_path, "w", encoding="utf-8") as handle:
    json.dump(config, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY

python3 "$CONTROL" score \
  --config "$BASE/runtime-config.json" \
  --root "$ROOT" \
  --panel-dir "$ROOT/$PANEL" \
  --output "$BASE/score"

cat > "$BASE/completion.json" <<EOF
{
  "status": "COMPLETED",
  "slurm_job_id": "$SLURM_JOB_ID",
  "source_annotation_run": "$MAIN_RUN",
  "target_annotation_read": false,
  "same_base_f1_computed": false,
  "fp_rescue_claim": false
}
EOF
echo COMPLETED > "$BASE/STATUS"
