# Execution scripts

These scripts read the frozen platypus preparation in the Baobab research
checkout and write under `outputs/PLATYPUS-STRONG-MASK-CONTROLS-20260917`.

Run `run_mask_panel.py RED` or `run_mask_panel.py RM2` once for the complete
20-contig, 104-Mb core-plus-halo panel. RM2 discovers one shared library;
it does not discover a separate library for each 5.2-Mb input. Each native
mask is then separated into twenty sequence-preserving inputs for
`run_tiberius_core.py`. Only run `score.py` after all forty receiver cells
complete. Gene endpoints use the fixed 100-Mb cores and 639 reference loci;
mask-coverage counts include halos and therefore use 104 Mb.

The submitted dependencies, failed attempts and resource changes are recorded
in `reports/PLATYPUS-STRONG-MASK-CONTROLS-20260917/`.
