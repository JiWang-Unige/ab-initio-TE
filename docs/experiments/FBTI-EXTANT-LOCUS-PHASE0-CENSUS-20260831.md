# FBTI-EXTANT-LOCUS-PHASE0-R1 population census

Date: 2026-08-31

Status: **engineering census passed; Gate L has not been evaluated**

Git implementation: `9d2cd9e83b09cc657cb4efcad92244ca9e47d747`

Slurm job: `12120604`, `COMPLETED 0:0`, 4 CPU, 32 GB requested,
0 GPU, 7 seconds elapsed.

## Question answered

This run asked only whether the provided FlyBase r6.68-derived tables and P3
canonical intervals can be joined into the complete label-blind S0/S1 package
population without changing coordinates, merging atoms or assigning a
biological locus interpretation.

The run would have stopped package construction if the supplied length table,
truth coordinates, feature IDs or the supplied 594-pair overlap graph disagreed
internally.
It did not sample calibration/main/reserve packages and cannot pass Gate L.

## Frozen inputs used

- FlyBase r6.68 5,734-row positive-instance metadata;
- FlyBase r6.68 594-pair interval-overlap graph;
- supplied 1,870-contig length table, 143,726,002 bp;
- the unchanged merged P3 canonical interval output from the completed exact
  FlyBase inference.

All intervals were interpreted as zero-based and half-open. S0 is a singleton
component of the supplied overlap graph. S1 is one complete non-singleton
connected component. Package spans are the S0 anchor or complete S1 envelope
plus 10 kb on each side, clipped at contig boundaries.

## Result

| Quantity | Observed |
|---|---:|
| FlyBase records | 5,734 |
| Supplied and independently reconstructed overlap pairs | 594 |
| Records participating in overlap | 812 |
| S0 coordinate-isolated units | 4,922 |
| S1 complete overlap components | 304 |
| Frozen P3 canonical atoms | 1,316,960 |
| Maximum non-overlapping S0 packages by earliest-end scheduling | 1,714 |
| Maximum non-overlapping S1 packages by earliest-end scheduling | 163 |
| Maximum non-overlapping packages without an S0/S1 quota | 1,737 |

The marginal S0 and S1 capacities exceed the requested 86 packages per type
(6 calibration, 60 main and 20 reserve). These separate maxima do **not** prove
that a jointly quota-constrained, challenge-balanced 86+86 panel exists. The
next sampler must construct that joint panel explicitly.

### Continuous population attributes

Values below are minimum / linear-interpolated first quartile / median /
linear-interpolated third quartile / maximum.

| Unit | Attribute | Five-number summary |
|---|---|---|
| S0 | core length | 6 / 109 / 313.5 / 1,097 / 26,406 |
| S0 | P3 atoms in core | 0 / 1 / 4 / 29 / 748 |
| S0 | nearest FBti gap | 0 / 85.25 / 879 / 8,706.5 / 294,853 |
| S1 | component envelope length | 158 / 1,270.25 / 2,652.5 / 6,220.25 / 66,001 |
| S1 | component size | 2 / 2 / 2 / 3 / 29 |
| S1 | maximum overlap depth | 2 / 2 / 2 / 2 / 5 |
| S1 | P3 atoms in core | 0 / 22.75 / 52.5 / 140.75 / 1,673 |

## Protocol defects exposed by the real assets

### Exact-name denominator is absent

All 5,734 complete `flybase_name` strings are distinct. Consequently:

- `exact-name frequency` has no variation and cannot be a sampling stratum;
- `exact-name-matched different-locus FPR` has a zero denominator;
- removing the brace suffix and calling the result a family would introduce an
  unverified family label and is not authorized.

The sampling-axis defect must be removed before panel construction and Gate L.
The zero-denominator FPR must be removed or marked not estimable before Gate E.
Neither defect changes the completed population census.

### Frozen P3 atoms have no probability values

The canonical file stores interval coordinates but `score` and `attributes`
are `.`. It is sufficient for Gate L Pass-2 projection and Gate O oracle
grouping, but not for the registered Gate E B2 features requiring P3 mean and
maximum probability. No new inference is authorized now. If L and O pass, the
Gate E input and resource contract must first be amended before any package-
local probability export is considered.

### Sampling and annotation calculations were under-specified

The parent protocol named the sampling variables but did not freeze bin
boundaries, quotas, seed or a non-overlap design with known inclusion
probabilities. It also did not fully define the Gate L annotation schemas,
locus correspondence, topology F1, boundary AC1, reserve activation or status
precedence.

`FBTI-EXTANT-LOCUS-ANNOTATION-CONTRACT-V0-20260831.md` is the implementation-
blocking proposal that resolves the annotation and metric definitions. It is
not yet a result. Panel sampling remains blocked until the zero-denominator
name term and the sampling design are independently reviewed and frozen.

## Status classification

### Engineering

- Truth, overlap graph, supplied r6.68 length table and P3 intervals passed the
  registered internal-consistency checks and joined.
- S0/S1 population census and continuous sampling variables materialized.
- The CPU-only Slurm path and unique attempt output were verified.

### Scientific

No new scientific result. No annotator reproduced the ontology, no oracle was
evaluated and no relation feature was tested.

### Closed

- Treating full `flybase_name` frequency as a usable stratum;
- reporting exact-name-matched FPR on the present raw string;
- reconstructing P3 probability from the canonical interval TSV;
- starting a Gate E model or any GPU work from this census.

### Next-only

Run the V1 fixed-seed joint challenge-panel freeze and then build the selected
context/atom manifests. Stop if the exact role/cell quotas and joint 86 S0 + 86
S1 non-overlap requirement are infeasible. This panel supports only conditional
challenge-panel conclusions, not FlyBase-population estimates.
