# Dossier: RepeatModeler2 2.0.9 + RepeatMasker 4.2.4

- slug: `repeatmodeler2_repeatmasker` · type: sota · added: 2026-08-11
- Links:  repo:https://github.com/Dfam-consortium/RepeatModeler.git
- PDF: refs/pdfs/repeatmodeler2_repeatmasker.pdf (failed(https://pmc.ncbi.nlm.nih.gov/articles/PMC7196820/bin/pnas.1921046117.pdf))
- Repo: refs/repos/repeatmodeler2_repeatmasker/ (cloned @ 14798c7)
- Supplementary: refs/supp/repeatmodeler2_repeatmasker/ (downloaded(2))
- Why relevant: 五工具 end-to-end denominator；官方版本、Dfam/FamDB 和 adapter 合同

## Dataset source
- Smoke uses a generated tiny FASTA only; scientific benchmarking later uses a separately frozen panel.
- RepeatMasker 4.2.4 does not bundle a TE database. Species-based runs require frozen Dfam 4.0/FamDB components; custom-library smoke may use `-lib` without Dfam.
- Dfam data are CC0; any Repbase-derived library is a separate licensed dependency and is excluded from this smoke.

## Metric implementation
- This source is an execution baseline, not a claim metric source. Smoke checks version/help/min-input and conversion to canonical zero-based half-open intervals.
- Scientific evaluator anchor: `/home/users/j/jwang/TE_compare/TE-Benchmark/core/workflow/scripts/`; exact adapter is frozen per experiment.

## Split scheme
- Not applicable to identity smoke. Later comparisons must reuse the same genome/truth tier and cannot random-split homologous TE copies.

## Weights / license
- No learned weights. RepeatModeler 2.0.9 tag commit `14798c73c2c32da17576deac4689a6e586932eb6`; RepeatMasker 4.2.4 source commit `3f49a049c7a7e843b2da1b708fe06bb39c90035b`.
- Both use Open Software License 2.1. Pinned SIF SHA-256: RM2 `93f5801a64dcc8adaec9b3307f188ff5feb65ed8c893764d0e5ab56f75020384`; RM `3a2d62dec0b930fa6a6aa463132976fb8de5405eedd1c4ce122ec7511689cd8c`.

## Reproducibility notes
- Required chain includes BuildDatabase, RepeatModeler, then RepeatMasker. RM2 2.0.9 is coupled to RM 4.2.4/Dfam 4.0-era dependencies; do not mix with historical RM2 2.0.5/RM 4.1.6 outputs.
- Offline run sets `BLAST_USAGE_REPORT=false`. RM2 LTRStruct requires the LTR dependency stack; smoke may explicitly type-block LTRStruct if those identities are absent.

## Relevance to our project
- 五工具 end-to-end denominator；官方版本、Dfam/FamDB 和 adapter 合同
