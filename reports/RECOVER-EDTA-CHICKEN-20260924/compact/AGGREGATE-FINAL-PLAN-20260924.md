# EDTA raw aggregation follow-up

The Helitron continuation `13189902` produced native Helitron FASTA/GFF/BED
artifacts and completed the filter stage, but its filter stderr reports:

```text
cp: cannot stat '../galGal6.fa.mod.EDTA.raw/galGal6.fa.mod.EDTA.intact.raw.gff3': No such file or directory
```

This is a real EDTA pipeline boundary.  `EDTA.pl` lines 516–520 in the pinned
2.3.0 source create the missing raw aggregate only in the `ALL` path:

1. concatenate LTR/TIR/Helitron intact FASTAs;
2. convert TIR+Helitron BED with the native `bed2gff.pl - TE_struc`;
3. append the LTR intact GFF and apply the native stable sort.

The filter-stage `galGal6.fa.mod.EDTA.combine/galGal6.fa.mod.EDTA.fa.stg1`
and `galGal6.fa.mod.EDTA.intact.fa.cln` are present and reusable.  The
partial `EDTA.final` and annotation directories are deliberately excluded.
The prepared `continue_aggregate_final.py` copies only the raw tree and these
combine artifacts to a fresh output, executes the exact native aggregation in
the pinned container, then runs:

```text
EDTA.pl --step final --overwrite 0 --sensitive 1 --anno 1 --threads 16
```

That EDTA 2.3.0 entry naturally falls through FINAL and ANNO.  No TIR,
Helitron, or filter rerun is planned.  Root stopped `13189902` after 3,255
Slurm seconds once the missing aggregate was confirmed; its raw and
filter-combine outputs and failure logs remain preserved.  The seven-day cell
therefore has 431,681 seconds remaining.  The prepared repair is now submitted
as `13190938` with `afterany:13189902`, a 431,681-second budget, and fresh
output `EDTA-aggregate-final-13190938`.  It remains an engineering recovery
until the native final/annotation gates and summary pass; the cancelled
continuation output remains untouched.

Static checks passed locally and on Baobab (`py_compile`, `bash -n`, and the
read-only prior-input gate).  The gate confirms M4/S7/TIR and Helitron inputs,
the filter stage-1/combine files, and absence of the aggregate GFF.
