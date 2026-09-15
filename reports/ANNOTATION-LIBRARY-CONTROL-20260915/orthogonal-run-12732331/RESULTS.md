# Source-only control and RepeatPeps result

Slurm job `12732331` completed on 2026-09-15.  It read only the existing
hg19 source FASTA on `chr2/3/4`, the fixed qualification table, and the frozen
source-only matched controls.

- No-reuse matching: 21,235 qualified FP cases and 23,586 qualified TN rows;
  5,540 unique controls were assigned once, leaving 15,695 FP cases unmatched.
  Of the unmatched cases, 2,586 had no covariate-compatible control and 13,109
  were left after the compatible control pool was exhausted.  The
  `ADJACENT`/`ISOLATED` split is retained in `no-reuse/summary.json`; no new
  annotation or model score entered selection.
- RepeatPeps query panel: 21,235 FP candidates plus the 5,540 no-reuse TN
  controls, 26,775 source intervals and 638,473 bp.  21,060 intervals are
  shorter than 30 bp, so protein evidence has limited sensitivity for this
  interval population.
- With `blastx` E-value at most `1e-5`, any-hit support was 14/21,235 FP and
  0/5,540 TN in the no-reuse pairs.  With the prespecified strong layer
  (bit score at least 50 and HSP query coverage at least 20%), support was
  4/21,235 FP and 0/5,540 TN; among matched pairs it was 0/5,540 FP and
  0/5,540 TN.  These are sparse computational orthogonal hits, not biological
  truth or FP rescue.

The relation-specific unmatched counts and all support fields are in the
compact JSON files beside this report.  Raw FASTA/query, BLAST, and per-query
tables remain on Baobab.
