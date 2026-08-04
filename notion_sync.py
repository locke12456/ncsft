import os
import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path
from notion_client import Client
from datetime import datetime
from config import Config

class NotionSync:
    """Notion file sync core class with pull functionality"""
    
    def __init__(self, notion_token=None, parent_page_id=None):
        """
        Initialize synchronizer
        
        Args:
            notion_token: Notion API token (optional, will use from config if not provided)
            parent_page_id: Parent page ID (optional, will use from config if not provided)
        """
        self.notion_token = notion_token or Config.NOTION_TOKEN
        self.parent_page_id = parent_page_id or Config.PARENT_PAGE_ID
        self.notion = Client(auth=self.notion_token)
        self.sync_cache = {}
        self.directory_page_cache = {}
        
    def load_cache_for_project(self, project_path):
        """Load sync cache for specific project"""
        cache_file = Config.get_cache_path(project_path)
        self.sync_cache = self._load_sync_cache(cache_file)
        return cache_file
        
    def scan_source_files(self, root_path, extensions=None):
        """
        Scan all code files in specified directory
        
        Args:
            root_path: Root directory path
            extensions: List of file extensions to scan, None means scan all supported types
            
        Returns:
            list: List of code file paths
        """
        source_files = []
        root = Path(root_path).resolve()  # Resolve to absolute path
        
        if not root.exists():
            raise ValueError(f"Specified path does not exist: {root_path}")
        
        # If no extensions specified, use all supported types
        if extensions is None:
            extensions = Config.get_supported_extensions()
        
        print(f"Starting directory scan: {root}")
        print(f"Supported file types: {', '.join(extensions)}")
        
        for ext in extensions:
            pattern = f"*{ext}"
            for file_path in root.rglob(pattern):
                # Check if in ignore list
                if Config.should_ignore_path(str(file_path)):
                    continue
                    
                source_files.append(file_path)
        
        # Sort by file path for consistent processing order
        source_files.sort()
        
        print(f"Scan complete, found {len(source_files)} code files")
        return source_files
    
    def get_file_hash(self, file_path):
        """
        Calculate MD5 hash of file
        
        Args:
            file_path: File path
            
        Returns:
            str: MD5 hash string
        """
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
                return hashlib.md5(file_content).hexdigest()
        except Exception as e:
            print(f"Cannot calculate file hash {file_path}: {str(e)}")
            return None
    
    def get_file_size(self, file_path):
        """Get file size"""
        try:
            return os.path.getsize(file_path)
        except:
            return 0
    
    def create_or_update_subpage(self, file_path, project_root, force_update=False, use_plain_text=False, update_mode='recreate'):
        """
        Create or update subpage for file
        
        Args:
            file_path: File path
            project_root: Project root directory path
            force_update: Whether to force update
            update_mode: 'recreate' = delete old page and create new;
                         'clear' = keep old page, clear content and rewrite
            
        Returns:
            str|None: Page ID or None (if failed)
        """
        file_hash = self.get_file_hash(file_path)
        if not file_hash:
            return None
            
        # Fix relative path calculation issue
        try:
            project_root_path = Path(project_root).resolve()
            file_absolute_path = Path(file_path).resolve()
            relative_path_obj = file_absolute_path.relative_to(project_root_path)
            relative_path = str(relative_path_obj)
            relative_directory = relative_path_obj.parent
            #relative_path = relative_path.replace('\\', '/')  
        except ValueError as e:
            print(f"Warning: Cannot calculate relative path {file_path}, using absolute path: {e}")
            relative_path = str(Path(file_path).resolve())
            relative_path = relative_path.replace('\\', '/')
            relative_directory = Path()
        
        file_size = self.get_file_size(file_path)
        
        # Check if update needed
        if not force_update and relative_path in self.sync_cache:
            cached_data = self.sync_cache[relative_path]
            if cached_data.get('hash') == file_hash:
                print(f"⏭️  Skipping {relative_path} (no changes)")
                return cached_data.get('page_id')
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try other encodings
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    content = f.read()
            except:
                print(f"❌ Cannot read file {file_path}: encoding issue")
                return None
        except Exception as e:
            print(f"❌ Cannot read file {file_path}: {str(e)}")
            return None
        
        # Content will be split into multiple code block parts
        # each up to MAX_CONTENT_LENGTH characters (no truncation)
        
        # Prepare page title and language
        page_title = f"{file_path.name}"
        language = Config.get_language_for_extension(file_path.suffix)
        is_markdown = file_path.suffix.lower() in ('.md', '.markdown')
        if use_plain_text and not is_markdown:
            language = 'plain text'
        
        try:
            target_parent_page_id = self.parent_page_id
            if is_markdown:
                target_parent_page_id = self._ensure_directory_hierarchy(relative_directory)

            old_page_id = self.sync_cache.get(relative_path, {}).get('page_id')
            
            if old_page_id and update_mode == 'clear' and not is_markdown:
                # Clear mode applies only to block-based code pages.
                try:
                    page_id = old_page_id
                    self._update_subpage_content(page_id, content, file_path, language, use_plain_text)
                    print(f"🔄 Cleared and updated {relative_path}")
                except Exception as e:
                    print(f"⚠️ Clear mode failed, falling back to recreate: {str(e)}")
                    # Fallback to recreate
                    old_page_id = None
            
            if not old_page_id or update_mode == 'recreate' or is_markdown:
                # Markdown is created with content in one request, so it uses recreate mode.
                if old_page_id:
                    try:
                        self.notion.pages.update(
                            page_id=old_page_id,
                            archived=True
                        )
                        print(f"🗑️ Deleted old page for {relative_path}")
                    except Exception as e:
                        print(f"⚠️ Could not delete old page: {str(e)}")
                
                if is_markdown:
                    new_page = self._create_markdown_page(
                        page_title,
                        content,
                        target_parent_page_id
                    )
                else:
                    new_page = self.notion.pages.create(
                        parent={
                            "type": "page_id",
                            "page_id": self.parent_page_id
                        },
                        properties={
                            "title": [{
                                "text": {
                                    "content": page_title
                                }
                            }]
                        }
                    )
                
                page_id = new_page["id"]
                if not is_markdown:
                    self._update_subpage_content(page_id, content, file_path, language, use_plain_text)
            print(f"✅ Created {relative_path}")
            
            # Update cache
            self.sync_cache[relative_path] = {
                'page_id': page_id,
                'hash': file_hash,
                'last_sync': datetime.now().isoformat(),
                'file_size': file_size,
                'language': language
            }
            
            return page_id
            
        except Exception as e:
            print(f"❌ Sync failed {relative_path}: {str(e)}")
            return None
    
    def _find_child_page(self, parent_page_id, page_title):
        """Find an existing direct child page by title."""
        cursor = None
        while True:
            request_args = {
                "block_id": parent_page_id,
                "page_size": 100
            }
            if cursor:
                request_args["start_cursor"] = cursor

            response = self.notion.blocks.children.list(**request_args)
            for block in response.get("results", []):
                if (
                    block.get("type") == "child_page"
                    and block.get("child_page", {}).get("title") == page_title
                ):
                    return block.get("id")

            if not response.get("has_more"):
                return None
            cursor = response.get("next_cursor")
            if not cursor:
                return None

    def _ensure_directory_hierarchy(self, relative_directory):
        """Create or reuse nested Notion pages for a relative directory path."""
        if not relative_directory or str(relative_directory) in ('', '.'):
            return self.parent_page_id

        current_parent_id = self.parent_page_id
        path_parts = []

        for directory_name in relative_directory.parts:
            if directory_name in ('', '.'):
                continue

            path_parts.append(directory_name)
            cache_key = '/'.join(path_parts)
            cached_page_id = self.directory_page_cache.get(cache_key)
            if cached_page_id:
                current_parent_id = cached_page_id
                continue

            directory_page_id = self._find_child_page(
                current_parent_id,
                directory_name
            )
            if not directory_page_id:
                directory_page = self.notion.pages.create(
                    parent={
                        "type": "page_id",
                        "page_id": current_parent_id
                    },
                    properties={
                        "title": [{
                            "text": {
                                "content": directory_name
                            }
                        }]
                    }
                )
                directory_page_id = directory_page["id"]

            self.directory_page_cache[cache_key] = directory_page_id
            current_parent_id = directory_page_id

        return current_parent_id

    def _create_markdown_page(self, page_title, markdown_content, parent_page_id=None):
        """Create a Notion page by passing Markdown directly to Notion."""
        target_parent_page_id = parent_page_id or self.parent_page_id
        payload = {
            "parent": {
                "type": "page_id",
                "page_id": target_parent_page_id
            },
            "properties": {
                "title": [{
                    "text": {
                        "content": page_title
                    }
                }]
            },
            "markdown": markdown_content
        }
        request = urllib.request.Request(
            "https://api.notion.com/v1/pages",
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers={
                "Authorization": f"Bearer {self.notion_token}",
                "Content-Type": "application/json",
                "Notion-Version": "2026-03-11"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(request) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as error:
            response_body = error.read().decode('utf-8', errors='replace')
            raise RuntimeError(
                f"Notion Markdown API failed ({error.code}): {response_body}"
            ) from error

    def _update_subpage_content(self, page_id, content, file_path, language, use_plain_text=False):
        """
        Update subpage content

        Args:
            page_id: Page ID
            content: File content
            file_path: File path
            language: Programming language
        """
        try:
            # Clear existing content
            children = self.notion.blocks.children.list(block_id=page_id)
            for block in children["results"]:
                try:
                    self.notion.blocks.delete(block_id=block["id"])
                except:
                    pass  # Some blocks may not be deletable, ignore errors
            
            # Choose appropriate icon based on file type
            file_icons = {
                'c#': '🔷',
                'python': '🐍',
                'javascript': '📜',
                'typescript': '📘',
                'java': '☕',
                'c++': '⚡',
                'c': '🔧',
                'go': '🔷',
                'rust': '🦀',
                'php': '🐘',
                'ruby': '💎',
                'swift': '🕊️',
                'kotlin': '🎯'
            }
            
            icon = file_icons.get(language, '📄')
            
            # Base content blocks
            blocks = [
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{
                            "type": "text", 
                            "text": {"content": f"{icon} {file_path.name}"}
                        }]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{
                            "type": "text", 
                            "text": {"content": f"📁 Path: {str(file_path)}\n🔤 Language: {language.title()}\n📏 Size: {len(content)} characters"}
                        }]
                    }
                },
                {
                    "object": "block",
                    "type": "divider",
                    "divider": {}
                }
            ]
            
            # Split content into code block parts, each up to MAX_CONTENT_LENGTH
            if len(content) > 0:
                max_block_size = Config.MAX_CONTENT_LENGTH
                
                # Split content by lines into parts of max_block_size each
                content_lines = content.split('\n')
                current_chunk_lines = []
                current_chunk_length = 0
                chunk_number = 1
                
                for line in content_lines:
                    line_length = len(line) + 1  # +1 for newline character
                    
                    # Check if adding this line would exceed limit
                    if current_chunk_length + line_length > max_block_size and current_chunk_lines:
                        # Create current chunk as a single code block
                        chunk_content = '\n'.join(current_chunk_lines)
                        code_block = self._build_single_code_block(chunk_content, language)
                        
                        # Add chunk title if multiple parts
                        if chunk_number > 1 or len(content) > max_block_size:
                            blocks.append({
                                "object": "block",
                                "type": "heading_3",
                                "heading_3": {
                                    "rich_text": [{
                                        "type": "text", 
                                        "text": {"content": f"📋 Code (Part {chunk_number})"}
                                    }]
                                }
                            })
                        
                        blocks.append(code_block)
                        
                        # Start new chunk
                        current_chunk_lines = [line]
                        current_chunk_length = line_length
                        chunk_number += 1
                    else:
                        current_chunk_lines.append(line)
                        current_chunk_length += line_length
                
                # Add final chunk
                if current_chunk_lines:
                    chunk_content = '\n'.join(current_chunk_lines)
                    code_block = self._build_single_code_block(chunk_content, language)
                    
                    if chunk_number > 1:
                        blocks.append({
                            "object": "block",
                            "type": "heading_3",
                            "heading_3": {
                                "rich_text": [{
                                    "type": "text", 
                                    "text": {"content": f"📋 Code (Part {chunk_number}, Complete)"}
                                }]
                            }
                        })
                    
                    blocks.append(code_block)
            
            # Add blocks to page in batches
            batch_size = 100
            for i in range(0, len(blocks), batch_size):
                batch = blocks[i:i+batch_size]
                self.notion.blocks.children.append(block_id=page_id, children=batch)
            
        except Exception as e:
            print(f"Failed to update page content: {str(e)}")

    def _build_single_code_block(self, content, language, chunk_size=1500):
        """
        Split full source into multiple rich_text parts inside a single code block.
        Notion API limit: each rich_text element max 2000 chars; array max ~100 elements.
        """
        rich_text_parts = []
        current_chunk_lines = []
        current_length = 0

        for line in content.split('\n'):
            line_len = len(line) + 1  # +1 for newline
            if current_length + line_len > chunk_size and current_chunk_lines:
                rich_text_parts.append({
                    "type": "text",
                    "text": {"content": '\n'.join(current_chunk_lines) + '\n'}
                })
                current_chunk_lines = [line]
                current_length = line_len
            else:
                current_chunk_lines.append(line)
                current_length += line_len

        if current_chunk_lines:
            rich_text_parts.append({
                "type": "text",
                "text": {"content": '\n'.join(current_chunk_lines)}
            })

        return {
            "object": "block",
            "type": "code",
            "code": {"rich_text": rich_text_parts, "language": language}
        }

    def sync_project(self, project_path, force_update=False, file_extensions=None, use_plain_text=False, update_mode='recreate'):
        """
        Sync entire project
        
        Args:
            project_path: Project path
            force_update: Whether to force update all files
            file_extensions: List of file extensions to sync, None means all supported types
            update_mode: 'recreate' = delete old page and create new;
                         'clear' = keep old page, clear content and rewrite
        """
        try:
            # Load environment variables from project path
            Config.load_env_from_path(project_path)
            
            # Update token and parent page ID if they changed
            self.notion_token = Config.NOTION_TOKEN
            self.parent_page_id = Config.PARENT_PAGE_ID
            self.notion = Client(auth=self.notion_token)
            self.directory_page_cache = {}
            
            # Load cache for this specific project
            cache_file = self.load_cache_for_project(project_path)
            
            # Resolve project path to absolute path
            project_root = Path(project_path).resolve()
            
            # If specific extensions specified, only scan those types
            source_files = self.scan_source_files(project_root, file_extensions)
            
            if not source_files:
                print("No matching code files found")
                return
            
            print(f"\nStarting sync of {len(source_files)} files...")
            print("=" * 60)
            
            # Group statistics by language
            language_stats = {}
            success_count = 0
            
            for i, file_path in enumerate(source_files, 1):
                print(f"[{i}/{len(source_files)}] ", end="")
                
                if self.create_or_update_subpage(file_path, project_root, force_update, use_plain_text, update_mode):
                    success_count += 1
                    # Statistics for language type
                    ext = file_path.suffix
                    language = Config.get_language_for_extension(ext)
                    language_stats[language] = language_stats.get(language, 0) + 1
            
            print("=" * 60)
            print(f"✨ Sync completed: {success_count}/{len(source_files)} files synced successfully")
            
            # Display language statistics
            if language_stats:
                print("\n📊 File type statistics:")
                for lang, count in sorted(language_stats.items()):
                    print(f"   {lang.title()}: {count} files")
            
            # Save cache
            self._save_sync_cache(cache_file)
            
        except Exception as e:
            print(f"Project sync failed: {str(e)}")
    
    def _retrieve_markdown_page(self, page_id):
        """Retrieve a Notion page as Enhanced Markdown."""
        api_base = "https:" + "//api.notion.com/v1/pages"
        request_url = "/".join((api_base, str(page_id), "markdown"))
        request = urllib.request.Request(
            request_url,
            headers={
                "Authorization": f"Bearer {self.notion_token}",
                "Notion-Version": "2026-03-11",
            },
            method="GET",
        )

        try:
            with urllib.request.urlopen(request) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            response_body = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Notion Markdown API failed ({error.code}): {response_body}"
            ) from error

        if payload.get("truncated"):
            unknown_block_ids = payload.get("unknown_block_ids", [])
            raise RuntimeError(
                "Notion Markdown response was truncated; refusing to write "
                f"partial content (unknown blocks: {unknown_block_ids})"
            )

        markdown_content = payload.get("markdown")
        if not isinstance(markdown_content, str):
            raise RuntimeError(
                "Notion Markdown response did not contain markdown text"
            )
        return markdown_content

    def pull_from_notion(self, project_path, output_dir=None, force_overwrite=False):
        """
        Pull files from Notion pages back to local directory
        
        Args:
            project_path: Original project path
            output_dir: Output directory (default: project_path + '_from_notion')
            force_overwrite: Whether to force overwrite existing local files
        """
        try:
            # Load environment variables and cache
            Config.load_env_from_path(project_path)
            self.notion_token = Config.NOTION_TOKEN
            self.parent_page_id = Config.PARENT_PAGE_ID
            self.notion = Client(auth=self.notion_token)
            
            cache_file = self.load_cache_for_project(project_path)
            
            if not self.sync_cache:
                print("❌ No sync cache found. Please sync project first.")
                return
            
            # Set output directory
            if not output_dir:
                project_name = Path(project_path).name
                output_dir = Path(project_path).parent / f"{project_name}_from_notion"
            else:
                output_dir = Path(output_dir)
            
            output_dir.mkdir(exist_ok=True)
            print(f"📥 Pulling files to: {output_dir}")
            print("=" * 60)
            
            success_count = 0
            total_files = len(self.sync_cache)
            
            for i, (relative_path, cache_data) in enumerate(self.sync_cache.items(), 1):
                page_id = cache_data.get('page_id')
                if not page_id:
                    continue
                
                print(f"[{i}/{total_files}] Pulling {relative_path}...")
                
                try:
                    # Create output file path
                    output_file = output_dir / relative_path
                    
                    # Check if file exists and force_overwrite is False
                    if output_file.exists() and not force_overwrite:
                        print(f"⏭️  Skipping {relative_path} (file exists, use -f to overwrite)")
                        continue
                    
                    # Get page content
                    is_markdown = (
                        Path(relative_path).suffix.lower() in ('.md', '.markdown')
                        or cache_data.get('language') == 'markdown'
                    )
                    if is_markdown:
                        content = self._retrieve_markdown_page(page_id)
                    else:
                        content = self._extract_code_from_page(page_id)
                    if content is None:
                        print(f"❌ Failed to extract content from {relative_path}")
                        continue
                    
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Write content to file
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    print(f"✅ Pulled {relative_path}")
                    success_count += 1
                    
                except Exception as e:
                    print(f"❌ Failed to pull {relative_path}: {str(e)}")
            
            print("=" * 60)
            print(f"✨ Pull completed: {success_count}/{total_files} files pulled successfully")
            print(f"📁 Output directory: {output_dir}")
            
        except Exception as e:
            print(f"Pull operation failed: {str(e)}")
    
    def _extract_code_from_page(self, page_id):
        """
        Extract code content from Notion page
        
        Args:
            page_id: Notion page ID
            
        Returns:
            str|None: Extracted code content or None if failed
        """
        try:
            blocks = self.notion.blocks.children.list(block_id=page_id)
            code_parts = []
            
            for block in blocks["results"]:
                if block["type"] == "code":
                    code_block = block["code"]
                    if code_block["rich_text"]:
                        code_content = ""
                        for text_obj in code_block["rich_text"]:
                            code_content += text_obj["text"]["content"]
                        code_parts.append(code_content)
            
            if code_parts:
                return '\n'.join(code_parts)
            else:
                print("Warning: No code blocks found in page")
                return ""
                
        except Exception as e:
            print(f"Error extracting code from page {page_id}: {str(e)}")
            return None
    
    def sync_specific_language(self, project_path, language, force_update=False):
        """
        Sync files of specific programming language
        
        Args:
            project_path: Project path
            language: Programming language name (e.g., 'python', 'c#')
            force_update: Whether to force update
        """
        # Find corresponding file extensions
        extensions = []
        for ext, lang in Config.SUPPORTED_LANGUAGES.items():
            if lang.lower() == language.lower():
                extensions.append(ext)
        
        if not extensions:
            print(f"❌ Unsupported programming language: {language}")
            print(f"Supported languages: {', '.join(set(Config.SUPPORTED_LANGUAGES.values()))}")
            return
        
        print(f"🎯 Syncing {language.title()} files (extensions: {', '.join(extensions)})")
        self.sync_project(project_path, force_update, extensions)
    
    def _load_sync_cache(self, cache_file):
        """Load sync cache from specific file"""
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Failed to load cache: {str(e)}")
                return {}
        return {}
    
    def _save_sync_cache(self, cache_file):
        """Save sync cache to specific file"""
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.sync_cache, f, indent=2, ensure_ascii=False)
            print(f"💾 Cache saved to {cache_file}")
        except Exception as e:
            print(f"Failed to save cache: {str(e)}")
    
    def clean_deleted_files(self, project_path):
        """Clean cache records of deleted files"""
        cache_file = self.load_cache_for_project(project_path)
        
        if not self.sync_cache:
            return
        
        project_root = Path(project_path).resolve()
        to_remove = []
        
        for relative_path in self.sync_cache.keys():
            full_path = project_root / relative_path
            if not full_path.exists():
                to_remove.append(relative_path)
        
        for relative_path in to_remove:
            del self.sync_cache[relative_path]
            print(f"🗑️  Removed deleted file from cache: {relative_path}")
        
        if to_remove:
            self._save_sync_cache(cache_file)
    
    def get_project_stats(self, project_path):
        """Get project statistics"""
        Config.load_env_from_path(project_path)
        cache_file = self.load_cache_for_project(project_path)
        
        project_root = Path(project_path).resolve()
        source_files = self.scan_source_files(project_root)
        
        stats = {
            'total_files': len(source_files),
            'languages': {},
            'synced_files': 0,
            'unsynced_files': 0
        }
        
        for file_path in source_files:
            ext = file_path.suffix
            language = Config.get_language_for_extension(ext)
            stats['languages'][language] = stats['languages'].get(language, 0) + 1
            
            # Check sync status
            try:
                project_root_path = Path(project_path).resolve()
                file_absolute_path = Path(file_path).resolve()
                relative_path = str(file_absolute_path.relative_to(project_root_path))
            except ValueError:
                # 同樣的修正：使用完整路徑確保一致性
                relative_path = str(Path(file_path).resolve())
                
            if relative_path in self.sync_cache:
                stats['synced_files'] += 1
            else:
                stats['unsynced_files'] += 1
        
        return stats