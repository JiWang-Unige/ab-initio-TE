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

当前 pin 为 `57d208251c837fce8028b32e362358ffa9df3cf5`，包含跨主机 bundle-root 及显式类别解析修复，已推送并从 GitHub 实际获取。源端绝对目录作为 provenance 保留，data stage 解析根改为调用方本机 bundle 目录。

## 已执行的真实部分矩阵

Slurm export `12709406` 在 array `12708424` 的 8 个 native cell 已完成、`platypus|rm2_rm` 仍运行时生成当前 snapshot；另 3 个 D `F` 缓存 cell 已完成。因此当前 12-cell registry 有 11 个 completed、1 个 running。Slurm `COMPLETED` 只有调度层状态，caller 是否成功以各 cell 的 `status.json` 为准；本 snapshot 中 11 个可评价 cell 的 caller status 均为 `COMPLETED`。

当前 callable coverage 读数如下。每个物种四区域的名义总长为 4,194,304 bp，fraction使用该面板ACGT可用碱基数作分母。这些是所有caller候选区间的T2 coverage，包含其known-TE、unknown/ambiguous及non-TE类别；分类分桶另存metrics，不能把总覆盖率直接当TE-positive recall或accuracy：

| species | method | candidate fragments | callable coverage (bp) | callable fraction |
|---|---|---:|---:|---:|
| platypus | fixed_rm | 15,359 | 2,428,915 | 0.579098 |
| platypus | hite | 7,874 | 998,052 | 0.237954 |
| platypus | D_F_cache | 6,732 | 2,146,893 | 0.511859 |
| sea_urchin | fixed_rm | 8,330 | 2,064,091 | 0.492294 |
| sea_urchin | hite | 4,882 | 540,660 | 0.128950 |
| sea_urchin | rm2_rm | 3,043 | 890,099 | 0.212292 |
| sea_urchin | D_F_cache | 4,396 | 628,428 | 0.149883 |
| c_briggsae | fixed_rm | 1 | 141 | 0.000034 |
| c_briggsae | hite | 2,122 | 276,511 | 0.067337 |
| c_briggsae | rm2_rm | 1,925 | 382,550 | 0.093161 |
| c_briggsae | D_F_cache | 1,704 | 237,027 | 0.057722 |

同一物种内相对于 D `F` 的 callable Jaccard 为：platypus `fixed_rm=0.841477`、`hite=0.432019`；sea urchin `fixed_rm=0.247991`、`hite=0.110324`、`rm2_rm=0.214326`；C. briggsae `fixed_rm=0`、`hite=0.335811`、`rm2_rm=0.334878`。这些差异说明方法输出的区域覆盖和 D 输出的一致性会随物种/方法变化，但不能单凭一致性给出独立准确率排名。D 缓存 canonical 没有 caller class 字段，因而其分桶主要落在 unknown；不能与 native 的 KnownTE/nonTE 分桶直接比较。

当前 snapshot 先以 GitHub commit `b75ebfa93254579147ee44f12ba83c4d24838365` 完成真实clean replay。后续检查发现旧分桶通过任意文本中的RNA子串识别non-TE，错误处理了SINE/tRNA及其子型；并将PLE列入known-TE，与本项目的歧义标签口径不一致。固定同一snapshot，以修复后的GitHub commit `57d208251c837fce8028b32e362358ffa9df3cf5`、不使用 `--dirty` 再次执行真正的 `ob run`，4个Omni jobs完成。5项focused tests通过，包括SINE/tRNA、独立tRNA、PLE、缺失类别及未知类别。

现仅按显式class_family/class/family的顶层类别分桶；SINE/tRNA属于known-TE，顶层tRNA才是non-TE，PLE在本项目比较中保留为unknown/ambiguous，不代表它在生物学上不是TE。实际3553条SINE/tRNA及子型记录从non-TE恢复为known-TE，298条PLE记录转为歧义分桶。以原提交的实际分类函数逐条复核差异，所有cell的总覆盖、candidate数及全部pairwise指标均不变。鸭嘴兽HiTE的known-TE callable覆盖从509,024修正为933,972bp；先前类别分桶不可再用于解释，原始输出不变。

修正后的metrics和collector仍保留12格、11格有读数，`platypus|rm2_rm`的metric为null，precision/F1始终为null。当前权威类别读数、逐条类别更正计数和clean日志位于`reports/TE-REAL-PANEL-BENCH-20260914/clean-replay-57d2082/`。

此前的紧凑证据保留在 `reports/TE-REAL-PANEL-BENCH-20260914/OMNI-CLEAN-12708424-COMPACT/`：其中native状态/registry及运行时间仍有效，旧类别桶由上述57d2082重放替代。完整bundle、Omni checkout和工作目录由本子树`.gitignore`排除，原始序列/概率/模型留在Baobab。`compact_snapshot_12708424_current`是两次重放的同一输入bundle；在native全部完成前不能把本次snapshot写成完整benchmark。

## 产物

`real_panel_export.py` 生成 `manifest.json`、`cell_registry.json`、`panels/*.json` 和 `cells/*/{status.json,provenance.json,predictions.tsv}`。Omni module 生成 `metrics.json` 和 `collector_summary.json`。应在报告中分别引用 native Slurm 的 `status.json`/walltime 与 Omni 的 replay/collection 日志；后者不替代 native runtime。
