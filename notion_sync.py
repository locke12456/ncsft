import os
import hashlib
import json
from pathlib import Path
from notion_client import Client
from datetime import datetime
from config import Config

class NotionSync:
    """Notion 檔案同步核心類別 (支援多語言)"""
    
    def __init__(self, notion_token, parent_page_id):
        """
        初始化同步器
        
        Args:
            notion_token: Notion API token
            parent_page_id: 父頁面 ID（檔案將建立為此頁面的子頁面）
        """
        self.notion = Client(auth=notion_token)
        self.parent_page_id = parent_page_id
        self.sync_cache = self._load_sync_cache()
        
    def scan_source_files(self, root_path, extensions=None):
        """
        掃描指定資料夾中的所有程式碼檔案
        
        Args:
            root_path: 根目錄路徑
            extensions: 要掃描的檔案副檔名清單，None 表示掃描所有支援的類型
            
        Returns:
            list: 程式碼檔案路徑清單
        """
        source_files = []
        root = Path(root_path).resolve()  # 解析為絕對路徑
        
        if not root.exists():
            raise ValueError(f"指定路徑不存在: {root_path}")
        
        # 如果沒有指定副檔名，使用所有支援的類型
        if extensions is None:
            extensions = Config.get_supported_extensions()
        
        print(f"開始掃描目錄: {root}")
        print(f"支援的檔案類型: {', '.join(extensions)}")
        
        for ext in extensions:
            pattern = f"*{ext}"
            for file_path in root.rglob(pattern):
                # 檢查是否在忽略清單中
                if Config.should_ignore_path(str(file_path)):
                    continue
                    
                source_files.append(file_path)
        
        # 按檔案路徑排序，確保一致的處理順序
        source_files.sort()
        
        print(f"掃描完成，找到 {len(source_files)} 個程式碼檔案")
        return source_files
    
    def get_file_hash(self, file_path):
        """
        計算檔案的 MD5 hash
        
        Args:
            file_path: 檔案路徑
            
        Returns:
            str: MD5 hash 字串
        """
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
                return hashlib.md5(file_content).hexdigest()
        except Exception as e:
            print(f"無法計算檔案 hash {file_path}: {str(e)}")
            return None
    
    def get_file_size(self, file_path):
        """取得檔案大小"""
        try:
            return os.path.getsize(file_path)
        except:
            return 0
    
    def create_or_update_subpage(self, file_path, project_root, force_update=False):
        """
        建立或更新檔案的子頁面
        
        Args:
            file_path: 檔案路徑
            project_root: 專案根目錄路徑
            force_update: 是否強制更新
            
        Returns:
            str|None: 頁面 ID 或 None（如果失敗）
        """
        file_hash = self.get_file_hash(file_path)
        if not file_hash:
            return None
            
        # 修復相對路徑計算問題
        try:
            project_root_path = Path(project_root).resolve()
            file_absolute_path = Path(file_path).resolve()
            relative_path = str(file_absolute_path.relative_to(project_root_path))
        except ValueError as e:
            # 如果 relative_to 失敗，使用檔案名作為備選
            print(f"警告：無法計算相對路徑 {file_path}，使用檔案名: {e}")
            relative_path = file_path.name
        
        file_size = self.get_file_size(file_path)
        
        # 檢查是否需要更新
        if not force_update and relative_path in self.sync_cache:
            cached_data = self.sync_cache[relative_path]
            if cached_data.get('hash') == file_hash:
                print(f"⏭️  跳過 {relative_path} (無變更)")
                return cached_data.get('page_id')
        
        # 讀取檔案內容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # 嘗試其他編碼
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    content = f.read()
            except:
                print(f"❌ 無法讀取檔案 {file_path}: 編碼問題")
                return None
        except Exception as e:
            print(f"❌ 無法讀取檔案 {file_path}: {str(e)}")
            return None
        
        # 檢查內容長度限制
        if len(content) > Config.MAX_CONTENT_LENGTH:
            content = content[:Config.MAX_CONTENT_LENGTH] + "\\n\\n... (檔案過長，已截斷)"
        
        # 準備頁面標題和語言
        page_title = f"{file_path.name}"
        language = Config.get_language_for_extension(file_path.suffix)
        
        try:
            # 檢查頁面是否已存在
            page_id = self.sync_cache.get(relative_path, {}).get('page_id')
            
            if page_id:
                # 更新現有子頁面
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
                    
                    # 更新頁面內容
                    self._update_subpage_content(page_id, content, file_path, language)
                    print(f"🔄 更新 {relative_path}")
                    
                except Exception as e:
                    print(f"更新頁面失敗，嘗試重新建立: {str(e)}")
                    page_id = None
            
            if not page_id:
                # 建立新的子頁面
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
                print(f"✅ 建立 {relative_path}")
            
            # 更新快取
            self.sync_cache[relative_path] = {
                'page_id': page_id,
                'hash': file_hash,
                'last_sync': datetime.now().isoformat(),
                'file_size': file_size,
                'language': language
            }
            
            return page_id
            
        except Exception as e:
            print(f"❌ 同步失敗 {relative_path}: {str(e)}")
            return None
    
    def _update_subpage_content(self, page_id, content, file_path, language):
        """
        更新子頁面內容

        Args:
            page_id: 頁面 ID
            content: 檔案內容
            file_path: 檔案路徑
            language: 程式語言
        """
        try:
            # 清除現有內容
            children = self.notion.blocks.children.list(block_id=page_id)
            for block in children["results"]:
                try:
                    self.notion.blocks.delete(block_id=block["id"])
                except:
                    pass  # 某些 block 可能無法刪除，忽略錯誤
            
            # 根據檔案類型選擇適當的圖示
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
            
            # 基礎內容區塊
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
                            "text": {"content": f"📁 路徑: {str(file_path)}\n🔤 語言: {language.title()}\n📏 大小: {len(content)} 字元"}
                        }]
                    }
                },
                {
                    "object": "block",
                    "type": "divider",
                    "divider": {}
                }
            ]
            
            # 強制分塊處理所有程式碼內容
            if len(content) > 0:
                # 使用更小的安全塊大小
                max_chunk_size = 1500  # 進一步縮小到 1500 字元
                
                # 將程式碼按行分塊
                content_lines = content.split('\n')
                current_chunk_lines = []
                current_chunk_length = 0
                chunk_number = 1
                
                for line in content_lines:
                    line_length = len(line) + 1  # +1 for newline character
                    
                    # 檢查添加這行是否會超過限制
                    if current_chunk_length + line_length > max_chunk_size and current_chunk_lines:
                        # 創建當前塊
                        chunk_content = '\n'.join(current_chunk_lines)
                        
                        # 添加塊標題（除非是第一個且只有一個塊）
                        if chunk_number > 1 or len(content) > max_chunk_size:
                            blocks.append({
                                "object": "block",
                                "type": "heading_3",
                                "heading_3": {
                                    "rich_text": [{
                                        "type": "text", 
                                        "text": {"content": f"📋 程式碼 (第 {chunk_number} 部分)"}
                                    }]
                                }
                            })
                        
                        # 添加程式碼區塊
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
                        
                        # 開始新的塊
                        current_chunk_lines = [line]
                        current_chunk_length = line_length
                        chunk_number += 1
                    else:
                        current_chunk_lines.append(line)
                        current_chunk_length += line_length
                
                # 添加最後一個塊
                if current_chunk_lines:
                    chunk_content = '\n'.join(current_chunk_lines)
                    
                    # 添加塊標題（如果有多個塊）
                    if chunk_number > 1:
                        blocks.append({
                            "object": "block",
                            "type": "heading_3",
                            "heading_3": {
                                "rich_text": [{
                                    "type": "text", 
                                    "text": {"content": f"📋 程式碼 (第 {chunk_number} 部分，完)"}
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
            
            # 分批添加 blocks 到頁面
            batch_size = 100
            for i in range(0, len(blocks), batch_size):
                batch = blocks[i:i+batch_size]
                self.notion.blocks.children.append(block_id=page_id, children=batch)
            
        except Exception as e:
            print(f"更新頁面內容失敗: {str(e)}")
    
    def sync_project(self, project_path, force_update=False, file_extensions=None):
        """
        同步整個專案
        
        Args:
            project_path: 專案路徑
            force_update: 是否強制更新所有檔案
            file_extensions: 要同步的檔案副檔名清單，None 表示所有支援的類型
        """
        try:
            # 解析專案路徑為絕對路徑
            project_root = Path(project_path).resolve()
            
            # 如果指定了特定副檔名，只掃描那些類型
            source_files = self.scan_source_files(project_root, file_extensions)
            
            if not source_files:
                print("未找到任何符合條件的程式碼檔案")
                return
            
            print(f"\\n開始同步 {len(source_files)} 個檔案...")
            print("=" * 60)
            
            # 按語言分組統計
            language_stats = {}
            success_count = 0
            
            for i, file_path in enumerate(source_files, 1):
                print(f"[{i}/{len(source_files)}] ", end="")
                
                if self.create_or_update_subpage(file_path, project_root, force_update):
                    success_count += 1
                    # 統計語言類型
                    ext = file_path.suffix
                    language = Config.get_language_for_extension(ext)
                    language_stats[language] = language_stats.get(language, 0) + 1
            
            print("=" * 60)
            print(f"✨ 同步完成: {success_count}/{len(source_files)} 個檔案成功同步")
            
            # 顯示語言統計
            if language_stats:
                print("\\n📊 檔案類型統計:")
                for lang, count in sorted(language_stats.items()):
                    print(f"   {lang.title()}: {count} 個檔案")
            
            # 儲存快取
            self._save_sync_cache()
            
        except Exception as e:
            print(f"專案同步失敗: {str(e)}")
    
    def sync_specific_language(self, project_path, language, force_update=False):
        """
        同步特定程式語言的檔案
        
        Args:
            project_path: 專案路徑
            language: 程式語言名稱 (如 'python', 'c#')
            force_update: 是否強制更新
        """
        # 找出對應的檔案副檔名
        extensions = []
        for ext, lang in Config.SUPPORTED_LANGUAGES.items():
            if lang.lower() == language.lower():
                extensions.append(ext)
        
        if not extensions:
            print(f"❌ 不支援的程式語言: {language}")
            print(f"支援的語言: {', '.join(set(Config.SUPPORTED_LANGUAGES.values()))}")
            return
        
        print(f"🎯 同步 {language.title()} 檔案 (副檔名: {', '.join(extensions)})")
        self.sync_project(project_path, force_update, extensions)
    
    def _load_sync_cache(self):
        """載入同步快取"""
        cache_file = Path(Config.CACHE_FILE)
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"載入快取失敗: {str(e)}")
                return {}
        return {}
    
    def _save_sync_cache(self):
        """儲存同步快取"""
        try:
            with open(Config.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.sync_cache, f, indent=2, ensure_ascii=False)
            print(f"💾 快取已儲存到 {Config.CACHE_FILE}")
        except Exception as e:
            print(f"儲存快取失敗: {str(e)}")
    
    def clean_deleted_files(self):
        """清理已刪除檔案的快取記錄"""
        if not self.sync_cache:
            return
        
        to_remove = []
        for file_path in self.sync_cache.keys():
            if not Path(file_path).exists():
                to_remove.append(file_path)
        
        for file_path in to_remove:
            del self.sync_cache[file_path]
            print(f"🗑️  移除已刪除檔案的快取: {file_path}")
        
        if to_remove:
            self._save_sync_cache()
    
    def get_project_stats(self, project_path):
        """取得專案統計資訊"""
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
            
            # 檢查同步狀態
            try:
                relative_path = str(file_path.relative_to(project_root))
            except ValueError:
                relative_path = file_path.name
                
            if relative_path in self.sync_cache:
                stats['synced_files'] += 1
            else:
                stats['unsynced_files'] += 1
        
        return stats