# Dossier: TEtrimmer target 1.7.4 (official max 1.7.2)

- slug: `tetrimmer_target_1_7_4` · type: sota · added: 2026-08-11
- Links:  repo:https://github.com/qjiangzhao/TEtrimmer.git
- PDF: refs/pdfs/tetrimmer_target_1_7_4.pdf (downloaded)
- Repo: refs/repos/tetrimmer_target_1_7_4/ (cloned @ 8954274)
- Supplementary: refs/supp/tetrimmer_target_1_7_4/ (downloaded(1))
- Why relevant: conditional fifth workflow；目标 1.7.4 当前不存在，记录 typed block，1.7.2 仅用于身份审计不得替代

## Dataset source
- Official repository provides `tests/test_input.fa` and `tests/test_genome.fa`; these are the only minimum-input smoke assets.
- Optional PFAM data must be local/frozen for offline domain annotation; no automatic network download is accepted as reproducible runtime evidence.

## Metric implementation
- Conditional workflow produces curated consensus libraries and optional RepeatMasker annotation. Smoke checks version/help/minimum launch and adapter schema only.
- It is not a sixth independent discovery denominator when merely postprocessing another workflow; provenance must name its upstream library.

## Split scheme
- Not applicable to identity smoke. Later use must keep upstream library/genome unit fixed and cannot compare postprocessed output against an unmatched denominator.

## Weights / license
- Official release-marker commit `61456873f27b3b97ac2938f1972fc01807d550d1` declares `TEtrimmer_version = "1.7.4"`; GPL-3.0. Frozen source tarball SHA-256: `3ac444549eeffb372d9fdff9af2ccb78e6a9fed9dd00aef20d42c8f165807edc`.
- Available dependency SIF is tagged 1.7.2, SHA-256 `38c0c325731cd40eb234056b981ef9ed940bc381ac703ab13fa867a086d5b612`. It may host dependencies only when exact 1.7.4 source is bind-mounted and its source hash is recorded; it cannot be reported as a native 1.7.4 image.

## Reproducibility notes
- GitHub releases/tags currently stop at v1.7.2 even though official commit `61456873f...` is labeled “released 1.7.4”. This is an explicit provenance warning, not permission to substitute versions or use later mutable main.
- If source-binding fails version/help/min-input validation, record `FOUNDATIONAL_TYPED_BLOCK` and retain evidence.

## Relevance to our project
- conditional fifth workflow；目标 1.7.4 当前不存在，记录 typed block，1.7.2 仅用于身份审计不得替代
