# Direction readiness fact check — 2026-09-14

This is an evidence report prepared for the current Pro discussion and updated
with the authorized Tiberius smoke repair. It separates live Slurm state,
engineering completion, metric validity and scientific/generalization status.
No model was trained and no sealed data were opened. The Tiberius smoke-r2
inference was submitted only after the explicit container-contract repair; its
job and output state are recorded below.

## Executive findings

| Question | Current finding | Scientific disposition |
|---|---|---|
| Is the latest six-species D model evaluated on unseen species? | No. D has six-species DEV, a *C. elegans* SCREEN, and the already archived internal-coordinate *C. elegans* CONF result (F1 `0.794878`/`0.803820` for seeds 42/17). The `conf_evaluated=false` field belongs to the DEV/SCREEN JSONs; it does not negate the separate CONF artifacts. There is no platypus, sea urchin, CB4, horse, opossum, fly or cattle model output. | Internal seen-species evidence only; no unseen-species generalization claim. |
| Are platypus/urchin/CB4 ready? | The usable Label-A engineering products are complete: CB4 `12522308_2`, sea urchin `12664906_1`, platypus `12664906_0`. Their `STATUS` explicitly says `LABEL_GENERATION_COMPLETED_NOT_SCIENTIFIC_PASS`. | Assembly/annotation preparation is complete; independence, exposure, homology and model evaluation remain open. |
| Has MoE or an adapter route been run? | No executable MoE/adapters result was found. The historical route recorded `NO MOE` because its prerequisites were not met; the user's current request is a new hypothesis. | Do not claim a routing benefit; define a new matched protocol before running it. |
| What does coarse `Unknown recall=.3886` mean? | `Unknown` is label 5 in a six-class coarse classifier. It means 38.86% of true Unknown positions were predicted Unknown, among 16,961 true Unknown positions. | It is not Unknown-TE recovery and cannot identify annotation errors by itself. |
| Is the Tiberius result available? | The retained smoke-r1 stopped at its first U call during import with `KeyError: BASE_MASK_OBSERVATION`, so it has no GTF/GFF/observation output. The repaired smoke-r2 job `12687393` is currently running in P3 preparation and has not reached a Tiberius call. | Engineering status is unresolved; neither smoke is a Tiberius scientific result. |
| Have RC/strand and two-model fusion solved the gap? | RC inference-time merges have one mouse-chr1 screen; no RC-aware training or biological-prior result exists. The P3+NT risk head improved ranking diagnostics but had no admissible safe action. | Keep as prior evidence; a new relation/consistency experiment must be separately defined. |
| Is the old graph linker evidence for the new fragment-linking proposal? | A one-seed graph screen exists, but `promotion_gate_pass=false`; its edge target is contiguous truth segmentation, not biological insertion identity. | It is a negative prior, not a solved same-insertion model. |

## Live cluster state

The initial live check on 2026-09-14 through the configured Baobab SSH route
returned an empty `squeue -u jwang`; after the authorized repair submission,
job `12687393` is the sole pending Tiberius smoke. Relevant `sacct` records
and the current repair state are:

| Job | Role | State | Elapsed |
|---|---|---|---:|
| `12522308_2` | CB4 Label-A | `COMPLETED 0:0` | 00:12:24 |
| `12522308_1` | original sea-urchin Label-A | `COMPLETED 0:0` | 02:29:58 |
| `12522308_0` | original platypus Label-A | `COMPLETED 0:0` | 16:03:48 |
| `12664906_1` | repaired sea-urchin Label-A | `COMPLETED 0:0` | 02:32:39 |
| `12664906_0` | repaired platypus Label-A | `COMPLETED 0:0` | 15:50:00 |
| `12652888` | P3/Tiberius smoke | `FAILED` | 00:21:58 |
| `12687393` | P3/Tiberius smoke-r2 repair | `RUNNING (P3 run-core)` | 00:16:02 at last check |

The original platypus and sea-urchin products are retained as failure evidence
because of the `simple1.matrix` error. Only the repaired products above are
usable for subsequent engineering checks. The live output root is
`/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE`.

## D model and external-panel status

The archived D artifacts are:

- seed 42: `docs/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904/seed42/D/dev_metrics.json`
- seed 17: `docs/experiments/CROSS-SPECIES-L1-UPSTREAM-20260904/seed17/D/dev_metrics.json`

Both JSON files declare `arm=D`, `split=DEV`, `calibration_scope=six-species-shared`,
the six species `c_elegans, chicken, human, mouse, pig, zebrafish`, and
`conf_evaluated=false`. Their model directories are respectively the D training
outputs `12307410_1/final_model` and `12361196_1/final_model`. The per-species
base-pair F1 values are:

| Species | D seed 42 DEV | D seed 17 DEV |
|---|---:|---:|
| *C. elegans* | 0.797565 | 0.807216 |
| chicken | 0.831720 | 0.836385 |
| human | 0.940310 | 0.941099 |
| mouse | 0.941998 | 0.940104 |
| pig | 0.893138 | 0.894193 |
| zebrafish | 0.927836 | 0.929588 |
| macro F1 | 0.888761 | 0.891431 |

The only SCREEN rows are *C. elegans*: D is 0.802736 for seed 42 and 0.807310
for seed 17. The separately archived CONF artifacts
(`CROSS-SPECIES-L1-UPSTREAM-20260904-CONF.md`,
`CROSS-SPECIES-L1-UPSTREAM-20260904/conf/seed42_D/conf_metrics.json`, and
`CROSS-SPECIES-L1-UPSTREAM-20260904/conf/seed17_D/conf_metrics.json`)
evaluate the same seen species on the predeclared internal-coordinate panel:
D CONF F1 is 0.794878 for seed 42 and 0.803820 for seed 17. The seed-42
worm DEV/CONF points remain below the historical 0.80 engineering target,
while seed 17 CONF exceeds it; the mixed result is reportable internal
evidence, not evidence that the species is intrinsically impossible. These
results do not establish that the shared model is ready for external or
universal use.
The archived upstream report explicitly says no external-panel opening was
released and that the pilot was not a fragment/boundary solution.

The exact candidate preparations are recorded in
`docs/experiments/CROSS-SPECIES-L1-PANEL-METADATA-20260908.md` and the live
remote `software_outputs/L1-PANEL-PREP-20260908-kqZrej/`:

| Candidate | Assembly | Product to consume | Engineering evidence | Missing for science |
|---|---|---|---|---|
| platypus | `GCF_004115215.2 / mOrnAna1.pri.v4` | `labela-12664906-0` | non-empty out/gff/tbl; no Matrix error; 322 IDs and 4,973,007 records coordinate-valid | independent exposure/homology qualification; D inference/CAL/DEV/test |
| sea urchin | `GCF_000002235.5 / Spur_5.0` | `labela-12664906-1` | non-empty out/gff/tbl; no Matrix error; 871 IDs and 752,977 records coordinate-valid | same |
| *C. briggsae* CB4 | `GCA_000004555.3 / CB4` | `labela-12522308-2` | non-empty output; 32,903 records previously coordinate-valid | prior project-role/exposure audit; D inference/CAL/DEV/test |

The Label-A `STATUS` files all intentionally read
`LABEL_GENERATION_COMPLETED_NOT_SCIENTIFIC_PASS`. The candidate panel document
also says that the full L1 protocol remains `NOT_COMPLETED`; Label-A generation
does not grant independent-test status.

No MoE or adapter result is present in the D pipeline. The historical route
document (`docs/experiments/CROSS-SPECIES-L1-MATERIAL-ROUTE-20260903.md`) says
to repair labels, denominators and splits first, then compare balanced shared
training with a worst-species objective, admitting adapters/MoE only after
reproducible negative transfer and specialist recovery. Its M1 soft-MoE row was
not executed because those conditions were not established. This is a historical
readiness boundary, not a permanent prohibition on the user's new direction.
For a new study, first freeze one dense D checkpoint and one global
CAL/threshold, close the candidate independence contract, and predefine
parameter-/compute-matched dense, adapter and MoE controls without model
selection feedback. The present evidence supplies no MoE result to report.

## Meaning and limits of `Unknown`

The implementation in `pipelines/PIPE-TEFM-LOCK-20260619/superfamily5_task.py`
defines label 0 as `BG`, labels 1–4 as `SINE/LINE/LTR/DNA`, and label 5 as
`Unknown`. The reported `unknown_recall` is computed as

```text
true Unknown predicted Unknown / all true Unknown
```

The pretrained six-class row in
`reports/tefm_lock/PIPE-TEFM-LOCK-20260619/summaries/superfamily5.tsv` is:

| Metric | Value | Denominator/meaning |
|---|---:|---|
| `unknown_recall` | 0.388597 | 16,961 true Unknown positions |
| `unknown_to_main4_rate` | 0.419315 | true Unknown positions predicted SINE/LINE/LTR/DNA |
| `main4_false_unknown_rate` | 0.000308 | true main4 positions predicted Unknown |
| `unknown_precision` | 0.708862 | predicted Unknown positions that are true Unknown |
| `main4_conditional_macro_f1` | 0.864415 | Macro-average of the four one-vs-rest main4 F1s, each computed over all six-label valid positions; BG/Unknown errors still count as FP/FN, while Unknown is excluded only from the four-class average |

Thus 0.3886 is neither a recall of hidden TEs nor a family-identification
accuracy. The 260 Unknown annotation fragments in
`reports/tefm_final/PIPE-TEFM-FINAL-INTERPRET-20260630/INTERPRETABILITY_REPORT.md`
have mean best-main4 fraction 0.4706. The top-30 file contains many human
`Retroposon/SVA` rows with strong DNA/LTR predictions. This is a useful audit
lead, but the model and the same label source are not independent evidence that
those rows are mislabeled. A defensible annotation-recovery claim requires a
new library/reannotation or curated review, with the original Unknown label,
callable denominator and all Unknown-to-BG/main4 outcomes retained.

## Tiberius failure and minimal repair

The frozen protocol is in
`docs/experiments/P3-TIBERIUS-BASE-MASK-20260911-R1.md`; its approved scope is
hg38 chr16/chr18, 20 five-Mb cores, modes U/P/R, fixed Tiberius 2.0.7, and the
P-minus-U locus comparison. It already permits the original smoke → full → CPU
score sequence.

The retained smoke-r1 output
`outputs/P3-TIBERIUS-BASE-MASK-20260911-R1/smoke-r1/` contains a valid
`preflight.json` with six-channel softmask input and `status.json` marked
`PREPARED_NO_MODEL_OUTPUTS`. It contains only U stdout/stderr among the model
logs; no GTF, GFF3 or observation JSON was written. The exact U error is:

```text
File "/work/te/scripts/experiments/P3-TIBERIUS-BASE-MASK-20260911-R1/observed_tiberius.py", line 12
TARGET = Path(os.environ["BASE_MASK_OBSERVATION"])
KeyError: 'BASE_MASK_OBSERVATION'
```

The cause is visible in
`sbatch/P3-TIBERIUS-BASE-MASK-20260911-R1-smoke.sbatch`: the wrapper is run
inside `singularity exec --cleanenv`, while line 39 supplies
`BASE_MASK_OBSERVATION=...` only as a host-side shell assignment. The container
array passes `CUDA_VISIBLE_DEVICES` explicitly but does not pass this variable.
The import-time lookup in `observed_tiberius.py` therefore fails before its
`try/finally` audit block.

The minimal auditable repair is to pass the per-mode target explicitly through
the container invocation, for example by adding
`--env BASE_MASK_OBSERVATION=/work/te/$OUT/core-chr16-0/$MODE.observation.json`
to the per-mode Singularity command. An equivalent endpoint wrapper may set the
variable immediately before `runpy.run_path`; it must preserve the same P3
FASTA, six-channel observer, model config, sequence length, output paths and
U/P/R order. This repair changes no scientific input or gate. After it is
reviewed, rerun the already approved smoke, then the same 60-cell full run and
CPU score; do not interpret the failed smoke as a scientific result.

### 2026-09-14 patch preparation

The local preparation changed the Tiberius runner, its direct test, and the
output-revision implementation in
`scripts/experiments/P3-TIBERIUS-BASE-MASK-20260911-R1/base_mask.py`:
the U/P/R loop now builds a per-mode container argv with an explicit
`BASE_MASK_OBSERVATION` `--env` entry. The observer, config, gates, inputs,
outputs and scientific protocol were unchanged. The same two scripts were
copied to Baobab after the previous remote versions were backed up under
`.codex-backups/P3-TIBERIUS-BASE-MASK-20260914-r1/`; no Slurm job was submitted.

Validation results:

- The initial environment repair validation was 4/4; after adding revision
  isolation, the current Baobab `te_benchmark` suite is 5/5, including a recording
  Singularity shim that executes the exact extracted U/P/R loop and verifies
  all three argv values place the observation target before the image under
  `--cleanenv`.
- Baobab `bash -n` of the smoke script passed.
- The existing remote `preflight.json` independently passed the six-channel
  contract: U/P/R shapes `[1, 5100000, 6]`, U masked bp `0`, P `2,014,566`, R
  `2,045,296`, `actual_loader=bricks2marble.io.load_fasta().one_hot`, and
  `first_five_tracks_equal=true`.

These are engineering/contract checks only. The prior `smoke-r1` remains
`PREPARED_NO_MODEL_OUTPUTS`; it is retained as failure evidence. To keep that
evidence immutable, `base_mask.py` now accepts an explicit output revision
(default `r1`) and the new launcher
`sbatch/P3-TIBERIUS-BASE-MASK-20260911-R1-smoke-r2.sbatch` uses `RUN=smoke`,
`REVISION=r2`, and the matching internal `smoke-r2` path. The single submitted
repair smoke is Baobab job `12687393` (at the last live check it was
`RUNNING` on `gpu035`, still in the fixed P3 `run-core` stage; R2 has
`region.jsonl.gz` and no Tiberius model outputs yet); no duplicate job was
submitted. The prepared
`full-r1` GPU launcher and separate `score-full-r1` CPU launcher use the same
implementation and remain unsubmitted until the smoke has real U/P/R model
outputs. The score launcher currently invokes the canonical `base_mask.py score`
once; it is not the independent NumPy recheck required by the protocol.
After the full 60-cell result exists, the remaining validation is to replay
the count aggregation, P-minus-U deltas, 10,000 shared-core bootstrap and all
four gate predicates independently, compare that replay to `result.json`, and
only then interpret the scientific decision.

## RC/strand, dual-model fusion and graph prior

The existing RC experiment is a screen-grade inference merge on mouse chr1 with
NTv2-250M at 4096 bp (`reports/tefm_final/PIPE-TEFM-FINAL-FRAGSANITY-20260630/`):

| Decode | Segment F1 @ IoU .8 | Boundary F1 @ 5 bp |
|---|---:|---:|
| forward raw | 0.3062 | reported in source table |
| forward CRF-style | 0.3569 | reported in source table |
| best non-oracle, consensus-min + CRF | 0.4149 | 0.1267 |
| oracle-connect | 0.4339 | — |
| oracle-fill | 0.9711 | — |

The code performs forward and reverse-complement inference and merges logits by
mean/max/min; it does not train an RC-consistency loss, an equivariant model or
a strand-biological prior. The report says max-probability merging increases
unsupported predictions and that the conservative gain is not uniform. A new
RC experiment must therefore compare forward-only, RC augmentation/consistency,
and matched controls under the same compute, with strand-stratified segment and
boundary metrics. It should not be described as a completed biological-prior
result.

The existing P3+NT dual-backbone risk diagnostic is also bounded. It reduced
DEV MSE from `0.06148917198` to `0.05620692714`, increased AP from
`0.30359897234` to `0.38721621958`, and reduced Brier from `0.10562712720` to
`0.10034488236`. However, the frozen ranking feasibility report
`docs/experiments/GAP-HN-RANK-FEASIBILITY-20260908-R1.md` found no admissible
whole-gap operating point: under the loose risk budget the largest prefix had
822 gaps, 4,449 positive bp and 441 negative bp, while the first prefix meeting
the minimum utility had 8,414 gaps, 46,251 positive bp and 24,747 negative bp.
The route is therefore `RANK_ACTION_NECESSARY_NO_GO`; ranking information gain
did not imply safe gap filling under that historical whole-gap contract. Simple
OR/AND/mean donor combinations were not a successful answer under the old
contract, and the conditional P3+NT route was not executed as a new study.
The user's proposed association/fragment-linking question is a separate
experiment and must define its own controls and endpoints.

There is an older learned graph screen,
`PIPE-TEFM-CAP-FRAGGRAPH-20260701`, with one seed, 80 training steps and human
and mouse quick panels. Its `fragment_graph_status.json` says
`promotion_gate_pass=false`. At IoU .8 and 5 bp, graph keep-all exactly
preserved the CE baseline (human segment/boundary F1 `.1542/.0763`; mouse
`.1437/.0513`). Keep/drop raised human to `.4964/.2458` and mouse to
`.3676/.1313`, but deleted 86.32% and 52.53% of true-backed fragments,
respectively. The implementation creates edge labels from contiguous true
segments (`runs_from_bool(labels == 1)`), not from biological TE insertion IDs.
Consequently it is a negative prior against repeating the old local graph
recipe, but it does not test the proposed `P(same insertion)` problem. It does
not permanently close a new, independently specified association experiment.

The proposed fragment-linking direction is genuinely new only if it keeps the
P3 fragments immutable, predicts pairwise same-insertion edges, and uses an
independent insertion-ID or curated/semisynthetic truth substrate. Before a
neural edge model, the existing instance-first plan calls for a no-training
Phase-0 audit: detection substrate, oracle link/boundary ceilings,
distance/consensus-only baselines, pair AUPRC, and cross-insertion fusion risk.
RepeatMasker fragment continuity alone cannot supply that biological identity.

## Readiness consequence for the Pro decision

The evidence supports the following ordering:

1. Finish the already approved Tiberius engineering repair and obtain the
   P-minus-U downstream result before expanding gap claims.
2. Close external candidate independence/exposure and run a frozen dense D
   external evaluation before investing in MoE/adapters. Keep the present D
   values as internal, per-species diagnostics.
3. Audit Unknown-main4-like fragments with independent annotation evidence;
   do not relabel Unknown from model predictions alone.
4. Treat RC consistency and pairwise fragment linking as separate hypotheses.
   The latter needs the instance-truth Phase-0 gates before training.
5. Report the old dual-backbone and graph results as bounded diagnostics and
   historical route outcomes, while retaining them as motivation for a cleaner
   association model with newly specified controls.

The current evidence is sufficient to state that the model can provide a
computational TE-material mask and that interval continuity is a separate
failure mode. It is not sufficient to state that the model is universal, that
Unknown positions are mislabeled TEs, that MoE improves multi-species transfer,
or that biological insertions have been reconstructed.
