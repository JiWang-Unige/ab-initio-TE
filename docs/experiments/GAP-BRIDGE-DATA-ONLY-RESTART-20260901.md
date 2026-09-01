# Data-only gap-bridge restart

Date: 2026-09-01

Status: **E0 engineering PASS; chunked full Phase 0 authorized; no new scientific result**

## E0 engineering result

- The frozen E0 contract was implemented at commit
  `e33b2ae9426a426ae2f5932b623455f0360edc74`; the CPU-only finalizer was added
  at `b887fa5`. Twelve targeted tests now pass, including explicit-region tail
  coverage, comparator projection, ambiguity retention and Slurm contracts.
- Job `12126691` passed the chr17 identity regression: all 25,543 ordered
  `(seqid,start,end)` tuples and the declared 9,830,400-bp length were exactly
  equal. No scientific metric was computed.
- The first chr3/chr5 array, `12126692_[0-1]`, completed each 50-Mb/6,104-window
  materialization before both tasks failed with exit 120 during a simultaneous
  BeeGFS `Communication error on send`. The failure is retained and excluded
  from every scientific denominator.
- The unchanged retry, `12127337_[0-1]`, wrote complete PASS export manifests,
  four-state `(50,000,000,4)` float16 tracks, float32 P_TE tracks and canonical
  masks for both chromosomes. Each task then failed only while flushing its
  final JSON to the long-idle Slurm/BeeGFS stdout stream. The valid exports
  were reused rather than spending another six GPU-hours.
- CPU finalization job `12128518_1` completed chr5. Task `12128518_0` failed
  with an explicit BeeGFS `OSError: [Errno 121] Remote I/O error` while writing
  chr3 candidates; chr3-only retry `12128695_0` then completed. Both failures
  remain in the engineering ledger.

| Region | Coverage contract | P3 intervals | Candidates | Eligible main | Bridge | Separation | Ambiguous | Terminal source |
|---|---|---:|---:|---:|---:|---:|---:|---|
| chr3:0-50M | 50,000,000 bp; 6,104 windows; 0 missing/overlap; one tail | 121,796 | 121,795 | 106,859 | 25,268 | 2,344 | 94,183 | export `20260901-r2`; finalize `20260901-r2` |
| chr5:0-50M | 50,000,000 bp; 6,104 windows; 0 missing/overlap; one tail | 99,631 | 99,630 | 85,017 | 23,915 | 1,699 | 74,016 | export `20260901-r2`; finalize `20260901-r1` |

Candidate and labeled tables have identical row counts on both chromosomes.
All three comparator relations are represented, so E0 establishes that the
frozen split, coordinate, export and label machinery is executable. These are
candidate censuses, not classifier performance, fragment improvement or a
publication result.

## Full Phase 0 resource decision

The valid 50-Mb exports required 3:12:15 and 3:13:13 per GPU. At that observed
rate, the frozen full chr3/chr5/chr13/chr19 set contains 552,815,762 bp and
requires approximately 35.5 GPU-hours for P3 export alone. The identity run
and two preflight attempts have already consumed approximately 11.3
GPU-hours, including the retained infrastructure failures. Therefore the full
screen did not fit the former cohort limit of 24 new GPU-hours. The observed
E0 spend plus one complete full-screen export is approximately 46.8
GPU-hours, which fits the user-approved 64-GPU-hour rebase below.

Decision: `E0_ENGINEERING_PASS`. On 2026-09-01 the user explicitly approved
private-node execution beyond the old 24-GPU-hour planning cap; the project
cap is rebased to 64 GPU-hours. Full Phase 0 is therefore
`AUTHORIZED_CHUNKED_PRIVATE`.

The four chromosomes are partitioned into 13 shards whose internal boundaries
are exact multiples of 8,192 bp. This preserves the original non-overlapping
P3 window geometry; only the last shard of each chromosome contains a tail
window. A dependent CPU stage must losslessly concatenate tracks and region
rows, merge a positive run crossing a shard boundary, and only then generate
whole-chromosome candidates. The scientific chromosomes, labels, feature
arms, test seal and gates remain unchanged. No reduced-chromosome substitute
is allowed to enter the scientific denominator.

The stitch stage projects comparator labels for chr3/chr5 training and chr13
validation only. It emits label-blind chr19 candidates plus an explicit seal;
chr19 comparator projection and every test metric remain forbidden until all
chr13 feature, regularization and operating-threshold choices are locked.

## Outcome

Gate L is retired from the active publication route because the required
independent TE-locus experts are not available. Its frozen contracts and
machine-ready annotation kits remain useful engineering assets, but the gate
was never scientifically evaluated and is neither a PASS nor a biological
NO-GO. Its terminal status is:

`RETIRED_UNEXECUTED_RESOURCE_INFEASIBLE`

The replacement route deliberately changes the estimand. It does not attempt
to reconstruct a biological or ancestral TE insertion. It asks whether a
frozen high-recall P3 material detector can be followed by a selective,
abstaining refiner that fills only those prediction-defined internal gaps
whose bases are supported as TE-positive by the existing Human comparator.
This is **comparator-consistent repeat-mask continuity**, not instance truth.

The one authorized next experiment is a feature-only P3 gap-discriminability
screen on previously unmaterialized Human chromosomes. It must precede a new
Transformer, CNN, continual learning or backbone update. The historical
FRAGGRAPH failure makes this a single re-entry falsification of the method
class, not a new unconstrained research branch.

## Why the target changes

The unavailable human judgement was essential only for claims about extant
locus identity, nested relations and biological insertion reconstruction. It
is not necessary for the narrower operational question of whether filling a
P3-negative interval makes the output agree more closely with the frozen
Human TE/background/unknown comparator.

Three targets must remain separate:

| Target | Available supervision | Current status | Legal claim |
|---|---|---|---|
| Biological insertion/locus reconstruction | Independent locus identity and typed nested/deleted relations | unavailable | abandoned under current assets |
| Comparator-consistent mask continuity | Human TE/background/unknown runs | available | active primary target |
| Downstream gene-annotation utility | fixed gene features; no rerun gene predictor yet | safety proxy only | no gene-accuracy claim |

For the active target, an adjacent pair of P3-positive runs is not claimed to
come from one insertion. The only action is whether the bases between them may
be added to a secondary repeat mask under the comparator contract.

## First-principles decomposition

### Confirmed facts

1. Human P3-R1 has high material recall on the consumed chr17 prefix
   (`0.943150`) but fragments comparator runs (`1.292430` fragments/truth).
2. Human P3 produced 4,961 internal gaps inside 14,253 comparator-positive
   runs. `48.84%` are 1 bp, `64.77%` are at most 2 bp, `80.91%` are at most
   5 bp, while p99 is 137.4 bp and the maximum is 16,384 bp.
3. Base, DAPT and P3 leave essentially the same Human internal false-negative
   mass (`1.154-1.155%` of truth bp). They mainly redistribute the mass into
   different run topologies.
4. Mouse P3 retains high material recall (`0.95298`) but has worse continuity
   (`2.144` fragments/truth). Fly is positive-only and cannot supply this
   route's negative denominator.
5. The Human comparator contains TE/background/unknown material runs. It does
   not contain biological copy identity, ancestral insertion boundaries or
   parent-child topology.
6. The materialized 8192-bp files contain only 3,000 chr1 train windows,
   3,000 chr11 validation windows and 3,000 chr17 test windows, each covering
   `0-24,576,000`. Metadata listing additional chromosomes described a plan,
   not the files that were actually materialized.
7. The P3-R1 checkpoint exists, but current chr17 products contain binary
   intervals and metrics rather than a reusable probability/logit track.
8. Generic DAPT, the tested TE-aware MLM, boundary/U-Net variants, simple gap
   merging, minimum length, HMM/CRF-style smoothing, near-full-seed C5 and
   consensus-coordinate-only recovery did not solve the active problem.

### Unverified assumptions being removed

- A short gap is automatically a model error.
- Two same-family fragments necessarily belong to one insertion.
- Better bp F1 guarantees a usable continuous repeat mask on a gigabase
  genome.
- A more expressive decoder can manufacture missing instance identity from
  the same local mask supervision.
- Comparator-negative sequence inside a putative insertion is biologically
  irrelevant to repeat masking or gene annotation.
- Reweighting the same comparator errors through continual learning is an
  independent information source.

### Actual objective

Starting from an immutable P3 mask, recover a useful subset of
comparator-positive internal gap bases at very high added-bp precision, reduce
comparator-run splitting and add negligible comparator-negative mask in gene
features. Always retain the original P3 output and emit every proposed fill in
a scored sidecar.

### Resources and constraints

- frozen P3-R1 backbone/head, 8192-bp geometry and threshold;
- Human genome and comparator with callable/unknown states;
- raw sequence and the ability to export frozen P3 logits on new regions;
- RepeatMasker/Dfam family or consensus evidence only after its exact source
  and leakage role are stated;
- fixed Human gene annotation only for incremental masking audit;
- no independent biological instance panel and no expert annotation budget;
- Mouse only after the Human gate; Fly is not part of routine development;
- chr17 is consumed; chr20-22 remain untouched final-confirmation reserve.

## Gate L disposition

Gate L is not renamed into an automatic gate. That would silently replace its
original biological-locus estimand while preserving misleading terminology.
The new decision is `GAP-BRIDGE-DATA-GATE-V0`, with new labels, denominators,
metrics and claims.

The following Gate L artifacts remain archived and reproducible:

- V1.4 ontology and annotation contract;
- frozen calibration/main/reserve packages;
- provenance-audit and adjudication schemas;
- automatic calculators and their engineering tests.

They are not inputs to the new classifier and cannot be described as an
evaluated biological truth panel.

## Historical FRAGGRAPH negative result

The proposed second stage has a historical near-neighbour and must not be
presented as wholly new. `PIPE-TEFM-CAP-FRAGGRAPH-20260701` trained a learned
linker on frozen old-CE embeddings, probabilities and geometry. It used at
most 128 train windows, 40 evaluation windows, 80 steps and one seed.

| Panel/arm | bp F1 | segment F1@0.8 | boundary F1@5 | deleted true-backed fraction |
|---|---:|---:|---:|---:|
| Human CE raw | 0.8369 | 0.1542 | 0.0763 | 0.0000 |
| Human graph keep-all | 0.8369 | 0.1542 | 0.0763 | 0.0000 |
| Human graph keep/drop | 0.7546 | 0.4964 | 0.2458 | 0.8632 |
| Mouse CE raw | 0.8232 | 0.1437 | 0.0513 | 0.0000 |
| Mouse graph keep-all | 0.8232 | 0.1437 | 0.0513 | 0.0000 |
| Mouse graph keep/drop | 0.8159 | 0.3676 | 0.1313 | 0.5253 |

Preservation-first decoding learned no useful links; deletion produced an
unsafe apparent interval gain. That result closes a repeat of the same old-CE
graph recipe.

One bounded re-entry is nevertheless scientifically distinct enough to test:

- frozen P3-R1 begins at 94.3%, not 75.6%, Human bp recall;
- the action is fill-only and can never delete an existing P3-positive base;
- candidate prevalence is measured naturally on new chromosomes;
- labels are gap-base comparator support, not same-insertion identity;
- raw sequence and joint fragment evidence are tested against distance and
  logits, with chromosome holdout and added-bp safety metrics.

If this re-entry fails, a larger neural gap model is not authorized.

## Candidate ontology

Candidates are generated before reading comparator labels. Let adjacent
maximal frozen-P3 positive runs be `[a,b)` and `[c,d)`, with `b<c`. Their
candidate gap is `[b,c)`. The main universe is limited to callable genomic
gaps of `1-512` bp on one chromosome, with no assembly `N` or frozen unknown
base. Padding and non-genomic window tails are excluded by coordinate
contract, not outcome. Candidates near a window seam remain eligible and
carry seam distance as a feature. Gaps longer than 512 bp automatically
abstain and their count and bp mass are reported separately. The 512-bp cap is
an inherited re-entry contract, not a biological boundary.

After candidate generation, the comparator assigns exactly one evaluation
label:

| Label | Definition | Meaning |
|---|---|---|
| `COMPARATOR_BRIDGE_SUPPORTED` | every gap base and the two immediately adjacent P3-positive bases are comparator-positive and belong to one maximal comparator-positive run | filling the gap agrees with this comparator |
| `COMPARATOR_SEPARATION_SUPPORTED` | every gap base is callable comparator-negative, the immediately adjacent P3-positive bases are comparator-positive, and the flanks belong to two different maximal comparator-positive runs | leaving the gap agrees with this comparator |
| `COMPARATOR_RELATION_AMBIGUOUS` | mixed/unknown gap state, unsupported flank, assembly uncertainty or any other non-clean relation | excluded from clean training and AP; any comparator-negative bp filled here still counts as added FP |

These labels replace the proposed names `model_gap=1` and `true_gap=0`.
Neither class proves TE origin, same-family identity or same biological
insertion. The same-family adjacent-copy failure is a valid negative whenever
the intervening callable bases are comparator-negative.

## Routes ranked by new information

| Rank | Route | New observable information | Current decision |
|---:|---|---|---|
| 1 | Frozen P3 plus feature-only selective gap classifier | raw gap/flank sequence, frozen logit shape, cross-fragment relation evidence | one Phase-0 re-entry authorized |
| 2 | SV-like joint fragment-to-consensus/cluster evidence | one-copy versus two-independent-copy alignment support, orientation and consensus-coordinate order | feature group and deterministic baseline inside Route 1; library-assisted claim only |
| 3 | Continual/hard-example post-training | no new information if trained only on the same comparator errors | closed unless library-free signal survives chr19, the purged challenge, chr20-22 confirmation and unchanged Mouse transfer |

The SV analogy is useful only at the evidence level. A structural-variant
split-read model asks whether two anchors admit one coherent explanation; it
does not license a distance-only merge or a same-family-equals-same-copy rule.

## Unified experiment matrix

| ID | Hypothesis | Unique change | Data/split | Model/tool | Leakage status | Gate consequence | Claim scope |
|---|---|---|---|---|---|---|---|
| E0 | New-region materialization and frozen inference are feasible | regions/logit export only | chr17 identity regression; chr3:0-50M + chr5:0-50M preflight | frozen P3-R1 | no scientific val/test metric read | establishes identity, throughput and candidate prevalence; no scientific GO | engineering only |
| G0 | Length alone explains safe fills | maximum gap length selected on validation | chr3/5 train, chr13 val, chr19 test | deterministic merge | chromosome held out | baseline only | comparator refinement |
| G1 | Frozen logit/geometry patterns add information | logits/geometry over G0 | same | L2 logistic probe | chromosome held out | must beat G0 | comparator refinement |
| G2 | Raw sequence adds non-geometric information | fixed sequence summaries over G1 | same plus homology-purged challenge | L2 logistic probe | family may cross; purged and family-held-out challenges reported | only library-free evidence can later license a Phase-1 proposal | comparator refinement |
| A0 | Joint alignment distinguishes one coherent repeat explanation from two | deterministic consensus/cluster evidence | same | fixed alignment scorer | library identity and source coupling disclosed | use A0 if it matches learned model; do not train CNN | library-assisted refinement |
| B0 | Combined sequence/logit/A evidence safely recovers gap bases | feature groups combined; no neural sequence encoder | full chr3/5 train, chr13 val, chr19 one-use test | L2-regularized logistic regression | test labels and metrics sealed until chr13 choices lock | PASS may license one small Phase-1 CNN comparison; FAIL closes neural re-entry | comparator refinement |

No Mouse or Fly cell runs before the Human gate. No new backbone training,
Transformer, CNN or continual-learning arm is part of Phase 0.

## The one next experiment: GAP-BRIDGE-PHASE0-R1

### Sequential execution inside one protocol

1. **Logit-export identity regression:** rerun frozen P3-R1 inference on the
   consumed chr17 interval and require the thresholded/stitched mask to match
   the committed P3 binary intervals exactly, without reading a new metric or
   changing threshold, stitching or window geometry. Failure is
   `LOGIT_EXPORT_CONTRACT_INVALID`, not a scientific result.
2. **E0 engineering preflight:** materialize chr3:0-50M and chr5:0-50M,
   export four-state float16 logits or probabilities, reconstruct the binary
   mask and emit the candidate/label census, runtime and I/O report. The
   100-Mb preflight must demonstrate that both chromosomes were materialized,
   directly testing the previous first-contig-only defect. It does not enter
   the scientific denominator.
3. **Frozen full-chromosome screen:** after E0 succeeds, run complete chr3 and
   chr5 as stage-2 train, complete chr13 as validation and complete chr19 as a
   one-use route-selection test. chr20-22 remain unread final-confirmation
   reserve.

The split, 512-bp cap, label ontology, feature blocks and threshold rule are
frozen before comparator projection. Engineering throughput may change batch
size and resource request, but not the scientific contract.

### Inputs

- genomic sequence for the four full scientific chromosomes;
- frozen P3-R1 logits and binary mask;
- comparator TE/background/unknown track, used only after candidate export;
- exact alignment/family evidence only in the explicitly library-assisted A0
  arm;
- fixed gene annotation, used only after predictions are frozen for safety
  audit.

Comparator coordinates, family labels derived from the comparator, gene
annotations and test labels are prohibited as predictive features.

### Feature-only models and baselines

The first round uses no learned sequence encoder. It compares:

1. P3 unchanged;
2. fill-all sanity control, never promotable;
3. validation-selected `gap_length <= k` merge;
4. distance-only calibrated score;
5. geometry plus frozen-logit summary;
6. raw-sequence context plus geometry/logits;
7. deterministic A0 one-copy-versus-two-copy alignment evidence, when its
   source contract is valid;
8. `FULL_LIBRARY_FREE = geometry + P3 logits + fixed raw-sequence summaries`;
9. `FULL_LIBRARY_ASSISTED = FULL_LIBRARY_FREE + family/alignment evidence`.

The only statistical probe is L2-regularized logistic regression on scalar
features. Feature scaling, regularization and operating threshold are chosen
on chr13. Raw-sequence summaries may include GC, entropy, homopolymer/low-
complexity measures, fixed-context k-mer similarities, deterministic local
alignment, and microhomology; they cannot include a trainable encoder. A
Transformer, CNN, graph model or trainable embedding would confound
separability with optimization and is explicitly deferred.

### Metrics

Candidate-level:

- AUPRC and normalized AP under natural prevalence;
- calibration (Brier score and ECE);
- precision/recall/F1 at a validation-frozen threshold;
- distance-matched AUPRC;
- performance by gap length `1-2`, `3-5`, `6-20`, `21-100`, `101-512` bp;
- comparator-negative fill rate for adjacent same-family/consensus runs when
  that stratum is available.

Added-bp and whole-mask:

- added-bp precision;
- internal-gap-bp recall overall and for gaps longer than 5 bp;
- whole-mask bp precision/recall/F1/MCC;
- split rate, fragments/truth, internal-gap count and mass;
- missed and terminal-omission rates.

Because Phase 0 only adds bases inside frozen internal candidates, a change in
fully missed truth rate means the output contract was violated.

Gene-feature safety audit:

- added comparator-negative bp in CDS, coding exons, all exons, splice +/-2
  bp and promoter +/-200 bp;
- affected genes/exons and the added-mask fraction per feature;
- added-bp precision separately for candidates overlapping gene features.

The natural-prevalence chr19 test is primary. A label-blind homology-purged
challenge uses the fixed 256-bp left and right flanks, excluding chr19
candidates connected to chr3/5/13 at `>=80%` identity, `>=50%` reciprocal
coverage and `>=100` aligned bp. A family-held-out challenge is reported when
its denominator exists. These challenges diagnose memorization and do not
replace the deployment-prevalence result.

### Prospective gate

The validation threshold is the most permissive threshold satisfying
added-bp precision `>=0.98`. On untouched chr19, all of the following are
required:

1. chr19 contains at least 1,000 clean bridge candidates, 1,000 clean
   separation candidates, 200 bridge candidates longer than 5 bp, and 20
   independent 1-Mb blocks containing both classes; otherwise return
   `TEST_DENOMINATOR_INSUFFICIENT` for this asset;
2. combined feature AUPRC is at least `0.05` absolute above the best
   distance/simple-merge/logit baseline, and a 1-Mb block-bootstrap 95% lower
   bound for the AP difference is above zero;
3. the AP gain remains positive on the homology-purged challenge, and at least
   one non-distance block contributes
   `AP(full)-AP(geometry+logits) >=0.03`;
4. added-bp precision point estimate is `>=0.97` and its 95% lower bound is
   `>=0.95`;
5. internal-gap-bp recall is `>=0.20`, including `>=0.10` for gaps longer
   than 5 bp;
6. split rate and fragments/truth each decrease at least 15% relative;
7. whole-mask bp precision decreases by no more than `0.001` absolute,
   whole-mask F1 does not decrease, every original P3-positive base is
   retained and missed rate does not increase;
8. no comparator-negative filled base intersects an annotated canonical
   splice donor/acceptor core +/-2 bp,
   comparator-negative added mask divided by callable CDS is `<=1e-5`, and
   gene-overlap added-bp precision is `>=0.995`; at matched recall the method
   is no worse than the best simple baseline in CDS/exon negative fills, and
   no single annotated CDS receives more than 20 comparator-negative bp.

At matched added-bp precision, the combined model must also deliver at least
one of: 20% more positive gap bp recovered, 20% fewer negative bp filled, or
10% greater relative split reduction than the best simple/A0 baseline.

### Decisions

- **Feature-only FAIL:** close the new neural gap classifier and continual
  learning. Retain original P3 plus a non-actionable gap-confidence sidecar;
  do not tune another loss/head/decoder.
- **A0 matches the combined model:** adopt deterministic A0 and stop neural
  development.
- **Combined feature PASS but library-free sequence contributes nothing:**
  allow only a library-assisted comparator-refinement method; continual
  learning remains closed.
- **Combined feature PASS with library-free sequence gain that persists under
  the homology-purged challenge:** authorize at most one Phase-1 comparison
  between the frozen feature probe and a <=1M-parameter raw-sequence
  CNN/Siamese model. If the feature method already passes, prefer it rather
  than adding a neural model.
- **Human final confirmation PASS on chr20-22:** only then run one unchanged
  Mouse direction-of-effect audit. Fly is not required for this route.

## Continual learning decision

Continual learning is not run in parallel. Training P3 again on
`comparator-positive AND P3-negative` bases would merely increase the weight
of the same noisy reference labels and can reduce fragmentation by overfitting
the comparator or sacrificing background precision.

It becomes eligible for a new proposal only after a **library-free raw
sequence signal** beats geometry+logits on chr19 and the homology-purged
challenge, reproduces on chr20-22, and has a directionally consistent result
under unchanged Mouse transfer. A later continual experiment would still need
train-chromosome out-of-sample P3 errors, replay easy
positives/negatives/unknowns and a new set of completely unconsumed Human
confirmatory chromosomes. Without that full evidence chain, continual
learning remains closed for this question.

## Outputs and practical use

The method never overwrites the primary annotation. It emits:

1. the original strict P3 mask;
2. a continuity-refined **softmask**;
3. a BED sidecar for each proposed fill with score, feature arm and abstention
   reason.

Hardmasking is not the default because a small false-positive rate still
creates many incorrectly masked bases on a gigabase genome.

## Resource estimate

The estimates remain ranges until E0 measures actual throughput:

| Work | Estimated resource |
|---|---:|
| 100-Mb chr3/chr5 preflight | 20-70 CPU core-hours, 2-8 GPU-hours, 2-5 GB |
| full chr3/5/13/19 materialization and QC | 50-150 CPU core-hours |
| full-chromosome P3 inference/logit export | 10-40 GPU-hours |
| candidate extraction and label projection | 30-100 CPU core-hours |
| deterministic family/consensus/alignment features | 100-600 CPU core-hours, conditional on assets |
| logistic probes, bootstrap and evaluation | 20-90 CPU core-hours |
| full Phase 0 storage | 10-25 GB |

The preflight measures the actual throughput before the full request. Its
result may revise only engineering resources, not chromosomes, labels,
features or gates. A later chr20-22 confirmation is estimated separately at
3-12 GPU-hours, 50-200 CPU core-hours and 3-10 GB.

No large multi-species training, MoE, new U-Net or TE-specific HMM is
authorized.

## Publication interpretation

If Phase 0 and final confirmation pass, the strongest honest framing is:

> From high-recall TE segmentation to calibrated mask continuity: selective
> gap bridging with frozen logits and cross-fragment repeat evidence.

Permitted conclusions:

- high bp recall does not guarantee a continuous comparator-consistent repeat
  mask;
- prediction-defined gap classification is distinct from per-bp
  segmentation;
- specified sequence/logit/alignment evidence improves selective Human mask
  continuity over simple merging on untouched chromosomes;
- the refined softmask has quantified incremental gene-feature risk;
- if library evidence dominates, the method is library-assisted refinement.

Prohibited conclusions:

- recovery of true TE insertions or ancestral boundaries;
- same-family fragments are one biological copy;
- nested parent-child topology reconstruction;
- de novo discovery when a repeat library is used;
- improvement of gene prediction without rerunning a gene predictor;
- mammalian or distant-species generalization before the corresponding legal
  audits;
- that RepeatMasker-style comparator continuity is biological truth.

## Open uncertainties exposed before implementation

- exact assembly identity among genome, comparator and gene annotation;
- the canonical unknown/callable projection on new chromosomes;
- whether consensus/family features derive from the same library that created
  the comparator;
- the number and natural prevalence of strict positive, strict negative and
  unresolved prediction-defined gaps in E0;
- whether the 16,384-bp tail reflects genuine inference dropout, stitching or
  padding; E0 reports it but does not add a special rescue rule;
- whether near-duplicate sequence components can be defined without using
  test labels.

These uncertainties determine whether an arm is interpretable or asset
blocked. They do not justify substituting a different task or silently
relaxing the gate.

## ChatGPT Pro review

ChatGPT Pro independently received the frozen results, the no-expert resource
constraint, the complete gap proposal, the historical FRAGGRAPH negative and
the actual materialized-data/logit audit. The convergence used here is:

- retire Gate L rather than relabel it;
- make comparator-consistent continuity the primary estimand;
- treat SV-like consensus/cluster evidence as a feature arm and deterministic
  baseline, not proof of insertion identity;
- treat the historical FRAGGRAPH result as a negative prior that permits only
  one final P3-based re-entry;
- require a chr17 bit-exact logit-export regression and a chr3/chr5 100-Mb
  two-contig preflight before full-chromosome execution;
- run deterministic arms plus one L2 logistic discriminability probe before
  any neural gap model;
- freeze chr3/5 train, chr13 validation, chr19 route-selection test and
  chr20-22 final reserve;
- keep continual learning closed unless library-free raw sequence adds held-
  out information and later reproduces on the final Human reserve and Mouse;
- reserve Mouse for post-Human transfer and remove Fly from routine execution.

This external review is advisory. Repository evidence and the prospective
gate above determine the route.
