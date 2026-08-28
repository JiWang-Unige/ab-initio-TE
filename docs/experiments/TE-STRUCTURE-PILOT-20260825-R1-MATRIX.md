# TE structure pilot: frozen Round-1 matrix

Date: 2026-08-25
Base commit: `67e1fd8396278b9982a3aaaafde54027d84aa411`

## Decision

The previous experiment is now named **generic human MLM-DAPT**. It used 3,000
random Human chr1 windows, nucleotide MLM and 800 optimizer steps. It did not
test TE-aware span masking or supervised multiscale segmentation.

No current repository asset establishes copy-level biological TE start/end,
full-length status or copy identity. Human H0 labels are RepeatMasker/UCSC-style
comparator runs; FlyBase is positive-only T1. These annotations are nevertheless
valid side information for deciding where a self-supervised nucleotide masking
task is sampled. Consequently:

1. D1 and D2 precede scientific interpretation of any new training.
2. P2-H is unblocked as **high-confidence RepeatMasker-reference-enriched,
   annotation-conditioned TE-aware continued pretraining**.
   It tests whether sampling 32-bp MLM spans from reference-annotation interior,
   boundary-crossing and flank regions reduces downstream comparator-run
   fragmentation. It does not test biological full-copy boundary learning.
3. Round 1 trains P2-H on the exact materialized Human chr1-prefix windows used
   by P1. Mouse chr1 is a no-tuning external-transfer set; all Drosophila remain
   a species holdout. Human+Mouse P2-HM is conditional
   Round 2, because running it first would confound masking with species mixture.
4. P2-H and P3-H run independently and in parallel. P3 tests task geometry, not
   recovery of biological full-copy truth. P4 opens only if both independently
   pass; a composition-matched P2-C has priority over P4.
5. The HiTE chr17 cell is an engineering comparison against the same
   RepeatMasker-style comparator, not a biological accuracy benchmark.

## Unified experiment matrix

| ID | Scientific hypothesis | Only changed variable | Data / species | Frozen split | Leakage status | Model / tool | Metrics | Go / no-go gate | Estimate | Dependencies | Can claim | Cannot claim |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D1-H | Longer comparator runs are reconstructed more completely | Truth-length stratum only | Existing Human chr17-prefix Base-CE and DAPT-CE predictions | train chr1; validation chr11; test chr17 prefix | No coordinate overlap; label-source leakage remains | Frozen predictions + strict interval evaluator | segment recall/F1@0.8; boundary recall/F1@5/25; fragments/truth; split; missed in `<80`, `80-499`, `500-999`, `>=1000` | Go to long-seed interpretation only if recall and boundary recall improve monotonically and `>=1000` segment recall is at least 2x `80-499`; otherwise no long-seed claim | CPU <1 h | Existing matched predictions | Length association with RepeatMasker comparator recovery | Biological full-length recovery or causality |
| D1-F | Longer curated FlyBase positives are easier to recover | Truth-length stratum only | Existing Base, DAPT and HiTE on FB2026_02 dmel r6.68 | FlyBase T1 species holdout | No Drosophila training for Base/DAPT; HiTE uses target genome | Frozen predictions + T1 evaluator | segment recall@0.8; boundary recall@5/25; fragments/truth; split; missed | Same monotonic/2x screen as D1-H; F1 is forbidden on T1 | CPU <1 h | FlyBase frozen assets | Positive-truth length association | Precision/F1 or exhaustive accuracy |
| D2 | RepeatMasker-style calls fragment curated FlyBase instances | Annotation source only | dm6 annotation aligned to FlyBase r6.68 | Whole frozen assembly; no training | Assembly identity must match; no model leakage | RepeatMasker/UCSC annotation + FlyBase T1 evaluator | bp recall; segment recall@0.8; boundary recall@5/25; fragments/truth; split; missed | If segment recall <0.5 or fragments/truth >1.5 while bp recall is material, treat RM rows/runs as inadequate full-copy boundary supervision | CPU 1-2 h | Exact assembly, contig map, RM provenance | Agreement/coverage of curated positives by RM-style calls | RM false positives or biological truth outside curated positives |
| H1 | HiTE and model outputs can be compared on one identical instance contract | Tool only | Human chr17 `0-9,830,400`, same FASTA, comparator and unknown mask | Existing held-out chr17 prefix | Same-label source for train/test; no coordinate overlap | HiTE 3.3.3; Base-CE; DAPT-CE | bp P/R/F1; segment F1@0.8; boundary F1@5/25; short rate; fragments/truth; split; missed; runtime | Go only if HiTE emits a non-empty canonical GFF and all methods share identical coordinates/mask. Otherwise engineering failure | CPU 4-12 h, tool-dependent | Frozen HiTE image; chr17-prefix FASTA | Engineering feasibility and RepeatMasker-comparator agreement | Independent biological superiority, novel TE discovery |
| P0 | Frozen direct-annotation baseline | None | Human H0 8192 bp | chr1/chr11/chr17-prefix | Label-source leakage acknowledged | Base checkpoint -> linear CE head | Frozen six-gate metrics + D1 | Comparator | Completed | None | Baseline comparator agreement | Full-copy annotation |
| P1 | Generic human continuation changes the representation | Generic MLM continuation only | 3,000 Human chr1 windows | Same as P0 | Same species and label source | Generic MLM-DAPT -> identical CE head | Frozen six gates + D1 | Completed 4/6: fragmentation hypothesis not passed | Completed | P0 | Exact recipe result | TE-aware post-training result |
| P2-M | A high-confidence reference sidecar can supply the complete TE-conditioned masking budget | Sidecar/filter and mask mechanism only | Same Human chr1-prefix source; raw hs1 RepeatMasker `.out` conditions masks | Split before sidecar filtering/mask construction | No family/copy field; homology leakage unknown and not claimable | Fixed alignment-quality filter + annotation-conditioned span-MLM builder/collator | retained/scanned; exact selected bp; global stratum fractions; every boundary span crosses a known transition; zero neutral fill | Go only if retained >=1,000, exact fixed-span 15% budget, interior 40-50%, boundary 25-35%, flank 20-30%; otherwise P2-H is not submitted | CPU <1 h | Audited Human H0 data and raw `.out` | Correct implementation of a high-confidence reference-enriched masking corpus | Biological TE boundary, full copy or model performance |
| P2-H | The complete high-confidence reference-enriched post-training recipe improves downstream reference-run structure | Enriched retained corpus plus annotation-conditioned span masking; backbone, 8192 context, 800 steps and CE stage remain fixed | Actual materialized train/val/test are chr1/chr11/chr17 prefixes; matched evaluation is first 1,200 chr17 windows; Mouse chr1 external; dm6 excluded | Coordinate split only; Mouse never tunes thresholds; family/homology leakage unknown | TE-aware span-MLM -> identical CE head | Human six gates; D1; Mouse transfer; FlyBase T1; stratum audit | Human must reach segment F1 >=0.400724, boundary F1@5 >=0.244286, short <=0.497931, fragments/truth <=1.180148, bp F1 >=0.929173 and missed <=0.087532. Human failure stops A | GPU <=8 h | P2-M GO | Engineering/scientific increment of the complete enriched annotation-conditioned recipe on this Human screen | Mask-only causality without P2-C; biological copy boundaries; multi-chromosome, unseen-family or universal transfer |
| P2-C | P2-H gain comes from annotation conditioning rather than contiguous spans/composition | Remove TE-coordinate conditioning only | Same Human windows, 32-bp spans, masked bp, 800 steps and CE; local GC/4-mer matched | No TE coordinate used to choose masks | Composition-matched span-MLM -> identical CE | Same as P2-H | Conditional on P2-H Human pass; P2-H must exceed P2-C by >=0.01 segment F1 and >=0.01 boundary F1, plus >=5% relative short or fragments improvement | GPU <=8 h conditional | P2-H Human pass | Annotation conditioning adds value beyond span masking/composition | TE grammar from MLM alone |
| P3 | Joint multiscale segmentation fixes task geometry better than a linear token head | Segmentation head/state target only; base checkpoint, Human data, 8192 context and optimizer steps matched | Human H0 comparator runs | chr1 train; chr11 validation; chr17-prefix test | No coordinate overlap; labels still RM-style | Trainable backbone + minimal 1D U-Net, four states: background/interior/left/right | Same six gates; boundary@25; D1; body/boundary channel diagnostics | Go if segment F1 and boundary F1@5 both exceed P0, short rate falls >=20%, fragments/truth falls >=15%, bp F1 decreases <=0.005 and missed increases <=0.03 | GPU 8-12 h | D1-H; label builder smoke | Multiscale supervised adaptation improves comparator-run segmentation | Biological copy boundaries or cross-species generalization |
| P4 | Representation adaptation and segmentation adaptation are complementary | P2 initialization only relative to P3 | Same data and split as P3 | Same as P3; dm6 excluded from P2 | Requires valid P2 leakage audit | P2 checkpoint -> identical P3 | Same as P3 plus FlyBase T1 | Go only if it beats `max(P2,P3)` on segment/boundary and passes all retention gates | GPU 8-12 h | P2 and P3 both pass | Interaction of two validated stages | General TE model without species holdout evidence |
| C5 | Genome-wide multi-copy evidence supplies information absent from local direct inference | Add target-genome copy search/MSA/refinement | Long high-confidence seeds on held-out target genome | Seeds selected without truth; evaluation frozen | Target-genome adaptation is explicit, not hidden | Direct seed model + copy search + MSA + consensus | seed precision/recall where definable; curated T1 recalls; boundaries; fragment recovery | Start only after direct stop rule or strong D1 long-seed result. Must outperform HiTE ablations on the same instance | CPU/GPU deferred | D1/D2 and direct stop | Hybrid discovery/refinement | Pure direct annotation |

## Stop rules

Pure direct annotation stops after the conditional ladder
`P2-H/P3-H -> P2-C or P2-HM -> P4` when either condition holds:

- neither model improves both segment F1 and boundary F1@5 on Human while
  satisfying the bp/missed retention gates; or
- improvement is Human-only and FlyBase `>=1000` segment/boundary recall remains
  below 0.05 or below one tenth of HiTE on the same positive truth.

Human failure stops P2 immediately. Human success with Mouse failure permits
exactly one fixed-budget P2-HM rescue (Human 1,500 + Mouse 1,500 windows; Mouse
chr1 excluded, chr2-13 train, chr14-16 validation, chr17-19 test). Failure after
that rescue closes A; more mammals, more steps and MoE are not allowed rescues.

The project then retains the direct model only as a long/high-confidence seed
generator and moves to C5. Complex MoE, large multi-species training and a
TE-specific HMM remain out of Round 1.

P3 is a 128-channel minimal falsification pilot, not a reproduction of
SegmentNT's much larger segmentation head or its original label ontology.

## What would demonstrate structure rather than composition

P2/P3 cannot use lower MLM/CE loss alone. A structural interpretation requires
all of the following observable evidence: boundary improvement at both 5 and
25 bp, lower fragmentation without higher missed rate, persistence in the
`>=500` and `>=1000` strata, and a Drosophila species holdout result. A later
mechanism cell should composition-match interior/flank negatives and shuffle
boundary position within the same sequences; loss of the gain after boundary
shuffling, but not after GC/k-mer matching, is the discriminating result.
