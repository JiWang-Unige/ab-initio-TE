#!/usr/bin/env bash
# Frozen, bounded raw-RNA evidence check for the platypus Tiberius panel.
#SBATCH --job-name=platypus-gene-evidence
#SBATCH --partition=public-cpu
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err

set -euo pipefail

ROOT=/home/users/j/jwang/ab-initio-TE
RUN_ROOT="$ROOT/outputs/PLATYPUS-GENE-EVIDENCE-20260917/run-${SLURM_JOB_ID}"
WORK="${SLURM_TMPDIR:-$RUN_ROOT/work}"
SCRIPT_DIR="$ROOT/scripts/experiments/PLATYPUS-GENE-EVIDENCE-20260917"
CFG="$ROOT/configs/PLATYPUS-GENE-EVIDENCE-20260917.yaml"
IMG=/home/users/j/jwang/ab-initio-TE/software_outputs/tiberius/GAP-BRIDGE-DOWNSTREAM-C-R1/container-20260905-r1/tiberius_2.0.7.sif
GEOMETRY=/home/users/j/jwang/ab-initio-TE/outputs/P3-TIBERIUS-EXTERNAL-20260915/prepared/platypus/geometry.json
PREPARED=/home/users/j/jwang/ab-initio-TE/outputs/P3-TIBERIUS-EXTERNAL-20260915/prepared/platypus
D_GTF=/home/users/j/jwang/ab-initio-TE/outputs/D-TIBERIUS-PLATYPUS-20260917/run/platypus/{core}/D.gtf
U_GTF=/home/users/j/jwang/ab-initio-TE/outputs/P3-TIBERIUS-EXTERNAL-20260915/run-r1/platypus/{core}/U_soft.gtf
R_GTF=/home/users/j/jwang/ab-initio-TE/outputs/P3-TIBERIUS-EXTERNAL-20260915/run-r1/platypus/{core}/R_TE.gtf
REFERENCE=/home/users/j/jwang/ab-initio-TE/outputs/P3-TIBERIUS-EXTERNAL-20260915/prepared/platypus/reference.json
HISTORICAL=/home/users/j/jwang/ab-initio-TE/reports/D-TIBERIUS-PLATYPUS-20260917/result.json
ASSEMBLY_DIR=/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/software_outputs/L1-PANEL-PREP-20260908-kqZrej
ASSEMBLY_GZ="$ASSEMBLY_DIR/GCF_004115215.2_mOrnAna1.pri.v4_genomic.fna.gz"

mkdir -p "$RUN_ROOT" "$WORK" "$WORK/tmp" "$WORK/fastq" "$RUN_ROOT/prepared" "$RUN_ROOT/logs"
date -Is > "$RUN_ROOT/logs/start-time.txt"
printf 'job_id=%s\nrun_root=%s\nwork=%s\ncpus=%s\n' "$SLURM_JOB_ID" "$RUN_ROOT" "$WORK" "${SLURM_CPUS_PER_TASK:-8}" > "$RUN_ROOT/provenance.txt"
cp "$CFG" "$RUN_ROOT/protocol.yaml"

python3 "$SCRIPT_DIR/prepare_candidates.py" \
  --geometry "$GEOMETRY" \
  --prepared-regions "$PREPARED" \
  --d-gtf-template "$D_GTF" \
  --u-soft-gtf-template "$U_GTF" \
  --r-te-gtf-template "$R_GTF" \
  --out-dir "$WORK/panel" \
  | tee "$RUN_ROOT/logs/prepare-candidates.json"
cp "$WORK/panel/blind_candidates.json" "$RUN_ROOT/prepared/"
cp "$WORK/panel/blind_candidates.tsv" "$RUN_ROOT/prepared/"
cp "$WORK/panel/panel_manifest.json" "$RUN_ROOT/prepared/"
cp "$WORK/panel/blind_panel.fa" "$RUN_ROOT/prepared/"

R1_URL=https://ftp.sra.ebi.ac.uk/vol1/fastq/SRR232/062/SRR23268362/SRR23268362_1.fastq.gz
R2_URL=https://ftp.sra.ebi.ac.uk/vol1/fastq/SRR232/062/SRR23268362/SRR23268362_2.fastq.gz
ENA_API='https://www.ebi.ac.uk/ena/portal/api/filereport?accession=SRR23268362&result=read_run&fields=run_accession,fastq_ftp,fastq_bytes,fastq_md5&format=tsv'
curl -fsSL --retry 3 --retry-delay 3 --connect-timeout 30 "$ENA_API" \
  > "$RUN_ROOT/logs/ena-filereport.tsv" || echo 'ENA API metadata request failed; static official URLs retained' > "$RUN_ROOT/logs/ena-filereport.tsv"
R1="$WORK/fastq/SRR23268362_1.fastq.gz"
R2="$WORK/fastq/SRR23268362_2.fastq.gz"
curl --fail --location --retry 5 --retry-all-errors --retry-delay 5 --connect-timeout 30 \
  --continue-at - --output "$R1" "$R1_URL" > "$RUN_ROOT/logs/ena-read1.log" 2>&1
curl --fail --location --retry 5 --retry-all-errors --retry-delay 5 --connect-timeout 30 \
  --continue-at - --output "$R2" "$R2_URL" > "$RUN_ROOT/logs/ena-read2.log" 2>&1
if [[ ! -s "$R1" || ! -s "$R2" ]]; then
  echo 'paired ENA FASTQ download is missing or empty' >&2
  exit 2
fi
printf 'read1=%s\nread2=%s\n' "$R1" "$R2" >> "$RUN_ROOT/provenance.txt"
md5sum "$R1" "$R2" > "$RUN_ROOT/logs/ena-md5.txt"

printf 'assembly=%s\n' "$ASSEMBLY_GZ" >> "$RUN_ROOT/provenance.txt"
gzip -dc "$ASSEMBLY_GZ" > "$WORK/reference.fa"

BIND="${RUN_ROOT}:/run,${WORK}:/work,${ASSEMBLY_DIR}:/assembly:ro"
singularity exec --cleanenv --bind "$BIND" --pwd /work "$IMG" \
  hisat2-build -p 8 /work/reference.fa /work/full_index \
  > "$RUN_ROOT/logs/hisat2-build.log" 2>&1
singularity exec --cleanenv --bind "$BIND" --pwd /work "$IMG" \
  hisat2 -p 8 --dta -x /work/full_index -1 "/work/fastq/$(basename "$R1")" \
  -2 "/work/fastq/$(basename "$R2")" --summary-file /run/logs/hisat2.summary \
  -S /work/aln.sam > "$RUN_ROOT/logs/hisat2.stdout" 2> "$RUN_ROOT/logs/hisat2.stderr"
singularity exec --cleanenv --bind "$BIND" --pwd /work "$IMG" \
  samtools view -F 2308 /work/aln.sam \
  | python3 "$SCRIPT_DIR/extract_junctions.py" --min-overhang 8 --out "$RUN_ROOT/junctions.tsv" \
  > "$RUN_ROOT/logs/extract-junctions.json"
singularity exec --cleanenv --bind "$BIND" --pwd /work "$IMG" bash -lc \
  'samtools view -@ 8 -b /work/aln.sam | samtools sort -@ 8 -o /work/aln.bam - && samtools index -@ 8 /work/aln.bam' \
  > "$RUN_ROOT/logs/samtools.log" 2>&1
rm -f "$WORK/aln.sam"
singularity exec --cleanenv --bind "$BIND" --pwd /work "$IMG" \
  stringtie /work/aln.bam -p 8 -o /run/stringtie.gtf -l RNAEVID \
  > "$RUN_ROOT/logs/stringtie.stdout" 2> "$RUN_ROOT/logs/stringtie.stderr"

python3 "$SCRIPT_DIR/summarize_evidence.py" \
  --candidates "$WORK/panel/blind_candidates.json" \
  --junctions "$RUN_ROOT/junctions.tsv" \
  --stringtie "$RUN_ROOT/stringtie.gtf" \
  --hisat2-summary "$RUN_ROOT/logs/hisat2.summary" \
  --geometry "$GEOMETRY" \
  --coordinate-mode assembly \
  --reference-json "$REFERENCE" \
  --historical-result "$HISTORICAL" \
  --out-dir "$RUN_ROOT/report" \
  | tee "$RUN_ROOT/logs/summarize.json"
cp "$RUN_ROOT/report"/* "$RUN_ROOT/" 2>/dev/null || true
du -sh "$RUN_ROOT" > "$RUN_ROOT/output-size.txt"
date -Is > "$RUN_ROOT/logs/end-time.txt"
echo "completed_run=$RUN_ROOT"
