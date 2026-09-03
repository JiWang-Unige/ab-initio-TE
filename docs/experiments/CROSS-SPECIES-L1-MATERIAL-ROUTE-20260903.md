# Cross-species L1 TE-material route decision (2026-09-03)

## Status

`PLAN FROZEN THROUGH X0; NO GPU TRAINING OR MOE AUTHORIZED YET`

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

The recorded version, command, source path and resulting manifest are the
consumed provenance. No unused checksum assets are added. UCSC, Ensembl,
FlyBase and other native annotations remain secondary comparators and are not
mixed into T0 truth.

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

Each training species contributes 1,500 train tiles and 300 validation tiles.
The 300 validation tiles are frozen before training as 150 `CAL` and 150 `DEV`
tiles. Across six species this is 73,728,000 training bp, or 18,000 native
4096-bp model windows.

For genomes with enough chromosomes, train tiles span at least five
chromosomes and CAL+DEV tiles at least three disjoint chromosomes. For
*C. elegans*, use four train chromosomes, one CAL/DEV chromosome and retain one
nuclear chromosome unused. External panels use 1,200 tiles across at least
four chromosomes or chromosome arms.

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
| *X. tropicalis* | `xenTro10` | amphibian vertebrate |
| *C. elegans* | `ce11` | invertebrate exposure |

All Drosophila sequence is excluded so that `dm6` remains a true species
holdout.

### External species

| Layer | Species | Assembly/truth | Use |
|---|---|---|---|
| sealed primary T0 | Horse | `equCab3` Label-A | placental mammal |
| sealed primary T0 | Pig | `susScr11` Label-A | placental mammal |
| sealed primary T0 | Opossum | `monDom5` Label-A | marsupial |
| sealed primary T0 | Fruit fly | exact `dm6` Label-A | distant invertebrate |
| locked replication T0 | Cattle | `bosTau9` Label-A | mammalian replication |
| stress/QC only | Lizard | `anoCar2` Label-A | non-gating label/domain stress |
| stress/QC only | *X. laevis* | `xenLae2` Label-A | non-gating label/domain stress |
| stress/QC only | Honeybee | `apiMel2` Label-A | known prevalence/source risk |
| stress/QC only | Beetle | `triCas2` Label-A | known weak specialist signal |
| external T1 | FlyBase FB2026_02 | exact r6.68 positives | recall only; never F1 |

X0 may inspect label/source and coordinate metadata for every species, but it
must not run model inference. Horse, pig, opossum and `dm6` remain sealed until
the model arm, all three checkpoints, calibration and global threshold are
frozen. Cattle opens only after the primary panel passes. Pig and cattle do
not count as two independent evolutionary levels.

Lizard, *X. laevis*, honeybee and beetle remain diagnostic until their labels
and training representation can support an interpretable gate. Rat and dog do
not enter until current Baobab assets are verified.

## First model contract

The first cross-species route uses the representation with the strongest
existing multi-species training evidence:

- frozen Human H0 NTv2-500M 4096-bp initialization;
- native 4096-bp binary token head;
- 2,000 update steps;
- effective batch 12, exactly two model windows per training species per
  update;
- label-blind uniform sampling within species;
- per-window callable-bp loss followed by equal species aggregation;
- no post-processing;
- one shared calibration and threshold for every species;
- final-step checkpoint, not target-selected best checkpoint.

The exact initialization, optimizer and schedule must be recoverable from the
existing H0 run metadata. If they are not reproducible, training stops rather
than silently substituting a new recipe.

This does not discard P3. P3 supplies topology guardrails and motivates a
later controlled multiscale-head comparison. It is not the first cross-species
arm because its 8192-bp training evidence is Human-only and its boundary
mechanism gate failed. Changing backbone and adding a U-Net while also changing
species would make a first-round gain uninterpretable.

## Experiment matrix

| ID | Hypothesis | Only changed variable | Data and split | Leakage status | Decision gate | Compute unit | Allowed conclusion |
|---|---|---|---|---|---|---|---|
| `X0-LABEL-SPLIT` | A comparable animal denominator exists | none; audit/materialization only | all listed exact assemblies; frozen coordinates | no inference; exposes source/split failure | all X0 gates pass or stop | CPU; no model job | whether this study is executable |
| `B1-BALANCED-ERM` | Equal-species sampling is sufficient for one shared model | Human-only fitting -> frozen six-species balanced fitting | TRAIN/CAL/DEV only | external species sealed; family/homology unproved | internal shared-model gate | one 2,000-step GPU arm per seed | shared-model engineering evidence |
| `B2-GROUPDRO` | Worst-species optimization reduces negative transfer | loss aggregation only: ERM -> frozen GroupDRO | identical to B1 | identical to B1 | B2 replacement gate | one 2,000-step GPU arm per seed | whether loss balancing is useful |
| `B0-FAILURE-SPECIALIST` | A shared-model failure is recoverable by target capacity | training distribution only; same NT model and budget | only failing TRAIN species; chromosome-disjoint | target-supervised diagnostic, never external evidence | specialist negative-transfer gate | one arm per failing training species | whether routing has a recoverable gap |
| `A1-CLADE-ADAPTER` | Small known-clade modules resolve structured negative transfer | <=0.5% adapter parameters only | same TRAIN/CAL/DEV | taxonomy route; no external labels | adapter admission/pass gates | conditional GPU arm | low-capacity clade conditioning value |
| `M1-SOFT-MOE` | Conditional computation beats adapters and larger dense controls | soft/top-2 experts only | same TRAIN/CAL/DEV | route learned without external labels | strict MoE gate and matched controls | conditional; not currently authorized | MoE value on this comparator |
| `R1-FASTA-ROUTER` | Unlabeled assembly sequence can select a validated path | taxonomy route -> frozen assembly-sketch route | nested LOSO and LOCO; model frozen | no labels or predicted TE fraction | retains route gain or abstains | CPU routing audit | sequence-domain routing, not phylogeny inference |
| `E1-PRIMARY-PANEL` | Frozen shared arm transfers to unseen animal species | evaluation only | horse, pig, opossum, dm6; 1,200 tiles each | species held out; threshold frozen | engineering external gate | inference only | panel-level species transfer |
| `E2-CATTLE-REPLICATION` | Mammalian transfer replicates once | evaluation only | cattle; 1,200 tiles | locked until E1 passes | cattle gate | inference only | mammalian replication |
| `E3-FULL-ASSEMBLY` | Panel result survives exhaustive denominator | panel -> all callable bases only | unchanged horse, pig, opossum, dm6, cattle assemblies | no refit or threshold change | full-assembly claim gate | whole-assembly inference | claim on these assemblies only |

The only currently released arm is X0. After X0 passes, B1 and B2 may run in
parallel on seed 42 because they use the same frozen data and differ only in
loss aggregation. Exact wall time is not assumed: a short throughput run must
measure it before requesting the three-seed budget.

## Training, calibration and internal selection

### B1 and B2

B1 uses equal-species ERM. B2 uses the preregistered GroupDRO update on the six
per-species losses; its exact learning-rate and smoothing constants are frozen
in the run config before seed 42.

Seed 42 is an engineering comparison on CAL/DEV only. B2 replaces B1 only if:

- minimum-species DEV bp F1 improves by at least 0.02;
- macro DEV F1 falls by no more than 0.005;
- no species loses more than 0.01 bp F1;
- hard-negative false-positive rate rises by no more than 0.005;
- the topology guardrails below pass.

Otherwise B1 remains the shared arm. The selected rule is then run at seeds
17, 42 and 20260903. If the direction is inconsistent across seeds, B1 is
retained.

### Global calibration

Each arm fits one global Platt map and one threshold from the six CAL species,
weighted equally by species. The threshold maximizes minimum-species CAL F1;
ties prefer higher macro F1, then proximity to 0.5, then the higher threshold.
The same frozen map and threshold are applied to DEV and every external
species.

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
capacity; routing and MoE are no-go. Conditional modeling is admitted only if
recoverable negative transfer occurs in at least two species from at least two
independent clades.

## Adapter and MoE gates

### Deterministic adapters first

The initially identifiable taxonomy groups are:

- Mammalia: Human and Mouse;
- non-mammalian vertebrates: Chicken, Zebrafish and *X. tropicalis*.

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

1. B1/B2 leave at least two clades below 0.80;
2. B0 proves recoverable and complementary specialists in those clades;
3. A1 improves both clades but leaves a residual gap of at least 0.03;
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
before E1. On each of horse, pig, opossum and `dm6`:

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
precision/recall gates and may be no more than 0.05 below the horse/pig/opossum
mean. This is one mammalian replication, not a second evolutionary level.

### E3 full-assembly claim

The unchanged three checkpoints and global threshold are then scored on all
callable bases of horse, pig, opossum, `dm6` and cattle. Use 1-Mb paired blocks
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
X0 harmonized Label-A + split + denominator audit
|
+-- FAIL -> repair/exclude invalid data; submit no GPU job
|
`-- PASS -> B1 balanced ERM and B2 GroupDRO on seed 42
    |
    `-- select by frozen internal rule -> confirm seeds 17/42/20260903
        |
        +-- all six DEV species pass -> freeze model/calibration -> E1
        |
        `-- one or more TRAIN species fail -> B0 specialists on failures
            |
            +-- specialist also fails -> MoE NO-GO; fix label/data/backbone
            |
            +-- only one clade recoverable -> no MoE; shared fallback
            |
            `-- >=2 species and >=2 clades recover -> A1 clade adapters
                |
                +-- all pass -> stop at adapters -> E1
                |
                +-- no useful adapter gain -> close conditional route
                |
                `-- useful gain but residual >=0.03 -> M1 + matched dense
                    |
                    +-- M1 fails matched controls -> close MoE
                    `-- M1 passes -> freeze -> E1

E1 horse/pig/opossum/dm6
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

Do not submit a GPU training job from existing mixed JSONL. It would answer the
wrong question because its source, coordinate and prevalence confounding are
unresolved. The next and only released unit is `X0-LABEL-SPLIT`, a CPU/data
audit and materialization step. Its output must be a compact manifest and
decision report, while FASTA, labels and large JSONL remain outside Git.

After X0 passes, run B1 and B2 seed 42 in parallel. Complex MoE, a learned
router, plant training, boundary loss and architecture search remain closed
unless their explicit upstream gate opens.

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
