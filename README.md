# 🚀 Notion Code File Sync Tool v2.0

> **Powerful bidirectional sync tool** for syncing code project files to Notion pages with **smart duplicate prevention**
> 

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://python.org)

[![Notion API](https://img.shields.io/badge/Notion-API-black.svg)](https://developers.notion.com)

[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## ✨ What's New in v2.0

### 🔧 Fixed Critical Issues

- **🚫 No More Duplicate Pages**: Fixed logic that created new pages instead of updating existing ones
- **💾 Smart Cache Management**: Improved cache key uniqueness for files with same names in different directories
- **🗑️ Automatic Cleanup**: Old pages are automatically archived when updates occur
- **🔄 Reliable Sync**: Cache remains valid across file updates, preventing unnecessary re-syncing

### 🎯 Key Improvements

- **Path Normalization**: Cross-platform path handling (Windows `\` ↔ Unix `/`)
- **Absolute Path Fallback**: Robust handling when relative path calculation fails
- **Archive-Safe Updates**: Handles archived/locked pages gracefully
- **Zero Architecture Changes**: Maintains full backward compatibility

---

## 🎯 Core Features

### 📤 Push Operation

- **Smart Upload**: Sync local code files to Notion pages
- **Incremental Sync**: Only updates changed files (MD5 hash comparison)
- **Multi-language Support**: 30+ programming languages with syntax highlighting
- **Intelligent Chunking**: Automatic handling of large files (1500 char chunks)
- **Project-specific Configuration**: Per-project `.env` settings

### 📥 Pull Operation

- **Reverse Sync**: Download files from Notion back to local directory
- **Structure Preservation**: Maintains original directory structure
- **Safe Overwrite**: Optional force overwrite with `-f` flag
- **Content Reconstruction**: Intelligently merges chunked code blocks

### 🧠 Smart Cache System

- **Persistent Cache**: `.notion_sync_cache.json` per project
- **Hash-based Detection**: Skip unchanged files automatically
- **Cross-session Consistency**: Maintains sync state across runs
- **Cleanup Tools**: Remove orphaned cache entries

---

## 🚀 Quick Start

### 1. Installation

```bash
# Clone repository
git clone <repository-url>
cd notion-tool

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create `.env` file in your project root:

```
NOTION_TOKEN=secret_your_notion_integration_token
PARENT_PAGE_ID=your_parent_page_id_here
```

### 3. Basic Usage

```bash
# Push entire project to Notion
python main.py push /path/to/your/project

# Push only Python files
python main.py push /path/to/project -l python

# Force update all files
python main.py push /path/to/project -f

# Pull files from Notion
python main.py pull /path/to/project

# Get project statistics
python main.py stats /path/to/project
```

---

## 📋 Command Reference

### Push Commands

```bash
# Basic sync
python main.py push <project_path>

# Language-specific sync
python main.py push <project_path> -l python     # Only Python files
python main.py push <project_path> -l javascript # Only JavaScript files
python main.py push <project_path> -l c#         # Only C# files

# Extension-specific sync
python main.py push <project_path> -e .py .js .ts

# Force update (ignore cache)
python main.py push <project_path> -f
```

### Pull Commands

```bash
# Pull to default directory ({project}_from_notion)
python main.py pull <original_project_path>

# Pull to specific directory
python main.py pull <original_project_path> -o /custom/output/dir

# Force overwrite existing files
python main.py pull <original_project_path> -f
```

### Utility Commands

```bash
# Show project statistics
python main.py stats <project_path>

# Clean orphaned cache entries
python main.py clean <project_path>
```

---

## 🔧 Configuration

### Environment Variables

```
# Required
NOTION_TOKEN=secret_your_integration_token_here
PARENT_PAGE_ID=notion_parent_page_id_here

# Optional
MAX_CONTENT_LENGTH=50000    # Max chars per file (default: 50000)
CHUNK_SIZE=1500            # Code block chunk size (default: 1500)
```

### Supported File Types

**Programming Languages**:

- Python (`.py`), JavaScript (`.js`), TypeScript (`.ts`)
- C# (`.cs`), C++ (`.cpp`, `.cc`, `.cxx`), C (`.c`)
- Java (`.java`), Go (`.go`), Rust (`.rs`)
- PHP (`.php`), Ruby (`.rb`), Swift (`.swift`)
- Kotlin (`.kt`), Scala (`.scala`), Perl (`.pl`)

**Web Technologies**:

- HTML (`.html`, `.htm`), CSS (`.css`), SCSS (`.scss`)
- Vue (`.vue`), React (`.jsx`, `.tsx`)
- JSON (`.json`), XML (`.xml`), YAML (`.yml`, `.yaml`)

**Configuration & Scripts**:

- Shell (`.sh`, `.bash`), PowerShell (`.ps1`)
- SQL (`.sql`), Dockerfile, Makefile
- Config files (`.ini`, `.cfg`, `.conf`)

---

## 🏗️ Architecture

### Core Components

1. [**`config.py`**] - Configuration management
    - Environment variable loading
    - File type mappings
    - Ignore patterns
2. **`notion_sync.py`** - Main synchronization logic
    - File scanning and hashing
    - Page creation/updating
    - Content chunking
    - Cache management
3. [**`main.py`**] - Command-line interface
    - Argument parsing
    - User interaction
    - Error reporting

### Cache Structure

```json
{
  "relative/path/to/file.py": {
    "page_id": "notion_page_id_here",
    "hash": "md5_hash_of_file_content",
    "last_sync": "2025-09-04T12:00:00.000000",
    "file_size": 1234,
    "language": "python"
  }
}
```

---

## 🧪 Testing

```bash
# Run all tests
python -m pytest test_notion_sync.py -v

# Run specific test class
python -m pytest test_notion_sync.py::TestPageCreationAndUpdate -v

# Run with coverage
python -m pytest test_notion_sync.py --cov=notion_sync --cov-report=html
```

---

## 🚨 Troubleshooting

### Common Issues

**1. Duplicate Pages**

```
Problem: Multiple pages created for same file
Solution: Use v2.0 with fixed duplicate prevention logic
```

**2. Archived Page Errors**

```
Error: "Can't edit block that is archived"
Solution: v2.0 automatically archives old pages before creating new ones
```

**3. Path Issues**

```
Problem: Same filename conflicts in cache
Solution: v2.0 uses full path as cache key for uniqueness
```

**4. Encoding Errors**

```
Problem: UnicodeDecodeError on certain files
Solution: Tool tries UTF-8 first, then GBK encoding
```

### Debug Commands

```bash
# Check cache status
python main.py stats <project_path>

# Clean problematic cache
python main.py clean <project_path>

# Force full resync
python main.py push <project_path> -f
```

---

## 🔐 Security & Privacy

- **API Token Security**: Store tokens in `.env` files, never commit to version control
- **Local Cache**: Cache files are stored locally and contain only metadata
- **No Content Storage**: File content is only sent to your Notion workspace
- **Minimal Permissions**: Only requires page read/write access

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License

---

## 🙏 Acknowledgments

- [Notion API](https://developers.notion.com) for providing excellent documentation
- [notion-client](https://github.com/ramnes/notion-sdk-py) for the Python SDK
- All contributors who helped improve this tool