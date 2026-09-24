# FUNCTIONAL-MASK-EVIDENCE-20260925: readiness audit

**Status:** `READINESS_AUDIT_COMPLETED`
**Date:** 2026-09-25
**Scope:** public-data and independence audit for the proposed functional
selective masking experiment.
**Execution:** metadata and primary-record inspection only; no raw-read
download, remapping, model inference, new training, threshold change, or
species selection by outcome.

## Decision

Independent public resources justify further construction of a small,
predeclared functional evidence panel for chicken and zebrafish, but the
confirmatory H/E endpoint is not ready. The coordinate audit resolves 22
structural candidates from only two source family units, none in the existing
pilot cores or halos; just one currently qualifies under the conservative
autonomous-candidate rule. Host complete-CDS evidence also still needs its
independent coding rule. The present table cannot support a genome-wide truth
set or an autonomous-TE exclusion claim from the old pilot alone.

Platypus has useful independent short-read RNA and protein resources, but no
matching public PacBio Iso-Seq source on `mOrnAna1.pri.v4` was found in this
audit. Older platypus TE studies are assembly-mismatched and require liftover;
they are not ready-made current-assembly truth.

## Existing local results that motivate the audit

The current D-training species utility results are development evidence only:

| species | assembly | D−U F1 | D−R_TE F1 | interpretation boundary |
|---|---|---:|---:|---|
| chicken | `galGal6` / `GCA_000002315.5` | +0.013201 | −0.005125 | D improves U, slightly below historical TE mask |
| zebrafish | `danRer11` / `GCA_000002035.4` | +0.098274 | +0.009632 | D improves U and is slightly above historical TE mask |
| platypus | `GCF_004115215.2` | existing D/U RNA-supported splice comparison only | not a full-CDS endpoint | one adult-male fibroblast run; no absence negatives |

The exact source reports are [chicken](../NONMAMMAL-GENE-UTILITY-20260918/chicken/RESULTS.md),
[zebrafish](../NONMAMMAL-GENE-UTILITY-20260918/zebrafish/RESULTS.md), and
[platypus RNA](../PLATYPUS-GENE-EVIDENCE-20260917/run-12858354/RESULTS.md).

## Exact public resources

### Long-read host transcript resources

**Chicken `PRJNA670545`, `GCA_000002315.5`/Galgal6.** The primary article
reports full-length PacBio isoforms mapped to Galgal6.

| run | sample | platform | reported amount |
|---|---|---|---:|
| `SRR13084015` / `SRX9530712` / `SAMN16512680` | male embryo/gonad, multiple developmental stages | PacBio Sequel II | 78,723,364,225 bases; ~19,158 MB archive |
| `SRR13084014` / `SRX9530713` / `SAMN16512697` | female embryo/gonad, multiple developmental stages | PacBio Sequel II | 71,469,274,780 bases; ~17,397 MB archive |

Sources: [NCBI BioProject PRJNA670545](https://www.ncbi.nlm.nih.gov/bioproject/670545),
[PMC11515837](https://pmc.ncbi.nlm.nih.gov/articles/PMC11515837/).

**Zebrafish `PRJNA973729`, `GCA_000002035.4`/GRCz11.** The primary article
reports all CCS reads mapped to GRCz11 over 21 embryo stages, with 49,624
merged transcripts.

| run | stage | platform | reported amount |
|---|---|---|---:|
| `SRR24682234` | 1–4 somites | PacBio Sequel FL-cDNA | 2,199,775,856 bases; ~927 MB archive |
| `SRR24682235` | 1-cell | PacBio Sequel FL-cDNA | 2,275,468,478 bases; ~1,000 MB archive |
| `SRR24682222` | 128-cell | PacBio Sequel FL-cDNA | 2,358,442,303 bases; ~1,019 MB archive |
| `SRR24682224` | 2-cell | PacBio Sequel FL-cDNA | 2,615,775,919 bases; ~1,129 MB archive |
| `SRR24682233` | 14–19 somites | PacBio Sequel FL-cDNA | 2,511,998,751 bases; ~1,068 MB archive |
| `SRR24682231` | 20–25 somites | PacBio Sequel FL-cDNA | 2,078,794,793 bases; ~882 MB archive |

The other stage accessions are listed in `evidence_manifest.tsv`. Sources:
[PRJNA973729](https://www.ncbi.nlm.nih.gov/bioproject/973729),
[PMC12139336](https://pmc.ncbi.nlm.nih.gov/articles/PMC12139336/), and
[the authors' processed repository](https://github.com/crystalBo/zebrafish_full-length_iso-seq).

`PRJNA899844` is a conditional secondary zebrafish source: PacBio liver,
brain, muscle and larvae plus matched Illumina data are available, but the
published processed material uses GRCz9. Raw reads must be remapped to GRCz11;
published GTF/translated FASTA files are not independent truth.

### Short-read multi-tissue resources

* Chicken `PRJNA699861`/GSE166257 contains two replicates across ten cell or
  tissue types (about 262 Gb). It supports junction/expression endpoints after
  a frozen mapping protocol, not complete-CDS truth.
* Chicken and platypus `PRJNA929280` contains heart/liver chicken RNA and male
  and female platypus fibroblast RNA. The current local platypus analysis uses
  `SRR23268362` (adult male fibroblast, 5.55 Gb bases) and correctly treats it
  as splice evidence only. `SRR23268361` is the corresponding female
  fibroblast run. Source: [PRJNA929280](https://www.ncbi.nlm.nih.gov/bioproject/929280)
  and [PMC11317591](https://pmc.ncbi.nlm.nih.gov/articles/PMC11317591/).

### Protein evidence

`PXD040182` contains heart/liver mass spectrometry for chicken, platypus and
mouse, with additional platypus/opossum fibroblast summaries. The source study
searched ProteinPilot against SwissProt and used unused ProtScore >1.3. This
is independent evidence for represented host proteins. It is not an external
translation database for novel D candidate CDS, and a protein hit cannot by
itself establish the complete current-assembly transcript.

Source: [PRIDE PXD040182](https://www.ebi.ac.uk/pride/archive/projects/PXD040182).

### Independent positive TE panels

**Chicken.** The ALVE/GGERV20 study on GRCg6a reports a 5,827-bp GGERV20
element, putative gag/pol ORFs, at least 65 full-length copies and related ALVE
structural/copy evidence. The two exact ALVE coordinates printed in the article
have now been extracted; the >=65 GGERV20 population count remains
coordinate-unresolved. Source: [PMC7597685](https://pmc.ncbi.nlm.nih.gov/articles/PMC7597685/).

**Zebrafish.** The ZB/Tc1-mariner study on GRCz11 reports TIR/TSD structure,
intact transposase ORFs and multi-copy evidence; it describes 10 putative
autonomous elements, 20 full-length ZB copies and 19 intact or putatively
functional copies. Supplementary Table S4 has now been parsed into 20 exact
GRCz11 coordinates; the 19/20 distinction is aggregate, not copy-resolved.
Source: [PMC7913693](https://pmc.ncbi.nlm.nih.gov/articles/PMC7913693/).

These panels are positive structural examples, not complete TE negatives. They
are suitable for an `E_structural` confirmation subset if the coordinate and
source filters are frozen before D/U/R outputs are opened.

## 2026-09-25 coordinate extraction and core overlap

The source records and the small zebrafish supplementary archive are stored
under `evidence/`. The NCBI assembly reports confirm that the source accessions
map to the current assemblies: `NC_006088.5` is chicken `chr1` in
`GCA_000002315.5/GRCg6a`, and the ZB `NC_007xxx` accessions map to the stated
`chr1`–`chr24` molecules in `GCA_000002035.4/GRCz11`.

The reproducible extractor is
[`extract_structural_panels.py`](../../scripts/experiments/FUNCTIONAL-MASK-EVIDENCE-20260925/extract_structural_panels.py).
It parses Supplementary Table S4 from the published ZB DOCX, validates each
length and `TA` target-site duplication, records the two printed chicken
coordinates, and intersects only with the fixed geometry JSON files. It does
not open model masks, model predictions, gene scores, or any D/U/R output.

The extracted panel has 22 coordinate-resolved loci:

| species | source panel | coordinate-resolved | autonomy qualification | existing 10-core overlap | existing core+halo overlap |
|---|---|---:|---:|---:|---:|
| chicken | ALVE6 + ALVE-JFevB | 2 | 1 full-length; 1 partial | 0 | 0 |
| zebrafish | 20 full-length ZB copies | 20 | 20 structural candidates; per-copy autonomy pending | 0 | 0 |

The source paper reports 19 intact/putatively functional copies among the
20 full-length copies, but the supplement does not identify which copy is the
 single exception. The table therefore retains all 20 as structural candidates
and reports the 19/20 qualification as an aggregate sensitivity caveat. These
22 loci are two source family units (chicken ALVE and zebrafish ZB/Tc1-mariner),
not 22 independent TE families; only ALVE-JFevB is currently marked primary
autonomous.

Chicken ALVE6 is a 4,176-bp 5-prime-truncated insertion and is explicitly
marked `E_structural_partial`; it is not in the primary autonomous denominator.
ALVE-JFevB is a 7,524-bp intact insertion at `chr1:32724216-32731739` with
gag-pol and envelope ORFs and source-reported `GGCTTG` target-site duplications.
The article's `>=65` full-length GGERV20 count has no coordinate-bearing table
in the accessible record, so it remains an unresolved population count rather
than an invented locus list.

The full per-locus table is
`evidence/structural_panels/structural_panels.tsv`; the counts and fixed core
geometry are in `evidence/structural_panels/structural_panel_summary.json`.

## ORF and activity boundary

The source evidence does not make every structural-positive locus an
experimentally demonstrated autonomous element.

* For chicken ALVE6 and ALVE-JFevB, ORFs were predicted with GLIMMER3. The
  article prints ORF intervals and describes ALVE-JFevB gag-pol/envelope as
  intact, including the ribosomal -1 frameshift. Its WGS junction analysis
  confirms the reference insertion in the surveyed genomes, but this paper did
  not perform a current-locus virus-rescue, transcript start/stop, or protein
  assay. ALVE6 is 5-prime truncated and is sensitivity-only. The source's
  historical envelope-expression references do not turn ALVE6 into an intact
  autonomous positive.
* For zebrafish ZB, Supplementary Table S4 gives full-length coordinates,
  element length, transposase amino-acid length and `TA` TSD. The article
  reports a 341-aa transposase ORF and functional domains, and experimentally
  demonstrates activity of a ZB construct in HepG2/HeLa and zebrafish
  enhancer-trapping assays. That construct-level assay does not validate
  start/stop integrity or autonomous activity of each endogenous copy. The
  source's 19/20 intact statement remains aggregate, so every ZB row is an
  `E_structural_full_length` candidate with per-copy autonomy pending.

Accordingly, the current structural table supports a positive structural
endpoint and a separate, more conservative autonomy-stratified sensitivity
analysis. It does not support the sentence “all 22 loci are autonomously active
TEs” or “21 independent TE families.”

## Non-circular evidence labels

| label | inclusion rule | primary use | cannot claim |
|---|---|---|---|
| `H_transcript_full` | exact-assembly full-length long-read transcript in sampled material | transcript structure endpoint | CDS start/stop/frame or genome-wide completeness |
| `H_CDS_full` | `H_transcript_full` plus an independent coding/protein rule | strict complete-CDS endpoint | a translated candidate GTF protein or absence-based negatives |
| `H_splice` | independent junction/intron-chain support only | secondary splice endpoint | complete CDS start/stop/frame |
| `H_supportive` | external peptide or frozen orthology/synteny | supportive stratification | a complete current-assembly model |
| `E_structural` | independently reported exact-assembly TE structure/copy and transpositional coding features | structural-positive endpoint; autonomy requires per-copy qualification | all other repeats are negative, or every full-length copy is autonomous |
| `E_transcribed` | TE-associated transcript/expression without autonomous structure | secondary activity endpoint | autonomy or insertion completeness |
| `uncertain` | assembly mismatch, partial/conflicting evidence, or insufficient source detail | sensitivity table only | binary truth label |

The complement of `H` or `E` is not a negative class. The model output, current
GTF, translated model proteins, historical F1, mask, or D class cannot be used
to create the matching truth label.

## Minimal next step and resource boundary

1. Preserve the extracted coordinate table. Before a confirmatory autonomous-TE
   endpoint, resolve per-copy coding integrity and the presently insufficient
   family/region coverage; none of these coordinates overlap the old pilot.
2. Select a tissue-balanced, predeclared subset of `PRJNA670545` and
   `PRJNA973729`; remap in a private Slurm job to the exact current assemblies.
   Score `H_transcript_full` and `H_splice` separately. Promote to
   `H_CDS_full` only after the independent coding/protein rule is met. No-read
   loci remain unlabeled.
3. Add PXD040182 as a separate host-support column. A raw spectra re-search
   needs a new protocol and resource decision; do not mix it with the current
   readiness result.
4. Only after the evidence table is frozen, run the equal-budget position
   intervention and its matched sham/strong controls.

No heavy computation was submitted by this audit. Metadata sizes are planning
estimates from public records and must be rechecked before a Slurm submission.

## Negative readiness findings

* No exact-current-assembly platypus PacBio Iso-Seq source was identified.
* The existing platypus RNA run is one adult-male fibroblast sample and cannot
  validate full CDS or tissue-general correctness.
* PXD040182's SwissProt search cannot independently validate novel D candidate
  proteins without a new raw-spectrum search protocol.
* Published zebrafish `PRJNA899844` annotations are GRCz9 and cannot be used
  as GRCz11 truth without remapping.
* Neither long-read transcript resource supplies negative labels for silent or
  unexpressed genes.

These findings bound the claim and do not invalidate the proposed panel.
