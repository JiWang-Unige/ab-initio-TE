# Fixed-D historical-candidate external screen

Status: **completed**. Slurm array `12849284` ran the three candidates serially on one GPU. Every task completed within the two-hour per-species limit; no training, target-specific calibration, sealed input, or second seed was used.

The screen used the D NTv2-500M seed42 checkpoint, the six-species CAL artifact, and the frozen threshold `0.42330056285498807`. The primary result below is the native forward (`F`) arm. RC, mean, and the predeclared phase diagnostic arms remain in the raw summaries but are not selected for the external claim.

## Evidence boundary

These are historical-candidate external screens, not untouched independent tests. None of the three species is in the six-species D supervised training table, but previous TEFM/transfer planning or screening included them. Assembly-specific pretraining exclusion is not established.

Regions were frozen before reading model scores or selecting labels: the first four usable rows in each source `chrom.sizes` file, with a centered 1,048,576-bp interval per row. The synthetic assembly report is only a coordinate-selection aid derived from `chrom.sizes`; its role fields do not represent biological NCBI assembly annotations.

The T1 endpoint is reference-positive recovery against strict TE classes. Unlabelled sequence is unknown and is not a negative class, so T1 precision and F1 are not reported. T0 values are comparator agreement with the same sparse reference and are not independent accuracy.

## Native D results

| candidate | assembly | fixed regions | known-TE label rows | known-TE union bp | callable bp | native F T1 recovery | native F T0 comparator F1 |
|---|---|---:|---:|---:|---:|---:|---:|
| *Xenopus tropicalis* | xenTro10 | 4 × 1 MiB | 5,700 | 1,390,306 | 4,193,304 | 0.885797 | 0.837062 |
| *Apis mellifera* | apiMel2 | 4 × 1 MiB | 5 | 637 | 3,701,994 | 0.857143 | 0.079603 |
| *Tribolium castaneum* | triCas2 | 4 × 1 MiB | 33 | 3,622 | 3,961,605 | 0.579514 | 0.010340 |

The bee and beetle labels are too sparse to support a biological accuracy claim. Their native recovery values are reference-positive diagnostics only. The very low T0 agreement is consistent with the sparse comparator and cannot be read as a calibrated false-positive rate.

## Source and qualification record

- Frog: same-assembly UCSC `xenTro10` FASTA and `rmsk.txt.gz`; source rows were converted to the evaluator's RepeatMasker `.out` subset after regions were frozen.
- The preparation-level frog count of 5,773 TE-class rows precedes strict family-ambiguity exclusion; the primary scorer excludes 73 `DNA/TcMar-Tigger?` rows and uses 5,700 strict known-TE rows. The class audit retains both groups.
- Bee: same-assembly UCSC `apiMel2` FASTA and downloaded UCSC `rmsk.txt.gz`/`chrom.sizes`; only five strict known-TE rows overlapped the panel.
- Beetle: same-assembly UCSC `triCas2` FASTA and existing `triCas2.fa.out.gz`; the source is an older RepeatMasker snapshot.

The exact raw summaries, label-class audits, qualification records, and prepared configuration are in `raw/`. They retain all diagnostic arms and the fixed threshold for auditability.

## Interpretation for the paper

The screen supports a bounded statement that the shared D checkpoint can recover some reference-positive TE material outside its six supervised species, including a vertebrate and two insects. It does not establish universal animal generalization, independent genome-wide F1, or Tiberius utility. The bee result is a coverage warning rather than a species-level performance estimate. MoE remains a separate follow-up decision and is not required to interpret this single-seed screen.
