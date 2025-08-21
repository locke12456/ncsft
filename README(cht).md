# Notion 程式碼檔案同步工具

一個用於將程式碼專案檔案自動同步到 Notion 頁面的 Python 工具。支援增量同步、目錄掃描，並為每個程式碼檔案建立獨立的 Notion 頁面。

## 功能特色

🔄 **增量同步**: 只更新有變更的檔案（透過 MD5 hash 比對）

📁 **目錄掃描**: 掃描指定目錄並支援忽略特定模式

📄 **獨立頁面**: 為每個程式碼檔案建立獨立的 Notion 頁面

🚀 **主動同步**: 類似 Git 的手動同步機制 - 你決定何時同步

💾 **快取系統**: 本地快取避免重複上傳並提升效率

🐍 **Python 實作**: 使用官方 Notion API 進行自動化操作

🌐 **多語言支援**: 支援多種程式語言

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
- **還有更多...**

## 安裝與設定

### 1. 安裝依賴套件

```bash
pip install -r requirements.txt
```

### 2. 環境變數設定

複製 `.env.example` 為 `.env` 並填入必要資訊：

```bash
cp .env.example .env
```

編輯 `.env` 檔案：

```
NOTION_TOKEN=your_notion_integration_token
PARENT_PAGE_ID=your_parent_page_id
PROJECT_ROOT=./your_project_path
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

### 同步當前目錄

```bash
python [main.py](http://main.py)
```

### 同步指定目錄

```bash
python [main.py](http://main.py) --path /path/to/your/project
```

### 同步特定檔案類型

```bash
# 只同步 Python 檔案
python [main.py](http://main.py) --extensions .py

# 同步 Python 和 JavaScript 檔案
python [main.py](http://main.py) --extensions .py .js
```

### 強制更新所有檔案

```bash
python [main.py](http://main.py) --force
```

### 顯示統計資訊

```bash
python [main.py](http://main.py) --stats
```

### 清理快取

```bash
python [main.py](http://main.py) --clean
```

### 完整命令選項

```bash
python [main.py](http://main.py) --help
```

## 工作原理

1. **掃描階段**: 遞迴掃描指定目錄中的所有支援程式碼檔案
2. **變更檢測**: 計算檔案的 MD5 hash，與本地快取比對
3. **同步處理**:
    - 建立新頁面（如果檔案是新增的）
    - 更新現有頁面（如果檔案有變更）
    - 跳過未變更的檔案（提高效率）
4. **快取更新**: 更新本地同步快取檔案

## 頁面結構

工具會建立包含以下結構的 Notion 頁面：

- **檔案資訊**: 路徑、程式語言和檔案大小
- **程式碼內容**: 具備語法高亮的程式碼區塊
- **分段內容**: 大型檔案會自動分割成多個程式碼區塊（受 Notion API 限制）

## 專案結構

```
notion-code-sync/
├── [README.md](http://README.md)
├── README (English).md
├── requirements.txt
├── .env.example
├── [config.py](http://config.py)              # 設定管理
├── notion_[sync.py](http://sync.py)         # 核心同步邏輯
├── [main.py](http://main.py)               # 命令列介面
└── .notion_sync_cache.json  # 本地快取（自動生成）
```

## 注意事項

- 確保 Notion Integration 有對目標頁面的寫入權限
- 大型專案首次同步可能需要較長時間
- 請勿手動刪除本地快取檔案 `.notion_sync_cache.json`
- 支援的檔案編碼：UTF-8
- 大型檔案會因 Notion API 限制而自動分段

## 常見問題

**Q: 如何忽略特定目錄？**

A: 在 [`config.py`](http://config.py) 中修改 `IGNORE_PATTERNS` 清單

**Q: 同步失敗怎麼辦？**

A: 檢查網路連線和 Notion API 權限，查看錯誤訊息

**Q: 可以同步其他程式語言嗎？**

A: 可以，在 [`config.py`](http://config.py) 中修改檔案掃描的副檔名

**Q: 如何處理編碼問題？**

A: 工具會自動嘗試 UTF-8 和 GBK 編碼。其他編碼可能需要手動轉換

## 授權

MIT License