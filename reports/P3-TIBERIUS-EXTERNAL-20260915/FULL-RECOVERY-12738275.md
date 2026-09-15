# P3 external Tiberius full-array recovery

Date: 2026-09-15 (Europe/Zurich)

## Observed interruption

Full array `12732547_[0-39%2]` completed indices 0--14. Indices 15 and 16 ran on `gpu035` from the Slurm timestamps `21:36:42` to `22:01:00` (24 minutes 18 seconds), then both ended as `CANCELLED by 0`. Their batch steps ended with `SIGTERM` and exit code 15. Indices 17--39 were never assigned and were cancelled at the same time. The six-hour cell limit was not reached, and accounting showed no timeout or out-of-memory state. `gpu035` subsequently returned to an available state without a recorded node drain or reboot.

The scheduler record identifies UID 0/controller-level cancellation but does not expose whether the event was an administrator action or an automatic controller event. No evidence attributes it to the user account, and no scientific failure is inferred from this interruption. The original full-array logs and accounting snapshot are retained in `slurm/` below.

## Preserved partial results

Cells `cow/c15` and `cow/c16` had completed the P3 export and input FASTA construction. Neither had completed a Tiberius arm: both status files were still `RUNNING` with zero recorded steps when SIGTERM arrived. The full partial directories were moved without overwriting to:

`outputs/P3-TIBERIUS-EXTERNAL-20260915/run-r1-cancelled-12732547/cow/{c15,c16}`

Compact copies of their status and mode logs, plus the full-array accounting and node snapshot, are stored under `full-recovery-12732547/partial-cells/` and `full-recovery-12732547/slurm/`. Trailing whitespace in the copied text logs is normalized for Git; original logs, raw sequences, arrays and other large artifacts remain on Baobab.

## Bounded recovery

The first pending recovery submission, `12738275_[15-39%2]`, included the already-complete platypus `c00` index 20. That task was cancelled before execution, and the remaining pending array was then cancelled so that it could not overlap with the corrected submission. The exact missing set is cow `c15--c19` (indices 15--19) plus platypus `c01--c19` (indices 21--39), 24 cores total. No complete cell is rerun; the completed platypus `c00` smoke cell is reused by the runner.

The corrected recovery array is `12738295_[15-19,21-39%2]`, using the original `run.sbatch`, fixed inputs, frozen P3 and Tiberius checkpoints, threshold, and per-cell allocation of one 3090 GPU, 8 CPUs, 96 GB and 6 hours. `TE_REQUIRE_SMOKE=1` remains enabled. The scheduler rejected a dependency on already-completed smoke child IDs, so this array was submitted only after verifying both smoke tasks `12735505_[0,20]` had completed with all five arms; the runner itself still enforces both five-arm smoke qualifications before any expanded task proceeds.

Score job `12732548` was updated in place to `afterok:12738295` and remains blocked until every fixed core is complete. No scoring has been run or accepted early.

## Platypus reference-manifest check

The completed reference repair `12732214_1` has a compact manifest at `full-recovery-12732547/reference-platypus-12732214-compact.json`. It records platypus assembly `GCF_004115215.2_mOrnAna1.pri.v4`, status `PREPARED_WITH_NATIVE_RM`, a complete Dfam3.9 lineage curated+uncurated export, 1,139 library FASTA records, RepeatMasker 4.2.4, and 387,011 converted repeat rows. The canonical file contains one header plus those 387,011 data rows. This verifies the reference preparation artifact used by the Tiberius run; it does not read or recompute downstream utility scores.
