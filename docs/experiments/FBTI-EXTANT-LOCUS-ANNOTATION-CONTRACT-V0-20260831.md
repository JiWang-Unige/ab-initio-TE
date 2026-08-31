# FBTI extant-locus annotation contract V0

Date: 2026-08-31

Status: **implementation-blocking contract proposal; not yet a frozen result**

Parent protocol:
`docs/experiments/FBTI-EXTANT-LOCUS-PHASE0-R1-20260831.md`

This document resolves the data-contract and metric ambiguities that currently
prevent an implementation of Gate L. It does not calculate a result and does
not authorize Gate O, Gate E or GPU work. The choices below are deliberately
minimal: every stored field is consumed by a frozen Gate L quantity or is a
primary biological annotation or circularity flag required by the parent
protocol.

The existing code supports the coordinate recommendation. In particular,
`repeatmasker_flybase_alignment.py`, `human_d1_canonical.py` and the LEMMI
canonical adapters use zero-based, half-open genomic intervals. No inspected
code or report contradicts that convention. No existing repository artifact
defines the remaining Gate L formulas, so those choices must be accepted and
versioned before a calculator is written.

## 1. Units, panels and coordinate convention

### Choice

- Every genomic interval is on the exact FlyBase r6.68 assembly and is stored
  as zero-based, half-open `[start, end)`, with `0 <= start < end <= contig_len`.
- A boundary is an interbase coordinate. Its allowed position set is stored as
  closed integer bounds `lower_pos <= upper_pos`; a point has
  `lower_pos == upper_pos`, an interval has `lower_pos < upper_pos`, and an
  unidentifiable boundary has both fields empty. This avoids pretending that a
  zero-width breakpoint is a genomic material interval.
- `package_id` is the analysis and bootstrap key. An S1 overlap component is
  one package regardless of its number of FlyBase records.
- Calibration packages are never scored. Gate L-P and L-R use the fixed 120
  main packages. Gate L-D uses the main packages plus only the activated
  reserve prefix described in Section 11.
- The first 24 main packages may be used as a workflow pilot. They remain in
  the main denominator only if the contract and annotation instructions do not
  change; otherwise they must be re-annotated under the frozen version.

### Why this matches the parent protocol

The parent protocol already fixes exact r6.68, package-level uncertainty,
60 S0 plus 60 S1 main packages, 40 reserve packages and component-level
resampling. Existing canonical project code establishes zero-based half-open
intervals.

### Failure and decision consequence

An assembly mismatch is an immediate Gate L-P `NO-GO`. Invalid coordinates,
duplicate package keys, overlapping expanded packages or incomplete main
annotation are input-contract failures: no scientific Gate L status is emitted
until the input is corrected.

## 2. Frozen package manifest

### Choice

`packages.tsv` contains exactly one row per package and these columns:

| Column | Contract |
|---|---|
| `package_id` | unique stable key |
| `panel` | `calibration`, `main`, or `reserve` |
| `panel_rank` | unique positive integer within panel |
| `reserve_pair_rank` | empty outside reserve; `1..20`, once for S0 and once for S1 |
| `stratum` | `S0` or `S1` |
| `assembly_id` | exact frozen r6.68 assembly identifier |
| `seqid` | exact frozen r6.68 contig identifier |
| `package_start`, `package_end` | expanded package interval |
| `focal_start`, `focal_end` | S0 anchor or full S1 component envelope |
| `overlap_component_id` | empty for S0; stable component key for S1 |
| `anchor_feature_ids` | comma-separated, lexicographically sorted exact FlyBase IDs |
| `sampling_stratum_id` | frozen combined sampling-stratum key |
| `inclusion_probability` | sampling inclusion probability for later population estimates |
| `deep_audit_feature_id` | exact feature ID for the 40-record audit, otherwise empty |

The 40 non-empty `deep_audit_feature_id` values are frozen before annotation:
20 distinct records from S0 main packages and 20 distinct records from S1 main
packages. They may not be selected after seeing annotation difficulty.

### Why this matches the parent protocol

The fields materialize only the sampling, non-overlap, provenance and weighting
rules already frozen in Sections 5.2 and 6 of the parent protocol.

### Failure and decision consequence

Wrong 60/60 or 20/20 counts, a non-prefix reserve activation, duplicate audit
records, an S1 package that omits part of its connected component, or expanded
package overlap makes the input invalid. A verified source/manifest identity
mismatch is instead a Gate L-P `NO-GO` because it falsifies provenance
integrity.

## 3. Provenance and evidence registry

### Choice

`provenance_audit.tsv` has one row for every anchor feature in every activated
package:

| Column | Contract |
|---|---|
| `package_id`, `feature_id` | compound unique key |
| `manifest_assembly_id`, `source_assembly_id` | expected and raw-packet assembly IDs |
| `manifest_seqid`, `source_seqid` | expected and raw-packet contigs |
| `manifest_start`, `manifest_end` | expected canonical interval |
| `source_start`, `source_end` | raw feature interval after one documented conversion to canonical coordinates |
| `source_feature_id` | raw-packet exact feature ID |
| `evidence_packet_id` | immutable versioned packet key |
| `deep_audit` | `0` or `1`; must agree with the manifest |
| `anchor_interpretability` | empty for basic audit; for deep audit only: `interpretable_extant_locus`, `explicit_uncertain`, or `uninterpretable` |
| `audit_note` | required only for `explicit_uncertain` or `uninterpretable` |

The calculator recomputes assembly, contig, coordinate and feature-ID equality
from the paired raw values; it does not trust redundant pass booleans.

`evidence_registry.tsv` contains:

`evidence_code`, `evidence_class`, `source_version`,
`independent_of_fbti_endpoint`, `used_by_gate_e`.

Every evidence code used in an annotation must occur in this registry. Only a
code with `independent_of_fbti_endpoint=1` can rescue an exact copied endpoint
for the L-P boundary-copy diagnostic. A FlyBase endpoint or a transformation
of that endpoint is never independent evidence. `used_by_gate_e` preserves the
parent protocol's later circularity exclusion: a primary Gate E label inferred
only from evidence later exposed as a Gate E feature must be excluded from that
primary denominator.

### Why this matches the parent protocol

This directly instantiates the four 100% integrity checks, the balanced
40-record deep audit, explicit uncertain anchors, versioned evidence tracks and
the prohibition on treating a copied FBti endpoint as independent evidence.

### Failure and decision consequence

- Any assembly mismatch is an immediate Gate L-P `NO-GO`.
- Any contig, normalized coordinate or feature-ID mismatch makes the relevant
  100% L-P check fail and therefore gives `NO-GO`.
- Fewer than 36 of the fixed 40 deep records classified as either
  `interpretable_extant_locus` or `explicit_uncertain` gives Gate L-P `NO-GO`.
- An unknown evidence code is an invalid input, not biological evidence.

## 4. Annotation bundle and keys

### Choice

Each Pass-1 actor (`A1`, `A2`, `ADJ`) supplies the following normalized TSVs.
The compound key always begins with `package_id,actor_id`; `actor_id` must equal
the bundle owner. Actor-local IDs need only be unique within one package.

### `package_reviews.tsv`

| Column | Contract |
|---|---|
| `package_id`, `actor_id` | one row per scored package and actor |
| `package_status` | `resolved`, `partially_resolved`, `unresolved`, or `abstained` |
| `topology_resolution` | A1/A2: empty; ADJ: `accept_a1`, `accept_a2`, `same_topology_minor_edit`, or `new_topology` |
| `topology_reason` | required for ADJ `new_topology`, otherwise optional |

### `loci.tsv`

`package_id`, `actor_id`, `locus_id`, `locus_status`,
`locus_envelope_start`, `locus_envelope_end`, where locus status uses the same
four-value status vocabulary. The envelope contains all supported material for
display only and never creates parent-positive bases. Every locus must have at
least one `material_segments.tsv` row; an annotator who cannot support any
material uses the package status `unresolved` or `abstained` rather than an
empty locus shell.

### `material_segments.tsv`

`package_id`, `actor_id`, `segment_id`, `locus_id`, `seqid`, `start`, `end`,
`evidence_codes`.

Each row is the ontology edge
`material_of(observed_material_segment, extant_locus_hypothesis)`; storing the
same edge again in `relations.tsv` is forbidden. Material segments assigned to
the same locus may not overlap or touch: touching segments are one continuous
observed material segment and must be merged by the annotator before lock.

### `boundaries.tsv`

`package_id`, `actor_id`, `locus_id`, `side`, `identifiability`, `lower_pos`,
`upper_pos`, `evidence_codes`.

`side` is `left` or `right`; `identifiability` is `point`, `interval`, or
`unidentifiable`. Each locus has exactly one row per side. Evidence codes are
comma-separated and sorted; empty means no independent evidence.

### `interruptions.tsv`

`package_id`, `actor_id`, `interruption_id`, `locus_id`, `seqid`, `start`,
`end`, `interruption_type`, `evidence_codes`.

The type is exactly one of `nested_locus_occupied`, `unknown_sequence`,
`assembly_gap`, `non_TE_supported`, or `unresolved`. `deletion` is not an
allowed value.

### `relations.tsv`

`package_id`, `actor_id`, `relation_id`, `relation_type`, `subject_locus_id`,
`object_locus_id`, `evidence_codes`.

The only values are `nested_in`, `distinct_locus`, and `overlap_unresolved`.
`nested_in` is directed: child is subject and parent is object.
`distinct_locus` and `overlap_unresolved` are symmetric and stored once with
lexicographically ordered locus IDs. Self-edges and duplicate typed edges are
forbidden.

After the adjudicated Pass-1 bundle is locked and P3 is revealed,
`atom_projection.tsv` contains one row per canonical atom in every scored
package:

`package_id`, `atom_id`, `seqid`, `start`, `end`, `assignment`,
`assigned_locus_id`, `assigned_segment_ids`.

`assignment` is `unique`, `mixed`, `unassigned`, or `unresolved` under the
parent protocol's exact overlap rules. `assigned_locus_id` is present only for
`unique`. Coordinates and IDs must match the immutable canonical atom file;
micro-tiles never appear in this table.

### Why this matches the parent protocol

The bundle is a direct normalized encoding of the frozen ontology and the
P3-blind/Pass-2 separation. It does not add a family label, ancestral boundary,
deletion label or P3-derived biological truth.

### Failure and decision consequence

Missing foreign keys, an illegal relation/type/status, a Pass-1 P3 atom, or a
non-canonical atom makes the input invalid. Such a failure is corrected before
Gate L; it must not be silently converted to `unresolved` or included in a
scientific denominator.

## 5. Supported-material-union IoU

### Choice

For each main package and annotator, union all intervals in that actor's
`material_segments.tsv`, without using locus IDs. The package IoU is

`bp(intersection(A1_union, A2_union)) / bp(union(A1_union, A2_union))`.

If exactly one union is empty, IoU is `0`. If both are empty, IoU is also `0`:
agreement to provide no observable material in a curated-positive package is
not evidence of reproducible material annotation. Gate L-R uses the median of
the 120 package IoUs.

### Why this matches the parent protocol

The parent names “supported-material-union IoU,” not locus-matched IoU. The
package union measures reproducibility of the observable material layer before
testing locus identity and avoids making the material score depend on a later
locus-matching heuristic.

### Failure and decision consequence

A median below `0.80` or the bootstrap lower bound below `0.70` fails Gate L-R
and gives final `NO-GO`, even if both annotators agree on locus count.

## 6. Locus correspondence and exact locus-count agreement

### Choice

Exact locus-count agreement is the fraction of main packages for which the
number of declared rows in A1 `loci.tsv` equals the number in A2 `loci.tsv`.
All declared statuses count. Two abstentions with zero loci agree on count but
cannot satisfy the separate resolved-fraction gate.

For metrics that require cross-annotator locus correspondence, construct the
supported-material union of every locus and perform a maximum-total-IoU
one-to-one bipartite matching within each package. Candidate pairs with zero
bp intersection are absent. Ties are resolved lexicographically by actor-local
locus IDs. Unmatched loci remain unmatched; no FBti ID, exact name, boundary or
P3 atom is used in matching.

Within each matched locus pair, material segments are matched by the same
maximum-total-IoU rule with zero-overlap pairs absent.

### Why this matches the parent protocol

Independent annotators cannot share inferred locus IDs. Material overlap is the
only already-authorized common observable that does not import P3 or a FlyBase
identity assumption. A one-to-one assignment exposes rather than repairs
split/merge disagreements, and exact locus-count agreement remains independent
of the correspondence rule.

### Failure and decision consequence

Exact locus-count agreement below `0.70` fails Gate L-R. Unmatched loci and
segments reduce topology agreement; they are never dropped. An implementation
that uses FBti IDs, exact names or P3 to align annotator loci violates the blind
contract and produces no Gate L result.

## 7. Topology-edge macro-F1

### Choice

The evaluated edge types are exactly the four frozen ontology relations:

1. `material_of` from each material-segment row;
2. `nested_in`;
3. `distinct_locus`;
4. `overlap_unresolved`.

After the correspondence in Section 6, a material edge matches only when both
its segment and locus match. A locus-locus edge matches only when its typed
endpoints match; endpoint order matters for `nested_in` and does not matter for
the two symmetric types. Unmatched A1 and A2 edges are false-positive and
false-negative contributions respectively. Because the comparison is between
two annotators, swapping their names leaves F1 unchanged.

Pool TP, FP and FN over the 120 main packages separately for each type, compute
`F1_t = 2 TP_t / (2 TP_t + FP_t + FN_t)`, and macro-average types having at
least one edge in either annotation. Types absent from both annotations are
excluded rather than scored as perfect. If all four types are absent, macro-F1
is `0`.

### Why this matches the parent protocol

This uses only the typed relations in the frozen ontology and gives rare
topology types equal weight instead of allowing numerous `material_of` rows to
hide disagreement about nesting or distinct loci.

### Failure and decision consequence

Point macro-F1 below `0.75` or its package-bootstrap lower bound below `0.65`
fails Gate L-R and gives final `NO-GO`. A denominator containing only
`material_of` may still be numerically evaluated, but Gate L-D will expose the
absence of nested and distinct-locus supervision.

## 8. Boundary-identifiability Gwet AC1

### Choice

Use unweighted, nominal, multi-category Gwet AC1 over the fixed categories
`point`, `interval`, and `unidentifiable`. The rated units are left and right
boundary rows of every matched locus pair from Section 6, pooled over the main
panel. Unmatched loci are handled by count/topology metrics and are not assigned
an artificial fourth boundary category.

For `N` paired ratings and category marginal proportions
`p_k = (n_A1,k + n_A2,k) / (2N)`:

- observed agreement `P_a` is the fraction of exact category agreements;
- chance agreement `P_e = sum_k p_k (1 - p_k) / (3 - 1)`;
- `AC1 = (P_a - P_e) / (1 - P_e)`.

If `N=0` or the denominator is zero, AC1 is unevaluable and Gate L-R cannot
pass. Boundary coordinates themselves are not used in AC1; this gate measures
whether the observation supports a point, an interval or abstention.

### Why this matches the parent protocol

The parent explicitly freezes the three identifiability states and asks for
Gwet AC1, not a distance-weighted boundary score. Nominal AC1 avoids inventing
an ordinal biological distance between `point`, `interval` and
`unidentifiable`. No inspected project code defines or contradicts this choice.

### Failure and decision consequence

AC1 below `0.60` or unevaluable AC1 fails Gate L-R and gives final `NO-GO`.

## 9. Boundary-copy diagnostic and major adjudication

### Choice

For every adjudicated **main-panel** boundary with
`identifiability=point`, compare its interbase position with both endpoints of
every anchor feature in the same package. The numerator is the number that
exactly copy at least one anchor endpoint and have no referenced evidence code
marked `independent_of_fbti_endpoint=1`. The denominator is all adjudicated
main-panel point boundaries. With no point boundaries, the rate is `0`, while
the reported denominator remains explicit.

An adjudicated package needs **major topology adjudication** exactly when
`topology_resolution=new_topology`. This value means the adjudicated locus
partition and typed relation graph is not accepted unchanged from either A1 or
A2. Choosing either complete actor topology, or changing only material/boundary
coordinates while retaining a topology shared by both, is not major. A reason
is mandatory for every `new_topology` row.

The resolved fraction is computed from the adjudicated, top-level
`package_status`: number of main packages marked `resolved` or
`partially_resolved`, divided by 120. It is not “at least one resolved locus.”

### Why this matches the parent protocol

The diagnostic directly tests whether apparent point precision is copied from
FBti rather than independently supported. The explicit adjudication field
avoids reconstructing a human decision from coordinate edits. Package status
matches the parent phrase “resolved + partially resolved package fraction.”

### Failure and decision consequence

- An unsupported copied-point fraction above `0.20` fails Gate L-P and gives
  `NO-GO`.
- A major-topology-adjudication fraction above `0.35` fails Gate L-R.
- A resolved plus partially resolved package fraction below `0.65` fails
  Gate L-R.

## 10. Gate L-D denominators

### Choice

L-D uses adjudicated Pass 1 plus the rule-derived canonical Pass-2 projection.
Counts are unique by the keys below:

- **Resolved multipart loci:** unique `(package_id,locus_id)` with
  `locus_status=resolved` and at least two non-touching material segments. At
  least one positive-length interval must separate consecutive segments.
- **Nested relations:** unique directed `(package_id,child_locus,parent_locus)`
  in adjudicated `nested_in` rows.
- **Local distinct-locus hard-negative pairs:** unique unordered adjudicated
  `distinct_locus` pair in one package, with at least one canonical atom
  uniquely assigned to each locus. “Local” means package-local; no additional
  genomic distance cutoff is added after challenge-balanced package sampling.
- **Positive co-locus atom pairs:** unique unordered pair of distinct canonical
  atoms uniquely assigned to the same adjudicated resolved locus. Count pairs
  once and separately count packages contributing at least one pair.
- **Mixed/unresolved atoms:** unique canonical atoms whose assignment is
  `mixed` or `unresolved`.

Micro-tiles and boundary perturbations map to canonical atoms and cannot enter
any L-D count. A canonical atom or relation occurring in multiple reserve
tranches is still counted once by its compound key.

### Why this matches the parent protocol

These are direct executable definitions of the five L-D quantities. Requiring
an atom on each distinct locus makes the hard negative usable by the later
relation experiment rather than inflating the denominator with unobservable
locus pairs.

### Failure and decision consequence

After all 160 packages, any of the following produces
`LABEL_DENOMINATOR_INSUFFICIENT` provided L-P and L-R passed: fewer than 30
resolved multipart loci, 20 nested relations, 30 hard-negative locus pairs, 50
positive atom pairs, 25 pair-contributing packages, or 15 mixed/unresolved
atoms. It does not support a claim that the ontology or sequence-only relation
route is impossible.

## 11. Reserve activation

### Choice

Evaluate L-D after the 120 main packages. If it fails, activate reserve in the
pre-frozen paired order: for rank `r`, add both the S0 and S1 package with
`reserve_pair_rank=r`, complete both independent annotations, adjudication,
provenance and projection, then recompute L-D. Stop only when all L-D minima
pass or after rank 20 (160 total packages). Reserve data never changes the
fixed L-R estimates, the 40-record deep audit or the main-panel boundary-copy
rate. Any basic provenance mismatch in an activated reserve package still
fails L-P.

### Why this matches the parent protocol

The parent permits at most 160 packages and pre-freezes 20 S0 plus 20 S1
reserve packages only for denominator shortfall. Paired prefix activation
prevents choosing reserve packages after seeing which biological relation is
missing.

### Failure and decision consequence

L-D failure before all 20 reserve ranks are complete is `INCOMPLETE`, not a
final gate status. L-D failure after rank 20 becomes
`LABEL_DENOMINATOR_INSUFFICIENT`. A provenance failure in any activated reserve
package takes precedence and produces `NO-GO`.

## 12. Bootstrap and point-estimate freeze

### Choice

Use `10,000` bootstrap replicates with integer seed `20260831`. Resample the
120 main packages with replacement **within S0 and S1 separately**, drawing 60
from each stratum per replicate. S1 connected components remain indivisible
packages. Recompute the median union IoU and the complete topology matching and
macro-F1 inside every replicate; never resample atom pairs or average
package-level topology F1 values.

The 95% lower bound is the non-interpolated empirical lower order statistic:
sort the 10,000 replicate estimates and take the 250th value in one-based
indexing. The ordinary sample median is the mean of the two central ordered
values for an even sample size. These choices apply identically to all
implementations.

### Why this matches the parent protocol

The resampling unit and lower-bound targets are frozen by the parent. S0/S1
stratification preserves the registered 60/60 challenge-balanced design, and
pooled recomputation prevents prolific packages from being treated as
independent pairs.

### Failure and decision consequence

A lower bound below `0.70` for median IoU or below `0.65` for topology
macro-F1 fails Gate L-R. A different seed, replicate count, resampling unit or
quantile rule is a different analysis and cannot be substituted after seeing
the gate.

## 13. Final status and precedence

### Choice

Input validation runs before scientific gate evaluation. A malformed or
incomplete input returns `CONTRACT_INVALID` with a non-zero process exit and no
Gate L result; it is never silently relabelled as scientific failure.

For a complete valid input, final status precedence is:

1. If any L-P check fails, including any activated-reserve provenance check,
   return `NO-GO`.
2. Otherwise, if any L-R check on the fixed main panel fails, return `NO-GO`.
3. Otherwise, if all L-D minima pass, return `PASS`.
4. Otherwise, if fewer than all 20 reserve pairs have been completed, return
   `INCOMPLETE` and identify the next frozen pair.
5. Otherwise return `LABEL_DENOMINATOR_INSUFFICIENT`.

Every output reports every submetric, numerator, denominator and threshold,
even when an earlier condition determines the final status. Calibration
packages are never included.

### Why this matches the parent protocol

The parent assigns biological meaning to L-P/L-R failure and a different,
strictly narrower meaning to L-D shortfall. The precedence prevents inadequate
denominators from hiding an ontology/provenance failure and prevents an input
error from entering the scientific denominator.

### Failure and decision consequence

- `NO-GO` closes relation modelling on this truth asset and invokes the
  corresponding L-P or L-R branch in the parent decision table.
- `LABEL_DENOMINATOR_INSUFFICIENT` closes relation training on this asset but
  does not claim sequence-only impossibility.
- `PASS` authorizes Gate O, not Gate E or model training.
- `INCOMPLETE` authorizes only the next frozen reserve pair.

## 14. Exact Gate L checklist produced by a future calculator

The future implementation must emit these checks and no alternate Gate L
surrogates:

| Check | Threshold / rule | Denominator |
|---|---:|---|
| assembly integrity | 100%; any mismatch immediate failure | all activated anchor records |
| contig integrity | 100% | all activated anchor records |
| coordinate integrity | 100% | all activated anchor records |
| feature-ID integrity | 100% | all activated anchor records |
| interpretable or explicit uncertain anchors | at least 36/40 | frozen deep audit |
| unsupported exact copied point boundaries | at most 0.20 | adjudicated main point boundaries |
| median supported-material-union IoU | at least 0.80 | 120 main packages |
| bootstrap lower bound of median IoU | at least 0.70 | stratified package bootstrap |
| exact locus-count agreement | at least 0.70 | 120 main packages |
| topology-edge macro-F1 | at least 0.75 | pooled typed edges, main panel |
| bootstrap lower bound of topology macro-F1 | at least 0.65 | stratified package bootstrap |
| boundary-identifiability nominal AC1 | at least 0.60 | matched main locus sides |
| major topology adjudication | at most 0.35 | 120 adjudicated main packages |
| resolved plus partially resolved | at least 0.65 | 120 adjudicated main packages |
| resolved multipart loci | at least 30 | main plus activated reserve |
| nested relations | at least 20 | main plus activated reserve |
| hard-negative locus pairs | at least 30 | main plus activated reserve |
| positive co-locus canonical atom pairs | at least 50 | main plus activated reserve |
| packages contributing positive pairs | at least 25 | main plus activated reserve |
| mixed/unresolved canonical atoms | at least 15 | main plus activated reserve |

Acceptance of this V0 contract must occur before annotation templates or a
calculator are treated as frozen. If any definition is changed after an
annotator sees P3 atoms or after Gate L metrics are computed, the version must
change and affected annotations must be regenerated or explicitly excluded.
