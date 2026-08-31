# FBTI Gate L machine closure and fastest publication route

Date: 2026-09-01

Status: **machine path ready; human Gate L not evaluated; no scientific PASS**

## Outcome

The fastest defensible route is now operationally closed on the machine side:

```text
V1.4 lock
  -> A1/A2 calibration
  -> A1/A2 main annotation + P3-blind ADJ provenance audit in parallel
  -> sealed A1/A2 bundles
  -> third-person adjudication
  -> automatic Gate L
  -> Gate O only after L PASS
  -> Gate E only after O PASS
  -> at most one restricted relation model only after E PASS
```

No additional post-training, decoder, smoothing or gap-filling run is the
current critical path. The missing observation is biological locus identity,
not another representation of the existing binary mask. Two independent
human annotators and one fixed provenance auditor/adjudicator are therefore
the only remaining prerequisite for Gate L.

## Why this route is necessary

Four observations survive all completed audits:

1. P3 retains high TE-material recovery but does not identify which separated
   material pieces belong to one extant locus. On Human P3, bp recall is
   `94.315%` while fragments/truth is `1.292`; on Mouse P3, bp recall is
   `95.298%` while fragments/truth is `2.144`.
2. Human comparator labels are binary TE/background/unknown runs. They do not
   contain biological copy identity, parent insertion identity or nested
   parent-child topology.
3. Generic DAPT, TE-aware MLM, P3 U-Net/boundary supervision, thresholding,
   gap merge, minimum length and local structured smoothing did not introduce
   that missing variable. P3-R2 failed the frozen Human route and its aligned
   supervision was worse than the matched spatial-permutation control on the
   mechanism endpoints.
4. Gap errors are clustered and heterogeneous. Human P3 has 4,961 internal
   gaps in 14,253 comparator runs; 64.77% are at most 2 bp, but the p99 is
   137.4 bp and the maximum is 16,384 bp. Short gaps are common, but distance
   alone does not tell whether a gap is a model dropout, host material, a
   nested child, another locus or an unidentifiable interruption.

The target is therefore hierarchical: retain the observed TE-material mask,
represent its coherent atoms, then infer typed relations among atoms without
relabeling the convex hull as TE-positive. This is the defensible version of
the gene/exon analogy: atoms resemble supported exons, while interruptions
remain explicitly typed rather than being silently filled as introns.

## Independent Pro review and V1.4 lock

ChatGPT Pro reviewed the repository and then reviewed the two final V1.4
ambiguities. The accepted operational interpretation is:

- ADJ may also be the fixed provenance auditor, but the 40-anchor audit is
  completed and locked before ADJ sees A1/A2 answers, disagreement summaries,
  metrics, projection or P3. It is an anchor-feasibility audit, not a locus or
  boundary annotation. Its prior category is hidden during adjudication.
- Boundary intervals and locus envelopes are epistemic annotations only. They
  never add, remove or fill observed material and never enter atom projection.
- Assigned and unresolved material may not overlap. Unresolved material enters
  total supported overlap; the already frozen 50%, 90/10 and 20% rules decide
  `unassigned`, `unique`, `mixed` or `unresolved`. A 1-bp contact has no special
  precedence.
- The preregistered gating burden remains
  `count(topology_resolution == "new_topology") / 120`. A coordinator witnesses
  package locks and reasons. A deterministic post-lock audit compares ADJ-A1,
  ADJ-A2 and A1-A2 topology, but is non-gating and cannot rescue or overturn
  A1/A2 reproducibility.

The binding files are:

- `docs/experiments/FBTI-EXTANT-LOCUS-ANNOTATION-CONTRACT-V1.4-ADDENDUM-20260901.md`;
- `docs/experiments/FBTI-GATE-L-ANNOTATOR-HANDBOOK-V1.4-20260901.md`;
- `docs/experiments/manifests/FBTI-EXTANT-LOCUS-GATE-L-V1.4/evidence_registry.tsv`.

## Frozen experiment matrix

| Stage | New information being tested | Frozen input | Output | Go/no-go consequence | Resource |
|---|---|---|---|---|---:|
| Calibration | whether two people can apply one ontology | 12 opaque P3-blind packages | locked wording, registry and schemas | semantic change repeats calibration | 12--16 person-hours |
| L-P | whether source provenance supports anchor review | 40 frozen deep anchors | provenance feasibility | failure closes this FlyBase truth route | 12--20 person-hours |
| L-R | whether material/locus/topology calls reproduce | 120 main packages | A1/A2 IoU, count, graph and boundary-status agreement | failure closes supervised locus assembly under this ontology | 90--120 person-hours, parallel |
| L-D | whether relation denominators exist | adjudicated main plus paired reserve prefix | multipart/nested/distinct/pair/ambiguous counts | insufficiency closes relation training on this asset | CPU plus reserve annotation only if requested |
| O | whether perfect atom membership would help | frozen atoms + adjudicated truth | oracle grouping ceiling and fusion safety | failure closes P3 atoms as an assembly substrate | CPU only |
| E | whether label-blind relations add information | frozen eligible pairs and grouped folds | B3 versus geometry B1/B2 | failure requires genuinely new observations | 220--440 CPU core-hours |
| Restricted model | whether passed information can be deployed | unchanged atoms, labels and folds | abstaining typed relation calls | confirmatory only | GPU budget decided after E |

FlyBase is not rebuilt for each step. The exact r6.68 packet and provenance
assets are reusable. It remains a positive-locus panel: whole-genome
precision/F1, FPR and population prevalence are forbidden. A positive method
paper still requires an independent biological-locus panel, preferably Human
if the final claim is Human annotation.

## Machine closure ledger

| Asset or check | Job / commit | Observed result | Classification |
|---|---|---|---|
| 120 main + 40 reserve packets | `12125398` | both tasks `COMPLETED 0:0` | engineering |
| response-schema kits | `12125409` | calibration and main templates complete | engineering |
| accepted provenance table | `12125437` | 293 rows, 120 packages, 40 deep calls blank, registered evidence code present | engineering |
| accepted calibration deliveries | `12125438` | A1/A2 each 12 packets and six response TSVs; order differs; no P3/manifest/atoms | engineering |
| accepted main deliveries | `12125441` | A1/A2 each 120 packets and six response TSVs; order differs; no P3/manifest/atoms | engineering, sealed |
| earlier module tests | `12125426` | 26 tests passed in `te_benchmark` | engineering |
| V1.4 full module + synthetic chain | `12125446` | 37 tests passed in 4.921 s, including NumPy bootstrap and full CLI chain | engineering gate passed |
| V1.4/projection/provenance/topology implementation | commits through `201ab2f` | GitHub and Baobab fast-forwarded | reproducibility |

The current server hand-off paths are:

```text
/home/users/j/jwang/ab-initio-TE/outputs/FBTI-EXTANT-LOCUS-PHASE0-R1/calibration-delivery-v1.4-20260901-r2/A1
/home/users/j/jwang/ab-initio-TE/outputs/FBTI-EXTANT-LOCUS-PHASE0-R1/calibration-delivery-v1.4-20260901-r2/A2
/home/users/j/jwang/ab-initio-TE/outputs/FBTI-EXTANT-LOCUS-PHASE0-R1/main-delivery-v1.4-20260901-r1/A1
/home/users/j/jwang/ab-initio-TE/outputs/FBTI-EXTANT-LOCUS-PHASE0-R1/main-delivery-v1.4-20260901-r1/A2
/home/users/j/jwang/ab-initio-TE/outputs/FBTI-EXTANT-LOCUS-PHASE0-R1/main-provenance-audit-v1.4-20260901-r2/provenance_audit.tsv
```

The older `*-proposal-*` deliveries are retained as engineering provenance and
must not be distributed.

## Fastest human execution plan

### Required named roles

- `A1`: independent TE/genome annotator;
- `A2`: second independent annotator, with no access to A1;
- `ADJ`: fixed provenance auditor and later adjudicator;
- coordinator: controls sealing, schema validation and unblinding, but does not
  create a fourth biological answer.

An agent, repeated passes by one person or an LLM cannot occupy A1/A2. Their
independence is the scientific observation being measured.

### Critical path

1. **Calibration, elapsed 1--2 working days.** A1/A2 independently complete
   the 12 calibration deliveries. The coordinator validates both returns.
   They discuss instruction ambiguity only; calibration answers never enter a
   metric. Any semantic change increments the contract and repeats all 12.
2. **Main annotation and provenance audit in parallel, elapsed 5--8 working
   days at full-time effort.** After calibration lock, A1/A2 receive the sealed
   120-package deliveries. At the same time ADJ completes the 40 frozen
   provenance rows without seeing either answer bundle. A1/A2 output remains
   sealed until the audit is locked.
3. **Validation and adjudication, elapsed 3--5 working days.** The coordinator
   validates and normalizes both bundles, then gives their disagreements and
   underlying evidence—not the provenance categories—to ADJ. ADJ returns a
   complete bundle and locks `topology_resolution` package by package.
4. **Automatic closure, minutes of CPU time.** The frozen scripts calculate
   L-P, L-R, the non-gating topology consistency audit, atom projection and
   L-D. Only a requested paired reserve prefix is annotated; the reserve may
   not be cherry-picked.

With three available experts, the realistic fastest elapsed time is roughly
9--15 working days. Machine-side delay after each human return is minutes, not
days. The schedule cannot be shortened by adding GPUs because the critical
path is independent biological judgement.

## Frozen Gate L decision

### L-P

- source assembly/contig/coordinate/feature identity integrity: `100%`;
- at least `36/40` deep anchors are interpretable or explicit-uncertain;
- unsupported copied point boundaries: `<=0.20`.

L-P is one fixed expert's provenance feasibility judgement, not an
inter-annotator reproducibility claim.

### L-R on the 120 main packages

- median material-union IoU `>=0.80`, bootstrap lower bound `>=0.70`;
- exact locus-count agreement `>=0.70`;
- ontology-edge macro-F1 `>=0.75`, bootstrap lower bound `>=0.65`;
- boundary-status Gwet AC1 `>=0.60`, with at least 40 matched loci from 20
  packages;
- major topology adjudication `<=0.35`;
- resolved + partially resolved packages `>=0.65`.

The automatic topology audit is reported alongside the field-based major
burden. Discordance is visible and publishable, but it does not change the
pre-registered gate or rescue failed A1/A2 agreement.

### L-D

- 30 resolved multipart loci from at least 20 packages;
- 20 nested relations from at least 10 packages;
- 30 distinct-locus pairs from at least 15 packages;
- 50 positive co-locus atom pairs from at least 25 packages;
- 15 mixed/unresolved atoms from at least 10 packages.

Final status precedence is `CONTRACT_INVALID`, `NO_GO_LP`, `NO_GO_LR`, explicit
boundary-denominator insufficiency, `INCOMPLETE`,
`LABEL_DENOMINATOR_INSUFFICIENT`, then `PASS`.

## What happens after Gate L

| Gate outcome | Meaning | Next only | Closed immediately |
|---|---|---|---|
| `NO_GO_LP` | the current source cannot support the intended anchor semantics | construct an independent locus truth source | relation learning on this asset |
| `NO_GO_LR` | the ontology is not reproducible | redesign the biological object or publish ambiguity | model capacity as a replacement for truth |
| L-D insufficient after reserve | the panel lacks relation supervision | another independently justified truth asset | sequence-only impossibility claim |
| L `PASS`, O fail | even oracle membership cannot rescue frozen atoms safely | diagnose/change atom source | new heads/losses on P3 atoms |
| L/O `PASS`, E fail | tested single-genome relations add insufficient safe information | comparative empty-site or other new evidence | larger encoder, LoRA, graph decoder |
| L/O/E `PASS` | truth, oracle value and incremental signal exist | one <=2M-parameter abstaining relation head, then independent-species confirmation | simultaneous atomizer/assembler redesign |

The one remaining mechanism-distinct form of post-training is therefore
conditional and relational: train same-locus/distinct/nested/unresolved atom
relations with instance-labelled positives and same-family different-instance
hard negatives. It is authorized only after L/O/E establish that the labels,
oracle value and non-geometric information exist. It is not TE-aware MLM and
does not fill gaps as material.

## Publication boundary

Already supportable:

- high bp recovery is insufficient for logical TE-instance annotation;
- tested local post-training/segmentation/post-processing objectives do not
  supply instance identity;
- gap errors are clustered and heterogeneous rather than IID;
- a positive-only FlyBase-derived panel can be used for a bounded ontology and
  route-selection test.

Not yet supportable:

- that Gate L has passed;
- that every FBti record is one independently verified biological insertion;
- whole-genome Fly precision/F1 or FPR;
- Human or cross-species instance generalization;
- recovery of deleted ancestral boundaries from one extant sequence;
- superiority of a post-trained instance assembler.

The strongest honest final question remains:

> Can explicit, label-blind cross-atom evidence organize discontinuous
> observed TE-derived material into uncertainty-aware extant loci while
> preserving nested children and abstaining where locus identity is not
> identifiable?

## Immediate next-only dependency

Machine preparation no longer blocks the experiment. Before any distribution,
the coordinator must record the real people assigned to `A1`, `A2` and `ADJ`.
Once named, distribute only the two accepted calibration paths above. Main
deliveries stay sealed until the calibration semantics are locked. No new GPU
job is authorized while this human dependency is unresolved.
