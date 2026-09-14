# HG19 2009 RepeatMasker provenance audit

**Verdict:** `2009_LABEL_MATERIAL_MATCH_RECORD_PROVENANCE_NOT_EXACT`

This audit compares the official UCSC hg19 initial-release `.out` file with the raw training `rmsk.txt.gz` on chr1/2/3/4/11/13 only. Official 1-based closed coordinates were converted to 0-based half-open; `C` strand was converted to `-`; repeat names, classes and families were case-folded to uppercase. IDs and scores were excluded from keys.

Official source: [https://hgdownload.soe.ucsc.edu/goldenPath/hg19/bigZips/hg19.fa.out.gz](https://hgdownload.soe.ucsc.edu/goldenPath/hg19/bigZips/hg19.fa.out.gz) (RepeatMasker open-3-2-7, `-s`, RepBase RELEASE 20090120).

| Scope | Official rows | Training rows | Matched | Official only | Training only |
|---|---:|---:|---:|---:|---:|
| all normalized records | 1918650 | 1918650 | 1608942 | 309708 | 309708 |
| TE normalized records | 1610832 | 1610832 | 1608421 | 2411 | 2411 |
| ignore normalized records | 3898 | 3898 | 16 | 3882 | 3882 |
| TE coordinates + strand | 1610832 | 1610832 | 1610832 | 0 | 0 |

| Chromosome | Official TE bp | Training TE bp | TE intersection bp | Effective P/I intervals equal |
|---|---:|---:|---:|---|
| chr1 | 110017410 | 110017410 | 110017410 | True |
| chr2 | 110570824 | 110570824 | 110570824 | True |
| chr3 | 94136774 | 94136774 | 94136774 | True |
| chr4 | 91732398 | 91732398 | 91732398 | True |
| chr11 | 63436009 | 63436009 | 63436009 | True |
| chr13 | 43791931 | 43791931 | 43791931 | True |

All unmatched normalized keys are retained in `/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/outputs/HG19-CHR1-REVISION-20260914/audit-2009-12698548/report/normalized_differences.tsv.gz` with multiplicities; the raw official download is kept beside the report on Baobab and is not part of the repository.

The verdict closes exact 2009 provenance only when normalized records and effective positive/ignore label material agree. A material-only match is reported separately and should not be described as exact library/engine inheritance.
