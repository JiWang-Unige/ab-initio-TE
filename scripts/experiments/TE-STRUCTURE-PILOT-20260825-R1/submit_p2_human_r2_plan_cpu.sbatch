#!/usr/bin/env bash
# Deterministic P2-H-R2 plan and CPU gate against frozen R1 corpus 12097860.
# This job does not alter the R1 corpus, masks, denominator, or decision.
# Set R1_CORPUS_ROOT only when the frozen R1 output is stored elsewhere.
#SBATCH --job-name=TE_P2_R2_PLAN
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/p2-r2-plan-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/p2-r2-plan-%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT_ROOT=${ROOT}/scripts/experiments/TE-STRUCTURE-PILOT-20260825-R1
R1_CORPUS_ROOT=${R1_CORPUS_ROOT:-${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p2-corpus-20260828-12097860}
RECORDS=2806
CORPUS=${R1_CORPUS_ROOT}/human_reference_run_masks.jsonl.gz
R1_META=${R1_CORPUS_ROOT}/human_reference_run_masks.meta.json
R1_AUDIT=${R1_CORPUS_ROOT}/sampling_audit.json
R1_DECISION=${R1_CORPUS_ROOT}/decision.json
RUN_ROOT=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p2-r2-plan-${SLURM_JOB_ID}
PLAN=${RUN_ROOT}/p2_human_r2_plan.json
R2_AUDIT=${RUN_ROOT}/r2_sampling_audit.json
GATE=${RUN_ROOT}/r2_cpu_gate.json

mkdir -p "${RUN_ROOT}"
cd "${ROOT}"

python "${SCRIPT_ROOT}/te_span_mlm.py" build-r2-plan \
  --data-jsonl "${CORPUS}" \
  --records "${RECORDS}" \
  --out-json "${PLAN}" \
  >/dev/null

python "${SCRIPT_ROOT}/te_span_mlm.py" audit-corpus \
  --data-jsonl "${CORPUS}" \
  --records "${RECORDS}" \
  --plan-json "${PLAN}" \
  --out-json "${R2_AUDIT}" \
  >/dev/null

python - "${R1_META}" "${R1_AUDIT}" "${R1_DECISION}" "${PLAN}" "${R2_AUDIT}" "${GATE}" <<'PY'
import json
import sys

r1_meta = json.load(open(sys.argv[1], encoding="utf-8"))
r1_saved_audit = json.load(open(sys.argv[2], encoding="utf-8"))
r1_decision = json.load(open(sys.argv[3], encoding="utf-8"))
plan = json.load(open(sys.argv[4], encoding="utf-8"))
r2_audit = json.load(open(sys.argv[5], encoding="utf-8"))

initial = plan["initial"]
final = plan["final"]
criteria = {
    "frozen_r1_retained_records_2806": (
        int(r1_meta["retained_records"]) == 2806
        and int(r1_saved_audit["records"]) == 2806
        and int(plan["records"]) == 2806
    ),
    "frozen_r1_decision_no_go": r1_decision["decision"] == "NO_GO",
    "callable_denominator_unchanged": (
        int(r1_saved_audit["callable_bp"]) == int(r2_audit["callable_bp"])
        and int(initial["callable_bp"]) == int(final["callable_bp"])
        and initial["callable_bp_by_record"] == final["callable_bp_by_record"]
        and final["callable_bp_by_record"] == r2_audit["callable_bp_by_record"]
    ),
    "per_window_span_count_unchanged": (
        initial["selected_spans_by_record"] == final["selected_spans_by_record"]
        and final["selected_spans_by_record"] == r2_audit["selected_spans_by_record"]
        and final["selected_bp_by_record"] == r2_audit["selected_bp_by_record"]
    ),
    "selected_bp_unchanged": (
        int(r1_saved_audit["selected_bp"]) == int(initial["selected_bp"]) == int(final["selected_bp"]) == int(r2_audit["selected_bp"])
    ),
    "neutral_spans_zero": int(r2_audit["neutral_spans"]) == 0,
    "r2_fraction_gate": all(
        float(lower) <= float(r2_audit["selected_span_fractions"][name]) <= float(upper)
        for name, (lower, upper) in plan["fraction_bounds"].items()
    ),
    "r2_boundary_gate": bool(plan["criteria"]["boundary_fraction_at_least_25pct"]),
}
result = {
    "decision": "GO" if all(criteria.values()) else "NO_GO",
    "r1_corpus_root": sys.argv[1].rsplit("/human_reference_run_masks.meta.json", 1)[0],
    "r1_job": 12097860,
    "r2_plan": sys.argv[4],
    "r2_audit": sys.argv[5],
    "records": 2806,
    "criteria": criteria,
    "initial": initial,
    "final": final,
    "r2_audit_summary": {
        "selected_bp": r2_audit["selected_bp"],
        "callable_bp": r2_audit["callable_bp"],
        "selected_span_fractions": r2_audit["selected_span_fractions"],
        "neutral_spans": r2_audit["neutral_spans"],
    },
}
json.dump(result, open(sys.argv[6], "w", encoding="utf-8"), indent=2, sort_keys=True)
open(sys.argv[6], "a", encoding="utf-8").write("\n")
print(json.dumps(result, indent=2, sort_keys=True))
PY
