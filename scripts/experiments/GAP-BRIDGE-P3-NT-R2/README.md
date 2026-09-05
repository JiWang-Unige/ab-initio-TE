# A：原生窗口配对准备（不训练）

`prepare_pair.py` 将原 Stage 1 的 143 channels / 7 scalars 原样复用，
构造同容量的 H0/HN 144 channels / 10 scalars。H0 新增槽在标准化之后为零；
HN 只新增 NT 连续 clipped logit 和三个 NT seam scalar。原文件未改动。

输入范围仅 chr3+chr5 TRAIN、chr13 DEV。无 CAL-GATE/test 评分、阈值选择或训练。
模型路径应为原四态 P3-R1（8192）与 NTv2-250M H0（4096）；不是 NTv2-500M。
smoke 选指定染色体按坐标排列的前 N 个原 manifest 候选，不按 label/risk 选择。

## 分离统计拟合与 blind inference

先在 CPU Slurm allocation 内拟合三维 NT stats：

```bash
python scripts/experiments/GAP-BRIDGE-P3-NT-R2/prepare_pair.py fit-stats \
  --candidate-manifest <original_candidate_manifest.tsv> \
  --output <fresh_nt_scalar_stats.json>
```

仅复用 `comparator_known=1` TRAIN 资格（chr3+chr5），不读取 targets；
资格字段不是模型 feature。原七维 stats 从 Stage 1 既有文件读取，不重新拟合。
三个新量：crop 是否跨 seam；gap midpoint 到最近 seam 的 `log1p(distance)`；
`sign(midpoint-seam)`。nearest tie 向左。注意原 P3 direction 保持旧实现，符号相反。
无方差列置 unit scale，使其中心化后为零；记录拟合总体及 count，不加 hash。

再在 GPU Slurm allocation 和原 Stage 1 / NT ensemble 使用的 `te_benchmark` 环境执行：

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
python scripts/experiments/GAP-BRIDGE-P3-NT-R2/prepare_pair.py smoke \
  --candidate-manifest <original_candidate_manifest.tsv> \
  --p3-scalar-stats <original_stage1_scalar_stats.json> \
  --nt-scalar-stats <fitted_nt_scalar_stats.json> \
  --region <original_8192_chr3_region.jsonl.gz> --seqid chr3 \
  --nt-model software_outputs/tefm_final/PIPE-TEFM-FINAL-20260623/runs/ntv2_250m_H0_w4096_seed42 \
  --p3-model outputs/TE-STRUCTURE-PILOT-20260825-R1/p3-human-20260828-r2-12097867/unet \
  --max-candidates 8 --output-dir <fresh_smoke_directory>
```

在仓库根目录运行。依赖沿用原 pipeline：numpy、torch、transformers 和已有模型
runtime；不安装或下载。默认 CUDA，`--device cpu` 可用于显式 CPU 分配，速度未知。
首次 smoke 规划 1 GPU / 16 GB RAM / 15 min，尚不是测量值。

NT 使用原 `strict_segment_eval.infer_probs_for_label_mode` 和 loader/tokenizer。
原点 0、stride 4096；从原 8192 sequence 逐半窗口前向；末端直接交原 tokenizer padding，
不向 DNA 添加 N，再将输出裁到真实长度。所有坐标（包括 N）保留，无 valid-mask 压缩。
P3 用原 native-window 前向及 adjacent carry 组装。

NT 原 adapter 的固定 688-token 容量可能被含 N 的 4096-bp 上下文耗尽，
此时输出仍为 4096 长、未覆盖位置默认为零；crop 本身全 ACGT 也不能排除此问题。
smoke 因此记录**本次实际前向**采用的 offset mapping 或 fallback raw-token 分支，
连同实际模型输出 token 数重建 token-to-bp coverage；不另调用 tokenizer 猜测分支。
每个候选 crop 必须全部覆盖，否则在 P3 前向/配对前以 `NT_TOKEN_COVERAGE_FAILED`
显式失败，给出缺失 bp 数与首末坐标；不能把这类默认零转换为可信的 -12 NT logit。
不删除 N、不压缩坐标、不修改窗口网格或 token 容量。窗口中 crop 之外的未覆盖 bp
仍在报告中保留，不代表候选 crop 自动失败。

`alignment_smoke.json` 报告每个窗口 token coverage、每个 crop 的完整 coverage、坐标长度、NT 长度、finite、paired base equality、
H0 extra-zero，以及 NT/P3 各自 load/inference runtime。`inference_labels_read=false`
精确定义为“不访问/解释 labels 字段”：JSON/TSV 文件可携带 labels 字节，解析器仍读取
文件内容；不能宣称从未读过这些字节。model feature 不使用 known、targets、family 或 support。
不保存全染色体 latent 或 comparator-derived masks。

## 定向检查

```bash
python -m unittest discover -s scripts/experiments/GAP-BRIDGE-P3-NT-R2 -p 'test_*.py' -v
```

八个测试各自注明可检测的具体失效及修改对象：tie/sign、配对槽位和 padding、末端/N
坐标保留、禁止 labels 字段访问、known TRAIN 统计资格和 DEV 排除、P3 seam carry offset，
以及 N 上下文截断和实际输出 token 数。后两项直接执行生产 `infer_probs_for_label_mode`
函数源码，仅 mock tokenizer/model/torch 边界；覆盖 offsets 与真实 fallback 两条路径，
不是 mock inference 的返回值。
它们不验证模型科学增益，也不替代真实前向 smoke。
