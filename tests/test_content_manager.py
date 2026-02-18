# tests/test_content_manager.py
import os
import tempfile
import time
import threading
import logging
import pytest
from content_manager import get_file_content, generate_content, FILE_SEPARATOR
from lru_cache import ThreadSafeLRUCache

# Setup logging for tests
from logging_config import setup_logging
setup_logging(level="INFO", console_output=False)

@pytest.fixture
def temp_repo():
    """Fixture to create a temporary repository structure."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create sample files
        file1_path = os.path.join(temp_dir, "file1.txt")
        with open(file1_path, 'w', encoding='utf-8') as f:
            f.write("Content of file1")

        file2_path = os.path.join(temp_dir, "file2.py")
        with open(file2_path, 'w', encoding='utf-8') as f:
            f.write("print('Hello')")

        # Create a binary file to test encoding error
        binary_path = os.path.join(temp_dir, "binary.bin")
        with open(binary_path, 'wb') as f:
            f.write(b'\x00\xFF')

        # Create a non-existent file path for testing
        missing_path = os.path.join(temp_dir, "missing.txt")

        yield temp_dir, file1_path, file2_path, binary_path, missing_path

def test_get_file_content_success(temp_repo):
    temp_dir, file1_path, _, _, _ = temp_repo
    content_cache = ThreadSafeLRUCache(100, 10)  # Small cache for testing
    lock = threading.Lock()
    read_errors: list[str] = []

    content = get_file_content(file1_path, content_cache, lock, read_errors)
    assert content == "Content of file1"
    assert content_cache.get(os.path.normcase(file1_path)) == "Content of file1"  # Check caching
    assert not read_errors

def test_get_file_content_cached(temp_repo):
    temp_dir, file1_path, _, _, _ = temp_repo
    content_cache = ThreadSafeLRUCache(100, 10)
    content_cache.put(os.path.normcase(file1_path), "Cached content")
    lock = threading.Lock()
    read_errors: list[str] = []

    content = get_file_content(file1_path, content_cache, lock, read_errors)
    assert content == "Cached content"
    assert not read_errors

def test_get_file_content_missing_file(temp_repo):
    temp_dir, _, _, _, missing_path = temp_repo
    content_cache = ThreadSafeLRUCache(100, 10)
    lock = threading.Lock()
    read_errors: list[str] = []

    content = get_file_content(missing_path, content_cache, lock, read_errors)
    assert content is None
    assert "Not Found: " + os.path.normcase(missing_path) in read_errors

def test_get_file_content_permission_denied(monkeypatch, temp_repo):
    temp_dir, file1_path, _, _, _ = temp_repo
    content_cache = ThreadSafeLRUCache(100, 10)
    lock = threading.Lock()
    read_errors: list[str] = []

    # Mock open to raise PermissionError
    def mock_open(*args, **kwargs):
        raise PermissionError("Permission denied")

    monkeypatch.setattr("builtins.open", mock_open)

    content = get_file_content(file1_path, content_cache, lock, read_errors)
    assert content is None
    assert "Permission Denied: " + os.path.normcase(file1_path) in read_errors

def test_get_file_content_binary_file(temp_repo):
    temp_dir, _, _, binary_path, _ = temp_repo
    content_cache = ThreadSafeLRUCache(100, 10)
    lock = threading.Lock()
    read_errors: list[str] = []

    content = get_file_content(binary_path, content_cache, lock, read_errors)
    assert content is not None  # With 'ignore', it reads, but content may have missing chars.
    assert not read_errors  # No error logged for binary with 'ignore'

def test_get_file_content_general_error(monkeypatch, temp_repo):
    temp_dir, file1_path, _, _, _ = temp_repo
    content_cache = ThreadSafeLRUCache(100, 10)
    lock = threading.Lock()
    read_errors: list[str] = []

    # Mock open to raise a general Exception
    def mock_open(*args, **kwargs):
        raise Exception("General error")

    monkeypatch.setattr("builtins.open", mock_open)

    content = get_file_content(file1_path, content_cache, lock, read_errors)
    assert content is None
    assert any("Read Error: " in err and "General error" in err for err in read_errors)

def test_generate_content_success(temp_repo):
    temp_dir, file1_path, file2_path, _, _ = temp_repo
    files_to_include = {file1_path, file2_path}
    lock = threading.Lock()
    content_cache = ThreadSafeLRUCache(100, 10)
    read_errors: list[str] = []

    generated_content = []
    token_counts = []
    local_errors: list[str] = []

    def completion_callback(content, token_count, errors, deleted_files=None):
        generated_content.append(content)
        token_counts.append(token_count)
        local_errors.extend(errors or [])

    generate_content(files_to_include, temp_dir, lock, completion_callback, content_cache, read_errors, None, None)

    # Since it's sync, callback is called immediately
    assert len(generated_content) == 1
    content = generated_content[0]

    parts = content.split(FILE_SEPARATOR)
    assert len(parts) == 2  # Two files, no trailing empty after last sep
    assert any("File: file1.txt\nContent:\n```txt\nContent of file1\n```\n" in p for p in parts)
    assert any("File: file2.py\nContent:\n```py\nprint('Hello')\n```\n" in p for p in parts)

    assert token_counts[0] > 0
    assert not local_errors
    assert not read_errors

def test_generate_content_with_errors(temp_repo):
    temp_dir, _, _, _, missing_path = temp_repo
    files_to_include = {missing_path}
    lock = threading.Lock()
    content_cache = ThreadSafeLRUCache(100, 10)
    read_errors: list[str] = []

    generated_content = []
    local_errors: list[str] = []
    local_deleted: list[str] = []

    def completion_callback(content, token_count, errors, deleted_files=None):
        generated_content.append(content)
        local_errors.extend(errors or [])
        local_deleted.extend(deleted_files or [])

    generate_content(files_to_include, temp_dir, lock, completion_callback, content_cache, read_errors, None, None)

    assert generated_content[0] == ""
    assert missing_path in local_deleted

def test_generate_content_sorted_order(temp_repo):
    temp_dir, file1_path, file2_path, _, _ = temp_repo
    # Add another file to test sorting
    file0_path = os.path.join(temp_dir, "afile.txt")  # 'a' before 'f'
    with open(file0_path, 'w') as f:
        f.write("Early file")

    files_to_include = {file1_path, file2_path, file0_path}
    lock = threading.Lock()
    content_cache = ThreadSafeLRUCache(100, 10)
    read_errors: list[str] = []

    generated_content = []

    def completion_callback(content, *args):
        generated_content.append(content)

    generate_content(files_to_include, temp_dir, lock, completion_callback, content_cache, read_errors, None, None)

    content = generated_content[0]
    parts = content.split(FILE_SEPARATOR)
    assert len(parts) == 3  # Three files , no trailing empty

    # Check order: sorted alphabetically by full path
    assert "afile.txt" in parts[0]
    assert "file1.txt" in parts[1]
    assert "file2.py" in parts[2]

def test_generate_content_token_count(temp_repo):
    temp_dir, file1_path, _, _, _ = temp_repo
    files_to_include = {file1_path}
    lock = threading.Lock()
    content_cache = ThreadSafeLRUCache(100, 10)
    read_errors: list[str] = []

    token_counts = []

    def completion_callback(_, token_count, __, ___=None):
        token_counts.append(token_count)

    generate_content(files_to_include, temp_dir, lock, completion_callback, content_cache, read_errors, None, None)

    # Approximate, but >0
    assert token_counts[0] > 5

def test_generate_content_performance(caplog, temp_repo):
    caplog.set_level(logging.INFO)
    temp_dir, file1_path, file2_path, _, _ = temp_repo
    files_to_include = {file1_path, file2_path}
    lock = threading.Lock()
    content_cache = ThreadSafeLRUCache(100, 10)
    read_errors: list[str] = []

    def completion_callback(*args):
        pass

    start_time = time.time()
    generate_content(files_to_include, temp_dir, lock, completion_callback, content_cache, read_errors, None, None)
    duration = time.time() - start_time

    assert duration < 1  # Should be fast for small files
    assert "Content generation complete" in caplog.text