# OmniBenchmark 接入：真实固定区域面板

本目录把 Slurm 上已经完成的 native caller 输出，和保存的 D `F` 结果，重放为一个 OmniBenchmark 0.6 T2 模块。它只评价同一四区域输入上的可调用碱基覆盖、候选 fragment 数、两结果的 callable intersection 和 Jaccard。这个面板没有独立 truth，因此输出中的 precision/F1 始终为 `null`；导入结果的时间也不作为 native 推理时间。

## 运行边界

固定 registry 有 12 个 cell：每个物种的 `fixed_rm`、`hite`、`rm2_rm` 三个 native cell，加一个保存的 `D_F_cache` replay cell。失败、超时、blocked、unsupported 和缺失输出都保留在 registry；collector 对缺少指标的 cell 写 `NOTRUN`，不会把它变成零分。compact bundle 只含 canonical interval TSV、status、坐标和 callable runs，不复制 FASTA 或概率数组。

## 生成 compact bundle

在能看到项目 `outputs/` 的 Baobab 节点，并在 native array `12708424` 完成或明确收束后运行：

```bash
python3 benchmarks/te_omnibenchmark/real_panel_export.py \
  --root /srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE \
  --native-array-id 12708424 \
  --output /tmp/te-real-panel-compact-12708424
```

导出器会从原 D panel 读取四段序列以记录 callable runs，并把 native/D 的 panel ID 统一到 `r01`--`r04`；原始 fasta 和 probability 文件仍留在源目录。导出前后不改变固定 panel、阈值或预测缓存。

## 本机 Omni 重放

将上述紧凑目录复制到执行 Omni 的本机路径后，设置其绝对路径：

```bash
export TE_REAL_PANEL_BUNDLE=/tmp/te-real-panel-compact-12708424
/Users/jiwang/Desktop/TE/manuscript-review-20260914/omnibenchmark-venv/bin/ob run \
  benchmarks/te_omnibenchmark/real_panel.yaml \
  --out-dir /tmp/te-real-panel-omni-12708424 --cores 1 -- --scheduler greedy
```

真实 bundle 不进入 Git。`real_panel.yaml` 使用仓库 named entrypoint `real_panel`；根 `omnibenchmark.yaml` 已包含：

```yaml
  real_panel: benchmarks/te_omnibenchmark/real_panel.py
```

当前 pin 为包含跨主机 bundle-root 修复的 `b75ebfa93254579147ee44f12ba83c4d24838365`，已推送并从 GitHub 实际获取。源端绝对目录作为 provenance 保留，data stage 解析根改为调用方本机 bundle 目录。

## 已执行的真实部分矩阵

Slurm export `12708689` 保存了 native array `12708424` 的一个明确时间点：12 cell中3个D缓存及1个HiTE完成、2个传统caller运行、6个尚未产出。HiTE在固定鸭嘴兽四区域得到7,874条canonical记录，native耗时620.1秒；它不是独立accuracy结果。

root随后以 GitHub commit `b75ebfa93254579147ee44f12ba83c4d24838365`、不使用`--dirty`执行真正的`ob run`。4个Omni jobs完成，metrics和collector均保留12格，4格有读数，6个NOTRUN和2个RUNNING的metric均为null。当前collector不从缺输出推断Slurm的细分排队原因，因此NOTRUN只表示该export时没有产物，不能解释为取消或失败。首次跨主机绝对路径失败记录留本机，修复后已通过真实重放和跨主机路径测试。

可提交证据位于 `reports/TE-REAL-PANEL-BENCH-20260914/clean-replay-b75ebfa/`。
完整bundle、Omni缓存checkout和工作目录被本子树`.gitignore`排除，原始序列/概率/模型留在Baobab。后续仍需等native全部完成后导出新的完整snapshot，不能把本次4个有结果cell写成完整benchmark。

## 产物

`real_panel_export.py` 生成 `manifest.json`、`cell_registry.json`、`panels/*.json` 和 `cells/*/{status.json,provenance.json,predictions.tsv}`。Omni module 生成 `metrics.json` 和 `collector_summary.json`。应在报告中分别引用 native Slurm 的 `status.json`/walltime 与 Omni 的 replay/collection 日志；后者不替代 native runtime。
