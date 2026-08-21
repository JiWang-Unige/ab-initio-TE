# Council Prompt: TE-FM Fragmentation Mechanism and Decoder Replacement

请用简体中文回答。你是独立研究顾问，目标是帮助 TE foundation model annotation pipeline 解决严格 segment/boundary 指标下碎片化严重的问题。不要写代码；请给出可执行的研究判断和下一步实验设计。

## 已有事实

- 主线任务：raw-genome TE annotation。bp-level TE detection 可以达到中等到较高 F1，但严格 interval/segment 指标暴露出 TE 注释不完整、边界抖动和碎片化。
- 当前 promoted 候选：`ntv2_250m_w4096` animal fine-tune；`ntv3_100m_pre_w2048` plant fine-tune。
- 严格 segment 评估输出：
  - `reports/tefm_final/PIPE-TEFM-FINAL-STRICTSEG-20260629/summaries/strict_segment_summary.tsv`
  - `reports/tefm_final/PIPE-TEFM-FINAL-STRICTSEG-20260629/summaries/strict_segment_headline_iou80_boundary5.tsv`
- 严格 headline：
  - animal `ntv2_250m_w4096 + crf_style_penalty4`, IoU 0.8, boundary 5bp: bp-F1 0.6453, segment-F1 0.2557, boundary-F1 0.0989。
  - animal raw threshold: bp-F1 0.6444, segment-F1 0.1948, boundary-F1 0.0751；mean fragments per true 1.4957；short predicted segments mean 4359.9。
  - animal gap/min filters strongly reduce short predicted segments but increase missed true rate; example `gap100_min100`: segment-F1 0.2145, missed true rate 0.4346。
  - plant strict segment remains much weaker: best plant segment-F1 at IoU 0.8/boundary 5 is ~0.0305 for `ntv3_100m_pre_w2048 + gap100_min100` despite bp-F1 0.4585。
- 上一轮 tri-review 已一致认为：继续调 threshold/gap/HMM/CRF penalty 意义有限，应 replace/add component：segment-aware decoder、boundary-aware head、interval refiner、semi-Markov/duration-aware decoder。
- 用户提出一个新问题：是否对正反双链都执行 annotation prediction，然后合并，会改善 fragment 或边界问题？

## 需要你重点回答

1. Fragment 多的主要可能来源分别是什么？请把原因分成：
   - 模型/训练目标导致；
   - windowing/tokenization/stride/边缘效应导致；
   - strand/orientation 导致；
   - 后处理/threshold 导致；
   - UCSC/RepeatMasker 标签本身的真实碎片化、嵌套 TE、低质量 label/library 导致；
   - TE 生物学真实结构导致。
   对每类原因给出可验证诊断实验。

2. 双链预测是否值得马上做？请明确：
   - 为什么可能有效；
   - 为什么可能无效或引入假阳性；
   - 推荐的 merge 规则；
   - 最小可运行 sanity experiment；
   - 如果只选一项优先实验，双链预测排在第几。

3. 下一代组件该怎么设计？请比较：
   - frozen bp model + interval refiner；
   - boundary-aware multi-task head；
   - segment-aware decoder；
   - semi-Markov/duration-aware decoder；
   - CRF/HMM 的继续改良；
   - overlap center merge 的继续改良。
   请给出优先级、输入输出、训练标签、预期修复的 failure mode、风险。

4. 如何判断“减少碎片化”不是简单把所有 fragment 都删掉？请指定必须同时报告的指标，例如 pred_true_backed_rate、short_true_backed_rate、missed_true_rate、fragment retention stratified by true-backed vs false-positive 等。

5. 请给出一个单 seed、低成本、可在当前 pipeline 中最快落地的实验矩阵。目标不是 claim SOTA，而是判断哪条机制最值得后续投入 GPU。

## 输出格式

请按以下标题输出：

1. Verdict
2. Mechanism Attribution
3. Double-Strand Prediction
4. Decoder/Refiner Recommendation
5. Metrics Guardrail
6. Minimal Next Experiment
7. Stop Criteria
