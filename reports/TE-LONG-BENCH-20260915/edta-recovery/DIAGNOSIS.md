# EDTA recovery diagnosis

This report records the two preserved native EDTA failures and the minimal
runtime compatibility recovery.  The original failed cells remain immutable
under `outputs/TE-LONG-BENCH-20260915/native-12731946/c_briggsae-edta` and
`outputs/TE-LONG-BENCH-20260915/native-12731947/sim100-edta`.

## Observed failures

- **CB4 (`c_briggsae`, job 12731951, parent cell 12731946_3):** EDTA completed
  LTR/SINE/LINE work and failed in TIR-Learner module 4 while extracting
  sequences.  `get_fasta_sequence.py` raised
  `KeyError: 'FR847112.2_split_1of4'`; the source FASTA contains
  `FR847112.2`, while GRF's active parser uses `^(\w+)_split_...`, which does
  not match dotted accession IDs.  The checkpoint CSV has 173,614 rows, of
  which 163,509 retain split IDs.  This is a chunk-ID/coordinate interface
  failure, not a biological candidate rejection.

- **sim100 (job 12732994, parent cell 12731947_3):** EDTA failed in
  TIR-Learner module 4 during TIR/TSD checking.  With pandas 3.0.3,
  `check_TIR_TSD.py` uses `family = x[0]` on a Series; this is interpreted as
  a label lookup and raises `KeyError: 0`.  The module 4 input checkpoint has
  52,065 rows and valid sequence columns, so this is a pandas interface
  incompatibility.

## Recovery

The recovery copies each failed cell's completed `work/` directory to a new
output, overlays three source-checked modules in the EDTA container, and runs
EDTA with `--overwrite 0` so complete LTR/SINE/LINE stages are reused.  The
frozen input, `--sensitive 1`, `--anno 1`, 16 CPUs, 80 GB, CPU constraint, and
unchanged native wall budget are retained.  No threshold, library, or model
parameter is changed.

The overlays are:

1. `run_GRF.py`: allow dotted accession IDs in the active split-ID parser.
2. `get_fasta_sequence.py`: canonicalize `<accession>_split_<part>of<n>` IDs
   and add the local GRF coordinates to the original-genome coordinates before
   FASTA lookup.
3. `check_TIR_TSD.py`: use the named `TIR_type` column under pandas 3.

The coordinate transform follows the TIR-Learner splitter and is checked by a
small oracle before resume:

| split ID | source offset |
| --- | ---: |
| `1of4` | 0 |
| `1.5of4` | 4,975,000 |
| `2of4` | 5,000,000 |
| `2.5of4` | 9,975,000 |
| `4of4` | 15,000,000 |

Thus an overlap chunk starts at `i × 5,000,000 − 25,000`, while a normal chunk
`i` starts at `(i − 1) × 5,000,000`; the boundary cases are exercised before
the Slurm command is launched.

## Local validation

The patch was applied to the exact three module sources extracted from the
EDTA image.  The source patch test passed for all three modules, including the
active GRF parser, the single coordinate-normalization call, and both pandas
family accesses.  `py_compile` and `bash -n` also passed for the recovery
driver and Slurm wrapper.

## Execution

The Slurm recovery array is `12738345` (two cells on `public-cpu`, constrained
to `E5-2630V4`).  Final cell statuses will be appended after completion.  A
failed recovery remains recorded as failed; the recovery does not overwrite
either original failure.

At the first runtime inspection both cells had passed EDTA dependency checks,
recognized the existing `panel.fa.mod`, and entered `EDTA_raw`; their
`edta_resume.stdout` files were nonempty and their status files recorded the
three overlays plus the offset oracle.  The empty `.time` files at that point
were expected because `/usr/bin/time` writes them only when the still-running
resume command exits.
