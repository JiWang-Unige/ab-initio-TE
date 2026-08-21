# wiki/ — 轻量可检索研究 wiki

随时把 **ideas / 看到的文章 / 跑过一次的笔记** 存下来并索引，方便知道下一步方向。
不是 Research OS 那套重型 wiki（raw/concepts/context_packs/全文索引），而是 grep 可达的精简版。

## 三类可索引内容
- **ideas/`<slug>`.md** — 一个假设/方向（status: untried / tried / parked + next step）
- **notes/`<slug>`.md** — "跑过一次"的笔记（what ran + quick result + takeaway + next direction）
- **papers** — 存在 `refs/dossiers/`（经 `refs/archive_source.sh` 归档），INDEX 自动汇总

## 用法
```bash
# 记一个 idea
bash wiki/wiki.sh add-idea --slug crf-multiscale --title "CRF + 多尺度上下文" \
  --hypothesis "U-Net 多尺度融合改善长序列边界" --why "长序列 backbone 收益存疑" \
  --next "screen 一版 CRF+UNet head" --refs "tiberius-2025"

# 记一个"跑过一次"的笔记
bash wiki/wiki.sh add-note --slug crf-seed0-try --title "CRF seed0 quick run" \
  --what "EXP-A-001 CRF screen seed0" --result "segment_f1=0.441" \
  --takeaway "略超 anchor 但噪声大" --next "多 seed 复跑"

# 重建索引 / 检索
bash wiki/wiki.sh index
bash wiki/wiki.sh search "CRF"
```

## 谁写这里
- `/note-add --kind idea|note`：统一捕获入口（paper 走 refs 归档，idea/note 走这里）。
- `/pursue`、`/result-log` 等可在产生洞见时 `add-note` 留痕。
- `wiki.sh index` 在每次 add 后自动重建 `INDEX.md`。
