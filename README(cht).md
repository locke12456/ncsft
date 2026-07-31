# Notion 程式碼檔案同步工具

一個用於將程式碼專案檔案自動同步到 Notion 頁面的 Python 工具。支援**雙向同步**、增量更新、目錄掃描，並為每個程式碼檔案建立獨立的 Notion 頁面。

## 功能特色

🔄 **雙向同步**: 推送檔案到 Notion，也可以拉取回本地目錄

📥 **拉取功能**: 從 Notion 頁面提取程式碼回到本地檔案

📁 **專案別配置**: 每個專案可擁有獨立的 .env 設定檔

📄 **獨立頁面**: 為每個程式碼檔案建立獨立的 Notion 頁面

🚀 **主動同步**: 類似 Git 的手動同步機制 - 你決定何時同步

💾 **智慧快取系統**: 專案別快取檔案避免重複上傳

🐍 **Python 實作**: 使用官方 Notion API 進行自動化操作

🌐 **多語言支援**: 支援 30+ 種程式語言和檔案類型

📚 **文件匯出**: 遞迴匯出 Notion 頁面樹（含子頁面）為 Markdown 檔案

## 支援的程式語言

- **Python** (.py)
- **C#** (.cs)
- **JavaScript** (.js, .jsx)
- **TypeScript** (.ts, .tsx)
- **Java** (.java)
- **C/C++** (.c, .cpp)
- **PHP** (.php)
- **Ruby** (.rb)
- **Go** (.go)
- **Rust** (.rs)
- **Swift** (.swift)
- **Kotlin** (.kt)
- **Scala** (.scala)
- **HTML/CSS** (.html, .css, .scss, .sass, .less)
- **Shell Scripts** (.sh, .bash, .ps1, .bat, .cmd)
- **設定檔** (.json, .yaml, .yml, .xml)
- **還有更多...**

## 安裝與設定

### 1. 安裝依賴套件

```bash
pip install -r requirements.txt
```

### 2. 環境變數設定

工具支援**專案別配置**。它會自動在專案目錄階層中尋找 `.env` 檔案。

複製 `.env.example` 為 `.env` 並填入必要資訊：

```bash
cp .env.example .env
```

編輯 `.env` 檔案：

```
NOTION_TOKEN=your_notion_integration_token
PARENT_PAGE_ID=your_parent_page_id
PROJECT_ROOT=./your_project_path
MAX_CONTENT_LENGTH=100000
CACHE_FILE=.notion_sync_cache.json
```

### 3. 取得 Notion Integration Token

1. 前往 [Notion Integrations](https://www.notion.so/my-integrations)
2. 點擊「New integration」
3. 填入名稱（例如：「Code File Sync」）
4. 選擇 workspace
5. 複製 Internal Integration Token

### 4. 取得父頁面 ID

1. 在 Notion 中建立一個新頁面（或使用現有頁面）
2. 邀請你的 Integration 到該頁面
3. 從頁面 URL 中取得頁面 ID

## 使用方式

工具現在支援**子指令**進行不同操作：

### 推送檔案到 Notion

```bash
# 推送當前目錄所有檔案
python [main.py](http://main.py) push ./

# 強制推送（更新所有檔案，忽略變更檢查）
python [main.py](http://main.py) push ./ -f

# 只推送特定語言檔案
python [main.py](http://main.py) push ./ -l python

# 推送特定副檔名
python [main.py](http://main.py) push ./ -e .py .js .css
```

### 從 Notion 拉取檔案

```bash
# 拉取所有已同步檔案
python [main.py](http://main.py) pull ./

# 強制拉取並覆寫現有本地檔案
python [main.py](http://main.py) pull ./ -f

# 拉取到指定輸出目錄
python [main.py](http://main.py) pull ./ -o ./pulled_code

# 拉取到指定目錄並強制覆寫
python [main.py](http://main.py) pull ./ -o ./pulled_code -f
```

### 專案統計資訊

```bash
# 顯示專案同步統計
python [main.py](http://main.py) stats ./
```

### 快取管理

```bash
# 清理已刪除檔案的快取記錄
python [main.py](http://main.py) clean ./
```

### 匯出 Notion 文件為 Markdown（docs）

將手寫的 Notion 文件（標題、表格、callout、toggle、巢狀子頁面）匯出到本地成為 Markdown 檔案，是 `push` 的反向操作。有子頁面的頁面會變成資料夾，沒有子頁面的頁面則變成單一 `.md` 檔。匯出過程有快取，可中斷後續傳，重跑時只會重新抓取有變更的頁面。

```bash
# 匯出單一頁面樹
python [main.py](http://main.py) docs <page-id-或-url> -o ./docs

# 匯出多個頁面樹
python [main.py](http://main.py) docs <page-id-1> <page-id-2> -o ./docs

# 只列出某頁面的子頁面，不進行匯出
python [main.py](http://main.py) docs --children-of <page-id> --list -o .

# 匯出某頁面底下的所有子頁面
python [main.py](http://main.py) docs --children-of <page-id> -o ./docs

# 強制重新下載，忽略快取
python [main.py](http://main.py) docs <page-id> -o ./docs -f

# 限制子頁面遞迴深度（預設 10）
python [main.py](http://main.py) docs <page-id> -o ./docs --depth 3
```

**docs 指令選項**

- `-o, --output`（必填）- 輸出目錄
- `--children-of PAGE` - 匯出 `PAGE` 底下的所有子頁面（不寫入該頁面本身內容）
- `--list` - 列出 `--children-of` 的子頁面後直接結束，不進行匯出
- `--env DIR` - 向上搜尋 `.env`（內含 `NOTION_TOKEN`）的起始目錄（預設：`.`）
- `--cache PATH` - 快取檔案路徑（預設：`{output}/.notion_docs_cache.json`）
- `-f, --force` - 忽略快取，強制重新下載
- `--depth N` - 子頁面遞迴最大深度（預設：10）
- `--date` - 記錄在每個檔案中的擷取日期（預設：今天）

**注意事項**

- 只需要 `NOTION_TOKEN`（不需要 `PARENT_PAGE_ID`），且即使未安裝 `notion-client` 也能運作（僅使用標準函式庫）
- Notion 託管的檔案／圖片連結是簽章過的網址，約一小時後失效；若需要長期保存這些附件，請留意匯出結束時列出的過期警告清單

### 指令參考

### Push 指令選項

- `-f, --force` - 強制更新所有檔案（忽略 hash 比對）
- `-l, --language` - 只同步特定語言（如 python, javascript）
- `-e, --extensions` - 同步特定副檔名（如 .py .js）

### Pull 指令選項

- `-f, --force` - 強制覆寫現有本地檔案
- `-o, --output` - 指定輸出目錄（預設：{專案名}_from_notion）

### 說明

```bash
python [main.py](http://main.py) --help
python [main.py](http://main.py) push --help
python [main.py](http://main.py) pull --help
```

## 工作原理

### Push 操作

1. **配置載入**: 從專案目錄階層中尋找並載入 .env
2. **掃描階段**: 遞迴掃描指定目錄中的所有支援程式碼檔案
3. **變更檢測**: 計算檔案的 MD5 hash，與本地快取比對
4. **同步處理**:
    - 建立新頁面（如果檔案是新增的）
    - 更新現有頁面（如果檔案有變更）
    - 跳過未變更的檔案（提高效率）
5. **快取更新**: 更新專案特定的同步快取檔案

### Pull 操作

1. **快取載入**: 載入專案特定的快取以尋找同步頁面
2. **內容提取**: 從 Notion 頁面取得程式碼內容
3. **檔案建立**: 用提取的內容重建本地檔案
4. **覆寫保護**: 除非使用 force 旗標，否則跳過現有檔案

## 頁面結構

工具會建立包含以下結構的 Notion 頁面：

- **檔案標題**: 檔案圖示和名稱
- **檔案資訊**: 路徑、程式語言和檔案大小
- **程式碼內容**: 具備語法高亮的程式碼區塊
- **分段內容**: 大型檔案會自動分割成多個程式碼區塊（受 Notion API 限制）

## 專案結構

```
ncsft/
├── [README.md](http://README.md)                    # 英文說明文件
├── README(cht).md              # 中文說明文件
├── requirements.txt            # Python 依賴套件
├── .env.example               # 環境變數範本
├── .gitignore                 # Git 忽略規則
├── [config.py](http://config.py)                  # 具動態 .env 載入的配置管理
├── notion_[sync.py](http://sync.py)             # 核心同步邏輯（統一版本）
├── notion_docs.py             # docs 指令：Notion 頁面樹匯出為 Markdown
├── [main.py](http://main.py)                    # 具子指令的命令列介面
├── block_[merger.py](http://merger.py)            # 區塊合併工具
├── test_notion_[sync.py](http://sync.py)        # 測試檔案
└── .notion_sync_cache.json    # 本地快取（自動產生，依專案）
```

## 進階功能

### 專案別配置

- 每個專案目錄可擁有獨立的 `.env` 檔案
- 工具會向上搜尋目錄樹尋找 `.env` 檔案
- 支援不同專案使用不同的 Notion token 和父頁面

### 智慧快取

- 快取檔案依專案目錄儲存
- 讓多專案能獨立同步
- 自動清理已刪除檔案的快取記錄

### 雙向工作流程

1. **開發**: 在本地進行程式碼開發
2. **推送**: `python [main.py](http://main.py) push ./ -f` - 同步到 Notion 進行文件化/分享
3. **協作**: 其他人可在 Notion 中檢視/編輯程式碼
4. **拉取**: `python [main.py](http://main.py) pull ./ -f` - 提取更新的程式碼回到本地

## 注意事項

- 確保 Notion Integration 有對目標頁面的寫入權限
- 大型專案首次同步可能需要較長時間
- 每個專案維護自己的快取檔案以進行獨立追蹤
- Pull 操作需要先前的 push 操作來建立頁面對應關係
- 支援的檔案編碼：UTF-8
- 大型檔案會因 Notion API 限制而自動分段

## 常見問題

**Q: 如何忽略特定目錄？**

A: 在 [`config.py`](http://config.py) 中修改 `IGNORE_PATTERNS` 清單

**Q: 同步失敗怎麼辦？**

A: 檢查網路連線和 Notion API 權限，查看錯誤訊息

**Q: 可以同步其他程式語言嗎？**

A: 可以，在 [`config.py`](http://config.py) 中修改 `SUPPORTED_LANGUAGES` 字典

**Q: 如何處理編碼問題？**

A: 工具會自動嘗試 UTF-8 和 GBK 編碼。其他編碼可能需要手動轉換

**Q: Pull 指令顯示「找不到同步快取」？**

A: 你需要先推送檔案以在快取中建立頁面對應關係

**Q: 如何在不同專案使用不同的 Notion 工作區？**

A: 在每個專案目錄建立獨立的 `.env` 檔案，包含不同的 `NOTION_TOKEN` 和 `PARENT_PAGE_ID`

## 使用範例

### 基本工作流程

```bash
# 設定專案
cd /path/to/your/project
cp /path/to/tool/.env.example .env
# 編輯 .env 填入你的 Notion 憑證

# 推送所有 Python 檔案到 Notion
python /path/to/tool/[main.py](http://main.py) push ./ -l python

# 拉取所有檔案回來（例如在 Notion 編輯後）
python /path/to/tool/[main.py](http://main.py) pull ./ -o ./from_notion

# 檢查同步統計
python /path/to/tool/[main.py](http://main.py) stats ./
```

### 多專案設定

```bash
# 專案 A
cd /path/to/projectA
echo "NOTION_TOKEN=token_a\nPARENT_PAGE_ID=page_a" > .env
python /path/to/tool/[main.py](http://main.py) push ./

# 專案 B
cd /path/to/projectB
echo "NOTION_TOKEN=token_b\nPARENT_PAGE_ID=page_b" > .env
python /path/to/tool/[main.py](http://main.py) push ./
```

## 授權

MIT License