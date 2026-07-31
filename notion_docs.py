# -*- coding: utf-8 -*-
"""
Recursive Notion page-tree -> Markdown exporter.

The existing push/pull flow in this repo treats a Notion page as a container for
one source file's code blocks. This module handles the other direction of the
same problem: a hand-written Notion document tree (headings, tables, callouts,
toggles, nested sub-pages) that has to land on disk as Markdown.

Design notes:
  * Output style follows Notion's own "Export to Markdown" conventions so the
    result is consistent with documents exported that way earlier: `<aside>`
    callouts, tab-indented nested lists, page title kept as an H1 with its emoji.
  * A page whose block list contains child pages becomes a folder; a leaf page
    becomes a single .md next to its siblings.
  * Every page is written and cached the moment it is fetched, so an interrupted
    run resumes without redoing finished work.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

NOTION_VERSION = "2022-06-28"
API_ROOT = "https://api.notion.com/v1"

# Notion allows ~3 requests/second per integration.
REQUEST_INTERVAL = 0.34
MAX_RETRIES = 5


# --------------------------------------------------------------------------
# naming
# --------------------------------------------------------------------------

# One leading emoji (plus any variation selectors / ZWJ continuation) is dropped
# from file and folder names; the title inside the document keeps it.
_LEADING_EMOJI = re.compile(
    "^(?:"
    "[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u2190-\u21FF\u2300-\u23FF]"
    "[\uFE00-\uFE0F\u200D\U0001F3FB-\U0001F3FF]*"
    ")+\\s*"
)

# Characters that are legal in a Notion title but not in a Windows file name.
_FILENAME_SUBSTITUTIONS = {
    "/": " ",
    "\\": " ",
    ":": "：",
    "*": "＊",
    "?": "？",
    '"': "”",
    "<": "＜",
    ">": "＞",
    "|": "｜",
}


def strip_leading_emoji(title):
    """Drop a leading emoji from a page title, keeping the rest untouched."""
    return _LEADING_EMOJI.sub("", title or "").strip()


def sanitize_name(title, fallback="untitled"):
    """Turn a Notion page title into a safe file/folder name."""
    name = strip_leading_emoji(title)
    for bad, good in _FILENAME_SUBSTITUTIONS.items():
        name = name.replace(bad, good)
    name = re.sub(r"\s+", " ", name).strip()
    # Windows rejects trailing dots and spaces.
    name = name.rstrip(". ")
    return name or fallback


def normalize_id(page_id):
    """Accept a bare 32-hex id, a dashed UUID, or a Notion URL."""
    if not page_id:
        return page_id
    raw = page_id.strip()
    match = re.findall(r"[0-9a-fA-F]{32}", raw.replace("-", ""))
    if match:
        clean = match[-1].lower()
        return f"{clean[:8]}-{clean[8:12]}-{clean[12:16]}-{clean[16:20]}-{clean[20:]}"
    return raw


def page_url(page_id):
    return "https://app.notion.com/p/" + normalize_id(page_id).replace("-", "")


# --------------------------------------------------------------------------
# API client
# --------------------------------------------------------------------------

class NotionApiError(RuntimeError):
    pass


class NotionReader:
    """Read-only Notion client over the standard library.

    `notion_client` is used when it is installed, but this module deliberately
    works without it so the exporter can run on a machine that only has Python.
    """

    def __init__(self, token, verbose=False):
        self.token = token
        self.verbose = verbose
        self.request_count = 0
        self._last_request = 0.0

    def _throttle(self):
        elapsed = time.monotonic() - self._last_request
        if elapsed < REQUEST_INTERVAL:
            time.sleep(REQUEST_INTERVAL - elapsed)
        self._last_request = time.monotonic()

    def _request(self, method, path, payload=None):
        url = f"{API_ROOT}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

        last_error = None
        for attempt in range(MAX_RETRIES):
            self._throttle()
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    self.request_count += 1
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", "replace")
                # 429 and 5xx are worth retrying; 4xx generally are not.
                if exc.code == 429 or exc.code >= 500:
                    wait = float(exc.headers.get("Retry-After", 0) or (2 ** attempt))
                    if self.verbose:
                        print(f"    ! HTTP {exc.code}, retrying in {wait:.1f}s")
                    time.sleep(wait)
                    last_error = NotionApiError(f"HTTP {exc.code}: {body[:300]}")
                    continue
                raise NotionApiError(f"HTTP {exc.code} on {method} {path}: {body[:300]}")
            except urllib.error.URLError as exc:
                wait = 2 ** attempt
                if self.verbose:
                    print(f"    ! network error ({exc.reason}), retrying in {wait}s")
                time.sleep(wait)
                last_error = NotionApiError(f"network error: {exc.reason}")

        raise last_error or NotionApiError(f"{method} {path} failed")

    def retrieve_page(self, page_id):
        return self._request("GET", f"/pages/{normalize_id(page_id)}")

    def list_children(self, block_id):
        """Return every child block, following pagination."""
        blocks = []
        cursor = None
        while True:
            path = f"/blocks/{normalize_id(block_id)}/children?page_size=100"
            if cursor:
                path += f"&start_cursor={cursor}"
            payload = self._request("GET", path)
            blocks.extend(payload.get("results", []))
            if not payload.get("has_more"):
                break
            cursor = payload.get("next_cursor")
        return blocks


# --------------------------------------------------------------------------
# rich text -> markdown
# --------------------------------------------------------------------------

def _wrap(text, marker):
    """Apply an inline marker without swallowing the surrounding whitespace."""
    stripped = text.strip()
    if not stripped:
        return text
    lead = text[: len(text) - len(text.lstrip())]
    trail = text[len(text.rstrip()):]
    return f"{lead}{marker}{stripped}{marker}{trail}"


def rich_text_to_md(rich_text):
    """Convert a Notion rich_text array to inline Markdown.

    A page mention is rendered as an ordinary link to the referenced Notion
    page. It is a cross reference, not a sub-page, so it is never downloaded.
    """
    parts = []
    for item in rich_text or []:
        kind = item.get("type")
        text = item.get("plain_text", "")

        if kind == "equation":
            expression = item.get("equation", {}).get("expression", text)
            parts.append(f"${expression}$")
            continue

        annotations = item.get("annotations", {})
        if annotations.get("code"):
            fence = "``" if "`" in text else "`"
            text = f"{fence}{text}{fence}"
        else:
            if annotations.get("bold"):
                text = _wrap(text, "**")
            if annotations.get("italic"):
                text = _wrap(text, "*")
            if annotations.get("strikethrough"):
                text = _wrap(text, "~~")
            if annotations.get("underline"):
                text = _wrap(text, "__")

        href = item.get("href")
        if href:
            label = text.replace("[", "\\[").replace("]", "\\]")
            text = f"[{label}]({href})"

        parts.append(text)
    return "".join(parts)


def _caption(block, key):
    return rich_text_to_md(block.get(key, {}).get("caption", []))


def _file_url(payload):
    if payload.get("type") == "external":
        return payload.get("external", {}).get("url", "")
    return payload.get("file", {}).get("url", "")


# --------------------------------------------------------------------------
# exporter
# --------------------------------------------------------------------------

class DocExporter:
    """Export a Notion page and its sub-pages as a Markdown tree."""

    # Blocks that carry no meaning once the document is a flat file.
    SKIPPED_TYPES = {"table_of_contents", "breadcrumb", "unsupported"}

    # Code lines carry this prefix while the document is assembled so that
    # whitespace clean-up cannot reach inside a code block.
    CODE_GUARD = "\x00"

    def __init__(self, reader, cache_path=None, retrieved_on=None, verbose=True, exclude=None):
        self.reader = reader
        self.cache_path = Path(cache_path) if cache_path else None
        self.cache = self._load_cache()
        self.retrieved_on = retrieved_on or datetime.now().strftime("%Y-%m-%d")
        self.verbose = verbose
        self.stats = {"written": 0, "skipped": 0, "failed": 0, "pages": 0, "excluded": 0}
        self.expiring_assets = []
        self.used_paths = set()
        self.excluded_titles = []
        self.exclude_patterns = [re.compile(p, re.I) for p in (exclude or [])]

    def is_excluded(self, title):
        """Sub-pages whose title matches an --exclude pattern are never fetched."""
        return any(pattern.search(title or "") for pattern in self.exclude_patterns)

    # -- cache ------------------------------------------------------------

    def _load_cache(self):
        if self.cache_path and self.cache_path.exists():
            try:
                with open(self.cache_path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                    if isinstance(data, dict) and "pages" in data:
                        return data
            except Exception as exc:  # a corrupt cache must not block a run
                print(f"⚠️  Could not read cache ({exc}); starting fresh")
        return {"pages": {}}

    def save_cache(self):
        if not self.cache_path:
            return
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as handle:
                json.dump(self.cache, handle, indent=2, ensure_ascii=False)
        except Exception as exc:
            print(f"⚠️  Could not write cache: {exc}")

    # -- traversal --------------------------------------------------------

    def export_tree(self, page_id, out_dir, force=False, max_depth=10):
        """Export `page_id` into `out_dir`, recursing into its sub-pages."""
        self._export_page(normalize_id(page_id), Path(out_dir), force, max_depth, 0)
        self.save_cache()
        return self.stats

    def _export_page(self, page_id, parent_dir, force, max_depth, depth):
        if depth > max_depth:
            print(f"{'  ' * depth}⚠️  Depth limit reached, stopping at {page_id}")
            return

        indent = "  " * depth
        try:
            page = self.reader.retrieve_page(page_id)
        except NotionApiError as exc:
            print(f"{indent}❌ Cannot read page {page_id}: {exc}")
            self.stats["failed"] += 1
            return

        if page.get("archived") or page.get("in_trash"):
            print(f"{indent}⏭️  Archived page skipped: {page_id}")
            return

        title = self._page_title(page)
        last_edited = page.get("last_edited_time", "")
        cached = self.cache["pages"].get(page_id, {})
        self.stats["pages"] += 1

        # An unchanged page still has to be walked, but its blocks do not need
        # re-fetching: the child ids recorded last time are enough.
        unchanged = (
            not force
            and cached.get("last_edited_time") == last_edited
            and cached.get("path")
            and Path(cached["path"]).exists()
        )
        if unchanged:
            print(f"{indent}⏭️  {title} (unchanged)")
            self.stats["skipped"] += 1
            self.used_paths.add(cached["path"])
            for child_id in cached.get("children", []):
                child_dir = Path(cached["dir"]) if cached.get("dir") else parent_dir
                self._export_page(child_id, child_dir, force, max_depth, depth + 1)
            return

        print(f"{indent}📄 {title}")
        try:
            blocks = self._fetch_blocks(page_id)
        except NotionApiError as exc:
            print(f"{indent}❌ Cannot read blocks of {title}: {exc}")
            self.stats["failed"] += 1
            return

        child_pages = self._collect_child_pages(blocks)
        name = sanitize_name(title, fallback=page_id[:8])

        # A page with sub-pages owns a folder; a leaf page is a single file.
        if child_pages:
            page_dir = parent_dir / name
            md_path = page_dir / f"{name}.md"
        else:
            page_dir = parent_dir
            md_path = parent_dir / f"{name}.md"
        md_path = self._reserve_path(md_path)

        # Sub-pages are exported first: only once a child has been written is its
        # real location known, and the parent links to it by that location.
        for child in child_pages:
            self._export_page(child["id"], page_dir, force, max_depth, depth + 1)

        markdown = self._render_document(title, page_id, blocks, md_path, page_dir)
        try:
            md_path.parent.mkdir(parents=True, exist_ok=True)
            # newline='' keeps the LF endings the docs tree uses.
            with open(md_path, "w", encoding="utf-8", newline="") as handle:
                handle.write(markdown)
            self.stats["written"] += 1
            print(f"{indent}   ✅ {md_path}")
        except Exception as exc:
            print(f"{indent}   ❌ Write failed: {exc}")
            self.stats["failed"] += 1
            return

        self.cache["pages"][page_id] = {
            "title": title,
            "path": str(md_path),
            "dir": str(page_dir),
            "last_edited_time": last_edited,
            "children": [child["id"] for child in child_pages],
            "fetched_at": datetime.now().isoformat(timespec="seconds"),
        }
        # Saving after every page keeps an interrupted run resumable.
        self.save_cache()

    def _reserve_path(self, md_path):
        """Claim an output path, renaming on a collision with a same-named page."""
        candidate = md_path
        suffix = 2
        while str(candidate) in self.used_paths:
            candidate = md_path.with_name(f"{md_path.stem} ({suffix}){md_path.suffix}")
            suffix += 1
        self.used_paths.add(str(candidate))
        return candidate

    def _page_title(self, page):
        for value in (page.get("properties") or {}).values():
            if value.get("type") == "title":
                return "".join(t.get("plain_text", "") for t in value.get("title", []))
        return "Untitled"

    def _fetch_blocks(self, block_id):
        """Fetch a block subtree, stopping at sub-pages and databases."""
        blocks = self.reader.list_children(block_id)
        for block in blocks:
            if block.get("has_children") and block.get("type") not in ("child_page", "child_database"):
                block["_children"] = self._fetch_blocks(block["id"])
        return blocks

    def _collect_child_pages(self, blocks):
        """Find sub-pages anywhere in the tree, including inside toggles/columns."""
        found = []
        for block in blocks:
            if block.get("type") == "child_page":
                title = block["child_page"].get("title", "Untitled")
                if self.is_excluded(title):
                    self.excluded_titles.append(title)
                    self.stats["excluded"] += 1
                    continue
                found.append({"id": block["id"], "title": title})
            for nested in block.get("_children", []) or []:
                found.extend(self._collect_child_pages([nested]))
        return found

    # -- rendering --------------------------------------------------------

    def _render_document(self, title, page_id, blocks, md_path, page_dir):
        header = [
            f"> **Notion 來源**：{page_url(page_id)}",
            f"> **擷取日期**：{self.retrieved_on}",
            "",
            f"# {title}",
            "",
        ]
        body = self._render_blocks(blocks, md_path, page_dir)
        text = "\n".join(header + body).rstrip() + "\n"
        return self._collapse_blank_lines(text)

    def _collapse_blank_lines(self, text):
        """Squeeze the blank-line runs that nested structures leave behind.

        Code blocks are exempt: their blank lines are content.
        """
        out = []
        blanks = 0
        for line in text.split("\n"):
            if line.startswith(self.CODE_GUARD):
                out.append(line[len(self.CODE_GUARD):])
                blanks = 0
                continue
            if line.strip():
                blanks = 0
            else:
                blanks += 1
                if blanks > 1:
                    continue
            out.append(line)
        return "\n".join(out)

    def _render_blocks(self, blocks, md_path, page_dir, indent=""):
        lines = []
        numbering = 0
        for block in blocks:
            block_type = block.get("type")

            if block_type == "numbered_list_item":
                numbering += 1
            else:
                numbering = 0

            rendered = self._render_block(block, md_path, page_dir, indent, numbering)
            lines.extend(rendered)
        return lines

    def _render_block(self, block, md_path, page_dir, indent, numbering):
        block_type = block.get("type")
        payload = block.get(block_type, {}) or {}
        children = block.get("_children", []) or []
        lines = []

        def text_of():
            return rich_text_to_md(payload.get("rich_text", []))

        def child_lines(extra_indent="\t"):
            if not children:
                return []
            return self._render_blocks(children, md_path, page_dir, indent + extra_indent)

        if block_type in self.SKIPPED_TYPES:
            return []

        if block_type == "paragraph":
            content = text_of()
            lines.append(f"{indent}{content}" if content else "")
            lines.extend(child_lines())
            lines.append("")

        elif block_type in ("heading_1", "heading_2", "heading_3"):
            level = "#" * int(block_type[-1])
            lines.append(f"{indent}{level} {text_of()}")
            lines.append("")
            # A toggleable heading keeps its children as ordinary content.
            lines.extend(child_lines(""))

        elif block_type == "bulleted_list_item":
            lines.append(f"{indent}- {text_of()}")
            lines.extend(child_lines())

        elif block_type == "numbered_list_item":
            lines.append(f"{indent}{numbering}. {text_of()}")
            lines.extend(child_lines())

        elif block_type == "to_do":
            mark = "x" if payload.get("checked") else " "
            lines.append(f"{indent}- [{mark}] {text_of()}")
            lines.extend(child_lines())

        elif block_type == "toggle":
            lines.append(f"{indent}- {text_of()}")
            lines.extend(child_lines())

        elif block_type == "quote":
            for line in (text_of() or "").split("\n"):
                lines.append(f"{indent}> {line}")
            lines.extend(child_lines())
            lines.append("")

        elif block_type == "callout":
            icon = payload.get("icon") or {}
            emoji = icon.get("emoji", "") if icon.get("type") == "emoji" else ""
            lines.append(f"{indent}<aside>")
            if emoji:
                lines.append(f"{indent}{emoji}")
                lines.append("")
            body = text_of()
            if body:
                lines.append(f"{indent}{body}")
            lines.extend(child_lines(""))
            lines.append("")
            lines.append(f"{indent}</aside>")
            lines.append("")

        elif block_type == "code":
            language = payload.get("language", "") or ""
            if language == "plain text":
                language = "text"
            content = "".join(t.get("plain_text", "") for t in payload.get("rich_text", []))
            guard = self.CODE_GUARD
            lines.append(f"{guard}{indent}```{language}")
            lines.extend(f"{guard}{indent}{line}" for line in content.split("\n"))
            lines.append(f"{guard}{indent}```")
            caption = _caption(block, block_type)
            if caption:
                lines.append(f"{indent}*{caption}*")
            lines.append("")

        elif block_type == "divider":
            lines.append(f"{indent}---")
            lines.append("")

        elif block_type == "table":
            lines.extend(self._render_table(block, indent))
            lines.append("")

        elif block_type in ("image", "video", "file", "pdf"):
            url = _file_url(payload)
            caption = _caption(block, block_type) or block_type
            if payload.get("type") == "file":
                # Notion-hosted URLs are signed and expire about an hour later.
                self.expiring_assets.append((str(md_path), url))
            prefix = "!" if block_type == "image" else ""
            lines.append(f"{indent}{prefix}[{caption}]({url})")
            lines.append("")

        elif block_type in ("bookmark", "embed", "link_preview"):
            url = payload.get("url", "")
            caption = _caption(block, block_type) or url
            lines.append(f"{indent}[{caption}]({url})")
            lines.append("")

        elif block_type == "equation":
            lines.append(f"{indent}$$")
            lines.append(f"{indent}{payload.get('expression', '')}")
            lines.append(f"{indent}$$")
            lines.append("")

        elif block_type in ("column_list", "column", "synced_block"):
            # Layout-only containers: emit their contents inline.
            lines.extend(child_lines(""))

        elif block_type == "child_page":
            title = payload.get("title", "Untitled")
            if self.is_excluded(title):
                # Not downloaded, so point at Notion rather than a missing file.
                label = title.replace("[", "\\[").replace("]", "\\]")
                lines.append(f"{indent}- [{label}]({page_url(block['id'])})")
            else:
                lines.append(f"{indent}- {self._child_link(title, block['id'], md_path, page_dir)}")

        elif block_type == "child_database":
            title = payload.get("title", "Untitled")
            lines.append(f"{indent}<!-- child database: {title} ({block['id']}) -->")
            lines.append("")

        elif block_type == "link_to_page":
            target = payload.get("page_id") or payload.get("database_id") or ""
            lines.append(f"{indent}- [{target}]({page_url(target)})")

        elif block_type == "table_of_contents":
            return []

        else:
            content = text_of()
            if content:
                lines.append(f"{indent}{content}")
            else:
                lines.append(f"{indent}<!-- unhandled block: {block_type} -->")
            lines.extend(child_lines())

        return lines

    def _child_link(self, title, child_id, md_path, page_dir):
        """Relative link from the parent document to a sub-page's file."""
        entry = self.cache["pages"].get(child_id) or {}
        if entry.get("path"):
            # The sub-page was exported first, so its real location is known.
            target = Path(entry["path"])
        else:
            name = sanitize_name(title, fallback=child_id[:8])
            target = page_dir / f"{name}.md"
        try:
            relative = target.relative_to(md_path.parent).as_posix()
        except ValueError:
            relative = target.as_posix()
        # Titles routinely contain brackets, and paths contain spaces and
        # parentheses; both have to be neutralised or the link stops parsing.
        label = title.replace("[", "\\[").replace("]", "\\]")
        return f"[{label}](<{relative}>)"

    def _render_table(self, block, indent):
        rows = block.get("_children", []) or []
        if not rows:
            return []
        has_header = block.get("table", {}).get("has_column_header", False)
        lines = []
        for index, row in enumerate(rows):
            cells = row.get("table_row", {}).get("cells", [])
            rendered = [rich_text_to_md(cell).replace("|", "\\|").replace("\n", "<br>") for cell in cells]
            lines.append(f"{indent}| " + " | ".join(rendered) + " |")
            if index == 0:
                separator = " | ".join("---" for _ in cells)
                if not has_header:
                    # Markdown needs a header row; keep the first row visible.
                    lines.insert(0, f"{indent}| " + " | ".join("" for _ in cells) + " |")
                lines.append(f"{indent}| {separator} |")
        return lines


# --------------------------------------------------------------------------
# command line
# --------------------------------------------------------------------------

def load_token(env_dir="."):
    """Find NOTION_TOKEN in the environment or in the nearest .env above env_dir.

    python-dotenv is not required: the parsing needed for a token line is trivial
    and this keeps the exporter runnable with nothing but the standard library.
    """
    if os.getenv("NOTION_TOKEN"):
        return os.getenv("NOTION_TOKEN")

    current = Path(env_dir).resolve()
    if not current.is_dir():
        current = current.parent

    while True:
        env_file = current / ".env"
        if env_file.exists():
            print(f"🔑 Loading .env from: {env_file}")
            with open(env_file, "r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
            if os.getenv("NOTION_TOKEN"):
                return os.getenv("NOTION_TOKEN")
        if current == current.parent:
            return None
        current = current.parent


def add_docs_arguments(parser):
    """Define the docs options; shared by the standalone CLI and ncsft's main.py."""
    parser.add_argument("pages", nargs="*", help="Page ids or Notion URLs to export")
    parser.add_argument("-o", "--output", required=True, help="Output directory")
    parser.add_argument(
        "--children-of", metavar="PAGE",
        help="Also export every sub-page of this page (its own content is not written)"
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List the sub-pages of --children-of and exit without exporting"
    )
    parser.add_argument(
        "--env", metavar="DIR", default=".",
        help="Directory to search upwards from for the .env holding NOTION_TOKEN"
    )
    parser.add_argument(
        "--exclude", action="append", metavar="REGEX", default=None,
        help="Skip sub-pages whose title matches this regex (case-insensitive; "
             "repeatable). Pages named on the command line are never excluded."
    )
    parser.add_argument("--cache", help="Cache file path (default: {output}/.notion_docs_cache.json)")
    parser.add_argument("-f", "--force", action="store_true", help="Re-download even if unchanged")
    parser.add_argument("--depth", type=int, default=10, help="Maximum sub-page recursion depth")
    parser.add_argument("--date", help="Retrieval date recorded in each file (default: today)")
    return parser


def run_export(args):
    """Execute the docs export described by `args`. Returns a process exit code."""
    token = load_token(args.env)
    if not token:
        print(f"❌ NOTION_TOKEN not found (looked for .env upwards from {Path(args.env).resolve()})")
        return 1

    reader = NotionReader(token, verbose=True)
    output_dir = Path(args.output).resolve()
    page_ids = [normalize_id(p) for p in args.pages]

    if args.children_of:
        parent_id = normalize_id(args.children_of)
        print(f"🔎 Listing sub-pages of {parent_id}")
        try:
            blocks = reader.list_children(parent_id)
        except Exception as exc:
            print(f"❌ Could not read {parent_id}: {exc}")
            return 1

        children = [b for b in blocks if b.get("type") == "child_page"]
        print(f"   found {len(children)} sub-pages")

        if getattr(args, "list", False):
            for index, block in enumerate(children, 1):
                title = block["child_page"].get("title", "Untitled")
                print(f"   {index:3d}. {block['id']}  {title}")
                print(f"        -> {sanitize_name(title)}")
            return 0

        for block in children:
            if block["id"] not in page_ids:
                page_ids.append(block["id"])

    if not page_ids:
        print("❌ Nothing to export: pass page ids or use --children-of")
        return 1

    cache_path = Path(args.cache) if args.cache else output_dir / ".notion_docs_cache.json"
    exporter = DocExporter(
        reader,
        cache_path=cache_path,
        retrieved_on=args.date,
        exclude=getattr(args, "exclude", None),
    )
    if exporter.exclude_patterns:
        print(f"🚫 Excluding sub-pages matching: {', '.join(p.pattern for p in exporter.exclude_patterns)}")

    print(f"📥 Exporting {len(page_ids)} document tree(s) to: {output_dir}")
    print("=" * 60)

    for index, page_id in enumerate(page_ids, 1):
        print(f"[{index}/{len(page_ids)}]", end=" ")
        try:
            exporter.export_tree(page_id, output_dir, force=args.force, max_depth=args.depth)
        except KeyboardInterrupt:
            exporter.save_cache()
            print("\n⚠️  Interrupted; rerun the same command to resume")
            return 130
        except Exception as exc:
            print(f"❌ Export failed for {page_id}: {exc}")
            exporter.stats["failed"] += 1

    exporter.save_cache()
    stats = exporter.stats

    print("=" * 60)
    print(f"✨ Export completed: {stats['written']} written, "
          f"{stats['skipped']} unchanged, {stats['excluded']} excluded, {stats['failed']} failed "
          f"({stats['pages']} pages visited, {reader.request_count} API calls)")
    if exporter.excluded_titles:
        print(f"\n🚫 Skipped {len(exporter.excluded_titles)} sub-page(s) by --exclude:")
        for title in exporter.excluded_titles:
            print(f"   - {title}")
    print(f"📁 Output directory: {output_dir}")
    print(f"💾 Cache: {cache_path}")

    if exporter.expiring_assets:
        print(f"\n⚠️  {len(exporter.expiring_assets)} Notion-hosted file link(s) were written as "
              "signed URLs and expire in about an hour:")
        for path, url in exporter.expiring_assets[:10]:
            print(f"   {path}  <-  {url[:80]}...")

    return 1 if stats["failed"] else 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="notion_docs",
        description="Export a Notion page and its sub-pages as a Markdown tree.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python notion_docs.py <page-id> -o ./docs --env /path/holding/dotenv
  python notion_docs.py --children-of <index-page-id> --list -o ./docs
  python notion_docs.py --children-of <index-page-id> -o ./docs
  python notion_docs.py <page-id> -o ./docs -f          # ignore the cache
        """
    )
    add_docs_arguments(parser)
    return run_export(parser.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
