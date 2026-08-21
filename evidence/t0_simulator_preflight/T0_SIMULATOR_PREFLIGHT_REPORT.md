# T0 controlled-truth simulator preflight

Date: 2026-08-08  
Executor: Codex lead  
Status: **blocked for claim-grade T0 generation pending fixes and independent verification**  
Work type: source audit and executable counterexamples; not a benchmark result

## Why T0 is required

Only a completely known simulated genome can support whole-space precision, specificity, FPR, F1, calibration and exact fusion/fragmentation/nesting truth. FlyBase and Rice reference sets remain T1 curated/reference positives and cannot substitute for T0.

## Candidate A: `IOB-Muenster/denovoTE-eval`

- Repository: https://github.com/IOB-Muenster/denovoTE-eval
- Pinned commit: `f735c252224e926707eca3a077c18915bcc7ee2d`
- Commit date: 2025-01-30T11:25:40Z
- Commit tree: `da4553e8096126e38eff689259723a97c8fcc419`
- License: GPL-3.0
- The simulator exposes a seed and parameters for identity, indels, TSD, fragmentation and nesting. Its simulated-genome approach was reused in the 2025 TEtrimmer Nature Communications paper.

Pinned source hashes:

| File | SHA-256 |
|---|---|
| `random_sequence_TEs.py` | `c23409278f81bb16d7ef6927513b95349b450ceca746809937c0e4693f6b4b70` |
| `random_nest_TEs.py` | `8140b85a5c3a357bf83dfe822912ea0b64821191daf417a397de4aa4b6c0b84d` |
| `config.yml` | `7de7cfc0311ac2483280e1e2cf4605747c42d35c02b984dde8579045cc962fd2` |
| `repeats_list` | `061184f6ca0604cd5bd5af5bfd27eb1835c4a16ca5176493afb88534f14c804a` |
| `repeats.fa` | `28fa4378f943d43e2c6e165066a49424258bc91ddceba604e7f597b8fb6a019d` |

The immutable checkout is stored at:

```text
/home/users/j/jwang/ab-initio-TE/software/external_sources/denovoTE-eval_f735c252
```

### Executable counterexamples

Slurm job `11455694` ran four independent contract tests against the unmodified pinned checkout. The job exited `1:0` because all four counterexamples failed, as expected for an audit that is designed to reject an unsafe simulator:

1. **Deletion indel applied to the wrong base.** `add_indels("ACGTA", [3])` with a forced deletion returns `CGTA`; it deletes loop index 0 instead of declared target position 3. Expected output is `ACGA`.
2. **TSD state leaks between elements.** A TSD-enabled one-base element followed by a TSD-disabled one-base element in a four-base background yields length 14 instead of 10. `tsd_seq_5`/`tsd_seq_3` are not reset inside the loop, so the second element inherits the first element's TSD.
3. **Negative identity is accepted.** With the RNG returning `-5`, `get_identity` returns `-5`; it only resamples values above 100. Invalid values can later make the requested mismatch sample exceed sequence length.
4. **Nested outer-right coordinate is off by one.** In a controlled 10 bp host with a 2 bp nested insertion, the nested interval ends at 8 but the outer right fragment starts at 8, not 9. Truth intervals overlap by one base that belongs to the nested element.

Evidence:

| File | Bytes | SHA-256 |
|---|---:|---|
| `test_upstream_denovote_simulator.py` | 4,532 | `db66d00b57de4b481848539b5f808650e62fb71de95b791a36f51b595322ba83` |
| `test_upstream_denovote_simulator.sbatch` | 657 | `0870b7e2a485f3274aec9eaed08527db80f1258b781c925355200f7a218b5ba3` |
| `test_upstream_denovote_simulator.11455694.slurm.err` | 2,860 | `9dc78d5c9a1cb28bd4353ef6c75e1b11a5317a32f5daf436bac5748c8a3df0bd` |

These are truth-generation defects, not cosmetic issues. No genome produced by the unmodified scripts may be called complete T0 truth.

## Candidate B: TE_Bench / GARLIC

- TE_Bench paper: Kania, Seifert & Yoder (2026), *Mobile DNA*, DOI `10.1186/s13100-026-00405-z`.
- Repository: https://github.com/hkania/TE_Bench
- Audited HEAD: `e7b92c56c055737b32720d473927c92894c787b2`
- Commit date: 2026-05-22T18:49:02Z
- Commit tree: `4f60d150a18b4ef0a876692bedb0252229e90144`
- TE_Bench uses GARLIC simulation and can benchmark nested structure, but its official guide explicitly states that GARLIC sequence generation does not follow a given seed. Its annotation-generation test is documented as approximately six hours for the supplied case.

TE_Bench/GARLIC is therefore suitable as an independently generated sensitivity route only if every realized input/output is archived with bytes and hashes. It cannot be the sole deterministic T0 generator for this project.

## Required repair and promotion gates

1. Patch Candidate A in a project-owned adapter/copy without modifying the immutable upstream checkout.
2. Make every parameter explicit; reject missing/zero/negative/out-of-range seeds, identities, indel fractions, fragmentation rates and nesting rates.
3. Fix deletion positions, reset per-element TSD state, and correct nested coordinate arithmetic.
4. Add stable unique instance IDs, raw family/superfamily labels, parent/child nesting IDs, original-copy coordinates, mutated-copy coordinates, TSD coordinates and explicit 0/1-based conventions.
5. Independently reconstruct every emitted TE sequence from the final FASTA and truth table, including strand, indel, fragmentation, nesting and TSD boundaries.
6. Prove same configuration+seed gives byte-identical FASTA/truth/manifest in two clean directories; prove different seeds produce distinct content while preserving requested strata.
7. Reject overlapping top-level insertions unless they are explicitly represented by a parent/child topology edge.
8. Run multiple archived seeds per condition; the seed/genome is a simulation replicate, not each TE interval.
9. Use TE_Bench/GARLIC as an external simulator sensitivity stratum with fully archived realized outputs; do not claim seed reproducibility that the official guide disclaims.
10. Do not start five-tool T0 performance runs until the simulator and independent verifier both pass.

## Proposed claim-grade factor design after repair

The initial promotion screen should use four 20 Mb profiles × five preregistered seeds:

- intact, low-divergence, non-nested;
- mixed divergence with realistic class balance;
- high-fragmentation/aged copies;
- high-nesting plus mixed fragmentation.

Only after all five tools complete the 20-genome screen should a compact factorial be scaled. Divergence, indel burden, fragmentation and nesting must be varied orthogonally enough to estimate their effects; simulation seed is the replicate. Full tool-by-profile results must retain failures/timeouts in the denominator.

No T0 asset or T0 performance result is frozen at this stage.
