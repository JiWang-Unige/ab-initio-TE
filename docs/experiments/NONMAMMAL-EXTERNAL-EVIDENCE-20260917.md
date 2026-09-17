# Nonmammalian external positive-evidence evaluation

This extension addresses the limited reference coverage of the previous frog,
bee and beetle screen. Species and assembly qualification precede model scores.
The final source manifest must name each original assembly and coordinate
asset before inference; cached RepeatMasker output alone does not qualify as
independent biological truth.

## Fixed design

- At most two nonmammalian species outside the six-species D supervised panel.
  Prior project exposure and unknown foundation-model pretraining exposure are
  recorded separately. No sealed species are opened.
- For each qualified assembly, select its four longest contigs of at least
  4,194,304 bp, breaking length ties lexicographically by FASTA ID. Use the
  centered 4,194,304 bp of each: 16,777,216 bp per species. Region selection
  uses sequence lengths only, with no label-density or prediction filtering.
- The frozen six-species NTv2-500M D seed42 checkpoint, existing shared CAL
  artifact, threshold 0.42330056285498807, native 4096-bp tiling, and forward
  sequence orientation are retained. There is no training, RC ensemble, phase
  sweep, threshold search or postprocessing.
- Report callable A/C/G/T base recovery separately for each documented
  positive layer and region, together with predicted coverage. Unknown or
  ambiguous bases are not reassigned as true negatives. Do not compute
  biological precision/F1 from a positive-only annotation layer.
- A curated TE library subsequently aligned with RepeatMasker remains a
  source-dependent coordinate layer. Structural or manually verified
  insertion evidence is identified separately; its incompleteness does not
  make unmatched model predictions false positives.
- Missing evidence, mapping incompatibility or native failure is reported
  directly. No species is replaced because its model score is poor. This is a
  regional external evaluation, not a whole-genome or per-insertion claim.

## Implementation and meaningful check

`scripts/experiments/NONMAMMAL-EXTERNAL-EVIDENCE-20260917/panel.py` prepares the
label-blind FASTA and evaluates original-assembly BED coordinates against
panel-coordinate model runs. A hand-computable fixture passed assembly-to-panel
clipping, overlapping-interval union, ambiguous-base exclusion and unknown
remainder accounting (10 callable reference-positive bases, 9 recovered,
15 callable total). This checks the coordinate failure modes that would alter
the scientific interpretation; it is not biological validation.

## Execution record

The first fixed species is silkworm, `GCF_014905235.1 / Bmori_2016v1.0`.
Its same-assembly historical NCBI RepeatMasker layer is source-dependent.
The additional structural layer runs the existing EDTA 2.3.0 raw LTR path
(LTRharvest/LTR_FINDER plus LTR_retriever), without a user supplied library.
The native pass list and EDTA cleanup are kept separately. These are orthogonal
algorithmic support, not manually established biological truth; bundled
classification evidence and self-derived RepeatMasker filtering remain part of
the native method. A missing or zero-positive structural layer is reported as
such. No LTR-age interpretation is made from the native default mutation rate.

Preparation job `12856134`, dependent frozen-D inference `12856138`, and
dependent structural-LTR job `12856147` were submitted on 2026-09-17. Their
outputs are separate from all previous screens. The second candidate is
*D. simulans* `GCA_004382185.1 / ASM438218v1` (wXD1), selected for its PacBio
assembly and original-paper supplementary resources before any D prediction.
It replaces the unexecuted legacy medaka candidate on evidence availability,
not model score. This is distinct from sealed *D. melanogaster* dm6. Jobs are
preparation `12856365`, inference `12856371` and structural evidence `12856372`.
The two GPU inferences are sequential; so are the structural jobs. Preparation
uses shared-cpu/15 min backfill and structural jobs shared-cpu/2 h. All scientific
inputs and endpoints remain as fixed above.

No new species-specific result is claimed until native inference and recovery
outputs are present. Structural and source-dependent results cannot alone close
the remaining independent biological-validation gap.
Inference ceiling: one GPU, four CPUs, 64 GB, two hours per species, sequential;
CPU preparation/evaluation ceiling: four CPUs, 16 GB, one hour per species.
Structural discovery ceiling: four CPUs, 24 GB, two hours, one job at a time.

The first structural attempt `12856147` exposed a container working-directory
mapping failure during dependency checks. It was stopped with its outputs
retained; the unstarted dependent `12856372` was also stopped. Explicit
`--pwd /work` fixes the mapping without changing native scientific arguments.
The replacement jobs are `12856425` (silkworm, completed in 3 min 34 s) and
`12856477` (*D. simulans*). Native pass-list inspection showed descending
coordinates for minus-strand insertions; conversion now normalizes their two
endpoints before converting 1-based inclusive to 0-based half-open. A reverse
strand fixture checked this exact coordinate case before scoring.

Primary score jobs are `12856610` and `12856612`. After observing the first
silkworm primary recovery result, an explicitly exploratory source decomposition
was added (`12857055`): partition structural-positive bases into those inside
and outside the historical known-TE layer, retaining both recovered and missed
bases. This does not change the fixed panel, model, threshold or primary
endpoints. The source difference is algorithmic support for an annotation gap,
not a proven conversion of model FP into biological TP.
