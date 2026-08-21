# TE 研究全览流程图 (v1 讨论草案)

> 2026-06-14 蕾姆综合【手稿 + v3/v4 + 03_roadmap + 旧A-H + landscape四队】绘制。
> **这是讨论底板，等待修改**。council / tri-review 待整条思路定稿后再上。
> 在 IDE/网页用 mermaid 渲染查看；⭐=核心创新点，⚠=头号风险，🚫=避雷。

## 一句话故事
首个用基因组基础模型做 **ab initio、跨物种(zero-human)、全长 TE 逐碱基注释 + 检测**的方法，配套填补空白的**跨物种 TE benchmark** → Nature Methods（方法+基准+资源三件套）。

## 主流程

```mermaid
flowchart TD
    Start(["🎯 目标: ab initio 跨物种 zero-human 全长 TE 注释模型 → Nature Methods"])

    subgraph P0["P0 · 地基 (M0)"]
        D0["数据 + typed 弱标签 (7 物种)"]
        D1["5-Tier 物种 split: 染色体级 + 同源去冗余"]
        D2["评测协议冻结: per-base macro-F1/AUPRC + per-element IoU + 边界 + 校准"]
        D3["baseline 复现: RepeatMasker / EDTA / EarlGrey"]
        D4["⚠ Evo2 显存 smoke + GENERanno 可及性"]
    end

    G0{"门: 数据就绪 + 协议冻结"}

    subgraph P1["P1 · GENERanno 监督 baseline (M1) — 发文主体雏形"]
        A1["GENERanno + 逐碱基头 → binary"]
        A2["⭐ 1D 检测头 DETR → 解决全长 + 显存"]
        A3["typed 多类: LINE/SINE/LTR/DNA/Helitron/other"]
        A4["手稿①② 3 模型 × 窗口对比"]
        A5["⭐ zero-human 训练 → 留出 hs1 评测"]
        A1 --> A2 --> A3
    end

    G1{"门: 跑通 + 留出物种第一个数 ≥ 进度门 0.55"}

    subgraph P2["P2 · Evo2 长上下文升级 (M2)"]
        B1["Evo2 LoRA/冻结 + 检测头"]
        B2["⭐ 嵌套 TE → DETR set-prediction"]
        B3["因果性处理: 双向头 / 解掩码"]
        B4["Caduceus 双向对照"]
    end

    subgraph P3["P3 · 泛化 + 评测方法学 (M3)"]
        C1["跨界泛化阶梯: no-human→animals→+plants→+fungi"]
        C2["进化距离 → 性能衰减曲线"]
        C3["⭐ no-human-on-human gold-standard (评测创新)"]
        C4["已知 / 未知家族分层"]
        C5["5 款传统工具系统对比"]
    end

    G2{"门: 严格超越传统工具 + tri-review"}

    subgraph P4["P4 · 投稿包 (M4)"]
        E1["多 seed paired + 校准 + 消融 + robustness"]
        E2["资源打包: benchmark + 权重 + 评测脚本"]
    end

    Pub(["📄 Nature Methods 投稿"])

    Start --> P0 --> G0 --> P1 --> G1
    G1 --> P2
    G1 --> P3
    P2 --> G2
    P3 --> G2
    G2 --> P4 --> Pub

    Avoid["🚫 避雷/搁置: CRF·HMM(旧E) | family嵌入聚类(旧G) | v3完整无监督/进化对比/生成→future work | PU-Learning本身"]
```

## 图例与纪律
- **四个核心创新点 ⭐**：① 1D 检测头(治全长+显存，超 YORO) ② zero-human 跨物种 ③ Evo2 长上下文吃全长TE ④ no-human gold-standard 可信评测。
- **决策门 {菱形}**：每个门是 go/no-go，不达标不进下一阶段。
- **并行**：P1 稳定后，P2(Evo2升级) 与 P3(泛化+评测) 可并行推进。
- **快速迭代**：Track A(小样本单seed扫架构/窗口) → 晋升 → Track B(scale多seed)；每轮 ≤3 正交方向，exp_id 隔离。
- **backbone 分阶段**：P1 GENERanno 先跑通(好微调、省算力) → P2 Evo2 破长TE死结。

## ⚠ 蕾姆标注的"最该先讨论"的开放点 (待改)
1. **检测式 vs 逐碱基的关系**：P1 同时画了"逐碱基头"和"检测头"，二者是谁主谁辅？是逐碱基为主+检测辅助，还是检测出 box 再转逐碱基评测？——这是架构核心，要定。
2. **手稿①② 与 zero-human 主线可能矛盾**：手稿①写"仅用 human 数据 fine-tune 看物种间泛化"(human训练→外推)，而 zero-human 主线是"排 human 训练→泛化到 human"(排human→内推)。**方向相反**，必须理清这两个到底要哪个、还是分别作不同实验。
3. **zero-human 卖点在 P1(GENERanno短窗) 就能立，还是要等 P2(Evo2长上下文)?**
4. **typed 粒度** 5类够不够；**主指标** per-base vs per-element 谁为先。

## 版本
v1 · 2026-06-14 · 讨论草案 · 待逐点修改后再上 council/tri-review
