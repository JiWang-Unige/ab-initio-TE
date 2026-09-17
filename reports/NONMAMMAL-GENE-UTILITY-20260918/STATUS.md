# Nonmammalian gene utility: preparation and native mechanism complete

The scientific utility result is **pending**. Preparation, reference construction,
same-letter mask inputs, and the native receiver mechanism have completed.

| species | exact assembly | core bp | input with halos | complete CDS loci | D TRAIN/CAL overlap |
| --- | --- | ---: | ---: | ---: | ---: |
| chicken | galGal6 | 50,000,000 | 52,000,000 | 1,064 | 0 bp |
| zebrafish | danRer11 | 50,000,000 | 52,000,000 | 984 | 0 bp |

Both are D-supervision species, and AUGUSTUS uses existing same-species
parameters. This is nonmammalian use by a second gene predictor, not unseen
species generalization and not a Tiberius result.

The controlled 100 kb native check lowercased only bases 1001–1200. AUGUSTUS
3.5.0 printed one `softmask / nep` hint with these exact inclusive coordinates
and a 1.15 repeat bonus; uppercase input printed none. `nep` is its native
abbreviation for nonexonpart. The native commands completed successfully in
jobs 12888535/36; the first wrapper lookup expected the unabbreviated feature
name and failed its observation check. Assessment-only jobs 12888731/32
verified the existing native outputs without rerunning predictions. The
earlier GFF3 hint-display conflict and reference-locus preparation failures
remain recorded in the experiment document. No utility prediction was used to
change geometry, gene units or gene parameters.

| stage | chicken | zebrafish |
| --- | ---: | ---: |
| successful preparation | 12888444 | 12888445 |
| native mechanism assessment | 12888731 | 12888732 |
| fixed D masks | 12889043 | 12889047 |
| first complete four-arm core | 12889048_0 | 12889049_0 |
| other nine cores, concurrency 2/species | 12889053 | 12889054 |
| complete-denominator score | 12889062 | 12889063 |

All new jobs use `private-teodoro-gpu`, and only the D mask stage requests a
GPU. D masks run sequentially before the finite LoRA/class GPU lane, allowing
CPU-only AUGUSTUS to continue in parallel. Each native prediction cell is one
CPU/8 GB, with four arms U/D/R_TE/RED. Final scoring requires every cell.

`jobs.jsonl` retains the full submission ledger. The geometry, reference
contracts and native mechanism results are exported alongside this status.
Slurm scheduling snapshots are not a promised completion time. At submission,
the available private GPU node's host-memory reservations were almost full
with the standardized 128 GB native benchmark cells; these jobs were preserved
rather than restarted to change resource requests.
