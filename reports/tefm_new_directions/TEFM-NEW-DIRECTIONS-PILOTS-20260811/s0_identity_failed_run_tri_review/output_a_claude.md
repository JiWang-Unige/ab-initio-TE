# 独立评审裁决 — SF-IDENTITY-PROVENANCE-AUDIT-20260811-R1

## Judgment

`run-sanity-check-first`。这是确定性、可恢复的审计失败，不是 provenance/comparability 的科学结论。

## Evidence interpretation

`dfam39_full.3.h5` 缺少 `Lookup/ByName` 是合法结构特征；leaf API 抛出 `KeyError` 是调用者错误假设分区同构。没有 identifier audit 或 coverage，故没有 S0/identity 科学结果。失败状态与禁用 split/cluster/train/GPU/S1 的范围都正确闭合。

## Repair assessment

候选窄修复有效：调用 leaf name lookup 前显式检查 `Lookup/ByName` 是否结构存在；不存在时记录并跳过 name-index lookup，存在但不可读/损坏时硬失败。不要直接使用顶层 API 的宽泛异常捕获，也不要重打包 H5。

## Mandatory gates

1. 冻结真实 Dfam 3.9 每个 H5 分区的 `ByName/ByStage/ByTaxon` 布局 manifest，并运行时核对。
2. 合成 absent-vs-corrupt：合法缺索引必须 skip+留痕；索引存在但损坏/不可读必须 `AUDIT_FAILED`。
3. 新鲜独立代码审查必须 PASS。
4. 继续禁止 split、cluster、train、inference、S0 metric、GPU、goal 自动修订。
5. 最多允许一次修后 CPU audit retry；再次出现新失败不得自动第三跑。

## Single next action

实现结构存在性窄修复并冻结真实分区布局回归，再完成 absent-vs-corrupt 测试和 fresh review。

## Confidence

High。

