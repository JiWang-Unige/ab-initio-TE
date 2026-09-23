# Fixture gate and recovery submission

The pinned EDTA container was used for all fixture jobs.  The source patch
passed the meaningful checks in every corrected attempt:

- the vectorization probe raised the expected Biopython slice `TypeError`;
- scalar `pandas.DataFrame.apply(axis=1)` succeeded;
- the patched `_SeqIO` function returned the same eight sequence strings as
  the scalar baseline, with `start`/`end` remaining `int64`;
- the original `check_TIR_TSD.py` positional access raised `KeyError: 0`, and
  the named `TIR_type` patch passed.

The synthetic unpatched nested-process branch was not reproduced, including
the forced diagnostic attempt.  This is recorded as `NOT_REPRODUCED`; it is
not evidence against the native failure.  The original chicken EDTA stderr
(`12888165`) directly records the slice probe error followed by Dask trying to
create a child from a daemon process, which is the authoritative failure
evidence.

| Job | State | Slurm elapsed | Role |
|---|---|---:|---|
| 13180745 | FAILED | 9 s | helper-name fixture error, before recovery code |
| 13180825 | COMPLETED | 7 s | corrected patch/scalar equivalence; unpatched branch not reproduced |
| 13180833 | COMPLETED | 6 s | diagnostic parallel branch; unpatched branch not reproduced |
| 13180880 | COMPLETED | 5 s | forced-parallel diagnostic; unpatched branch not reproduced |

All 27 fixture seconds are charged.  Together with the 166,862 historical
seconds, the recovery budget is 437,911 seconds (`5-01:38:31`).

EDTA recovery job `13180896` was submitted with `afterany:13180772`, using the
same 16-CPU/128-GB private allocation and a fresh output root.  Its terminal
contract requires the native Module 4/Step 7 checkpoint-load message, standard
top-level `annotation.gff3`/`library.fasta`, native sequence-ID decoding, and
the frozen `summarize_native.py` `annotation_summary.json` before success.
