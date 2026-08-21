# SOTA Model Inventory

> 由 /sota-inventory 写。每个链接都用 WebFetch 实际访问过 —— ✅ / ❌ / ⚠️ 是验证状态。

## Summary
- Inventory patch: 2026-08-11, bounded five-workflow benchmark denominator.
- Total candidates: 5 workflows（RepeatModeler2+RepeatMasker 计为一个端到端工作流）
- Trivial-to-reproduce: 0
- Moderate: 3（RM2+RM、EDTA、Earl Grey；均仍需数据库/最小启动 smoke）
- Hard / unknown: 2（HiTE 需新冻结 runtime；TEtrimmer 1.7.4 只有官方 main commit、无 release/container 1.7.4）
- Link verification failures: 2 个 PMC PDF 自动下载失败；论文页面和官方仓库均已验证，见失败源表。

## Candidate models

| Model | Paper | GitHub | Weights | Architecture | Dataset | Metric | Value | Repro | Worth? | Notes |
|---|---|---|---|---|---|---|---:|---|---|---|
| RepeatModeler2 2.0.9 + RepeatMasker 4.2.4 | [✅ PNAS 2020](https://doi.org/10.1073/pnas.1921046117) | [✅ RM2](https://github.com/Dfam-consortium/RepeatModeler/releases/tag/2.0.9) / [✅ RM](https://www.repeatmasker.org/dev/RepeatMasker/) | [✅ pinned SIF candidates](../codex_jobs/E1B-OCI-ACQUIRE-20260809A/evidence/candidate_records.tsv) | de novo family discovery → fixed-library whole-genome masking | tiny non-claim FASTA for smoke; later frozen benchmark panel | invocation/adapter engineering PASS；scientific metrics later | n/a | moderate | yes | freeze RM2 `14798c7`, RM `3f49a04`, Dfam 4.0/FamDB；不得混入旧 2.0.5/4.1.6 results |
| EDTA 2.3.0 | [✅ Genome Biology](https://doi.org/10.1186/s13059-019-1905-y) | [✅ release](https://github.com/oushujun/EDTA/releases/tag/v2.3.0) | [✅ pinned SIF](../codex_jobs/E1B-OCI-ACQUIRE-20260809A/evidence/candidate_records.tsv) | multi-module de novo TE library construction + annotation | official rice test assets / tiny non-claim FASTA | invocation/adapter engineering PASS；scientific metrics later | n/a | moderate | yes | exact tag `a9f7a56`; local legacy EDTA 2.0/2.2 must not substitute |
| Earl Grey 7.3.0 frozen | [✅ MBE 2024](https://doi.org/10.1093/molbev/msae068) | [✅ release](https://github.com/TobyBaril/EarlGrey/releases/tag/v7.3.0) | [✅ pinned SIF](../codex_jobs/E1B2R2-EARLGREY-ACQUIRE-20260809A/evidence/candidate_record.tsv) | RepeatModeler/BEAT/RepeatMasker integrated workflow | bundled test genome / tiny non-claim FASTA | invocation/adapter engineering PASS；scientific metrics later | n/a | moderate | yes | freeze pre-result v7.3.0 SIF; v7.3.1 released 2026-08-11 is recorded but not silently substituted |
| HiTE 3.3.3 | [✅ Nature Communications](https://doi.org/10.1038/s41467-024-49912-8) | [✅ release](https://github.com/CSU-KangHu/HiTE/releases/tag/v.3.3.3) | [⚠️ official container tag](https://hub.docker.com/r/kanghu/hite) | structural, homology, de novo and signature modules with boundary adjustment | bundled demo / tiny non-claim FASTA | invocation/adapter engineering PASS；scientific metrics later | n/a | hard | partial | source commit `ae317c8` verified；no locally accepted 3.3.3 SIF yet，cell fail-closed until acquired and hashed |
| TEtrimmer target 1.7.4 | [✅ Nature Communications](https://doi.org/10.1038/s41467-025-63889-y) | [⚠️ official release-marker commit](https://github.com/qjiangzhao/TEtrimmer/commit/61456873f27b3b97ac2938f1972fc01807d550d1) | [⚠️ dependency SIF is 1.7.2 only](../codex_jobs/E1B-OCI-ACQUIRE-20260809A/evidence/candidate_records.tsv) | automated consensus curation / conditional de novo mode | official test FASTA | invocation/adapter engineering PASS；scientific metrics later | n/a | hard | partial | exact source commit declares 1.7.4 but no 1.7.4 tag/container；must bind this commit or typed-block，never report 1.7.2 as 1.7.4 |

## Model families (refined from /research-synthesize)

### Family A: <名字>
- Members(已验证):
- Core idea:
- Strength on this task:
- Weakness:
- What we can borrow:
- What we should not borrow:

## Baselines to reproduce first

| Priority | Model | Why this one | Required GPU | Required data | Risk | Expected setup time |
|---:|---|---|---|---|---|---|

## Models to skip

| Model | Reason | Could revisit if |
|---|---|---|

## Conflict resolution (from /research-synthesize §8)

| Conflict ID | Resolution | Source |
|---|---|---|

## Link verification status

| URL | Type | Status | Last verified |
|---|---|---|---|
| https://www.repeatmasker.org/dev/ | official release page | ✅ | 2026-08-11 |
| https://github.com/Dfam-consortium/RepeatModeler/releases/tag/2.0.9 | official release | ✅ | 2026-08-11 |
| https://github.com/oushujun/EDTA/releases/tag/v2.3.0 | official release | ✅ | 2026-08-11 |
| https://github.com/TobyBaril/EarlGrey/releases/tag/v7.3.0 | official release | ✅ | 2026-08-11 |
| https://github.com/CSU-KangHu/HiTE/releases/tag/v.3.3.3 | official release | ✅ | 2026-08-11 |
| https://github.com/qjiangzhao/TEtrimmer/releases | official releases | ⚠️ highest tagged release is 1.7.2 | 2026-08-11 |

## 2026-08-11 workflow-family conclusions

- 这五项不是同一个 published-SOTA 表中的完全可比“模型”；它们构成本轮 end-to-end workflow smoke denominator。smoke 只判身份、依赖、数据库、离线启动与 adapter，不判科学优劣。
- TE_Bench 是 evaluator/adapter anchor，不是第六个 end-to-end workflow。MCHelper 不得静默加入 denominator。
- 新 smoke 固定 RM2 2.0.9 + RM 4.2.4、EDTA 2.3.0、Earl Grey 7.3.0。HiTE 3.3.3 与 TEtrimmer 1.7.4 必须先形成可审计 runtime identity，否则单元格 typed-block。
- 历史 Label-A（RepeatMasker 4.2.2 + Dfam 3.9）和旧 de novo runs 保留原版本语义，绝不与本轮 Dfam 4.0 smoke 混算。

## Baselines to reproduce first — 2026-08-11 bounded cohort

| Priority | Model/workflow | Why this one | Required GPU | Required data | Risk | Expected setup time |
|---:|---|---|---:|---|---|---|
| 1 | five-workflow identity/help/min-input smoke | 它本身就是后续 benchmark 的运行地基 | 0 | tiny synthetic FASTA + frozen runtime/database manifests | version/db mismatch | < 4 h CPU allocation |
| 2 | raw/CENTER70/strict/loose/current-postprocess fragmentation comparators | F lattice 的公平基线 | 0 | frozen historical prediction/truth subset | T1/T2 truth only | < 2 h CPU allocation |
| 3 | flat direct-superfamily + k-mer nearest prototype | S open-set 的同 split 基线 | 0-1 | frozen snapshot + family/homology/clade roles | homology leakage | < 4 h allocation |

## ⚠️ 需手动或后续自动补全的源

| slug | 失败项 | 原因 | 影响 |
|---|---|---|---|
| repeatmodeler2_repeatmasker | PMC PDF 自动下载 | NCBI bin URL 返回失败；DOI/PMC 页面和 release tarballs 已验证 | 不阻塞 smoke；阻塞 paper-table 级全文摘录 |
| earlgrey_7_3_1 | PMC PDF 自动下载 | NCBI bin URL 返回失败；论文 DOI、官方 repo 与 release tarball 已验证 | 不阻塞 smoke |
| hite_3_3_3 | accepted local runtime | 只有官方 source/release，旧本地 SIF 是 unpinned 3.0 | 阻塞 HiTE min-input cell，直到 smart-sbatch 内 acquisition+hash 通过 |
| tetrimmer_target_1_7_4 | tagged/container release | 官方 main commit 声明 1.7.4，但 releases/biocontainer 最高 1.7.2 | 必须 source-bind exact commit 或 typed-block；禁止版本替换 |

## Conflict resolution — 2026-08-11

| Conflict ID | Resolution | Source |
|---|---|---|
| AUG-VERSION-EDTA | EDTA 2.3.0 是正式 release；本地旧 2.0/2.2 runtime 不可替代 | official GitHub release + `refs/dossiers/edta_2_3_0.md` |
| AUG-VERSION-HITE | HiTE intended source version 可冻结为 3.3.3；旧 unpinned 3.0 SIF 拒绝 | official GitHub release + `refs/dossiers/hite_3_3_3.md` |
| AUG-VERSION-TETRIMMER | 1.7.4 存在于官方 release-marker source commit，但没有独立 tag/container；1.7.2 只可作依赖 runtime | official repo commit `61456873f...` + `refs/dossiers/tetrimmer_target_1_7_4.md` |
