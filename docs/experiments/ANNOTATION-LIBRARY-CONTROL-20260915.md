# Annotation library control — 2026-09-15

## Question

Does the apparent support for model-positive intervals depend on representing a
repeat family with one particular consensus library?  This experiment changes
the library contents while holding the assembly, sequence context, engine, and
old source-only case/control selection fixed.

## Frozen design

The input is the already evaluated hg19 panel in `old_confusion_intervals.bed`.
Only `chr2`, `chr3`, and `chr4` are read.  The panel contains 2,500 fixed
8,192-bp centers (20,480,000 center bp).  Each center is extracted with the
same 4,096-bp halo, and the resulting FASTA is reused byte-for-byte by both
annotation runs.  No model score, model prediction, target annotation, or
sealed chromosome is read by the annotation pass.

Both runs use the same RepeatMasker 4.2.2 executable and
`-pa 4 -xsmall -gff -lib` flags.  They are launched as two independent
processes on an 8-CPU node to reduce wall time; the per-run engine flags and
query inputs remain identical.  The only planned input change is the
consensus library:

1. `dfam2018_consensus`: the frozen Dfam/RepBase release-20181026 consensus
   library retained in the project backup.
2. `dfam39_human_curated`: the human-lineage curated Dfam 3.9 FamDB export,
   generated with `famdb.py families -a -d -c 9606` and
   `--include-class-in-name`.

This compares two **library configurations**, not a pure release-date effect:
the 2018 library is global and includes RepBase material, while the newer
export is restricted to curated human-lineage Dfam families. Taxonomic scope,
curation and database contents are inseparable in this contrast. Report
library sensitivity without attributing it solely to newer annotation or to
the one-consensus representation hypothesis.

The old hg19 RepeatMasker comparator is used only to retain the pre-existing
old-TE relation and to report the frozen denominator.  It is not treated as
biological truth and is not an input to library selection.  The existing
`matched_controls.tsv` is joined only after both new annotations exist.  Its
cases and controls were selected from source-only covariates before this
experiment; unmatched FP intervals remain in all summaries and reused controls
are counted.

## Output definition

For every retained qualified TP/FP/FN/TN interval, each library is scored for
overlap with four mutually exclusive classes:

- `TE`: `SINE`, `LINE`, `LTR`, `DNA`, `RC`, or `Retroposon`;
- `NONTE`: known non-TE classes `Simple_repeat`, `Low_complexity`, `Satellite`,
  and RNA subclasses;
- `UNKNOWN`: an explicit `Unknown` class or a class containing `?`;
- `UNRECOGNIZED`: any other class, kept separate rather than silently treated
  as non-TE.

For each class, support is reported at three fixed interval-overlap layers:
any base, at least 50%, and at least 80%.  The report retains counts and
fractions by old state, plus source-only matched FP/TN pair summaries and the
library-to-library support transitions.  The output is descriptive evidence of
library sensitivity.  It does not recompute same-base F1, relabel FP/FN, or
claim FP rescue.

## Source-only no-reuse sensitivity and protein evidence

Because the frozen matched table reuses one TN control as many as 775 times,
the companion sensitivity pass rematches all eligible FP and TN rows with the
same source-only hard covariates, deterministic FP row order, GC tolerance, and
tie-breaks, but removes a control after its first assignment.  It reports
covariate failure separately from control-pool exhaustion and retains every
unmatched FP.  Assignment is deterministic greedy order by frozen FP row ID;
therefore “pool exhausted” describes this prespecified assignment order and
is not a claim of globally maximum-cardinality matching.  This pass also does
not read either new library or any target annotation.

The orthogonal computational layer uses every fixed FP candidate and each
unique TN control from the source-only matched table as a DNA query against the
existing HiTE `RepeatPeps.lib` protein database.  `blastx` is run with fixed
`-evalue 1e-5 -seg yes -max_target_seqs 5 -max_hsps 1` settings and both
translated strands.  We report all-query hit rates and a prespecified strong
evidence layer (E-value at most `1e-5`, bit score at least 50, HSP query
coverage at least 20%).  This is computational orthogonal support only; it is
not manual review, experimental validation, or an independent biological-truth
label.

## External evidence boundary

The existing hg19–CHM13 reciprocal-chain and source/target sequence checks may
be reported as an automated sequence-compatibility layer.  They do not provide
manual or experimental biological truth.  New target annotation is explicitly
excluded from case/control selection and is not read by this protocol.

## Reproducibility and status

- Protocol/config: [`configs/ANNOTATION-LIBRARY-CONTROL-20260915.json`](../../configs/ANNOTATION-LIBRARY-CONTROL-20260915.json)
- Implementation: [`control.py`](../../scripts/experiments/ANNOTATION-LIBRARY-CONTROL-20260915/control.py)
- Contract tests: [`test_control.py`](../../scripts/experiments/ANNOTATION-LIBRARY-CONTROL-20260915/test_control.py)
- Source-only controls: [`matching_sensitivity.py`](../../scripts/experiments/ANNOTATION-LIBRARY-CONTROL-20260915/matching_sensitivity.py)
- Protein evidence: [`protein_support.py`](../../scripts/experiments/ANNOTATION-LIBRARY-CONTROL-20260915/protein_support.py)
- Slurm entry point: [`run_library_control.sbatch`](../../scripts/experiments/ANNOTATION-LIBRARY-CONTROL-20260915/run_library_control.sbatch)
- Existing-annotation score recovery: [`score_existing_run.sbatch`](../../scripts/experiments/ANNOTATION-LIBRARY-CONTROL-20260915/score_existing_run.sbatch)
- Orthogonal entry point: [`run_source_only_controls_and_protein.sbatch`](../../scripts/experiments/ANNOTATION-LIBRARY-CONTROL-20260915/run_source_only_controls_and_protein.sbatch)
- No-reuse library score: [`score_no_reuse_library.sbatch`](../../scripts/experiments/ANNOTATION-LIBRARY-CONTROL-20260915/score_no_reuse_library.sbatch)
- Fixed source qualification: `HG19-CHR1-REVISION-20260914-MATCHED/match-12708406`
- Resource request: 8 CPU, 32 GB RAM, 2 hours, `shared-cpu`; raw annotations
  remain on Baobab and only compact reports are copied into Git-tracked space.
- Orthogonal resource request: 4 CPU, 32 GB RAM, 2 hours, `shared-cpu`.

At protocol freeze, the execution status was `NOT_RUN`.  The job IDs, exact
library manifests, source-only no-reuse summary, and protein evidence summary
are appended below after Slurm completion.  A failed run remains a preserved
engineering result and is not silently replaced by a different engine or input
context.

Execution provenance is kept separate from the result claim.  Job `12732016`
was the first serial `-pa4` implementation run. It was cancelled as a redundant
attempt after byte-identical panel manifests were confirmed; its partial logs
remain an engineering record, not a timing result. Job `12732075` is the main two-library run: it uses
the same `-pa4` invocation for each library, with the two processes run in
parallel on an 8-CPU node.  Jobs `12731953` and `12731964` are preserved
startup/input-contract failures; they do not contribute annotations.

## Results

The fixed library-control experiment is complete.  Both RepeatMasker
annotations from `12732075` are complete and end with `ProcessRepeats` and
`done`; the parent job's `TIMEOUT` occurred during scoring.  Its legacy
interval-support table contains all 97,242 qualified rows.  The repaired
existing-annotation scorer `12735616` completed in 46 seconds and produced
both library tables and summaries.  The legacy table is byte-identical to the
table from the preserved partial attempt, providing a direct regression check
for the performance repair.  The no-reuse library score `12735617`, submitted
after `12735616`, completed in 52 seconds.  The stale dependent job `12732397`
was cancelled after its dependency became unsatisfiable and is not a result.

Across the full qualified denominator, any-TE support was 82.96%, 33.57%,
68.73%, and 36.61% for TP, FP, FN, and TN under the 2018 global Dfam/RepBase
library, and 82.06%, 24.46%, 67.30%, and 23.46% under the curated human-lineage
Dfam 3.9 library.  At the >=50% and >=80% layers, the corresponding FP/TN
fractions were 30.76%/10.72% and 28.80%/8.25% for the legacy library, versus
22.04%/6.41% and 20.05%/4.95% for the curated library.  The matched-pair
FP-minus-TN differences remain modest and are reported in the compact result
file.

This closes the experiment as descriptive evidence that library contents and
reference coverage materially affect external TE support.  It does not prove
that individual model FPs are true TEs, provide independent biological truth,
justify relabelling the frozen source states, or support a new F1 value.  The
release date, taxonomic scope, curation, and RepBase content of the two
libraries are confounded.  The independent source-only and protein layer is in
[`reports/ANNOTATION-LIBRARY-CONTROL-20260915/orthogonal-run-12732331/`](../../reports/ANNOTATION-LIBRARY-CONTROL-20260915/orthogonal-run-12732331/).

The complete compact result is in
[`reports/ANNOTATION-LIBRARY-CONTROL-20260915/RESULTS.md`](../../reports/ANNOTATION-LIBRARY-CONTROL-20260915/RESULTS.md),
with machine-readable summaries in the two score subdirectories.
