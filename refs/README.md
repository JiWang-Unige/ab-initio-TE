# refs/ — 文献与 SOTA 归档区

规范化保存每个 SOTA 候选 / 中途发现文献的**原始材料 + 细节档案**，方便后续审查可比性
（数据集来源、指标实现、split 口径）而不必反复重新搜。

## 布局

```
refs/
├── sources.md            # 索引：一行一个已归档来源（slug | title | type | pdf | repo | added_by | date）
├── pdfs/<slug>.pdf       # 论文 PDF（arXiv 自动下载；其他手动拖入）
├── repos/<slug>/         # 代码仓库（git clone --depth 1；过大则只留 <slug>.link.md）
├── supp/<slug>/           # 论文补充材料 PDF/zip/table（下载失败时由用户手动补）
├── dossiers/<slug>.md    # SOTA 细节档案：数据集来源 / 指标实现 / split / 权重&license / 复现要点 / 相关性
└── archive_source.sh     # 自动归档脚本（下载 PDF + clone repo + 建 dossier + 写索引）
```

## 怎么用

```bash
# 归档一个 arXiv 论文 + 其 GitHub 仓库
bash refs/archive_source.sh --slug tiberius-2025 --arxiv 2501.12345 \
  --repo https://github.com/org/tiberius \
  --supp-url https://example.org/supplementary.pdf \
  --title "Tiberius: ..." --type sota \
  --why "exon-level F1 SOTA 锚点，待核实 split/metric"
```

- `--type sota`：来自 /sota-inventory 的正式 SOTA 候选。
- `--type note`：来自 /note-add 的中途发现文献。

## 谁写这里

- `/sota-inventory`：把每个验证过的候选归档（PDF/repo/dossier）。
- `/note-add`：中途发现的文章归档 + 填 dossier 相关性。
- dossier 的 dataset/metric/split 字段在归档时建骨架，由 sota-inventory 的 WebFetch/本地全文/补充材料核实后填实。下载失败会写入 `failed(url)`，由 `scripts/sota_failure_report.py` 汇总给主人手动补。

> slug 命名约定：`<firstauthor-or-name>-<year>`，小写连字符，如 `tiberius-2025`、`bilstm-crf-2023`。
