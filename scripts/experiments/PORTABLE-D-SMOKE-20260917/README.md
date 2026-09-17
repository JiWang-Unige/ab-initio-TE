# Portable D parity smoke

`smoke_compare.py` is a bounded engineering validator for the sibling
`release_candidate/` package. It stages the small bundle files, symlinks an
existing verified D checkpoint, and compares portable versus historical-loader
per-base margins, calibrated probabilities, threshold masks and output tracks
on synthetic 4096-bp, 9-bp and 5-bp sequences. It also verifies that the
softmasked FASTA lowercases only threshold-positive canonical A/C/G/T bases;
IUPAC/N bases remain uppercase.

It takes explicit paths and does not assume a cluster root. The supplied
`submit_smoke.sbatch` requests one GPU, four CPUs, 32 GB and ten minutes; pass
`PORTABLE_ROOT`, `ORIGINAL_MODEL_DIR`, `ORIGINAL_CODE_DIR`, `ORIGINAL_HELPER`
and `OUTPUT_DIR` through the environment. `CONDA_INIT`/`CONDA_ENV` are optional
runtime hooks. No labels or reference annotations are read.

For the real positive-sequence check, `smoke_compare.py` also accepts
`--input-fasta`; `submit_cpu_actual_parity.sbatch` runs this mode CPU-only with
16 CPUs, 32 GB and a 30-minute limit. The input FASTA is sequence-only and is
selected before inference. This mode reports natural threshold-positive bp but
does not score accuracy or read labels.

The default parity tolerances are recorded in `smoke_report.json`: 3e-6 for
raw margins and 1e-6 for calibrated probabilities. Threshold masks must match
at every base. These tolerances cover the observed small GPU floating-point
difference between two separately loaded copies of the same checkpoint; they
do not permit a mask disagreement.
