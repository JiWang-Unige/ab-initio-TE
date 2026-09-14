# Fragment linking Phase 0（2026-09-14）

## 目的与边界

本阶段只冻结 fragment-pair 输入合同，并用一个可运行的 synthetic fixture 检查候选边、truth identity、split 单位和连通分量的基本行为。它是工程准备，不是模型实验；fixture 中的 family、orientation、predicted length 和 parent insertion ID 都是人工设定，统一标记为 `ENGINEERING_ONLY`。

本阶段没有调用 GLM、没有训练、没有读取 sealed 数据、没有填补任何 gap，也没有修改 material mask。M2/M3 只登记后续所需的输入和真实 truth 缺口，不生成模型分数。

## 输入合同

实现文件：

`scripts/experiments/FRAGMENT-LINKING-PHASE0-20260914/fragment_linking_phase0.py`

合同版本是 `fragment-linking-phase0-v1`，运行后会写出 `contract.json`。核心字段如下：

| 字段 | 含义 |
|---|---|
| `fragment_id` | fragment 的独立节点 ID |
| `contig`, `interval.start`, `interval.end` | 坐标；严格使用半开区间 `[start,end)` |
| `source_copy_id` | source-copy 分组键；只用于 split 约束，不替代 insertion truth |
| `family_group_id` | family-group 分组键；只用于 split 约束，不替代 insertion truth |
| `truth.parent_insertion_id` | 独立的 insertion truth identity；已知 truth 必须有值 |
| `truth.status` | `known` 或 `unresolved` |
| `truth.family`, `truth.orientation` | truth 命名空间；`unresolved` 时为空 |
| `prediction.family`, `prediction.orientation`, `prediction.length` | 预测特征命名空间；未知预测特征用空值，不能从 truth 回填 |

`truth.parent_insertion_id` 不从 `source_copy_id` 或 `family_group_id` 推导。若 pair 的任一端是 `unresolved`，`truth_pair_status=unresolved` 且 `truth_same_insertion=null`；该 pair 不进入 negative denominator、FP 或 FN。

fixture 中的 family 字段使用合成 family ID（例如 `Fam_LINE_A`、`Fam_LTR_A`），只是为了区分 family-group 与 coarse class；这些 ID 不是 Dfam family，也不表示真实生物学注释。

## Split 合同

代码先生成逐 fragment 的 `split_assignments.tsv`，再用这些实际的 fragment→role 记录检查 group 是否泄漏：

- `source_copy_split`：同一 `source_copy_id` 的所有 fragments 必须进入同一 split；
- `family_group_split`：同一 `family_group_id` 的所有 rows 必须进入同一 split。

两种 assignment 同时输出在 `split_assignments.tsv`，并且测试会故意把同一 source-copy 的一个 fragment 改到另一 role，确认验证器会失败。synthetic fixture 的分组本身是人工构造的工程输入，不代表真实 Dfam 或物种数据的同源隔离已经完成。

## B0/B1 edge 输出

pair 生成只枚举同一 contig 上的重叠或距离不超过 25 bp 的候选 pair；重叠 pair 被保留，因此 nested insertion 不会被坐标预处理丢掉。

- **B0 distance**：`distance_bp <= 25` 即输出 association edge。
- **B1 predicted rules**：在 B0 候选上，要求 predicted family 两端都已知且相同、predicted orientation 两端都已知且相同、以及 `min(predicted_length)/max(predicted_length) >= 0.5`。

`pairs.tsv` 除了 truth/prediction 特征，还记录每个 endpoint 的 source-copy role 和 family-group role。只有两端在相应 role 下都相同的 pair 才能进入 role-gated edge 文件；任一 role 不同就标记 `EXCLUDED_CROSS_SPLIT`。`edges_B0_distance.tsv` 和 `edges_B1_predicted_rules.tsv` 是同时通过两种 role gate 的边；`*_all_fixture.tsv` 保留全 fixture 的规则预测，供工程诊断使用。这些是 edge 列表，不是 merged intervals；代码不产生 gap sequence、merged start/end 或 mask。

## Synthetic fixture 覆盖的行为

| case | 设计 | 预期检查 |
|---|---|---|
| `same_insertion` | 两个 fragments 共享 `ins_same` | B0/B1 都能保留一个真 edge |
| `adjacent_independent` | 两个相邻 fragments 的 parent IDs 不同，但预测 family/orientation 相同 | B1 产生已知 negative 的 false edge |
| `nested_outer` + `nested_inner` | inner insertion 位于 outer 两个 fragments 之间 | B0 仅按距离连接；B1 用预测 family mismatch 阻断 |
| `unknown_orientation` | 同一 insertion，但左端 predicted orientation 为空、右端为 `+` | B0 可连，B1 因缺方向而 abstain/no-link |
| `transitive_chain` | 三个不同 parent IDs 的 fragments，两个相邻 pair 都满足 B1 规则 | B1 的 connected component 出现传递性误融合 |
| `far_same_insertion` | 同一 insertion 的两个 fragments 距离超过候选窗口 | candidate-recall 分母仍计入，候选分子不计入 |
| `unresolved_truth` | truth parent 缺失，但预测特征完整且相邻 | 可产生候选/edge，但不能作为 negative |

fixture 的 family/orientation 是人工输入，不能当作模型预测效果或生物学 truth。`fixture_fragments.jsonl` 中 truth 与 prediction 是两个独立对象，方便后续 M2/M3 接入真实预测时替换 prediction namespace 而不覆盖 truth。

## Toy 运行结果

运行命令：

```bash
python3 scripts/experiments/FRAGMENT-LINKING-PHASE0-20260914/fragment_linking_phase0.py \
  --out-dir reports/FRAGMENT-LINKING-PHASE0-20260914/toy_run
```

当前 fixture 输出（`reports/FRAGMENT-LINKING-PHASE0-20260914/toy_run/metrics.json`）：

- 16 fragments，8 candidate pairs；
- candidate-recall denominator = 4 个已知 same-insertion pairs，candidate numerator = 2，recall = 0.5；这个低值是有意保留的窗口漏检示例，不是模型分数；
- unresolved candidate = 1，B0/B1 都把它从 negative 统计中排除；
- B0 overmerged components = 3（包含 nested/adjacent/chain）；B1 overmerged components = 2（包含 adjacent/chain）；
- B1 对 `unknown_orientation` 的已知 same-insertion candidate 产生 1 个工程 FN，原因是缺少 predicted orientation 时按合同 abstain/no-link；这不是把该 pair 当成 biological negative；
- B1 检测到 transitive chain false merge；
- `intervals_unchanged=true`、`gap_filling_applied=false`、`material_mask_changed=false`；上述 metrics 覆盖整个 fixture，明确不是 heldout evaluation。

连通分量只用于暴露 pair edge 的传递闭包后果。即使 component 包含多个 parent insertion，Phase 0 也不会把它们写成一个新的坐标区间。

## M2/M3 状态与真实 truth 缺口

`contract.json` 中明确记录：

- **M2**：`INPUT_CONTRACT_ONLY`。后续需要经批准的 model edge scores、固定训练/评估 split 和真实 insertion-level truth；当前没有这些输入，不生成 score。
- **M3**：`INPUT_CONTRACT_ONLY`。后续需要 gap/context sequence evidence 和独立的 fragment-to-insertion linkage truth；当前没有经过核验的生物学 linkage truth，不生成 score。

当前 fixture 只能证明数据结构和统计分母的实现行为。它不能估计 candidate recall、pair precision、cluster overmerge rate 的真实物种值，也不能证明 B0/B1 对真实 genome 有效。

## 实现与验证文件

- 实现：[fragment_linking_phase0.py](/Users/jiwang/Desktop/TE/ab-initio-TE/scripts/experiments/FRAGMENT-LINKING-PHASE0-20260914/fragment_linking_phase0.py)
- 定向测试：[test_fragment_linking_phase0.py](/Users/jiwang/Desktop/TE/ab-initio-TE/scripts/experiments/FRAGMENT-LINKING-PHASE0-20260914/test_fragment_linking_phase0.py)
- 小型工程结果：[engineering_report.json](/Users/jiwang/Desktop/TE/ab-initio-TE/reports/FRAGMENT-LINKING-PHASE0-20260914/toy_run/engineering_report.json)
- 完整 toy 输出目录：[toy_run](/Users/jiwang/Desktop/TE/ab-initio-TE/reports/FRAGMENT-LINKING-PHASE0-20260914/toy_run)

验证命令：

```bash
python3 scripts/experiments/FRAGMENT-LINKING-PHASE0-20260914/test_fragment_linking_phase0.py -v
```

7 个定向测试通过。没有启动训练、推理、真实数据处理或 Slurm 作业，也没有提交 Git。
