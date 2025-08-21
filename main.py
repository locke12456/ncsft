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
║                    Notion Code File Sync Tool                 ║
║                                                              ║
║     Sync code project files to Notion pages automatically    ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def main():
    """Main entry point"""
    print_banner()
    
    # Setup command line argument parser
    parser = argparse.ArgumentParser(
        description='Sync code project files to Notion pages',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  python main.py                          # Sync current directory
  python main.py -p /path/to/code         # Sync specified directory
  python main.py -e .py .js               # Sync only Python and JavaScript files
  python main.py --force                  # Force update all files
        """
    )
    
    parser.add_argument(
        '--path', '-p',
        type=str,
        default='.',
        help='Path to scan for code files (default: current directory)'
    )
    
    parser.add_argument(
        '--extensions', '-e',
        nargs='*',
        help='Specify file extensions to scan (e.g., .py .cs .js), if not specified, scan all supported types'
    )
    
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force update all files, ignore cache'
    )
    
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Simulate execution without actual upload (Note: not supported in current version)'
    )
    
    parser.add_argument(
        '--stats', '-s',
        action='store_true',
        help='Display sync statistics'
    )
    
    parser.add_argument(
        '--clean', '-c',
        action='store_true',
        help='Clean local cache'
    )
    
    parser.add_argument(
        '--verbose', '-v', 
        action='store_true', 
        help='Display detailed output'
    )
    
    args = parser.parse_args()
    
    try:
        # Check configuration
        if not Config.validate():
            print("❌ Configuration validation failed, please check .env file")
            sys.exit(1)
        
        # Initialize synchronizer
        sync = NotionSync(Config.NOTION_TOKEN, Config.PARENT_PAGE_ID)
        
        if args.verbose:
            print(f"📁 Project path: {args.path}")
            print(f"🎯 Parent page ID: {Config.PARENT_PAGE_ID}")
            if args.extensions:
                print(f"📝 Specified extensions: {args.extensions}")
        
        # Execute corresponding operations
        if args.stats:
            sync.show_stats()
        elif args.clean:
            if sync.clean_cache():
                print("✅ Cache cleaned successfully")
            else:
                print("❌ Cache cleanup failed")
        elif args.dry_run:
            print("⚠️  Dry-run mode is not currently supported, will perform actual sync")
            # Execute sync
            if args.extensions:
                sync.sync_project(args.path, args.force, args.extensions)
            else:
                sync.sync_project(args.path, args.force)
        else:
            # Execute sync
            if args.extensions:
                sync.sync_project(args.path, args.force, args.extensions)
            else:
                sync.sync_project(args.path, args.force)
    
    except KeyboardInterrupt:
        print("\n⚠️  User interrupted operation")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Execution failed: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()