# Chicken EDTA recovery — 2026-09-24

This is an engineering recovery for the preserved chicken EDTA native cell in
the frozen whole-genome benchmark.  It has a fresh output root and does not
modify the failed native directory.

## Failure and budget

The original EDTA attempt `12888165` ran for 166,835 Slurm seconds on 16 CPU
and 128 GB before failing in TIR-Learner Module 4, Step 8.  The earlier
container-path attempt `12888133` consumed 27 Slurm seconds.  The 7-day cell
budget therefore leaves 437,938 seconds before the recovery fixture.  The
fixture wall time is deducted before the recovery `--time` is submitted.

The first harness attempt (`13180745`, 9 s) failed before the check because it
called a non-existent helper name.  The corrected attempt (`13180825`, 7 s)
passed the scalar and patched-path checks, but did not reproduce the native
daemon branch on the tiny frame.  Diagnostic reruns (`13180833`, 6 s, and
`13180880`, 5 s) gave the same result even with swifter's parallel branch
forced.  The native EDTA stderr remains the direct failure evidence: it shows
the slice-probe TypeError followed by the daemon-process assertion.  The
fixture's patched output matches the scalar output for all eight rows, keeps
the coordinates as int64, and passes the named `TIR_type` check.  All four
fixture allocations are charged to the remaining cell budget; none is a
genome-scale result.

The failure is a runtime compatibility chain.  `get_fasta_sequence.py` uses
swifter on a function that is not vectorizable; its first DataFrame probe
raises the expected Biopython slice error, after which swifter selects its
Dask process scheduler.  That call is already inside TIR-Learner's outer
`multiprocessing.Pool`, so a daemon worker attempts to create a child and
raises `daemonic processes are not allowed to have children`.  The image uses
Python 3.12.13, pandas 3.0.3, swifter 1.4.0, and Dask 2026.1.2.  A separate
pandas 3 interface issue is present in `check_TIR_TSD.py`: `family=x[0]`
must address the existing `TIR_type` column by name.

## Frozen recovery

The source checkpoint is already at Module 4, Step 7.  Recovery copies the
normalized genome, all completed EDTA raw branches, the checkpoint, and the
TIR-Learner sandbox into a new output root.  The old tree is never used as a
writable working directory.  Only Module 4, Steps 8–10 and the downstream EDTA
TIR cleanup/filter/final/annotation stages are rerun.  LTR, SINE, LINE, and
whole-genome discovery are not recomputed.

The two source-checked overlay edits are:

1. In `get_fasta_sequence.py`, replace only the nested-Pool `swifter.apply`
   used to retrieve FASTA strings with `DataFrame.apply(axis=1)`.  This keeps
   the outer 16-process TIR-Learner parallelism and leaves coordinates and
   sequence logic unchanged.
2. In `check_TIR_TSD.py`, replace its two `family=x[0]` accesses with
   `family=x["TIR_type"]`, preserving the same family value under pandas 3.

No integer truncation, threshold change, library change, `--force`, or input
change is permitted.  The recovery runs with the same EDTA image, source
overlay, species, sensitivity, annotation flag, and 16 CPU/128 GB private
allocation.  The first recovery attempt (`13180896`) failed after 306 s at an
engineering checkpoint filename check; its output is preserved.  After fixing
that exact filename, fresh retry `13189201` started after chicken RM2 mask
recovery `13180772` completed.  The historical 166,862 s, four fixture
allocations (27 s), and failed retry (306 s) leave 437,605 s (`5-01:33:25`)
for the active recovery cell.

The recovery binds the fresh output as `/work` and sets the container working
directory to `/work`.  It records the checkpoint files and rejects stale
absolute symlinks.  After the TIR stage it requires the native
`Successfully loaded checkpoint` message for Module 4/Step 7.  On terminal
success it copies the native EDTA TEanno GFF and TElib to the standard
top-level `annotation.gff3` and `library.fasta` paths, optionally copies
`masked.fa`, then runs the frozen `summarize_native.py` adapter to create
`annotation_summary.json`; a recovery is not considered complete if that
summary fails.  It also checks that the copied annotation has no `_J...`
encoded sequence IDs.  EDTA 2.3.0's source decodes the final GFF with its
native `seqid_codec.pl` using `galGal6.fa.mod.seqid.map`; the recovery records
that source-backed check and does not perform a coordinate or name rewrite.

The active retry's `tir_raw_resume.stdout` now records `Successfully loaded
checkpoint` with the frozen `Module: 4` and `Step: 7`, followed by
`Module 4, Step 8: Get FASTA sequences from CNN prediction`.  This confirms
that the fresh retry consumes the preserved checkpoint.  The TIR stage remains
running; no terminal annotation or score is claimed yet.

## Fixture gate

`fixture.sbatch` runs the exact image on a tiny synthetic DataFrame.  It shows
that the initial TypeError is the swifter vectorization probe, that ordinary
scalar `pandas.apply` succeeds, and that the patched path produces the same
sequence strings as the scalar baseline.  The synthetic unpatched nested
process branch is recorded as `NOT_REPRODUCED`; the native failed-run stderr
is the authoritative daemon-error evidence.  The fixture also checks the
named-family patch before genome-scale recovery starts.
