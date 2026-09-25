# BRAKER evaluation preparation and scoring interface

This note records the implementation boundary for `evaluation.py`. It is a
preparation and scoring interface, not a completed BRAKER result. It does not
run a model, read a BRAKER output during preparation, or treat RefSeq as
exhaustive biological truth.

## Preparation

Run the preparation on a private CPU job after the existing `ncbiRefSeq.txt.gz`
and `geometry.json` files have been checked in the two-species utility output:

```text
python3 scripts/experiments/BRAKER-MASK-UTILITY-20260925/evaluation.py \
  prepare --species chicken
python3 scripts/experiments/BRAKER-MASK-UTILITY-20260925/evaluation.py \
  prepare --species zebrafish --download-long-read
```

The default output is
`outputs/BRAKER-MASK-UTILITY-20260925/evaluation/{species}`. An explicit
`--output-dir` is preferred for a resubmission so that an existing preparation
is never overwritten. The script reads the whole-assembly FASTA only to obtain
the primary `chrN` lengths (using `.fai` when available), reuses the frozen
whole-genome D exposure manifest, and reuses the old utility geometry. It
writes:

* `full_autosome_regions.tsv`: every numeric autosome, before exclusions;
* `primary_regions.tsv`: every numeric autosome except D TRAIN/CAL
  chromosomes, with the ten old utility halo intervals subtracted;
* `exclusions.tsv`: the exact chromosome and halo exclusions;
* `reference-full.json` and `reference-primary.json`: complete coding
  RefSeq isoforms and connected `(chrom, strand, name2)` gene-locus units;
* `refseq-complete-coding-isoforms-*.tsv` and `refseq-gene-loci-*.tsv`;
* `evaluation-manifest.json`, which freezes the coordinates and denominators
  before a BRAKER GTF is read;
* the shared `evaluation/preparation.json` gate. It remains `PARTIAL` after
  only one species, and becomes `EVALUATION_READY` only after both species
  denominators exist and the fish long-read GTF has been parsed.

The complete CDS rule is the existing utility rule: `cdsStart < cdsEnd`, both
genePred completeness fields are `cmpl`, coding exon frames are valid, and
the normalized coding intervals are contained in the selected domain. A
gene-locus is a connected component of transcript spans for one chromosome,
strand, and `name2`/gene key. An isoform crossing a removed halo is excluded
from the primary denominator; it is not silently clipped.

The fish RefSeq audit found four primary-domain exact-chain alias groups before
any BRAKER output was read: `pcdh2g28/pcdh2g29` on chr14 (source lines
11940/11939), `efemp2b/fibpb` on chr21 (lines 31748/31745--31747),
`si:dkey-4c15.14/zgc:173693` on chr22 plus (lines 33179/33183, 33177), and
`LOC100151570/si:ch211-222k6.1` on chr22 minus (lines 33704/33705). The full
autosome audit adds `si:cabz01032474.1/zgc:171727` on chr4 minus (lines
48145/48146). These records have identical chromosome, strand, and CDS-chain
coordinates under different RefSeq gene-name keys. The script unions these
connected reference candidates into one identifiable locus, preserving all raw
gene IDs, transcript IDs, source lines, and the merge count in
`exact_chain_alias_merges`; it neither selects one alias nor drops a row.

For zebrafish, `--download-long-read` fetches the fixed pinned GTF URL and
requires the frozen 5,921,281-byte length. The parser keeps every deduplicated
multi-exon intron chain, records the source `class_code`, and reports exact
intron-chain matches to complete RefSeq CDS isoforms separately for the full
and primary domains. `class_code=u` is retained as provenance and is never
called coding by itself. An exact intron-chain match is splice-structure
support only; it does not provide CDS start, stop, or frame truth. No RNA
absence is converted into a negative observation.

The pinned source was inspected before implementation: its contigs are
numeric (`1`, `2`, ...), and `class_code` is present on the `transcript` row,
not necessarily on every `exon` row. The parser therefore maps numeric
zebrafish contigs `1..25` to UCSC `chr1..chr25`, reads transcript attributes
without treating the transcript span as an exon, and verifies the resulting
structures against canonical RefSeq coordinates. The same logic was exercised
with positive- and negative-strand fixtures.

## BRAKER GTF scoring

After all arms have been run with the same evidence and resources, score the
primary domain with either one GTF:

```text
python3 scripts/experiments/BRAKER-MASK-UTILITY-20260925/evaluation.py \
  score --species chicken --evaluation-dir outputs/BRAKER-MASK-UTILITY-20260925/evaluation/chicken \
  --gtf path/to/D/braker.gtf --name D
```

or the fixed arm names together:

```text
python3 scripts/experiments/BRAKER-MASK-UTILITY-20260925/evaluation.py \
  score --species chicken --evaluation-dir outputs/BRAKER-MASK-UTILITY-20260925/evaluation/chicken \
  --arm D=path/to/D/braker.gtf \
  --arm RM2_FULL=path/to/RM2_FULL/braker.gtf \
  --arm RED_FULL=path/to/RED_FULL/braker.gtf
```

The primary score uses all unique normalized CDS chains within the selected
domain. The reference denominator contains only complete RefSeq CDS records,
but a BRAKER prediction missing `start_codon` or `stop_codon` remains in the
prediction denominator and is counted as FP unless its normalized CDS chain
matches a reference chain. When BRAKER emits codons as separate GTF features,
the scorer adds those intervals to the CDS intervals before normalization;
this handles both the separate-feature and already-included representations.
The output reports complete-feature and partial-feature chain counts. Only
predictions outside the domain or with no CDS are excluded from the endpoint.

When `D`, `RM2_FULL`, and/or `RED_FULL` are supplied, the script also reports
the prespecified 10,000-replicate seed-42 chromosome bootstrap interval for
`D − RM2_FULL` and `D − RED_FULL`. This is a regional sensitivity interval,
not a biological replicate or a claim of independent genome-wide truth. The
score JSON marks `sealed_labels_read=false`; the input RefSeq is a reference
agreement layer.

Scores are written to `score-primary.json` and `score-full.json` separately;
use `--domain full` for the latter. Existing outputs are not overwritten;
`--output` can name a new file when an explicit reanalysis is warranted. The
successful fish preparation is `evaluation/zebrafish-r2`, so fish scoring
must pass that directory explicitly.

## Positive-only long-read structure endpoint

Before any target BRAKER prediction, private job 13194397 froze
`evaluation/zebrafish-r2/long-read-denominators.json` using
`long_read_score.py`. At least one source transcript's entire exon span must
fit in a single allowed region. Deduplication uses chromosome, strand, and
complete intron chain. The resulting primary/full denominators are
27,862/48,068 structures; the reference-CDS-compatible subsets are
4,874/8,523. Source class codes, including `u`, remain visible.

Fish scoring automatically adds exact intron-chain recovery, chromosome
counts, and D-versus-comparator gained/lost structures. These are descriptive
positive-set recovery endpoints, with no RNA-derived FP or precision. The
all-structure set may contain noncoding transcripts and UTR introns absent
from UTR-off BRAKER CDS predictions; a mismatch is not proof of an incorrect
coding prediction. The compatible subset is explicitly reference-assisted
and does not establish independent CDS endpoints. Tests cover strand,
excluded-halo containment, partial predictions, and separate primary/full
outputs.

## Resource and interpretation boundary

The script is lightweight and can be run inside the already planned private
CPU preparation/scoring jobs. It does not create masked FASTA files, acquire
RNA/proteins, invoke BRAKER, alter the D threshold, or alter any historical
pilot denominator. BRAKER itself must remain the workflow-level comparison:
each arm gets the same predeclared RNA/protein evidence, independent working
directory, and resource budget. If the same long-read RNA is later used as
BRAKER hints, it cannot also be presented as independent validation evidence.
