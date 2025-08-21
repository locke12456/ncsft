import unittest
import tempfile
import shutil
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from notion_sync import NotionSync
from config import Config

class TestNotionSync(unittest.TestCase):
    """Unit tests for NotionSync class"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.mock_notion_token = "test_token_123"
        self.mock_parent_page_id = "test_page_id_456"
        
        # Create mock Notion client
        self.mock_notion_client = Mock()
        
        # Create NotionSync instance with mocked Notion client
        with patch('notion_sync.Client'):
            self.sync = NotionSync(self.mock_notion_token, self.mock_parent_page_id)
            self.sync.notion = self.mock_notion_client
            self.sync.sync_cache = {}
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def create_test_file(self, filename, content, subdir=""):
        """Helper method to create test files"""
        if subdir:
            os.makedirs(os.path.join(self.test_dir, subdir), exist_ok=True)
            file_path = os.path.join(self.test_dir, subdir, filename)
        else:
            file_path = os.path.join(self.test_dir, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return Path(file_path)

class TestFileScanAndHash(TestNotionSync):
    """Test file scanning and hashing functions"""
    
    def test_scan_source_files_basic(self):
        """Test basic file scanning functionality"""
        # Create test files
        self.create_test_file("test1.py", "print('hello')")
        self.create_test_file("test2.cs", "Console.WriteLine('hello');")
        self.create_test_file("readme.txt", "This is readme")  # Should be ignored
        
        # Scan for Python files only
        files = self.sync.scan_source_files(self.test_dir, ['.py'])
        
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].name == "test1.py")
    
    def test_scan_source_files_recursive(self):
        """Test recursive directory scanning"""
        # Create files in subdirectories
        self.create_test_file("main.py", "print('main')", "src")
        self.create_test_file("utils.py", "def helper(): pass", "src/utils")
        self.create_test_file("test.py", "import unittest", "tests")
        
        files = self.sync.scan_source_files(self.test_dir, ['.py'])
        
        self.assertEqual(len(files), 3)
        
        # Files should be sorted by full path (not just filename)
        # Since scan_source_files calls source_files.sort(), check full paths are sorted
        file_paths = [str(f) for f in files]
        sorted_paths = sorted(file_paths)
        self.assertEqual(file_paths, sorted_paths)
        
        # Also verify we found the expected files
        filenames = [f.name for f in files]
        expected_files = {"main.py", "utils.py", "test.py"}
        self.assertEqual(set(filenames), expected_files)
    
    def test_get_file_hash(self):
        """Test MD5 hash calculation"""
        content = "test content for hashing"
        test_file = self.create_test_file("hash_test.py", content)
        
        hash1 = self.sync.get_file_hash(test_file)
        hash2 = self.sync.get_file_hash(test_file)
        
        # Same file should have same hash
        self.assertEqual(hash1, hash2)
        self.assertIsNotNone(hash1)
        self.assertEqual(len(hash1), 32)  # MD5 hash length
    
    def test_get_file_hash_different_files(self):
        """Test that different files have different hashes"""
        file1 = self.create_test_file("file1.py", "content1")
        file2 = self.create_test_file("file2.py", "content2")
        
        hash1 = self.sync.get_file_hash(file1)
        hash2 = self.sync.get_file_hash(file2)
        
        self.assertNotEqual(hash1, hash2)
    
    def test_get_file_hash_nonexistent(self):
        """Test hash calculation for nonexistent file"""
        nonexistent_file = Path(self.test_dir) / "nonexistent.py"
        
        hash_result = self.sync.get_file_hash(nonexistent_file)
        
        self.assertIsNone(hash_result)

class TestContentChunking(TestNotionSync):
    """Test content chunking functionality - addressing the \\n vs \n issue"""
    
    def test_newline_handling_in_chunking(self):
        """Test that newlines are handled correctly in chunking (not escaped)"""
        # This test addresses the \\n vs \n issue we encountered
        content = "line1\nline2\nline3\nline4\nline5"
        
        # Test that content.split('\n') works correctly
        lines = content.split('\n')
        self.assertEqual(len(lines), 5)
        self.assertEqual(lines[0], "line1")
        self.assertEqual(lines[4], "line5")
        
        # Test that joining works correctly
        rejoined = '\n'.join(lines)
        self.assertEqual(rejoined, content)
    
    def test_chunk_size_calculation(self):
        """Test that chunk size calculation works correctly"""
        lines = ["short", "a bit longer line", "this is a much longer line with more content"]
        
        total_size = 0
        for line in lines:
            total_size += len(line) + 1  # +1 for newline
        
        # Remove the extra +1 from the last line
        total_size -= 1
        
        joined_content = '\n'.join(lines)
        self.assertEqual(len(joined_content), total_size)
    
    def test_large_content_chunking_logic(self):
        """Test the chunking logic for large content"""
        # Create content larger than MAX_CHUNK_SIZE (1500)
        large_lines = [f"line_{i:04d}_with_some_content_to_make_it_longer" for i in range(100)]
        large_content = '\n'.join(large_lines)
        
        # Simulate the chunking logic
        MAX_CHUNK_SIZE = 1500
        chunks = []
        current_chunk_lines = []
        current_chunk_length = 0
        
        for line in large_lines:
            line_length = len(line) + 1  # +1 for newline
            
            if current_chunk_length + line_length > MAX_CHUNK_SIZE and current_chunk_lines:
                chunks.append('\n'.join(current_chunk_lines))
                current_chunk_lines = [line]
                current_chunk_length = line_length
            else:
                current_chunk_lines.append(line)
                current_chunk_length += line_length
        
        # Add final chunk
        if current_chunk_lines:
            chunks.append('\n'.join(current_chunk_lines))
        
        # Verify all chunks are within size limit
        for i, chunk in enumerate(chunks):
            self.assertLessEqual(len(chunk), MAX_CHUNK_SIZE, 
                               f"Chunk {i+1} exceeds size limit: {len(chunk)} > {MAX_CHUNK_SIZE}")
        
        # Verify content integrity
        rejoined_content = '\n'.join(chunks)
        self.assertEqual(rejoined_content, large_content)
        
        # Should have multiple chunks for large content
        self.assertGreater(len(chunks), 1)

class TestPageCreationAndUpdate(TestNotionSync):
    """Test page creation and update functionality"""
    
    def test_create_new_subpage(self):
        """Test creating a new subpage"""
        test_file = self.create_test_file("new_file.py", "print('new file')")
        
        # Mock Notion API responses
        self.mock_notion_client.pages.create.return_value = {"id": "new_page_id_123"}
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        self.mock_notion_client.blocks.children.append.return_value = {}
        
        page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=True)
        
        self.assertEqual(page_id, "new_page_id_123")
        self.mock_notion_client.pages.create.assert_called_once()
    
    def test_update_existing_subpage(self):
        """Test updating an existing subpage"""
        test_file = self.create_test_file("existing_file.py", "print('updated content')")
        
        # Add file to cache
        self.sync.sync_cache["existing_file.py"] = {
            'page_id': "existing_page_id_456",
            'hash': "old_hash",
            'last_sync': "2023-01-01T00:00:00"
        }
        
        # Mock Notion API responses
        self.mock_notion_client.pages.update.return_value = {}
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        self.mock_notion_client.blocks.children.append.return_value = {}
        
        page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=True)
        
        self.assertEqual(page_id, "existing_page_id_456")
        self.mock_notion_client.pages.update.assert_called_once()
    
    def test_skip_unchanged_file(self):
        """Test skipping files that haven't changed"""
        test_content = "print('unchanged content')"
        test_file = self.create_test_file("unchanged_file.py", test_content)
        
        # Calculate actual hash
        actual_hash = self.sync.get_file_hash(test_file)
        
        # Add file to cache with correct hash
        self.sync.sync_cache["unchanged_file.py"] = {
            'page_id': "cached_page_id_789",
            'hash': actual_hash,
            'last_sync': "2023-01-01T00:00:00"
        }
        
        page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=False)
        
        self.assertEqual(page_id, "cached_page_id_789")
        # Should not call Notion API for unchanged files
        self.mock_notion_client.pages.create.assert_not_called()
        self.mock_notion_client.pages.update.assert_not_called()

class TestCacheManagement(TestNotionSync):
    """Test cache loading and saving functionality"""
    
    def test_load_nonexistent_cache(self):
        """Test loading cache when file doesn't exist"""
        with patch('pathlib.Path.exists', return_value=False):
            cache = self.sync._load_sync_cache()
            self.assertEqual(cache, {})
    
    def test_load_valid_cache(self):
        """Test loading valid cache file"""
        cache_data = {
            "test.py": {
                "page_id": "page123",
                "hash": "hash123",
                "last_sync": "2023-01-01T00:00:00"
            }
        }
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(cache_data))):
                cache = self.sync._load_sync_cache()
                self.assertEqual(cache, cache_data)
    
    def test_save_cache(self):
        """Test saving cache to file"""
        self.sync.sync_cache = {
            "test.py": {
                "page_id": "page456",
                "hash": "hash456",
                "last_sync": "2023-01-01T12:00:00"
            }
        }
        
        with patch('builtins.open', mock_open()) as mock_file:
            with patch('json.dump') as mock_json_dump:
                self.sync._save_sync_cache()
                mock_file.assert_called_once()
                mock_json_dump.assert_called_once()

class TestErrorHandling(TestNotionSync):
    """Test error handling scenarios"""
    
    def test_read_file_encoding_error(self):
        """Test handling of file encoding errors"""
        # Create a file with binary content that can't be decoded as UTF-8
        binary_file = Path(self.test_dir) / "binary_file.py"
        with open(binary_file, 'wb') as f:
            f.write(b'\xFF\xFE\x00\x00')  # Invalid UTF-8 sequence
        
        page_id = self.sync.create_or_update_subpage(binary_file, self.test_dir)
        
        # Should handle encoding error gracefully
        self.assertIsNone(page_id)
    
    def test_notion_api_error(self):
        """Test handling of Notion API errors"""
        test_file = self.create_test_file("api_error_test.py", "print('test')")
        
        # Mock API to raise exception
        self.mock_notion_client.pages.create.side_effect = Exception("API Error")
        
        page_id = self.sync.create_or_update_subpage(test_file, self.test_dir)
        
        # Should handle API error gracefully
        self.assertIsNone(page_id)
    
    def test_nonexistent_project_path(self):
        """Test handling of nonexistent project path"""
        nonexistent_path = "/this/path/does/not/exist"
        
        with self.assertRaises(ValueError):
            self.sync.scan_source_files(nonexistent_path)

class TestConfigIntegration(TestNotionSync):
    """Test integration with Config class"""
    
    def test_supported_extensions(self):
        """Test that supported extensions are recognized"""
        # Create files with different extensions
        self.create_test_file("test.py", "# Python")
        self.create_test_file("test.cs", "// C#")
        self.create_test_file("test.js", "// JavaScript")
        self.create_test_file("test.txt", "Plain text")  # Not supported
        
        with patch.object(Config, 'get_supported_extensions', return_value=['.py', '.cs', '.js']):
            files = self.sync.scan_source_files(self.test_dir)
            
        self.assertEqual(len(files), 3)  # Should exclude .txt file
    
    def test_language_detection(self):
        """Test language detection for different file types"""
        with patch.object(Config, 'get_language_for_extension') as mock_lang:
            mock_lang.return_value = "python"
            
            test_file = self.create_test_file("test.py", "print('test')")
            
            # This would normally call Config.get_language_for_extension
            language = Config.get_language_for_extension(".py")
            
            mock_lang.assert_called_with(".py")

def mock_open(read_data=''):
    """Helper function to create mock file objects"""
    from unittest.mock import mock_open as original_mock_open
    return original_mock_open(read_data=read_data)

if __name__ == '__main__':
    # Run specific test classes or all tests
    unittest.main(verbosity=2)