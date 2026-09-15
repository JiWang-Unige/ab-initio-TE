#!/bin/bash
#SBATCH --job-name=te-lib-control
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=outputs/ANNOTATION-LIBRARY-CONTROL-20260915/library-%j.log

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark

CONFIG=configs/ANNOTATION-LIBRARY-CONTROL-20260915.json
CONTROL=scripts/experiments/ANNOTATION-LIBRARY-CONTROL-20260915/control.py
BASE="$ROOT/outputs/ANNOTATION-LIBRARY-CONTROL-20260915/run-${SLURM_JOB_ID}"
PANEL="$BASE/panel"
LIBDIR="$BASE/libraries"
AUDITDIR="$BASE/library-audits"
OLD_LIB="$ROOT/.backup/data/libraries/dfam/3.9/families/Dfam-RepeatMasker.lib.gz"
FAMDB="$ROOT/software_outputs/L1-PANEL-PREP-20260908-kqZrej/labela-12664906-1/RepeatMasker/famdb.py"
FAMDB_DB="$ROOT/software_outputs/repeatmasker_dfam/raw_runs/self_labelA/RMDFAM_FULLPARTITIONS_RERUN_20260617/famdb_fullpartitions"
RM="$CONDA_PREFIX/bin/RepeatMasker"

test -x "$RM"
test ! -e "$BASE"
test ! -e "$PANEL"
test ! -e "$BASE/score"
mkdir "$BASE"
python3 - "$CONFIG" "$BASE/runtime-config.json" "$SLURM_JOB_ID" <<'PY'
import json
import sys

config_path, output_path, job_id = sys.argv[1:]
with open(config_path, encoding="utf-8") as handle:
    config = json.load(handle)
base = f"outputs/ANNOTATION-LIBRARY-CONTROL-20260915/run-{job_id}"
for library in config["libraries"]:
    directory = "annotation-dfam2018" if library["label"] == "dfam2018_consensus" else "annotation-dfam39-curated"
    library["annotation_out"] = f"{base}/{directory}/panel.fa.out"
config["execution_run_dir"] = base
with open(output_path, "w", encoding="utf-8") as handle:
    json.dump(config, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY
python3 "$CONTROL" prepare --config "$BASE/runtime-config.json" --root "$ROOT" --output "$PANEL"
mkdir "$LIBDIR" "$AUDITDIR" "$BASE/annotation-dfam2018" "$BASE/annotation-dfam39-curated"

test -s "$OLD_LIB"
gzip -dc "$OLD_LIB" > "$LIBDIR/dfam2018_consensus.lib"
python3 "$FAMDB" -i "$FAMDB_DB" families -f fasta_name --include-class-in-name -a -d -c 9606 \
  > "$LIBDIR/dfam39_human_curated.fa"
test -s "$LIBDIR/dfam2018_consensus.lib"
test -s "$LIBDIR/dfam39_human_curated.fa"
python3 "$CONTROL" audit-library --library "$LIBDIR/dfam2018_consensus.lib" \
  --label dfam2018_consensus --output "$AUDITDIR/dfam2018_consensus.json"
python3 "$CONTROL" audit-library --library "$LIBDIR/dfam39_human_curated.fa" \
  --label dfam39_human_curated --output "$AUDITDIR/dfam39_human_curated.json"

RM_VERSION="$($RM -v 2>&1 | head -1)"
cat > "$BASE/annotation_metadata.json" <<EOF
{
  "status": "ANNOTATION_INPUTS_READY",
  "slurm_job_id": "$SLURM_JOB_ID",
  "repeatmasker": "$RM_VERSION",
  "flags": ["-pa", "4", "-xsmall", "-gff", "-lib"],
  "panel": "$PANEL/panel.fa",
  "panel_manifest": "$PANEL/panel_manifest.json",
  "target_annotation_read": false,
  "model_scores_read": false,
  "library_only_control": true
}
EOF

"$RM" -pa 4 -xsmall -gff -lib "$LIBDIR/dfam2018_consensus.lib" -dir "$BASE/annotation-dfam2018" \
  "$PANEL/panel.fa" > "$BASE/annotation-dfam2018/run.stdout" 2> "$BASE/annotation-dfam2018/run.stderr" &
LEGACY_PID=$!
"$RM" -pa 4 -xsmall -gff -lib "$LIBDIR/dfam39_human_curated.fa" -dir "$BASE/annotation-dfam39-curated" \
  "$PANEL/panel.fa" > "$BASE/annotation-dfam39-curated/run.stdout" 2> "$BASE/annotation-dfam39-curated/run.stderr" &
CURRENT_PID=$!
wait "$LEGACY_PID"
wait "$CURRENT_PID"
test -s "$BASE/annotation-dfam2018/panel.fa.out"
test -s "$BASE/annotation-dfam39-curated/panel.fa.out"

python3 "$CONTROL" score --config "$BASE/runtime-config.json" --root "$ROOT" --panel-dir "$PANEL" --output "$BASE/score"
cat > "$BASE/completion.json" <<EOF
{
  "status": "COMPLETED",
  "slurm_job_id": "$SLURM_JOB_ID",
  "score": "$BASE/score/summary.json",
  "target_annotation_read": false,
  "same_base_f1_computed": false,
  "fp_rescue_claim": false
}
EOF
echo COMPLETED > "$BASE/STATUS"
