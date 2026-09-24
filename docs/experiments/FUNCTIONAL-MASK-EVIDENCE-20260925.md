# FUNCTIONAL-MASK-EVIDENCE-20260925

## Status

`READINESS_AUDIT_COMPLETED` (2026-09-25). This document is an evidence
availability audit for the proposed functional selective masking experiment.
It is not a launch authorization, a new training protocol, or a result of the
pilot. No raw reads were downloaded or remapped in this audit, and no
threshold, seed, species, denominator, or frozen 20260918 result was changed.

The purpose is to decide whether a confirmation experiment can be built from
independent evidence. The central experiment discussion defines the intended
claim: at equal masking budget, a fixed TE-supervised model may choose mask
positions that improve host-gene recovery while reducing autonomous-TE coding
units being absorbed into host gene models. That claim requires a host set
(`H`) and an autonomous-TE set (`E`) whose labels are not copied from the
same gene-prediction or model output being evaluated.

See [the central claim discussion](../manuscript/20260924/central-claim-discussion.md),
[the existing platypus RNA protocol](PLATYPUS-GENE-EVIDENCE-20260917.md), and
the machine-readable [evidence manifest](../../reports/FUNCTIONAL-MASK-EVIDENCE-20260925/evidence_manifest.tsv).

## Existing evaluation context

The current chicken and zebrafish utility experiments use the exact reference
assemblies `galGal6`/`GCA_000002315.5` and `danRer11`/`GCA_000002035.4`.
They are D-training species, so their 10 fixed 5-Mb cores are suitable for a
development pilot but cannot by themselves establish unseen-species transfer.
The observed utility results are retained unchanged:

* Chicken: D versus U F1 is `+0.013201`; D is slightly below the historical
  same-assembly TE mask (`D-R_TE = -0.005125`).
* Zebrafish: D versus U F1 is `+0.098274`; D is slightly above the historical
  TE mask (`D-R_TE = +0.009632`).
* Platypus: the existing single adult-male fibroblast RNA run supports splice
  junctions and de-novo chains only. It does not provide a complete-CDS truth
  set, and lack of support is not a negative label.

These values motivate the pilot but must not be re-used as an independent
confirmation endpoint.

## Evidence found

### Chicken host-transcript evidence

`PRJNA670545` contains PacBio Sequel II full-length RNA from male and female
embryo/gonad samples. The source article states that high-quality isoforms were
mapped to `Galgal6`. The two large runs identified in the official SRA records
are:

| accession | sample | platform | bases / archive size | role |
|---|---|---|---:|---|
| `SRR13084015` (`SRX9530712`, `SAMN16512680`) | male embryo/gonad, multiple developmental stages | PacBio Sequel II | 78,723,364,225 bases; ~19,158 MB | full-length transcript and splice support in sampled tissues |
| `SRR13084014` (`SRX9530713`, `SAMN16512697`) | female embryo/gonad, multiple developmental stages | PacBio Sequel II | 71,469,274,780 bases; ~17,397 MB | full-length transcript and splice support in sampled tissues |

This is the strongest currently identified exact-assembly long-read source for
the chicken arm. It supports complete transcript structures only for expressed
genes in the sampled material; it is not a genome-wide negative set and does
not independently establish every start, stop, or coding frame. The source
records are [BioProject PRJNA670545](https://www.ncbi.nlm.nih.gov/bioproject/670545)
and the primary study [PMC11515837](https://pmc.ncbi.nlm.nih.gov/articles/PMC11515837/).

`PRJNA699861`/`GSE166257` provides multi-tissue short-read chicken RNA with
two biological replicates across ten cell or tissue types (about 262 Gb in
the study). It is useful for junction and expression support after a frozen
mapping protocol, but not for complete CDS truth. The study record is
[PRJNA699861](https://www.ncbi.nlm.nih.gov/bioproject/699861).

### Zebrafish host-transcript evidence

`PRJNA973729` contains PacBio full-length RNA from 21 embryonic stages of
strain AB. The study states that CCS reads were mapped to `GRCz11`, yielding
49,624 merged transcripts, including 2,112 unannotated transcripts and 33,018
novel isoforms. Representative runs are:

| accession | stage | bases / archive size | role |
|---|---|---:|---|
| `SRR24682234` | 1–4 somites | 2,199,775,856 bases; ~927 MB | full-length transcript support |
| `SRR24682235` | 1-cell | 2,275,468,478 bases; ~1,000 MB | full-length transcript support |
| `SRR24682222` | 128-cell | 2,358,442,303 bases; ~1,019 MB | full-length transcript support |
| `SRR24682224` | 2-cell | 2,615,775,919 bases; ~1,129 MB | full-length transcript support |
| `SRR24682233` | 14–19 somites | 2,511,998,751 bases; ~1,068 MB | full-length transcript support |
| `SRR24682231` | 20–25 somites | 2,078,794,793 bases; ~882 MB | full-length transcript support |

The remaining stage runs are listed in the manifest. This is an exact-current-
assembly long-read source, but it is embryo restricted. It can support
`H_transcript_full` for expressed embryonic loci, not absence-based negatives or adult
genome-wide completeness. Sources are [BioProject PRJNA973729](https://www.ncbi.nlm.nih.gov/bioproject/973729),
the primary study [PMC12139336](https://pmc.ncbi.nlm.nih.gov/articles/PMC12139336/),
and the authors' processed annotation repository
[crystalBo/zebrafish_full-length_iso-seq](https://github.com/crystalBo/zebrafish_full-length_iso-seq).

`PRJNA899844` includes PacBio liver, brain, muscle, and larvae data, with
matched Illumina runs. The published processed records use `GRCz9`, so they
must be remapped to `GRCz11` before use and cannot be treated as exact-current
assembly truth by simply importing the published GTF or translated FASTA.
The raw-data record is [PRJNA899844](https://www.ncbi.nlm.nih.gov/bioproject/899844).

### Independent host-protein support

The PNAS chicken/platypus dosage-compensation study provides a matched RNA and
mass-spectrometry resource. The raw proteomics project is
[PXD040182](https://www.ebi.ac.uk/pride/archive/projects/PXD040182), and the
study is [PMC11317591](https://pmc.ncbi.nlm.nih.gov/articles/PMC11317591/).
It contains chicken and platypus heart/liver protein measurements and
platypus fibroblast material. The study's MS search used ProteinPilot against
SwissProt with an unused-ProtScore threshold above 1.3 (reported as >95%
confidence).

This is independent protein evidence for already represented host proteins,
but it is not an independent discovery database for novel model-predicted CDS.
The summaries cannot be used to call every unobserved model prediction false.
Re-searching raw spectra against a frozen external translation set would be a
new, heavy, pre-registered protocol and is not part of this readiness audit.

### Positive autonomous-TE structural evidence

Two limited, high-confidence positive panels are available without using the
current D output as truth:

* In chicken `GRCg6a`, the ALVE/GGERV20 study
  ([PMC7597685](https://pmc.ncbi.nlm.nih.gov/articles/PMC7597685/)) reports
  structural integrity and copy evidence for endogenous avian leukosis virus
  elements. `GGERV20` is reported as a 5,827-bp element with putative gag/pol
  ORFs and at least 65 full-length copies in `GRCg6a`; ALVE-JFevB is inserted
  in GGERV20. Exact coordinates and the paper's population filters must be
  extracted before any locus is placed in `E`.
* In zebrafish `GRCz11`, the ZB/Tc1-mariner study
  ([PMC7913693](https://pmc.ncbi.nlm.nih.gov/articles/PMC7913693/)) reports
  autonomous candidates with terminal inverted repeats, target-site
  duplications, intact transposase ORFs and copy evidence. The paper describes
  10 putative autonomous elements, 20 full-length ZB copies and 19 intact or
  putatively functional copies. Exact coordinates and the paper's independent
  sequence criteria must be extracted before use.

These are positive structural panels, not complete TE truth. They were found
by independent studies and are appropriate for a small predeclared `E_structural`
panel. They do not justify calling all other repeat intervals negatives.

### Platypus evidence and its gap

The current exact-assembly platypus source remains
`PRJNA929280`/`SRR23268362` (adult-male fibroblast short-read RNA), already
analysed in [the existing report](../../reports/PLATYPUS-GENE-EVIDENCE-20260917/run-12858354/RESULTS.md).
`PXD040182` adds independent heart/liver protein support. I did not identify a
public PacBio Iso-Seq dataset that is both platypus and already on the current
`GCF_004115215.2` (`mOrnAna1.pri.v4`) assembly. The CARP study
([PMC5851578](https://pmc.ncbi.nlm.nih.gov/articles/PMC5851578/)) reports
full-length L2 candidates and intact ORF2 in an older platypus assembly, but
those loci require an explicit liftover/assembly-compatibility audit and must
not be inserted directly into the current `E` set. This is a real readiness
limitation, not a reason to label unsupported loci negative.

## Non-circular construction contract

The minimum defensible evidence labels are:

* `H_transcript_full`: exact-assembly full-length long-read transcript. This
  establishes a transcript structure in sampled material; it does not by
  itself establish the CDS start, stop, frame, or translation.
* `H_CDS_full`: a stricter subset of `H_transcript_full` whose coding start,
  stop and frame are independently supported by a frozen coding rule and an
  external protein/orthology source. A translated GTF model or the same
  candidate's protein is not independent evidence. This category may be empty
  until the protein/search rule is executed.
* `H_splice`: independent junction or intron-chain support without a complete
  CDS endpoint. This is a secondary endpoint, not a full-CDS truth label.
* `H_supportive`: external orthology/synteny or SwissProt peptide support that
  does not establish the complete current-assembly transcript.
* `E_structural`: independently reported TE structure/copy evidence on the
  exact assembly, such as TIR/TSD, intact transposase or gag/pol ORF and a
  documented multi-copy family. Exact coordinates and inclusion criteria must
  be frozen before looking at D outputs.
* `E_transcribed`: TE-associated transcript or expression evidence without
  autonomous structural proof. Report separately from `E_structural`.
* `uncertain`: conflicting, partial, assembly-mismatched, or insufficient
  evidence. It is excluded from the primary binary endpoint and retained in a
  sensitivity table.

The host and TE sets must be assembled from source records, coordinates and
rules fixed before matching to D/U/R masks. The same candidate-derived GTF,
translated protein, D mask, D class, or historical F1 cannot be used to create
its own truth label. The complement of `H` or `E` is not a negative set.

## Minimal next stage if root authorizes execution

1. Extract exact coordinates and source filters for the chicken ALVE/GGERV20
   and zebrafish ZB panels, and freeze a small `E_structural` table without
   opening D/U/R outputs.
2. From `PRJNA670545` and `PRJNA973729`, remap a predeclared, tissue-balanced
   subset of long-read data to `GCA_000002315.5` and `GCA_000002035.4` in a
   private Slurm job. Score `H_transcript_full` and `H_splice` separately.
   Promote a locus to `H_CDS_full` only when the independent coding/protein
   rule is met; do not use no-read loci as negatives.
3. Join PXD040182 peptide evidence only as a separate H-support column. If raw
   spectra are re-searched, first write a new frozen protocol and obtain a
   separate resource decision.
4. Run the fixed D/U/R/strong-control position intervention only after the
   evidence table, regions, equal-budget matching and primary endpoint are
   frozen. Keep the development pilot separate from any external confirmation.

The audit therefore supports proceeding to a small, explicit evidence-panel
stage for chicken and zebrafish. It does not support claiming a complete
genome-wide H/E truth set or an exact-assembly platypus long-read confirmation
without additional data work.

## 2026-09-25 structural-panel extraction

The published zebrafish supplement was downloaded through Europe PMC and
parsed locally from `Supplementary Table S4`. It gives 20 coordinate-resolved
full-length ZB copies on GRCz11 RefSeq/NCBI accessions, each 1,597 bp with a
341-aa transposase and `TA` target-site duplication. The article reports 19
intact/putatively functional copies in aggregate, but the supplement does not
assign that 19/20 distinction to copy IDs; therefore all 20 are retained as
coordinate-resolved structural candidates, with the aggregate qualification
reported as a sensitivity caveat.

The chicken article prints two exact GRCg6a coordinates: `ALVE6` at
`chr1:210601-214776` and `ALVE-JFevB` at `chr1:32724216-32731739` (source
coordinates are 1-based inclusive). ALVE6 is 5-prime truncated and is kept as
`E_structural_partial` for sensitivity only. ALVE-JFevB is intact with gag-pol
and envelope ORFs and flanking `GGCTTG` target-site duplications, so it is the
single primary chicken autonomous-candidate locus. The paper's `>=65`
full-length GGERV20 copy count has no per-copy coordinate table in the
accessible record and is explicitly excluded from the candidate denominator.

The extraction script is
[`extract_structural_panels.py`](../../scripts/experiments/FUNCTIONAL-MASK-EVIDENCE-20260925/extract_structural_panels.py).
It validates the NCBI assembly reports, parses the ZB DOCX table, records the
chicken source coordinates, and intersects only with the fixed utility-panel
geometry. It does not read any D/U/R mask, inference, score, or gene-output
file. The resulting [structural panel table](../../reports/FUNCTIONAL-MASK-EVIDENCE-20260925/evidence/structural_panels/structural_panels.tsv)
contains 22 coordinate-resolved candidates, of which 21 are full-length
structural candidates. Only the chicken ALVE-JFevB locus currently meets the
primary autonomous-candidate rule; the 20 ZB loci remain per-copy autonomy
pending because the source reports 19/20 intact only in aggregate. The 22 loci
represent two source family units, not 22 independent TE families. **None overlap the existing ten chicken cores or
their halos; none of the 20 ZB copies overlap the existing ten zebrafish cores
or halos.** The candidate sets are ready as independent whole-genome positive
panels, but they cannot be evaluated inside the already exposed development
cores without a separately frozen external-region intervention.

The downloaded source records and assembly reports are under
`reports/FUNCTIONAL-MASK-EVIDENCE-20260925/evidence/`; their use is limited to
source provenance and coordinate validation. No raw chicken subreads or
uncorrected long-read data were downloaded.

The ORF boundary is explicit. Chicken ORFs were predicted with GLIMMER3 in
the source paper; ALVE-JFevB has source-reported intact gag-pol and envelope
ORFs and WGS junction confirmation, but no current-locus virus-rescue or direct
start/stop protein assay in that study. ALVE6 is 5-prime truncated and remains
sensitivity-only. The zebrafish paper experimentally tested a ZB construct in
HepG2/HeLa and zebrafish enhancer-trapping assays, but that does not prove
autonomy or start/stop integrity for every endogenous ZB copy. Thus each ZB row
is `E_structural_full_length` with per-copy autonomy pending, and the source's
19/20 intact statement is retained only as an aggregate sensitivity note. The
22 loci are two source-family units, not 22 independent TE families or 22
experimentally active elements.

## Primary sources

The accession-level source list is in
`reports/FUNCTIONAL-MASK-EVIDENCE-20260925/evidence_manifest.tsv`; all entries
are official NCBI/ENA/PRIDE records or the cited primary papers. Metadata sizes
are planning estimates from public run records and must be rechecked at job
submission. No heavy data transfer or analysis was performed in this audit.
