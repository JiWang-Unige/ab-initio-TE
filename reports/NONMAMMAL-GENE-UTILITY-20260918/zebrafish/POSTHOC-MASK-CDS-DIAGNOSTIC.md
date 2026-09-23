# Zebrafish post-hoc mask–CDS diagnostic

This diagnostic was run after the frozen four-arm AUGUSTUS utility score. It
reads the existing fixed geometry, complete protein-coding reference isoforms,
and the four existing masked FASTAs; it does not rerun AUGUSTUS, change a mask,
or alter the locus-level score. The CPU job was `12899904` (private partition,
1 CPU, 8 GB, 18 s, exit 0).

The ten fixed 5-Mb cores contain a merged CDS union of 1,845,174 bp. The
corresponding core masking totals are:

| arm | masked core bp | masked core | masked CDS bp | masked CDS fraction |
|---|---:|---:|---:|---:|
| U | 0 | 0.0000% | 0 | 0.0000% |
| D | 23,269,086 | 46.5382% | 25,830 | 1.3999% |
| R_TE | 20,196,539 | 40.3931% | 15,464 | 0.8381% |
| RED | 19,547,753 | 39.0955% | 77,267 | 4.1875% |

The native prediction inputs include 100-kb halos. Across the 52-Mb inputs,
D/R_TE/RED mask 24,249,297 / 21,021,267 / 20,349,038 bp, respectively
(46.6333% / 40.4255% / 39.1328%); U masks 0 bp.

RED overlaps roughly three times as much reference CDS as D (77,267 versus
25,830 bp; 4.19% versus 1.40%), so genic masking is compatible with part of
RED's lower F1. Total masked sequence is lower for RED than D, however. The
lower RED score therefore cannot be described as a simple consequence of total
masked-bp intensity; the diagnostic supports a composition/genic-overlap
explanation and does not establish causality. R_TE overlaps less CDS than D,
while D still has a modest positive F1 difference over R_TE, so the learned
mask's utility is not determined by CDS overlap alone.

The diagnostic is a panel-level mechanism readout. It does not convert this
AUGUSTUS experiment into a Tiberius result, and it does not establish
whole-genome or unseen-species generalization.
