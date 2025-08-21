import os
from dotenv import load_dotenv
from pathlib import Path
import re

# Load environment variables
load_dotenv()

class Config:
    """Configuration management class"""
    
    # Notion API configuration
    NOTION_TOKEN = os.getenv('NOTION_TOKEN')
    PARENT_PAGE_ID = os.getenv('PARENT_PAGE_ID')
    
    # Project configuration
    PROJECT_ROOT = os.getenv('PROJECT_ROOT', '.')
    
    # Optional configuration - can be overridden via environment variables
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', '100000'))
    CACHE_FILE = os.getenv('CACHE_FILE', '.notion_sync_cache.json')
    
    # Supported programming languages and their extensions
    SUPPORTED_LANGUAGES = {
        '.py': 'python',
        '.cs': 'c#',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.java': 'java',
        '.cpp': 'c++',
        '.c': 'c',
        '.php': 'php',
        '.rb': 'ruby',
        '.go': 'go',
        '.rs': 'rust',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.html': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.sass': 'sass',
        '.less': 'less',
        '.xml': 'xml',
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.sql': 'sql',
        '.sh': 'shell',
        '.bash': 'bash',
        '.ps1': 'powershell',
        '.bat': 'batch',
        '.cmd': 'batch',
        '.r': 'r',
        '.m': 'matlab',
        '.pl': 'perl',
        '.lua': 'lua',
        '.dart': 'dart',
        '.vue': 'vue',
        '.jsx': 'javascript',
        '.tsx': 'typescript',
    }
    
    # File and directory patterns to ignore
    IGNORE_PATTERNS = [
        # Version control
        '.git', '.svn', '.hg',
        # Dependencies
        'node_modules', '__pycache__', '.venv', 'venv', 'env',
        # Build outputs
        'build', 'dist', 'target', 'bin', 'obj',
        # IDE files
        '.vscode', '.idea', '*.suo', '*.user',
        # Temporary files
        '*.tmp', '*.temp', '*.log',
        # OS files
        '.DS_Store', 'Thumbs.db',
        # Package files
        '*.min.js', '*.min.css',
    ]
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        if not cls.NOTION_TOKEN:
            print("❌ NOTION_TOKEN not found in environment variables")
            print("Please set NOTION_TOKEN in .env file")
            return False
        
        if not cls.PARENT_PAGE_ID:
            print("❌ PARENT_PAGE_ID not found in environment variables")
            print("Please set PARENT_PAGE_ID in .env file")
            return False
        
        # Normalize page ID format
        cls.PARENT_PAGE_ID = cls.normalize_page_id(cls.PARENT_PAGE_ID)
        
        if not cls._is_valid_page_id(cls.PARENT_PAGE_ID):
            print("❌ PARENT_PAGE_ID format is invalid")
            print("Expected format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx (UUID format)")
            print(f"❌ Invalid: {cls.PARENT_PAGE_ID}")
            return False
        
        print("✅ Configuration validation successful")
        return True
    
    @classmethod
    def normalize_page_id(cls, page_id):
        """Normalize page ID to standard UUID format"""
        if not page_id:
            return page_id
        
        # Remove possible prefixes (like "Projects-")
        if '-' in page_id and len(page_id) > 36:
            # Check if it's in format "prefix-uuid"
            parts = page_id.split('-', 1)
            if len(parts) == 2 and len(parts[1]) == 32:  # 32 hex characters
                page_id = parts[1]
        
        # Remove all hyphens first
        clean_id = page_id.replace('-', '')
        
        # Check if it's 32 hex characters
        if len(clean_id) == 32 and all(c in '0123456789abcdefABCDEF' for c in clean_id):
            # Insert hyphens in UUID format: 8-4-4-4-12
            return f"{clean_id[:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:]}"
        
        return page_id
    
    @classmethod
    def _is_valid_page_id(cls, page_id):
        """Check if page ID is valid UUID format"""
        uuid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
        return bool(re.match(uuid_pattern, page_id))
    
    @classmethod
    def get_supported_extensions(cls):
        """Get list of all supported file extensions"""
        return list(cls.SUPPORTED_LANGUAGES.keys())
    
    @classmethod
    def get_language_for_extension(cls, extension):
        """Get programming language for file extension"""
        return cls.SUPPORTED_LANGUAGES.get(extension.lower(), 'text')
    
    @classmethod
    def should_ignore_path(cls, path):
        """Check if path should be ignored based on ignore patterns"""
        path_str = str(path).lower()
        path_obj = Path(path)
        
        # Check each part of the path
        for part in path_obj.parts:
            for pattern in cls.IGNORE_PATTERNS:
                # Handle wildcard patterns
                if '*' in pattern:
                    if pattern.startswith('*.'):
                        # File extension pattern
                        if part.endswith(pattern[1:]):
                            return True
                    else:
                        # Other wildcard patterns
                        import fnmatch
                        if fnmatch.fnmatch(part.lower(), pattern.lower()):
                            return True
                else:
                    # Exact match
                    if part.lower() == pattern.lower():
                        return True
        
        return False
    
    @classmethod
    def get_ignore_patterns(cls):
        """Get complete list of ignore patterns"""
        return cls.IGNORE_PATTERNS.copy()