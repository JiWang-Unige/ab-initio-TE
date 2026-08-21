---
name: generalization
description: "Ph8· Phase-8 comprehensive evaluation after the primary SOTA has been strictly exceeded."
---
> Codex/Antigravity note: this generated skill is mirrored from the Claude skill. When the body mentions a `/skill-name` command, Codex users should invoke `$skill-name`; Claude users keep `/skill-name`.


# Generalization (Phase 8)

主候选已在 primary 上**严格**超越 SOTA → 进入全面验证。本 skill 把 `$ARGUMENTS` 推过 8 维。

## 触发条件

- `/result-log` 显示 `sota_claim_gate` ✅(strict `>`)
- `/pivot` decision = continue / scale,**不能**是 abandon
- Comparability audit 已过(6 维 ✅)
- Multi-seed paired test 已计划好

## 8 个维度

| Dim | Question | Pass? | Run |
|---|---|---|---|
| 1. 跨分布 | 换 split scheme / 物种 / 时间窗口后是否仍超越? | ✅/❌ | 1-3 |
| 2. OOD | held-out 分布外样本上的表现? | ✅/❌ | 1 |
| 3. Robustness | 添加 noise / corruption / adversarial 后下降多少? | ✅/❌ | 2-4 |
| 4. Secondary metrics | 其他常见 metric 也超越 / 不退化? | ✅/❌ | 1 |
| 5. 计算成本 | inference / training cost 没显著恶化? | ✅/❌ | 1 (logged) |
| 6. Ablation | 关键模块去掉后效果如预期下降? | ✅/❌ | 3-5 |
| 7. Failure cases | 错误样本有规律 / 可解释? | ✅/❌ | analysis |
| 8. Multi-seed paired | ≥3 seeds 双侧 paired t-test p < 0.05? | ✅/❌ | ≥3 seeds × both |

## 工作流

### Step 1 · 设计 evaluation matrix

```markdown
## Generalization matrix for <exp_id>

| Dim | Test set | Metric | SOTA baseline | Threshold to pass |
|---|---|---|---|---|
| 1.1 cross-species mouse | mm10_test | F1 | <SOTA mouse> | F1 > SOTA mouse |
| 1.2 cross-species rat | rn7_test | F1 | <SOTA rat> | F1 > SOTA rat - 0.02 (acceptable degradation) |
| 2.1 OOD long seq >5kb | held_out_long | F1 | -- | F1 > 0.6 (absolute floor) |
| 3.1 robustness 5% noise | train_eval_noisy | F1 | -- | drop < 0.05 |
...
```

### Step 2 · 跑 evaluation(可能多个 sbatch)

每个 dim 一个 sbatch job(或 array)。每个跑完 `/result-log` 一遍。

### Step 3 · Multi-seed paired test
> **这是全流程唯一强制多 seed 的关口**（CLAUDE §9 多 seed 时机）。迭代期（screen + scale 选方向）一直是单 seed；到这里方向已确定，才花算力跑 ≥3 seeds 做 paired 统计检验，把赢家钉成稳健 SOTA。
```python
# 伪代码
seeds = [42, 123, 7]
our_results = [f1_seed_42, f1_seed_123, f1_seed_7]
sota_results = [f1_sota_seed_42, ...]  # same data + seeds

from scipy.stats import wilcoxon  # paired, non-parametric
stat, p = wilcoxon(our_results, sota_results, alternative='greater')
```

报告 stat + p + 每个 seed 的差。

### Step 4 · Failure case analysis

至少 30 个 false positive + 30 false negative,分类:

- 序列长度 short / medium / long
- 物种 / domain
- 标签质量(human label noise)
- 与 SOTA 的错误重合度

### Step 5 · 写 generalization report

```markdown
# Generalization Report: <exp_id>

## Summary
- Primary SOTA exceedance: ✅ confirmed on <split>
- Generalization dims passed: <X>/8
- Robust SOTA claim status: <claim / partial / cannot claim>

## Per-dim results

### Dim 1: Cross-distribution
- 1.1 mm10: F1=<x>, SOTA=<y>, gap=<z>, pass: ✅/❌
- 1.2 rn7: F1=<x>, SOTA=<y>, gap=<z>, pass: ✅/❌

### Dim 2: OOD
...

(continue for all 8)

## Statistical test
- Method: Wilcoxon signed-rank paired, alt='greater'
- N seeds: <n>
- p-value: <p>
- Significant at α=0.05: ✅/❌

## Failure case analysis
- 30 FP + 30 FN reviewed
- Patterns:
- Comparison to SOTA's failure cases:

## Verdict
- [ ] Robust SOTA — all 8 dim pass + p < 0.05
- [ ] Conditional SOTA — passes on primary + some dims (specify)
- [ ] Single-split fluke — primary exceed but multiple dims fail
- [ ] Cannot claim — multi-seed not significant

## Next
- if robust: 锁定该架构为新的 internal SOTA baseline，归档到 docs/06 + wiki，并以它为参照开下一条正交攻坚线
- if conditional: scope claim to what we can defend
- if fluke / cannot-claim: **先撤回已写的 claim（见下 G10），再 back to /pivot**
```

> **撤回 claim（G10，HARD）**：`/pursue` 在多 seed 之前、tri-review + human gate 后就可能把 `ACTIVE_GOAL.status=achieved` 并在 docs/06 记 SOTA claim。**若本步判 single-split fluke / cannot-claim**，不能只 `→ /pivot` 走人——必须先：① `/revise-goal` 把 `status` 退回 `active`；② 在 `docs/06` 对应结果标 `claim_retracted: <reason>`；③ `docs/00` 记一句撤回。否则会留下"已达成"的假 SOTA，跨会话 `context_pack` 恢复时会被当真值。

## Don'ts

- 不要在 sota_claim_gate ❌ 时调用
- 不要省 multi-seed
- 不要把 single-seed 显著差异当 robust SOTA
- 不要在 dims 上挑挑拣拣只报告 pass 的那几个——所有 dim 都报

## Hand-off

- **Inputs from**: `docs/06_results_log.md` (strict-exceed entry),`docs/03_benchmark_roadmap.md` §7.3 M5 milestone
- **Outputs to**: `docs/06_results_log.md` (append generalization entries) + a `Generalization Report` section
- **Next step**: 稳健 → 锁定为新 internal SOTA baseline（归档 docs/06 + wiki/notes），开下一条正交线；若失败 → `/pivot` 重新决策
