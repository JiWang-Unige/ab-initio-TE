# Chakraborty sim-complex supplementary metadata

**Checked:** 2026-09-17
**Purpose:** qualify repeat-layer evidence for the selected *Drosophila simulans* external object. This report records source inspection and one remote coordinate lookup only. It does not run project inference, download the 45 MB assembly, or create a confirmation set. The 193XP result below is a **satellite tandem repeat**, not a TE positive.

## Download and extraction

The Europe PMC supplementary bundle was downloaded to a temporary directory from:

<https://www.ebi.ac.uk/europepmc/webservices/rest/PMC7919458/supplementaryFiles>

The bundle contained `supp_gr.263442.120_SupplementalFile_S1.zip`; the nested archive contained only `File_S1.fasta`. The temporary extraction was not copied into the repository. The inspection helper is [inspect_chakraborty_supplement.py](../../../scripts/experiments/NONMAMMAL-EXTERNAL-EVIDENCE-20260917/sources/inspect_chakraborty_supplement.py).

## Custom library contents

`File_S1.fasta` contains **2,316 records**, **7,121,885 bp** total, with lengths from **40 to 17,900 bp**. It is a shared family/satellite library, not a genome-coordinate file. There are no chromosome names, start/end fields, assembly accession fields, or insertion IDs in the FASTA headers.

The header class counts are:

| Header class | Records |
|---|---:|
| LTR | 1,335 |
| Non-LTR_retrotransposon | 437 |
| DNA | 436 |
| RC | 43 |
| rDNA | 24 |
| Satellite | 21 |
| Other | 16 |
| Low_complexity | 2 |
| SINE | 1 |
| Non-LTR_retrotransposon_484 | 1 |

The library contains species-tagged families from the sim-complex and five `noCat_*_novel_repeat` records. The exact header relevant to the FISH check is:

```text
193XP_SAT#Satellite/Satellite
```

That record is 193 bp and is explicitly a **satellite**, not an interspersed TE family. The library sequence contains the 35 bp reverse complement of the probe listed in Supplemental Table S14 at library-sequence offset 112 (0-based). The probe row is:

```text
5’-/56-FAM/ACATTGGTCAAATGTCAATATGTGGTTATGAATCC-3’.
```

This establishes a direct connection between the FISH probe and the custom `193XP` satellite record. The probe itself is short and repetitive, so it is not a unique genomic coordinate by itself. It must not be counted as a TE positive, a model TP, or evidence that a TE family was missed by the reference library.

Supplemental Table S14 contains primers and the satellite probe sequence, but no genome coordinates. Supplemental Table S17 lists `PRJNA383250` for the genome assemblies and the PacBio run `SRR5491305` for *D. simulans*, but also contains no TE coordinates. The supplementary material contains TE-class library records (LTR, DNA, non-LTR, RC and others), but **no independent, TE-class-specific genome coordinate or TE-specific FISH positive** was found.

## Coordinate mapping to the exact assembly

The selected assembly is `GCA_004382185.1 / ASM438218v1`, wXD1. A UCSC BLAT query of the full 193 bp `193XP_SAT` satellite sequence against `GCA_004382185.1` returned 48 reported alignments. The top alignment is a **full-length, zero-mismatch, plus-strand match**:

| Query | Assembly coordinate | BLAT coordinate convention | Evidence |
|---|---|---|---|
| `193XP_SAT`, 193 bp | `CM015611.1:22839222-22839415` | 0-based, half-open | 193/193 matches, 0 mismatches, 1 block |

The assembly report maps `CM015611.1` to chromosome X (23,123,156 bp). In 1-based inclusive notation, the exact match is `X:22,839,223-22,839,415`. This is a coordinate-level **satellite-repeat** support record derived from the paper’s custom sequence and the exact long-read assembly. It is not a TE coordinate, a TE positive, or a full-genome truth annotation.

The same interval was checked against the UCSC RepeatMasker layer. The track query for `CM015611.1:22839222-22839415` returned an empty `repeatMasker` list. A direct scan of the public same-assembly file [GCA_004382185.1.repeatMasker.out.gz](https://hgdownload.soe.ucsc.edu/hubs/GCA/004/382/185/GCA_004382185.1/GCA_004382185.1.repeatMasker.out.gz) found **136,707 parsed rows and zero rows overlapping this interval**. Thus this site is a concrete example of a **satellite repeat present in the custom repeat source but absent from the standard RM repeat layer**. It supports a repeat-layer coverage/control observation only; it must not be described as a TE library gap, a model FP correction, a model TP, or a TE positive.

The UCSC track provenance is [ASM438218v1 RepeatMasker metadata](https://hgdownload.soe.ucsc.edu/hubs/GCA/004/382/185/GCA_004382185.1/html/GCA_004382185.1_ASM438218v1.repeatMasker.html). It records RepeatMasker open-4.0.8, Dfam_Consensus-20181026, RepBase-20181026, and the `drosophila simulans` run parameters. The custom library is a separate article-derived source, but its genome coordinates still require an explicit mapping step; the coordinate above is the one manually checked remote BLAT result.

## Use in the external panel

This supports the following bounded repeat-layer evaluation/control:

1. Freeze `GCA_004382185.1 / ASM438218v1` and its chromosome naming.
2. Keep the UCSC RepeatMasker output as source layer A.
3. Keep the Chakraborty `File_S1.fasta` as source layer B and label the 193XP coordinate above as `satellite_repeat_FISH_support`, excluded from the TE-positive and model-TP denominators.
4. Keep any future true TE-class mapping separate from this satellite control. Do not use the absence of the RM hit to define a genome-wide negative class.

The result is strong enough to test a repeat-layer coverage difference on an exact non-model assembly. It does not, by itself, test the paper’s TE-specific reference-library-gap claim, justify genome-wide F1, or show that a custom-library-only TE interval is a true insertion. The supplementary material yielded **no independent concrete TE-class positive** in this inspection. The local metadata JSON can be regenerated with the helper script; raw supplementary files remain outside the repository.
