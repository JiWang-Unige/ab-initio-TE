#!/usr/bin/env bash
# Exact current Base-CE edge-position audit on the frozen human_h0_w8192 test set.
# Resource selection is intentionally left to submission CLI, e.g. --time=12:00:00 --gres=gpu:a100:1.
#SBATCH --job-name=dapt_base_ce_edge
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/DAPT-DIRECT-ANNOTATION-20260824-BASE-CE-EDGE/edge_%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/DAPT-DIRECT-ANNOTATION-20260824-BASE-CE-EDGE/edge_%j.err

set -euo pipefail
ROOT=/home/users/j/jwang/ab-initio-TE
EXP_BASE=DAPT-DIRECT-ANNOTATION-20260824-BASE-CE-EDGE
EXP="${EXP_BASE}-${SLURM_JOB_ID:?SLURM_JOB_ID is required}"
MODEL_DIR="$ROOT/software_outputs/p1_c1_structure_20260824/runs/screen_ce_12059660_0"
DATA_DIR="$ROOT/software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/data/human_h0_w8192"
STATUS_ROOT="$ROOT/outputs/$EXP"
REPORT_ROOT="$ROOT/reports/$EXP"

eval "$(conda shell.bash hook)"
conda activate te_benchmark
cd "$ROOT"
mkdir -p "$STATUS_ROOT" "$REPORT_ROOT" "$ROOT/logs/$EXP_BASE"
printf 'RUNNING\n' > "$STATUS_ROOT/STATUS"
trap 'rc=$?; if ((rc == 0)); then printf "COMPLETED\n" > "$STATUS_ROOT/STATUS"; else printf "FAILED\n" > "$STATUS_ROOT/STATUS"; fi; exit "$rc"' EXIT

test -d "$MODEL_DIR"
test -s "$DATA_DIR/test/data.jsonl.gz"
python3 pipelines/PIPE-TEFM-SUPP-20260617/edge_position_analysis.py \
  --model-dir "$MODEL_DIR" \
  --data-dir "$DATA_DIR" \
  --out-tsv "$REPORT_ROOT/edge_position.tsv" \
  --batch-size 1 \
  --max-samples 1200 \
  --stage base_ce_edge_audit \
  --model-key base_ce \
  --window 8192 \
  --species human
