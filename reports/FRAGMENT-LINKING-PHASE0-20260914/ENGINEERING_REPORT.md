# Fragment linking Phase 0 engineering report

状态：`PASS_ENGINEERING_ONLY`

本报告只记录 synthetic fixture 的合同和不变量验证。fixture 中 16 个 fragment 及其 family/orientation/prediction 字段均为人工设定；没有模型、真实 genome、sealed 数据或生物学分数。

family 字段使用 `Fam_LINE_A`、`Fam_LTR_A` 等合成 family ID，用于和 coarse class 区分；它们不是 Dfam family。以下 metrics 覆盖整个 fixture，属于工程诊断，不是 heldout evaluation。

| 检查 | 结果 |
|---|---:|
| 合同版本 | `fragment-linking-phase0-v1` |
| 半开区间 `[start,end)` | PASS |
| source-copy split 无泄漏 | PASS |
| family-group split 无泄漏 | PASS |
| candidate-recall 分母 | 4 个 known same-insertion pair |
| candidate-recall 分子 | 2 个 candidate pair |
| candidate recall | 0.5（窗口漏检 fixture） |
| unresolved candidate 排除 | 1 个；不计作 negative |
| role-gated B0/B1 edge 文件 | 4 / 3 条 |
| B0 distance overmerge | 3 components |
| B1 rule overmerge | 2 components |
| B1 transitive-chain false merge | 检出 |
| B1 unknown-orientation FN | 1 个 candidate；缺方向时 abstain/no-link |
| interval 不变 | PASS |
| gap filling | 未执行 |
| material mask 修改 | 未执行 |
| M2/M3 | `INPUT_CONTRACT_ONLY` |

详细 pair 表、edge 表、cluster 表和合同见同目录 `toy_run/`。`pairs.tsv` 和 `*_all_fixture.tsv` 保留跨 role 的全 fixture 诊断行，并将其标为 `EXCLUDED_CROSS_SPLIT`；role-gated 文件只保留两端同 role 的边。本报告不应被引用为真实物种性能结果。

重现：

```bash
python3 scripts/experiments/FRAGMENT-LINKING-PHASE0-20260914/fragment_linking_phase0.py \
  --out-dir reports/FRAGMENT-LINKING-PHASE0-20260914/toy_run
python3 scripts/experiments/FRAGMENT-LINKING-PHASE0-20260914/test_fragment_linking_phase0.py -v
```
