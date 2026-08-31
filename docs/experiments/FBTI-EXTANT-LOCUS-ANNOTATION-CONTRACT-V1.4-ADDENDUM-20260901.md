# FBTI extant-locus annotation contract V1.4 addendum

Date: 2026-09-01

Status: **accepted for calibration on 2026-09-01, before any human answer; operational lock; no Gate L result**

This addendum resolves implementation ambiguities found before any human
annotation. It does not change the frozen panel, ontology, thresholds,
bootstrap, reserve order or gate sequence. It is accepted for calibration on
2026-09-01, before any human answer.

## 1. Provenance deep-audit actor

The third adjudicator (`ADJ`) is also the fixed provenance auditor for the 40
preselected `deep_audit_feature_id` records. ADJ completes and locks this
audit P3-blind before viewing any A1/A2 answer bundle, Gate L metric or P3
output/feature. When ADJ later adjudicates, the prior audit category is not
shown and cannot be used as evidence.

The fixed `provenance_audit.tsv` records the source-identity fields, the
registered `evidence_codes`, one category and its note. This audit is a single
anchor-feasibility judgement, not a judgement about material, locus partition,
topology or boundary; it is not an inter-annotator reproducibility metric and
not a three-party consensus. The legacy category values mean only:

- `interpretable_extant_locus`: the anchor is feasible for an extant-locus
  annotation task; this does not assert one locus or any material, topology or
  boundary answer;
- `explicit_uncertain`: the provenance chain is traceable, but a documented
  provenance or biological ambiguity prevents a stable anchor interpretation;
  this does not assert one locus; or
- `uninterpretable`: anchor feasibility for an extant-locus annotation task
  cannot be established.

Every category records one or more supporting registered `evidence_codes`.
The required `audit_note` records the direct reason for the last two classes.
The fixed L-P threshold remains at least 36 of 40 in the first two classes.

## 2. Boundary uncertainty and atom projection

A locus `boundary_interval` and `locus_envelope` are epistemic/display
statements about the outer locus boundary. Neither changes, extends, erodes
or fills an `observed_material_segment`, and neither participates in atom
projection.

Pass-2 projection uses positive-length overlap with the adjudicated material
rows. Assigned and unresolved material rows must not have positive-length
overlap. For each atom, total supported overlap is the union of overlap with
both assigned and unresolved material, counting each base once. The existing
V1 thresholds are then applied to that total support:

1. a package-censored atom is `package_censored` and excluded;
2. if total supported overlap is `<50%` of the atom, the atom is
   `unassigned`;
3. otherwise, calculate each assigned-locus contribution and the total
   supported overlap (including unresolved material). An atom is `unique`
   only when one assigned locus contributes at least 90% of total supported
   overlap and every second assigned locus contributes at most 10%;
4. otherwise, an atom is `mixed` when at least two assigned loci each cover
   `>=20%` of the atom; and
5. otherwise, the atom is `unresolved`.

There is no absolute precedence for any 1-bp overlap. In particular, a
positive-length overlap with unresolved material does not by itself force
`unresolved`; its bases contribute to total support and the existing
`50%`, `90%/10%` and `20%` rules decide the projection.

Consequently, a point/interval/unidentifiable locus boundary alone never
changes atom assignment. This prevents an uncertain outer boundary from
silently becoming material while retaining unresolved material as support
without inventing a locus identity.

## 3. Evidence registry freeze

The initial calibration registry is the committed
`manifests/FBTI-EXTANT-LOCUS-GATE-L-V1.4/evidence_registry.tsv`.
An exact copied FlyBase endpoint is unsupported unless at least one referenced
code has `independent_of_fbti_endpoint=1`. Codes marked `used_by_gate_e=1`
remain legal for Gate L, but a later Gate E primary label inferred only from
such codes must be excluded under the existing circularity rule.

The generic presence of raw sequence is not itself an independent boundary
code. Annotators must record the specific observable used. Empty evidence is
legal and should lead to an interval or unidentifiable boundary when a point
cannot be supported.

## 4. Major topology remains the V0 gate, with a non-gating audit

The V0 preregistered topology fields and definitions remain unchanged,
including `relation_type`, directed immediate-parent `nested_in`, symmetric
`distinct_locus`, `overlap_unresolved`, and the existing
`topology_resolution` values. The gating major-topology burden remains
`count(topology_resolution == "new_topology") / 120`; it is not replaced by a
new distance estimand. ADJ locks this field package by package before aggregate
Gate L output is available. A fixed coordinator witnesses the lock, checks the
frozen category definition and requires a topology-change reason for every
`new_topology`; the coordinator does not annotate or change the bundle.

After lock, a deterministic consistency audit compares ADJ separately with A1
and A2, and A1 with A2. It reuses the V1 maximum-cardinality,
maximum-total-IoU locus matching (`IoU >= 0.50`, genomic-coordinate tie-break),
then asks whether the match is complete, the locus partition on jointly
supported assigned material is identical, and the mapped typed relation graph
is identical, including `nested_in` direction. Actor-local IDs, locus envelopes,
boundary coordinates, evidence codes and material endpoint edits are not
topology evidence. The audit reports equivalence flags, field-by-audit
discordances and unevaluable packages. It never changes the preregistered field
or Gate L PASS/NO-GO status.

## 5. Calibration lock

The 12 calibration packages remain outside every metric. A1 and A2 complete
them independently; the adjudicator then reviews disagreements and records
only instruction ambiguities. Before main annotation, the coordinator freezes:

- this addendum and the annotator handbook;
- the evidence registry;
- the six Pass-1 TSV schemas;
- the opaque-ID normalization rule; and
- the Pass-2 projection rule above.

If a semantic rule changes after calibration, increment the contract version
and repeat calibration. If it changes after any main annotation, re-annotate
every affected main package under one version. Editorial wording that changes
no decision rule may be clarified without changing a locked answer.

No other V0/V1/V1.1/V1.2/V1.3 clause is changed.
