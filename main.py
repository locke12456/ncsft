#!/usr/bin/env python3 
# -*- coding: utf-8 -*-

import argparse
import sys
from pathlib import Path
from config import Config
from notion_sync import NotionSync

def print_banner():
    """Print application banner"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║           Notion Code File Sync Tool v2.0 (Improved)       ║
║                                                              ║
║     Sync code project files to Notion with smart updates    ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def main():
    """Main entry point"""
    print_banner()
    
    # Setup command line argument parser
    parser = argparse.ArgumentParser(
        description='Sync code project files to Notion pages with improved duplicate handling',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  python main.py push /path/to/project                    # Push all files to Notion
  python main.py push /path/to/project -f                 # Force update all files
  python main.py push /path/to/project -l python          # Only sync Python files
  python main.py push /path/to/project -e .py .js         # Only sync specific extensions
  python main.py pull /path/to/project                    # Pull files from Notion
  python main.py pull /path/to/project -f                 # Force overwrite local files
  python main.py pull /path/to/project -o /output         # Pull to specific directory
  python main.py stats /path/to/project                   # Show project statistics
  python main.py clean /path/to/project                   # Clean deleted files from cache

Notes:
  - The tool will automatically look for .env files in the project directory hierarchy
  - Each project can have its own .env configuration
  - Cache files are stored per project directory
  - v2.0 includes improved logic to prevent duplicate pages
        """
    )
    
    # Add subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Push command (sync to Notion)
    push_parser = subparsers.add_parser('push', help='Push files to Notion')
    push_parser.add_argument('path', help='Project directory path')
    push_parser.add_argument('-f', '--force', action='store_true', help='Force update all files')
    push_parser.add_argument('-l', '--language', help='Only sync specific language (e.g., python, javascript)')
    push_parser.add_argument('-e', '--extensions', nargs='+', help='Only sync specific extensions (e.g., .py .js)')
    push_parser.add_argument(
        '--plain-text',
        action='store_true',
        help='Use single code block with plain text chunks (experimental)'
    )
    push_parser.add_argument(
        '-m', '--mode',
        choices=['recreate', 'clear'],
        default='recreate',
        help='Update mode: recreate = delete old page and create new (default); clear = keep old page, clear content and rewrite'
    )
    
    # Pull command (sync from Notion)
    pull_parser = subparsers.add_parser('pull', help='Pull files from Notion')
    pull_parser.add_argument('path', help='Original project directory path')
    pull_parser.add_argument('-o', '--output', help='Output directory (default: {project}_from_notion)')
    pull_parser.add_argument('-f', '--force', action='store_true', help='Force overwrite existing local files')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show project statistics')
    stats_parser.add_argument('path', help='Project directory path')
    
    # Clean command
    clean_parser = subparsers.add_parser('clean', help='Clean deleted files from cache')
    clean_parser.add_argument('path', help='Project directory path')
    
    # Parse arguments
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
    if not Config.validate(project_path):
        print("❌ Configuration validation failed")
        return
    
    # Initialize NotionSync
    try:
        sync = NotionSync()
    except Exception as e:
        print(f"❌ Failed to initialize NotionSync: {str(e)}")
        return
    
    # Execute command
    try:
        if args.command == 'push':
            execute_push_command(sync, args, project_path)
        elif args.command == 'pull':
            execute_pull_command(sync, args, project_path)
        elif args.command == 'stats':
            execute_stats_command(sync, project_path)
        elif args.command == 'clean':
            execute_clean_command(sync, project_path)
            
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
    except Exception as e:
        print(f"❌ Command execution failed: {str(e)}")
        import traceback
        traceback.print_exc()

def execute_push_command(sync, args, project_path):
    """Execute push command"""
    print(f"🚀 Starting push operation for: {project_path}")
    
    if args.language:
        # Sync specific language
        sync.sync_specific_language(
            str(project_path), 
            args.language, 
            force_update=args.force
        )
    elif args.extensions:
        # Sync specific extensions
        print(f"🎯 Syncing files with extensions: {', '.join(args.extensions)}")
        sync.sync_project(
            str(project_path), 
            force_update=args.force, 
            file_extensions=args.extensions,
            use_plain_text=args.plain_text,
            update_mode=args.mode
        )
    else:
        # Sync all supported files
        sync.sync_project(str(project_path), force_update=args.force, use_plain_text=args.plain_text, update_mode=args.mode)

def execute_pull_command(sync, args, project_path):
    """Execute pull command"""
    print(f"📥 Starting pull operation for: {project_path}")
    
    output_dir = args.output if args.output else None
    force_overwrite = getattr(args, 'force', False)
    sync.pull_from_notion(str(project_path), output_dir, force_overwrite)

def execute_stats_command(sync, project_path):
    """Execute stats command"""
    print(f"📊 Gathering statistics for: {project_path}")
    
    try:
        stats = sync.get_project_stats(str(project_path))
        
        print("\n" + "=" * 50)
        print("📊 PROJECT STATISTICS")
        print("=" * 50)
        print(f"📁 Total files: {stats['total_files']}")
        print(f"✅ Synced files: {stats['synced_files']}")
        print(f"❓ Unsynced files: {stats['unsynced_files']}")
        
        if stats['languages']:
            print("\n🔤 Languages breakdown:")
            for lang, count in sorted(stats['languages'].items()):
                print(f"   {lang.title()}: {count} files")
        
        if stats['synced_files'] > 0:
            sync_percentage = (stats['synced_files'] / stats['total_files']) * 100
            print(f"\n📈 Sync completion: {sync_percentage:.1f}%")
            
    except Exception as e:
        print(f"❌ Failed to gather statistics: {str(e)}")

def execute_clean_command(sync, project_path):
    """Execute clean command"""
    print(f"🧹 Cleaning cache for: {project_path}")
    
    try:
        sync.clean_deleted_files(str(project_path))
        print("✅ Cache cleaning completed")
    except Exception as e:
        print(f"❌ Cache cleaning failed: {str(e)}")

if __name__ == "__main__":
    main()