# FBTI extant-locus annotation contract V1.3 addendum

Date: 2026-08-31

Status: **implementation-blocking context-independence correction**

Job `12121964` solved the V1.2 MILP to proven optimality with zero gap, then
stopped because non-focal truth feature `FBti0059698` overlapped two selected
packages. The attempt has no valid sidecars or Gate L result and enters no
scientific denominator.

V1.3 adds one label-blind conflict rule before selection: two candidate
packages conflict when any frozen FlyBase truth interval has positive-length
overlap with both expanded package intervals. This rule uses only the frozen
truth coordinates already defining the sampling frame. It cannot use P3 atoms,
names, annotation outcomes, nearest gap or difficulty judgements.

The same PCG64 seed and candidate-role priority contract, role and hard-cell
quotas, deep-audit rule and V1.1 P3-censoring rule remain unchanged. A new
V1.3 panel is solved ab initio under the enlarged conflict graph. Failure to
find a proven-optimal feasible 172-package solution is
`PROTOCOL_INFEASIBLE_OR_INPUT_MISMATCH`; do not change the seed or repair the
selection.
