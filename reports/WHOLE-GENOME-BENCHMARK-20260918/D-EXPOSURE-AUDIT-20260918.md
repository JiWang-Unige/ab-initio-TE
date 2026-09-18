# D checkpoint exposure audit

Protocol: `WHOLE-GENOME-BENCHMARK-20260918`.

The D-independent stratum was fixed from the actual six-species materialization
before any whole-genome score was read. The source manifests are:

- `/home/users/j/jwang/ab-initio-TE/outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202/TRAIN/{species}.jsonl.gz`
- `/home/users/j/jwang/ab-initio-TE/outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202/CAL/{species}.jsonl.gz`
- `/home/users/j/jwang/ab-initio-TE/outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202/DEV/{species}.jsonl.gz`

Each JSONL record supplies `chrom`, `start`, and `end` for a 4,096-bp
training/evaluation half. The observed records for the benchmark species were:

| species | split | records | observed chromosomes | observed coordinate envelope (bp) |
|---|---|---:|---|---|
| chicken | TRAIN | 3,000 | chr2, chr3, chr4, chr7, chr8 | chr2 90,112–149,356,544; chr3 548,864–110,755,840; chr4 385,024–91,217,920; chr7 335,872–36,544,512; chr8 212,992–30,081,024 |
| chicken | CAL | 1,000 | chr1, chr5, chr6 | chr1 3,194,880–197,386,240; chr5 3,153,920–59,162,624; chr6 2,228,224–36,192,256 |
| chicken | DEV | 1,000 | chr1, chr5, chr6 | chr1 106,496–197,132,288; chr5 114,688–59,768,832; chr6 1,097,728–32,440,320 |
| zebrafish | TRAIN | 3,000 | chr1, chr3, chr4, chr7, chr9 | chr1 811,008–59,572,224; chr3 49,152–61,669,376; chr4 131,072–77,799,424; chr7 221,184–74,219,520; chr9 106,496–55,779,328 |
| zebrafish | CAL | 1,000 | chr2, chr5, chr6 | chr2 1,703,936–59,547,648; chr5 1,187,840–72,335,360; chr6 2,170,880–60,088,320 |
| zebrafish | DEV | 1,000 | chr2, chr5, chr6 | chr2 139,264–58,441,728; chr5 65,536–69,943,296; chr6 335,872–59,613,184 |

The fixed D-independent chromosome set is chicken `chr10` and `chr20`, and
zebrafish `chr10` and `chr20`. Neither set occurs in any TRAIN, CAL, or DEV
manifest for its species. This chromosome-level exclusion is conservative for
the records observed in the manifests; it cannot rule out homologous sequence
exposure or other historical leakage, which remains a stated caveat.

The pair was fixed before any native output or score was inspected because both
chromosomes are present primary assembly records, have non-trivial lengths in
the frozen FASTA, and are absent from the audited exposure sets. No chromosome
was chosen by model performance or comparator label density.

The older SF5 chromosome split is retained only for retrospective stratification
and is never used as the D-independent test definition. Native EDTA/RM2
discovery and timing still receive the complete assembly. The D arm is binary
material inference, so class/family is N/A for D; native Unknown labels remain
in the audit rather than being dropped.
