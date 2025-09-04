#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import argparse
from pathlib import Path
from notion_client import Client
from config import Config

class NotionCleanupTool:
    """Tool for cleaning up duplicate Notion pages - PATH-AWARE VERSION"""
    
    def __init__(self, notion_token=None):
        """Initialize cleanup tool"""
        self.notion_token = notion_token or Config.NOTION_TOKEN
        self.notion = Client(auth=self.notion_token)
    
    def find_true_duplicates_with_path_check(self, parent_page_id, project_path=None):
        """
        Find TRUE duplicate pages by checking both title AND file path
        
        Args:
            parent_page_id: Parent page ID to search under
            project_path: Optional project path for cache comparison
            
        Returns:
            list: List of TRUE duplicate page groups (same title AND same path)
        """
        try:
            children = self.notion.blocks.children.list(block_id=parent_page_id)
            
            # Group pages by title AND extracted file path
            page_groups = {}
            
            print("🔍 Analyzing pages and extracting file paths...")
            
            for child in children['results']:
                if child['type'] == 'child_page':
                    page_title = child['child_page']['title']
                    page_id = child['id']
                    
                    # Get page content to extract the actual file path
                    try:
                        page_details = self.notion.pages.retrieve(page_id=page_id)
                        file_path = self._extract_file_path_from_page(page_id)
                        
                        if file_path:
                            # Create unique key: filename + path
                            unique_key = f"{page_title}::{file_path}"
                            
                            if unique_key not in page_groups:
                                page_groups[unique_key] = []
                            
                            page_groups[unique_key].append({
                                'id': page_id,
                                'title': page_title,
                                'file_path': file_path,
                                'created_time': page_details.get('created_time', ''),
                                'last_edited_time': page_details.get('last_edited_time', ''),
                                'archived': page_details.get('archived', False)
                            })
                            
                            print(f"   📄 {page_title} -> {file_path}")
                        else:
                            print(f"   ⚠️ Could not extract path from: {page_title}")
                            
                    except Exception as e:
                        print(f"   ❌ Error processing page {page_title}: {str(e)}")
            
            # Find TRUE duplicates (same filename AND same path)
            true_duplicates = []
            for unique_key, pages in page_groups.items():
                if len(pages) > 1:
                    # Filter out archived pages
                    active_pages = [p for p in pages if not p.get('archived', False)]
                    
                    if len(active_pages) > 1:
                        page_title = active_pages[0]['title']
                        file_path = active_pages[0]['file_path']
                        
                        print(f"🚨 TRUE DUPLICATE found:")
                        print(f"   File: {page_title}")
                        print(f"   Path: {file_path}")
                        print(f"   Duplicates: {len(active_pages)} copies")
                        
                        # Sort by creation time (keep newest)
                        active_pages.sort(key=lambda x: x.get('created_time', ''), reverse=True)
                        
                        true_duplicates.append({
                            'base_title': page_title,
                            'file_path': file_path,
                            'pages': active_pages,
                            'duplicate_count': len(active_pages) - 1
                        })
            
            return true_duplicates
            
        except Exception as e:
            print(f"❌ Error finding true duplicates: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def _extract_file_path_from_page(self, page_id):
        """
        Extract the actual file path from page content
        
        Args:
            page_id: Page ID
            
        Returns:
            str|None: File path or None if not found
        """
        try:
            # Get page content blocks
            blocks = self.notion.blocks.children.list(block_id=page_id)
            
            for block in blocks['results']:
                if block['type'] == 'paragraph':
                    # Look for the path information in paragraph blocks
                    paragraph = block['paragraph']
                    if paragraph.get('rich_text'):
                        for text_obj in paragraph['rich_text']:
                            content = text_obj.get('text', {}).get('content', '')
                            
                            # Look for path pattern: "📁 Path: C:\\..."
                            if '📁 Path:' in content or '📁 路徑:' in content:
                                # Extract path after the colon
                                path_start = content.find(':') + 1
                                path_line = content[path_start:].split('\\n')[0].strip()
                                
                                if path_line:
                                    return path_line
                                    
                            # Also check for plain path patterns
                            elif 'C:\\\\' in content or '/home/' in content or '/Users/' in content:
                                lines = content.split('\\n')
                                for line in lines:
                                    line = line.strip()
                                    if ('C:\\\\' in line or '/home/' in line or '/Users/' in line) and len(line) > 10:
                                        return line
            
            return None
            
        except Exception as e:
            print(f"❌ Error extracting path from page {page_id}: {str(e)}")
            return None
    
    def find_same_name_different_path_files(self, parent_page_id):
        """
        Find files with same name but different paths (these should NOT be considered duplicates)
        
        Returns:
            dict: Dictionary of filename -> list of different paths
        """
        try:
            children = self.notion.blocks.children.list(block_id=parent_page_id)
            
            filename_to_paths = {}
            
            for child in children['results']:
                if child['type'] == 'child_page':
                    page_title = child['child_page']['title']
                    page_id = child['id']
                    
                    file_path = self._extract_file_path_from_page(page_id)
                    
                    if file_path:
                        if page_title not in filename_to_paths:
                            filename_to_paths[page_title] = set()
                        filename_to_paths[page_title].add(file_path)
            
            # Filter to only show files with same name but different paths
            different_path_files = {}
            for filename, paths in filename_to_paths.items():
                if len(paths) > 1:
                    different_path_files[filename] = list(paths)
            
            return different_path_files
            
        except Exception as e:
            print(f"❌ Error finding same-name different-path files: {str(e)}")
            return {}
    
    def cleanup_duplicates_path_aware(self, duplicates, dry_run=False):
        """
        PATH-AWARE cleanup: Only remove pages with identical filename AND path
        
        Args:
            duplicates: List of TRUE duplicate groups (same name AND same path)
            dry_run: If True, only show what would be cleaned
            
        Returns:
            int: Number of pages cleaned
        """
        cleaned_count = 0
        
        if not duplicates:
            print("✅ No TRUE duplicates found to clean")
            return 0
        
        print(f"🔍 Found {len(duplicates)} TRUE duplicate groups (same name AND same path)")
        print(f"{'🔍 DRY RUN MODE - No actual changes will be made' if dry_run else '🗑️ CLEANUP MODE - Pages will be archived'}")
        print("=" * 80)
        
        for group in duplicates:
            filename = group['base_title']
            file_path = group['file_path']
            pages = group['pages']
            
            print(f"\\n📄 File: {filename}")
            print(f"📂 Path: {file_path}")
            print(f"🔢 Copies: {len(pages)} identical versions")
            
            # Show all versions with timestamps
            for i, page in enumerate(pages):
                status = "📌 KEEP (newest)" if i == 0 else f"🗑️ REMOVE (#{i+1})"
                created = page.get('created_time', 'Unknown')[:19]  # Truncate timestamp
                edited = page.get('last_edited_time', 'Unknown')[:19]
                print(f"     {status}")
                print(f"        ID: {page['id']}")
                print(f"        Created: {created}")
                print(f"        Edited: {edited}")
            
            # Remove duplicates (keep the first one - newest)
            pages_to_remove = pages[1:]
            
            for i, page in enumerate(pages_to_remove, 2):
                if dry_run:
                    print(f"   🔍 [DRY RUN] Would archive copy #{i}: {page['title']}")
                    cleaned_count += 1
                else:
                    try:
                        result = self.notion.pages.update(
                            page_id=page['id'],
                            archived=True
                        )
                        print(f"   ✅ Archived copy #{i}: {page['title']}")
                        cleaned_count += 1
                    except Exception as e:
                        print(f"   ❌ Failed to archive copy #{i}: {str(e)}")
        
        return cleaned_count
    
    def cleanup_project_duplicates(self, project_path, dry_run=False):
        """
        PATH-AWARE cleanup for a specific project
        
        Args:
            project_path: Project directory path
            dry_run: If True, only show what would be cleaned
            
        Returns:
            int: Number of pages cleaned
        """
        try:
            # Load configuration
            Config.load_env_from_path(project_path)
            parent_page_id = Config.PARENT_PAGE_ID
            
            if not parent_page_id:
                print("❌ No parent page ID found in configuration")
                return 0
            
            print(f"🔍 PATH-AWARE scanning for project: {project_path}")
            print(f"📂 Parent page ID: {parent_page_id}")
            print("\\n🎯 Step 1: Finding same-name but different-path files (these will be PRESERVED)...")
            
            # First, show files with same name but different paths
            different_path_files = self.find_same_name_different_path_files(parent_page_id)
            
            if different_path_files:
                print(f"✅ Found {len(different_path_files)} filenames with legitimate different paths:")
                for filename, paths in different_path_files.items():
                    print(f"   📄 {filename}:")
                    for path in sorted(paths):
                        print(f"      📂 {path}")
                print("   ➡️ These will be PRESERVED (not treated as duplicates)")
            else:
                print("   ✅ No same-name different-path files found")
            
            print("\\n🎯 Step 2: Finding TRUE duplicates (same name AND same path)...")
            
            # Find TRUE duplicates (same name AND same path)
            true_duplicates = self.find_true_duplicates_with_path_check(parent_page_id, project_path)
            
            if not true_duplicates:
                print("✅ No TRUE duplicate pages found")
                return 0
            
            print(f"⚠️ Found {len(true_duplicates)} TRUE duplicate groups")
            total_duplicates = sum(group['duplicate_count'] for group in true_duplicates)
            print(f"📊 Total TRUE duplicate pages to clean: {total_duplicates}")
            
            return self.cleanup_duplicates_path_aware(true_duplicates, dry_run)
            
        except Exception as e:
            print(f"❌ Cleanup operation failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return 0

def main():
    """Main entry point for cleanup tool"""
    parser = argparse.ArgumentParser(
        description='PATH-AWARE cleanup of duplicate Notion pages',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  python cleanup_tool.py scan /path/to/project              # Find TRUE duplicates (dry run)
  python cleanup_tool.py clean /path/to/project             # Clean TRUE duplicates only
  python cleanup_tool.py clean /path/to/project --dry-run   # Show what would be cleaned

IMPORTANT NOTES:
  - Only files with IDENTICAL filename AND IDENTICAL file path will be considered duplicates
  - Files with same name but different paths will be PRESERVED
  - Example: src/utils.py and test/utils.py are DIFFERENT files, not duplicates
  - Only TRUE duplicates (same content uploaded multiple times) will be removed
  - The newest version of TRUE duplicates will be kept
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Find TRUE duplicates (path-aware dry run)')
    scan_parser.add_argument('path', help='Project directory path')
    
    # Clean command  
    clean_parser = subparsers.add_parser('clean', help='Clean up TRUE duplicates only')
    clean_parser.add_argument('path', help='Project directory path')
    clean_parser.add_argument('--dry-run', action='store_true', 
                             help='Show what would be cleaned without actually doing it')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Convert path to absolute path
    project_path = Path(args.path).resolve()
    
    if not project_path.exists():
        print(f"❌ Error: Path does not exist: {args.path}")
        return
    
    # Validate configuration for the specific project
    try:
        if not Config.validate(project_path):
            print("❌ Configuration validation failed")
            return
    except Exception as e:
        print(f"❌ Configuration error: {str(e)}")
        return
    
    # Initialize cleanup tool
    try:
        cleanup_tool = NotionCleanupTool()
    except Exception as e:
        print(f"❌ Failed to initialize cleanup tool: {str(e)}")
        return
    
    try:
        if args.command == 'scan':
            print("🔍 PATH-AWARE SCAN MODE - Finding TRUE duplicates only...")
            cleaned_count = cleanup_tool.cleanup_project_duplicates(str(project_path), dry_run=True)
            if cleaned_count > 0:
                print(f"\\n💡 Run 'python cleanup_tool.py clean {args.path}' to actually clean {cleaned_count} TRUE duplicate pages")
            else:
                print("\\n✅ No TRUE duplicates found")
            
        elif args.command == 'clean':
            dry_run = getattr(args, 'dry_run', False)
            if dry_run:
                print("🔍 PATH-AWARE DRY RUN MODE...")
            else:
                print("🗑️ PATH-AWARE CLEANUP MODE - Only removing TRUE duplicates...")
            
            cleaned_count = cleanup_tool.cleanup_project_duplicates(str(project_path), dry_run=dry_run)
            
            if dry_run:
                if cleaned_count > 0:
                    print(f"\\n💡 Run without --dry-run to actually clean {cleaned_count} TRUE duplicate pages")
                else:
                    print("\\n✅ No TRUE duplicates found")
            else:
                if cleaned_count > 0:
                    print(f"\\n✨ PATH-AWARE cleanup completed: {cleaned_count} TRUE duplicate pages archived")
                    print("🎯 Files with same name but different paths were PRESERVED")
                else:
                    print("\\n✅ No TRUE duplicates found to clean")
        
    except KeyboardInterrupt:
        print("\\n⚠️ Operation cancelled by user")
    except Exception as e:
        print(f"❌ Cleanup operation failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()