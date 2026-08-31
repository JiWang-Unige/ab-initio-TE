# FBTI-EXTANT-LOCUS-PHASE0-R1: frozen route-selection protocol

Date: 2026-08-31

Status: **protocol frozen; no experiment result yet**

Reviewed repository state: `097c8c8bc9d2c8edae8a76051358e07dd9df8989`

Implementation note: the frozen scientific gate order remains unchanged, but
`FBTI-EXTANT-LOCUS-ANNOTATION-CONTRACT-V1-ADDENDUM-20260831.md` and its V1.1
atom-ownership correction override the V0 sampling, manifest, annotation and
metric clauses where they conflict.

## Technical summary

The current fragment problem cannot be interpreted as a biological-instance
error from the existing metrics. Exact FlyBase evaluation first flattens 5,734
feature records into 4,972 positive truth runs. The reported
`145.744246 fragments/truth` for long truth therefore describes predictions
overlapping a flat-union run, not fragments assigned to one `FBti` biological
instance.

The existing Human supervision and P3 boundary targets also contain no
biological copy identity. They teach TE-associated bases and comparator-run
transitions. Generic/TE-aware MLM, U-Net, boundary losses, HMM/CRF-like
smoothing, thresholding and gap rules changed representations or run geometry
without adding the missing locus-membership observation.

The next scientific object is consequently not a reconstructed historical
insertion. It is an uncertainty-aware **extant TE locus** whose currently
observable TE-derived material may be multipart, nested or boundary-censored.
Historical deletion and ancestral breakpoints remain hypotheses unless an
independent observation, such as an orthologous empty site, supports them.

The only authorized next experiment is the serial, zero-GPU
`FBTI-EXTANT-LOCUS-PHASE0-R1` route-selection study:

1. **L -- label feasibility:** establish that an independent, P3-blind extant
   locus ontology can be annotated reproducibly.
2. **O -- oracle substrate value:** establish that frozen P3 atoms contain a
   substantial, legally fixable locus-splitting burden.
3. **E -- evidence sufficiency:** establish that label-blind sequence and
   structure relations add held-out information beyond geometry alone without
   unacceptable fusion.

All three gates must pass before one frozen-encoder, shallow relation model is
authorized. This panel does not authorize LoRA, full-backbone post-training,
another graph decoder or whole-genome accuracy claims.

## 1. Evidence correction and decision boundary

### 1.1 What the repository directly confirms

- Exact FlyBase r6.68 contains 5,734 curated-positive feature records, but the
  completed evaluator applies `union_runs()` before segment and fragmentation
  scoring, yielding 4,972 flat-union truth runs.
- FlyBase T1 is positive-only. Recall, coverage, known-positive topology and
  unanchored prediction burden are legal; whole-genome precision, F1, FP and
  TN are not.
- Human labels are RepeatMasker-style TE/background/unknown comparator runs.
  They have no biological `copy_id`, parent-child relation or ancestral
  boundary.
- P3 left/right states and P3-R2 targets are derived from comparator-run
  transitions. The matched-permutation result therefore falsifies the tested
  run-boundary mechanism, not all biological TE structure.
- C5 closed near-full-seed retrieval under query coverage `>=0.8`, identity
  `>=0.8` and target span `>=500 bp`. It did not test partial-atom relations,
  comparative empty sites or an extant-locus ontology.
- Rice consensus coordinate alone provided incomplete grouping signal and
  remains closed as a standalone solution.

### 1.2 What is not yet confirmed

- One FlyBase `FBti` record is not yet proven to equal one historical
  insertion event.
- An `FBti` outer interval is not automatically observed parent material, a
  recoverable locus boundary or an ancestral insertion breakpoint.
- The reported high `fragments/truth` has not been decomposed into material
  fragmentation, legitimate biological multipartness and false locus split.
- Single-genome sequence/structure observables have not yet been shown to
  distinguish one interrupted locus from adjacent same-name loci.
- The repository does not contain the materialized genome, checkpoints,
  prediction tracks or full FlyBase provenance packets needed to reproduce
  every reported number from Git alone.

### 1.3 The rejected estimand

The project rejects the claim that one raw extant genome must determine a
unique historical insertion event and exact ancestral outer boundary. The
same observed sequence may be compatible with:

- one insertion later interrupted by deletion or a nested insertion; or
- two adjacent, truncated insertions from the same family.

More model capacity cannot resolve two histories that are observationally
equivalent under the allowed input.

## 2. Separate the four quantities previously called fragmentation

| Quantity | Error? | Primary endpoint |
|---|---|---|
| One continuous observed material segment split into multiple P3 atoms | Yes: material fragmentation | atoms per continuous material segment |
| One extant locus represented by multiple material segments around a child or unknown interruption | No: biological multipartness | material segments per locus |
| Atoms from one extant locus assigned to several locus groups | Yes: false locus split | groups per locus / co-locus recall |
| Atoms from distinct loci assigned to one group | Yes, and safety-critical | cross-locus fusion risk |
| Boundary unidentifiable from available observations | No if the method abstains | boundary identifiability and selective coverage |

The old `fragments/truth` metric remains a historical comparator only. It is
not the headline endpoint of the new task.

## 3. Frozen output ontology

### 3.1 Biological truth layer

Primary entities:

- `observed_material_segment`
- `extant_locus_hypothesis`
- `interruption_region`
- `boundary_interval`

Primary relations:

- `material_of(material_segment, locus)`
- `nested_in(child_locus, parent_locus)`
- `distinct_locus(locus_i, locus_j)`
- `overlap_unresolved(locus_i, locus_j)`

Locus status is epistemic, not a biological edge:

- `resolved`
- `partially_resolved`
- `unresolved`
- `abstained`

Interruption types are restricted to observations:

- `nested_locus_occupied`
- `unknown_sequence`
- `assembly_gap`
- `non_TE_supported`
- `unresolved`

`deletion` is forbidden without comparative or equivalent independent
evidence.

Each locus records `supported_material_union`, left/right boundary intervals,
boundary identifiability and a display-only `locus_envelope`. The envelope is
never converted into parent-positive bases.

### 3.2 Prediction and projection layer

`p3_atom` is not a biological truth entity. Frozen P3 atoms are projected onto
the independent biological layer as:

- `atom_supports_material(atom, material_segment)`
- `atom_assignment(atom, locus) = unique | mixed | unassigned | unresolved`

`same_locus(atom_i, atom_j)` is derived only when both atoms are uniquely
assigned to the same resolved extant locus. Micro-tiles or boundary
perturbations must map back to their canonical parent atom and cannot enlarge
the independent denominator.

## 4. Candidate routes ranked by new information

| Rank | Route | New observable | Minimum falsification | Stop rule |
|---:|---|---|---|---|
| 1 | Extant-locus provenance and manual truth | P3-independent material segments, locus topology, boundary uncertainty and evidence provenance | 12 calibration packages plus a 24-package double-blind pilot | Stop supervised locus modelling if provenance or ontology is not reproducible |
| 2 | Partial-atom relational identifiability | Cross-atom partial homology, orientation/order, third-copy collinearity, terminal/TSD and flank-transition evidence | Low-capacity full-evidence probe versus equal-capacity geometry probe on grouped held-out packages | Stop the single-reference relation route if incremental information or fusion safety fails |
| 3 | Comparative empty-site rescue | Orthologous presence/absence, empty site and conserved breakpoint evidence | Frozen 20-locus unresolved panel | Stop as a main route if reliable placement occurs in <50% or resolves <30% of unresolved cases |

Route 2 differs from closed C5: it scores relations between partial atoms and
does not emit convex-hull bases, fill gaps or require near-full query coverage.

## 5. Frozen experiment design

### 5.1 Scientific question

In an exact FlyBase r6.68 positive-locus panel, can an extant TE-locus ontology
be annotated reproducibly, and do non-geometric raw-sequence relations among
frozen P3 atoms identify co-locus material while preserving nested children,
separating distinct loci and allowing abstention?

### 5.2 Sampling and independence

- **Calibration:** 12 packages used only to train annotators and refine the
  written protocol. They never enter metrics.
- **Main panel:** 120 non-overlapping packages: 60 S0 and 60 S1.
- **Reserve:** 40 packages: 20 S0 and 20 S1, ordered before annotation and used
  only for denominator shortfall.
- **S0 unit:** one `FBti` anchor with no bp overlap with another known `FBti`.
  This means coordinate-isolated, not biologically simple or negative.
- **S1 unit:** one complete connected component of the `FBti` interval-overlap
  graph. Multiple records in a component are never treated as independent
  packages.
- **Package span:** focal S0 interval or complete S1 component plus 10 kb on
  each side, clipped at contig edges. Expanded packages may not overlap.
- **S0 strata:** outer-interval length bin, P3 atom multiplicity, nearest
  `FBti` distance and exact-name frequency.
- **S1 strata:** component size, maximum overlap depth, component span and P3
  atom multiplicity.
- `flybase_name` is an exact string nuisance variable, not a verified family.
- Population-level estimates use known stratum inclusion weights because the
  60/60 panel is challenge-balanced rather than prevalence-representative.

For Gate E, use five outer grouped folds with four-fold grouped calibration
inside each training portion. Overlap components, exact-name strings and
label-blind atom-sequence homology components cannot cross folds. The homology
blocking rule is alignment `>=80%` identity, `>=50%` reciprocal coverage and
`>=100 bp`; it is a split firewall, not an inference feature.

### 5.3 Double-blind annotation

Two independent annotators label all main packages. A third adjudicator
resolves disagreements. If the adjudicator is one of the two annotators, the
output is not described as three-party consensus.

**Pass 1 -- P3-blind biological annotation**

Annotators may see exact r6.68 sequence, raw FlyBase provenance packets,
package records and versioned independent evidence tracks. They cannot see P3
atoms, model probabilities, probe scores or intermediate adjudication.

They label material segments, extant locus hypotheses, typed locus relations,
interruptions, boundary point/interval/unidentifiable status and evidence
codes. The Pass-1 layer is independently completed, adjudicated and versioned
before P3 output is revealed. A label inferred only from a feature later used
by Gate E is excluded from E's primary denominator to prevent label-feature
circularity.

**Pass 2 -- frozen-atom projection**

Projection is rule-derived except for ambiguous cases:

- `unique`: at least 50% of atom length overlaps supported material; at least
  90% of supported overlap belongs to one locus; second locus `<=10%`;
- `mixed`: at least two loci each cover `>=20%` of the atom;
- `unassigned`: total supported-material overlap `<50%`;
- `unresolved`: assignment changes within allowed boundary uncertainty.

Unlabelled sequence in a positive-only package is unknown, not negative.

### 5.4 Frozen atoms and sensitivity controls

The primary substrate is the unchanged canonical P3 interval file, including
all P3 atoms in each package. It is not clipped, merged, filtered, thresholded
or minimum-length-pruned using truth.

Two representation sensitivities are allowed:

- `micro-tiling`: 128-bp tiles; terminal remainder `<64 bp` joins the previous
  tile; results aggregate to canonical atoms;
- `boundary +/-25 bp`: erosion and dilation without merging atoms.

These controls do not create independent samples or candidate pairs.

### 5.5 Baselines and allowed evidence

| ID | Arm | Information |
|---|---|---|
| B0 | `ATOM_SINGLETON` | one canonical atom per locus hypothesis |
| B1 | `DISTANCE_ONLY` | genomic distance/gap |
| B2 | `GEOMETRY_P3` | gap, atom length, P3 mean/max probability and local atom density |
| B3 | `FULL_RELATIONAL_PROBE` | B2 plus frozen sequence/structure observables |
| N0 | within-package label permutation | null control |
| O1 | manual membership oracle | ceiling only, never a method result |

B2 and B3 use equal-capacity L2-regularized logistic probes. B3 may add only
deployment-available observables: reverse-complement-invariant k-mer
similarity, local-alignment identity/coverage, consistent orientation/order
to the same third genomic hit, terminal-repeat compatibility, TSD candidate
compatibility, flank-transition evidence and interruption-region TE evidence.

Inference cannot use `FBti` ID, exact name, truth coordinates, S0/S1 status,
manual material, truth gap, truth-derived candidate pairs or external known TE
libraries.

## 6. Frozen go/no-go gates

All uncertainty calculations, bootstrap and permutation operate at package or
component level, never at atom-pair level.

### Gate L -- label and provenance feasibility

**L-P: provenance integrity**

- assembly, contig, coordinate and feature-ID integrity: `100%`;
- at least `36/40` deeply audited records are interpretable extant-locus
  anchors or explicit uncertain anchors;
- any assembly identity mismatch: immediate `NO-GO`;
- without an independent evidence code, point boundaries exactly copying an
  `FBti` endpoint: `<=20%`.

**L-R: pre-adjudication reproducibility**

| Metric | GO threshold |
|---|---:|
| Median supported-material-union IoU | `>=0.80` |
| Package-bootstrap 95% lower bound of median IoU | `>=0.70` |
| Exact locus-count agreement | `>=0.70` |
| Topology-edge macro-F1 | `>=0.75` |
| Topology macro-F1 95% lower bound | `>=0.65` |
| Boundary-identifiability Gwet AC1 | `>=0.60` |
| Packages needing major topology adjudication | `<=0.35` |
| Resolved + partially resolved package fraction | `>=0.65` |

**L-D: minimum denominator after at most 160 packages**

- `>=30` resolved multipart loci;
- `>=20` adjudicated `nested_in` relations;
- `>=30` local distinct-locus hard-negative pairs;
- `>=50` positive co-locus atom pairs from `>=25` packages;
- `>=15` mixed/unresolved atoms for the abstention audit.

Failure of L-D is `LABEL_DENOMINATOR_INSUFFICIENT`, not evidence that the
ontology is irreproducible or that sequence-only grouping is impossible.

### Gate O -- oracle substrate value

| Metric | GO threshold |
|---|---:|
| Pooled supported-material bp recall of frozen P3 | `>=0.50` |
| Atom-covered resolved-locus fraction | `>=0.60` |
| Uniquely assignable fraction among material-supported atoms | `>=0.70` |
| Oracle-fixable false-split burden | `>=0.25` of atom-covered resolved loci |
| Oracle exact co-locus grouping recall | `>=0.60` |
| Grouping recall delta versus singleton | `>=0.20` absolute |
| Locus-count MAE reduction versus singleton | `>=40%` relative |
| Canonical atom and supported-material retention | `1.000` |
| Child material swallowed into parent | `0` |
| Oracle cross-locus fusion | `0` |

O evaluates only observed, uniquely assignable atoms. It never requires the
oracle to invent missed material or fill interruptions.

### Gate E -- incremental single-genome relation information

For held-out positive prevalence `pi`, report normalized average precision as
`nAP = (AP - pi) / (1 - pi)`. Reject an absolute `AUPRC >=0.70` gate because AP
depends on the candidate universe and prevalence.

**Threshold-free requirements**

| Metric | GO threshold |
|---|---:|
| Prevalence-weighted B3 normalized AP | `>=0.30` |
| AP delta, B3 versus best B1/B2 | `>=0.10` absolute |
| Package-bootstrap 95% lower bound of AP delta | `>0` |
| Brier skill versus B2 | `>=0.05` |
| Weighted ECE | `<=0.10` |
| Calibration slope | `0.5--1.5` |

Inner validation selects separate link and distinct thresholds with abstention
between them. On outer held-out folds:

| Metric | GO threshold |
|---|---:|
| Non-abstained eligible-pair coverage | `>=0.50` |
| Positive co-locus link recall | `>=0.40` |
| Distance-matched distinct-locus FPR | `<=0.10` |
| Exact-name-matched different-locus FPR | `<=0.10` |
| Package-level cross-locus fusion-risk point estimate | `<=0.05` |
| One-sided 90% upper bound of fusion risk | `<=0.15` |
| Parent-child false-link rate | `<=0.05` |
| Parent-across-nested-child bridge recall | `>=0.40` |

Package-level fusion risk means at least one predicted link joining two
adjudicated distinct loci in a package. Phase 0 does not introduce a graph
decoder.

After mapping sensitivities back to canonical atoms:

| Stability metric | GO threshold |
|---|---:|
| Canonical pair-decision Jaccard | `>=0.80` |
| Absolute normalized-AP change | `<=0.05` |
| Absolute package fusion-risk change | `<=0.05` |

## 7. Decision branches and post-training boundary

| Result | Meaning | Authorized next step | Closed step |
|---|---|---|---|
| L-P fail | `FBti` cannot support the required semantics | build an independent locus truth source | relation modelling |
| L-R fail | extant-locus ontology is not reproducible | publish ambiguity/limitation or redesign the object | asking a model to replace absent truth |
| L-D fail | this asset lacks a relation denominator | close relation training on this asset | claiming sequence-only impossibility |
| O fail | P3 atoms are not a useful grouping substrate | material-detector diagnosis or a new independent atom source | more losses/heads on the same atoms |
| E fail | current single-genome observables lack usable relation signal | comparative empty-site or other genuinely new observations | larger encoder, LoRA, graph decoder, new smoothing |
| L/O/E pass | truth, oracle value and incremental signal exist | one frozen encoder plus `<=2M` trainable-parameter shallow calibrated relation head | LoRA, full-backbone post-training, simultaneous atomizer/assembler changes |

Even a complete pass is route-selection evidence, not claim-grade validation.
The next model must keep atoms and labels fixed and use grouped nested
cross-validation. A second-species independent manual panel is required before
any cross-species or general-purpose claim.

## 8. Resource budget and dependencies

| Work | Estimate |
|---|---:|
| Package and provenance construction | `40--80 CPU core-hours` |
| Partial-hit and collinearity features | `200--400 CPU core-hours` |
| Grouped CV, calibration and bootstrap | `20--40 CPU core-hours` |
| Peak RAM | `32--64 GB` |
| GPU | `0 GPU-hours` |
| Annotator protocol training | `12--16 person-hours` |
| Main 120 double annotation | `90--120 person-hours` |
| Adjudication | `25--40 person-hours` |
| Provenance deep audit | `12--20 person-hours` |
| Main-panel total | `140--180 person-hours` |
| All 40 reserve packages, if required | additional `30--40 person-hours` |

Before annotation begins, the exact r6.68 sequence, raw feature provenance,
P3 canonical intervals and evidence-packet generation contract must be frozen.
No GPU allocation or model implementation is part of this phase.

## 9. Publication consequence

### Scientific question

> In a single raw genome, does sequence-internal relational information beyond
> per-base TE-associated probability allow discontinuous observed TE-derived
> material to be organized into uncertainty-aware extant loci while preserving
> nested elements, separating adjacent distinct loci and abstaining when
> boundaries are not identifiable?

### Positive claim boundary

If L/O/E pass, the project may claim on an independently double-annotated,
adjudicated FlyBase-derived positive-locus panel that explicit cross-atom
sequence/structure evidence exceeds geometry-only baselines and recovers a
material fraction of multipart extant loci without filling interruptions or
swallowing nested children. It may not claim ancestral insertion recovery or
whole-genome precision.

### Negative claim boundary

If L and O pass but E fails, the project may claim that the current
single-genome sequence/structure observables do not add reliable extant-locus
identity beyond geometry, or achieve recall only through unacceptable fusion.
That result closes further capacity, loss and decoder escalation on the same
information and motivates only a genuinely new observation such as a
comparative empty site.

## 10. What remains closed

- headline interpretation of flat-union `fragments/truth` as per-FBti
  biological fragmentation;
- generic or masking-only TE-aware MLM as an instance solution;
- another threshold, gap, minimum-length, U-Net, boundary-loss, HMM/CRF or
  local decoder ladder;
- near-full-seed C5 rescue and consensus-coordinate-only grouping;
- simple connected-component assembly;
- MoE, unrestricted full-backbone post-training and LoRA before claim-grade
  independent labels;
- historical deletion or ancestral boundary labels inferred from one extant
  sequence;
- FlyBase positive-only whole-genome precision/F1.
