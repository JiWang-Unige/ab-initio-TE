## Judgment

`run-sanity-check-first`。

## Evidence interpretation

S0 provenance audit 因 Dfam 3.9 合法分区结构差异而 fail-closed；没有无效数据被晋升，所有 CPU-only/no-S1 范围都被遵守。这不是 provenance 科学结论。

## Repair assessment

候选窄修复在科学和操作上有效。直接使用顶层 `FamDB.get_family_by_name()` 不可接受，因为它会宽泛捕获异常；leaf 层显式检查 `Lookup/ByName` 存在性可以兼容合法异构，同时保留损坏/不可读对象的硬失败。

## Mandatory gates

1. 显式检查 `Lookup/ByName` group presence。
2. 增加 pinned Dfam 3.9 真实布局回归。
3. 合成证明 absent index 可安全跳过、corrupt/unreadable present index 必须失败。
4. fresh independent code review PASS。
5. S0-first/S1-locked 顺序继续绝对绑定。

## Single next action

实现结构检查与 absent-vs-corrupt tests，独立审查通过后仅进行一次 CPU audit retry。

## Confidence

High。
