# Publication strategy

Date: 2026-08-09
Status: Publication-Validation planning; no submission-ready claim

## Mode switch

- From: Mixed discovery / asset remediation
- To: Publication-Validation with bounded discovery gates
- Reason: the paper question and four candidate pillars are mature enough to
  define claim-specific evidence, but none of the new pillars yet has a real
  claim-grade result.
- What remains iterative: only asset recovery, falsifiable pilots and minimum
  corrections needed to close a named evidence gap.
- Frozen unless evidence breaks it: truth tiers, no-leakage grouping, separate
  end-to-end and taxonomy benchmark panels, failure accounting, species/clade
  inference units and the rule that model-only hits are not novel TEs.

## Recommended positioning

| Position | Required story | Minimum evidence burden | Current fit |
|---|---|---|---|
| Nature Methods stretch | One reusable end-to-end annotation framework with benchmark leadership, calibrated uncertainty, external genomes and demonstrated downstream biological utility | Five-tool task-matched benchmark; multi-genome T0/Tier-C validation; at least two claim-grade method pillars; robust efficiency; independent downstream task | Not yet eligible; all new pillars remain asset/code gates |
| Nature Communications primary | A coherent biological-computational story showing that topology, hierarchy and transfer uncertainty jointly improve TE annotation across clades | Strong multi-genome benchmark; topology plus open-set results; one independent validation; embedding/transfer may be bounded secondary results | Plausible only after F and S pass real pilots |
| Genome Biology / NAR Genomics and Bioinformatics backup | A rigorous, reusable TE annotation/benchmark resource with one clearly novel method and transparent negative results | Reproducible benchmark; one successful main method; complete provenance, statistics and software usability | Most defensible fallback if only one pillar survives |

Target choice remains conditional. Do not write to a Nature Methods claim burden
until the topology and open-set pilots both pass and one downstream validation is
positive. Nature Communications is the current planning target, not a promised
submission destination.

## One-sentence story

TEFM converts uncertain per-base repeat evidence into topology-preserving loci,
assigns only the deepest taxonomy supported under family/clade shift, and
quantifies when sequence representations or training anchors remain trustworthy,
under a leakage-safe multi-tool benchmark.

## Contribution menu

| ID | Candidate claim | Type | Evidence needed | Current evidence | Risk | Recommendation |
|---|---|---|---|---|---|---|
| C1 | A task-separated, truth-tier-aware benchmark exposes different library, locus, boundary, taxonomy and operational failure modes | data resource / pipeline | Exact five-tool versions, frozen genomes/truth, adapters, paired biological-unit statistics, failures retained | Contract only; no accepted benchmark cells | High | Keep as the paper's evidence spine; run after tool feasibility |
| C2 | A preservation-constrained parent-aware interval lattice reduces fragmentation without fusion or nested-element loss | method mechanism / performance | Real T0 plus deterministic synthetic T0; raw/HMM/CRF/strict/loose comparators; fusion ceiling; ablations | 17-genome synthetic generator and evaluator code gate passed; no method/performance | Medium-high | Primary method pillar; execute first after real A0-A6 gate |
| C3 | Hierarchical open-set annotation emits the deepest supported TE taxon and abstains safely on unseen families/clades | method / robustness | Frozen ontology, homology-blocked and clade-held-out groups, selective risk/calibration, five sequence-classifier comparators | S0-S4 code gate passed; real ontology/homology assets absent | Medium-high | Co-primary pillar if real S0-S4 can be frozen |
| C4 | A calibrated fixed-anchor transfer surface predicts expected range and an uncertainty-aware best-anchor set from pre-annotation genome features | robustness / deployment | Exact anchor provenance or clean rebuild, balanced species-by-anchor cube, grouped validation, uncertainty and OOD rule | Real P1 proves all five historical run records are missing | Very high | Rebuild/recover first; secondary claim only; kill if balanced design is infeasible |
| C5 | Raw pretrained DNA embeddings improve label-free recovery of sealed TE families beyond sequence-similarity and untrained controls | method mechanism | Official Parasail freeze, sealed family/copy groups, identity components, representation-matched clustering grid and stability | Security/asset code gate passed; backend pins and real assets absent | High | Exploratory secondary pillar; no UMAP-only claim |
| C6 | Topology-aware masks improve an independent biological analysis at matched coverage | biological insight / downstream utility | Preregistered gene-annotation or comparable task, identical evidence, coverage-matched controls, locus audit | Not started | High | Required for Nature Methods stretch; bounded validation for Nature Communications |

## Claim ordering and kill rules

1. C1 provides the denominator and evaluator contract; it cannot be replaced by
   historical summary tables.
2. C2 is the first scientific pilot because its loci feed C3 and C5.
3. C3 is promoted only if homology-blocked selective risk improves and unknown
   remains a valid output.
4. C4 is dropped from the headline if exact/rebuilt anchors or a balanced cube
   cannot be obtained; a negative provenance result belongs in Methods/Supplement.
5. C5 is promoted only if gains persist against alignment/MinHash/k-mer and
   untrained controls under sealed family and species strata.
6. C6 is run only after one stable mask intervention exists; a negative result
   narrows the venue/story rather than triggering post-hoc endpoints.

## Figure and table plan

| Figure/table | Message | Required experiments | Status |
|---|---|---|---|
| Fig. 1 | Task/truth hierarchy and five-tool benchmark reveal distinct failure modes and resource trade-offs | BENCH-PILOT, BENCH-FULL | Blocked on tool/assets |
| Fig. 2 | Parent-aware topology recovers fragmented loci without fusion or supported-base deletion | F-REAL-ASSET, F-PILOT, F-SCALE | Synthetic code gate only |
| Fig. 3 | Hierarchical open-set labels remain calibrated under family/clade shift | S-REAL-ASSET, S-PILOT, S-SCALE | Code gate only |
| Fig. 4 | Representation value is separable from sequence similarity, length/GC/species confounding and cluster choice | E-BACKEND, E-ASSET, E-PILOT, E-SCALE | Code gate only |
| Fig. 5 | Transfer is an uncertainty-aware surface/best-anchor set, not a universal scalar law | G-P1.5, G-CUBE, G-PILOT | P1 blocked; pivot in review |
| Fig. 6 | A coverage-matched downstream task tests biological utility | D-UTILITY-PILOT, D-UTILITY-FULL | Not started |
| Table 1 | Exact tools, versions, databases, modes, assets and failures | BENCH-PILOT/FULL manifests | Not started |
| Table 2 | Claim-to-evidence crosswalk and biological-unit effect sizes/CIs | all admitted full runs | Not started |

## Current conclusion

- Recommended target: Nature Communications planning target; Nature Methods
  remains a stretch conditional on C2+C3+benchmark+downstream utility.
- Main story: uncertainty-aware TE annotation across topology, taxonomy and
  cross-genome transfer, with label-free representation evidence as a separate
  falsifiable mechanism test.
- Keep: C1 and C2; conditionally keep C3; treat C4/C5 as kill-gated secondary
  pillars; require C6 only for the stretch target.
- Top evidence gaps: real T0/comparator identities; immutable ontology/homology
  groups; reproducible anchors/balanced cube; official alignment backend and
  sealed family/copy groups; runnable exact five-tool panel.
- Next action: finish the four active real-asset/recovery handoffs, then submit
  only independently reviewed asset jobs through `smart-sbatch`.
