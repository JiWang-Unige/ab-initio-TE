---
name: sota-randomized
description: "A3.5/B· Re-train verified SOTA baselines under the project's small-sample/screen protocol with randomized initialization and multiple seeds, then predict/evaluate fairly instead of only using published or pretrained SOTA outputs. Creates a seed/sample manifest, sbatch-ready run matrix, reports mean±std, updates screen_anchor, docs/14_validation_matrix.md, and docs/02/06. Use before claiming small-sample progress or when comparing our Track-A result against SOTA on a screen budget."
argument-hint: "<SOTA model name(s), sample_fraction, seeds, metric, dataset/split>"
---

# SOTA-Randomized: SOTA 小样本随机重训 / 预测基线

本 skill 修补原架构的缺口：不能只拿 SOTA 模型在小样本上的“预测结果”比较；需要把 SOTA 模型按我们的 screen 协议 **随机初始化 / 重新训练 / 多 seed 预测**，建立公平的 `screen_anchor`。

## 触发时机

必须触发：
- Track A screen 想说“我们在小样本上优于 SOTA-like baseline”。
- `ACTIVE_GOAL.json.screen_anchor` 为空或不是同预算重训得到。
- SOTA repo/weights 可运行，但 published full-data 数值不能公平当 screen_anchor。
- 投稿阶段需要 reviewer-proof 的 baseline variance。

可选触发：
- 比较 pretrained vs random init 的价值。
- 验证 SOTA 是否只是 seed luck。

## Step 1 · 选择 SOTA 模型

从 `docs/02_sota_model_inventory.md` 和 `refs/dossiers/` 选择 1-3 个：
- reproducibility = trivial/moderate 优先。
- metric/split 可对齐优先。
- 如果 SOTA 代码不可跑，写明 blocker，不要伪造随机重训结果。

输出：

```markdown
| Model | Repo/weights | Repro level | Training entry | Metric alignment | Use? | Reason |
|---|---|---|---|---|---|---|
```

## Step 2 · 定义公平 screen 协议

协议必须与我们的 Track A 一致：
- dataset version。
- split scheme。
- sample_fraction。
- epochs/patience。
- batch size/resource cap。
- metric implementation。
- seed list。
- whether pretrained weights allowed。

若要比较 random init 与 pretrained init，分成两个 condition：
- `init=random`：随机初始化重新训练。
- `init=published_pretrained`：用公开权重微调/预测（只能作为另一条 baseline，不能混在 random mean 里）。

## Step 3 · 生成 run matrix

优先调用脚本生成 manifest：

```bash
python3 scripts/sota_seed_matrix.py \
  --model <model_slug> \
  --sample-fractions 0.05,0.10 \
  --seeds 1,2,3,4,5 \
  --metric <primary_metric> \
  --dataset <dataset_id> \
  --out configs/sota_randomized/<model_slug>_matrix.csv
```

每行生成一个 run_id：

```text
SOTA-<model_slug>-SF<frac>-S<seed>
```

## Step 4 · 实现与提交

- 复用 SOTA repo 的 train/eval entry；必要时写 wrapper 到 `pipelines/sota_randomized/<model_slug>/` 或 `scripts/sota_<model_slug>_wrapper.py`。
- 每个 run 的 config 放 `configs/<run_id>.yaml`。
- sbatch 放 `sbatch/<run_id>.sbatch`。
- checkpoint/output 放 `runs/<run_id>/`。
- metric 放 `reports/<run_id>.json`。
- STATUS 放 `outputs/<run_id>/STATUS`。

仍然必须经过：`/implement`（代码/数据/smoke）→ `/smart-sbatch`（资源/提交）→ `/result-log`（结果记录）。

## Step 5 · 汇总 mean±std 与 screen_anchor

完成后汇总：

```markdown
## Randomized SOTA screen report <date>

| Model | init | sample_fraction | seeds completed | Metric mean | std | best | worst | comparable? | Notes |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
```

写入：
- `docs/14_validation_matrix.md` §5。
- `docs/02_sota_model_inventory.md` 的 baseline/screen_anchor 补充段。
- `docs/06_results_log.md` 每个 run 的 result。
- 若建立了公平 screen_anchor，提议更新 `ACTIVE_GOAL.json.screen_anchor`（如果会改 goal，走 `/revise-goal` 人闸；不要直接改）。

## Step 6 · 公平解释

必须区分：
- `published SOTA`：full/scale claim anchor。
- `randomized SOTA screen_anchor`：小样本/同预算比较。
- `pretrained inference/fine-tune baseline`：有外部权重优势，不能和 random init 混淆。

## 不要做的事

- 不要用 published full-data SOTA 当 screen_anchor。
- 不要只跑 1 个 seed 就 claim 小样本稳定优于 SOTA。
- 不要把 random init 与 pretrained weights 混成一个平均值。
- 不要修改 SOTA repo 使其对我们模型不公平；wrapper 改动必须记录。

## Handoff

- **Outputs to**: `configs/sota_randomized/*.csv`, `configs/<run_id>.yaml`, `sbatch/<run_id>.sbatch`, `runs/<run_id>/`, `reports/<run_id>.json`, `docs/14`, `docs/06`, `docs/02`
- **Next**: `/result-log` → `/note-gate` → `/publication-plan` 或 `/benchmark-roadmap` 更新 screen_anchor
