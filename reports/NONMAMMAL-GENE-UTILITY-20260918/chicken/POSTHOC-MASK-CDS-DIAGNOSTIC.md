# Chicken mask overlap with reference CDS

This is a post-hoc diagnostic on the already completed chicken inputs. It
does not change the gene-locus denominator, predictions, bootstrap intervals,
or any mask. For each of the ten fixed 5-Mb cores, CDS intervals from the
complete protein-coding reference isoforms were merged before counting
overlap, so alternative isoforms do not duplicate coding bases. Lowercase
positions in each existing arm FASTA were intersected with that merged CDS
union.

The ten cores contain 2,034,021 merged CDS bases. The same 50,000,000 core bp
were supplied to every arm; the total 52-Mb halo input is used for the overall
masking fractions reported in `RESULTS.md`.

| arm | masked bp in 50-Mb core | core fraction | masked CDS bp | fraction of merged CDS |
| --- | ---: | ---: | ---: | ---: |
| U | 0 | 0.0000% | 0 | 0.0000% |
| D | 677,650 | 1.3553% | 283 | 0.0139% |
| R_TE | 2,091,349 | 4.1827% | 1,192 | 0.0586% |
| RED | 33,081,990 | 66.1640% | 1,023,600 | 50.3240% |

The learned D mask and the historical TE mask remove very little of the
merged reference coding sequence on this panel, whereas the all-repeat RED
mask removes about half. These relative masking levels are consistent with
RED's low gene recall/F1 and support overmasking as an explanation on this
fixed panel; they do not isolate the causal contribution of masking from the
other differences between arms. This is a diagnostic of these inputs and
does not establish that every lowercase base is biologically TE or that the
masking pattern generalizes to other assemblies.

The machine-readable output is
`posthoc-mask-cds-diagnostic.json`, including per-core merged CDS and overlap
counts.

The executable analysis is
`scripts/experiments/NONMAMMAL-GENE-UTILITY-20260918/diagnose_mask_cds.py`;
it reads the existing geometry, reference, and arm FASTAs without rerunning
the predictor or changing the primary scores.
