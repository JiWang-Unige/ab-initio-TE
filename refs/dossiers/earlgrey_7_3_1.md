# Dossier: Earl Grey 7.3.1

- slug: `earlgrey_7_3_1` · type: sota · added: 2026-08-11
- Links:  repo:https://github.com/TobyBaril/EarlGrey.git
- PDF: refs/pdfs/earlgrey_7_3_1.pdf (failed(https://pmc.ncbi.nlm.nih.gov/articles/PMC11003543/bin/vead101.pdf))
- Repo: refs/repos/earlgrey_7_3_1/ (cloned @ 9b71694)
- Supplementary: refs/supp/earlgrey_7_3_1/ (downloaded(1))
- Why relevant: 五工具 denominator；冻结 2026-08-11 官方 release

## Dataset source
- Earl Grey ships a test genome/expected summary assets. This cohort freezes the already acquired v7.3.0 SIF before results; v7.3.1 is archived only as the current official source update.
- v7.3.x requires Dfam 4.0 through FamDB and selected partitions must be frozen because they affect outputs.

## Metric implementation
- Identity smoke checks version/help/min-input and canonical adapter output only. Scientific comparison is deferred to the common TE_Benchmark evaluator.

## Split scheme
- Not applicable to smoke; later workflow comparison is genome-level with one frozen input/truth tier.

## Weights / license
- Frozen benchmark candidate is v7.3.0 commit `828d6978a0b649f64df7ac1630022b50d0adcc20`; SIF SHA-256 `60bed858ec262243ce3f0e4a12209f805e6029c18346f48d030f78de6445335d`.
- Repo license is OSL-2.1. v7.3.1 source commit `9b716949f65ea75c04af71c34bf358cef246a217` is not silently substituted.

## Reproducibility notes
- Dfam 4.0 is external and not preconfigured in the frozen SIF. First-run helper output alone is not a successful scientific launch.
- Existing Dfam 3.9 configured image is mutable/rejected and cannot satisfy this cohort.

## Relevance to our project
- 五工具 denominator；冻结 2026-08-11 官方 release
