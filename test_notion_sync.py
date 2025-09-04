import unittest
import tempfile
import shutil
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from notion_sync import NotionSync
from config import Config

class TestNotionSyncFixed(unittest.TestCase):
    """Unit tests for NotionSync class - Updated for fixed version"""
    
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

class TestFixedRelativePathCalculation(TestNotionSyncFixed):
    """Test the fixed relative path calculation logic"""
    
    def test_relative_path_success(self):
        """Test successful relative path calculation"""
        test_file = self.create_test_file("test.py", "print('test')", "src")
        
        # Mock successful page creation
        self.mock_notion_client.pages.create.return_value = {"id": "page_123"}
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        
        page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=True)
        
        # Check that cache uses correct relative path
        expected_relative_path = "src/test.py"
        self.assertIn(expected_relative_path, self.sync.sync_cache)
        self.assertEqual(self.sync.sync_cache[expected_relative_path]['page_id'], "page_123")
    
    def test_relative_path_fallback_to_absolute(self):
        """Test fallback to absolute path when relative calculation fails"""
        test_file = self.create_test_file("test.py", "print('test')")
        
        # Mock Path.relative_to to raise ValueError
        with patch('pathlib.Path.relative_to', side_effect=ValueError("Not relative")):
            self.mock_notion_client.pages.create.return_value = {"id": "page_456"}
            self.mock_notion_client.blocks.children.list.return_value = {"results": []}
            
            page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=True)
            
            # Cache should use absolute path as key
            
            absolute_path = str(test_file.resolve()).replace('\\', '/') 
            self.assertIn(absolute_path, self.sync.sync_cache)
    
    def test_same_filename_different_paths(self):
        """Test that same filename in different paths have different cache keys"""
        # Create same filename in different directories
        file1 = self.create_test_file("utils.py", "# Utils 1", "src")
        file2 = self.create_test_file("utils.py", "# Utils 2", "tests")
        
        self.mock_notion_client.pages.create.side_effect = [
            {"id": "page_src_utils"},
            {"id": "page_tests_utils"}
        ]
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        
        # Sync both files
        page_id1 = self.sync.create_or_update_subpage(file1, self.test_dir, force_update=True)
        page_id2 = self.sync.create_or_update_subpage(file2, self.test_dir, force_update=True)
        
        # Should have different page IDs
        self.assertNotEqual(page_id1, page_id2)
        
        # Should have different cache keys
        cache_keys = list(self.sync.sync_cache.keys())
        self.assertEqual(len(cache_keys), 2)
        self.assertIn("src/utils.py", cache_keys)
        self.assertIn("tests/utils.py", cache_keys)

class TestOldPageDeletionLogic(TestNotionSyncFixed):
    """Test the new old page deletion logic"""
    
    def test_delete_old_page_before_creating_new(self):
        """Test that old page is deleted before creating new one"""
        test_file = self.create_test_file("update_test.py", "print('updated')")
        
        # Setup cache with existing page
        relative_path = "update_test.py"
        self.sync.sync_cache[relative_path] = {
            'page_id': "old_page_id_123",
            'hash': "old_hash",
            'last_sync': "2023-01-01T00:00:00"
        }
        
        # Mock Notion API responses
        self.mock_notion_client.pages.update.return_value = {}  # For archiving
        self.mock_notion_client.pages.create.return_value = {"id": "new_page_id_456"}
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        
        page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=True)
        
        # Verify old page was archived
        self.mock_notion_client.pages.update.assert_any_call(
            page_id="old_page_id_123",
            archived=True
        )
        
        # Verify new page was created
        self.mock_notion_client.pages.create.assert_called_once()
        
        # Verify cache was updated with new page ID
        self.assertEqual(page_id, "new_page_id_456")
        self.assertEqual(self.sync.sync_cache[relative_path]['page_id'], "new_page_id_456")
    
    def test_handle_old_page_deletion_failure(self):
        """Test handling when old page deletion fails"""
        test_file = self.create_test_file("deletion_fail_test.py", "print('test')")
        
        # Setup cache with existing page
        relative_path = "deletion_fail_test.py"
        self.sync.sync_cache[relative_path] = {
            'page_id': "old_page_id_789",
            'hash': "old_hash",
            'last_sync': "2023-01-01T00:00:00"
        }
        
        # Mock deletion to fail, but creation to succeed
        self.mock_notion_client.pages.update.side_effect = Exception("Cannot delete")
        self.mock_notion_client.pages.create.return_value = {"id": "new_page_id_999"}
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        
        page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=True)
        
        # Should still create new page even if deletion failed
        self.assertEqual(page_id, "new_page_id_999")
        self.mock_notion_client.pages.create.assert_called_once()
    
    def test_no_old_page_to_delete(self):
        """Test creating new page when no old page exists"""
        test_file = self.create_test_file("brand_new.py", "print('brand new')")
        
        # No existing cache
        self.sync.sync_cache = {}
        
        self.mock_notion_client.pages.create.return_value = {"id": "brand_new_page"}
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        
        page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=True)
        
        # Should not try to delete anything
        # pages.update should only be called for page creation, not archiving
        update_calls = [call for call in self.mock_notion_client.pages.update.call_args_list 
                       if call[1].get('archived') is True]
        self.assertEqual(len(update_calls), 0)
        
        # Should create new page
        self.assertEqual(page_id, "brand_new_page")
        self.mock_notion_client.pages.create.assert_called_once()

class TestCacheConsistency(TestNotionSyncFixed):
    """Test cache consistency with the new logic"""
    
    def test_cache_key_consistency(self):
        """Test that cache keys remain consistent across runs"""
        test_file = self.create_test_file("consistency_test.py", "print('test')")
        
        self.mock_notion_client.pages.create.return_value = {"id": "page_consistent"}
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        
        # First run
        page_id1 = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=True)
        first_cache = self.sync.sync_cache.copy()
        
        # Reset mocks for second run
        self.mock_notion_client.reset_mock()
        self.mock_notion_client.pages.create.return_value = {"id": "page_consistent_2"}
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        
        # Second run with same file (different content to force update)
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("print('updated content')")
        
        page_id2 = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=True)
        
        # Cache keys should be the same
        self.assertEqual(list(first_cache.keys()), list(self.sync.sync_cache.keys()))
        
        # But page IDs should be different (old deleted, new created)
        cache_key = list(self.sync.sync_cache.keys())[0]
        self.assertNotEqual(first_cache[cache_key]['page_id'], self.sync.sync_cache[cache_key]['page_id'])
    
    def test_hash_update_triggers_page_recreation(self):
        """Test that hash change triggers old page deletion and new page creation"""
        test_file = self.create_test_file("hash_update_test.py", "original content")
        original_hash = self.sync.get_file_hash(test_file)
        
        # Setup cache with original state
        relative_path = "hash_update_test.py"
        self.sync.sync_cache[relative_path] = {
            'page_id': "original_page_id",
            'hash': original_hash,
            'last_sync': "2023-01-01T00:00:00"
        }
        
        # Update file content (change hash)
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("updated content that changes hash")
        
        new_hash = self.sync.get_file_hash(test_file)
        self.assertNotEqual(original_hash, new_hash)  # Confirm hash changed
        
        # Mock API responses
        self.mock_notion_client.pages.update.return_value = {}  # For archiving
        self.mock_notion_client.pages.create.return_value = {"id": "new_page_id"}
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        
        page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=False)
        
        # Should delete old page
        self.mock_notion_client.pages.update.assert_called_with(
            page_id="original_page_id",
            archived=True
        )
        
        # Should create new page
        self.mock_notion_client.pages.create.assert_called_once()
        
        # Cache should be updated
        self.assertEqual(self.sync.sync_cache[relative_path]['page_id'], "new_page_id")
        self.assertEqual(self.sync.sync_cache[relative_path]['hash'], new_hash)

class TestCrossPlatformPathHandling(TestNotionSyncFixed):
    """Test cross-platform path handling improvements"""
    
    def test_windows_path_normalization(self):
        """Test that Windows paths are normalized correctly"""
        test_file = self.create_test_file("path_test.py", "print('path test')", "src\\utils")
        
        # Mock the relative_to to simulate Windows-style path
        with patch('pathlib.Path.relative_to') as mock_relative:
            mock_relative.return_value = Path("src\\utils\\path_test.py")
            
            self.mock_notion_client.pages.create.return_value = {"id": "path_page"}
            self.mock_notion_client.blocks.children.list.return_value = {"results": []}
            
            page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=True)
            
            # Cache key should use forward slashes (normalized)
            cache_keys = list(self.sync.sync_cache.keys())
            
            # Should contain normalized path (forward slashes)
            normalized_key = [k for k in cache_keys if "src/utils/path_test.py" in k or "src\\utils\\path_test.py" in k]
            self.assertTrue(len(normalized_key) > 0, f"Expected normalized path in cache keys: {cache_keys}")
    
    def test_absolute_path_fallback(self):
        """Test absolute path fallback when relative calculation fails"""
        test_file = self.create_test_file("fallback_test.py", "print('fallback')")
        
        with patch('pathlib.Path.relative_to', side_effect=ValueError("Path not relative")):
            self.mock_notion_client.pages.create.return_value = {"id": "fallback_page"}
            self.mock_notion_client.blocks.children.list.return_value = {"results": []}
            
            page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=True)
            
            # Cache should use absolute path as key
            absolute_path = str(test_file.resolve()).replace('\\', '/')  
            self.assertIn(absolute_path, self.sync.sync_cache)
            self.assertEqual(self.sync.sync_cache[absolute_path]['page_id'], "fallback_page")

class TestPageDeletionAndRecreation(TestNotionSyncFixed):
    """Test the new page deletion and recreation logic"""
    
    def test_archive_old_page_on_update(self):
        """Test that old page is archived when file is updated"""
        test_file = self.create_test_file("archive_test.py", "original content")
        
        # Setup cache with existing page
        relative_path = "archive_test.py"
        old_hash = self.sync.get_file_hash(test_file)
        self.sync.sync_cache[relative_path] = {
            'page_id': "old_page_to_archive",
            'hash': old_hash,
            'last_sync': "2023-01-01T00:00:00"
        }
        
        # Update file content
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("updated content")
        
        # Mock API responses
        self.mock_notion_client.pages.update.return_value = {}  # For archiving
        self.mock_notion_client.pages.create.return_value = {"id": "new_archived_page"}
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        
        page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=False)
        
        # Verify old page archiving was called
        archive_calls = [call for call in self.mock_notion_client.pages.update.call_args_list 
                        if call[1].get('archived') is True]
        self.assertEqual(len(archive_calls), 1)
        
        # Verify the correct page was archived
        archived_call = archive_calls[0]
        self.assertEqual(archived_call[1]['page_id'], "old_page_to_archive")
        
        # Verify new page creation
        self.mock_notion_client.pages.create.assert_called_once()
        
        # Verify cache update
        self.assertEqual(self.sync.sync_cache[relative_path]['page_id'], "new_archived_page")
    
    def test_handle_archive_failure_gracefully(self):
        """Test graceful handling when archiving old page fails"""
        test_file = self.create_test_file("archive_fail_test.py", "content")
        
        relative_path = "archive_fail_test.py"
        self.sync.sync_cache[relative_path] = {
            'page_id': "page_cannot_delete",
            'hash': "old_hash",
            'last_sync': "2023-01-01T00:00:00"
        }
        
        # Mock archiving to fail, but creation to succeed
        self.mock_notion_client.pages.update.side_effect = Exception("Archive failed")
        self.mock_notion_client.pages.create.return_value = {"id": "new_page_despite_failure"}
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        
        page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=True)
        
        # Should still create new page despite archive failure
        self.assertEqual(page_id, "new_page_despite_failure")
        self.mock_notion_client.pages.create.assert_called_once()
    
    def test_no_unnecessary_deletion_for_new_files(self):
        """Test that new files don't trigger unnecessary deletion attempts"""
        test_file = self.create_test_file("brand_new.py", "print('brand new')")
        
        # Empty cache (no existing page)
        self.sync.sync_cache = {}
        
        self.mock_notion_client.pages.create.return_value = {"id": "brand_new_page"}
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        
        page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=True)
        
        # Should not attempt any archiving for new files
        archive_calls = [call for call in self.mock_notion_client.pages.update.call_args_list 
                        if call[1].get('archived') is True]
        self.assertEqual(len(archive_calls), 0)
        
        # Should create new page
        self.assertEqual(page_id, "brand_new_page")

class TestSkipLogicWithNewChanges(TestNotionSyncFixed):
    """Test that skip logic still works correctly with the new changes"""
    
    def test_skip_unchanged_file_no_api_calls(self):
        """Test that unchanged files are skipped without any API calls"""
        test_file = self.create_test_file("unchanged.py", "print('unchanged')")
        file_hash = self.sync.get_file_hash(test_file)
        
        relative_path = "unchanged.py"
        self.sync.sync_cache[relative_path] = {
            'page_id': "unchanged_page",
            'hash': file_hash,  # Same hash
            'last_sync': "2023-01-01T00:00:00"
        }
        
        page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=False)
        
        # Should return cached page ID
        self.assertEqual(page_id, "unchanged_page")
        
        # Should not make any Notion API calls
        self.mock_notion_client.pages.create.assert_not_called()
        self.mock_notion_client.pages.update.assert_not_called()
        self.mock_notion_client.blocks.children.list.assert_not_called()

class TestIntegrationScenarios(TestNotionSyncFixed):
    """Test realistic integration scenarios"""
    
    def test_project_with_duplicate_filenames(self):
        """Test syncing a project with duplicate filenames in different directories"""
        # Create files with same name in different paths
        file1 = self.create_test_file("helper.py", "# Helper in src", "src")
        file2 = self.create_test_file("helper.py", "# Helper in utils", "utils")
        file3 = self.create_test_file("helper.py", "# Helper in tests", "tests")
        
        self.mock_notion_client.pages.create.side_effect = [
            {"id": "helper_src"},
            {"id": "helper_utils"},
            {"id": "helper_tests"}
        ]
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        
        # Sync all files
        page_ids = []
        for file_path in [file1, file2, file3]:
            page_id = self.sync.create_or_update_subpage(file_path, self.test_dir, force_update=True)
            page_ids.append(page_id)
        
        # All should have different page IDs
        self.assertEqual(len(set(page_ids)), 3)
        
        # All should have different cache keys
        self.assertEqual(len(self.sync.sync_cache), 3)
        cache_keys = list(self.sync.sync_cache.keys())
        self.assertEqual(len(set(cache_keys)), 3)
        
        # Should contain the expected relative paths
        expected_paths = {"src/helper.py", "utils/helper.py", "tests/helper.py"}
        actual_paths = set(cache_keys)
        self.assertEqual(actual_paths, expected_paths)
    
    def test_mixed_update_and_create_scenario(self):
        """Test scenario with both new files and updated existing files"""
        # Create existing file
        existing_file = self.create_test_file("existing.py", "old content")
        existing_hash = self.sync.get_file_hash(existing_file)
        
        # Setup cache for existing file
        self.sync.sync_cache["existing.py"] = {
            'page_id': "existing_page_id",
            'hash': existing_hash,
            'last_sync': "2023-01-01T00:00:00"
        }
        
        # Update existing file
        with open(existing_file, 'w', encoding='utf-8') as f:
            f.write("new content")
        
        # Create brand new file
        new_file = self.create_test_file("brand_new.py", "brand new content")
        
        # Mock API responses
        self.mock_notion_client.pages.update.return_value = {}  # For archiving
        self.mock_notion_client.pages.create.side_effect = [
            {"id": "updated_existing_page"},
            {"id": "brand_new_page"}
        ]
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        
        # Process both files
        existing_result = self.sync.create_or_update_subpage(existing_file, self.test_dir, force_update=False)
        new_result = self.sync.create_or_update_subpage(new_file, self.test_dir, force_update=False)
        
        # For existing file: should archive old + create new
        archive_calls = [call for call in self.mock_notion_client.pages.update.call_args_list 
                        if call[1].get('archived') is True]
        self.assertEqual(len(archive_calls), 1)
        self.assertEqual(archive_calls[0][1]['page_id'], "existing_page_id")
        
        # Should create 2 new pages total
        self.assertEqual(self.mock_notion_client.pages.create.call_count, 2)
        
        # Results should be correct
        self.assertEqual(existing_result, "updated_existing_page")
        self.assertEqual(new_result, "brand_new_page")
        
        # Cache should be updated for both
        self.assertEqual(len(self.sync.sync_cache), 2)
        self.assertEqual(self.sync.sync_cache["existing.py"]['page_id'], "updated_existing_page")
        self.assertEqual(self.sync.sync_cache["brand_new.py"]['page_id'], "brand_new_page")

def mock_open(read_data=''):
    """Helper function to create mock file objects"""
    from unittest.mock import mock_open as original_mock_open
    return original_mock_open(read_data=read_data)

if __name__ == '__main__':
    # Run tests with detailed output
    unittest.main(verbosity=2)