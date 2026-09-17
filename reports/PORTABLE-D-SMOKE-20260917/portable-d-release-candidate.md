# Portable D release candidate and loader-parity smoke

Date: 2026-09-17. This is an engineering report for the local release
candidate; it is not a new accuracy or generalization result.

## Delivered candidate

The future-export root is
[`release_candidate/`](/Users/jiwang/Desktop/TE/ab-initio-TE/release_candidate/).
It contains a small installable `portable_d` package, relative-path bundle
manifest and calibration, copied NTv2 tokenizer/model-code files, a notebook,
requirements and a FASTA example. The checkpoint is deliberately absent: the
verified seed-42 arm-D `pytorch_model.bin` is about 1.97 GB and remains under
its upstream terms. The candidate makes no MIT or other permissive weight
license claim; see `release_candidate/NOTICE.md`.

The command accepts `--device auto|cpu|cuda` and produces:

* `material_probability.bedGraph` — one calibrated probability run track over
  all input bases;
* `material_runs.bed` — threshold-positive connected TE-material runs;
* `softmasked.fa` — threshold-positive canonical A/C/G/T bases lowercased for
  downstream masking; predicted IUPAC/N bases stay uppercase;
* `ambiguity_qc.bed` and a final `summary.json`.

The result is material-level masking, not family annotation or insertion
reconstruction. It does not read labels or reference libraries and does not
fill gaps.

## Frozen identity and semantics

The manifest identifies `CROSS-SPECIES-L1-UPSTREAM-20260904`, seed 42, arm D,
NTv2-500M multi-species. The calibration is copied from the verified local
seed-42 D JSON with absolute `model_dir`, `tokenizer_dir` and `model_code_dir`
removed; the exact slope, intercept, threshold, six species, CAL split,
`calibration_protocol=CROSS-SPECIES-L1-X0-PLATT-V1` and historical `protocol`
field are preserved. The loader validates the explicit `calibration_protocol`;
the historical field remains provenance only.

The package copies the source evaluator's six-base tokenization, 4096-bp
windowing, padding length, token-margin-to-base projection and Platt transform.
The portable loader imports the bundled `esm_config.py` and `modeling_esm.py`
directly, so it does not import scripts from the research repository and does
not contain Baobab paths.

## Validation before the real smoke

The following checks passed:

* Python syntax compilation, JSON parsing and `git diff --check` for the new
  candidate/smoke files;
* remote `te_benchmark` bundle validation and six-base projection checks at
  1–4096 bp;
* a remote mocked-model output test covering multi-contig FASTA, 4096-bp and
  short-tail coordinates, ambiguity QC, exact probability tracks, material
  BED and the canonical-base-only softmask rule.

These checks only validate the portable implementation and output contract.

## Real parity smoke

`scripts/experiments/PORTABLE-D-SMOKE-20260917/smoke_compare.py` stages a small
copy of the bundle and symlinks the existing checkpoint without copying the
weights. It runs the portable and historical loaders on synthetic 4096-bp,
9-bp and 5-bp sequences, compares per-base margins/probabilities and compares
the threshold mask and streamed BEDGraph/BED outputs. It reads no labels or
reference annotations. `submit_smoke.sbatch` requests one GPU, four CPUs, 32 GB
and ten minutes, and receives all paths through environment variables.

The first bounded run, **12849486**, completed in 1:44 on one GPU but failed
only because its provisional raw-margin tolerance was `1e-6`; the observed
maximum difference was `1.9073486328125e-6`. The run did not show a probability
or threshold-mask disagreement. Retry **12849647** depended on the active
animal task (`afterany:12849284_1`) and completed in 1:18 with one GPU, four
CPUs and 32 GB. Its machine-readable result is
[`smoke_report.json`](smoke_report.json): PASS. Across the three windows
(4096, 9 and 5 bp), raw-margin differences were at most `1.9073486328125e-6`,
calibrated probability differences at most `7.769857065034746e-9`, and the
material mask matched at every base. The probability track was exactly equal
to the portable captured probabilities. A separate existing-fixture check is
[`softmask_contract.json`](softmask_contract.json): PASS for all three contigs.

A PASS means loader/output parity only; it does not promote a new scientific
claim.

## Real CPU parity smoke

To close the deployment check on naturally positive sequence, job **12853594**
ran the same candidate and historical loader on CPU only (private-teodoro-gpu,
16 CPUs, 32 GB, 30-minute limit; elapsed 43 seconds). The input was fixed in
advance as the first two records in the frozen human/hs1 DEV stream: the two
4096-bp halves of `chr4:2326528-2334720`. The inference process received only
the sequence-only FASTA; labels and reference annotation were not passed to
either loader. Selection details are recorded in
[`source_manifest.json`](cpu_actual_12853594/source_manifest.json).

The run completed with **PASS**. Portable and historical raw margins matched
exactly on both windows, calibrated probabilities matched exactly, the
threshold mask matched exactly, and the streamed probability track and
canonical-base-only softmask matched. The naturally nonempty material mask
covered 3,418 of 8,192 bp (2,934 bp in the first half and 484 bp in the
second); both loaders reported the same total. This is CPU execution and
loader/output parity evidence only, not a new accuracy, species-generalization,
or downstream utility result. The machine-readable report and compact output
tracks are under [`cpu_actual_12853594/`](cpu_actual_12853594/).
