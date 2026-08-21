## Judgment

`run-sanity-check-first`: execute one strictly bounded HiTE-only continuation.

## Evidence interpretation

RM2+RepeatMasker is a credible engineering pass. HiTE is INVALID_RUN because rc124 proves only that 600s was insufficient. Overall remains failed and supports no biological accuracy claim.

## Reuse assessment

RM can be reused only as an independent cell artifact: preserve original exp/job/container/input/command/version/manifest hashes, keep R1 aggregate FAILED, and label final reconciliation as a combination of two independently reviewed artifacts.

## Next-run design

Prefer A. New HiTE-only exp; identical SIF/fixture/direct argv/annotate/2 threads/offline; 4 CPU/48 GiB/0 GPU/1h; 1800s timeout and at least 600s remaining for cleanup/adapter/publish. Success requires rc0, non-empty parseable final GFF and canonical adapter output.

## Mandatory gates

- Freeze all input/code/asset/argv/version hashes and a cell-level reuse policy.
- Explicit total budget, kill-after and headroom.
- Zero-exit + final GFF + adapter + manifest rehash.
- Reconciliation checks both parent jobs and all pins; any drift forbids combination.
- If 1800s still times out, stop; do not auto-extend.
- No accuracy/pipeline/SOTA claim.

## Single next action

Build and review a frozen HiTE-only 1800-second continuation; submit only after gates pass.

## Confidence

High.

