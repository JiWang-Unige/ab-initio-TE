# Annotation revision: human asset readiness (2026-09-14)

Status: metadata qualification only; no new training, inference, liftover, or FP-rescue result.

## Decision

Existing hg19, hg38, and hs1 files make a paired annotation-revision experiment feasible. They do **not** yet establish that an old apparent FP was subsequently confirmed as TE. In particular, the existing hs1 annotation metadata identifies a **2018 library**, so assembly chronology cannot substitute for annotation provenance.

The proposed claim is that some apparent FPs against an older comparator receive independent support. This can affect observed precision and F1. It does not by itself quantify all missing annotations, prove the remaining FPs are TEs, establish recall bias, or explain cross-species performance differences.

## Assets observed on Baobab

Root: `/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE`.

| Asset | Relative path | Observed bytes |
|---|---|---:|
| hg19 sequence | `data/raw/ucsc/human/hg19/hg19.fa.gz` | 948731419 |
| hg38 sequence | `data/raw/ucsc/human/hg38/hg38.fa.gz` | 983659424 |
| hg19 UCSC repeat comparator | `software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/human/hg19/raw/rmsk.txt.gz` | 148359433 |
| hg38 UCSC repeat comparator | `software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/human/hg38/raw/rmsk.txt.gz` | 155633856 |
| hs1 repeat comparator | `software_outputs/repeatmasker_dfam/comparators/ucsc_reference_repeatmasker/human/hs1/raw/hs1.repeatMasker.out.gz` | 181182971 |
| hs1 sequence | `.backup/data/genome_data/current_eukaryotes/animals/human/hs1.fa` | 3179638084 |
| hs1 repeat metadata | `.backup/data/genome_data/current_eukaryotes/animals/human/hs1.repeatMasker.version.txt` | 922 |

Existing source records: `configs/UCSC_RMSK_SPECIES_ANIMALS_20260617/source_manifest.tsv`, `configs/RMDFAM_STRESS_HUMAN_ASSEMBLIES_20260617/species_table.tsv`, and `docs/species_label_source_audit.md`.

The hs1 metadata was read directly through SSH on 2026-09-14. Its relevant fields are:

```text
Search Engine: Crossmatch [ 1.090518 ]
Complete Database: dc20181026-rb20181026
Dfam_Consensus RELEASE 20181026
RepBase RELEASE 20181026
RepeatMasker engine: -engine crossmatch -s
RepeatMasker library options: -species 'Homo sapiens'
```

This observation qualifies the existing local hs1 comparator only. It does not describe every T2T repeat annotation available elsewhere.

## Qualified public source for the next annotation version

The [T2T consortium CHM13 resource](https://github.com/marbl/CHM13) links a distinct `RepeatMasker v4.1.2p1.2022Apr14` annotation and reciprocal hg19/hg38↔CHM13v2.0 chain files. These are appropriate candidates to acquire next, rather than silently reusing the local 2018-library track:

- [CHM13v2.0 native RepeatMasker output](https://s3-us-west-2.amazonaws.com/human-pangenomics/T2T/CHM13/assemblies/annotation/chm13v2.0_RepeatMasker_4.1.2p1.2022Apr14.out).
- [hg19 to CHM13v2 chain](https://s3-us-west-2.amazonaws.com/human-pangenomics/T2T/CHM13/assemblies/chain/v1_nflo/hg19-chm13v2.chain) and [reverse chain](https://s3-us-west-2.amazonaws.com/human-pangenomics/T2T/CHM13/assemblies/chain/v1_nflo/chm13v2-hg19.chain).
- [hg38 to CHM13v2 chain](https://s3-us-west-2.amazonaws.com/human-pangenomics/T2T/CHM13/assemblies/chain/v1_nflo/grch38-chm13v2.chain) and [reverse chain](https://s3-us-west-2.amazonaws.com/human-pangenomics/T2T/CHM13/assemblies/chain/v1_nflo/chm13v2-grch38.chain).

The [UCSC T2T repeat-track description](https://hgdownload.gi.ucsc.edu/gbdb/hs1/hubs/public/t2tRepeatMasker.html) specifies RepeatMasker 4.1.2-p1, RMBlast 2.10.0+, and Dfam3.3 plus T2T-derived entries submitted to Dfam3.6 and HG002-Y additions. Hence engine and library both differ from the old local track; an annotation contrast using them is not a library-only intervention. The [custom library resource](https://github.com/jessicaStorer88/RepeatMasker_library_CHM13) is a source for planning an engine-matched library experiment.

These URLs and descriptions were directly checked on 2026-09-14. Native tracks/chains were not downloaded or run in this step; downstream coordinate and sequence qualification remains required. New support is an updated computational/curated comparator, not independent experimental proof.

## Minimal experiment to qualify next

1. Freeze one GLM and one seed, one hg19 training chromosome, a separate development region, and held-out evaluation chromosomes. Respect existing sealed chromosomes. Do not choose the training chromosome or threshold by inspecting future-label rescue.
2. First isolate **annotation/library change on the same sequence**: apply independently sourced old/new libraries or curated annotation versions to a fixed assembly under documented engine settings. This separates annotation effects from new sequence and coordinate mapping.
3. Add hg19→hg38→hs1 as an assembly-aware extension. Partition unique reciprocal sequence-supported mappings, ambiguous mappings, sequence-changed loci, and unmapped/new sequence; do not silently discard these denominators.
4. Freeze apparent-FP candidate units and matched negative controls before inspecting new support. Report supported candidate/bp proportions, remaining unresolved candidates, and stratified uncertainty. A binary fragment is not an insertion count.
5. Include blinded independent sequence/homology/structural evidence for a sampled subset. New RepeatMasker overlap alone is comparator support, not independent experimental validation.
6. For a second species, qualify Drosophila Release 6 annotation updates first; Arabidopsis is a second candidate. Check actual TE track changes, exact sequence identity, library provenance, and leakage before selecting either. Do not infer identity from assembly lengths or release names alone.

No training or expensive comparator run is authorized by this metadata note alone; this note records the concrete preparation for the user's requested new experiment. The final scientific split and new training configuration must be explicit before execution.

## Second-species follow-up from Pro

The [official UCSC mm10 database index](https://hgdownload.soe.ucsc.edu/goldenPath/mm10/database/) was checked after Pro proposed it. It contains `rmskOutBaseline.txt.gz` and `rmskOutCurrent.txt.gz` (both approximately 142 MB), plus their alignment and joined counterparts. They offer a concrete **same-mm10** annotation contrast to qualify. The listed filesystem dates are not sufficient evidence of the library/tool generation dates or of biological corrections. First recover that provenance and count actual TE-feature changes. Mouse was part of D task training, so this study would concern annotation revision, not D's unseen-species transfer. FlyBase Release6 remains the other preferred candidate, conditional on actual TE changes.
