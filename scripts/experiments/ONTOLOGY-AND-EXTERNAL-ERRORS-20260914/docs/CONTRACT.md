# Ontology and external-error retrospective audit

This directory contains one bounded CPU analysis associated with the fixed
SF5 label contract and the fixed D external panel.  It is an audit of existing
artifacts, not a new model experiment.

Part A streams the materialised `animal_sf5_w4096` train/validation/test
windows, compares their six-ID label map with the recorded mapper, and reports
the exact `all6`, `main4`, `Unknown`, and background base-pair denominators.
The mapper maps `LINE`, `SINE`, `LTR`, and `DNA` to the four named classes and
maps `RC`, `Retroposon`, `PLE`, ambiguous strings, and unrecognised classes to
the single `Unknown` ID.  It does not map those known other TE examples to
`BG`; bases missing from the source annotation are painted `BG`, so annotation
absence and a true background base remain inseparable in the encoded windows.

This means the legacy `Unknown` precision/recall is not a single biological
quantity.  The encoded labels cannot retrospectively separate known other TEs
from ambiguous and genuinely unclassified records.  The historical chrX
90-row audit is retained as provenance only: it has no model predictions and
is not a population estimate of annotation error.

Part B reads the saved D probability arrays at the existing frozen CAL
threshold and the fixed sea-urchin uncurated-library comparator plus platypus
Label-A comparator.  Every overlapping RepeatMasker record is classified as
`known_te`, `unknown_or_ambiguous`, `hard_non_te`, or `excluded_non_te` under
the existing D contract.  It is stratified by top-level class, clipped panel
length, RepeatMasker divergence, and frozen source region.  The report keeps
row sums and a separate union summary; a row is not treated as an insertion
identity.  For each arm, `rows_any_recovered`, `rows_fully_recovered`, and
callable base-pair recall are reported.  Unlabelled sequence is never a
negative denominator, and T0 comparator agreement is not independent accuracy.

The analysis is deliberately fixed:

- D seed/checkpoint, four regions, saved probabilities, and threshold remain
  unchanged.
- No model is loaded and no inference, training, or threshold fitting occurs.
- Unknown/non-TE records remain in their own denominators; they are not
  silently converted to background or positive TE.
- Whole-assembly Label-A rows outside the four panel contigs are counted as
  non-panel rows.  For the lifted sea-urchin file, selected panel IDs and
  coordinates are checked rather than silently discarded.
- The preferred next label design is hierarchical: binary TE material,
  main4/known-other-TE class, and an explicit unresolved/abstain state.  Any
  future claim about independent SVA or family accuracy requires an output
  head and an annotation set that directly supports it.

Run on Baobab with:

```bash
sbatch scripts/experiments/ONTOLOGY-AND-EXTERNAL-ERRORS-20260914/sbatch/run_cpu.sbatch
```

The Slurm output is a compact JSON bundle under
`/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/outputs/ONTOLOGY-AND-EXTERNAL-ERRORS-20260914/run-<jobid>/`.
Only compact reports and provenance should be copied into this directory;
large FASTA, probability, and annotation files remain on the cluster.
