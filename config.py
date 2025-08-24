import os
from dotenv import load_dotenv
from pathlib import Path
import re

class Config:
    """Configuration management class with dynamic .env loading"""
    
    # Default values
    _notion_token = None
    _parent_page_id = None
    _project_root = None
    _max_content_length = 100000
    _cache_file = '.notion_sync_cache.json'
    
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
    def load_env_from_path(cls, path):
        """Load environment variables from specific path"""
        path_obj = Path(path).resolve()
        
        # Try to find .env in the given path or its parents
        current_path = path_obj if path_obj.is_dir() else path_obj.parent
        
        while current_path != current_path.parent:  # Stop at root
            env_file = current_path / '.env'
            if env_file.exists():
                print(f"Loading .env from: {env_file}")
                load_dotenv(env_file)
                
                # Update class variables with loaded values
                cls._notion_token = os.getenv('NOTION_TOKEN')
                cls._parent_page_id = os.getenv('PARENT_PAGE_ID')
                cls._project_root = os.getenv('PROJECT_ROOT', str(current_path))
                cls._max_content_length = int(os.getenv('MAX_CONTENT_LENGTH', '100000'))
                cls._cache_file = os.getenv('CACHE_FILE', str(current_path / '.notion_sync_cache.json'))
                
                return True
            current_path = current_path.parent
        
        # Fallback to main directory .env
        main_env = Path.cwd() / '.env'
        if main_env.exists():
            print(f"Loading .env from main directory: {main_env}")
            load_dotenv(main_env)
            
            cls._notion_token = os.getenv('NOTION_TOKEN')
            cls._parent_page_id = os.getenv('PARENT_PAGE_ID')
            cls._project_root = os.getenv('PROJECT_ROOT', '.')
            cls._max_content_length = int(os.getenv('MAX_CONTENT_LENGTH', '100000'))
            cls._cache_file = os.getenv('CACHE_FILE', '.notion_sync_cache.json')
            
            return True
        
        print("Warning: No .env file found in path hierarchy")
        return False
    
    @classmethod
    @property
    def NOTION_TOKEN(cls):
        return cls._notion_token
    
    @classmethod  
    @property
    def PARENT_PAGE_ID(cls):
        return cls._parent_page_id
    
    @classmethod
    @property
    def PROJECT_ROOT(cls):
        return cls._project_root
    
    @classmethod
    @property
    def MAX_CONTENT_LENGTH(cls):
        return cls._max_content_length
    
    @classmethod
    @property
    def CACHE_FILE(cls):
        return cls._cache_file
    
    @classmethod
    def validate(cls, project_path=None):
        """Validate configuration, optionally loading from specific path"""
        if project_path:
            cls.load_env_from_path(project_path)
        else:
            # Load from current directory if not already loaded
            if not cls._notion_token:
                cls.load_env_from_path(Path.cwd())
        
        if not cls._notion_token:
            print("❌ NOTION_TOKEN not found in environment variables")
            print("Please set NOTION_TOKEN in .env file")
            return False
        
        if not cls._parent_page_id:
            print("❌ PARENT_PAGE_ID not found in environment variables")
            print("Please set PARENT_PAGE_ID in .env file")
            return False
        
        # Normalize page ID format
        cls._parent_page_id = cls.normalize_page_id(cls._parent_page_id)
        
        if not cls._is_valid_page_id(cls._parent_page_id):
            print("❌ PARENT_PAGE_ID format is invalid")
            print("Expected format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx (UUID format)")
            print(f"❌ Invalid: {cls._parent_page_id}")
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
                if pattern.startswith('*'):
                    # Wildcard pattern
                    if part.endswith(pattern[1:]):
                        return True
                else:
                    # Direct match
                    if part == pattern:
                        return True
        
        # Check the full path for patterns
        for pattern in cls.IGNORE_PATTERNS:
            if pattern in path_str:
                return True
        
        return False
    
    @classmethod
    def get_cache_path(cls, project_path=None):
        """Get cache file path for specific project"""
        if project_path:
            return Path(project_path) / '.notion_sync_cache.json'
        return Path(cls._cache_file or '.notion_sync_cache.json')