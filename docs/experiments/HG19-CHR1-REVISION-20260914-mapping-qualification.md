# hg19 to CHM13v2 mapping qualification appendix

This is a bounded coordinate qualification stage after formal EVAL job
`12696405` (`afterok:12696405`). It consumes only
`old_confusion_intervals.bed` from the frozen old hg19 evaluation and the two
existing reciprocal chain files:

- source intervals: `outputs/HG19-CHR1-REVISION-20260914/eval-full-12696405/old_confusion_intervals.bed`
- forward chain: `outputs/ANNOTATION-REVISION-20260914/chm13-assets-12695221/hg19-chm13v2.chain`
- reverse chain: `outputs/ANNOTATION-REVISION-20260914/chm13-assets-12695221/chm13v2-hg19.chain`

Only source and target chromosomes `chr2`, `chr3`, and `chr4` are in scope.
Rows on `chr16`, `chr18`, or `chr19`–`chr22` and mapped destinations outside
the target panel are retained as out-of-scope outcomes and are not silently
discarded. Every TP/FP/FN/TN source interval is retained. The mapping stage
does not read CHM13 annotations and does not compute F1, FP rescue, or an
annotation revision claim.

The production command uses the official UCSC Linux `liftOver` executable
([source URL](https://hgdownload.soe.ucsc.edu/admin/exe/linux.x86_64/liftOver))
with `-bedPlus=6`, `-multiple`, and `-minMatch=0.95`. The Slurm wrapper
downloads it into the project `software/ucsc/` directory when absent and
records the source URL and tool probe in the output summary. The source and
reverse mapping output files retain every mapped and unmapped destination.

An interval is qualified only if it has exactly one forward destination,
exactly one reverse destination returning the original source interval, equal
source/target interval lengths, and an in-scope target chromosome. Ambiguous,
unmapped, non-reciprocal, target-out-of-scope, and length-changing mappings
remain separate statuses. Length-changing mappings are never treated as
same-coordinate base-level evidence. Equal span alone also does not guarantee
an internal base-by-base bijection because chain blocks may contain internal
indels.

The local independent synthetic regression checks a small reciprocal
coordinate block, a length-changing mapping, ambiguous and unmapped
destinations, and a reciprocal destination outside the target panel. The
initial CLI smoke `12705496` exposed and retained a reversed synthetic-chain
fixture; it did not read formal EVAL data. After correcting the fixture to the
production chain orientation, the
official-binary CLI smoke `12705600` also passed on Baobab: `-bedPlus=6`
preserved both identity columns, plus-strand `chr2:10-20` mapped to
`chr2:60-70` and back, production-style dot-strand `chr2:20-30` mapped to
`chr2:70-80` and back with strand `.` retained, and a minus-strand
`chr3:0-100` mapped to `chr3:10-110` and back with output strand `-`. The
qualification job `12705502` subsequently completed in 10 seconds after
formal evaluation `12696405` completed. Of 97,242 source intervals, 93,116
were unique, reciprocal, and the same length (17,120,893 source bp).
For old-comparator FP intervals, 21,235 of 21,402 qualified. All other
mapping outcomes are retained in the compact
[summary](../../reports/HG19-CHR1-REVISION-20260914/mapping-qualification-12705502/summary.json).
No target annotation was read in this job; mapping qualification alone
does not demonstrate TE support or justify a same-base F1 recalculation.
