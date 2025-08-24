# Notion Code File Sync Tool

A Python tool for syncing code project files to Notion pages automatically. Supports **bidirectional sync**, incremental updates, directory scanning, and creates individual Notion pages for each code file.

## Features

🔄 **Bidirectional Sync**: Push files to Notion AND pull them back to local directories

📥 **Pull Functionality**: Extract code from Notion pages back to local files

📁 **Per-Project Configuration**: Each project can have its own .env configuration

📄 **Individual Pages**: Creates separate Notion pages for each code file

🚀 **Active Sync**: Git-like manual sync mechanism - you control when to sync

💾 **Smart Cache System**: Project-specific cache files to avoid duplicates

🐍 **Python Implementation**: Uses official Notion API for automation

🌐 **Multi-language Support**: Supports 30+ programming languages and file types

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
- **Configuration Files** (.json, .yaml, .yml, .xml)
- **And many more...**

## Installation & Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

The tool supports **per-project configuration**. It will automatically look for `.env` files in your project directory hierarchy.

Copy `.env.example` to `.env` and fill in the required information:

```bash
cp .env.example .env
```

Edit the `.env` file:

```
NOTION_TOKEN=your_notion_integration_token
PARENT_PAGE_ID=your_parent_page_id
PROJECT_ROOT=./your_project_path
MAX_CONTENT_LENGTH=100000
CACHE_FILE=.notion_sync_cache.json
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

The tool now supports **subcommands** for different operations:

### Push Files to Notion

```bash
# Push all files in current directory
python [main.py](http://main.py) push ./

# Push with force update (update all files regardless of changes)
python [main.py](http://main.py) push ./ -f

# Push specific language files only
python [main.py](http://main.py) push ./ -l python

# Push specific file extensions
python [main.py](http://main.py) push ./ -e .py .js .css
```

### Pull Files from Notion

```bash
# Pull all synced files from Notion
python [main.py](http://main.py) pull ./

# Pull with force overwrite (overwrite existing local files)
python [main.py](http://main.py) pull ./ -f

# Pull to specific output directory
python [main.py](http://main.py) pull ./ -o ./pulled_code

# Pull to specific directory with force overwrite
python [main.py](http://main.py) pull ./ -o ./pulled_code -f
```

### Project Statistics

```bash
# Show project sync statistics
python [main.py](http://main.py) stats ./
```

### Cache Management

```bash
# Clean deleted files from cache
python [main.py](http://main.py) clean ./
```

### Command Reference

### Push Command Options

- `-f, --force` - Force update all files (ignore hash comparison)
- `-l, --language` - Sync specific language only (e.g., python, javascript)
- `-e, --extensions` - Sync specific file extensions (e.g., .py .js)

### Pull Command Options

- `-f, --force` - Force overwrite existing local files
- `-o, --output` - Specify output directory (default: {project}_from_notion)

### Help

```bash
python [main.py](http://main.py) --help
python [main.py](http://main.py) push --help
python [main.py](http://main.py) pull --help
```

## How It Works

### Push Operation

1. **Configuration Loading**: Finds and loads .env from project directory hierarchy
2. **Scanning Phase**: Recursively scans specified directory for supported code files
3. **Change Detection**: Calculates MD5 hash of files and compares with local cache
4. **Sync Processing**:
    - Creates new pages (if file is new)
    - Updates existing pages (if file has changes)
    - Skips unchanged files (improves efficiency)
5. **Cache Update**: Updates project-specific sync cache file

### Pull Operation

1. **Cache Loading**: Loads project-specific cache to find synced pages
2. **Content Extraction**: Retrieves code content from Notion pages
3. **File Creation**: Recreates local files with extracted content
4. **Overwrite Protection**: Skips existing files unless force flag is used

## Page Structure

The tool creates Notion pages with the following structure:

- **File Header**: File icon and name
- **File Information**: Path, language, and file size
- **Code Content**: Syntax-highlighted code blocks
- **Chunked Content**: Large files are automatically split into multiple code blocks (due to Notion API limits)

## Project Structure

```
ncsft/
├── [README.md](http://README.md)                    # English documentation
├── README(cht).md              # Chinese documentation
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore patterns
├── [config.py](http://config.py)                  # Configuration with dynamic .env loading
├── notion_[sync.py](http://sync.py)             # Core sync logic (unified version)
├── [main.py](http://main.py)                    # Command line interface with subcommands
├── block_[merger.py](http://merger.py)            # Block merging utilities
├── test_notion_[sync.py](http://sync.py)        # Test files
└── .notion_sync_cache.json    # Local cache (auto-generated per project)
```

## Advanced Features

### Per-Project Configuration

- Each project directory can have its own `.env` file
- The tool searches up the directory tree for `.env` files
- Supports different Notion tokens and parent pages per project

### Smart Caching

- Cache files are stored per project directory
- Enables multiple projects to be synced independently
- Automatic cleanup of deleted files from cache

### Bidirectional Workflow

1. **Development**: Work on code locally
2. **Push**: `python [main.py](http://main.py) push ./ -f` - Sync to Notion for documentation/sharing
3. **Collaboration**: Others can view/edit code in Notion
4. **Pull**: `python [main.py](http://main.py) pull ./ -f` - Extract updated code back to local

## Notes

- Ensure your Notion Integration has write permissions to the target page
- Initial sync of large projects may take considerable time
- Each project maintains its own cache file for independent tracking
- Pull operation requires previous push operation to establish page mappings
- Supported file encoding: UTF-8
- Large files are automatically chunked due to Notion API limitations

## Common Issues

**Q: How to ignore specific directories?**

A: Modify the `IGNORE_PATTERNS` list in [`config.py`](http://config.py)

**Q: What to do if sync fails?**

A: Check network connection and Notion API permissions, review error messages

**Q: Can I sync other programming languages?**

A: Yes, modify the `SUPPORTED_LANGUAGES` dictionary in [`config.py`](http://config.py)

**Q: How to handle encoding issues?**

A: The tool automatically tries UTF-8 and GBK encodings. For other encodings, manual conversion may be needed

**Q: Pull command shows "No sync cache found"?**

A: You need to push files first to create the page mappings in cache

**Q: How to use different Notion workspaces for different projects?**

A: Create separate `.env` files in each project directory with different `NOTION_TOKEN` and `PARENT_PAGE_ID`

## Examples

### Basic Workflow

```bash
# Setup project
cd /path/to/your/project
cp /path/to/tool/.env.example .env
# Edit .env with your Notion credentials

# Push all Python files to Notion
python /path/to/tool/[main.py](http://main.py) push ./ -l python

# Pull all files back (e.g., after editing in Notion)
python /path/to/tool/[main.py](http://main.py) pull ./ -o ./from_notion

# Check sync statistics
python /path/to/tool/[main.py](http://main.py) stats ./
```

### Multi-Project Setup

```bash
# Project A
cd /path/to/projectA
echo "NOTION_TOKEN=token_a\nPARENT_PAGE_ID=page_a" > .env
python /path/to/tool/[main.py](http://main.py) push ./

# Project B
cd /path/to/projectB
echo "NOTION_TOKEN=token_b\nPARENT_PAGE_ID=page_b" > .env
python /path/to/tool/[main.py](http://main.py) push ./
```

## License

MIT License