# FBTI Gate L annotator handbook V1.4

Date: 2026-09-01

Status: **calibration handbook proposal; P3-blind; no scientific result**

This handbook operationalizes the frozen V0--V1.4 annotation contract. It is
for calibration first. It does not ask an annotator to reproduce FlyBase
coordinates, reconstruct an ancestral insertion or repair P3 predictions.

## Roles and blinding

- `A1` and `A2` receive the same opaque packets in different assignment order.
  They work independently and do not see one another's answers.
- Neither annotator sees P3 atoms, probabilities, model outputs or Gate E
  features other than raw-sequence observations already allowed by the
  evidence registry.
- `ADJ` receives A1/A2 answers only after both bundles are locked. ADJ also
  performs the separate 40-record provenance audit before viewing A1/A2.
- Calibration answers never enter Gate L metrics.

The distributed response files use an opaque `CALIB-*`, `MAIN-*` or
`RESERVE-*` value in the field named `package_id`. The coordinator maps it
back to the frozen internal package ID before validation; annotators never
receive that mapping.

## What is being annotated

The primary observable is extant TE-derived material in the supplied assembly.
A logical extant locus may contain several non-touching material segments, for
example around a nested child, an assembly gap or an unresolved interruption.
The interval between segments is not made TE-positive merely because the
segments are grouped.

Do not infer `deletion`, an ancestral breakpoint, or a historical insertion
event from one extant sequence. Use `unresolved` or an interval boundary when
the supplied evidence does not identify the object.

## Packet workflow

For each row of `assignment.tsv`:

1. Read `packet.tsv`, `sequence.fa`, `context_features.tsv` and
   `raw_flybase_features.gff3` in that packet directory.
2. Record the top-level package status in `package_reviews.tsv`.
3. Record every supported material interval in `material_segments.tsv`.
4. Assign a material segment to a locus only when the assignment is stable;
   otherwise use `locus_assignment_status=unresolved` and leave `locus_id`
   empty.
5. Declare supported loci in `loci.tsv`. Envelopes are display-only and do not
   fill the sequence between material segments.
6. Give each locus exactly one left and one right row in `boundaries.tsv`.
7. Record observed interruptions in `interruptions.tsv`.
8. For every unordered pair of declared loci, record exactly one relation in
   `relations.tsv`.
9. Use only codes from the frozen `evidence_registry.tsv`, comma-separated and
   sorted.

All genomic intervals are zero-based half-open. Boundary positions are
interbase coordinates: point uses equal lower/upper positions, interval uses
`lower_pos < upper_pos`, and unidentifiable leaves both positions empty.

## Package and locus status

Use `resolved` only when all supported material is assigned and every locus
pair has a definite relation. Use `partially_resolved` when at least one stable
locus exists but assignment/topology remains uncertain. Use `unresolved` when
material exists but no stable locus partition can be asserted. Use `abstained`
only at package level when the packet is insufficient to make a material or
locus assertion.

Locus status is only `resolved`, `partially_resolved` or `unresolved`.
`unidentifiable` boundary status alone does not downgrade a locus.

## Material and topology rules

- Touching material segments assigned to the same locus are one segment and
  must be merged before lock.
- Assigned material of two resolved or partially resolved loci cannot overlap.
  Ambiguous material uses unresolved assignment.
- Relation values are `nested_in`, `distinct_locus` and
  `overlap_unresolved`.
- `nested_in(child,parent)` is directed and stores only the immediate parent.
- Symmetric relations are stored once with lexicographically ordered locus
  IDs.
- A `nested_locus_occupied` interruption requires `child_locus_id` and the
  matching immediate `nested_in` edge.
- Other interruption values are `unknown_sequence`, `assembly_gap`,
  `non_TE_supported` and `unresolved`.

## Boundaries and evidence

Use a point only when the supplied observations support one interbase
position. A FlyBase feature endpoint or transformed copy of it is not
independent evidence. The specific sequence observation supporting a point
must be recorded using the registry; otherwise use an interval or
unidentifiable boundary.

Boundary intervals never extend or trim supported material. If the material
itself is supported but its locus membership is uncertain, encode that in
`material_segments.tsv`, not by widening a locus envelope.

## Independent lock and adjudication

A1 and A2 each return all six TSVs. The coordinator validates schema and
ontology before revealing either answer. A failed contract check is corrected
as an annotation-format error and produces no scientific result.

ADJ returns a complete bundle, not a patch. For each package,
`topology_resolution` is one of `accept_a1`, `accept_a2`,
`same_topology_minor_edit` or `new_topology`; the last requires a reason.

After the 12 calibration packages, the team records ambiguous instructions,
accepts one contract version and repeats calibration if any semantic rule
changed. Only then may the 120 main packages begin.
