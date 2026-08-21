# Dossier: EDTA 2.3.0

- slug: `edta_2_3_0` · type: sota · added: 2026-08-11
- Links:  repo:https://github.com/oushujun/EDTA.git
- PDF: refs/pdfs/edta_2_3_0.pdf (downloaded)
- Repo: refs/repos/edta_2_3_0/ (cloned @ ac68654)
- Supplementary: refs/supp/edta_2_3_0/ (downloaded(1))
- Why relevant: 五工具 denominator；冻结 v2.3.0，阻止本地 v2.2 结果混入

## Dataset source
- Official repo includes a rice test genome/library; bounded smoke may instead use a deterministic tiny FASTA and must label it non-scientific.
- EDTA output includes a non-redundant TE library and, with `--anno 1`, GFF3 whole-genome annotation.
- Repo/code GPL-3.0; input genome licensing is recorded per experiment.

## Metric implementation
- Official `lib-test.py` compares a library-derived RepeatMasker annotation to a reference annotation; not used for claims in identity smoke.
- Smoke adapter must canonicalize EDTA GFF3 coordinates and record empty/missing outputs fail-closed.

## Split scheme
- Not applicable to tool identity smoke. Later evaluation uses genome-level frozen units and identical truth tiers across workflows.

## Weights / license
- Release `v2.3.0`, commit `a9f7a56d6a1c1a9cdcf2a1d7b8c27a74a38dbfc2`, GPL-3.0.
- Pinned Biocontainer SIF SHA-256 `812f277d85d575ba745c08ff2a3876d36aeb8fc0e0a08d95db28404b3837f40e`.

## Reproducibility notes
- Exact container invocation: `EDTA.pl --genome genome.fa ...`; do not build the released repo's legacy `EDTA_2.2.x.yml` and then accidentally invoke EDTA 2.2.2 from PATH.
- Soft links/absolute paths can behave differently in the official container; bind/copy rules and command identity must be in the run manifest.

## Relevance to our project
- 五工具 denominator；冻结 v2.3.0，阻止本地 v2.2 结果混入
