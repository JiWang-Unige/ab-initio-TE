# Nonmammalian gene utility: chicken complete, zebrafish pending

Preparation, reference construction, same-letter mask inputs, and the native
receiver mechanism have completed. The chicken scientific utility result is
now complete. The zebrafish first core has completed; array tasks 1 and 2
are running and the remaining cores and final score are still pending.

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

Chicken fixed-D masks completed as job `12889043` in 14m57s (10/10
records, 52 Mb including halos). The native mask manifest is archived as
`chicken/D_mask.json`. All ten chicken prediction cells and score
`12889062` completed successfully. The compact result is in
`chicken/RESULTS.md` and `chicken/compact-result.json`: U/D/R_TE/RED F1 values
are 0.247788/0.260989/0.266114/0.039100, respectively, with 1,064 reference
loci. D−U is +0.013201 F1 (chromosome-bootstrap 95% interval
[0.005109, 0.025163]); D−R_TE is −0.005125 ([-0.010349, −0.001594]); and
D−RED is +0.221889 ([0.189399, 0.248788]). The interval is a ten-chromosome
sensitivity interval, not biological-replicate uncertainty. This supports a
modest D-mask benefit over unmasked chicken sequence and does not support
superiority to the same-assembly historical TE mask.

The fixed-input masking diagnostic also merged CDS intervals from the
complete protein-coding chicken reference isoforms (2,034,021 bp) before
intersecting masks. D/R_TE/RED masked 283 / 1,192 / 1,023,600 CDS bp
respectively (0.0139% / 0.0586% / 50.3240%). This is consistent with RED's
low F1 and supports overmasking as an explanation on this panel; it does not
isolate the causal contribution of masking. The per-core JSON and method note
are in
`chicken/posthoc-mask-cds-diagnostic.json` and
`chicken/POSTHOC-MASK-CDS-DIAGNOSTIC.md`; the primary result and total-mask
fractions are in `chicken/RESULTS.md`.

Zebrafish first core `12889049_0` completed cleanly; at the latest snapshot
`12889054_1/_2` were running and `12889054_3-9` remained queued by the array
limit. Score `12889063` remains dependency-gated on the remaining cells. No
zebrafish utility result is reported until all ten cells and all four arms
pass the score gate.
