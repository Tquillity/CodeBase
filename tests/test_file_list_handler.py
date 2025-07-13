# tests/test_file_list_handler.py
import os
import tempfile
import threading
import pytest
import time
from unittest.mock import patch, MagicMock
from file_list_handler import generate_list_content
from content_manager import FILE_SEPARATOR

@pytest.fixture
def temp_repo():
    """Fixture to create a temporary repository with sample files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        file1_path = os.path.join(temp_dir, "file1.txt")
        with open(file1_path, 'w', encoding='utf-8') as f:
            f.write("Content of file1")

        file2_path = os.path.join(temp_dir, "file2.py")
        with open(file2_path, 'w', encoding='utf-8') as f:
            f.write("print('Hello')")

        missing_path = os.path.join(temp_dir, "missing.txt")

        yield temp_dir, file1_path, file2_path, missing_path

def test_generate_list_content_success(temp_repo):
    temp_dir, file1_path, file2_path, _ = temp_repo
    files_to_copy = {file1_path, file2_path}
    lock = threading.Lock()
    content_cache = {}
    list_read_errors = []

    generated_contents = []
    token_counts = []
    errors_list = []

    def completion_callback(content, token_count, errors):
        generated_contents.append(content)
        token_counts.append(token_count)
        errors_list.extend(errors)

    generate_list_content(files_to_copy, temp_dir, lock, completion_callback, content_cache, list_read_errors)

    # Wait for thread to complete
    time.sleep(0.5)  # Short wait, assuming fast execution

    assert len(generated_contents) == 1
    content = generated_contents[0]

    parts = content.split(FILE_SEPARATOR)
    assert len(parts) == 2  # Two files, no trailing empty
    assert any("File: file1.txt\nContent:\n```txt\nContent of file1\n```\n" in p for p in parts)
    assert any("File: file2.py\nContent:\n```py\nprint('Hello')\n```\n" in p for p in parts)

    assert token_counts[0] > 0
    assert not errors_list
    assert not list_read_errors

def test_generate_list_content_with_missing_file(temp_repo):
    temp_dir, _, _, missing_path = temp_repo
    files_to_copy = {missing_path}
    lock = threading.Lock()
    content_cache = {}
    list_read_errors = []

    generated_contents = []
    errors_list = []

    def completion_callback(content, token_count, errors):
        generated_contents.append(content)
        errors_list.extend(errors)

    generate_list_content(files_to_copy, temp_dir, lock, completion_callback, content_cache, list_read_errors)

    time.sleep(0.5)

    assert generated_contents[0] == ""
    assert "Not Found: " in errors_list[0]

def test_generate_list_content_threading():
    # Test that it starts a thread
    with patch('threading.Thread') as mock_thread:
        thread_instance = MagicMock()
        mock_thread.return_value = thread_instance

        generate_list_content(set(), "", threading.Lock(), lambda *a: None, {}, [])

        mock_thread.assert_called_once()
        thread_instance.start.assert_called_once()
        assert mock_thread.call_args.kwargs['target'].__name__ == 'generate_content'
        assert mock_thread.call_args.kwargs['daemon'] == True