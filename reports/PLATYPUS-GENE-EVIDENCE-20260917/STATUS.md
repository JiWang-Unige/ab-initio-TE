# Platypus independent RNA evidence — execution status

Job **12858354 completed** on `shared-cpu` (8 CPU, 32 GB) in **34m34s**, exit 0.
The full-assembly alignment, junction extraction, reference-free StringTie
assembly and blind 1,083-candidate scoring all completed. D has 281/689
multi-exon candidates with all introns supported versus 262/680 for U_soft
and 283/687 for R_TE. Among reference-relative D versus U_soft gains/losses,
22/49 gains and 8/18 losses have strict full-junction support.

See [completed results](run-12858354/RESULTS.md). All candidate outputs from
20 inference regions include halos (104 Mb); the separate gene-reference
comparison uses 100 Mb. The post-hoc chromosome bootstrap is explicitly
exploratory and does not represent independent biological replication.

The selected sequencing run is absent from annotation105's listed RNA inputs
and belongs to a later public study. The data support temporal/study-level
independence from that annotation release; distinct biological individuals
are not established. The stranded kit is known, FR/RF orientation is not
fixed, and the junction endpoint is explicitly strand-agnostic.

## Corrections made before evidence scoring

- The original unstarted job assumed STAR's `SJ.out.tab` after HISAT2; this was
  replaced by primary SAM CIGAR extraction with NH=1 and template de-duplication.
- Alignment uses the complete assembly, avoiding false uniqueness caused by
  excluding genomic alternatives outside the 100-Mb evaluation panel.
- SRA `.1`/`.2` suffixes are retained as distinct templates. Paired mates crossing
  the same junction count once. Each supporting template must itself have
  at least 8 bases on each splice side; one good anchor cannot qualify several
  short-anchor reads. At least three qualifying templates are required.
- The primary StringTie endpoint is the multi-exon intron chain. Full exon-chain
  equality remains secondary because RNA UTR endpoints can differ from coding
  predictions. Single-exon candidates are separate.
- Missing native files raise an error rather than becoming zero RNA support.
- Attempt 12857953 failed after 6 s (exit 78) because SRA Toolkit was not
  configured. The same run's official ENA FASTQ replaces the download route;
  no user-wide SRA configuration or scientific input was changed.

## Verification completed

Both official ENA FASTQ files have downloaded successfully. The native job MD5
values match the ENA file report: read 1 `09b0452420729cfa89a672777b44ff0f`,
read 2 `2878bdc28e2d3c536f3e26899437747c`. The full-assembly alignment and downstream processing completed;
file identity verification is separate from biological support.

`verify_contract.py` passes hand-computable QNAME/mate, NH, splice-coordinate,
per-template-anchor, UTR, single-exon and missing-output cases. On the actual
candidate union, the post-hoc reference join covers all **49 gains / 18 losses**
for D versus U_soft and all **13 gains / 9 losses** for D versus R_TE. This is
coordinate and set-coverage verification, **not RNA validation**.

The existing frozen D result was mirrored to the research report path needed
by the running script before its final join; its native source remains
`outputs/D-TIBERIUS-PLATYPUS-20260917/run/result.json`. Failed attempts remain
separate. Whole-assembly BAM/SAM and FASTQ stay on Baobab; only compact evidence
outputs should be synchronized after the job completes.
