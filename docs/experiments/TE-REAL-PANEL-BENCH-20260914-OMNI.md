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
  --dirty --out-dir /tmp/te-real-panel-omni-12708424 --cores 1
```

真实 bundle 不进入 Git。`real_panel.yaml` 使用仓库 named entrypoint `real_panel`；根 `omnibenchmark.yaml` 需要在接入提交后增加：

```yaml
  real_panel: benchmarks/te_omnibenchmark/real_panel.py
```

然后把 YAML 的 repository commit 更新到包含该入口和 exporter 的实际提交。当前 YAML 中的 commit 只是接入时的暂存 pin，不能在该代码尚未进入 GitHub 时用于 clean checkout。

## 产物

`real_panel_export.py` 生成 `manifest.json`、`cell_registry.json`、`panels/*.json` 和 `cells/*/{status.json,provenance.json,predictions.tsv}`。Omni module 生成 `metrics.json` 和 `collector_summary.json`。应在报告中分别引用 native Slurm 的 `status.json`/walltime 与 Omni 的 replay/collection 日志；后者不替代 native runtime。
