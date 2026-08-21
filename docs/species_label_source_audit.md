# Species Label Source Audit

Date: 2026-06-16

Purpose: decide which species in `docs/species.md` should use a project-owned
RepeatMasker+Dfam Label-A annotation instead of relying on UCSC `rmsk` tracks.
This pass prioritizes animals.

## Source Channels

1. UCSC genome registry: `https://api.genome.ucsc.edu/list/ucscGenomes`
2. UCSC table downloads: `https://hgdownload.soe.ucsc.edu/goldenPath/<db>/database/rmsk.txt.gz`
3. Local Dfam 3.9 FamDB lineage coverage:
   `.backup/data/libraries/earlgrey_runtime_famdb`
4. Project policy from council decision: claim-bearing labels use self-run
   RepeatMasker+Dfam as Label-A; UCSC `rmsk` is an external/legacy comparator.

## Decision Rule

Use self-run RepeatMasker+Dfam Label-A for every animal used in training,
screening, holdout, or claim-bearing evaluation. UCSC `rmsk` tracks are not
mixed into Label-A because their assembly versions, RepeatMasker/Dfam lineage,
library versions, and masking policy are heterogeneous across species and years.

Use de novo+Dfam only as Label-B diagnostic/U-shield/sensitivity evidence, and
only promote it to a primary label source after a separate route decision.

## Animal Audit

| Group | Species | TaxID | UCSC status checked | Local Dfam 3.9 lineage-specific families | Decision |
|---|---:|---:|---|---:|---|
| Anchor | Homo sapiens | 9606 | `hg38`/`hg19` have UCSC `rmsk`; `hs1` standard `rmsk.txt.gz` path returned 404 | 52 | Self-run Label-A required for `hs1`; UCSC hg tracks only legacy controls |
| Core train | Mus musculus | 10090 | `mm39` and `mm10` have UCSC `rmsk` | 27 | Self-run Label-A required; already in anchor batch |
| Core train | Rattus norvegicus | 10116 | `rn7`, `rn6`, `rn5` have UCSC `rmsk` | 24 | Self-run Label-A required; prioritize next animal batch |
| Core train | Canis lupus familiaris | 9615 | `canFam6`, `canFam5`, `canFam4`, `canFam3` have UCSC `rmsk` | 0 | Self-run Label-A required; high-priority de novo+Dfam diagnostic if model/U-quality is poor |
| Core train | Gallus gallus | 9031 | `galGal6`, `galGal5`, `galGal4` have UCSC `rmsk` | 177 | Self-run Label-A required; already in anchor batch |
| Core train | Danio rerio | 7955 | `danRer11`, `danRer10`, `danRer7`, `danRer6`, `danRer5` have UCSC `rmsk` | 1720 | Self-run Label-A required; already in anchor batch |
| Core train | Drosophila melanogaster | 7227 | `dm6` has UCSC `rmsk` | 608 | Self-run Label-A required; already complete in anchor batch |
| Core train | Caenorhabditis elegans | 6239 | `ce11`, `ce10` have UCSC `rmsk` | 180 | Self-run Label-A required; already complete in anchor batch |
| Holdout | Sus scrofa | 9823 | `susScr11`, `susScr3`, `susScr2` have UCSC `rmsk` | 901 | Self-run Label-A required before claim-bearing holdout |
| Holdout | Bos taurus | 9913 | `bosTau9` plus many older UCSC assemblies have `rmsk` | 934 | Self-run Label-A required before claim-bearing holdout |
| Holdout | Equus caballus | 9796 | `equCab3` has UCSC `rmsk` | 1032 | Self-run Label-A required before claim-bearing holdout |
| Holdout | Xenopus tropicalis | 8364 | `xenTro10` plus older UCSC assemblies have `rmsk` | 1244 | Self-run Label-A required before claim-bearing holdout |
| Holdout | Apis mellifera | 7460 | UCSC only exposed old `apiMel2`/`apiMel1` `rmsk` snapshots | 248 | Self-run Label-A required; do not rely on old UCSC-only snapshot |
| Holdout | Tribolium castaneum | 7070 | No current UCSC database match found by taxid/name | 1140 | Self-run Label-A mandatory from NCBI/Ensembl assembly; no UCSC `rmsk` fallback |

## Practical Priority

P0 is the existing anchor batch: human `hs1`, mouse `mm39`, chicken `galGal6`,
zebrafish `danRer11`, fruit fly `dm6`, and worm `ce11`.

P1 should add missing core-training animals: rat `rn7`/mRatBN7.2 and dog
`canFam6`/Dog10K. Dog is especially risky because the local Dfam 3.9 query found
zero dog-lineage-specific families, so model failures on dog should trigger a
bounded de novo+Dfam diagnostic early.

P2 should add animal holdouts before any claim-bearing cross-species evaluation:
pig `susScr11`, cow `bosTau9`, horse `equCab3`, frog `xenTro10`, honeybee
`apiMel2`/newer NCBI assembly if selected, and Tribolium from a non-UCSC
assembly source.

## Key Interpretation

UCSC `rmsk` availability means "useful external comparator", not "safe primary
label". The multiple UCSC database names and download sizes per species confirm
that UCSC tracks are heterogeneous snapshots. They can help audit concordance
and detect gross errors, but they should not define project positives/negatives
for fair multi-species model training or evaluation.

## Plant / Fungi Comparator Materialization

Date: 2026-06-17

The plant and fungi entries are handled under the same policy: self-run
RepeatMasker+Dfam remains the project-owned Label-A source when a species is
used for claim-bearing training or evaluation, while UCSC/local legacy
RepeatMasker annotations are comparator evidence only.

Materialized comparator directory:
`software_outputs/repeatmasker_dfam/ucsc_reference_repeatmasker/UCSC_RMSK_SPECIES_PLANTS_FUNGI_20260617`

Completed comparator materialization:

| Kingdom | Species code | Scientific name | Source format | QC note |
|---|---|---|---|---|
| plant | rice | *Oryza sativa* | BED | OK |
| plant | maize | *Zea mays* | BED | OK |
| plant | sorghum | *Sorghum bicolor* | RepeatMasker out | OK |
| plant | brachypodium | *Brachypodium distachyon* | RepeatMasker out | OK |
| plant | thale_cress | *Arabidopsis thaliana* | BED | OK |
| plant | teosinte | *Zea diploperennis* | BED | OK |
| plant | soybean | *Glycine max* | BED | OK |
| fungi | yeast | *Saccharomyces cerevisiae* | BED | OK |
| fungi | fission_yeast | *Schizosaccharomyces pombe* | RepeatMasker out | OK; 10 strict TE records, 35 plus-unknown records |
| fungi | neurospora | *Neurospora crassa* | BED | OK |
| fungi | aspergillus | *Aspergillus nidulans* | BED | OK |
| fungi | magnaporthe | *Magnaporthe oryzae* | RepeatMasker out | OK but sparse TE signal |
| fungi | fusarium | *Fusarium graminearum* | RepeatMasker out | QC warning: source contains 0 TE-class records after strict and plus-unknown filtering |
| fungi | cryptococcus | *Cryptococcus neoformans* | RepeatMasker out | OK |

Missing external comparator sources currently recorded in
`missing_external_comparator.tsv`: `setaria_italica`, `green_foxtail`, `tomato`,
`wild_rice`, `arabidopsis_lyrata`, and `grape`. These species can still be
covered by self-run Label-A or by a later targeted UCSC/Ensembl/NCBI comparator
retrieval pass; they should not be silently treated as having comparator
coverage in the current run.
