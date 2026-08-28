# Human/Mouse TE post-training decision

Date: 2026-08-28

## Decision

The copy-level asset blocker is removed for P2-H. Existing Human UCSC/
RepeatMasker-style annotation is sufficient to condition where a nucleotide
span-MLM task is sampled, because the target remains the original nucleotide.
It is not sufficient to call an annotation run a biological full-length copy.

Round 1 is therefore:

1. D1-H, D1-F, D2 and the HiTE Human chr17 engineering pilot on CPU.
2. P2-H: Human-only annotation-conditioned span-MLM, then the identical CE
   stage. Mouse chr1 is external transfer with no tuning; Drosophila is absent
   from all training.
3. P3-H: Base checkpoint plus joint four-state multiscale U-Net training on the
   same Human split.
4. P2-C only if P2-H passes the Human gate. P2-C uses the same Human windows,
   32-bp spans, masked bp and training budget, but selects masks without TE
   coordinates and matches local GC/4-mer composition.
5. P2-HM and P4 are conditional Round 2 and receive no Round-1 GPU budget.

This decision was independently reviewed with ChatGPT Pro using repository
commit `763c8a3d8513c39992fde94ddf3d27c4a568121c`, the frozen Human/FlyBase
metrics, and the audited Human/Mouse/FlyBase assets. Pro agreed that the old
`copy_level=true` training gate was too strict for self-supervised masking, but
that all result wording must remain at reference-annotation level.

## Frozen data roles

- Human metadata lists candidate chromosome groups, but the existing 3,000-row
  materialized train/validation/test files were previously audited row by row
  and stop at the first chromosome: chr1/chr11/chr17 prefixes. The matched
  screen evaluates only the first 1,200 chr17 windows. P2-H Round 1 must reuse
  these exact files to isolate the masking change from P1.
- A confirmatory multi-chromosome panel is not yet materialized. If the pilot
  passes, it must be rebuilt with 600 windows per chromosome: train
  chr1/3/5/7/9, validation chr11/13/15 and test chr17/19/20/21/22.
- Mouse Round-1 external test: the existing 1,200 chr1 windows. It does not
  select thresholds or checkpoints.
- Mouse conditional Round-2: chr2-13 train, chr14-16 validation, chr17-19 test;
  chr1/X/Y/MT excluded.
- Drosophila: complete species holdout.

The current chr1/chr11/chr17 separation prevents coordinate overlap, but the
screen is not evidence of multi-chromosome generalization. It also does not establish
family/copy/homology separation because current assets lack reliable component
identity; unseen-family generalization is therefore not claimable.

## P2-H construction contract

- 8192-bp inputs, 800 optimizer steps, 15% masked bases and the existing
  80/10/10 MLM replacement rule.
- Fixed 32-bp contiguous spans allocated 45% interior, 30% reference-boundary
  crossing and 25% flank.
- Interior is at least 64 bp from a reference-run boundary.
- Boundary spans must actually cross a known TE/non-TE transition and contain
  at least 8 bp on each side; ambiguous overlaps and window edges are excluded.
- Clean external sequence is required for 128 bp; flank spans are sampled
  64-256 bp outside a clean boundary.
- Runs may union only when intervals overlap or directly touch. Positive gaps
  are not merged, and consensus coordinates are not used to fabricate copies.
- Unknown, N, pad and window-edge transitions are never eligible.

The first raw-row eligibility pass uses valid query coordinates, normalized
strand, SW score >=225, milliDiv <=500, milliDel/milliIns <=200, genomic span
>=64 bp, and explicit TE classes (LINE, SINE, LTR, DNA, RC/Helitron and mapped
retrotransposons). Simple repeat, low complexity, satellite, RNA repeats,
unknown and ambiguous other are excluded. These are pilot eligibility rules,
not full-length criteria. Consensus begin/end/left are QC only.

## Gates

P2-H must satisfy all Human conditions relative to the frozen P1 generic DAPT:

- segment F1@0.8 >=0.400724;
- boundary F1@5 >=0.244286;
- short prediction rate <=0.497931;
- fragments/truth <=1.180148;
- bp F1 >=0.929173;
- missed rate <=0.087532.

Mouse positive transfer requires segment F1/recall +0.01 absolute, boundary
F1/recall@5 +0.005, fragments/truth no worse than 1.10x P1 and bp recall at
least 95% of P1. FlyBase is a stress test, not the Round-1 blocker; supportive
transfer is bp recall >=0.025, segment recall >=0.002, boundary recall >=0.001
and fragments/truth below 11.703138.

If P2-H passes Human, P2-H must then beat P2-C by at least 0.01 segment F1 and
0.01 boundary F1, with at least 5% relative improvement in short rate or
fragments/truth. Otherwise the result supports contiguous span MLM, not TE
annotation conditioning.

P3-H uses the same Human fragmentation and retention gates. It is not rescued
with post-hoc HMM/CRF/smoothing if it fails.

## Stop and pivot

- Human P2-H failure closes self-supervised route A and forbids P2-HM.
- Human/mechanism success with Mouse failure permits one fixed-budget P2-HM
  rescue. Failure to produce measurable FlyBase gain closes A; more mammals,
  more steps, MoE and another MLM objective are not allowed rescues.
- P4 is run only if P2 and P3 independently pass, and must beat both parents.
- If the best direct model still fails the Human fragmentation gates or fails
  to transfer structure to Mouse/FlyBase, pure direct annotation closes.
- If D1 shows long TE runs are substantially easier but short-fragment recovery
  remains poor, the retained model becomes a high-confidence long-seed
  generator for target-genome copy search, MSA/consensus, boundary refinement
  and short-fragment recovery. This is hybrid discovery/refinement, not pure
  direct annotation.

## Claims

P2-H success may support: annotation-conditioned TE-aware continued pretraining
improves downstream TE reference-annotation segmentation beyond pretrained and
generic-Human-MLM initialization.

It cannot support biological full-copy boundary recovery, unseen-family
generalization or a universal cross-species annotator. Human/Mouse evaluation
is reference-annotation agreement; FlyBase T1 reports only recall, boundary and
fragmentation.

## Running decision jobs

Slurm `12097522` produced valid Base and DAPT FlyBase D1 JSONs, then failed with
node-to-log `Remote I/O error`. Rescue `12097635` produced the HiTE D1 JSON, then
failed D2 for a scientific contract reason: FlyBase truth uses r6.68 contigs
`2L/2R/3L/3R/4/X/Y`, whereas the available UCSC RepeatMasker asset uses dm6
`chr2L/...` plus many `chrUn_*` contigs. Prefix rewriting is not accepted as
assembly identity. D2 remains blocked until RepeatMasker is run on the exact
FlyBase r6.68 assembly or a documented assembly/coordinate map is available.
Failed attempts are retained outside the scientific denominator.

### FlyBase D1 result

| Model | Bin | Segment recall@0.8 | Boundary recall@5 | Fragments/truth | Missed |
|---|---:|---:|---:|---:|---:|
| Base | <80 | 0 | 0 | 0.0133 | 0.9915 |
| Base | 80-499 | 0 | 0 | 0.1959 | 0.9618 |
| Base | 500-999 | 0 | 0 | 0.7887 | 0.9259 |
| Base | >=1000 | 0 | 0 | 8.8024 | 0.7532 |
| DAPT | <80 | 0.001211 | 0.001211 | 1.6937 | 0.6901 |
| DAPT | 80-499 | 0.000471 | 0 | 6.8643 | 0.5031 |
| DAPT | 500-999 | 0 | 0 | 15.4292 | 0.3486 |
| DAPT | >=1000 | 0 | 0 | 22.4642 | 0.3178 |
| HiTE | <80 | 0.112591 | 0.095642 | 0.1731 | 0.8281 |
| HiTE | 80-499 | 0.161093 | 0.096090 | 0.3297 | 0.6971 |
| HiTE | 500-999 | 0.239651 | 0.143791 | 0.9760 | 0.3638 |
| HiTE | >=1000 | 0.339514 | 0.157289 | 2.4290 | 0.0767 |

HiTE passes the preregistered long-seed screen: segment and boundary recall rise
with truth length, and `>=1000` segment recall is 2.11 times the 80-499 value.
Base and DAPT do not recover any `>=1000` truth at IoU 0.8; their rising
fragments/truth with length is fragmentation, not complete long-TE recovery.
This supports a long-seed substrate for HiTE/hybrid methods, not yet for the
current direct genome-LM models.
