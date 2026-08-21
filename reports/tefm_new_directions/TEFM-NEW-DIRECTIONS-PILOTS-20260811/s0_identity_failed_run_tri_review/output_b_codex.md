## Judgment

`run-sanity-check-first`。这是确定性的分区布局兼容错误，不是 provenance/comparability 的科学结论；运行是 `failed_run`，不能解释为 typed block、valid negative 或 S0 结果。

## Evidence interpretation

审计在生成 `identifier_audit.tsv` 和 coverage 前终止，因此没有证明 provenance 可绑定或不可绑定。无 split、训练、推理或指标产生，`validate_goal=failed_run` 与终态一致。

## Repair assessment

候选窄修复原则上有效，并且比直接采用宽泛捕获异常的顶层 API 更符合 fail-closed：仅确认 `Lookup/ByName` 结构性不存在时跳过该叶的 name lookup；这不得改变 inventory/conservation denominator。存在但无法读取、类型/结构异常或查询异常时必须失败。缺索引分区中的目标 family 最终仍必须从其他可靠索引绑定，或成为明确 typed block。

## Mandatory gates

- 针对 pinned Dfam 3.9 实际布局的回归，确认 partition 3 缺 ByName、其他分区存在，并验证 denominator 不变。
- synthetic absent 只允许结构缺失时跳过。
- synthetic corrupt/unreadable/present-but-invalid 必须 `AUDIT_FAILED`。
- 零库存、库存减少、分区遗漏、重复/歧义、非唯一绑定或 coverage 不完整都必须 fail-closed 或显式 typed block。
- 全部测试和 fresh independent review PASS。

## Single next action

实施结构存在性窄修复和 fail-closed 回归包，提交 fresh independent review；PASS 前不重试。S0-first/S1-locked 顺序不变。

## Confidence

High。

