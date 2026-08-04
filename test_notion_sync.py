import unittest
import tempfile
import shutil
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from notion_sync import NotionSync
from config import Config

class TestShouldIgnorePath(unittest.TestCase):
    """Tests for Config.should_ignore_path() - exact segment matching only"""

    # --- should be ignored ---

    def test_exact_build_directory(self):
        self.assertTrue(Config.should_ignore_path("/project/build/output.py"))
    def test_exact_target_directory(self):
        self.assertTrue(Config.should_ignore_path("/project/target/classes/Main.class"))
    def test_exact_dist_directory(self):
        self.assertTrue(Config.should_ignore_path("/project/dist/bundle.js"))
    def test_exact_bin_directory(self):
        self.assertTrue(Config.should_ignore_path("/project/bin/app.exe"))
    def test_exact_obj_directory(self):
        self.assertTrue(Config.should_ignore_path("/project/obj/debug/app.obj"))
    def test_nested_ignored_directory(self):
        self.assertTrue(Config.should_ignore_path("/project/src/build/output.py"))
    def test_node_modules(self):
        self.assertTrue(Config.should_ignore_path("/project/node_modules/lodash/index.js"))
    def test_pycache(self):
        self.assertTrue(Config.should_ignore_path("/project/src/__pycache__/module.pyc"))
    def test_git_directory(self):
        self.assertTrue(Config.should_ignore_path("/project/.git/config"))
    def test_venv_directory(self):
        self.assertTrue(Config.should_ignore_path("/project/.venv/lib/python.py"))
    def test_wildcard_tmp(self):
        self.assertTrue(Config.should_ignore_path("/project/src/temp.tmp"))
    def test_wildcard_log(self):
        self.assertTrue(Config.should_ignore_path("/project/src/app.log"))
    def test_wildcard_min_js(self):
        self.assertTrue(Config.should_ignore_path("/project/static/jquery.min.js"))
    def test_wildcard_min_css(self):
        self.assertTrue(Config.should_ignore_path("/project/static/style.min.css"))
    def test_ds_store(self):
        self.assertTrue(Config.should_ignore_path("/project/.DS_Store"))

    # --- should NOT be ignored (regression tests for the substring bug) ---

    def test_filename_contains_build(self):
        self.assertFalse(Config.should_ignore_path("/project/src/build_utils.py"))
    def test_filename_contains_target(self):
        self.assertFalse(Config.should_ignore_path("/project/src/target_parser.cs"))
    def test_filename_starts_with_build(self):
        self.assertFalse(Config.should_ignore_path("/project/src/builder.py"))
    def test_filename_ends_with_build(self):
        self.assertFalse(Config.should_ignore_path("/project/src/rebuild.py"))
    def test_directory_name_contains_build(self):
        self.assertFalse(Config.should_ignore_path("/project/rebuild_scripts/deploy.py"))
    def test_directory_name_contains_target(self):
        self.assertFalse(Config.should_ignore_path("/project/target_env/config.py"))
    def test_filename_contains_dist(self):
        self.assertFalse(Config.should_ignore_path("/project/src/distribution.py"))
    def test_filename_contains_bin(self):
        self.assertFalse(Config.should_ignore_path("/project/src/binary_utils.py"))
    def test_normal_python_file(self):
        self.assertFalse(Config.should_ignore_path("/project/src/main.py"))
    def test_normal_cs_file(self):
        self.assertFalse(Config.should_ignore_path("/project/src/GameManager.cs"))
    def test_normal_nested_file(self):
        self.assertFalse(Config.should_ignore_path("/project/src/utils/helper.py"))

    # --- case sensitivity ---

    def test_uppercase_BUILD_directory(self):
        # exact match is case-sensitive; change if you add case-insensitive matching
        self.assertFalse(Config.should_ignore_path("/project/BUILD/output.py"))

class TestNotionSyncFixed(unittest.TestCase):
    """Unit tests for NotionSync class - Updated for fixed version"""
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.mock_notion_token = "test_token_123"
        self.mock_parent_page_id = "test_page_id_456"
        self.mock_notion_client = Mock()
        with patch('notion_sync.Client'):
            self.sync = NotionSync(self.mock_notion_token, self.mock_parent_page_id)
            self.sync.notion = self.mock_notion_client
            self.sync.sync_cache = {}
    def tearDown(self):
        shutil.rmtree(self.test_dir)
    def create_test_file(self, filename, content, subdir=""):
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
        test_file = self.create_test_file("test.py", "print('test')", "src")
        self.mock_notion_client.pages.create.return_value = {"id": "page_123"}
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=True)
        expected_relative_path = str(Path("src/test.py"))  # OS-native separator
        self.assertIn(expected_relative_path, self.sync.sync_cache)
        self.assertEqual(self.sync.sync_cache[expected_relative_path]['page_id'], "page_123")
    def test_relative_path_fallback_to_absolute(self):
        test_file = self.create_test_file("test.py", "print('test')")
        with patch('pathlib.Path.relative_to', side_effect=ValueError("Not relative")):
            self.mock_notion_client.pages.create.return_value = {"id": "page_456"}
            self.mock_notion_client.blocks.children.list.return_value = {"results": []}
            page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=True)
            absolute_path = str(test_file.resolve()).replace('\\', '/')
            self.assertIn(absolute_path, self.sync.sync_cache)
    def test_same_filename_different_paths(self):
        file1 = self.create_test_file("utils.py", "# Utils 1", "src")
        file2 = self.create_test_file("utils.py", "# Utils 2", "tests")
        self.mock_notion_client.pages.create.side_effect = [
            {"id": "page_src_utils"},
            {"id": "page_tests_utils"}
        ]
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        page_id1 = self.sync.create_or_update_subpage(file1, self.test_dir, force_update=True)
        page_id2 = self.sync.create_or_update_subpage(file2, self.test_dir, force_update=True)
        self.assertNotEqual(page_id1, page_id2)
        cache_keys = list(self.sync.sync_cache.keys())
        self.assertEqual(len(cache_keys), 2)
        self.assertIn(str(Path("src/utils.py")), cache_keys)    # OS-native separator
        self.assertIn(str(Path("tests/utils.py")), cache_keys)  # OS-native separator

class TestOldPageDeletionLogic(TestNotionSyncFixed):
    """Test the new old page deletion logic"""
    def test_delete_old_page_before_creating_new(self):
        test_file = self.create_test_file("update_test.py", "print('updated')")
        relative_path = "update_test.py"
        self.sync.sync_cache[relative_path] = {
            'page_id': "old_page_id_123",
            'hash': "old_hash",
            'last_sync': "2023-01-01T00:00:00"
        }
        self.mock_notion_client.pages.update.return_value = {}
        self.mock_notion_client.pages.create.return_value = {"id": "new_page_id_456"}
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=True)
        self.mock_notion_client.pages.update.assert_any_call(
            page_id="old_page_id_123",
            archived=True
        )
        self.mock_notion_client.pages.create.assert_called_once()
        self.assertEqual(page_id, "new_page_id_456")
        self.assertEqual(self.sync.sync_cache[relative_path]['page_id'], "new_page_id_456")
    def test_handle_old_page_deletion_failure(self):
        test_file = self.create_test_file("deletion_fail_test.py", "print('test')")
        relative_path = "deletion_fail_test.py"
        self.sync.sync_cache[relative_path] = {
            'page_id': "old_page_id_789",
            'hash': "old_hash",
            'last_sync': "2023-01-01T00:00:00"
        }
        self.mock_notion_client.pages.update.side_effect = Exception("Cannot delete")
        self.mock_notion_client.pages.create.return_value = {"id": "new_page_id_999"}
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=True)
        self.assertEqual(page_id, "new_page_id_999")
        self.mock_notion_client.pages.create.assert_called_once()
    def test_no_old_page_to_delete(self):
        test_file = self.create_test_file("brand_new.py", "print('brand new')")
        self.sync.sync_cache = {}
        self.mock_notion_client.pages.create.return_value = {"id": "brand_new_page"}
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=True)
        update_calls = [c for c in self.mock_notion_client.pages.update.call_args_list
                        if c[1].get('archived') is True]
        self.assertEqual(len(update_calls), 0)
        self.assertEqual(page_id, "brand_new_page")
        self.mock_notion_client.pages.create.assert_called_once()

class TestCacheConsistency(TestNotionSyncFixed):
    """Test cache consistency with the new logic"""
    def test_cache_key_consistency(self):
        test_file = self.create_test_file("consistency_test.py", "print('test')")
        self.mock_notion_client.pages.create.return_value = {"id": "page_consistent"}
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        page_id1 = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=True)
        first_cache = self.sync.sync_cache.copy()
        self.mock_notion_client.reset_mock()
        self.mock_notion_client.pages.create.return_value = {"id": "page_consistent_2"}
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("print('updated content')")
        page_id2 = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=True)
        self.assertEqual(list(first_cache.keys()), list(self.sync.sync_cache.keys()))
        cache_key = list(self.sync.sync_cache.keys())[0]
        self.assertNotEqual(first_cache[cache_key]['page_id'], self.sync.sync_cache[cache_key]['page_id'])
    def test_hash_update_triggers_page_recreation(self):
        test_file = self.create_test_file("hash_update_test.py", "original content")
        original_hash = self.sync.get_file_hash(test_file)
        relative_path = "hash_update_test.py"
        self.sync.sync_cache[relative_path] = {
            'page_id': "original_page_id",
            'hash': original_hash,
            'last_sync': "2023-01-01T00:00:00"
        }
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("updated content that changes hash")
        new_hash = self.sync.get_file_hash(test_file)
        self.assertNotEqual(original_hash, new_hash)
        self.mock_notion_client.pages.update.return_value = {}
        self.mock_notion_client.pages.create.return_value = {"id": "new_page_id"}
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=False)
        self.mock_notion_client.pages.update.assert_called_with(
            page_id="original_page_id",
            archived=True
        )
        self.mock_notion_client.pages.create.assert_called_once()
        self.assertEqual(self.sync.sync_cache[relative_path]['page_id'], "new_page_id")
        self.assertEqual(self.sync.sync_cache[relative_path]['hash'], new_hash)

class TestCrossPlatformPathHandling(TestNotionSyncFixed):
    """Test cross-platform path handling improvements"""
    def test_windows_path_normalization(self):
        test_file = self.create_test_file("path_test.py", "print('path test')", "src")
        with patch('pathlib.Path.relative_to') as mock_relative:
            mock_relative.return_value = Path("src\\utils\\path_test.py")
            self.mock_notion_client.pages.create.return_value = {"id": "path_page"}
            self.mock_notion_client.blocks.children.list.return_value = {"results": []}
            page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=True)
            cache_keys = list(self.sync.sync_cache.keys())
            normalized_key = [k for k in cache_keys
                              if "src/utils/path_test.py" in k or str(Path("src/utils/path_test.py")) in k]
            self.assertTrue(len(normalized_key) > 0, f"Expected normalized path in cache keys: {cache_keys}")
    def test_absolute_path_fallback(self):
        test_file = self.create_test_file("fallback_test.py", "print('fallback')")
        with patch('pathlib.Path.relative_to', side_effect=ValueError("Path not relative")):
            self.mock_notion_client.pages.create.return_value = {"id": "fallback_page"}
            self.mock_notion_client.blocks.children.list.return_value = {"results": []}
            page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=True)
            absolute_path = str(test_file.resolve()).replace('\\', '/')
            self.assertIn(absolute_path, self.sync.sync_cache)
            self.assertEqual(self.sync.sync_cache[absolute_path]['page_id'], "fallback_page")

class TestPageDeletionAndRecreation(TestNotionSyncFixed):
    """Test the new page deletion and recreation logic"""
    def test_archive_old_page_on_update(self):
        test_file = self.create_test_file("archive_test.py", "original content")
        relative_path = "archive_test.py"
        old_hash = self.sync.get_file_hash(test_file)
        self.sync.sync_cache[relative_path] = {
            'page_id': "old_page_to_archive",
            'hash': old_hash,
            'last_sync': "2023-01-01T00:00:00"
        }
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("updated content")
        self.mock_notion_client.pages.update.return_value = {}
        self.mock_notion_client.pages.create.return_value = {"id": "new_archived_page"}
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=False)
        archive_calls = [c for c in self.mock_notion_client.pages.update.call_args_list
                         if c[1].get('archived') is True]
        self.assertEqual(len(archive_calls), 1)
        self.assertEqual(archive_calls[0][1]['page_id'], "old_page_to_archive")
        self.mock_notion_client.pages.create.assert_called_once()
        self.assertEqual(self.sync.sync_cache[relative_path]['page_id'], "new_archived_page")
    def test_handle_archive_failure_gracefully(self):
        test_file = self.create_test_file("archive_fail_test.py", "content")
        relative_path = "archive_fail_test.py"
        self.sync.sync_cache[relative_path] = {
            'page_id': "page_cannot_delete",
            'hash': "old_hash",
            'last_sync': "2023-01-01T00:00:00"
        }
        self.mock_notion_client.pages.update.side_effect = Exception("Archive failed")
        self.mock_notion_client.pages.create.return_value = {"id": "new_page_despite_failure"}
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=True)
        self.assertEqual(page_id, "new_page_despite_failure")
        self.mock_notion_client.pages.create.assert_called_once()
    def test_no_unnecessary_deletion_for_new_files(self):
        test_file = self.create_test_file("brand_new.py", "print('brand new')")
        self.sync.sync_cache = {}
        self.mock_notion_client.pages.create.return_value = {"id": "brand_new_page"}
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=True)
        archive_calls = [c for c in self.mock_notion_client.pages.update.call_args_list
                         if c[1].get('archived') is True]
        self.assertEqual(len(archive_calls), 0)
        self.assertEqual(page_id, "brand_new_page")

class TestSkipLogicWithNewChanges(TestNotionSyncFixed):
    """Test that skip logic still works correctly with the new changes"""
    def test_skip_unchanged_file_no_api_calls(self):
        test_file = self.create_test_file("unchanged.py", "print('unchanged')")
        file_hash = self.sync.get_file_hash(test_file)
        relative_path = "unchanged.py"
        self.sync.sync_cache[relative_path] = {
            'page_id': "unchanged_page",
            'hash': file_hash,
            'last_sync': "2023-01-01T00:00:00"
        }
        page_id = self.sync.create_or_update_subpage(test_file, self.test_dir, force_update=False)
        self.assertEqual(page_id, "unchanged_page")
        self.mock_notion_client.pages.create.assert_not_called()
        self.mock_notion_client.pages.update.assert_not_called()
        self.mock_notion_client.blocks.children.list.assert_not_called()

class TestIntegrationScenarios(TestNotionSyncFixed):
    """Test realistic integration scenarios"""
    def test_project_with_duplicate_filenames(self):
        file1 = self.create_test_file("helper.py", "# Helper in src", "src")
        file2 = self.create_test_file("helper.py", "# Helper in utils", "utils")
        file3 = self.create_test_file("helper.py", "# Helper in tests", "tests")
        self.mock_notion_client.pages.create.side_effect = [
            {"id": "helper_src"},
            {"id": "helper_utils"},
            {"id": "helper_tests"}
        ]
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        page_ids = []
        for file_path in [file1, file2, file3]:
            page_id = self.sync.create_or_update_subpage(file_path, self.test_dir, force_update=True)
            page_ids.append(page_id)
        self.assertEqual(len(set(page_ids)), 3)
        self.assertEqual(len(self.sync.sync_cache), 3)
        cache_keys = list(self.sync.sync_cache.keys())
        self.assertEqual(len(set(cache_keys)), 3)
        expected_paths = {
            str(Path("src/helper.py")),    # OS-native separator
            str(Path("utils/helper.py")),
            str(Path("tests/helper.py")),
        }
        actual_paths = set(cache_keys)
        self.assertEqual(actual_paths, expected_paths)
    def test_mixed_update_and_create_scenario(self):
        existing_file = self.create_test_file("existing.py", "old content")
        existing_hash = self.sync.get_file_hash(existing_file)
        self.sync.sync_cache["existing.py"] = {
            'page_id': "existing_page_id",
            'hash': existing_hash,
            'last_sync': "2023-01-01T00:00:00"
        }
        with open(existing_file, 'w', encoding='utf-8') as f:
            f.write("new content")
        new_file = self.create_test_file("brand_new.py", "brand new content")
        self.mock_notion_client.pages.update.return_value = {}
        self.mock_notion_client.pages.create.side_effect = [
            {"id": "updated_existing_page"},
            {"id": "brand_new_page"}
        ]
        self.mock_notion_client.blocks.children.list.return_value = {"results": []}
        existing_result = self.sync.create_or_update_subpage(existing_file, self.test_dir, force_update=False)
        new_result = self.sync.create_or_update_subpage(new_file, self.test_dir, force_update=False)
        archive_calls = [c for c in self.mock_notion_client.pages.update.call_args_list
                         if c[1].get('archived') is True]
        self.assertEqual(len(archive_calls), 1)
        self.assertEqual(archive_calls[0][1]['page_id'], "existing_page_id")
        self.assertEqual(self.mock_notion_client.pages.create.call_count, 2)
        self.assertEqual(existing_result, "updated_existing_page")
        self.assertEqual(new_result, "brand_new_page")
        self.assertEqual(len(self.sync.sync_cache), 2)
        self.assertEqual(self.sync.sync_cache["existing.py"]['page_id'], "updated_existing_page")
        self.assertEqual(self.sync.sync_cache["brand_new.py"]['page_id'], "brand_new_page")

class TestDirectMarkdownPageApi(TestNotionSyncFixed):
    """Tests for sending Markdown source directly to Notion."""

    def test_create_markdown_page_sends_source_unchanged(self):
        markdown_content = (
            "# Report\n\n"
            "| Field | Value |\n"
            "| --- | --- |\n"
            "| Age | 100 |\n\n"
            "**Bold** and [Link](https://example.com)"
        )
        response_context = MagicMock()
        response_context.__enter__.return_value.read.return_value = b'{"id":"markdown_page_123"}'

        with patch(
            'notion_sync.urllib.request.urlopen',
            return_value=response_context
        ) as urlopen:
            result = self.sync._create_markdown_page('Report.md', markdown_content)

        self.assertEqual(result['id'], 'markdown_page_123')
        request = urlopen.call_args.args[0]
        payload = json.loads(request.data.decode('utf-8'))
        headers = {key.lower(): value for key, value in request.header_items()}

        self.assertEqual(request.get_method(), 'POST')
        self.assertEqual(request.full_url, 'https://api.notion.com/v1/pages')
        self.assertEqual(headers['notion-version'], '2026-03-11')
        self.assertEqual(payload['markdown'], markdown_content)
        self.assertEqual(payload['parent']['page_id'], self.mock_parent_page_id)
        self.assertEqual(
            payload['properties']['title'][0]['text']['content'],
            'Report.md'
        )

    def test_markdown_file_uses_direct_page_api(self):
        markdown_file = self.create_test_file(
            'guide.md',
            '# Guide\n\n| A | B |\n| --- | --- |\n| 1 | 2 |'
        )
        self.mock_notion_client.pages.create.reset_mock()

        with patch.object(
            self.sync,
            '_create_markdown_page',
            return_value={'id': 'native_markdown_page'}
        ) as create_markdown_page:
            page_id = self.sync.create_or_update_subpage(
                markdown_file,
                self.test_dir,
                force_update=True
            )

        self.assertEqual(page_id, 'native_markdown_page')
        create_markdown_page.assert_called_once()
        sent_title, sent_markdown, sent_parent = create_markdown_page.call_args.args
        self.assertEqual(sent_title, 'guide.md')
        self.assertIn('| A | B |', sent_markdown)
        self.assertEqual(sent_parent, self.mock_parent_page_id)
        self.mock_notion_client.pages.create.assert_not_called()
        self.mock_notion_client.blocks.children.list.assert_not_called()

    def test_nested_markdown_uses_directory_parent(self):
        markdown_file = self.create_test_file(
            'README.md',
            '# Nested README',
            'docs/api'
        )

        with patch.object(
            self.sync,
            '_ensure_directory_hierarchy',
            return_value='api_folder_page'
        ) as ensure_hierarchy, patch.object(
            self.sync,
            '_create_markdown_page',
            return_value={'id': 'nested_markdown_page'}
        ) as create_markdown_page:
            page_id = self.sync.create_or_update_subpage(
                markdown_file,
                self.test_dir,
                force_update=True
            )

        self.assertEqual(page_id, 'nested_markdown_page')
        ensure_hierarchy.assert_called_once_with(Path('docs/api'))
        create_markdown_page.assert_called_once_with(
            'README.md',
            '# Nested README',
            'api_folder_page'
        )

    def test_directory_hierarchy_creates_nested_pages_once(self):
        self.mock_notion_client.blocks.children.list.return_value = {
            'results': [],
            'has_more': False
        }
        self.mock_notion_client.pages.create.side_effect = [
            {'id': 'docs_folder_page'},
            {'id': 'api_folder_page'}
        ]

        first_result = self.sync._ensure_directory_hierarchy(Path('docs/api'))
        second_result = self.sync._ensure_directory_hierarchy(Path('docs/api'))

        self.assertEqual(first_result, 'api_folder_page')
        self.assertEqual(second_result, 'api_folder_page')
        self.assertEqual(self.mock_notion_client.pages.create.call_count, 2)
        self.mock_notion_client.pages.create.assert_has_calls([
            call(
                parent={
                    'type': 'page_id',
                    'page_id': self.mock_parent_page_id
                },
                properties={
                    'title': [{
                        'text': {
                            'content': 'docs'
                        }
                    }]
                }
            ),
            call(
                parent={
                    'type': 'page_id',
                    'page_id': 'docs_folder_page'
                },
                properties={
                    'title': [{
                        'text': {
                            'content': 'api'
                        }
                    }]
                }
            )
        ])

    def test_retrieve_markdown_page_returns_markdown(self):
        markdown_content = "# Report\n\n| A | B |\n| --- | --- |\n| 1 | 2 |"
        response_context = MagicMock()
        response_context.__enter__.return_value.read.return_value = json.dumps({
            "markdown": markdown_content,
            "truncated": False,
            "unknown_block_ids": [],
        }).encode("utf-8")

        with patch(
            "notion_sync.urllib.request.urlopen",
            return_value=response_context,
        ) as urlopen:
            result = self.sync._retrieve_markdown_page("markdown_page_123")

        self.assertEqual(result, markdown_content)
        request = urlopen.call_args.args[0]
        headers = {key.lower(): value for key, value in request.header_items()}
        expected_url = (
            "https:" + "//api.notion.com/v1/pages/"
            "markdown_page_123/markdown"
        )
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.full_url, expected_url)
        self.assertEqual(headers["notion-version"], "2026-03-11")

    def test_retrieve_markdown_page_rejects_truncated_content(self):
        response_context = MagicMock()
        response_context.__enter__.return_value.read.return_value = json.dumps({
            "markdown": "# Partial",
            "truncated": True,
            "unknown_block_ids": ["block_456"],
        }).encode("utf-8")

        with patch(
            "notion_sync.urllib.request.urlopen",
            return_value=response_context,
        ):
            with self.assertRaises(RuntimeError):
                self.sync._retrieve_markdown_page("markdown_page_123")

    def test_pull_routes_markdown_through_markdown_api(self):
        output_dir = Path(self.test_dir) / "pulled"
        self.sync.sync_cache = {
            str(Path("docs") / "README.md"): {
                "page_id": "markdown_page_123",
                "language": "markdown",
            }
        }

        with patch.object(Config, "load_env_from_path"), patch(
            "notion_sync.Client",
            return_value=self.mock_notion_client,
        ), patch.object(
            self.sync,
            "load_cache_for_project",
            return_value=Path(self.test_dir) / ".notion_sync_cache.json",
        ), patch.object(
            self.sync,
            "_retrieve_markdown_page",
            return_value="# Nested README",
        ) as retrieve_markdown, patch.object(
            self.sync,
            "_extract_code_from_page",
        ) as extract_code:
            self.sync.pull_from_notion(
                self.test_dir,
                output_dir,
                force_overwrite=True,
            )

        retrieve_markdown.assert_called_once_with("markdown_page_123")
        extract_code.assert_not_called()
        output_file = output_dir / "docs" / "README.md"
        self.assertEqual(
            output_file.read_text(encoding="utf-8"),
            "# Nested README",
        )

    def test_pull_keeps_code_extraction_for_source_files(self):
        output_dir = Path(self.test_dir) / "pulled_code"
        self.sync.sync_cache = {
            str(Path("src") / "tool.py"): {
                "page_id": "code_page_123",
                "language": "python",
            }
        }

        with patch.object(Config, "load_env_from_path"), patch(
            "notion_sync.Client",
            return_value=self.mock_notion_client,
        ), patch.object(
            self.sync,
            "load_cache_for_project",
            return_value=Path(self.test_dir) / ".notion_sync_cache.json",
        ), patch.object(
            self.sync,
            "_retrieve_markdown_page",
        ) as retrieve_markdown, patch.object(
            self.sync,
            "_extract_code_from_page",
            return_value="print('ok')",
        ) as extract_code:
            self.sync.pull_from_notion(
                self.test_dir,
                output_dir,
                force_overwrite=True,
            )

        retrieve_markdown.assert_not_called()
        extract_code.assert_called_once_with("code_page_123")
        output_file = output_dir / "src" / "tool.py"
        self.assertEqual(
            output_file.read_text(encoding="utf-8"),
            "print('ok')",
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)