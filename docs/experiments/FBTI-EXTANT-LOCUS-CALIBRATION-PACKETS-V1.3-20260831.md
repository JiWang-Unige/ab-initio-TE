# FBTI extant-locus calibration evidence packets V1.3

Date: 2026-08-31  
Status: engineering artifact; no Gate L result

`build_calibration_packets.py` materializes the twelve calibration packages
from the frozen V1.3 panel (`677b72a`). It does not resample packages and does
not read or write canonical P3 atoms.

## Inputs

- the committed V1.3 `packages.tsv`;
- the committed V1.3 `context_features.tsv`, containing every positive-length
  overlapping FlyBase record for each selected package (a derived manifest,
  not raw provenance);
- the exact raw FlyBase r6.68 GFF3 (`.gff3` or `.gff3.gz`); and
- the exact runtime FlyBase r6.68 assembly FASTA.

The builder checks the frozen calibration composition (6 S0 and 6 S1, role
ranks 1--12, all S0 hard cells and two packages per S1 hard cell), package
interval containment/non-overlap, context interval overlap, focal-feature
presence, global context-feature uniqueness, and exact raw-GFF provenance for
each context feature. A matching raw record must have
`source=FlyBase`, `type=transposable_element`, and one `ID=FBti...` attribute;
its contig, strand and 1-based closed coordinates must agree with the context
row's canonical 0-based half-open coordinates. `sim4` `match` and
`match_part` records are not independent evidence in this packet. The package
sequence is the exact `[package_start0, package_end0)` slice on the declared
contig.

## Output

`packet_manifest.tsv` is a coordinator-only mapping from opaque
`CALIB-01`--`CALIB-12` IDs to the frozen package metadata. Each
`packets/CALIB-NN/` directory contains:

- `sequence.fa`: the exact package sequence;
- `packet.tsv`: opaque packet ID, assembly/contig, core coordinates and package
  coordinates; and
- `context_features.tsv`: derived context fields, with `packet_id` replacing
  the source `package_id` and no `header_md5`; and
- `raw_flybase_features.gff3`: the exact matching FlyBase feature lines.

The packet-facing files omit source package ID, role, rank, unit type, hard
cell and selection priority. The coordinator mapping must not be distributed
to annotators. Raw FlyBase feature provenance is supplied only by the
packet-local GFF3 file, as permitted by Pass 1 of the annotation contract;
model probabilities, P3 atoms, P3-derived boundaries, sim4 alignment tracks,
and intermediate adjudication are absent.

The output is a calibration aid only. It does not create annotation bundles,
truth labels for Gate L, an evidence registry, hashes/checksums, or a model.

## Engineering execution

- Slurm `12122748` (`r1`) failed before creating an output directory. The
  FlyBase asset named `dmel-all-r6.68.gff.gz` is a gzip-compressed tar archive,
  so reading it as a directly gzipped GFF produced an invalid field count at
  the tar header. It is retained as an engineering failure and enters no
  scientific denominator.
- The `r2` submission changes only transport: it streams the exact
  `dmel-all-r6.68.gff` member from that archive into the unchanged builder and
  uses a new output directory. Slurm `12122757` then reached the standard
  `##FASTA` section after all GFF3 features and failed on the first embedded
  sequence line; it also enters no scientific denominator and created no
  output directory.
- The `r3` parser stops at the standard `##FASTA` directive. It does not skip
  or relax validation of any GFF3 feature. Panel membership, raw feature rows,
  sequence, ontology and all Gate L contracts remain unchanged.
- Slurm `12122769` (`r3`, Git `7629551`) completed `0:0` in 71 seconds with
  1 CPU, 8 GB requested RAM and 0 GPU. The frozen output is
  `/home/users/j/jwang/ab-initio-TE/outputs/FBTI-EXTANT-LOCUS-PHASE0-R1/calibration-packets-v1.3-20260831-r3`.
  It contains 12 packet directories and 12 coordinator-manifest rows. The 133
  packet-facing context rows have 133 matching raw FlyBase GFF3 rows, and no
  packet-facing file contains package role, hard-cell, package ID, P3 atom or
  probability fields. The archive producer reports an expected broken pipe
  after the parser intentionally stops at `##FASTA`; the builder and Slurm job
  both completed successfully and all registered output checks passed.

This remains an engineering result. The packets are now the reusable frozen
calibration input; subsequent annotation must not rescan or reconstruct the
raw FlyBase release. Gate L is still unevaluated.
