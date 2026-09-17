# PLATYPUS-GENE-EVIDENCE-20260917

This experiment tests whether the positive Tiberius downstream result on
platypus has support from a source that was not available when the current
assembly-matched RefSeq annotation was submitted. It is an evidence audit,
not a replacement gene annotation and not an independent biological truth set.

## Frozen provenance and independence boundary

The reference assembly is `GCF_004115215.2` (`mOrnAna1.pri.v4`, taxid 9258).
NCBI Annotation Release 105 identifies the annotation submission date as
2021-03-08 and describes Gnomon models with RNA and protein similarity
evidence. The local D/P3 reference contains 639 complete standard CDS-chain
loci selected from that release. That reference is therefore retained only for
a post-hoc coordinate join; it is not used to construct the blind panel or to
call a predicted gene supported.

The external raw-data source is NCBI `PRJNA929280`, run `SRR23268362`
(`SRX19212274`, `SAMN32954940`), an adult male platypus fibroblast paired-end
RNA-seq run from the UNSW HiSeq 2000 study (TruSeq Total RNA STRANDED),
submitted 2023-01-29 and made public in 2024. NCBI reports 5,552,048,376 bases
and an archive of about 3.57 GB for this run. The Annotation Release 105 input
table queried 2021-03-03 has no target run/BioSample; its older fibroblast entry
is the separate 2012 `PRJNA152927/SRR414997` run. This supports an independent
public sequencing study/run relative to the 2021 annotation inputs. Public
metadata do not provide an individual ID, so the experiment does not establish
that the sequenced animal differs from every animal used in earlier work.
RefSeq and UniProt proteins are not used as truth in this experiment.
The public run metadata do not provide a verified FR/RF orientation contract
for this analysis, so the raw junction endpoint is strand-agnostic and cannot
be used to prove the direction of a predicted transcript.

The tissue restriction is material: no RNA support from this single adult-male
fibroblast run is an unobserved-expression result, not evidence that a
prediction is false. A positive result is evidence of transcription/splicing
in this tissue and run, not proof of complete gene correctness.

## Frozen panel and input pairing

The panel uses the already selected 20 platypus cores (5 Mb each with 100 kb
halos). For each core, the union contains every transcript exon chain emitted
by these three fixed arms:

* D: the new Tiberius run;
* U_soft: the prior unmasked/reference-softmask control;
* R_TE: the prior RepeatMasker-TE mask control.

Candidate selection is blind to `reference.json`, historical F1 values, the
D-vs-control gain/loss lists, RNA coverage, junctions, and model scores. An
exact candidate is a `(native panel contig, strand, ordered exon chain)` tuple;
duplicate chains emitted by multiple arms are one candidate with an arm-membership
set. The panel fasta preserves the native contig and local one-based GTF
coordinates.

The preparation script records the candidate union and overlap counts. In the
observed preparation, the three arms emitted 762, 754, and 766 transcript
records (D, U_soft, and R_TE), which collapsed to 1,083 exact exon-chain
candidates. The overlap breakdown was 502 shared by all three, 157 D+R_TE,
31 D+U_soft, 7 R_TE+U_soft, 72 D-only, 214 U_soft-only, and 100 R_TE-only.
These are candidate-panel counts, not biological performance metrics.

## Evidence procedure

The single bounded CPU job is configured for 8 CPU, 32 GB RAM, and 4 hours.
The paired FASTQ files are fetched over HTTPS from the official ENA files for
the same `SRR23268362` accession. This avoids a site-local SRA Toolkit
configuration failure while preserving the raw sequencing input; the ENA
filereport and local MD5 sums are retained in the run logs. The raw paired
reads are aligned to the complete `GCF_004115215.2` assembly
with HISAT2 from the pinned Tiberius 2.0.7 container using DTA mode. This
full-assembly alignment is required so that a read mapping to a different
chromosome or unplaced contig is not incorrectly called unique merely because
it is absent from the 20-core panel. Candidate chains are then projected from
their native panel coordinates to assembly coordinates. The strict junction
threshold is at least 3 primary `NH:i:1` alignment templates and an 8-base splice
overhang. HISAT2 does not produce STAR's `SJ.out.tab`; the report derives
junctions directly from primary SAM CIGAR `N` operations. Only trailing `/1`
and `/2` suffixes are normalized; `.1` and `.2` are retained exactly. Adjacent
NH=1 records are de-duplicated, so a junction traversed by both records of one
template contributes once. The procedure assumes the normal HISAT2 SAM
property that paired records are adjacent.

StringTie is run de novo without a reference GTF, so its exact-chain endpoint
is an assembly of the same raw reads rather than an external gold standard.

For each candidate, the report records the number and fraction of expected
introns with strict junction support, whether all expected introns are
strictly supported, exact de-novo StringTie intron-chain support, full
exon-chain support as a stricter diagnostic, and any-strand diagnostics. A
strict junction count is calculated per template after requiring that template's
two flanking continuous matches to meet the 8-base overhang; short-anchor
templates therefore cannot be rescued by a separate long-anchor template in
the same total. The primary summaries are calculated by arm membership
and by arm-overlap category. One-exon candidates are kept in the panel and are
reported separately because a splice-junction endpoint is not defined for
them.

The optional reference join is performed only after the blind evidence rows
are generated. It maps exact panel chains to assembly-matched RefSeq isoforms
and reports how the historical D-vs-U_soft loss/gain and D-vs-R_TE loss/gain
sets intersect the RNA evidence. This join cannot change the blind candidate
denominators and must be described as reference-relative exploratory analysis.

## Interpretation rules

The experiment can support a statement such as “a subset of predicted
transcripts, including candidates emitted by the D arm, has independent
temporal raw-RNA splice or de-novo chain support in adult-male fibroblast.” It
cannot support “all D gains are correct,” “unsupported genes are false,” or a
genome-wide independent accuracy estimate. Any downstream manuscript table
must show the raw run accession, the one-tissue boundary, the blind union
contract, and the number of candidates with each evidence type.

## Files

* `configs/PLATYPUS-GENE-EVIDENCE-20260917.yaml`: frozen inputs, thresholds,
  resource budget, and interpretation boundary.
* `scripts/experiments/PLATYPUS-GENE-EVIDENCE-20260917/prepare_candidates.py`:
  blind candidate union and panel fasta construction.
* `scripts/experiments/PLATYPUS-GENE-EVIDENCE-20260917/run.sbatch`: one bounded
  Slurm execution using official ENA FASTQ, the full-assembly HISAT2 index,
  samtools, and StringTie. A prior attempt using site SRA Toolkit is retained
  as an execution failure (`vdb-config` was unconfigured), not as a result.
* `scripts/experiments/PLATYPUS-GENE-EVIDENCE-20260917/extract_junctions.py`:
  primary `NH:i:1` CIGAR-junction extraction into a six-column summary; it
  does not assume a STAR output file.
* `scripts/experiments/PLATYPUS-GENE-EVIDENCE-20260917/summarize_evidence.py`:
  primary evidence and post-hoc reference-join summary.

Primary external records: [NCBI Annotation Release 105 for platypus](https://www.ncbi.nlm.nih.gov/refseq/annotation_euk/Ornithorhynchus_anatinus/105/),
[PRJNA929280](https://www.ncbi.nlm.nih.gov/bioproject/929280), and
[SRX19212274](https://www.ncbi.nlm.nih.gov/sra/SRX19212274). The associated
study record is [PMC11317591](https://pmc.ncbi.nlm.nih.gov/articles/PMC11317591/);
the study-level paper is used only to document source provenance, not as a
gene truth set.

## Execution update

The official-ENA replacement job is **12858354**, shared-cpu, 8 CPUs, 32 GB,
4-hour ceiling. It is running; no RNA validation result is claimed yet.
Failed/unstarted attempts and successful coordinate/set-coverage checks are
recorded in `reports/PLATYPUS-GENE-EVIDENCE-20260917/STATUS.md` and `jobs.json`.
The observed 1,083-candidate union covers all 49/18 historical D-versus-U_soft
gains/losses and all 13/9 D-versus-R_TE gains/losses in the post-hoc join.
That complete join checks coordinates and coverage, not RNA support.
