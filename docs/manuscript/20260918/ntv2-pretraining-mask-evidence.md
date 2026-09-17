# NTv2-500M 预训练与 TE masking：可支持的范围

2026-09-18 重新检查官方模型卡、原论文与数据入口。结论：现有项目的 0.522 读出不能用来宣布“预训练不含 TE 信息”；TE 是否被预处理移除也尚未证实。

| 问题 | 本轮可核实证据 | 不能推出的结论 |
| --- | --- | --- |
| 500M 是什么 | NTv2 模型卡明确是约五亿参数，不是 500 Mb 输入 | 不能与基因组大小单位混用 |
| 预训练内容 | 官方描述 850 个 NCBI 基因组、约 174B nt；该模型不含植物和病毒 | 不能据此断言每个外部测试物种、assembly 或区间从未出现在预训练中 |
| mask 是什么 | 模型卡描述随机 token MLM：选取 15%，再按 80/10/10 替换 mask/random/保持 | 不等于 RepeatMasker 或将 TE 变为 N |
| 输入清理 | 原文 Data preparation 说非 A/T/C/G 字符转成 N、6-mer 优先 tokenization | 未说明源 FASTA 的 TE softmask 状态及小写字母规范化顺序；不能自动推导 TE 被删或全保留 |
| 预训练是否学习重复信息 | 原文 Results 报告 NT Multispecies 2.5B 的重复元素 token 重建良好 | 不等于 NTv2-500M 在本项目 mean-pooled TE/BG 分类达到高准确率 |
| .5221 的适用对象 | 项目历史特定 GENERanno、512 bp、特定 pooled representation/5NN 读出 | 不是 NTv2 分数、不是信息量上界、不是零样本 TE 标注性能 |

公开数据入口 `InstaDeepAI/multi_species_genome` 本轮网页返回内部错误；无认证读取 README/API 返回 HTTP 401。没有绕过访问控制，也没有取得原始预训练语料或完整预处理脚本。因此 TE hard/softmask 的强断言保持未核实。

论文表述应根据本项目的配对实验分别说明：预训练表示的受监督读出、无监督聚类、类别微调后读出变化、实际碱基层面标注，是四种不同证据。二维 BG 聚团不必然意味着原空间的 TE/BG 高可分性；需要相同记录、各类 P/R 和支持数、固定读出器，以及组成与 pooling 检查。即使改进，也不单凭该图推论生物学机制或完全排除记忆。

来源：

- [NTv2-500M 官方模型卡](https://huggingface.co/InstaDeepAI/nucleotide-transformer-v2-500m-multi-species)，Training data / Preprocessing / Training procedure。
- [Dalla-Torre et al., Nature Methods](https://www.nature.com/articles/s41592-024-02523-z)，Results 的 NT Multispecies 2.5B token reconstruction；Methods 的 Pre-training datasets / Data preparation / Training。
- [官方模型文档](https://github.com/instadeepai/nucleotide-transformer/blob/main/docs/nucleotide_transformer.md)。
