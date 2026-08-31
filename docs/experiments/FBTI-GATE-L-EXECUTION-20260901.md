# FBTI Gate L execution and publication route

Date: 2026-09-01

Status: **machine preparation in progress; human Gate L not evaluated**

## Decision

The fastest defensible path is to finish Gate L before any new post-training,
decoder or post-processing experiment. The frozen project has enough sequence,
FlyBase provenance, panel and P3-atom assets to run the test, but it does not
yet have the independent human annotations that define a biological extant
locus. More GPU work cannot replace that missing observation.

The critical path is therefore:

```text
V1.4 operational lock
  -> 12-package A1/A2 calibration
  -> handbook/evidence-registry lock
  -> 120-package independent A1/A2 annotation
  -> P3-blind third-person adjudication and provenance audit
  -> canonical atom projection
  -> automatic Gate L
  -> Gate O only if L passes
  -> Gate E only if O passes
```

Gate O and Gate E interfaces may be documented while annotation runs, but no
O/E scientific computation, GPU allocation or neural implementation is
authorized early.

## What is already complete

| Asset | State | Meaning |
|---|---|---|
| V1.3 172-package joint panel | frozen | 12 calibration, 120 main, 40 reserve; challenge-panel estimand |
| `context_features.tsv` | frozen | every package-local FlyBase feature, package-unique |
| `package_atoms.tsv` | frozen and hidden in Pass 1 | canonical P3 substrate for later projection |
| 12 calibration evidence packets | `PASS`, job 12122769 | reusable P3-blind human input |
| 120 main evidence packets | `PASS`, job 12125398 task 0 | machine-ready, not yet annotated |
| 40 reserve evidence packets | `PASS`, job 12125398 task 1 | frozen; annotate only by paired prefix after L-D shortfall |
| A1/A2/ADJ response-kit generator | implemented, targeted tests pass | engineering only |
| Human annotations and adjudication | absent | Gate L remains unevaluated |

The main and reserve packet job was CPU-only, used 1 CPU and 8 GB per task,
consumed zero GPU, and completed both tasks in about 71 seconds. It produced
120 and 40 opaque P3-blind packet directories respectively. These are
engineering outputs and enter no scientific denominator by themselves.

## The experiment matrix

| Stage | Scientific question | Frozen input | New observation | Primary output | Gate | Resource |
|---|---|---|---|---|---|---:|
| L-calibration | Can two people apply one ontology without hidden implementation choices? | 12 opaque packets | independent human decisions and ambiguity log | accepted handbook, evidence registry and schemas | no metric | 12--16 person-hours |
| L-P | Is FlyBase provenance adequate for the extant-locus anchor claim? | 40 preselected deep-audit anchors | P3-blind provenance judgement | integrity and 36/40 interpretability checks | pass/fail | 12--20 person-hours |
| L-R | Is the ontology reproducible before adjudication? | fixed 120 main packets | independent A1/A2 material, locus and topology | IoU, count agreement, edge F1, AC1 | pass/fail | 90--120 person-hours in parallel |
| L-D | Does the asset contain enough relation supervision? | adjudicated main plus frozen reserve prefix | locus topology plus rule-derived atom membership | five registered denominators | pass/incomplete/insufficient | reserve adds at most 30--40 person-hours |
| O | Are frozen P3 atoms worth grouping? | adjudicated truth and canonical atoms | manual membership oracle | oracle grouping ceiling and fusion safety | pass/fail | CPU only |
| E | Do non-geometric single-genome relations add information? | fixed eligible pairs and grouped folds | sequence/structure relation features | B3 versus geometry B1/B2 | pass/fail | 220--440 CPU core-hours |
| restricted model | Can the passed signal be deployed? | unchanged atoms, labels and folds | at most 2M trainable relation parameters | abstaining typed relations | confirmatory only | GPU decided later |

## Parallel work without invalidating the experiment

The two annotators are the main parallel branch. They receive the same packet
set in independent order and cannot exchange answers. Packet construction,
return-schema validation, Gate L metric implementation and the coordinator's
provenance table can proceed in parallel because none exposes P3 to A1/A2.

The adjudicator cannot begin package adjudication before both annotation
bundles are locked. Reserve annotation cannot begin before the automatic L-D
count requests the next frozen pair. Gate O cannot begin before final Gate L
`PASS`.

Agents, repeated passes by one person, or a language model cannot be counted as
the two independent biological annotators. They may prepare packets, validate
schemas and calculate registered metrics only.

## Operational lock required before calibration

V1.4 proposes only two clarifications:

1. the third adjudicator performs the 40-record P3-blind provenance audit
   before viewing A1/A2 output;
2. locus boundary intervals never create material, while any canonical atom
   overlapping unresolved-assignment material abstains as `unresolved`.

The initial evidence registry contains one non-independent FlyBase provenance
code, four specific sequence-derived codes that are also future Gate E
features, and one assembly-gap code. The generic existence of raw sequence is
not enough to claim an independently supported point boundary.

These clauses must be accepted before calibration. If calibration shows that
an evidence code or ontology decision is unusable, revise the version and
repeat calibration. No main answer may span contract versions.

## Human hand-off

Each annotator receives:

- one opaque packet directory tree;
- their `assignment.tsv`;
- six blank Pass-1 response TSVs;
- the V1.4 handbook; and
- the frozen evidence registry.

They do not receive `packet_manifest.tsv`, internal package IDs,
`package_atoms.tsv`, P3 probabilities or the other annotator's files. The
coordinator keeps the opaque mapping and normalizes returned IDs only after an
independent bundle is locked.

The calibration exit condition is procedural, not a fitted F1 threshold:

- both complete all 12 packages independently;
- schema validation passes;
- every instruction ambiguity is resolved in writing;
- the handbook, registry and projection rule receive one version;
- semantic changes trigger a new calibration pass.

## Frozen Gate L decision

### L-P provenance

- assembly, contig, coordinate and feature-ID integrity: 100%;
- interpretable or explicit-uncertain deep anchors: at least 36/40;
- unsupported copied point boundaries: at most 0.20.

### L-R reproducibility on 120 main packages

- median material-union IoU at least 0.80; bootstrap lower bound at least 0.70;
- exact locus-count agreement at least 0.70;
- ontology-edge macro-F1 at least 0.75; bootstrap lower bound at least 0.65;
- boundary-status Gwet AC1 at least 0.60 with its registered denominator;
- major topology adjudication at most 0.35;
- resolved plus partially resolved packages at least 0.65.

### L-D denominator

- at least 30 resolved multipart loci from 20 packages;
- 20 eligible nested relations from 10 packages;
- 30 eligible distinct-locus pairs from 15 packages;
- 50 positive co-locus atom pairs from 25 packages;
- 15 mixed/unresolved atoms from 10 packages.

Final status precedence remains `CONTRACT_INVALID`, `NO_GO_LP`, `NO_GO_LR`,
explicit metric-denominator insufficiency, `INCOMPLETE`,
`LABEL_DENOMINATOR_INSUFFICIENT`, then `PASS`.

## What each outcome changes

| Outcome | Scientific meaning | Next-only | Closed |
|---|---|---|---|
| `NO_GO_LP` | this FlyBase asset cannot support the intended locus semantics | independent truth source | relation modelling on this asset |
| `NO_GO_LR` | the ontology is not reproducible | redesign the object or publish ambiguity | model capacity as a substitute for truth |
| denominator insufficient | this panel lacks trainable relation events | another truth asset, if justified | sequence-only impossibility claim |
| O fail | P3 is a poor atom substrate even with an oracle | diagnose/new atom source | more heads/losses on P3 atoms |
| E fail | tested single-genome relations add insufficient safe information | comparative empty-site evidence | larger encoder, LoRA, graph decoder |
| L/O/E pass | truth, oracle value and incremental signal exist | one restricted relation head, then an independent species panel | simultaneous atomizer/assembler redesign |

## Publication boundary

A passed Phase 0 can support a route-selection result on a double-annotated,
adjudicated FlyBase-derived positive-locus panel. It cannot support FlyBase
whole-genome precision/F1, ancestral insertion recovery, population prevalence
or cross-species generality. A positive method paper still needs a second
independent biological-locus panel, preferably Human if the final claim is
Human annotation.

The strongest honest question is whether explicit cross-atom relation evidence
can organize discontinuous observed TE-derived material into uncertainty-aware
extant loci while preserving nested children and abstaining on unidentifiable
cases. This is more informative than lowering flat-run `fragments/truth` by
filling short gaps.

## Immediate next actions

1. Accept or revise the two V1.4 clarifications.
2. Name two independent annotators and one adjudicator/provenance auditor.
3. Materialize the 12 calibration response kits and distribute them with the
   handbook and evidence registry.
4. Finish the Pass-1 validator and Gate L calculator on synthetic fixtures
   while the people annotate.
5. Lock calibration before distributing the already-built 120 main packets.

No new GPU run is part of these actions.
