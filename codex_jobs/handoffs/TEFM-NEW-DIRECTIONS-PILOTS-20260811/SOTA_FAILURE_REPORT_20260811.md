### SOTA source failure report
以下项目需要用户手动帮助或后续重试（PDF/补充材料/仓库/权重）：

| Kind | Source | Failure | URL(s) |
|---|---|---|---|
| pdf | docs/02_sota_model_inventory.md:11 | - Link verification failures: 2 个 PMC PDF 自动下载失败；论文页面和官方仓库均已验证，见失败源表。 | - |
| unknown | docs/02_sota_model_inventory.md:76 | \| slug \| 失败项 \| 原因 \| 影响 \| | - |
| pdf | docs/02_sota_model_inventory.md:78 | \| repeatmodeler2_repeatmasker \| PMC PDF 自动下载 \| NCBI bin URL 返回失败；DOI/PMC 页面和 release tarballs 已验证 \| 不阻塞 smoke；阻塞 paper-table 级全文摘录 \| | - |
| pdf | docs/02_sota_model_inventory.md:79 | \| earlgrey_7_3_1 \| PMC PDF 自动下载 \| NCBI bin URL 返回失败；论文 DOI、官方 repo 与 release tarball 已验证 \| 不阻塞 smoke \| | - |
| pdf | refs/sources.md:7 | \| repeatmodeler2_repeatmasker \| RepeatModeler2 2.0.9 + RepeatMasker 4.2.4 \| sota \| failed(https://pmc.ncbi.nlm.nih.gov/articles/PMC7196820/bin/pnas.1921046117.pdf) \| cloned \| dossiers/repeatmodeler2_repeatmasker.md \| archive_source \| 2026-08-11 \| | https://pmc.ncbi.nlm.nih.gov/articles/PMC7196820/bin/pnas.1921046117.pdf |
| pdf | refs/sources.md:9 | \| earlgrey_7_3_1 \| Earl Grey 7.3.1 \| sota \| failed(https://pmc.ncbi.nlm.nih.gov/articles/PMC11003543/bin/vead101.pdf) \| cloned \| dossiers/earlgrey_7_3_1.md \| archive_source \| 2026-08-11 \| | https://pmc.ncbi.nlm.nih.gov/articles/PMC11003543/bin/vead101.pdf |
| pdf | refs/dossiers/earlgrey_7_3_1.md:5 | - PDF: refs/pdfs/earlgrey_7_3_1.pdf (failed(https://pmc.ncbi.nlm.nih.gov/articles/PMC11003543/bin/vead101.pdf)) | https://pmc.ncbi.nlm.nih.gov/articles/PMC11003543/bin/vead101.pdf |
| unknown | refs/dossiers/edta_2_3_0.md:17 | - Smoke adapter must canonicalize EDTA GFF3 coordinates and record empty/missing outputs fail-closed. | - |
| unknown | refs/dossiers/edta_2_3_0.md:24 | - Pinned Biocontainer SIF SHA-256 `812f277d85d575ba745c08ff2a3876d36aeb8fc0e0a08d95db28404b3837f40e`. | - |
| pdf | refs/dossiers/repeatmodeler2_repeatmasker.md:5 | - PDF: refs/pdfs/repeatmodeler2_repeatmasker.pdf (failed(https://pmc.ncbi.nlm.nih.gov/articles/PMC7196820/bin/pnas.1921046117.pdf)) | https://pmc.ncbi.nlm.nih.gov/articles/PMC7196820/bin/pnas.1921046117.pdf |
| unknown | refs/dossiers/sf_target_set.md:33 | The final table must be propagated to: | - |

处理：能手动下载的文件放入 `refs/pdfs/<slug>.pdf` 或 `refs/supp/<slug>/`，私有/大仓库放 `refs/repos/<slug>.link.md` 写清位置，然后重新跑 /sota-inventory 的 verification update。
