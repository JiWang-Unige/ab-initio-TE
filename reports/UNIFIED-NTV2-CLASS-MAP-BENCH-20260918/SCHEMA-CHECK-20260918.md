# Native EDTA schema check

The terminal EDTA parser contract was checked against the completed pinned
sample at
`outputs/TE-LONG-BENCH-20260915/native-12738464/sim100-edta/work/panel.fa.mod.EDTA.anno/panel.fa.mod.EDTA.TEanno.gff3`.
The file contains the expected EDTA TEanno structure: complete feature rows
such as `Bel_Pao_LTR_retrotransposon`, `Cacta_TIR_transposon`, and
`Helitron`, explicit `classification=...` attributes, `repeat_fragment`
Unknown rows, and structural `long_terminal_repeat` rows. The parser observes
the same 100-Mb single-contig panel and converts GFF3 1-based inclusive
coordinates to 0-based half-open coordinates.

Under the frozen class-map policy, 123,471 valid rows were observed; 122,867
were retained as class-bearing material rows, 561 explicit rRNA/non-TE rows
were skipped, 43 structural/parent/missing-class rows were counted as parser
diagnostics, and seven `repeat_region` containers were suppressed because a
complete TE child replaced each container. Complete TE bodies were retained
when they carried structural children. The resulting union was 91,257 merged
intervals and 40,921,429 bp. The whole binary parser owner independently
asserted exact equality of the `(chrom,start,end)` merged interval list and
the same 40,921,429-bp union for this GFF3 input.

EDTA's auxiliary `TEanno.bed` is deliberately not used as the class-map
benchmark input. Its merged union on this sample is 41,047,216 bp and is not
coordinate-identical to the frozen GFF3 parser output, so mixing that format
would silently change the comparator contract. The benchmark therefore keeps
the terminal native `annotation.gff3` as its only EDTA class source and reports
the BED observation only as an unused format diagnostic.

The deterministic `parser_smoke.py` fixture also passes for source BG mapping,
native non-TE exclusion, Unknown/ambiguous preservation, LTR body retention,
container suppression, and the known-five/full-eight metric paths.
