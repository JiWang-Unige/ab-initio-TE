# Cross-species L1 TE-material route decision (2026-09-03)

## Status

`X0-R2 AND TRAIN MATERIALIZATION PASS; H0 IDENTITY GATE PENDING; NO GPU OR MOE SUBMITTED`

Execution ledger: CPU job `12175737` was intentionally cancelled after 3:08
with no scientific output when a concurrent audit found that its Human pool
could overlap chromosomes already supervised in H0. It is an excluded
engineering attempt, not part of the X0 scientific denominator. The corrected
manifest below restricts Human to previously unexposed chromosomes before the
replacement CPU audit was submitted.

Replacement CPU job `12175761` completed in 6:07 with exit code 0 and empty
stderr. All 22 TRAIN/CAL/DEV/TEST panel rows passed their frozen X0 gates, so
the route advances to B1/B2 engineering. The full coordinate manifest remains
outside Git at
`outputs/CROSS-SPECIES-L1-MATERIAL-X0-R2/12175761/tiles.tsv`; the compact
readiness result is versioned under the matching experiment manifest directory.

TRAIN/CAL/DEV materialization job `12176202` then completed in 10:39 with exit
code 0, empty stderr and peak RSS 1,567,440 KiB. It produced exactly 18 files:
for each of Human, Mouse, Chicken, Zebrafish, Pig and *C. elegans*, TRAIN has
1,500 unique 8192-bp tiles / 3,000 halves and CAL and DEV each have 500 tiles /
1,000 halves. No primary or replication species were materialized. This passes
the data hand-off gate for model engineering.

This report consolidates the repository audit, three parallel independent
reviews, and a full-context ChatGPT Pro review. All four routes converged on
the same decision:

1. do not start with MoE;
2. first repair the cross-species label, denominator and split contract;
3. compare a species-balanced shared model with the same model trained by a
   worst-species objective;
4. admit adapters or MoE only if shared training causes reproducible negative
   transfer that same-architecture specialists can recover.

This is a new **L1 TE-associated base-pair material** problem. It does not
reopen the closed Human P3 boundary/fragment mechanism claim and does not
inherit gap-bridge, complete-insertion or biological-instance claims.

## Scientific question and claim boundary

The primary question is:

> Can one sequence-only model, with one global calibration and threshold and
> without target-species labels, reproduce a harmonized computational
> TE-material mask with bp F1 at least 0.80 in every preregistered held-out
> animal assembly?

The target is a gate, not a guarantee. It becomes supportable only if the
frozen full-assembly confirmation criteria below pass. Before that, `>=0.80`
is an engineering objective.

The primary output is a binary per-base TE-material probability. RepeatMasker
connected components, insertion identity, nesting and historical boundaries
are not the estimand. Segment, boundary, split, fusion and fragmentation
metrics remain mandatory guardrails against a bp-only false success.

Even a successful result supports agreement with the project-owned harmonized
RepeatMasker+Dfam Label-A comparator. It does not establish exhaustive
biological TE truth, complete insertion reconstruction, unseen-family
discovery, or phylogeny inference.

## Existing evidence that changes the route

### P3 is promising for bp signal but narrow for cross-species claims

P3-R1 used the GENERanno eukaryote 0.5B backbone, an 8192-bp input and a
width-128 multiscale U-Net head. It was jointly supervised for 800 steps with
seed 42 on the first 3,000 Human chr1 windows, validated on 800 chr11 windows
and tested on 1,200 chr17 windows. Its training exposure was about 24.6 Mb
from one species and one chromosome.

P3-R1 is supervised fine-tuning of a backbone and segmentation head on
comparator-derived labels. It is SegmentNT-style only in the architectural
sense of nucleotide-level multiscale segmentation. It is not self-supervised
TE-aware post-training and does not create an independently validated
post-trained foundation model.

| Frozen P3-R1 evaluation | bp F1 | Segment F1@0.8 | Boundary F1@5 | Fragments/truth | Qualification |
|---|---:|---:|---:|---:|---|
| Human chr17 | 0.934496 | 0.378631 | 0.215650 | 1.292430 | same-species chromosome-prefix T0 |
| Mouse chr1 | 0.902004 | 0.096592 | 0.026062 | 2.144423 | zero-tune transfer on one prefix |
| FlyBase r6.68 | not legal | recall 0.078037 | recall 0.013475 | 51.557723 | positive-only T1; no precision/F1 |

Human-to-Mouse transfer is encouraging for a shared L1 material signal. The
simultaneous topology collapse shows that high bp F1 is not evidence of intact
TE annotation or fragment resolution. P3-R2 further failed its aligned-versus-
shuffled boundary mechanism gate, so this new study must not claim that P3 has
already learned biological TE boundaries.

### Earlier cross-species screens are diagnostics, not a clean benchmark

The earlier strict 4096-bp `invert_boost` screen reported bp F1 of 0.930978 on
Human, 0.962308 on Mouse, 0.943726 on fruit fly, 0.254479 on honeybee, 0.744424
on rice and 0.905165 on maize. Several training-species rows are confounded by
a builder path that can reuse the longest training chromosome for evaluation.
Evaluation also used one chromosome prefix, and label source was entangled
with species.

The target-supervised NTv2-500M species probes exceeded 0.80 in 18/22 species
and in all 11 vertebrate probes. Beetle was 0.149, *C. elegans* 0.767, soybean
0.580 and Arabidopsis 0.417. These are feasibility upper bounds, not a unified
model or unseen-species result.

The existing expert-selection evidence also argues against immediate MoE:

- the best available per-species anchor oracle averaged 0.7787;
- the best broad anchor averaged 0.5432;
- a deployable leave-species-out selector had RMSE 0.304;
- a label-free MinHash router found the best expert top-1 only 45.5% of the
  time and top-2 86.4%; leave-clade-out required abstention.

MoE cannot rescue a target for which no expert can learn the comparator. The
first missing evidence is recoverable negative transfer, not routing capacity.

## Frozen X0 label and split contract

### Comparator definition

Every primary animal T0 label must be regenerated or directly verified through
one project-owned RepeatMasker+Dfam Label-A route with the same:

- RepeatMasker version and command;
- Dfam release and lineage-library materialization rule;
- exact assembly and contig namespace;
- TE class inclusion and overlap priority;
- positive, reliable-negative, unknown and hard-negative definitions;
- callable-background and assembly-N rule.

The recorded version, semantic command, source path and resulting manifest are
the consumed provenance. The non-semantic RepeatMasker `-pa` worker count may
differ and is recorded but does not change the label contract. No unused
checksum assets are added. UCSC, Ensembl, FlyBase and other native annotations
remain secondary comparators and are not mixed into T0 truth, calibration or
unknown masks.

The Label-A state mapping is now explicit:

- `LINE`, `SINE`, `LTR`, `DNA`, `RC` and `Retroposon` top-level classes are P;
- Label-A `Unknown`/`Unclassified` intervals and non-ACGT assembly bases are U;
- all other callable ACGT bases are N;
- simple repeat, low complexity, satellite, tandem and RNA intervals are the
  `hardN` subset of N;
- priority is P over U over N.

Raw RepeatMasker output contains repeat names and classes, but current JSONL
does not retain stable copy, superfamily or homology-component identities.
Species-held-out testing is therefore possible; strict unseen-family,
unseen-copy or homology-clean claims are not.

### Sampling unit and coordinates

The data denominator is an 8192-bp genomic tile. For the selected native
4096-bp model, every tile is deterministically divided into its left and right
contiguous halves. Metrics aggregate the two halves back to the original tile
and genomic coordinate space.

- No FASTA-order prefix is allowed.
- Training species contribute equal expected gradient mass.
- CAL, DEV and external panels preserve natural TE prevalence.
- Augmentation, if later authorized, occurs only after the split.
- Training and validation chromosomes are disjoint within each training
  species.
- External species are absent from training, CAL, DEV, model selection,
  calibration and threshold selection.
- Every row records assembly, chromosome, coordinates, callable bp,
  positive/negative/unknown bp and prevalence.

Each training species contributes 1,500 train tiles and 1,000 validation
tiles. The validation tiles are frozen before training as 500 `CAL` and 500
`DEV` tiles. Across six species this is still 73,728,000 training bp, or
18,000 native 4096-bp model windows; the larger validation denominator does
not change training exposure. The original 150/150 split was infeasible for
chicken at its approximately 3.8% natural Label-A prevalence: it supplied only
about 47,000 expected positive bp per panel against the frozen 100,000-bp
gate. The 500/500 amendment preserves label-blind sampling, natural prevalence
and the original mass gate.

For genomes with enough chromosomes, train tiles span at least five
chromosomes and CAL+DEV tiles at least three disjoint chromosomes. For
*C. elegans*, use four train chromosomes, one CAL/DEV chromosome and retain one
nuclear chromosome unused. External panels use 1,200 tiles across at least
four chromosomes or chromosome arms.

Human uses a stricter exposure rule because the selected initialization is a
Human-supervised H0 model. H0 used chr1/3/5/7/9 for fitting, chr11/13/15 for
validation and chr17/19/20/21/22 for reported testing. X0-R2 therefore draws
the new Human TRAIN/CAL/DEV panels only from the previously unexposed
chr2/4/6/8/10/12/14/16/18 pool. Five train chromosomes and three validation
chromosomes are selected label-blind from that pool and one is retained unused.

### X0 numerical readiness gates

X0 passes only when all decision-bearing panels satisfy:

- exact FASTA/annotation assembly and contig agreement;
- zero coordinate overlap between train and CAL/DEV;
- zero external-species sequence in train, CAL or DEV;
- unknown mass no greater than 10% of callable panel bp;
- positive prevalence between 0.5% and 80%;
- each CAL and DEV panel has at least 100,000 positive and 500,000 callable
  negative bp;
- each primary or replication panel has at least 250,000 positive and
  2,000,000 callable negative bp;
- an external panel supplies at least sixteen 512-kb blocks containing both
  positive and negative callable bases;
- no chromosome supplies more than 40% of external evaluated bp.

A failed gate changes the decision to repair or exclude that species; no GPU
job is submitted for an invalid denominator.

## Animal panels and sealing

### Shared-model TRAIN/CAL/DEV species

| Species | Assembly | Role |
|---|---|---|
| Human | `hs1` | mammal anchor |
| Mouse | `mm39` | mammal anchor |
| Chicken | `galGal6` | avian vertebrate |
| Zebrafish | `danRer11` | teleost vertebrate |
| Pig | `susScr11` | replacement mammal |
| *C. elegans* | `ce11` | invertebrate exposure |

All Drosophila sequence is excluded so that `dm6` remains a true species
holdout.

### External species

| Layer | Species | Assembly/truth | Use |
|---|---|---|---|
| sealed primary T0 | Horse | `equCab3` Label-A | placental mammal |
| sealed primary T0 | Opossum | `monDom5` Label-A | marsupial |
| sealed primary T0 | Fruit fly | exact `dm6` Label-A | distant invertebrate |
| locked replication T0 | Cattle | `bosTau9` Label-A | mammalian replication |
| stress/QC only | Lizard | `anoCar2` Label-A | non-gating label/domain stress |
| stress/QC only | *X. laevis* | `xenLae2` Label-A | non-gating label/domain stress |
| stress/QC only | Honeybee | `apiMel2` Label-A | known prevalence/source risk |
| stress/QC only | Beetle | `triCas2` Label-A | known weak specialist signal |
| external T1 | FlyBase FB2026_02 | exact r6.68 positives | recall only; never F1 |

X0 may inspect label/source and coordinate metadata for every species, but it
must not run model inference. Horse, opossum and `dm6` remain sealed until the
model arm, all three checkpoints, calibration and global threshold are frozen.
Cattle opens only after the primary panel passes. Pig and cattle do not count
as two independent evolutionary levels because pig is now a training species.
The seal is prospective for this route: these species appeared in older screens,
so E1 is a frozen external re-evaluation, not a first-ever blind experiment.

`xenTro10` is removed from the decision-bearing route: its whole-genome
Label-A strict-TE mass is only 84,583 bp, less than even one CAL or DEV minimum,
so no label-blind split can pass. Lizard, *X. laevis*, honeybee and beetle remain
diagnostic until their labels and training representation can support an
interpretable gate. Rat and dog are legacy, non-fullpartition assets and do not
enter X0-R2.

## First model contract

The first cross-species route uses the representation with the strongest
existing multi-species training evidence:

- NTv2-500M 4096-bp initialization from the existing H0 step-800 final
  checkpoint, loading model weights only;
- native 4096-bp binary token head;
- 2,000 update steps;
- effective batch 12: B1/B2 use one 8192-bp tile, or two model windows, per
  species per update; the matched H1 control uses six Human tiles per update;
- label-blind uniform sampling within species;
- per-window callable-bp loss followed by equal species aggregation;
- no post-processing;
- one shared calibration and threshold for every species;
- final-step checkpoint, not target-selected best checkpoint.

The existing run-root loader resolves H0 to the Human-validation-selected
step-600 `best_model`; B1/B2 must not use that implicit selection. Their frozen
initialization is the explicit
`TFSUPP_ntv2_500m_H0_w4096_seed42/checkpoints/checkpoint-800` model state. The
tokenizer comes from the original NTv2-500M model, because the checkpoint stores
weights/config but no tokenizer files. Optimizer and scheduler state are reset.
This choice does not assert that step 800 is better than step 600; it makes the
initialization time point deterministic and removes a Human-validation model
selection event.

The H0 metadata recovers AdamW, linear decay, learning rate `2e-5`, weight decay
`0.01`, warmup ratio `0.1`, TE class weight `3`, batch `1` and gradient
accumulation `8`. B1/B2 retain the schedule meaning rather than the old absolute
warmup duration: 2,000 updates therefore use exactly 200 warmup updates. An
80-update warmup would silently change the ratio from 10% to 4%.

This does not discard P3. P3 supplies topology guardrails and motivates a
later controlled multiscale-head comparison. It is not the first cross-species
arm because its 8192-bp training evidence is Human-only and its boundary
mechanism gate failed. Changing backbone and adding a U-Net while also changing
species would make a first-round gain uninterpretable.

## Experiment matrix

| ID | Hypothesis | Only changed variable | Data and split | Leakage status | Decision gate | Compute unit | Allowed conclusion |
|---|---|---|---|---|---|---|---|
| `X0-LABEL-SPLIT` | A comparable animal denominator exists | none; audit/materialization only | all listed exact assemblies; frozen coordinates | no inference; exposes source/split failure | all X0 gates pass or stop | CPU; no model job | whether this study is executable |
| `I0-H0-INIT` | Continued training changes cross-species behavior relative to its actual start | zero weight updates | six-species CAL/DEV; external only when E1 opens | one existing seed42 reference; no external feedback | attribution reference only | calibration/inference | seed42 before/after change |
| `H1-HUMAN-MATCHED-CONTINUE` | Any B1 change is not explained only by continued optimization and the new target projection | training composition only: six Human tiles per step | Human TRAIN; six-species CAL/DEV | Human coordinates exclude H0-supervised chromosomes; external sealed | attribution control only | one 2,000-step GPU arm for seed 42 | separates the multispecies distribution effect from the matched continuation recipe |
| `B1-BALANCED-ERM` | Equal-species sampling is sufficient for one shared model | H1 Human-only composition -> one tile from each of six species | TRAIN/CAL/DEV only | external species sealed; family/homology unproved | internal shared-model gate | one 2,000-step GPU arm per seed | shared-model engineering evidence |
| `B2-GROUPDRO` | Worst-species optimization reduces negative transfer | loss aggregation only: ERM -> frozen GroupDRO | identical to B1 | identical to B1 | B2 replacement gate | one 2,000-step GPU arm per seed | whether loss balancing is useful |
| `B0-FAILURE-SPECIALIST` | A shared-model failure is recoverable by target capacity | training distribution only; same NT model and budget | only failing TRAIN species; chromosome-disjoint | target-supervised diagnostic, never external evidence | specialist negative-transfer gate | one arm per failing training species | whether routing has a recoverable gap |
| `A1-CLADE-ADAPTER` | Small known-clade modules resolve structured negative transfer | <=0.5% adapter parameters only | same TRAIN/CAL/DEV | taxonomy route; no external labels | adapter admission/pass gates | conditional GPU arm | low-capacity clade conditioning value |
| `M1-SOFT-MOE` | Conditional computation beats adapters and larger dense controls | soft/top-2 experts only | same TRAIN/CAL/DEV | route learned without external labels | strict MoE gate and matched controls | conditional; not currently authorized | MoE value on this comparator |
| `R1-FASTA-ROUTER` | Unlabeled assembly sequence can select a validated path | taxonomy route -> frozen assembly-sketch route | nested LOSO and LOCO; model frozen | no labels or predicted TE fraction | retains route gain or abstains | CPU routing audit | sequence-domain routing, not phylogeny inference |
| `E1-PRIMARY-PANEL` | Frozen shared arm transfers to unseen animal species | evaluation only | horse, opossum, dm6; 1,200 tiles each | species held out; threshold frozen | engineering external gate | inference only | panel-level species transfer |
| `E2-CATTLE-REPLICATION` | Mammalian transfer replicates once | evaluation only | cattle; 1,200 tiles | locked until E1 passes | cattle gate | inference only | mammalian replication |
| `E3-FULL-ASSEMBLY` | Panel result survives exhaustive denominator | panel -> all callable bases only | unchanged horse, opossum, dm6, cattle assemblies | no refit or threshold change | full-assembly claim gate | whole-assembly inference | claim on these assemblies only |

X0 and TRAIN materialization have passed. The next released units are the H0
loader identity gate, I0 and a two-step H1/B1/B2 engineering smoke. H1, B1 and
B2 use the same initialization, update count, optimizer, target projection and
compute; H1 versus B1 changes only training-species composition, while B1
versus B2 changes only loss aggregation. Exact wall time is not assumed: the
smoke must measure it before any 2,000-step budget is requested.

## Training, calibration and internal selection

### I0 initialization reference

`I0-H0-INIT` applies zero weight updates to the frozen H0 step-800 seed42
checkpoint. It fits its own six-species CAL global Platt map and threshold and
reports the same six-species DEV metrics as B1/B2. It is mandatory for the
seed42 before/after comparison, but it is not a training arm and does not enter
the B1-versus-B2 replacement gate, three-seed mean, no-seed-below-0.77 gate,
architecture admission or deployment selection. Its external predictions are
released only when E1 is released for the already-frozen trained pipelines and
cannot feed back into training or arm selection.

I0 can show how much 2,000 further updates changed this particular H0
checkpoint under the same calibration contract. It cannot establish
initialization-seed robustness or isolate the causal effect of multispecies data
from the effect of additional optimization.

Before I0 or any continuation arm is consumed, a loader identity gate compares
the checkpoint-native H0 loader with the B1/B2 loader on the first 16 fixed
Human CAL halves in CPU FP32 evaluation mode. Token IDs and attention masks
must be exactly equal; token-logit and bp-projected margin maximum absolute
differences must be at most `1e-6`; token-margin signs must agree exactly. A
failure permits only a loader correction and blocks training. The gate records
the observed differences directly; it does not add unused checksums.

### H1, B1 and B2

H1 starts from the same H0 step-800 state and applies the same reset optimizer,
200 warmup updates, 2,000 total updates, bp-mass target/loss and final-step
selection as B1. Each update draws six Human TRAIN tiles, so total model-window
compute is matched to B1. Therefore `I0 -> H1` measures the combined effect of
continued optimization plus the new Label-A/bp-mass recipe, and `H1 -> B1`
isolates the change from Human-only to six-species training composition. H1 is
an attribution control, not a deployment candidate.

B1 uses equal-species ERM. B2 uses the preregistered GroupDRO update on the six
per-species losses. Each optimizer update observes the species in the frozen
order Human, Mouse, Chicken, Zebrafish, Pig and *C. elegans*. A species
microbatch is the two 4096-bp halves of one 8192-bp tile; each half is first
normalized by its weighted callable-bp mass and the two half losses are then
averaged.

B1 gives every species weight `1/6`. B2 starts from uniform `q`, uses
`eta=0.01`, and applies the exponentiated update from the detached current six
species losses to the next optimizer step. The update is maintained in
float64 log space. There is no EMA, uniform smoothing or min/max clamp. The
manual PyTorch loop directly backpropagates `q_s*L_s`; at initialization this
is `L_s/6`, so the six species losses sum to the equal-species mean. Thus
aggregation is the only arm difference.

Seed 42 is an engineering comparison on CAL/DEV only. B2 replaces B1 only if:

- minimum-species DEV bp F1 improves by at least 0.02;
- macro DEV F1 falls by no more than 0.005;
- no species loses more than 0.01 bp F1;
- the equal-species macro hard-negative false-positive rate rises by no more
  than 0.005;
- the topology guardrails below pass.

Otherwise B1 remains the shared arm and only B1 is added at seeds 17 and
20260903. If B2 passes the seed-42 replacement gate, both B1 and B2 are run at
seeds 17 and 20260903. B2 replaces B1 only if the same replacement conditions
pass on the three-seed mean, B2 has positive minimum-species F1 change at every
seed, no seed contains a species loss greater than 0.01 and topology guardrails
pass at every seed. Otherwise B1 is retained. H1 accompanies the seed-42
cohort; additional H1 seeds are unnecessary for selecting B1 versus B2.

### Global calibration

Each seed fits its own global Platt map and threshold from the six CAL species;
there is no across-seed logit or mask ensemble. Within a seed, species receive
equal total weight and callable bp receive equal weight within species. The
input is the bp-projected TE-minus-background logit margin. Platt fitting uses
no class weight or regularization and constrains the slope to be nonnegative.

Threshold candidates are the unique calibrated probabilities plus the two
all-positive/all-negative endpoints; tied probabilities are never split. First
maximize minimum-species CAL F1, retain candidates within `0.001` of that
maximum, then maximize macro-species F1. Remaining ties within `1e-12` choose
the threshold closest to 0.5, then the higher threshold. The resulting map and
threshold are shared across species for that seed and applied unchanged to DEV
and every released external panel. This per-seed definition is required for
the three-seed mean and no-seed-below-0.77 gates.

A label-optimized per-species threshold may be reported only as
`TEST_LABEL_ORACLE_THRESHOLD`. It is diagnostic of ranking versus calibration
and cannot enter a success gate or deployment route.

### Internal shared-model gate

Before any external panel opens, all three selected-arm seeds must show on each
of the six DEV species:

- mean bp F1 >=0.80;
- mean bp precision and recall each >=0.75;
- macro-species bp F1 >=0.83;
- no topology guardrail violation.

If this passes, stop architecture expansion and open E1. Adapters and MoE are
not rewards for a successful shared model.

## Diagnosing negative transfer before conditional models

If any TRAIN species fails the internal gate, B0 trains the identical NT model
on that species with chromosome-disjoint TRAIN/CAL/DEV and a diagnostic
species-specific CAL threshold. A recoverable negative-transfer case requires
all three seeds to show:

- specialist DEV bp F1 >=0.85;
- at least +0.05 bp F1 over the shared arm;
- at least +0.03 AUPRC over the shared arm;
- the same direction on topology guardrails.

If the specialist remains below 0.80, the problem is label/data/backbone
capacity; routing and MoE are no-go. One recoverable species does not admit
conditional modeling. A deterministic adapter for a clade is admitted only
when at least two training species in that same identifiable clade independently
pass the complete specialist recovery gate. MoE remains closed at this point.

## Adapter and MoE gates

### Deterministic adapters first

The initially identifiable taxonomy groups are:

- Mammalia: Human, Mouse and Pig;
- non-mammalian vertebrates: Chicken and Zebrafish.

*C. elegans* alone cannot identify an Ecdysozoa or invertebrate adapter. A
proposal to route unseen `dm6` to a one-species *C. elegans* adapter is therefore
not claim-grade. Until a second independent invertebrate training species
passes X0, `dm6` uses the shared fallback.

Adapters are at most 0.5% of backbone parameters and add at most 2% active
FLOPs. They advance only if they improve minimum DEV F1 by at least 0.03,
recover at least half of the specialist gap, cause no species loss greater than
0.01 and preserve the shared fallback in LOSO/LOCO diagnostics. If all species
reach 0.80, stop at adapters.

### MoE admission

M1 is authorized only when all conditions hold:

1. at least two separately identifiable clades each contain at least two
   species with recoverable specialist gaps;
2. a deterministic adapter independently passes its gate in both clades;
3. each passing adapter leaves a residual specialist gap of at least 0.03 and
   at least one species remains below 0.80;
4. the comparison includes a parameter-matched dense model and an
   active-FLOP-matched dense model within 5%;
5. external species remain sealed.

M1 passes only if minimum DEV bp F1 improves by at least 0.03 over A1, macro F1
by at least 0.01, no species loses more than 0.01, and the paired block-level
gain has a positive 95% lower bound. Expert load must not collapse: different
experts must dominate different clades and the effective expert count must be
at least 1.5. These checks determine whether MoE learned specialization rather
than merely adding capacity.

If A1 passes, stop at adapters. If M1 fails either matched dense control, close
MoE.

## External evaluation gates

### E1 engineering panel

The model arm, three checkpoints, global calibration and threshold are frozen
before E1. On each of horse, opossum and `dm6`:

- three-seed mean bp F1 >=0.80;
- no seed bp F1 <0.77;
- mean precision and recall each >=0.75;
- 512-kb paired-block bootstrap lower bound for mean F1 >=0.78;
- macro-species mean F1 >=0.83;
- worst-species mean F1 >=0.80;
- topology guardrails pass.

Passing supports `ANIMAL_L1_ENGINEERING_GO`, not a whole-genome claim.

### E2 cattle replication

Cattle opens only after E1 passes. It must meet the same mean F1 and
precision/recall gates and may be no more than 0.05 below the horse/opossum
mean. This is one mammalian replication, not a second evolutionary level.

### E3 full-assembly claim

The unchanged three checkpoints and global threshold are then scored on all
callable bases of horse, opossum, `dm6` and cattle. Use 1-Mb paired blocks
and 1,000 bootstrap resamples. Claim-grade success requires:

- every species three-seed mean bp F1 >=0.80;
- every species F1 95% lower bound >=0.80;
- no seed/species point F1 <0.78;
- mean precision and recall each >=0.75, with lower bounds >=0.73;
- macro-species F1 lower bound >=0.82;
- worst-species F1 lower bound >=0.80;
- topology guardrails pass.

The resulting claim is restricted to these held-out assemblies, this Label-A
comparator and a single global threshold. The full-assembly run expands the
denominator of the same species used in E1/E2; it is not a second untouched
species confirmation.

### Mandatory topology guardrails

For every candidate relative to B1 on the same coordinates:

- segment F1@IoU 0.8 and boundary F1@5 may not fall by more than 0.05 absolute;
- fragments/truth and split rate may not rise by more than 25%;
- missed rate may not rise by more than 0.03;
- fusion, short-prediction and length-stratified metrics are reported.

These are catastrophic-regression guards, not evidence of accurate biological
instances. A model can pass L1 while remaining unsuitable for complete TE
boundary annotation.

## Routing design

Deployment normally knows the assembly or TaxID. The primary conditional route
is therefore deterministic taxonomy metadata at the **whole-assembly** level.
Per-window and per-token routing are forbidden because they can use local TE
composition as a shortcut and create seams.

Only after a taxonomy-conditioned model passes may a raw-FASTA route be tested.
It uses a frozen whole-assembly Mash/FracMinHash-style summary, is evaluated by
leave-one-species-out and leave-one-clade-out folds, and falls back to the
shared model for an unseen clade. A distance above the 95th percentile of the
training LOSO distribution triggers abstention/shared fallback.

Forbidden inputs include target TE coverage, RepeatMasker output, annotation
source, family labels, predicted TE fraction, target validation F1 and
label-optimized thresholds. Because host distance explained little of the
earlier transfer variation and TE evolution can depart from the host tree, this
is `taxonomy-conditioned` or `sequence-domain routing`, not automatic
phylogenetic or evolutionary-relation inference.

## Decision tree

```text
X0 harmonized Label-A + split + denominator audit and materialization
|
+-- FAIL -> repair/exclude invalid data; submit no GPU job
|
`-- PASS -> H0 loader identity gate
    |
    +-- FAIL -> repair loader only; submit no continuation job
    |
    `-- PASS -> lock I0; smoke then run H1, B1 and B2 on seed 42
    |
    `-- select by frozen internal rule -> confirm seeds 17/42/20260903
        |
        +-- all six DEV species pass -> freeze model/calibration -> E1
        |
        `-- one or more TRAIN species fail -> B0 specialists on failures
            |
            +-- specialist also fails -> conditional route NO-GO; fix label/data/backbone
            |
            +-- fewer than two species in one clade recover -> no adapter or MoE
            |
            `-- >=2 species in one clade recover -> A1 deterministic adapter
                |
                +-- all pass -> stop at adapters -> E1
                |
                +-- no useful adapter gain -> close conditional route
                |
                `-- >=2 clades pass adapters, residual >=0.03 -> M1 + matched dense
                    |
                    +-- M1 fails matched controls -> close MoE
                    `-- M1 passes -> freeze -> E1

E1 horse/opossum/dm6
|
+-- FAIL -> report failed species transfer; do not tune on E1
`-- PASS -> E2 cattle
    |
    +-- FAIL -> no mammalian replication claim
    `-- PASS -> E3 unchanged full-assembly evaluation
```

## Plant expansion

Plant work starts only after the animal route is resolved. The earlier missing
Viridiplantae partition was repaired in the 30/30 species rerun, so the problem
is not assumed to be a missing Dfam library. Plant X0 must independently audit
Label-A agreement, polyploid/subgenome and unplaced-contig handling, revisit the
soybean/Arabidopsis specialist failures, and define unseen monocot and eudicot
holdouts. The animal threshold and router are tested as transfer hypotheses;
they are not assumed valid in plants.

## Immediate executable decision

Do not submit a full 2,000-step job until the H0 loader identity gate and the
H1/B1/B2 two-step smoke pass. Materialization job `12176202` is now the frozen
training data root. I0 may run alongside the smoke after identity passes, but
its CAL/DEV result must be recorded before viewing continuation-arm DEV
results. The first full cohort is H1/B1/B2 seed 42; H1 closes the otherwise
unresolved attribution between multispecies composition and the changed
continuation recipe.

Complex MoE, learned routing, plant training, boundary loss and architecture
search remain closed unless their explicit upstream gate opens. Horse, opossum,
`dm6` and cattle remain unread by training, calibration and internal selection.

## Evidence files

- `docs/experiments/P3-R2-DECISION-20260829.md`
- `docs/experiments/P3-R2-CLOSURE-20260830.md`
- `docs/experiments/C5-HYBRID-CLOSURE-20260831.md`
- `reports/tefm_calib/PIPE-TEFM-CALIB-20260621/FINAL_REPORT.md`
- `reports/tefm_final/PIPE-TEFM-FINAL-SELECTOR-20260630/FINAL_REPORT.md`
- `reports/tefm_final/PIPE-TEFM-FINAL-GENOMEDECAY-20260630/GENOME_DECAY_REPORT.md`
- `docs/species_label_source_audit.md`
- `docs/10_findings.md`
- `pipelines/PIPE-TEFM-SUPP-20260617/prepare_ucsc_windows.py`
- `pipelines/PIPE-TEFM-CALIB-20260621/prepare_species_holdout.py`

## Method anchors

- SegmentNT: [Annotating the genome at single-nucleotide resolution with DNA
  foundation models](https://www.nature.com/articles/s41592-025-02881-2)
- GroupDRO: [Distributionally Robust Neural Networks for Group
  Shifts](https://arxiv.org/abs/1911.08731)
- Soft MoE: [From Sparse to Soft Mixture of
  Experts](https://deepmind.google/research/publications/49566/)
- assembly sketching: [Mash: fast genome and metagenome distance estimation
  using MinHash](https://doi.org/10.1186/s13059-016-0997-x)
