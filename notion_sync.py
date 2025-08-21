import os
import hashlib
import json
from pathlib import Path
from notion_client import Client
from datetime import datetime
from config import Config

class NotionSync:
    """Notion file sync core class (multi-language support)"""
    
    def __init__(self, notion_token, parent_page_id):
        """
        Initialize synchronizer
        
        Args:
            notion_token: Notion API token
            parent_page_id: Parent page ID (files will be created as subpages of this page)
        """
        self.notion = Client(auth=notion_token)
        self.parent_page_id = parent_page_id
        self.sync_cache = self._load_sync_cache()
        
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
    
    def create_or_update_subpage(self, file_path, project_root, force_update=False):
        """
        Create or update subpage for file
        
        Args:
            file_path: File path
            project_root: Project root directory path
            force_update: Whether to force update
            
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
            relative_path = str(file_absolute_path.relative_to(project_root_path))
        except ValueError as e:
            # If relative_to fails, use filename as fallback
            print(f"Warning: Cannot calculate relative path {file_path}, using filename: {e}")
            relative_path = file_path.name
        
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
        
        # Check content length limit
        if len(content) > Config.MAX_CONTENT_LENGTH:
            content = content[:Config.MAX_CONTENT_LENGTH] + "\n\n... (File too long, truncated)"
        
        # Prepare page title and language
        page_title = f"{file_path.name}"
        language = Config.get_language_for_extension(file_path.suffix)
        
        try:
            # Check if page already exists
            page_id = self.sync_cache.get(relative_path, {}).get('page_id')
            
            if page_id:
                # Update existing subpage
                try:
                    self.notion.pages.update(
                        page_id=page_id,
                        properties={
                            "title": [{
                                "text": {
                                    "content": page_title
                                }
                            }]
                        }
                    )
                    
                    # Update page content
                    self._update_subpage_content(page_id, content, file_path, language)
                    print(f"🔄 Updated {relative_path}")
                    
                except Exception as e:
                    print(f"Update page failed, trying to recreate: {str(e)}")
                    page_id = None
            
            if not page_id:
                # Create new subpage
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
                self._update_subpage_content(page_id, content, file_path, language)
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
    
    def _update_subpage_content(self, page_id, content, file_path, language):
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
            
            # Force chunking for all code content
            if len(content) > 0:
                # Use smaller safe chunk size
                max_chunk_size = 1500  # Further reduced to 1500 characters
                
                # Split code by lines into chunks
                content_lines = content.split('\n')
                current_chunk_lines = []
                current_chunk_length = 0
                chunk_number = 1
                
                for line in content_lines:
                    line_length = len(line) + 1  # +1 for newline character
                    
                    # Check if adding this line would exceed limit
                    if current_chunk_length + line_length > max_chunk_size and current_chunk_lines:
                        # Create current chunk
                        chunk_content = '\n'.join(current_chunk_lines)
                        
                        # Add chunk title (unless it's the first and only chunk)
                        if chunk_number > 1 or len(content) > max_chunk_size:
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
                        
                        # Add code block
                        blocks.append({
                            "object": "block",
                            "type": "code",
                            "code": {
                                "rich_text": [{
                                    "type": "text", 
                                    "text": {"content": chunk_content}
                                }],
                                "language": language
                            }
                        })
                        
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
                    
                    # Add chunk title (if there are multiple chunks)
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
                    
                    blocks.append({
                        "object": "block",
                        "type": "code",
                        "code": {
                            "rich_text": [{
                                "type": "text", 
                                "text": {"content": chunk_content}
                            }],
                            "language": language
                        }
                    })
            
            # Add blocks to page in batches
            batch_size = 100
            for i in range(0, len(blocks), batch_size):
                batch = blocks[i:i+batch_size]
                self.notion.blocks.children.append(block_id=page_id, children=batch)
            
        except Exception as e:
            print(f"Failed to update page content: {str(e)}")
    
    def sync_project(self, project_path, force_update=False, file_extensions=None):
        """
        Sync entire project
        
        Args:
            project_path: Project path
            force_update: Whether to force update all files
            file_extensions: List of file extensions to sync, None means all supported types
        """
        try:
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
                
                if self.create_or_update_subpage(file_path, project_root, force_update):
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
            self._save_sync_cache()
            
        except Exception as e:
            print(f"Project sync failed: {str(e)}")
    
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
    
    def _load_sync_cache(self):
        """Load sync cache"""
        cache_file = Path(Config.CACHE_FILE)
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Failed to load cache: {str(e)}")
                return {}
        return {}
    
    def _save_sync_cache(self):
        """Save sync cache"""
        try:
            with open(Config.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.sync_cache, f, indent=2, ensure_ascii=False)
            print(f"💾 Cache saved to {Config.CACHE_FILE}")
        except Exception as e:
            print(f"Failed to save cache: {str(e)}")
    
    def clean_deleted_files(self):
        """Clean cache records of deleted files"""
        if not self.sync_cache:
            return
        
        to_remove = []
        for file_path in self.sync_cache.keys():
            if not Path(file_path).exists():
                to_remove.append(file_path)
        
        for file_path in to_remove:
            del self.sync_cache[file_path]
            print(f"🗑️  Removed deleted file from cache: {file_path}")
        
        if to_remove:
            self._save_sync_cache()
    
    def get_project_stats(self, project_path):
        """Get project statistics"""
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
                relative_path = str(file_path.relative_to(project_root))
            except ValueError:
                relative_path = file_path.name
                
            if relative_path in self.sync_cache:
                stats['synced_files'] += 1
            else:
                stats['unsynced_files'] += 1
        
        return stats