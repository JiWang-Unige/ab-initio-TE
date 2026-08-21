# PIPE-TEFM-SUPP-20260617 Final Screen Report

日期：2026-06-18

## 范围

本轮按用户要求完成 UCSC strict-TE comparator 上的补充筛选实验：

- H0 human-only quick fine-tune/window sweep，seed=42。
- B/C fine_tune 物种一条染色体 transfer eval。
- mouse-only fine-tune 后对 human/cattle/horse/pig eval。
- A2 no-human animal mixture fine-tune 后对 A2 eval_only eval。
- 非重叠窗口 edge-vs-center 分析。
- 简单泛化衰减 sanity check。

所有指标都是 token-level proxy screen；不是最终 bp-level/segment-level claim。

## 产物

- 总表：`reports/tefm_supp/PIPE-TEFM-SUPP-20260617/summaries/all_metrics.tsv`
- 窗口：`reports/tefm_supp/PIPE-TEFM-SUPP-20260617/summaries/window_sweep.tsv`
- B/C transfer：`reports/tefm_supp/PIPE-TEFM-SUPP-20260617/summaries/transfer_summary.tsv`
- downstream：`reports/tefm_supp/PIPE-TEFM-SUPP-20260617/summaries/downstream_summary.tsv`
- edge：`reports/tefm_supp/PIPE-TEFM-SUPP-20260617/summaries/edge_summary.tsv`
- 泛化衰减：`reports/tefm_supp/PIPE-TEFM-SUPP-20260617/summaries/decay_screen.tsv`

最终汇总规模：118 metric rows；20 window rows；72 transfer rows；26 downstream rows；75 edge-bin rows。

## 主要结果

### Model/window

- H0 human window sweep 最佳：`ntv2_500m`, window=4096, TE-F1=0.9458, AUPRC=0.9893。
- 第二：`generanno`, window=4096, TE-F1=0.9430, AUPRC=0.9869。
- `generanno` window=8192 完成后 TE-F1=0.9340，未超过 4096。
- B/C 2048 全模型 transfer mean TE-F1：`generanno` 0.5477，`ntv2_500m` 0.5367，`dnabert2` 0.4535，`hyenadna` 0.4258。
- B/C 4096 对比：`ntv2_500m` mean TE-F1=0.5185，高于 `generanno` 0.4851。

结论：窗口按 H0 screen 选 4096；模型选择不唯一。若按第 1 步 2048 transfer mean，`generanno` 略优；若按 4096 paired transfer 和 H0 window，`ntv2_500m` 更稳。下游因此保留了两条分支。

### Mouse-only downstream

`mouse_to_A1_w4096`，4 个 vertebrate eval species：

- `generanno`: mean TE-F1=0.8721，median=0.8800，mean AUPRC=0.9452。
- `ntv2_500m`: mean TE-F1=0.8546，median=0.8821，mean AUPRC=0.9366。

结论：mouse-only 对 close vertebrates 的泛化较好；human 与 cattle/horse/pig 没有出现灾难性断崖。

### A2 no-human animal mixture

`mixedA2_to_A2_w4096`，9 个 eval species：

- `generanno`: all-species mean TE-F1=0.5590，vertebrate mean=0.7160，invertebrate mean=0.0094。
- `ntv2_500m`: all-species mean TE-F1=0.5414，vertebrate mean=0.6941，invertebrate mean=0.0071。

结论：mixture 对 vertebrate eval 有一定泛化，但对 held-out invertebrate 基本失败。按用户要求，不继续自动改进；记录为后续 tri-review/pivot 议题。

### Edge effect

非重叠窗口存在边缘衰减：

- 512 窗口：edge-minus-center 约 -0.034 到 -0.036 TE-F1。
- 1024 窗口：`generanno` -0.0406，`ntv2_500m` -0.0248，`dnabert2` -0.0077。
- 4096/8192 窗口：多为 -0.008 到 -0.015，较可控。

结论：边缘效应真实存在；短窗口更明显。若做最终 bp-level prediction，建议采用 overlap sliding + center-weight merge，再做 HMM/CRF 或 segment-level smoothing。

### 泛化衰减

简单 ordinal-distance screen 呈负相关：

- B/C transfer：Pearson 约 -0.88 到 -0.93。
- A2 mixture：`generanno`/`ntv2_500m` 同样主要由 vertebrate vs invertebrate 断层驱动。

结论：可以记录为 sanity pattern，但不建立正式泛化衰减公式。当前距离编码粗糙、标签质量和 kingdom/domain shift 共同作用，公式不具备 claim 价值。

## Tri-review

- PASS_WITH_WARNINGS。
- 结果适合指导下一步筛选，不适合 claim。
- 最大风险：token-level proxy、quick max_windows 首染色体截断、one-chrom eval、strict UCSC comparator 对非人类/植物覆盖不均、不同 tokenizer 下 token 指标不可直接当 bp 指标。
- A2 mixture 的 invertebrate failure 是真实行动项：不要继续盲调；后续应考虑 kingdom/head routing、分层采样、标签源修复或按 clade 分模型。
- 碎片化处理建议优先顺序：overlap+center-weight merge -> 小段过滤/密度阈值 -> HMM/CRF smoothing -> segment superfamily classifier。不要在当前 screen 上直接 claim 超家族完整注释。

## 阻塞项

- NTv3 本地快照缺 `InstaDeepAI/ntv3_base_model` remote-code 模块，未能 smoke/train。
- Evo2 本地快照缺 HuggingFace `model_type`/tokenizer adapter，未能 smoke/train。

## 建议下一步

1. 主线候选保留 `generanno` 和 `ntv2_500m`，window=4096。
2. 做 bp-level evaluator 与 overlap-merge evaluator 后再判断最终 claim。
3. 对 A2 invertebrate failure 做一次人工 tri-review/pivot，不自动继续训练。
4. 若要解决碎片化，先实现 overlap center-weight 合并，再加 HMM/CRF/启发式密度过滤。
