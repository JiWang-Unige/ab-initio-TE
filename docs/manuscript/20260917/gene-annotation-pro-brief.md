# Gene-annotation-led v1: evidence and editorial review brief

Date: 2026-09-17. Status: discussion brief, **not an approved new experimental protocol**. Evidence baseline: `14d8d5c97cdef63e76f6b983d335747298c55157`. The 20260916 manuscript and all frozen reports remain unchanged.

## Decision to review

Can a focused v1 paper center on useful gene annotation with predicted repeat masks, instead of presenting every exploratory TE-model branch? Assess a Nature Communications ambition honestly, identifying a finite set of decisive additions rather than a larger model-development programme. Unrelated exploratory branches can be outside the paper's scope; directly relevant controls, prespecified endpoint outcomes and local losses cannot be selectively suppressed. No new experiments are being launched by this brief.

Crucially, **P3 (human-trained GENERanno-family model) is not D (six-species NTv2-500M model)**. Their positive and negative results cannot be attributed interchangeably.

## Strongest completed evidence: P3 masks and Tiberius

P3 produces a TE-material softmask using 8192-bp windows and a frozen 0.5 threshold. The downstream experiment does not require recovering complete biological TE insertions. A target-library-independent inference path is distinct from independence of training annotations or foundation-model pretraining exposure.

| Panel | Reference loci | U_soft F1 | U_nosm F1 | P3-mask F1 | RepeatMasker TE F1 | RepeatMasker all-repeat F1 |
|---|---:|---:|---:|---:|---:|---:|
| Human hg38 chr16/18 | 726 | 0.636307 | Not run | 0.699363 | Not separately run | 0.695431 (historical UCSC track) |
| Cow ARS-UCD2.0 | 470 | 0.437651 | 0.548604 | 0.616466 | 0.617383 | 0.611222 |
| Platypus mOrnAna1.pri.v4 | 639 | 0.557425 | 0.532342 | 0.589170 | 0.591733 | 0.589949 |

Human: 20 fixed 5-Mb cores, paired block bootstrap. P−U_soft = +0.063056, 95% interval [0.036503, 0.106832], 55 gained and 16 lost exact-reference loci. The prespecified ≤1% loss safeguard **failed** (16/510 = 3.1373%); the joint gate remains not met. P−R interval crosses zero.

Cow and platypus: 20 fixed 5-Mb cores per species across ten autosomes, 100-kb halos, 200 Mb total evaluation cores. All 40 cores and 200 native five-arm calls completed, with no difficult-core exclusion. Cow/platypus are absent from the frozen Tiberius checkpoint's 29-species training list; do not extend this to unverified foundation-model pretraining independence.

- P−U_nosm: cow +0.067861 [0.028046, 0.116576]; platypus +0.056828 [0.028078, 0.082591]. This compares complete pipelines with different Tiberius checkpoints.
- P−U_soft: cow +0.178815 [0.147761, 0.207924]; platypus +0.031745 [0.005494, 0.061528]. These isolate the mask input using the same checkpoint.
- Prespecified primary P−R_TE: cow −0.000917 [−0.020464, 0.016219]; platypus −0.002563 [−0.015224, 0.009415]. Neither superiority nor equivalence/noninferiority is established.
- Relative to U_soft, gains/losses are 42/7 in cow and 51/24 in platypus. Relative to U_nosm, 53/31 and 90/40. A lost exact reference CDS-chain match is not proof of biological gene deletion.
- External R_TE/R_all use native RepeatMasker 4.2.4 with complete Dfam 3.9 lineage curated+uncurated libraries. Thus these are **not experiments under deliberately scarce target libraries**.
- External evaluation is agreement with assembly-matched NCBI gene annotations, not independent experimental gene truth. Cow has 220 NM-containing loci; platypus has none, so the latter NM subset is null. Bootstrap units are chromosome clusters, not independent species.

Primary records:

- [Human results](../../../reports/P3-TIBERIUS-BASE-MASK-20260911-R1/full-r1-score-12710872/RESULTS.md)
- [External results](../../../reports/P3-TIBERIUS-EXTERNAL-20260915/full-r1-score-12740044/RESULTS.md)
- [Human protocol](../../experiments/P3-TIBERIUS-BASE-MASK-20260911-R1.md)
- [External protocol](../../experiments/P3-TIBERIUS-EXTERNAL-20260915.md)

## Other completed branches: retain provenance, decide manuscript relevance

| Branch | Observed result / boundary | Possible role in a P3-focused paper |
|---|---|---|
| Six-species D | Internal bp macro F1 0.888761; all six species participated in task fine-tuning. Strict segment/boundary measures are much lower. External screens chiefly provide reference-positive recall, not full genome-wide F1. | Omit if D is outside the product and claims; retain if claiming this shared model's broad annotation capability. |
| Controlled library sensitivity | Fixed D checkpoint and 500 DEV tiles/species; Dfam 3.9 curated → curated+uncurated. Zebrafish mask unchanged; pig F1 0.857443→0.648572, chicken 0.827195→0.539633. Some apparent FP gain library support, but many more newly labelled bases are model-negative. | Contextual evidence about comparator dependence, not P3 validation or proof that annotation incompleteness causes the species ranking. |
| Long TE benchmark | D F1 0.450648 on 100-Mb TE_Bench/GARLIC simulation; fixed RM 0.976293, RM2→RM 0.946999, HiTE 0.637386, EDTA 0.844020, EarlGrey 0.974942. Generator records are represented by fixed-library names/accessions. No D CPU speed advantage. CB4 has only 1,571 reference TE bp and cannot support a full precision/F1 ranking. | A direct constraint on D/SOTA TE claims. Does not measure P3. Do not transfer D's benchmark to P3, or cherry-pick only favorable D results. |
| Gap / linking / multi-GLM | No validated biological insertion recovery. One truth-assisted downstream gap-addition diagnostic yielded no new correct CDS chain. | Can defer this separate task; define v1 as material masking, not gap repair or insertion reconstruction. |
| NTv2 label-free clustering | Actual fine-tuning completed; small transductive ARI gain but NMI/inductive ARI not consistently improved; no stable superiority over k-mer SSL. | Entire exploratory branch can be omitted if no clustering claim or delivered module. |
| SF5 classification | Broad-class result completed; material F1 0.884305, main-four pooled macro 0.833687. Not validated family/superfamily annotation for all copies. | Off-scope for binary material-mask utility unless a classification product is claimed. |
| hg19/new annotations | Library/configuration comparisons and matched controls completed; newer library support is not independent biological confirmation. Strong peptide support is scarce. | Avoid a “discovered true TE years in advance” result without stronger evidence. |
| MoE/adapters/multiple prototypes | No consistent gain warranting broader claims. | Defer architecture development to v2; no automatic requirement for a v1 utility paper. |

Records: [library control](../../../reports/SPECIES-LIBRARY-CONTROL-20260916/RESULTS.md), [long benchmark](../../../reports/TE-LONG-BENCH-20260915/RESULTS.md), [current full manuscript](../20260916/manuscript-en.md), [release boundaries](../20260916/reproducibility-and-release.md). These remain available even if not every branch belongs in the narrowed paper.

## Questions for independent editorial/scientific discussion

1. Give one precise, supportable central claim for a P3 gene-annotation paper. Distinguish today's evidence from a conditional stronger claim after a few additions. Is Nature Communications presently justified, or what specifically prevents that?
2. Propose a 4–5-figure narrative and a main/supplement/off-scope table. Which unfavorable findings directly qualify the central claim and must remain visible? Which whole research branches may legitimately be deferred?
3. Does “no target TE reference library at inference” describe the implemented P3 pipeline? What evidence is still needed to claim particular usefulness in library-poor species? Do not describe training as annotation-free.
4. Prioritize at most three decisive experimental packages, with fixed comparisons, endpoints and stopping rules. Consider (i) controlled library availability plus a truly external application, (ii) independent RNA/protein support for gained and lost gene structures, and (iii) P3-matched runtime/strong library-free controls. Do not require multiple training seeds as default; the user prioritizes structural effects.
5. Include strong practical alternatives: official unmasked Tiberius, native rich-library RM, de novo RepeatModeler2→RM, and a lightweight library-independent masker such as Red where appropriate. “Masking beats no mask” alone may have limited novelty. Fairly separate equal-information and full-pipeline practical comparisons.
6. Are current P3 model-selection/training partitions and baseline comparisons sufficient to explain why this model was chosen? Which minimal P3-specific ablation is necessary, rather than borrowing D results?
7. Can whole-genome deployment, independently supported gene corrections and a usable release provide the advance needed without pursuing plants/fungi, MoE, clustering or gap repair now? Specify which additions are essential versus optional.
8. Suggest a restrained positive title and opening claim, and a realistic journal strategy without acceptance probabilities or promises. Avoid making the paper a catalogue of every unsuccessful experiment, while preserving scientific completeness for the stated question.

## Relevant primary context

- [Tiberius original paper](https://academic.oup.com/bioinformatics/article/40/12/btae685/7903281): repeat masking is already part of this research context; a new paper must establish added value beyond that general observation.
- [Tiberius official repository](https://github.com/Gaius-Augustus/Tiberius): current guidance discusses unmasked models and sensitivity to masking. The present experiments use frozen checkpoints and versions, not automatically the latest defaults.
- [Red original study](https://pmc.ncbi.nlm.nih.gov/articles/PMC4513396/): a library-independent repeat detector is a relevant practical control, so absence of a curated target library does not mean absence of alternatives.
- [Nature Communications scope](https://www.nature.com/ncomms/aims): journal fit must rest on the significance of the demonstrated advance, not solely model size or a positive downstream metric.

The review should state which fixed GitHub commit/files it actually accessed. If access is incomplete, distinguish repository verification from evaluation of this supplied evidence brief.
