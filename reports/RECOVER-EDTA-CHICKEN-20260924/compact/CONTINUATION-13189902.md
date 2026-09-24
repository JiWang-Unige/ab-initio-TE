# EDTA Helitron continuation — job 13189902

Status at this record: **RUNNING** on `gpu035` in `private-teodoro-gpu`
(16 CPU, 128 GB, no GPU).  The output root is
`outputs/RECOVER-EDTA-CHICKEN-20260924/native/chicken/EDTA-helitron-cont-13189902`.

The preserved source retry `13189201` is terminally failed after 2,669 Slurm
seconds, but its TIR resume completed with return code 0 and recorded the
frozen Module 4/Step 7 checkpoint load.  Its filter failed with return code 2
because the native Helitron raw FASTA was absent, followed by the missing
stage-1 library.  The source tree still has the non-empty LTR/SINE/LINE/TIR
raw artifacts, RM2 raw library, and checkpoint; no Helitron file is present.

The continuation copies that tree to a fresh writable root and runs exactly
these native stages:

```text
EDTA_raw.pl --type helitron --overwrite 0 --species others --threads 16
EDTA.pl --step filter --overwrite 0 --sensitive 1 --anno 1 --threads 16
```

The EDTA 2.3.0 `--step filter` entry falls through the native `FINAL` and
`ANNO` labels, so the second command is the complete filter→final→annotation
cascade.  TIR is not rerun.  The continuation does not use `--force`, does not
create an empty Helitron file, and does not write to the preserved retry.  The
remaining seven-day cell budget at submission was 434,936 seconds after
charging the prior recovery's 2,669 seconds.  Terminal success still requires
native `annotation.gff3`, `library.fasta`, sequence-ID decoding, and the
frozen `annotation_summary.json` adapter.
