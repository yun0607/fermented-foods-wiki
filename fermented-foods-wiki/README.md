# 發酵食物科學百科 — LLM Wiki

**專案狀態：已核准 5 篇條目與 5 份公開來源，詳見文章索引與匯入紀錄。**

## 專案概念
供完全不熟悉發酵食品的一般大眾閱讀，涵蓋發酵原理、常見食品、健康、製作、食品安全與保存。所有正式知識敘述均須可追溯至公開來源。

## 資料夾
- `AGENTS.md`：AI Agent 的操作與檢查規則（以本檔為準）
- `raw/`：收集原始公開資料，**不要放個資或機密文件**
- `sources.json`：來源 metadata、對應館藏檔案與審查狀態
- `wiki/articles/`：通過檢查的 Markdown 條目
- `wiki/index.md`：依分類的文章索引
- `wiki/log.md`：Ingest 和重試紀錄
- `wiki/review/`：審查表與有爭議的待確認記錄
- `templates/`：文章、來源、審查紀錄模板
- `scripts/lint_wiki.py`：可執行的結構與引用驗證工具
- `reports/`：實際檢查輸出檔
- `docs/`：GitHub Pages 公開閱讀介面
- `scripts/build_wiki_site.py`：從已核准的 Wiki Markdown 產生網站，需 Python 3.9 以上版本

## 操作順序
1. 先把 1–2 篇公開來源放進 `raw/`，並在 `sources.json` 建立來源 ID 及 metadata。
2. 使用 `templates/article.md` 建立條目，來源 ID 要對照 `sources.json`。
3. 跑 `python3 scripts/lint_wiki.py`，修正格式與引用問題；另由 AI 在**新的審查對話**或人工比對原始來源。
4. 每輪把問題、修正與通過狀態寫進 `wiki/log.md`，最多自動重試 3 輪。
5. 首批通過再擴充至至少 5 篇公開來源；最終跑 `python3 scripts/lint_wiki.py --strict`。
6. HTML 簡報為另一階段，本專案目前未建立。

## 執行檢查
```bash
python3 scripts/lint_wiki.py
python3 scripts/lint_wiki.py --strict
```
一般檢查驗證文章結構與來源引用。累積至少 5 筆不同的已核准來源，且均被已核准文章引用後，再使用嚴格模式驗收。

## 產生與預覽網站

更新 `wiki/articles/` 中已核准的文章後，在專案根目錄執行：

```bash
python3 scripts/lint_wiki.py --strict
python3 scripts/build_wiki_site.py
python3 scripts/build_wiki_site.py --check
python3 -m http.server 8000 --bind 127.0.0.1 --directory docs
```

開啟 `http://127.0.0.1:8000/` 預覽。網站包含五大分類、文章目錄、全文及原始來源連結。文章從 Markdown 產生，樣式位於 `docs/styles.css`。`--check` 驗證已產生的首頁是否與現有條目一致。

## 發布到 GitHub Pages

1. 在 GitHub 建立空的公開儲存庫，例如 `fermented-foods-wiki`。
2. 將專案與 `docs/` 一起提交到本機 Git。首次連結遠端時，將下方的 `OWNER` 和 `REPOSITORY` 換成 GitHub 帳號及儲存庫名稱，再推送 `main`。

   ```bash
   git remote add origin https://github.com/OWNER/REPOSITORY.git
   git push -u origin main
   ```

3. 開啟儲存庫的 **Settings → Pages**，在 **Source** 選 **Deploy from a branch**，選取 **main** 和 **/docs**，再按 **Save**。
4. 部署完成後，在 **Settings → Pages** 點 **Visit site**。專案網站通常位於 `https://OWNER.github.io/REPOSITORY/`，可將該網址交給老師。

[GitHub Pages 官方設定說明](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)

## 給 Coding Agent 的起始命令
「請先閱讀 AGENTS.md。現在只 Ingest 1–2 份已核實的公開來源，記錄來源 ID，建立文章，執行 Lint，並用獨立審查方式核對內容；不通過就按 Graph 回退，最多 3 輪。更新 wiki/log.md，不要產生簡報。」
