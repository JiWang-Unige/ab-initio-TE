# Phase 7: MVP 后续扩展计划

## 当前 MVP 配置

| 参数 | MVP 值 | 说明 |
|------|--------|------|
| 染色体 | chr1 | 单染色体快速验证 |
| 训练对数 | 10,000 | 约 2-3k TE 序列 |
| 验证对数 | 1,000 | |
| Epochs | 5 | |
| GPU | 1x A100 | gpu031 |
| 预计时间 | ~2-3h | |

### 成功标准

```
✅ ARI > 0.5 (聚类质量)
✅ pos_sim > neg_sim (对比学习有效)
✅ 训练 loss 稳定下降
```

---

## Phase 7.1: 扩展到全基因组 (MVP 成功后)

### 配置变更

| 参数 | MVP | Full | 倍数 |
|------|-----|------|------|
| 染色体 | chr1 | chr1-22 | 22x |
| 训练对数 | 10k | 100k | 10x |
| 验证对数 | 1k | 10k | 10x |
| Epochs | 5 | 20 | 4x |
| GPU | 1 | 4 | 4x |
| 预计时间 | 3h | 6-8h | ~2.5x |

### 脚本

```bash
# 数据准备（需要创建新脚本）
sbatch slurm/prepare_real_full.sbatch

# 多 GPU 训练
sbatch slurm/train_multi_gpu.sbatch

# 评估
sbatch slurm/evaluate_real_full.sbatch
```

### 配置文件

- `configs/experiments/exp001_real_full.yaml` ✅ 已创建

---

## Phase 7.2: Consensus 对比实验

MVP 成功后，运行 Consensus 实验进行对比：

```bash
# 准备 Consensus 数据
sbatch slurm/prepare_consensus_data.sbatch

# 训练
sbatch slurm/train_exp002_consensus.sbatch

# 评估
sbatch slurm/evaluate_exp002_consensus.sbatch
```

### 预期结果对比

| 指标 | Real Genome | Consensus | 预期 |
|------|-------------|-----------|------|
| ARI | ? | ? | Real > Consensus (假设) |
| NMI | ? | ? | |
| Silhouette | ? | ? | |

---

## Phase 7.3: 后续实验

1. **长度阈值对比**: 100bp vs 50bp minimum
2. **聚类方法对比**: KMeans vs Hierarchical vs HDBSCAN
3. **TE vs non-TE 二分类**
4. **新 TE 检测验证**

---

## 技术债务

- [ ] 添加 TensorBoard 日志
- [ ] 实现 early stopping
- [ ] 添加 gradient accumulation 支持
- [ ] 实现 mixed precision (bf16)
- [ ] 添加聚类可视化 (t-SNE/UMAP plots)

---

## 提交命令

```bash
# MVP (单 GPU，chr1)
cd /srv/beegfs/scratch/shares/ds4dh/common/TE_benchmark/TE_final/te_foundation/phase7_embedding
sbatch slurm/mvp_full_pipeline.sbatch

# 监控
squeue -u $USER
tail -f logs/phase7_mvp_*.out
```
