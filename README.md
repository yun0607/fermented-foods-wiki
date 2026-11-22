# 發酵食物科學百科 — LLM Wiki

五大主題涵蓋發酵原理、常見食品、健康、自製與食品安全。繁體中文文章供初學者閱讀，以 SRC-001 至 SRC-008 八篇指定公開來源為依據。

## 從這裡開始

- [Wiki 文章索引](wiki/index.md)列出五大主題與正式條目。
- [來源清單](sources.json)可查書目、原文網址、館藏摘要及核准範圍。
- [Ingest 與驗證紀錄](wiki/log.md)可查來源切換原因、修正輪次及人工覆核事項。
- [切換前備份](archive/2026-11-22-before-eight-sources/README-archive.md)保留舊文章、來源、館藏、索引與歷史紀錄。

## 驗證

在專案根目錄執行：

```bash
python3 scripts/lint_wiki.py
python3 scripts/lint_wiki.py --strict
```

一般 lint 檢查書目欄位、文章結構、逐段引用與索引。嚴格模式另要求八筆指定來源已核准並被核准文章引用，以及五大主題都有核准文章。科學內容、初學者可讀性及食品安全另由獨立審查對照原文。

## 網站階段

本階段交付 Markdown Wiki。`docs/` 屬於切換前的歷史閱讀介面。新版網站規劃採一頁式 Wiki。
