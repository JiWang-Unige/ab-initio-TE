# TEFM benchmark data freeze v0.2

Date frozen: 2026-08-08  
Status: executable data contract; it does not assert any tool-performance result  
Parent protocol: `BENCHMARK_CONTRACT_V0_1.md`

## Non-negotiable truth tiers

- **T0 controlled complete truth:** full precision/recall/F1, boundary error, nesting, fusion/fragmentation and calibration are allowed only after a complete synthetic truth generator and its independent verifier pass. No production T0 asset is frozen yet.
- **T1 curated/reference positive:** positive recall, positive boundary recovery, full-length recovery within a declared positive subset, known-positive topology diagnostics and ontology-conditioned recall are allowed. Unlabelled genome space is unknown, not negative.
- **T2 diagnostic:** coverage, concordance and qualitative discovery diagnostics only. No absolute accuracy claim.

The biological unit is genome/species. Interval rows, chromosomes and TE copies are not independent biological replicates.

## FlyBase FB2026_02 / D. melanogaster r6.68

### Frozen assets

| Role | Asset | Bytes | SHA-256 |
|---|---|---:|---|
| Exact assembly | `dmel-all-chromosome-r6.68.fasta.gz` | 42,393,067 | `81751d3b66bc504525ab88342aa91817eee80bfff136c893e9cda76ea05643b1` |
| Curated-positive instances | `dmel-all-transposon-r6.68.fasta.gz` | 2,555,275 | `cef9cb5d71752bf1999a90259fdf1b5d831231876f3bfa58ad6981e02cee7ec0` |
| Same-release annotation | `dmel-all-r6.68.gff.gz` | 823,890,922 | `e91afadca66c5e1a9bae64cb0e7b7bea439bb86069bf847f42a6bb5a386a1f46` |

All 5,734 FASTA records match their 1-based-inclusive, strand-aware header coordinates exactly in the assembly. All IDs also match same-release primary GFF `transposable_element` coordinates: 5,733 coordinate-and-strand exact plus `FBti0215368`, whose GFF strand is officially unspecified (`.`). Corrected GFF QA Slurm job `11455471` completed `0:0`.

### Frozen derived truth

Remote: `data/raw/benchmark_v1/flybase/FB2026_02/dmel_r6.68/derived/curated_positive_truth_v1/`

- BED: 5,734 rows, 0-based half-open, SHA-256 `d47d94aa56b4c65ce8199838c3c71a37a58bc54590ce277f1ffdf14b10413bd2`.
- Metadata: 5,734 rows, SHA-256 `2a60cb9037525e15bc58d6c77a434cc7f7e5dc3b52ad65bab968b8ff5dd8e904`.
- Overlap graph: 594 pairs, SHA-256 `c64cc23ea6728376aa56b4d4a509247f4d43c0b539e281a8920f475dde9a6f1a`.
- Manifest SHA-256: `fb1a651d412488f279b164145f55ad7276d4b8b407dd5068c61b7dd9e89cd6a7`.
- Independent verifier SHA-256: `1b0d21792b4fe6b392d664b406f1dcb0e35ef2e2449feffbc7f8615396ecf424`.

Exactly 812 positive intervals participate in an overlap. Relationships are 573 strict containments, 20 partial overlaps and one equal-coordinate pair; maximum local half-open depth is five. Evaluators must preserve this graph. Flat overwrite, last-write-wins label arrays and union-only instance scoring are forbidden.

FlyBase names are retained as source names, not yet treated as a validated TE superfamily ontology. Full-length wording must be restricted to a separately preregistered subset or stated as recovery of FlyBase exported positive instances; the six-base minimum forbids calling every entry full-length autonomous.

## Rice RGAP Release 7 / EDTA v2.3.0 reference

### Frozen assets and sequence domain

| Role | Asset | Bytes | SHA-256 |
|---|---|---:|---|
| RGAP7 assembly | `all.con` | 381,956,675 | `db8b7efb4df6ae33195143f3444b8816917441e1b964d150663ceeb2249506c4` |
| EDTA reference annotation | `Rice_MSU7.fasta.std7.0.0.out` | 67,732,146 | `dbcc72884c9eb633c1657cc18af4797c2717fce81ff0736b79bf94fe7c46d04f` |
| EDTA reference library | `rice7.0.0.liban` | 5,306,510 | `bb470806821d8ba990fc0e89ae61cba2341dcde7cc72cfbcd264a1adf6abef2b` |

EDTA release commit: `a9f7a56d6a1c1a9cdcf2a1d7b8c27a74a38dbfc2`. Annotation blob: `7532cec33fcf81a69b58f3f1cd3cbbe5f986715b`. Library blob: `7977b028b61edc47e839736c17e43715038c3d5c`.

The denominator is exactly RGAP `Chr1` through `Chr12`. These 12 sequences are hash-identical to the existing IRGSP-1.0 records `1` through `12`. `ChrSy`, `ChrUn`, organelles, BACs and Ensembl `Syng_TIGR_*` extras are outside the primary denominator.

### Frozen row partition

Source rows: 494,393. Build job `11455558` and independent verifier `11455566` completed `0:0`.

| Decision | Rows | Frozen rule |
|---|---:|---|
| T1 TE-positive segment | 386,672 | Primary chromosome and root in `DNAauto`, `DNAnona`, `Evirus`, `LINE`, `LTR`, `MITE`, `SINE` |
| Primary non-TE exclusion | 106,397 | Primary chromosome and root in `Centro`, `Low_complexity`, `Satellite`, `Simple_repeat` |
| Non-primary exclusion | 1,324 | `ChrSy` or `ChrUn`, irrespective of repeat class |

The retained segment union is 173,256,733 bp; raw aligned-segment sum is 176,682,526 bp. Source topology is preserved: 341,313 `(query, RepeatMasker ID)` groups, 30,255 multirow groups and 45,228 `*`-marked rows. No silent group merge is allowed.

Remote: `data/raw/benchmark_v1/rice/derived/edta_v230_positive_segments_v1/`

- BED SHA-256: `df4d734e95efd7c168a0e573922440a75d6bb637d296721a47adfbd15e2f853a`.
- Positive TSV SHA-256: `06ac8f7cb0976aeae2a061f6c184779aebb5caf0b162b9755967985a0a89c6bf`.
- Five-output manifest SHA-256: `23c209c44b8cb2678c46a457cd429f2d44d10517cdf725489fc51c0b61fbaa56`.
- Independent verifier SHA-256: `54f70891de2e07b37badcd76fb9d15a2d60eee17f1b6516d2a64c2f4e0a0cac0`.

`Evirus` is included in the primary TE-like positive set; a sensitivity result excluding it must accompany any class-aggregated endpoint. Raw class/family strings must be retained alongside any ontology normalization.

## Maize MTEC scope

MTEC is a family/consensus-library resource, not coordinate-complete instance truth. Historical and current immutable assets contain 1,477 and 1,517 records, respectively. All 1,477 historical records are unchanged; current adds exactly 40 records. Current MTEC incorporates TEtrimmer-assisted additions and lacks an explicit repository license. Therefore:

- do not use current MTEC as an unqualified independent truth for the TEtrimmer curation arm;
- report historical-common and 40-added strata separately if used;
- do not redistribute either biological asset until rights are resolved;
- do not compute whole-genome precision/F1 from MTEC.

## Global evaluator requirements

1. Verify input bytes and SHA-256 before every run.
2. Record coordinate convention at every adapter boundary; reject ambiguous BED/GFF semantics.
3. Preserve original source ID, raw label and topology/group ID.
4. Use a deterministic, order-invariant maximum-quality matching objective for instance endpoints.
5. Report fragment and fusion topology separately from one-to-one matches.
6. Reject NaN/Infinity, duplicate truth IDs, path traversal, stale completion markers and mismatched result identities.
7. Count failed, timed-out and unsupported native executions in the declared denominator; do not silently drop cells.
8. Do not begin real-tool T1 pilots until the external frozen-contract acceptance suite passes in an isolated candidate tree.

## Remaining blockers

- Production T0 controlled truth and verifier are not frozen.
- Rice/Fly superfamily ontology joins are not frozen.
- Rice/RGAP and MTEC redistribution rights remain unresolved.
- B73v4 coordinate-level T1 truth remains unresolved; MTEC alone does not solve it.
- The five-tool runner/reconciler P0 defects remain under external-engineer correction and Codex revalidation.
