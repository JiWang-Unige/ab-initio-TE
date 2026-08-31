# FBTI extant-locus annotation contract V1.4 addendum

Date: 2026-09-01

Status: **operational clarification proposed before calibration; no Gate L result**

This addendum resolves two implementation ambiguities found before any human
annotation. It does not change the frozen panel, ontology, thresholds,
bootstrap, reserve order or gate sequence. It becomes binding only after the
coordinator and annotators accept it before calibration starts.

## 1. Provenance deep-audit actor

The third adjudicator is also the fixed provenance auditor for the 40
preselected `deep_audit_feature_id` records. The audit is completed P3-blind
and before the adjudicator views either A1 or A2 annotation.

The existing `provenance_audit.tsv` schema remains unchanged because the actor
is fixed by this contract. This audit is a single provenance judgement, not an
inter-annotator reproducibility metric and not a three-party consensus. The
adjudicator may classify only:

- `interpretable_extant_locus`;
- `explicit_uncertain`; or
- `uninterpretable`.

The required `audit_note` records the direct reason for the last two classes.
The fixed L-P threshold remains at least 36 of 40 in the first two classes.

## 2. Boundary uncertainty and atom projection

A locus `boundary_interval` is an epistemic statement about the outer locus
boundary. It never extends, erodes or fills an `observed_material_segment` and
therefore is not an alternative TE-positive interval.

Pass-2 projection uses positive-length overlap with the adjudicated material
rows as follows:

1. a package-censored atom is `package_censored` and excluded;
2. any atom overlapping an adjudicated material row whose
   `locus_assignment_status=unresolved` is `unresolved`;
3. otherwise calculate `C` from assigned material only and apply the V1
   `unassigned`, `unique`, `mixed`, then `unresolved` precedence unchanged.

Consequently, a point/interval/unidentifiable locus boundary alone never
changes atom assignment. This prevents an uncertain outer boundary from
silently becoming material and gives unresolved material an explicit
abstaining projection rather than a guessed locus ID.

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

## 4. Calibration lock

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
