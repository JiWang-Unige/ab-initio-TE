# First-principles restart: from TE-associated bases to TE instances

Date: 2026-08-31

> **Superseded protocol notice.** The numerical results and closed-route
> evidence in this report remain part of the audit trail, but its biological
> interpretation of FlyBase `fragments/truth` and its Phase 0 A0--A3 protocol
> are not authorized. The FlyBase metric was computed after flat-union into
> 4,972 truth runs, not against 5,734 `FBti` identities. A1/A2 also assumed
> atom-membership and identifiable biological-boundary truth that the current
> assets do not contain. The current frozen decision is
> [`FBTI-EXTANT-LOCUS-PHASE0-R1-20260831.md`](FBTI-EXTANT-LOCUS-PHASE0-R1-20260831.md):
> first validate a P3-blind extant-locus ontology, then test oracle substrate
> value and label-blind relation information.

## Decision

The fragment problem is not currently supported as a semantic-segmentation
problem. The frozen results instead identify a missing latent variable:

> Which observed TE-positive evidence atoms belong to the same biological TE
> insertion?

The direct models predict whether each base is TE-associated. They do not
predict instance identity. Thresholding connected TE-positive bases into
intervals silently assumes that one connected component equals one biological
instance. That assumption was never validated and is contradicted by the
external diagnostics.

The project therefore does not reopen pure direct P3, the frozen C5 whole-seed
retrieval route, or another post-training-plus-smoothing ladder. The next
route is a new, explicitly instance-level task. Its first experiment is a
no-training **FlyBase FBti instance-identifiability audit**. Only if that audit
shows that instance membership is recoverable from label-blind evidence may a
same-instance relation model be trained.

This restart was reviewed in two rounds with ChatGPT Pro. The second round
included the exact FlyBase FBti asset, nested-instance counts, the failed C5
whole-seed contract and the earlier Rice consensus-collinearity negative
result.

## 1. Confirmed, unavoidable facts

### 1.1 Base-pair recognition and instance reconstruction are different tasks

- Human Base/DAPT bp F1 is approximately `0.934`, while segment F1 is only
  `0.339956/0.380724` and boundary F1@5 is `0.199781/0.224286`.
- Mouse transfer retains bp F1 `0.902004` and bp recall `0.952980`, but segment
  F1 falls to `0.096592`, boundary F1@5 to `0.026062`, and fragments/truth
  rises to `2.144423`.
- On exact FlyBase r6.68 positive truth, the frozen P3 model touches `98.8491%`
  of curated instances >=1000 bp (`missed=0.011509`) yet produces
  `145.744246` fragments/truth and only `0.032609` segment recall@0.8.

The model can therefore find TE-associated sequence without reconstructing
the insertion that generated it. Better base-pair classification is not, by
itself, an identified solution to fragmentation.

### 1.2 The current supervision does not contain biological instance identity

The Human comparator-strict target is a binary TE/background/unknown run
layer. It contains no biological `copy_id`, parent insertion, homology
component or nested parent-child relation. Its “truth segments” are continuous
positive runs, not independently validated biological insertions.

Consequently, the current linear and U-Net heads can learn local TE state and
local run edges, but cannot be expected to infer whether two separated
positive runs are surviving parts of one insertion.

### 1.3 Existing post-training and post-processing did not add that missing
information

- Generic Human MLM-DAPT improved some Human endpoints but passed only four of
  six frozen fragment gates.
- TE-enriched span-MLM followed by the same CE head did not solve the frozen
  Human route.
- In P3-R2, aligned boundary supervision was worse than a matched spatial
  permutation control on segment F1 (`0.407518` versus `0.447522`), boundary
  F1@5 (`0.215538` versus `0.250507`) and fragments/truth (`1.185996` versus
  `1.086999`).
- Threshold sweeps, gap merging, minimum-length filtering, local HMM/CRF-like
  smoothing, semi-Markov decoding and frozen refiners reorganized the same
  local evidence and failed their gates.

These results do not prove that TE biology is unlearnable. They show that the
tested objectives did not introduce biological instance-membership evidence.

### 1.4 The frozen C5 experiment tested only near-full-seed retrieval

The closed C5 A1 contract searched whole P3/HiTE seeds with query coverage
`>=0.8`, identity `>=0.8` and target span `>=500 bp`. Only `6/4,820` union
seeds had at least two qualifying copies, and endpoints changed by about
`1e-4`. This falsifies the frozen near-full-seed contract. It does not test
partial conserved modules, family-level evidence or an atom-to-instance
relation model.

### 1.5 Consensus coordinate alone has already failed as a complete solution

The Rice consensus-collinearity audit mapped leaves to frozen consensus
coordinates and recovered high pairwise purity (`0.924138`) but low recall
(`0.184930`) and low exact recovery (`0.138889`). Consensus coordinate can be
one evidence channel, but reopening it as a standalone grouping rule would
repeat a closed route.

### 1.6 A biological instance layer is already available for the first audit

Exact FlyBase r6.68 provides `5,734` independent transposon feature records
with stable `FBti` identifiers. Their length distribution is:

| Length | Instances |
|---|---:|
| <80 bp | 934 |
| 80--499 bp | 2,454 |
| 500--999 bp | 529 |
| >=1000 bp | 1,817 |

There are `812` instances participating in overlaps/nesting, with maximum
overlap depth `5`. This is sufficient for a positive-only instance
identifiability audit without first creating a manual Human panel.

## 2. Habitual but unverified assumptions

The following assumptions must no longer be treated as facts:

1. A connected component of high TE probability is one TE insertion.
2. A biological insertion must appear as one contiguous observed TE interval.
3. Fewer output intervals always means better annotation.
4. RepeatMasker run edges are full-copy biological boundaries.
5. Long instances are “easy” because most of their bases are detected.
6. More context, another decoder, or another continuity loss creates the
   information needed to identify an insertion.
7. Whole-seed homology is the only useful multi-copy evidence.
8. A consensus coordinate is sufficient to group all surviving parts of a
   divergent or nested insertion.
9. A single exact boundary is identifiable when terminal sequence has been
   deleted or overwritten.
10. Training and evaluating only semantic segments can demonstrate intact-copy
    annotation.

Several assumptions may be true for restricted TE classes, but they require
class- and evidence-specific tests rather than being built into the evaluator.

## 3. The actual target

The publication-relevant target is not merely a smoother binary mask. It is a
hierarchical TE annotation:

1. **TE-associated base probability:** which bases carry TE evidence.
2. **Evidence atoms:** locally coherent predicted intervals or structural
   modules.
3. **Logical TE instance:** a multipart set of atoms inferred to originate
   from one insertion.
4. **Instance geometry:** outer span, strand, terminal-boundary uncertainty,
   completeness and nested children.
5. **Family/subfamily identity:** when evidence supports it.

For a nested or deleted insertion, `outer_span` and `supported_atoms` must be
stored separately. The convex hull of the atoms must not be relabelled as
parent TE-positive bases, because it can contain host sequence or a nested TE.
An unresolved remnant is a legitimate output when instance identity or exact
terminals are not identifiable.

## 4. Real resources and constraints

### Available

- Frozen P3 predictions and the exact FlyBase r6.68 positive-instance table.
- `5,734` stable FBti truth instances, including a non-trivial nested subset.
- Human, Mouse and FlyBase frozen diagnostics.
- Frozen embeddings/backbone, but they should be used only after a deterministic
  evidence substrate is demonstrated.
- Target-genome sequence, consensus-coordinate mappings, and tools for local
  homology, terminal/TSD and flank-transition evidence.

### Constraints

- FlyBase T1 is positive-only. Whole-genome precision/F1, false-positive rate
  and true negatives are forbidden.
- Human comparator runs are not biological copy truth.
- Nested insertions make naive interval convexification invalid.
- Some deleted copies have non-identifiable original terminals; uncertainty is
  part of the scientific target.
- The frozen C5 whole-seed search and Rice consensus-only grouping remain
  closed.
- No complex MoE, large multi-species training, TE-specific HMM or new neural
  decoder is justified before the no-training gate below.

## 5. Parts of the old route that only patched the surface

| Surface intervention | What it changes | Why it cannot identify an instance |
|---|---|---|
| Threshold and calibration sweeps | Number and width of local positive runs | No relation between separated runs is observed |
| Gap merging / minimum length | Connected-component geometry | Encodes distance as identity and can swallow nested/host sequence |
| HMM/CRF/semi-Markov smoothing | Local transition prior | Reorders local states without copy membership evidence |
| Boundary loss / four-state head | Local edge prediction | Comparator-run edges are not biological parent-copy labels |
| Larger context / U-Net | Receptive field and multiscale features | Attention to two atoms is not supervision that they share an insertion |
| Generic or TE-aware MLM | Sequence representation | MLM does not supply a copy identity or parent relation |
| Frozen whole-seed C5 search | Near-full-copy homology | Too strict for partial, deleted and nested copies under the tested contract |
| Consensus-coordinate-only grouping | One family-coordinate feature | High precision but insufficient recall in the completed Rice audit |

Post-training is not excluded in principle. It is demoted from “solution” to a
conditional representation component: it is useful only if it improves an
explicit instance-relation task after that task is shown to be identifiable.

## 6. New path derived from facts, target and constraints

### Phase 0: FlyBase FBti instance-identifiability audit (no training)

Freeze the existing P3-R1 threshold and predictions. Treat predicted
intervals as evidence atoms. Run four arms on the same positive denominator:

| Arm | Information allowed | Question |
|---|---|---|
| A0 | Raw P3 atoms | What detection and fragmentation substrate exists? |
| A1 | Truth FBti membership for linking only | If atom-to-instance identity were known, how much fragmentation is removable without filling gaps? |
| A2 | Truth outer boundary on detected instances | Is remaining error primarily boundary/detection rather than linking? This is an oracle ceiling, not a method result. |
| A3 | Label-blind deterministic evidence | Can partial/module homology, orientation/order, consensus coordinate, terminal/TSD and flank transition recover same-instance relations? |

A3 must include distance-only and consensus-coordinate-only ablations. It must
not use FBti, truth boundary or truth genomic gap during inference. Whole-seed
C5 is not an A3 arm; A3 searches relations between partial atoms/modules.

### Legal positive-only endpoints

- truth-instance touched/recall and truth-bp coverage;
- per-instance covered fraction and missed rate;
- atoms/fragments per truth, split rate and length strata;
- boundary recall@5/25 and median boundary error on known positives;
- relation precision/recall/F1/AUPRC only for candidate atom pairs whose atoms
  map to known-positive FBti instances;
- connected-component exact recovery, false fusion between known distinct
  positives and false split within one FBti;
- nested topology recovery, parent-child separability and depth-stratified
  recall.

Score membership, outer-boundary error and supported-bp coverage separately.
For nested instances, also report a parent observable mask with known child
intervals subtracted. Never score the convex hull as recovered parent bases.

### Frozen go/no-go proposal

| Gate | Requirement | Decision changed by failure |
|---|---|---|
| Detection substrate | >=60% of all FBti and >=75% of >=500-bp FBti touched | Stop instance assembly; improve candidate detection under independent truth |
| Relation substrate | >=25% of detected instances have >=2 atoms and >=500 multi-atom instances exist | Stop relation modelling; insufficient pairwise denominator |
| Oracle link ceiling | On multi-atom truth, fragments/truth and split rate each fall >=50% without convex-hull filling | If not, fragmentation is not mainly an identity/linking problem |
| Oracle boundary ceiling | Detected-instance segment recall@0.8 >=0.60 and boundary recall@25 >=0.80 | If not, detection/boundary observability is the dominant limit |
| Label-blind evidence | Pair AUPRC >=0.70, >=0.15 above consensus-only, known-positive cross-FBti fusion <=10%, nested-pair recall >=0.40 | Do not train Phase 1; deterministic evidence has not established an identifiable signal |

The numerical gates are prospective route-selection thresholds, not results.
They must be frozen before Phase 0 output is inspected.

### Phase 1: conditional same-instance relation model

Only after all Phase 0 route gates pass, train the unique missing variable:

`P(same TE instance | atom_i, atom_j, sequence and structural evidence)`

The initial model should be pairwise relation prediction followed by
graph/hierarchical assembly. Features may include frozen genome-LM embeddings,
partial-module homology clusters, relative orientation/order, reliable
consensus coordinate, terminal/TSD support and flank compatibility.

If contrastive post-training is used, its ontology must be instance-aware:

- positives: atoms from the same biological instance;
- hard negatives: same family but different instances;
- negatives: different families;
- split by family/homology component, not random atom pairs.

The encoder may then be fine-tuned as part of relation learning. A boundary
scorer is downstream, because a boundary is defined for an assembled object.
It should not be the first new neural target.

Before claiming mammalian generalization, construct an independent Human
manual instance panel. If Drosophila is used for training, the old
species-holdout claim is retired and the experiment is described as a new
instance-assembly task.

## 7. Premises for the new path

The route is viable only if:

1. P3 atoms overlap enough independent FBti instances to form a relation
   denominator.
2. A substantial fraction of the observed fragment count is false splitting
   of one instance, rather than multiple true nested/adjacent insertions.
3. Same-instance atom pairs contain label-blind signal beyond genomic distance
   and consensus coordinate alone.
4. Stable FBti identifiers approximate biological insertion identity closely
   enough for a positive-only pilot.
5. The nested evaluator keeps membership, supported bases and parent outer span
   separate.
6. The final claim is restricted when terminals are not identifiable.

The largest current uncertainty is item 3. That is exactly what Phase 0 A3 is
designed to decide.

## 8. First validation step

Implement and run only Phase 0 A0--A3 on the existing exact FlyBase assets.
This is a CPU/no-training engineering pilot and a scientific route-selection
audit. It requires no new model, no new genome download and no manual
annotation before its gates are known.

The first output must be one same-denominator table containing:

1. FBti detection substrate by length and overlap depth;
2. the A1 oracle-link ceiling without convex-hull filling;
3. the A2 oracle-boundary ceiling;
4. A3 pairwise and component-level results with distance-only and
   consensus-only ablations;
5. an explicit PASS/FAIL for every frozen gate.

If Phase 0 fails, the project should not add another post-training objective.
It should either improve independent instance truth/candidate detection or
close the intact-instance objective and publish the failure-chain diagnosis.
If Phase 0 passes, the next and only neural experiment is the Phase 1
same-instance relation model, followed by a Human manual-panel confirmation.

## 9. Publication consequence

A positive route would support a coherent paper:

1. High bp recovery is empirically insufficient for TE instance annotation.
2. Independent FBti truth decomposes error into detection, linking, boundary
   and nested-topology ceilings.
3. Distance and consensus-coordinate-only rules are insufficient.
4. Module/structure/locus evidence makes instance identity measurable.
5. An explicit relation model improves instance recovery rather than merely
   smoothing a semantic mask.

A negative Phase 0 is also decisive: it would show that the current candidate
representation lacks enough observable information for intact-instance
reconstruction. It would prevent another costly but non-identifying cycle of
post-training, loss changes and post-processing.

## Source and claim boundary

- HiTE combines target-genome copy evidence, structural signals and boundary
  refinement; it is not a simple local semantic segmenter:
  <https://www.nature.com/articles/s41467-024-49912-8>.
- RepeatMasker reports library/model matches and fragments; its runs should not
  be silently equated with independently curated biological insertions:
  <https://www.repeatmasker.org/dev/faq.html>.
- FlyBase bulk data supplies the canonical transposon-insertion feature layer
  used for the FBti audit: <https://flybase.org/downloads/bulkdata>.

These sources motivate the ontology and evidence channels. The numerical
route decision above is based on this project's frozen results and exact local
assets, not on literature claims.
