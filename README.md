# Notion Code File Sync Tool

A Python tool for syncing code project files to Notion pages automatically. Supports incremental sync, directory scanning, and creates individual Notion pages for each code file.

## Features

🔄 **Incremental Sync**: Only updates changed files (via MD5 hash comparison)

📁 **Directory Scanning**: Scan specific directories with ignore patterns support

📄 **Individual Pages**: Creates separate Notion pages for each code file

🚀 **Active Sync**: Git-like manual sync mechanism - you control when to sync

💾 **Cache System**: Local cache to avoid duplicate uploads and improve efficiency

🐍 **Python Implementation**: Uses official Notion API for automation

🌐 **Multi-language Support**: Supports multiple programming languages

## Supported Languages

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
- **And many more...**

## Installation & Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy `.env.example` to `.env` and fill in the required information:

```bash
cp .env.example .env
```

Edit the `.env` file:

```
NOTION_TOKEN=your_notion_integration_token
PARENT_PAGE_ID=your_parent_page_id
PROJECT_ROOT=./your_project_path
```

### 3. Get Notion Integration Token

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Click "New integration"
3. Fill in name (e.g., "Code File Sync")
4. Select workspace
5. Copy the Internal Integration Token

### 4. Get Parent Page ID

1. Create a new page in Notion (or use existing one)
2. Invite your Integration to this page
3. Extract the Page ID from the page URL

## Usage

### Sync Current Directory

```bash
python [main.py](http://main.py)
```

### Sync Specific Directory

```bash
python [main.py](http://main.py) --path /path/to/your/project
```

### Sync Specific File Types

```bash
# Only Python files
python [main.py](http://main.py) --extensions .py

# Python and JavaScript files
python [main.py](http://main.py) --extensions .py .js
```

### Force Update All Files

```bash
python [main.py](http://main.py) --force
```

### Display Statistics

```bash
python [main.py](http://main.py) --stats
```

### Clean Cache

```bash
python [main.py](http://main.py) --clean
```

### Complete Command Options

```bash
python [main.py](http://main.py) --help
```

## How It Works

1. **Scanning Phase**: Recursively scans specified directory for supported code files
2. **Change Detection**: Calculates MD5 hash of files and compares with local cache
3. **Sync Processing**:
    - Creates new pages (if file is new)
    - Updates existing pages (if file has changes)
    - Skips unchanged files (improves efficiency)
4. **Cache Update**: Updates local sync cache file

## Page Structure

The tool creates Notion pages with the following structure:

- **File Information**: Path, language, and file size
- **Code Content**: Syntax-highlighted code blocks
- **Chunked Content**: Large files are automatically split into multiple code blocks (due to Notion API limits)

## File Structure

```
notion-code-sync/
├── [README.md](http://README.md)
├── README (English).md
├── requirements.txt
├── .env.example
├── [config.py](http://config.py)              # Configuration management
├── notion_[sync.py](http://sync.py)         # Core sync logic
├── [main.py](http://main.py)               # Command line interface
└── .notion_sync_cache.json  # Local cache (auto-generated)
```

## Notes

- Ensure your Notion Integration has write permissions to the target page
- Initial sync of large projects may take considerable time
- Do not manually delete the local cache file `.notion_sync_cache.json`
- Supported file encoding: UTF-8
- Large files are automatically chunked due to Notion API limitations

## Common Issues

**Q: How to ignore specific directories?**

A: Modify the `IGNORE_PATTERNS` list in [`config.py`](http://config.py)

**Q: What to do if sync fails?**

A: Check network connection and Notion API permissions, review error messages

**Q: Can I sync other programming languages?**

A: Yes, modify the file scanning extensions in [`config.py`](http://config.py)

**Q: How to handle encoding issues?**

A: The tool automatically tries UTF-8 and GBK encodings. For other encodings, manual conversion may be needed

## License

MIT License