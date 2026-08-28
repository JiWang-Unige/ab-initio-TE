#!/usr/bin/env bash
#SBATCH --job-name=TE_P2_CORPUS
#SBATCH --partition=private-teodoro-gpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/p2-corpus-%j.out
#SBATCH --error=/home/users/j/jwang/ab-initio-TE/logs/TE-STRUCTURE-PILOT-20260825-R1/p2-corpus-%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
SCRIPT_ROOT=${ROOT}/scripts/experiments/TE-STRUCTURE-PILOT-20260825-R1
RUN_ROOT=${ROOT}/outputs/TE-STRUCTURE-PILOT-20260825-R1/p2-corpus-20260828-${SLURM_JOB_ID}
INPUT=${ROOT}/software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/data/human_h0_w8192/train/data.jsonl.gz
RMSK_OUT=${ROOT}/software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/UCSC_RMSK_SPECIES_ANIMALS_20260617/human_hs1/raw/human_hs1.repeatmasker.out.gz
RMSK_ALL_BED=${RUN_ROOT}/human_hs1_chr1_high_confidence_all.bed
RMSK_BED=${RUN_ROOT}/human_hs1_chr1_0_24576000_high_confidence.bed

mkdir -p "${RUN_ROOT}"
cd "${ROOT}"

python "${SCRIPT_ROOT}/build_high_conf_repeatmasker_sidecar.py" \
  --input-out "${RMSK_OUT}" \
  --output-bed "${RMSK_ALL_BED}" \
  --seqid chr1 \
  > "${RUN_ROOT}/high_conf_repeatmasker_sidecar.json"

awk -F '\t' -v OFS='\t' -v region_end=24576000 \
  '$1 == "chr1" && $2 < region_end && $3 > 0 { if ($2 < 0) $2 = 0; if ($3 > region_end) $3 = region_end; if ($2 < $3) print }' \
  "${RMSK_ALL_BED}" > "${RMSK_BED}"

python "${SCRIPT_ROOT}/build_annotation_span_corpus.py" \
  --input-jsonl "${INPUT}" \
  --output-jsonl "${RUN_ROOT}/human_reference_run_masks.jsonl.gz" \
  --metadata "${RUN_ROOT}/human_reference_run_masks.meta.json" \
  --max-records 3000 \
  --retain-packable-windows 3000 \
  --annotation-bed "${RMSK_BED}" \
  >/dev/null

CORPUS_META=${RUN_ROOT}/human_reference_run_masks.meta.json
RETAINED_RECORDS=$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["retained_records"])' "${CORPUS_META}")

if (( RETAINED_RECORDS > 0 )); then
  python "${SCRIPT_ROOT}/te_span_mlm.py" audit-corpus \
    --data-jsonl "${RUN_ROOT}/human_reference_run_masks.jsonl.gz" \
    --records "${RETAINED_RECORDS}" \
    --out-json "${RUN_ROOT}/sampling_audit.json" \
    >/dev/null
fi

python - "${RUN_ROOT}/decision.json" "${RETAINED_RECORDS}" \
  "${RUN_ROOT}/sampling_audit.json" "${RUN_ROOT}/human_reference_run_masks.jsonl.gz" <<'PY'
import gzip
import json
import sys

retained_records = int(sys.argv[2])
audit = json.load(open(sys.argv[3], encoding="utf-8")) if retained_records > 0 else None
expected_selected_bp = None
if audit is not None:
    expected_selected_bp = 0
    with gzip.open(sys.argv[4], "rt", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if index >= retained_records:
                break
            record = json.loads(line)
            callable_bp = sum(
                not unknown and base.upper() != "N"
                for unknown, base in zip(record["unknown_mask"], record["sequence"])
            )
            target_bp = round(callable_bp * 15 / 100)
            target_spans = target_bp // 32
            if target_bp > 0 and target_spans == 0:
                target_spans = 1
            expected_selected_bp += target_spans * 32
fractions = audit["selected_span_fractions"] if audit is not None else {}
selected_fraction = audit["selected_fraction_of_callable"] if audit is not None else None
fraction_bounds = {
    "interior": [0.40, 0.50],
    "boundary": [0.25, 0.35],
    "flank": [0.20, 0.30],
}
fraction_pass = (
    audit is not None
    and all(
        lower <= float(fractions[name]) <= upper
        for name, (lower, upper) in fraction_bounds.items()
    )
)
fixed_span_fraction_pass = (
    audit is not None
    and int(audit["selected_bp"]) == expected_selected_bp
)
criteria = {
    "retained_records": retained_records >= 1000,
    "selected_span_fractions": fraction_pass,
    "selected_fraction_of_callable_matches_15pct_fixed_span_budget": fixed_span_fraction_pass,
}
json.dump(
    {
        "decision": "GO" if all(criteria.values()) else "NO_GO",
        "retained_records": retained_records,
        "go_threshold": 1000,
        "selected_span_fractions": fractions,
        "selected_fraction_of_callable": selected_fraction,
        "selected_bp": audit["selected_bp"] if audit is not None else None,
        "expected_selected_bp": expected_selected_bp,
        "fixed_span_target_fraction": 0.15,
        "criteria": criteria,
    },
    open(sys.argv[1], "w", encoding="utf-8"),
    indent=2,
    sort_keys=True,
)
PY
