#!/bin/bash
#SBATCH --job-name=tib-external-data
#SBATCH --partition=shared-cpu
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=04:00:00
#SBATCH --output=outputs/P3-TIBERIUS-EXTERNAL-20260915/logs/acquire-%j.log
set -euo pipefail
TASK_ROOT=/home/users/j/jwang/ab-initio-TE
cd "$TASK_ROOT"
TE_DEST=software_outputs/P3-TIBERIUS-EXTERNAL-20260915/source
mkdir -p "$TE_DEST/cow" "$TE_DEST/platypus" "$TE_DEST/tiberius"
for TE_ITEM in genomic.fna.gz genomic.gff.gz assembly_report.txt; do
  TE_NAME="GCF_002263795.3_ARS-UCD2.0_${TE_ITEM}"
  curl -L --fail --retry 2 --connect-timeout 30 \
    "https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/002/263/795/GCF_002263795.3_ARS-UCD2.0/$TE_NAME" \
    -o "$TE_DEST/cow/$TE_NAME.part"
  mv "$TE_DEST/cow/$TE_NAME.part" "$TE_DEST/cow/$TE_NAME"
done
TE_NAME=GCF_004115215.2_mOrnAna1.pri.v4_genomic.gff.gz
curl -L --fail --retry 2 --connect-timeout 30 \
  "https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/004/115/215/GCF_004115215.2_mOrnAna1.pri.v4/$TE_NAME" \
  -o "$TE_DEST/platypus/$TE_NAME.part"
mv "$TE_DEST/platypus/$TE_NAME.part" "$TE_DEST/platypus/$TE_NAME"
curl -L --fail --retry 2 --connect-timeout 30 \
  https://bioinf.uni-greifswald.de/bioinf/tiberius/models/tiberius_nosm_weights_v2.tar.gz \
  -o "$TE_DEST/tiberius/tiberius_nosm_weights_v2.tar.gz.part"
mv "$TE_DEST/tiberius/tiberius_nosm_weights_v2.tar.gz.part" "$TE_DEST/tiberius/tiberius_nosm_weights_v2.tar.gz"
date -u +%FT%TZ > "$TE_DEST/acquired_at.txt"
