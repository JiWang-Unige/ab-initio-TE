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
  uses a new output directory. Panel membership, raw feature rows, sequence,
  ontology and all Gate L contracts remain unchanged.
