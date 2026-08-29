# TE structure pilot: final decision report

Date: 2026-08-29

## Decision

The frozen Human screen closes the current pure direct-annotation route.
Neither TE-aware span-MLM followed by the matched CE stage (P2-H-R2) nor the
minimal four-state multiscale U-Net (P3-H) passed the preregistered Human
fragmentation gate. P2 passed 2/6 conditions and P3 passed 4/6. P2-C, P2-HM,
P4, Mouse/Fly transfer escalation, MoE, more MLM variants and a TE-specific HMM
are therefore not authorized by this pilot.

The next research route is a bounded hybrid discovery/refinement pilot:
long/high-confidence seeds, target-genome copy search, multi-copy alignment,
boundary refinement from internal homology versus divergent flanks, seed-only
consensus construction, and only then short-fragment recovery. This is not pure
direct annotation.

## Evidence status

| Evidence | Status | Interpretation allowed |
|---|---|---|
| Human D1, Job `12098335` | Completed CPU rescue; diagnostic scientific evidence within the frozen comparator screen | Length association with RepeatMasker-style run recovery |
| HiTE Human chr17, Job `12097868` | Completed engineering pilot | Same-instance RepeatMasker-comparator agreement and runtime feasibility |
| P3-H payload + finalize Job `12098769` | Recovered pilot; original Job `12097889` failed only on its final log write | Frozen go/no-go decision; not a clean single-job paper denominator |
| P2-H-R2 span-MLM/CE payload + strict-eval Job `12107296` | Recovered split-stage pilot; original training wrappers `12098005` and `12098772` failed on shared-log writes after saving their respective artifacts | Frozen go/no-go decision; not a clean single-job paper denominator |
| D2 RepeatMasker–FlyBase | Blocked by assembly identity | No D2 biological interpretation |

The failed wrappers and their real causes remain recorded. They are not
reported as successful scientific jobs. The completed rescue/finalize jobs
make the saved outputs usable for the pilot stop decision, but do not turn the
failed job identifiers into successful denominator runs.

## Human matched results

All rows use the same first 1,200 chr17 8192-bp windows and
RepeatMasker-style comparator. Segment F1 is at IoU 0.8 and boundary F1 uses a
5-bp tolerance.

| Method | bp F1 | Segment F1 | Boundary F1 | Short rate | Fragments/truth | Missed rate | Frozen gate |
|---|---:|---:|---:|---:|---:|---:|---|
| P0 Base-CE | 0.933773 | 0.339956 | 0.199781 | 0.622414 | 1.388409 | 0.057532 | Baseline |
| P1 generic DAPT-CE | 0.934173 | 0.380724 | 0.224286 | 0.547001 | 1.263032 | 0.060198 | 4/6, NO-GO |
| P2-H-R2 span-MLM -> CE | 0.937653 | 0.370356 | 0.229826 | 0.588583 | 1.400407 | 0.057532 | 2/6, NO-GO |
| P3-H four-state U-Net | 0.934496 | 0.378631 | 0.215650 | 0.551110 | 1.292430 | 0.055637 | 4/6, NO-GO |
| HiTE | 0.711143 | 0.312135 | 0.119373 | 0.229818 | 0.687294 | 0.393952 | Engineering comparator only |

P2 retained bp accuracy and missed rate, but it did not improve segment F1
over P1 and made both short rate and fragments/truth worse. The result does not
support annotation-conditioned span masking as a solution to fragmentation in
this recipe.

P3 improved segment and 5-bp boundary F1 over Base while retaining bp F1 and
missed rate. Its short rate fell by about 11%, not the required 20%, and
fragments/truth fell by about 7%, not the required 15%. The minimal multiscale
head changes task geometry in the expected direction but does not close the
fragment problem.

HiTE does not dominate the direct models on the Human comparator. Its much
lower fragmentation is coupled to a missed rate of 0.394, versus about 0.056-
0.060 for the direct models; its segment and boundary F1 are also lower. The
comparison shows a precision/continuity versus recovery trade-off, not
independent biological superiority.

## D1: length does not rescue current direct annotation

| Model | Truth length | Segment F1 | Segment recall | Boundary F1@5 | Boundary recall@5 | Fragments/truth | Missed | Split |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Base | <80 | 0.2105 | 0.1855 | 0.1167 | 0.1028 | 1.0321 | 0.2691 | 0.1313 |
| Base | 80-499 | 0.5446 | 0.5677 | 0.3419 | 0.3564 | 1.2769 | 0.0461 | 0.1349 |
| Base | 500-999 | 0.3526 | 0.4883 | 0.1357 | 0.1879 | 1.9438 | 0.0093 | 0.2847 |
| Base | >=1000 | 0.2126 | 0.3770 | 0.0294 | 0.0521 | 2.7271 | 0.0016 | 0.3533 |
| DAPT | <80 | 0.2223 | 0.1864 | 0.1238 | 0.1038 | 0.9513 | 0.2663 | 0.0891 |
| DAPT | 80-499 | 0.5639 | 0.5607 | 0.3541 | 0.3521 | 1.1809 | 0.0498 | 0.0960 |
| DAPT | 500-999 | 0.3908 | 0.4904 | 0.1577 | 0.1979 | 1.6804 | 0.0093 | 0.2434 |
| DAPT | >=1000 | 0.2494 | 0.3927 | 0.0391 | 0.0615 | 2.3155 | 0.0016 | 0.3155 |

Long Human comparator runs are detected but reconstructed badly. In the
`>=1000` bin, missed rate is almost zero while boundary F1 collapses and
fragments/truth rises above 2.3. This falsifies the prerequisite that the
current direct models already provide accurately bounded long seeds.

FlyBase D1 gives a different result for HiTE: its segment and boundary recall
increase with truth length and `>=1000` segment recall is 0.3395, while Base
and DAPT recover no `>=1000` truth at IoU 0.8. Consequently, a hybrid pilot may
use HiTE-like target-genome evidence as its initial positive control, but the
current direct model cannot yet be assumed to be the long-seed engine.

## D2 remains unresolved

The available UCSC RepeatMasker asset is dm6 with `chr2L/...` and `chrUn_*`
contigs, whereas the FlyBase curated-positive truth uses release r6.68 contigs
`2L/2R/3L/3R/4/X/Y`. Prefix rewriting does not establish assembly identity.
D2 remains blocked until RepeatMasker is run on the exact FlyBase r6.68 FASTA
or a documented coordinate/assembly mapping is supplied. Until then, the
project cannot claim that RepeatMasker rows themselves fragment the curated
FlyBase instances.

## Engineering failures retained

| Job | Real outcome |
|---|---|
| `12097785` | Human D1 predictions completed; shared stdout flush failed (`exit 120`). Not in denominator. |
| `12098149` | First D1 CPU evaluation wrote JSONs; stdout flush failed (`exit 120`). Not in denominator. |
| `12097867` | First P3 training attempt hit shared tqdm/log I/O. Not in denominator. |
| `12097889` | P3 training and evaluation completed; final `echo` returned Remote I/O (`exit 1`). Finalized by `12098769`. |
| `12098005` | P2 span-MLM completed; CE was interrupted by shared tqdm/log I/O (`exit 120`). |
| `12098772` | P2 CE training, model save and token test completed; stdout flush failed before strict segmentation (`exit 120`). |
| `12107296` | P2 strict segment evaluation completed (`0:0`) with evaluator output redirected away from the Slurm stream. |

The repeated failures were logging-path engineering failures, not evidence for
or against the biological hypotheses. The recovered metrics above are used
only for route selection.

## Closed directions

- Generic Human MLM-DAPT as a fragment solution.
- This Human annotation-conditioned 32-bp span-MLM recipe.
- This minimal four-state 128-channel U-Net as a sufficient direct solution.
- Threshold sweeps, gap merging, minimum-length filtering, HMM/CRF-style
  inference smoothing and more generic post-processing.
- P2-C, P2-HM and P4, because their prerequisite Human gates failed.
- MoE, larger multi-species continuation, more masking variants and a
  TE-specific HMM in the next round.

These results do not prove that every SegmentNT-scale architecture or every
TE-aware objective must fail. They close the preregistered implementations and
the current escalation ladder.

## Next-only experiment set

1. **D2 exact-assembly repair.** Run RepeatMasker on the exact FlyBase r6.68
   FASTA, freeze the annotation provenance, and compare it directly with the
   curated-positive truth. This is CPU work and precedes claims about label
   fragmentation.
2. **C5-H engineering pilot.** On the frozen Human chr17 prefix, compare three
   seed sources: HiTE long/high-confidence calls, P3 high-confidence calls, and
   their union. For each seed source, add target-genome copy search, alignment
   and boundary refinement. Report the existing strict metrics and include a
   seed-source/refinement ablation. A lower fragment count is unacceptable if
   missed rate rises as it did for unrefined HiTE.
3. **C5-F positive-truth falsification.** On exact FlyBase r6.68, freeze seeds
   without consulting truth, build seed-only consensuses, recover copies and
   short fragments, and report positive-truth bp/segment/boundary recall plus
   fragments/truth. Precision/F1 remains forbidden on FlyBase T1.

The C5 pilot proceeds only if copy search plus refinement improves boundary or
segment recovery beyond its seed-only arm while retaining recall. If the gain
comes only from known-library matching, it is a conventional library-assisted
annotation result and must be described that way. If no seed source yields a
measurable refinement gain, the hybrid route stops rather than adding MoE or a
new decoder.

## Publication status

The project now has a defensible negative result and a clear mechanism-level
diagnosis: local direct models recover substantial TE-positive sequence but
split long instances and fail at precise boundaries; generic continuation,
TE-conditioned span continuation and a minimal multiscale head do not solve
that defect under the frozen Human screen. This is not yet a complete paper.

The missing publication evidence is: exact-assembly D2; a clean successful
hybrid ablation; more than one held-out chromosome/species instance; explicit
family/homology separation or an honest statement that it is unavailable; and
evidence that any recovered elements are not merely known-library matches.
No current result supports biological full-copy accuracy, unseen-family
generalization, de novo TE discovery or universal cross-species annotation.
