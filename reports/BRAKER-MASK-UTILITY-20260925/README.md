# BRAKER 完整流程应用验证：执行登记

2026-09-25，按用户新的自主执行指令启动。[固定协议](../../docs/experiments/BRAKER-MASK-UTILITY-20260925.md)、[精确部署输入](../../configs/BRAKER-MASK-UTILITY-20260925.inputs.json)、[作业登记](jobs.jsonl)。

目的为鸡/斑马鱼完整 ETP 的 D、RM2_FULL、RED_FULL 六臂应用比较，不把旧同预算 pilot 的局限抹去。两个物种都是 D 微调物种；RNA/外源蛋白在同物种各臂相同。所有长任务运行于 private CPU，无 GPU。

## 已实际完成

共享 OrthoDB v12 Vertebrata 文件已下载、完整解压过滤，移除鸡 taxid9031 的17,274条与鱼 taxid7955 的25,793条，保留19,350,805条外源蛋白、10,487,364,393个氨基酸字母。原始文件6,188,932,489 bytes。原生状态为 `PROTEINS_READY`，统计见 [proteins-status.json](proteins-status.json)。这仅是输入准备完成，不是基因注释或科学结果。

精确 ENA paired RNA 元数据已保存：鸡4类组织/细胞类型共20,490,058,265压缩bytes，鱼WT24/48hpf共6,055,852,095bytes。原有鱼PRJNA899844每run过大，不纳入本次25GB/物种预算；没有先观察mask效果再选输入。鱼不引入KO，不把胚胎RNA当完整组织覆盖。

## 正在执行与衔接

- `13194294`：真实 ETP bundled sample已完成。最终GTF含1,537条CDS feature，GeneMark/AUGUSTUS中间GTF存在；原生状态ETP_EXAMPLE_COMPLETE。Slurm共811秒，1.8022 allocated CPU-hours；仅工程运行资格，不作准确率结果。见 [smoke-status.json](smoke-status.json)。
- `13194295 / 13194296`：鸡/鱼完整 D、RM2 重建及全基因组 RED；原先参考FASTA的大小写不继承。
- `13194304`：共享蛋白准备完成。
- `13194313 / 13194314`：RNA获取和 HISAT2 比对，分别依赖上述掩码准备完成，生成同物种三臂共用的无注释辅助 BAM。

评价准备脚本在新预测前固定常染色体区域、D TRAIN/CAL排除、旧用途halo排除、完整RefSeq分母与独立长读长结构。正式六臂由 `run.sbatch` 固定为两个物种 × 三种mask，最多两臂并发，每臂16CPU/96GB/72h；只有真实smoke及共同输入、两物种评价域均准备好后才运行。不得把提交或exit0当作科学完成。

独立鱼 processed GTF 只承担转录结构支持。作者参考比较信息保留；`u`不是coding真值，缺少RNA匹配不算FP。鸡暂无可直接使用的 processed IsoSeq坐标，不把现有证据说成两物种均有独立完整CDS真值。

固定比较与失败都保留；不看新分数改区域、模型、阈值、分母或预算。当前是执行状态，尚无新的完整BRAKER科学比较结果。

## 新预测之前的实现核实

GTF scorer已用真实bundled BRAKER格式核对，独立start/stop codon行会并入CDS坐标并去重；预测缺codon标记不会从错误分母消失。鱼长读长文件使用numeric contig，固定映射1–25到chr1–chr25；class_code从transcript行取，transcript span不会被当作exon。正负链、独立codon、跨旧halo排除和numeric-contig小型fixture通过。

评价准备13194346在鱼参考同CDS链多名称歧义处停止，鸡分母已完成且保留。没有读取目标BRAKER分数。鱼主域4组、全域5组坐标相同的参考单位已按exact-CDS连通合并，保留名称/源行明细。恢复13194364完成，未覆盖原失败目录；正式六臂13194349已更新为依赖RNA准备及成功的13194364。原生失败15秒、0.0167 allocated CPU-hours计入。

## 评价准备终态

恢复33秒完成，原失败15秒一并保留，评价准备累计0.0533 allocated CPU-hours。全局状态EVALUATION_READY。鸡主域201,407,137 bp、6,588参考loci；鱼主域769,648,038 bp、14,576参考loci。[准备摘要](evaluation-preparation.json)

鱼独立长读长文件取得48,086个多外显子结构，8,523个与全域完整RefSeq CDS内含子链匹配，主域匹配4,874个。该子集仅增强结构支持，不提供独立CDS起止/蛋白功能真值；其余结构不自动视为非编码。后续须依据preparation.json里的鱼zebrafish-r2路径评分。[长读长资格统计](zebrafish-long-read-summary.json)

正式六臂仍等待两个物种的全基因组mask和共同RNA BAM完成；已排入依赖队列，后续由已恢复的heartbeat自动核实、分析及Git同步。
