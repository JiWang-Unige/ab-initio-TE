# Dossier: HiTE 3.3.3

- slug: `hite_3_3_3` · type: sota · added: 2026-08-11
- Links:  repo:https://github.com/CSU-KangHu/HiTE.git
- PDF: refs/pdfs/hite_3_3_3.pdf (downloaded)
- Repo: refs/repos/hite_3_3_3/ (cloned @ f5f2c7f)
- Supplementary: refs/supp/hite_3_3_3/ (downloaded(1))
- Why relevant: 五工具 denominator；冻结官方 v.3.3.3 和 exact commit

## Dataset source
- Official repository contains demo data and the paper benchmarks nine reference assemblies; bounded smoke uses only demo/tiny non-claim input.
- Code is GPL-3.0. External reference genomes retain their own licenses.

## Metric implementation
- Identity smoke checks `main.py -h`, version 3.3.3, minimum launch and deterministic conversion of final annotation/library output.
- Any later accuracy uses the common frozen evaluator, not HiTE's self-reported summary alone.

## Split scheme
- No train/test split for identity smoke. Later evaluation holds out complete genomes/families and reuses one truth tier.

## Weights / license
- Official tag `v.3.3.3`, commit `ae317c879b3d217b419fefa38c6ff2cacbf1695c`, GPL-3.0.
- Official README declares container `kanghu/hite:3.3.3`; no accepted local SIF existed at entry, so acquisition+hash must precede output inspection.

## Reproducibility notes
- Old local `hite.sif` is unpinned 3.0 and rejected. If 3.3.3 acquisition fails, the cell is `FOUNDATIONAL_TYPED_BLOCK`.
- Recommended runtime is CPU-heavy (official guidance 40 CPU/128 GB); bounded smoke must use a tiny input and conservative CPU/memory request.

## Relevance to our project
- 五工具 denominator；冻结官方 v.3.3.3 和 exact commit
