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
