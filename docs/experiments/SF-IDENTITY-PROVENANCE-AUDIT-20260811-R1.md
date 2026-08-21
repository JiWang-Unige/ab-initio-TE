---
exp_id: SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1
date: 2026-08-11
approach_family: data-identity-audit
parent_exp: SF-DIRECT-BASELINE-SCREEN-20260811-R2
motivated_by: "S0 DATA Job 11523252 exposed unresolved Dfam identity; Job 11523938 exposed a partition-layout assumption"
track: S0-prerequisite
profile: smoke
status: done
primary_metric: unique_provenance_coverage
value: 0.9583766909469302
vs_anchor: "-0.0416233091 vs required 1.0 identity coverage"
one_liner: "Exact Dfam provenance audit: 6447/6727 unique, human-gated typed block"
---

# SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1

## Job 11524255 repair-only retry result

- Slurm `COMPLETED 0:0` in `00:18:32`; 4 CPU/32 GiB/0 GPU; fresh independent code review PASS.
- Terminal state: `IDENTITY_PROVENANCE_TYPED_BLOCK`, `semantic_success=true`, `valid_negative=true`, claim-ineligible.
- Audited 35,616,746 annotation records. Exact Dfam name/accession provenance uniquely resolves 6,447/6,727 P identifiers (`0.9583766909`); 279 are missing and `X13_LINE` is ambiguous between two exact candidates.
- The label-contract audit retains 43,728 excluded candidate records across 10 identifiers separately; P + excluded occurrence conservation delta is zero and no positive identifier was deleted.
- The largest missing identifiers are frequent mammalian families, so this cannot be repaired by silent filtering. A human-gated identity/homology and label-exclusion decision is required before any new DATA materialization.
- No split, clustering, training, inference, calibration, GPU work or S1 execution occurred. Route-level `validate_goal` remains `failed_run` only because the required S0 model metric was intentionally not produced.
- Canonical output manifest 7/7 and payload manifest 5/5 independently rehash; evidence is under `outputs/SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1/preview/attempts/audit-slurm-11524255/`.

## Tri-review and decision

- Three independent external CLI reviewers completed a 3/3 quorum. All treat the run as a valid asset-level negative, not a model metric or failed audit.
- All three block S0 DATA/GPU and hierarchical S1 because exact name/accession identity does not cover the intended split universe.
- Claude favors replacing the exact-only component with a frozen sequence-homology supplement; Antigravity prefers exhausting a curated static exact-alias contract first; Codex requires the human-gated decision package to cover both options and all unresolved/excluded cases.
- Pivot: `comparability audit first`. No implementation or compute follows until a human selects one identity contract and explicitly decides `X13_LINE` and the 10 excluded identifiers.
- Raw reviews: `reports/tefm_new_directions/TEFM-NEW-DIRECTIONS-PILOTS-20260811/s0_identity_valid_negative_tri_review/`.

## Job 11523938 failed-run result

- Formal CPU audit (4 CPU/32 GiB/0 GPU) ended `AUDIT_FAILED` after about 2m07s; 14/14 allocation tests passed first.
- The real Dfam sweep exposed an implementation assumption: partition `dfam39_full.3.h5` has no `Lookup/ByName`, so direct leaf `get_family_by_name()` raised `KeyError`. This is not an unresolved-family result and not a valid-negative provenance result.
- Canonical failure manifest verifies; `semantic_success=false`, `validate_goal=failed_run`. No identifier/provenance table was promoted.
- No immediate retry is authorized. A repair must narrowly recognize a structurally absent name index, retain corruption failures, add a real partition-layout regression and pass fresh review after tri-review/pivot.
- 3/3 external CLI tri-review unanimously selected `run-sanity-check-first`. Pivot authorizes only that narrow repair and at most one fresh-reviewed CPU retry; broad exception swallowing, denominator changes, split/cluster/train/GPU/S1 remain prohibited.

## 问题与边界

本 CPU-only asset audit 只回答一个问题：PRE-S0 canonical annotation 中每个 P-state `RepeatMasker repeat_name`，是否都能通过现有合同获得 100% 唯一、可哈希的 Dfam 3.9 provenance。

它不删除正例、不建 split、不聚类、不训练，也不依据前缀猜测 identity。若现有合同不足，终态为 `IDENTITY_PROVENANCE_TYPED_BLOCK`，要求人闸决定是否修订 homology-component 合同；不会自动 cluster 或修改 `GOAL_S_DIRECT_R2`。

## 精确解析合同

1. P-state 枚举直接加载并 SHA-256 固定 `SF-DIRECT-BASELINE-SCREEN-20260811-R2/direct_s0_data.py` 与其 config，复用相同 ontology、hard-negative 和 `classify_annotation` 行为；因此 Unknown、`?`、RC、Retroposon 不会由本 audit 重新定义。
   现有 labeler 中 `Unknown` 与 `RC/Helitron` 是 P5，正常进入 provenance resolver；`Unknown?`、`LINE?`、`DNA?`、`Retroposon/SVA` 等被判为 U 的潜在 TE 不会被静默丢弃，而是进入独立 `label_contract_excluded.tsv`。该表记录 identifier、occurrences、raw classes 和 species，但这些记录不进入 resolved-provenance 分母。
2. resolver 严格按 `exact Dfam name`，随后 `exact Dfam accession`；不做 case-fold、prefix、substring 或版本猜测。`DR002419729` 是必须出现且必须经 exact-accession 路径解析的显式合同项。
3. 唯一成功项记录 versioned accession、consensus SHA-256，以及命中的 FamDB partition 的 project-relative path、精确 size 与 layout-bound source identity SHA-256。
4. missing、ambiguous、label conflict 与 duplicate-consensus 分开计数。same-name/different-consensus 属于 resolution ambiguity；duplicate-consensus 指不同 canonical identifiers 已各自唯一解析、但指向相同 consensus，是 homology-component 合同需要人闸修订的触发器，并非 resolver ambiguity。
5. 输出同时报告 parsed annotation records、P records、label-contract-excluded candidate records 与 provenance candidate records，并强制 `sum(P identifier occurrences)=P records`、`sum(excluded occurrences)=excluded records`、`P+excluded=candidate records<=parsed records`。零 records、空 P inventory 或任一守恒失败都是 `AUDIT_FAILED`，不能降格为 valid negative。

### Dfam H5 index-layout provenance

12 个实际 Dfam H5 partition 的 filename、partition、精确 byte size、`Lookup`、`Lookup/ByName`、`Lookup/ByStage`、`Lookup/ByTaxon` presence 已冻结到 `FROZEN_DFAM_H5_INDEX_LAYOUT_V1.json`，并由 config 固定 manifest SHA-256。该合同同时绑定既有 `rmlib.config` SHA-256 和每个 H5 的 Dfam/FamDB version、partition metadata；不新增对约 600 GiB partition 内容逐文件全哈希的负担。每个成功 resolver 项的 source identity SHA-256 是上述 database metadata、rmlib hash、layout-manifest hash、partition filename/index/size 的确定性组合，而不是未经预注册的全文件哈希。

真实布局仅 partition 3 明确缺 `Lookup/ByName`。`exact_name` 对它执行可计数的 skip，并继续 exact-accession 阶段；identifier inventory 与 P/excluded denominator 不因 skip 改变，最终仍无法解析的 identifier 是普通 missing typed blocker。其余 partition 的 ByName 存在且必须为 HDF5 Group：缺失、wrong-type、unreadable 或 query 异常全部是 `AUDIT_FAILED`，不得被吞掉或伪装成 missing。

## 终态语义

- `PROVENANCE_COMPLETE`：所有 P identifiers 均唯一溯源，资产审计语义成功。
- `IDENTITY_PROVENANCE_TYPED_BLOCK`：审计完整执行并得到有效否定结论，`semantic_success=true`、`valid_negative=true`、rc0；必须人闸修订，自动聚类仍禁止。
- `AUDIT_FAILED`：输入 identity、runtime 或完整性失败，`semantic_success=false`、rc2。
- 当前仅为 `IMPLEMENTED_NOT_RUN` 静态 preview，不表示任何真实 provenance 结论，也不是 code-review PASS。

## 资源与运行边界

Slurm 脚本显式请求 `private-teodoro-gpu` 的 4 CPU、32 GiB、2h、0 GPU，并在执行前调用正式 `pre_submit_gate.py`。runner 还要求真实 `SLURM_JOB_ID`。本轮只做登录节点静态测试，未扫描 canonical annotations、未提交 Slurm。
