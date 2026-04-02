# Notion Code File Sync Tool v2.1

Sync code project files to Notion pages with smart caching, chunked uploads, and flexible update modes.

---

## Features

- **Push & Pull** — Bidirectional sync between local files and Notion pages
- **Incremental Sync** — MD5 hash comparison, only changed files are synced
- **No Truncation** — Large files split into multiple code block parts (each up to MAX_CONTENT_LENGTH)
- **Update Modes** — `recreate` (delete old page, create new) or `clear` (keep page ID, rewrite content)
- **30+ Languages** — Syntax highlighting for Python, C#, JS, TS, Go, Rust, etc.
- **Per-project Config** — Each project can have its own `.env` file

---

## Quick Start

**1. Install**

```bash
pip install notion-client python-dotenv
```

**2. Configure** — Create `.env` in your project root:

```
NOTION_TOKEN=secret_your_token_here
PARENT_PAGE_ID=your_parent_page_id
MAX_CONTENT_LENGTH=100000
```

**3. Push**

```bash
python main.py push /path/to/project
```

---

## Commands

### push — Upload files to Notion

```bash
python main.py push <path>                # Sync all supported files
python main.py push <path> -f              # Force update all (skip hash check)
python main.py push <path> -l python       # Only sync Python files
python main.py push <path> -e .py .cs .js  # Only sync specific extensions
python main.py push <path> -m clear        # Keep page, rewrite content
python main.py push <path> -m recreate     # Delete old page, create new (default)
python main.py push <path> -f -m clear     # Force + clear mode
python main.py push <path> --plain-text    # Single code block with rich_text parts
```

### pull — Download files from Notion

```bash
python main.py pull <path>                 # Pull to {project}_from_notion
python main.py pull <path> -o /output/dir  # Pull to specific directory
python main.py pull <path> -f              # Force overwrite existing files
```

### stats / clean

```bash
python main.py stats <path>                # Show project statistics
python main.py clean <path>                # Remove deleted files from cache
```

---

## Update Modes

| Command | Hash Check | Behavior |
| --- | --- | --- |
| `push` | changed only | recreate (default) |
| `push -f` | all files | recreate (default) |
| `push -m clear` | changed only | clear page & rewrite |
| `push -f -m clear` | all files | clear page & rewrite |
| `push -m recreate` | changed only | delete old, create new |
| `push -f -m recreate` | all files | delete old, create new |
- **recreate** — Archives old page → creates new page. Page ID changes.
- **clear** — Keeps old page → deletes all blocks → rewrites content. Page ID preserved.
- Without `-f`: only files with changed MD5 hash are processed.
- With `-f`: all files are processed regardless of hash.

---

## Configuration (.env)

```
NOTION_TOKEN=secret_xxx          # Required: Notion integration token
PARENT_PAGE_ID=abc123...         # Required: Target parent page ID
MAX_CONTENT_LENGTH=100000        # Optional: Max chars per code block part (default: 100000)
```

The tool searches for `.env` upward from the project directory.

---

## How Chunking Works

1. File content is split by lines into parts of up to MAX_CONTENT_LENGTH chars each.
2. Each part becomes one Notion code block (via `_build_single_code_block`).
3. Inside each code block, content is split into rich_text elements of 1500 chars (API limit: 2000).
4. Multiple parts get headings: Code (Part 1), Code (Part 2), etc.

<aside>
📦

**Example**: 250,000 char file with MAX_CONTENT_LENGTH=100000:

Part 1: 100,000 chars → 1 code block

Part 2: 100,000 chars → 1 code block

Part 3: 50,000 chars → 1 code block

</aside>

---

## Supported Languages

| Language | Extensions |
| --- | --- |
| Python | .py |
| C# | .cs |
| JavaScript | .js, .jsx |
| TypeScript | .ts, .tsx |
| Java | .java |
| C/C++ | .c, .cpp |
| Go | .go |
| Rust | .rs |
| PHP | .php |
| Ruby | .rb |
| Swift | .swift |
| Kotlin | .kt |
| HTML/CSS | .html, .css, .scss |
| Vue | .vue |
| Shell | .sh, .bash |
| PowerShell | .ps1 |
| SQL | .sql |
| JSON/YAML/XML | .json, .yaml, .yml, .xml |

---

## Project Structure

```
notion-tool/
├── main.py              # CLI entry point
├── notion_sync.py       # Core sync logic
├── config.py            # Configuration & language mappings
├── cleanup_tool.py      # Cleanup utilities
├── block_merger.py      # Block merging utilities
├── patch.py             # Patch utilities
├── test_notion_sync.py  # Tests
├── .env                 # Project config (not committed)
└── README.md
```

---

## Cache

Each project stores sync state in `.notion_sync_cache.json`:

```json
{
  "path/to/file.py": {
    "page_id": "notion-page-uuid",
    "hash": "md5-hash",
    "last_sync": "2026-04-02T16:00:00",
    "file_size": 12345,
    "language": "python"
  }
}
```

Use `python main.py clean <path>` to remove entries for deleted files.

---

## Troubleshooting

| Problem | Solution |
| --- | --- |
| Duplicate pages | Upgrade to v2.0+ with fixed cache logic |
| Archived page errors | v2.0+ auto-archives before recreate |
| Encoding errors | Tool tries UTF-8, then GBK |
| Large file fails | Set MAX_CONTENT_LENGTH in .env |
| Page ID changed | Use `-m clear` to preserve page ID |

---

## License

MIT