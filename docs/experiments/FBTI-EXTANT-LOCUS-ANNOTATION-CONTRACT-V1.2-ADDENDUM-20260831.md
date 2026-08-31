# FBTI extant-locus annotation contract V1.2 addendum

Date: 2026-08-31

Status: **implementation-blocking role-priority and manifest correction**

This addendum changes only the seeded MILP objective in Section 2 of
`FBTI-EXTANT-LOCUS-ANNOTATION-CONTRACT-V1-ADDENDUM-20260831.md` and supersedes
the V1.1 requirement to reuse the earlier priority vector.

The V1 implementation assigned the same candidate-level objective coefficient
to calibration, main and reserve variables. Swapping two eligible candidates
between roles could therefore leave the objective unchanged even though only
main packages enter the Gate L estimand. Job `12121043` consequently does not
freeze a valid role assignment. Retry `12121050` was cancelled when this defect
was identified and also enters no scientific denominator.

For V1.2:

1. Sort population rows by `unit_id` and variables within each row in the fixed
   order `calibration`, `main`, `reserve`.
2. Use NumPy `PCG64(seed=20260831)` to draw one float64 priority for every
   candidate-role variable, in that exact order.
3. Use this single length-`3N` vector directly as the MILP objective and write
   the selected candidate-role value as `selection_priority`.
4. The priority uses no P3 atom, FlyBase name, nearest gap, annotation or
   difficulty judgement.

## Deep-audit records

Before annotation, select exactly 20 S0 main packages and 20 S1 main packages
by ascending selected candidate-role `selection_priority`, breaking a residual
tie by `package_id`. For each selected package, freeze the lexicographically
first focal `feature_id` as `deep_audit_feature_id`. Components are disjoint, so
the resulting 40 records are distinct. This selection cannot use annotation
difficulty or any post-freeze diagnostic.

## Frozen census inputs and generation commit

The formal census output retains direct copies of the exact truth table,
overlap table, P3 atom table and contig-length table it consumed. The joint
panel and sidecar job reads those frozen copies, requires the census `STATUS`
to be `PASS`, and records both census and panel-generation Git commits. No
checksum or fingerprint sidecar is introduced.

After context generation, a truth `feature_id` may occur in only one selected
package. If a non-focal truth interval spans two otherwise non-overlapping
packages, stop with `CONTRACT_INVALID`; the packages would not be independent
bootstrap units. This rule does not apply to P3 atoms, which follow V1.1.

All hard cells, role totals, expanded-package non-overlap constraints and
annotation rules otherwise remain unchanged. V1.2 freezes a new panel because
the earlier role-tied output was never a valid frozen panel; this is not an
outcome-based package swap.
