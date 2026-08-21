# Common review prompt — S0 identity/provenance valid negative

All three reviewers were given the same frozen evidence for
`SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1`, Job `11524255`.

They were asked to determine whether the CPU-only audit was semantically valid,
whether exact Dfam name/accession identity was sufficient for a leakage-safe S0
family/homology split, whether S0 DATA/GPU or hierarchical S1 could proceed, and
which single bounded action should follow. The frozen facts were:

- Slurm `COMPLETED 0:0`, 4 CPU/32 GiB/0 GPU, 18m32s.
- Audit terminal `IDENTITY_PROVENANCE_TYPED_BLOCK`, semantic success and valid
  negative; no split, clustering, training, inference or model metric.
- 35,616,746 parsed annotation records; 24,566,629 P records; 24,610,357
  provenance-candidate records; 43,728 label-contract-excluded records.
- 6,447/6,727 P identifiers uniquely resolved (`0.9583766909469302`); 279
  missing and one ambiguous (`X13_LINE`, 686 occurrences, two exact candidates).
- Identifier and occurrence conservation delta is zero; no silent deletion.
- The 10 excluded identifiers are retained separately and not treated as
  negatives or silently inserted into the provenance denominator.
- Canonical output manifest 7/7 and payload manifest 5/5 rehash successfully.
- The route-level S0 goal remains unvalidated because no
  `main4_conditional_macro_f1` exists.

The reviewers were explicitly forbidden to reinterpret the audit as a model
result, weaken the denominator, authorize GPU/S1, or silently choose a new
identity/homology/label policy.
