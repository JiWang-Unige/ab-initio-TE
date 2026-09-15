#!/bin/bash
#SBATCH --job-name=te-lib-orthogonal
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=outputs/ANNOTATION-LIBRARY-CONTROL-20260915/orthogonal-%j.log

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
cd "$ROOT"
source /opt/ebsofts/Mamba/23.1.0-4/etc/profile.d/conda.sh
conda activate te_benchmark

BASE="$ROOT/outputs/ANNOTATION-LIBRARY-CONTROL-20260915/orthogonal-run-${SLURM_JOB_ID}"
MATCHING=scripts/experiments/ANNOTATION-LIBRARY-CONTROL-20260915/matching_sensitivity.py
PROTEIN=scripts/experiments/ANNOTATION-LIBRARY-CONTROL-20260915/protein_support.py
QUALIFICATION="$ROOT/outputs/HG19-CHR1-REVISION-20260914-MATCHED/match-12708406/interval_qualification.tsv"
MATCHED="$ROOT/outputs/HG19-CHR1-REVISION-20260914-MATCHED/match-12708406/matched_controls.tsv"
SOURCE_FASTA="$ROOT/data/raw/ucsc/human/hg19/hg19.fa.gz"
PROTEIN_DB="$ROOT/refs/repos/hite_3_3_3/library/RepeatPeps.lib"

test ! -e "$BASE"
test -s "$QUALIFICATION"
test -s "$MATCHED"
test -s "$SOURCE_FASTA"
test -s "$PROTEIN_DB.pin"
mkdir "$BASE"

python3 "$MATCHING" \
  --qualification "$QUALIFICATION" \
  --allowed-chromosomes chr2 chr3 chr4 \
  --output "$BASE/no-reuse"

python3 "$PROTEIN" build-queries \
  --matched-controls "$MATCHED" \
  --additional-matches "$BASE/no-reuse/matched_controls_no_reuse.tsv" \
  --source-fasta "$SOURCE_FASTA" \
  --output "$BASE/query"

BLASTX_VERSION="$(blastx -version 2>&1 | head -1)"
cat > "$BASE/run_metadata.json" <<EOF
{
  "status": "BLASTX_RUNNING",
  "slurm_job_id": "$SLURM_JOB_ID",
  "blastx": "$BLASTX_VERSION",
  "database": "$PROTEIN_DB",
  "query_fasta": "$BASE/query/queries.fa",
  "query_scope": ["chr2", "chr3", "chr4"],
  "target_annotation_read": false,
  "model_scores_read": false,
  "selection_uses_new_library_support": false
}
EOF

blastx \
  -query "$BASE/query/queries.fa" \
  -db "$PROTEIN_DB" \
  -out "$BASE/blastx.tsv" \
  -evalue 1e-5 \
  -seg yes \
  -max_target_seqs 5 \
  -max_hsps 1 \
  -num_threads 4 \
  -outfmt "6 qseqid sseqid evalue bitscore length qstart qend sstart send qlen qcovhsp"
test -f "$BASE/blastx.tsv"

python3 "$PROTEIN" summarize \
  --query-dir "$BASE/query" \
  --blastx "$BASE/blastx.tsv" \
  --no-reuse-matches "$BASE/no-reuse/matched_controls_no_reuse.tsv" \
  --output "$BASE/protein-summary"
cat > "$BASE/completion.json" <<EOF
{
  "status": "COMPLETED",
  "slurm_job_id": "$SLURM_JOB_ID",
  "no_reuse_summary": "$BASE/no-reuse/summary.json",
  "protein_summary": "$BASE/protein-summary/summary.json",
  "raw_blastx_retained_on_baobab": true,
  "target_annotation_read": false,
  "same_base_f1_computed": false,
  "fp_rescue_claim": false
}
EOF
echo COMPLETED > "$BASE/STATUS"
