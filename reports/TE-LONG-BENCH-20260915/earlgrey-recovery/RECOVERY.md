# EarlGrey compatibility recovery, 2026-09-15

Both original selected attempts failed after producing their refined libraries:

| input | failed job | original wall seconds | continuation |
|---|---|---:|---|
| full CB4 | 12732198_4 | 6359.033299149014 | 12735632_4 |
| sim100 | 12731947_4 | 7942.038973964984 | 12735633_4 |

The installed EarlGrey 7.3.0 script selects the newest TEstrainer directory using GNU `find -printf`. Its image instead provides BusyBox 1.36.1 find. Running that exact read-only selection pipeline in the failed CB4 directory returned `find: unrecognized: -printf` and pipeline exit codes `1 0 0 0`. The parent's `set -eo pipefail`, combined with stderr suppression in the selection expression, explains the otherwise silent failure immediately after library compilation. Both compiled library files were present and nonempty.

The compatibility repair replaces only directory selection with equivalent Python glob/mtime selection. It is applied to a copy of the actual installed script and bound over its original entrypoint; the original image is unchanged. The patched full script passed Bash syntax validation. Executing its actual replacement expression with `set -eo pipefail` passed both an empty directory case and a case with two directories of known different modification times plus a matching non-directory file.

Each continuation copies the preserved original work tree inside its Slurm allocation and performs the previously interrupted copy of the one completed refined library to EarlGrey's canonical stage output. Original work trees contained no symlinks; no original failed output is overwritten. The native pipeline then skips completed discovery/refinement stages. Live logs confirmed both continuations reached final RepeatMasker annotation with the original combined library.

The unchanged 84600-second native budget includes original wall time, work-tree copying and continuation. `status.json` retains original steps and prior wall time, adds continuation wall time separately, and reports their sum as the cell's `wall_seconds`. These are interrupted workflow costs with disclosed engineering recovery, not an uninterrupted fresh-run timing claim. The original failed status files are retained here; sequence, libraries and raw outputs remain on Baobab.

This repair supplies no accuracy result. Final output qualification and the complete 14-cell comparison remain pending. Final scoring job 12732389 was updated to wait on both continuation jobs and every other selected cell.

## Second compatibility failure after final masking

At the next live check, 12735632_4 and 12735633_4 had finished final RepeatMasker annotation but failed at merging (exit2). Their cumulative wall times were 8120.870137 and 8786.049792 seconds. The original and continuation artifacts remain preserved.

Two concrete failures were visible in the native logs: `LTR_FINDER_parallel` declared `/usr/bin/perl`, which is absent in the image (the installed interpreter is `/usr/local/bin/perl`), and `rmOutToGFF3.pl` could not find `CrossmatchSearchEngine.pm`. The latter made an empty GFF, causing the subsequent RepeatCraft and R failures. The bundled LTR_FINDER binary itself successfully displayed its native help; invoking the Perl scripts with the existing interpreter/module path passed their syntax checks.

The next copied continuations, 12738271_4 (CB4) and 12738272_4 (sim100), retain final RepeatMasker outputs. Only the LTR_FINDER_parallel shebang and the `PERL5LIB=/usr/local/share/RepeatMasker` environment were repaired. Runtime source patches remain local copies bound into the unchanged image; prior patch application is recognized when resuming its preserved work tree. Logs confirm final masking reached and, for sim100, progression through RepeatCraft to overlap resolution. A subsequent protocol audit, documented below, found that the initial custom library was not present in the final combined library. No biological threshold or model was changed.

All earlier elapsed time remains included in each cell's original 84600-second budget and cumulative wall-time result. The complete step history is retained across continuations. These jobs still require final output qualification; an intermediate successful stage is not a benchmark result.

## Historical native completion; later protocol-invalidated

The final continuations both completed with exit 0 and nonempty, coordinate-qualified canonical outputs. CB4 job `12738271_4` processed all 108,384,165 bp in 367 sequences and produced 164,463 native GFF rows; sim100 job `12738272_4` processed all 100,000,000 bp and produced 35,363 rows. These are output row counts before the common TE/non-TE scoring filter, not measures of accuracy. The later audit found that these completed outputs did not satisfy the intended initial-library protocol, so the historical completion does not qualify the EarlGrey accuracy cells.

Cumulative workflow wall times are 8725.850726 seconds for CB4 and 9014.238390 seconds for sim100, including their failed attempts and copies. The final continuation alone took 604.980589 and 228.188598 seconds, respectively. Both remain within the original 84600-second budget. The corresponding completed status JSON files are included in this directory. Actual method accuracy comparisons wait for the complete benchmark scoring bundle.

## Protocol-fidelity correction

The completed outputs above were subsequently audited for the intended
reference-assisted protocol. In the resumed EarlGrey invocation,
`firstMaskCustomLib` was skipped because the initial `.masked` file already
existed. That function was the only `startCust` path that assigned `RepSub`;
the final `cat $latestFile $RepSub` therefore produced a combined library equal
to the strained de novo library alone. The final RepeatMasker output used
`RND-*` records, while the supplied `lineage.fa` contained the Dfam records.
The original work trees and status files remain unchanged, and the old score is
retained as protocol-invalid for the intended full-library comparison.

`native.py` now applies a source-checked resume patch that restores
`RepSub="$startCust"` before `novoMask`. A bounded recovery driver,
`scripts/experiments/TE-LONG-BENCH-20260915/earlgrey_recovery.py`, copies each
preserved completed work tree in Slurm, removes only final-stage caches, and
reuses the initial mask, database and strained library. It performs `bash -n`
validation on the generated EarlGrey script and accepts the repaired cell only
when the runtime combined library is exactly `strained + lineage.fa` and the
final canonical GFF passes coordinate validation.

Recovery array `12739911` was submitted for CB4 and sim100. Its new outputs are
under `native-12739911/{c_briggsae,sim100}-earlgrey`; final runtime acceptance
and scoring remain pending at submission time.
