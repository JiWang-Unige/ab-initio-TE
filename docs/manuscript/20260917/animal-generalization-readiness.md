# D 共享模型外部泛化准备审计

更新时间：2026-09-17。本文档保留准备审计及其后的固定外部 screen 结果；本轮没有训练、目标校准或 sealed 面板读取。

## 结论先行

目前不能把“六物种模型的泛化能力已经完整测试”写进论文。现有 D 模型在六个参与监督微调的物种上有完整 DEV 结果，但这些结果是同域监督结果，不是物种外泛化。

已有一次固定 D seed42 的外部推理，使用了同一个六物种共享校准和阈值：鸭嘴兽、紫海胆和秀丽隐杆线虫近缘种 *Caenorhabditis briggsae*。鸭嘴兽的四个 1-MiB 区域支持的是参考注释一致性端点；海胆和 *C. briggsae* 的标签稀疏，只能把主要结果解释为 reference-positive recovery。它们不能构成完整、独立、全基因组的物种泛化结论。本轮外部 screen 按预先约定只使用 seed42；多 seed 不是本轮收束条件。

因此，下一步应先完成一个候选物种资格和覆盖审计，再做固定 checkpoint 的分阶段外部评估；只有在共享模型的外部错误模式确认后，才决定是否训练物种专家或 MoE。MoE 目前没有足够的因果依据作为第一步。

## D 模型的实际训练和校准边界

当前 D 共享模型的监督微调物种是：human/hs1、mouse/mm39、chicken/galGal6、zebrafish/danRer11、pig/susScr11 和 *C. elegans*/ce11。训练、CAL 和 DEV 的物种表见 `scripts/experiments/CROSS-SPECIES-L1-20260903/species_x0_r2.tsv`；固定材料由 `outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202/` 提供。

seed42 D coverage arm 的固定推理组件是：

| 组件 | 固定路径（Baobab） |
|---|---|
| final model | `/home/users/j/jwang/ab-initio-TE/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/train/seed42/12307410_1/final_model` |
| calibration | `/home/users/j/jwang/ab-initio-TE/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/evaluate/seed42/12353905_1/calibration.json` |
| NTv2 code | `/home/users/j/jwang/ab-initio-TE/.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species` |
| model | NTv2-500M multi-species + D token-classification head |
| window/tokenization | 4096 bp halves；6-bp tokens和尾部单碱基投影 |
| batch | 12（既有外部 run） |
| Platt slope/intercept | 0.6984053956932976 / -0.8050313412075021 |
| global threshold | 0.42330056285498807 |
| threshold source | 六物种 CAL；外部物种不得重新校准或按目标物种挑阈值 |

校准文件同时含 `calibration_protocol: CROSS-SPECIES-L1-X0-PLATT-V1` 和实验溯源字段 `protocol: CROSS-SPECIES-L1-UPSTREAM-20260904-V1`。现有 FASTA 入口优先读取前者，协议检查能够匹配。初始审计据第二个字段推测的兼容性问题经源码核读已排除，不需要修改协议守卫；实际移植问题是 artifact 绝对路径和研究目录依赖。

## 已测结果和解释边界

### 六物种 DEV：不是外部泛化

当前 D seed42 的 DEV bp F1 为 human 0.940310、mouse 0.941998、zebrafish 0.927836、pig 0.893138、chicken 0.831720、*C. elegans* 0.797565；这些是六个监督微调物种的 DEV 结果，不是外部泛化。seed17 是历史内部复核模型，本轮外部 screen 不重复执行。

六个物种都参与了监督微调，且 DEV 是已使用的开发分区。这里可以说明共享模型在训练物种上的物种平衡表现和最弱物种风险，不能说明对未参与监督的动物泛化。

### 已完成 D 外部推理

| 物种/assembly | 推理范围 | 标签覆盖 | 可报告端点 | 不能报告 |
|---|---|---|---|---|
| 鸭嘴兽 *O. anatinus* / GCF_004115215.2 | 4 个固定 1-MiB 区域 | RepeatMasker/Dfam 稀疏 comparator；未标注区不是负类 | reference-comparator F1 0.784126，positive recovery 0.959325 | 独立生物学 precision、全基因组 F1、未见 DNA |
| 紫海胆 *S. purpuratus* / GCF_000002235.5 | 4 个固定 1-MiB scaffold 区域 | curated 后扩展到 uncurated 的稀疏 comparator | 扩展标签下 positive recovery 0.428937；覆盖缺口和模型漏检并存 | 全基因组 F1、独立 precision、完整真值 |
| *C. briggsae* CB4 / GCA_000004555.3 | D external 输出中为 4 个固定 1-MiB 区域；全 assembly 标签资产另行存在 | 仅 1,571 个稀疏正 bp 的 comparator | positive recovery 0.618714 | 全基因组 F1、TN/FP、完整生物学准确率 |

上述外部 run 均使用 seed42 D、六物种 CAL、同一个固定阈值；没有目标物种适应、重新训练或 target-specific threshold。外部标签的来源和正类覆盖可以支持 reference-dependent diagnostics，但不能把 reference-negative 区域当作可靠背景。

三种外部物种已经被打开并用于历史 D external run，因此本轮不能再称其为新的独立盲测。NTv2 backbone 的逐 assembly 预训练暴露仍未知，不能声称完全未见 DNA。

### 旧 transfer screen：只能作为候选排序线索

`reports/tefm_extend/PIPE-TEFM-EXTEND-20260620/` 中的 GENERanno-4096 `invert_boost` screen 曾覆盖 horse、cattle、opossum、lizard、western honey bee、red flour beetle、rice、maize、sorghum、Brachypodium、Arabidopsis、soybean 和 teosinte 等对象。它不是 NTv2-500M D 的结果，不能用于证明 D 的外部泛化，也不能与 D 的 F1 直接合并。该 screen 对 insect stress 对象很低、对部分植物较好，适合帮助选择未来 panel 和诊断标签风险。

## 第一批候选物种建议

这里的“候选”表示可以进入资格审计，不表示已经获得独立终端资格。

### 优先候选：一套脊椎动物 + 一套无脊椎动物

1. western clawed frog / *Xenopus tropicalis* / xenTro10：补齐两栖类，Tiberius 有 `model_cfg/vertebrates.yaml`，当前配置 `softmasking: false`。它的当前 D 任务监督状态不是六物种之一，但历史计划曾把它列入 A2/vertebrate 角色，因此结果只能称历史候选上的外部 screen。
2. western honey bee / *Apis mellifera* / apiMel2：代表昆虫，Tiberius 有 `model_cfg/insecta.yaml`，当前配置 `softmasking: false`。*A. mellifera* 出现在该 Tiberius insecta checkpoint 的训练物种表中，因此它不能承担 Tiberius 下游的类群外部 holdout；D 的 TE screen 仍可作为任务外部 screen。现有标签来源适合做 coverage/recovery 诊断，不能单独承担生物真值结论。
3. red flour beetle / *Tribolium castaneum* / triCas2：与 honey bee 不同的昆虫谱系，Tiberius 同样使用当前 `insecta.yaml`（`softmasking: false`）。现有来源为旧 RepeatMasker 输出，结果按 source-dependent screen 解释。

这三者比重新增加另一个哺乳动物更能检验“跨脊椎动物和跨无脊椎动物”的边界。它们的证据等级由同 assembly 来源、标签覆盖、历史候选暴露和 pretraining exclusion 状态决定；当前不能把它们称为 untouched independent test。

### 第二批：植物作为单独的跨界 stress，而非动物模型泛化主结论

rice、maize 和 sorghum 有本地 TE BED/RepeatMasker 来源，Tiberius 可分别使用 `model_cfg/angiosperms.yaml`。它们可以检验 D 的 cross-kingdom signal，但植物的 LTR、nested insertion 和库覆盖机制与动物不同，应作为单独的 cross-kingdom 分析，不把它们混入动物 macro F1。真菌候选需要另外处理 RIP、repeat depletion 和注释质量，不应在第一批动物实验中顺带加入。

已完成的鸭嘴兽、海胆和 *C. briggsae* 结果应保留作“已有外部诊断”，不重复计算；如果希望把它们用于论文主结果，需要先把标签覆盖、assembly 范围和 historical exposure 写成独立的结果表。

## 固定推理方案

### 有标签评估入口

对每个通过资格审计的候选，先生成独立的 `TEST/<species>.jsonl.gz`，其每条 record 至少保留 `sequence`、`labels`、`split`、`assembly`、`chrom`、`start`、`end`、`tile_id` 和 `half`。标签中的 `1/0/?/H` 语义沿用 `calibrate_evaluate_x0.py`；`?` 不进入主要 callable 分母，`H` 单独作 hard-N guardrail。

固定 D seed42 的评估命令形式为：

```bash
python3 scripts/experiments/CROSS-SPECIES-L1-20260903/calibrate_evaluate_x0.py apply-only \\
  --model-dir /home/users/j/jwang/ab-initio-TE/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/train/seed42/12307410_1/final_model \\
  --tokenizer-dir /home/users/j/jwang/ab-initio-TE/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/train/seed42/12307410_1/final_model \\
  --model-code-dir /home/users/j/jwang/ab-initio-TE/.backup/pretrained_models/nucleotide-transformer-v2-500m-multi-species \\
  --data '<species>=<prepared TEST jsonl.gz>' \\
  --calibration-json /home/users/j/jwang/ab-initio-TE/outputs/CROSS-SPECIES-L1-UPSTREAM-20260904/evaluate/seed42/12353905_1/calibration.json \\
  --metrics-json '<new output>/metrics.json' \\
  --batch-size 12
```

命令不接受 threshold 参数；阈值从固定 CAL 文件读取。外部候选不能参与 CAL、阈值选择、模型选择或 MoE 路由选择。本轮外部 screen 固定 seed42 单次运行；结论由固定 checkpoint、固定面板和配对 endpoint 定义，不以补做第二个 seed 作为收束条件。

本轮 frog/bee/beetle screen 的四个区域来自各自冻结 `chrom.sizes` 文件的前四个可用行，每个区域取居中的 1,048,576 bp；这是可复核的 source-order 选择辅助，不把合成 report 中的字段解释为真实 NCBI molecule/assembly-role 注释。RC0 复用的 `phase_offset_bp=3` 只保留为一个预先声明的诊断 arm；native D 的主 endpoint 始终是 contig origin 0 的 F arm，不搜索相位，也不按最好 arm 报告结果。

### 无标签 FASTA 生产入口

无标签部署可以使用 sequence-only FASTA 接口。当前 D calibration 文件同时包含 `calibration_protocol: CROSS-SPECIES-L1-X0-PLATT-V1` 和 upstream `protocol: CROSS-SPECIES-L1-UPSTREAM-20260904-V1`，现有接口的 protocol guard 可以匹配，不需要身份兼容补丁。无标签输出只能是 material probability/connected runs，不能生成 precision、recall、F1 或 family identity。

### 与 Tiberius 的对应关系

| 类群 | Tiberius config | 备注 |
|---|---|---|
| Mammalia | `mammalia_softmasking_v2.yaml` 和 `mammalia_nosofttmasking_v2.yaml` | 仅用于哺乳类配对输入；P3 外部结果属于另一模型 |
| Vertebrata | `vertebrates.yaml` | frog、lizard 等非哺乳脊椎动物候选；当前 `softmasking: false` |
| Insecta | `insecta.yaml` | bee、beetle 等候选；当前 `softmasking: false`，且 *A. mellifera* 在该 checkpoint 的训练物种表中 |
| Angiosperms | `angiosperms.yaml` | rice、maize、sorghum 等植物候选 |
| Fungi | `fungi.yaml` | 后续单独的真菌实验 |

Tiberius 的类群 checkpoint 不能被当作 D 的 TE 结果；它只规定下游基因注释的配对模型。当前 frog/bee/beetle screen 不自动构成 Tiberius softmasking utility 实验资格。P3-Tiberius 已完成的 cow/platypus 结果也不能归给 D。

## 资源上限和分阶段策略

先做每个候选 4 个固定、assembly-report 预先决定的 1-MiB 区域；区域不能按模型分数、基因密度或标签阳性率选择。既有 D 外部 timing 在旧 GPU 上约 30–35 秒/MiB，batch 12；因此 3 个候选的模型 forward 远低于 1 GPU 小时。准备和 Label-A 生成是主要 CPU/I/O 成本，应单独预算，建议第一轮每物种最多 16 CPU、96 GB、2 小时准备上限，GPU 每物种 1 张卡、2 小时上限，超过上限停止并报告工程失败。

只有候选的 assembly、标签来源、历史暴露、callable/unknown/hard-N 覆盖和实际证据等级已经记录，才考虑扩大到全 assembly。全基因组规模不能按 4-MiB screen 的成本线性乐观外推；候选 bp、标签生成方式、I/O 和输出缓存确定前，不预设总 GPU 小时。

## 六物种 D DEV 的固定序列和标签路径

父任务的 paired context 干预可以读取已经使用过的 DEV，不能把它称为独立测试。远端精确路径为：

```text
/home/users/j/jwang/ab-initio-TE/outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202/DEV/human.jsonl.gz
/home/users/j/jwang/ab-initio-TE/outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202/DEV/mouse.jsonl.gz
/home/users/j/jwang/ab-initio-TE/outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202/DEV/chicken.jsonl.gz
/home/users/j/jwang/ab-initio-TE/outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202/DEV/zebrafish.jsonl.gz
/home/users/j/jwang/ab-initio-TE/outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202/DEV/pig.jsonl.gz
/home/users/j/jwang/ab-initio-TE/outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202/DEV/c_elegans.jsonl.gz
```

读取函数是 `read_jsonl(path)`，位于 `scripts/experiments/CROSS-SPECIES-L1-20260903/calibrate_evaluate_x0.py`；它使用 `gzip.open(path, "rt")` 并对每行执行 `json.loads`。序列在 `record["sequence"]`，标签在 `record["labels"]`，tile 对应关系由 `tile_id` 与 `half` 给出。配对干预必须复用 `sequence_tokens`、`project_token_margins` 和 `assemble_tiles` 的 6-bp/尾部投影语义，不读取 CAL、CONF 或任何 sealed 数据。

## 形成 claim 前必须补齐的项目

1. 每个候选的 exact assembly、FASTA、RepeatMasker/Dfam 版本、label provenance、P/U/N/H 规则和全域 callable 分母。
2. 监督暴露、模型选择、CAL、DEV、历史评分反馈和 backbone 逐 assembly 暴露；未知 backbone exposure 时只写“无目标物种任务监督”，不写“完全未见”。
3. 至少一个 label-rich 的非哺乳动物和一个 label-poor 的非哺乳动物，并把 reference agreement、positive recovery 和独立证据分开。
4. 每物种 F1/P/R、AP、hard-N、segment/boundary 和 worst-species，所有结果保留，不按结果删物种。
5. 如果固定外部 screen 显示跨类群且可重复的 negative transfer，再单独设计专家/adapter/MoE 实验；当前结果不预设 MoE，也不把它当作本轮必要条件。

## 固定 screen 已完成

Slurm `12849284_0–2` 全部完成，固定 D/CAL/阈值，每种四个预先选定 1-MiB 区域。native F 是唯一主 arm；RC、平均和相位诊断保留在原始结果中，不按结果选择。

| 物种 | strict TE 参考并集 bp | native reference-positive recovery | comparator F1 |
|---|---:|---:|---:|
| *X. tropicalis* / xenTro10 | 1,390,306 | 0.885797 | 0.837062 |
| *A. mellifera* / apiMel2 | 637 | 0.857143 | 0.079603 |
| *T. castaneum* / triCas2 | 3,622 | 0.579514 | 0.010340 |

三者均未参与 D 的六物种监督，但不是此前完全未观察的项目候选。蜂和甲虫的标签覆盖不足，不能用 comparator F1 声称生物学准确率或由其挑选下一种动物。它们揭示下一步需要改善参考证据资格；不能把缺少标签自动解释为模型正确。完整来源、原始四臂和分母见 [结果报告](../../../reports/ANIMAL-GENERALIZATION-CLOSURE-20260917/RESULTS.md)。历史 transfer screen 和 P3/Tiberius 结果仍不归给 D。

## 后续真实参考的资格补充

2026-09-17定向核读公开原始来源后，不能把候选名单直接当成已获得全基因组真值：

- [FlyBase官方数据说明](https://wiki.flybase.org/wiki/FlyBase:Downloads_Overview)明确其D. melanogaster自然TE插入集合限于保留两端完整的插入。它适合独立来源的已知插入恢复评价，不能把未标注区域全部当负类；canonical TE sequence set也不是全基因组插入坐标真值。当前的其他Drosophila物种页面不自动意味着有同等程度的现代全基因组TE注释。
- [TE_Bench作者仓库](https://github.com/hkania/TE_Bench)提供GARLIC模拟、模拟真值生成和给定注释的评分流程；真实输入可带外部参考进入评分。它本身不解决某个真实物种的参考完备性。本项目100Mb数据是该路线的派生模拟，不是独立生物学真值。
- [TEtrimmer原论文](https://www.nature.com/articles/s41467-025-63889-y)覆盖六种生物及三套模拟，但真实评价大量采用策划参考库后的RepeatMasker注释；这是有价值的库依赖基准，不能仅因论文已发表就称为对所有方法独立的真值。

下一面板需同时保留参考来源、完整度和方法依赖：完整插入positive recovery、宽覆盖材料agreement、匹配非TE背景/独立验证是不同端点。先选择符合端点的数据，再固定物种和区域；不继续根据当前D分数调整名单。
