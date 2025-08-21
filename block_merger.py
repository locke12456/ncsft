import json
from notion_client import Client
from config import Config

class BlockMerger:
    """Notion 程式碼區塊合併工具（智能分段版本）"""
    
    def __init__(self, notion_token):
        self.notion = Client(auth=notion_token)
        self.MAX_CHUNK_SIZE = 1800  # 安全的字元限制（留一些緩衝）
    
    def merge_code_blocks_in_page(self, page_id):
        """
        合併頁面中連續的程式碼區塊（智能分段）
        
        Args:
            page_id: 頁面 ID
            
        Returns:
            bool: 是否成功合併
        """
        try:
            # 獲取頁面所有區塊
            blocks = self._get_all_blocks(page_id)
            
            # 找出程式碼區塊群組
            code_block_groups = self._find_code_block_groups(blocks)
            
            if not code_block_groups:
                print("未找到可合併的程式碼區塊")
                return False
            
            # 合併每個群組
            merged_count = 0
            for group in code_block_groups:
                if len(group['blocks']) > 1:  # 只合併有多個區塊的群組
                    if self._merge_block_group_smart(page_id, group):
                        merged_count += 1
            
            print(f"✅ 成功合併 {merged_count} 個程式碼區塊群組")
            return merged_count > 0
            
        except Exception as e:
            print(f"❌ 合併失敗: {str(e)}")
            return False
    
    def _get_all_blocks(self, page_id):
        """獲取頁面所有區塊"""
        blocks = []
        has_more = True
        start_cursor = None
        
        while has_more:
            response = self.notion.blocks.children.list(
                block_id=page_id,
                start_cursor=start_cursor,
                page_size=100
            )
            
            blocks.extend(response['results'])
            has_more = response['has_more']
            start_cursor = response.get('next_cursor')
        
        return blocks
    
    def _find_code_block_groups(self, blocks):
        """找出連續的程式碼區塊群組"""
        groups = []
        current_group = None
        
        for i, block in enumerate(blocks):
            if block['type'] == 'code':
                if current_group is None:
                    # 開始新的群組
                    current_group = {
                        'start_index': i,
                        'blocks': [block],
                        'language': block['code'].get('language', 'text')
                    }
                elif block['code'].get('language') == current_group['language']:
                    # 延續當前群組（相同語言）
                    current_group['blocks'].append(block)
                else:
                    # 語言不同，結束當前群組，開始新群組
                    if len(current_group['blocks']) > 1:
                        groups.append(current_group)
                    
                    current_group = {
                        'start_index': i,
                        'blocks': [block],
                        'language': block['code'].get('language', 'text')
                    }
            elif block['type'] == 'heading_3' and block['heading_3']['rich_text']:
                # 檢查是否是程式碼分段標題
                title = block['heading_3']['rich_text'][0]['text']['content']
                if '程式碼' in title and ('部分' in title or '第' in title):
                    # 這是程式碼分段標題，跳過（稍後會被刪除）
                    continue
                else:
                    # 其他標題，中斷程式碼群組
                    if current_group and len(current_group['blocks']) > 1:
                        groups.append(current_group)
                    current_group = None
            else:
                # 非程式碼區塊，結束當前群組
                if current_group and len(current_group['blocks']) > 1:
                    groups.append(current_group)
                current_group = None
        
        # 處理最後一個群組
        if current_group and len(current_group['blocks']) > 1:
            groups.append(current_group)
        
        return groups
    
    def _merge_block_group_smart(self, page_id, group):
        """智能合併程式碼區塊群組（處理 2000 字元限制）"""
        try:
            # 收集所有程式碼內容
            all_content = []
            blocks_to_delete = []
            
            for block in group['blocks']:
                # 提取程式碼內容
                if block['code']['rich_text']:
                    content = block['code']['rich_text'][0]['text']['content']
                    all_content.append(content)
                
                blocks_to_delete.append(block['id'])
            
            # 合併內容
            merged_content = '\n'.join(all_content)
            
            print(f"🔄 智能合併 {len(group['blocks'])} 個程式碼區塊 ({len(merged_content)} 字元)")
            
            # 如果內容小於限制，直接合併
            if len(merged_content) <= self.MAX_CHUNK_SIZE:
                return self._create_single_block(page_id, group, merged_content, blocks_to_delete)
            
            # 內容過大，需要智能分段
            return self._create_chunked_blocks(page_id, group, merged_content, blocks_to_delete)
            
        except Exception as e:
            print(f"❌ 智能合併群組失敗: {str(e)}")
            return False
    
    def _create_single_block(self, page_id, group, content, blocks_to_delete):
        """創建單個程式碼區塊"""
        try:
            first_block = group['blocks'][0]
            
            # 創建新的合併程式碼區塊
            new_block = {
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": content}
                    }],
                    "language": group['language']
                }
            }
            
            # 獲取插入位置
            previous_block_id = self._get_previous_block_id(page_id, first_block['id'])
            
            # 插入新區塊
            if previous_block_id:
                self.notion.blocks.children.append(
                    block_id=page_id,
                    children=[new_block],
                    after=previous_block_id
                )
            else:
                self.notion.blocks.children.append(
                    block_id=page_id,
                    children=[new_block]
                )
            
            # 刪除原始區塊和相關的分段標題
            self._delete_related_blocks(page_id, group)
            
            print(f"✅ 成功創建單個合併區塊")
            return True
            
        except Exception as e:
            print(f"❌ 創建單個區塊失敗: {str(e)}")
            return False
    
    def _create_chunked_blocks(self, page_id, group, merged_content, blocks_to_delete):
        """創建分段的程式碼區塊（優化版本）"""
        try:
            # 將內容按行分割
            lines = merged_content.split('\n')
            chunks = []
            current_chunk = []
            current_size = 0
            
            for line in lines:
                line_size = len(line) + 1  # +1 for newline
                
                # 如果當前區塊加上這行會超過限制
                if current_size + line_size > self.MAX_CHUNK_SIZE and current_chunk:
                    # 保存當前區塊
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = [line]
                    current_size = line_size
                else:
                    # 添加到當前區塊
                    current_chunk.append(line)
                    current_size += line_size
            
            # 添加最後一個區塊
            if current_chunk:
                chunks.append('\n'.join(current_chunk))
            
            # 如果分段後只有一個區塊，說明單行就超過了限制，需要強制截斷
            if len(chunks) == 1 and len(chunks[0]) > self.MAX_CHUNK_SIZE:
                print(f"⚠️  內容過大，進行強制截斷")
                content = chunks[0][:self.MAX_CHUNK_SIZE-50] + "\n\n... (內容過長，已截斷)"
                chunks = [content]
            
            print(f"📚 將內容分為 {len(chunks)} 個區塊")
            
            # 創建新的區塊組
            first_block = group['blocks'][0]
            previous_block_id = self._get_previous_block_id(page_id, first_block['id'])
            
            new_blocks = []
            for i, chunk in enumerate(chunks):
                # 添加標題區塊（除了第一個）
                if i > 0:
                    title_block = {
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [{
                                "type": "text",
                                "text": {"content": f"（續第 {i+1} 部分）"}
                            }]
                        }
                    }
                    new_blocks.append(title_block)
                
                # 添加程式碼區塊
                code_block = {
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": chunk}
                        }],
                        "language": group['language']
                    }
                }
                new_blocks.append(code_block)
            
            # 批次插入新區塊
            if previous_block_id:
                self.notion.blocks.children.append(
                    block_id=page_id,
                    children=new_blocks,
                    after=previous_block_id
                )
            else:
                self.notion.blocks.children.append(
                    block_id=page_id,
                    children=new_blocks
                )
            
            # 刪除原始區塊和相關的分段標題
            self._delete_related_blocks(page_id, group)
            
            print(f"✅ 成功創建 {len(chunks)} 個優化分段區塊")
            return True
            
        except Exception as e:
            print(f"❌ 創建分段區塊失敗: {str(e)}")
            return False
    
    def _get_previous_block_id(self, page_id, target_block_id):
        """獲取目標區塊的前一個區塊ID"""
        blocks = self._get_all_blocks(page_id)
        
        for i, block in enumerate(blocks):
            if block['id'] == target_block_id:
                if i > 0:
                    return blocks[i-1]['id']
                else:
                    return None  # 第一個區塊
        return None
    
    def _delete_related_blocks(self, page_id, group):
        """刪除相關的區塊（程式碼區塊和分段標題）"""
        all_blocks = self._get_all_blocks(page_id)
        blocks_to_delete = []
        
        # 添加程式碼區塊
        for block in group['blocks']:
            blocks_to_delete.append(block['id'])
        
        # 查找並添加相關的分段標題
        for i, block in enumerate(all_blocks):
            if (block['type'] == 'heading_3' and 
                block['heading_3']['rich_text'] and
                block['id'] not in blocks_to_delete):
                
                title = block['heading_3']['rich_text'][0]['text']['content']
                if '程式碼' in title and ('部分' in title or '第' in title):
                    # 檢查這個標題是否在我們要刪除的程式碼區塊附近
                    if self._is_title_related_to_group(all_blocks, i, group):
                        blocks_to_delete.append(block['id'])
        
        # 刪除所有相關區塊
        for block_id in blocks_to_delete:
            try:
                self.notion.blocks.delete(block_id=block_id)
            except:
                pass  # 忽略刪除失敗的區塊
    
    def _is_title_related_to_group(self, all_blocks, title_index, group):
        """檢查標題是否與程式碼群組相關"""
        group_block_ids = {block['id'] for block in group['blocks']}
        
        # 檢查標題後面幾個區塊是否屬於這個群組
        for i in range(title_index + 1, min(title_index + 3, len(all_blocks))):
            if all_blocks[i]['id'] in group_block_ids:
                return True
        
        return False
    
    def merge_all_pages_under_parent(self, parent_page_id):
        """合併父頁面下所有子頁面的程式碼區塊"""
        try:
            # 獲取父頁面下的所有子頁面
            children = self.notion.blocks.children.list(block_id=parent_page_id)
            
            merged_pages = 0
            for child in children['results']:
                if child['type'] == 'child_page':
                    page_id = child['id']
                    page_title = child['child_page']['title']
                    
                    print(f"🔍 處理頁面: {page_title}")
                    
                    if self.merge_code_blocks_in_page(page_id):
                        merged_pages += 1
            
            print(f"\n✨ 完成！成功處理 {merged_pages} 個頁面")
            return merged_pages > 0
            
        except Exception as e:
            print(f"❌ 批次合併失敗: {str(e)}")
            return False

# 使用範例
if __name__ == "__main__":
    merger = BlockMerger(Config.NOTION_TOKEN)
    
    # 合併特定頁面
    # merger.merge_code_blocks_in_page("your-page-id")
    
    # 合併父頁面下所有子頁面
    # merger.merge_all_pages_under_parent(Config.PARENT_PAGE_ID)