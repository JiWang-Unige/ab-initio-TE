---
name: grill
description: "A3.5· A deep two-phase exchange on the USER's research direction AFTER papers/code have been read (post /sota-inventory, pre /configure-project)."
---
> Codex/Antigravity note: this generated skill is mirrored from the Claude skill. When the body mentions a `/skill-name` command, Codex users should invoke `$skill-name`; Claude users keep `/skill-name`.


# Grill: deep co-development + adversarial clarification of the research direction

`/research-interview` 在**模糊想法**期拷问过一次。但读完 `/sota-inventory` 的论文+代码后，你对方法/指标/数据集有了**新认识**，方向也会变——此时该**再深聊一次**，在烧 GPU 前既把**思路本身想深想透**、又把**技术细节钉死**。

本 skill 是**两段式**，缺一不可：
- **Phase 1 · 深度思路共创**（思考伙伴，不是只会挑刺）：把主人的想法 steelman 到最强、铺开假设空间、找出最有趣/最可能"出彩而非增量"的角度——和主人**一起把这个 idea 想得更深更远**。
- **Phase 2 · 对抗收敛拷问** = grill-me（苏格拉底式追问、逼出具体答案）+ devils_advocate（对抗式找最弱假设、反谄媚）——把发散出的想法收敛成**可辩护的具体决策**。

> 为什么要 Phase 1：纯对抗式拷问容易只盯"流程/可比性/实现细节"，把主人逼进防御姿态，却没**和主人就研究思路本身做有深度的智力交流**。先共创再拷问 = 既不谄媚（Phase 2 照样毫不留情），又真正参与了主人的 thinking。

**位置**：`/sota-inventory` 之后、`/configure-project` 之前。也可在任何"方向发虚"时随时调用。

> **建议在 plan 模式下跑本 skill**（Claude `plan` / Codex plan）：grill 全程只读 docs/dossiers + 和主人来回深聊（共创+拷问），聊定后 `ExitPlanMode` 退出再 append `docs/00` 澄清合约——正是 plan 模式"只读+反复细聊"最擅长的场景。
> **长讨论的落盘（你自控压缩，不必每轮自动存）**：grill 可能聊很久。聊定后照常 append `docs/00` 澄清合约；**若讨论很长、你准备 `/compact`，先让 agent 把当前已得结论 flush 到 docs/00（或 docs/11 §4）再压**——不必每聊一句就存（太碎费 token）。plan 模式聊久了先 `ExitPlanMode` 落盘再继续。（撞上 auto-compact 才会丢最后一段未 flush 的，故 context 快满时主动 flush。）

## Step 0 · 读新认识（基于已读到的论文/代码，不要泛泛拷问）
读 `docs/01`（综述）、`docs/02`（验证过的 SOTA 表）、`refs/dossiers/*`（已下载论文/代码里**真正**的指标算法/数据集/split）、`ACTIVE_GOAL.json`、`$ARGUMENTS`（用户的当前方向/假设）。拷问必须**扣住这些新事实**——例如 dossier 里发现某 SOTA 的指标是 macro-F1 而非你以为的 micro，就拿这个逼问。

## Phase 1 · 深度思路共创（先和主人把 idea 想深，再拷问）
**目标**：不是评判，是**参与主人的 thinking**——把想法想得比主人单独想更深、更远、更有趣。逐项做（inline 对话式，鼓励来回）：

1. **Steelman（最强复述）**：先把主人的方向**复述成它最强的版本**——"如果你这个想法对，最深刻的解释是 ___；它真正在赌的底层机制是 ___"。让主人确认/修正"我是不是理解到了你想表达的最强形态"。（这步建立信任，也暴露双方理解差。）
2. **铺开假设空间**：这个 idea 属于哪一类更大的假设家族？相邻还有哪些"近亲想法"主人没提但值得放上桌？用 `lit_search.py similar/search` + MCP `anysearch`(academic) / exa 拉相邻思路，**把想法放进更大的智力地图**，不是孤立看。
3. **找"出彩点" vs 增量**：哪个版本的这个想法会是**令人意外的结果**（surprising，值得发表）而非"又涨了 0.5 个点"的增量？"如果只能让一个机制为真、你最希望哪个为真？"——逼出主人真正兴奋的内核。
4. **建设性延伸**：主动**提出更强的变体 / 没想到的组合 / 可迁移的邻域结论**（"你这个 + docs/02 里 X 的 trick 合起来可能更狠"）。这是共创，不是附和——延伸必须有机制理由，不是为了夸。
5. **想透"为什么是现在/这里"**：为什么这个方向在**本任务的数据与标签结构**上特别有戏？（与 Phase 2 的逻辑链拷问衔接，但这里是**一起探索**而非逼问。）

**纪律**：Phase 1 是发散+共创，但**不降低标准**——不为了气氛附和，延伸/赞同都要给机制依据；想法本身的硬伤照样在 Phase 2 毫不留情地打。Phase 1 让主人**愿意把真实想法摊开**，Phase 2 才有东西可钉。

## Phase 2 · 对抗收敛拷问

## Step 1 · 八维对抗拷问（针对"研究方向/技术假设"，非论文）
逐维提问，每维**至少一个非此即彼或要数字/机制的尖锐问题**，禁止接受"应该会更好""大概"这类空答：

1. **核心赌注**：你这次架构上到底押什么？一句话机制 delta 是什么？最强的反方论证是什么（为什么它可能不 work）？
2. **选择性偏置**：你是不是只盯着支持你想法的论文？docs/02 里有没有与你方向**矛盾**的证据被你忽略了？
3. **逻辑链**：为什么机制 X 会在**本任务的标签结构**上带来指标提升？中间有哪些**隐藏假设**？（如"CRF 的转移建模能帮序列标注"——本任务的标签真有强转移依赖吗？）
4. **可比性**：你打算的比较口径，和你刚读到的 SOTA **同 split/同 metric 实现/同 preprocessing** 吗？不一致点在哪？
5. **替代方案**：为什么是 X 不是 Y/Z？（用 `python3 scripts/lit_search.py similar <paperId>` 拉出该方向的替代，逐一问"为什么不选它"）
6. **过度外推**：你打算用小样本 screen 的证据去赌 full-data？有没有"小样本走运、大样本崩"的风险？
7. **So-what / 成本**：就算 work，超 SOTA 的幅度够发论文吗？这条线值得占 GPU 吗？机会成本是什么？
8. **Frame-lock**：整条方向背后有没有一个**没被说出口的前提**？（如默认"序列建模越长越好"）如果这个前提错了，方向还成立吗？

## Step 2 · 反谄媚纪律（借 devils_advocate）
- 用户答得含糊 → **点破并复述**："你回答的是 X，但我问的是 Y，请具体到机制/数字。"
- 给用户的答案打分 1-5（1=断言无据 / 5=有论文或数据支撑的具体答案）。**< 4 不算把这点钉死**，继续追问或标为"待 /reproduce-baselines 或 lit_search 验证"。
- **压力≠证据**：用户反复坚持同一个空答不提高分数。不要为了和谐而放过。
- 但**只攻论点不攻人**；用户给出有论文/数据支撑的答案就如实接受并推进。

## Step 3 · 哪些问题"问了也答不出"→ 转成可执行验证
有些技术细节用户和模型都拿不准（如"这个数据集到底是纯 raw 还是已滤过 FP"），**别空辩**——标记为：
- `→ /reproduce-baselines`：需本地复现 SOTA 才能确认（指标算法/数据集 rawness/split）。
- `→ lit_search/exa`：需检索才能确认（某替代架构在相关领域怎么实现最好）。

## Step 4 · 产出"方向澄清合约"（含共创成果，喂给后续 /benchmark-roadmap）
inline 输出（不写死任何 docs/03，那是 benchmark-roadmap 的事；可 append 到 docs/00 的 `## direction_clarified_<date>`）：
```markdown
## Direction clarified <date>
- 想法最强形态(Phase 1 steelman): <一句, 主人确认过的最强版本>
- 共创浮现的更有趣角度/延伸: <bullets, Phase 1 一起想出来的 surprising 角度或更强变体>
- 核心架构赌注: <一句, 含 mechanism delta>
- 已钉死的技术决策: <bullets, 每条带依据/打分≥4>
- 仍开放、需验证的问题: <bullet → /reproduce-baselines 或 lit_search>
- 被劝退/降级的子方向 + 理由: <bullets>
- 最强反方论证（保留警惕）: <2-3 句>
```

## 边界
- grill **共创+拷问+澄清**，不替用户做方向决策；用户确认的答案才是后续 benchmark-roadmap 的输入。
- Phase 1 共创**不等于附和**——延伸/赞同必须有机制依据，硬伤一律留到 Phase 2 照打（反谄媚优先级高于气氛）。
- 不写 docs/03（roadmap 主体）。不 kill running job。
- 发现"答不出"的技术事实 → 明确转 `/reproduce-baselines` 或检索，不要靠辩论糊弄过去。

## Hand-off
- **Inputs from**: `/sota-inventory`(docs/02 + refs/dossiers)、用户的当前方向
- **Uses**: `scripts/lit_search.py`（similar/search 拉相邻思路与替代方案）、MCP `anysearch`(academic 找论文/general 找相邻工作)、MCP exa
- **Outputs to**: docs/00 `## direction_clarified_<date>`（含共创成果的澄清合约）
- **Next**: `/configure-project`（据澄清诉求让 AI 填 CLAUDE/cluster 配置，人闸）→ `/benchmark-roadmap`（定 paths）；开放问题转 `/reproduce-baselines`
