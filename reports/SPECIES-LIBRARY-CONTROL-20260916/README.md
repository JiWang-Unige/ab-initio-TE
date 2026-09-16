# Three-species library diagnostic — execution record

2026-09-16. Retrospective zebrafish/pig/chicken original DEV; [fixed protocol](../../docs/experiments/SPECIES-LIBRARY-CONTROL-20260916.md).

Preparation 12743578 completed in 3m58s. All 500 centres per species match the original materialized input. Curated/combined consensus records are 1966/1966, 784/3831 and 218/395; curated sequences are unchanged subsets. Zebrafish exports are identical. The [preparation record](preparation/complete-12743578.json) contains the actual TRAIN/CAL/DEV positive exposure and source paths. These counts do not measure completeness.

Fixed-D replay 12743579, all six annotation cells 12743580_[0-5], and dependent score 12743581 have reached Slurm COMPLETED. Replay took 5m13s and score 2m53s, both exit0. After an intermittent SSH outage, all compact outputs were retrieved. Historical counts, all six native denominators and local tile aggregation/transitions passed qualification. The finite experiment is complete; [scientific interpretation](RESULTS.md) and [qualification](compact-qualification.json) are available. See [job mapping](jobs.json). Raw FASTA, predictions and native annotations remain on Baobab under outputs/SPECIES-LIBRARY-CONTROL-20260916/run-r1.

The original evaluator saved only aggregate metrics. Replay reproduced original TP/FP/FN/callable exactly, with no refit. It cannot demonstrate original per-position identity without the missing historical cache. Two focused local tests passed for nonzero-origin RM/core coordinate clipping, overlapping classes and exhaustive confusion transitions. The score stage additionally checks original raw-label reproduction, native complete query denominators and the identical-library control.

10:32 UTC Slurm update: native cells 0/1/2/4/5 completed exit0 with complete.json; only pig combined (index3) remains running. D replay still waits for GPU resources. Aggregate scientific scoring remains pending.

11:16 UTC Slurm update: all six native annotation cells completed exit0; pig combined took 9m41s. Replay12743579 remains pending resources and score12743581 dependency pending. A subsequent SSH connection was refused before compact native qualification could be retrieved; no scientific scoring or full qualification is claimed from Slurm alone. No duplicate job was submitted.

2026-09-16 20:24 UTC: retrieval and qualification complete. Pig F1 changed 0.857443→0.648572 and chicken 0.827195→0.539633 between the two controlled library arms; zebrafish stayed 0.927805 with identical libraries. Added reference-positive detection was 6.96% and 8.01% in pig/chicken. Added FP support and many additional comparator misses coexist; no biological relabelling or corrected historical F1 is claimed. The earlier connection and job states below the current summary are historical records.
