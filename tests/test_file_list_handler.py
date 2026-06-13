# tests/test_file_list_handler.py
import os
import tempfile
import threading
import pytest
from unittest.mock import patch, MagicMock
from file_list_handler import generate_list_content
from constants import FILE_SEPARATOR


@pytest.fixture
def mock_gui():
    gui = MagicMock()
    gui.task_queue = MagicMock()
    gui.settings = MagicMock()
    gui.settings.get.return_value = "Markdown (Grok)"
    gui.settings.security_enabled.return_value = False
    gui.settings.sanitize_urls_enabled.return_value = False
    gui.register_background_thread = MagicMock()
    gui._shutdown_requested = False
    gui._scan_cancel_requested = False

    def mock_put(task):
        if isinstance(task, tuple) and len(task) == 2:
            func, args = task
            func(*args)

    gui.task_queue.put = mock_put
    return gui


@pytest.fixture
def temp_repo():
    with tempfile.TemporaryDirectory() as temp_dir:
        file1_path = os.path.join(temp_dir, "file1.txt")
        with open(file1_path, 'w', encoding='utf-8') as f:
            f.write("Content of file1")

        file2_path = os.path.join(temp_dir, "file2.py")
        with open(file2_path, 'w', encoding='utf-8') as f:
            f.write("print('Hello')")

        missing_path = os.path.join(temp_dir, "missing.txt")

        yield temp_dir, file1_path, file2_path, missing_path


def test_generate_list_content_success(temp_repo, mock_gui):
    temp_dir, file1_path, file2_path, _ = temp_repo
    files_to_copy = {file1_path, file2_path}
    lock = threading.Lock()
    from lru_cache import ThreadSafeLRUCache
    content_cache = ThreadSafeLRUCache(100, 10)

    generated_contents = []
    token_counts = []
    errors_list = []
    done = threading.Event()

    def completion_callback(content, token_count, errors, deleted_files=None):
        generated_contents.append(content)
        token_counts.append(token_count)
        errors_list.extend(errors)
        done.set()

    generate_list_content(mock_gui, files_to_copy, temp_dir, lock, completion_callback, content_cache)

    assert done.wait(timeout=2)

    assert len(generated_contents) == 1
    content = generated_contents[0]

    parts = content.split(FILE_SEPARATOR)
    assert len(parts) == 2
    assert any("File: file1.txt\nContent:\n```txt\nContent of file1\n```\n" in p for p in parts)
    assert any("File: file2.py\nContent:\n```py\nprint('Hello')\n```\n" in p for p in parts)

    assert token_counts[0] > 0
    assert not errors_list


def test_generate_list_content_with_missing_file(temp_repo, mock_gui):
    temp_dir, _, _, missing_path = temp_repo
    files_to_copy = {missing_path}
    lock = threading.Lock()
    from lru_cache import ThreadSafeLRUCache
    content_cache = ThreadSafeLRUCache(100, 10)

    generated_contents = []
    errors_list = []
    deleted_list = []
    done = threading.Event()

    def completion_callback(content, token_count, errors, deleted_files=None):
        generated_contents.append(content)
        errors_list.extend(errors)
        if deleted_files:
            deleted_list.extend(deleted_files)
        done.set()

    generate_list_content(mock_gui, files_to_copy, temp_dir, lock, completion_callback, content_cache)

    assert done.wait(timeout=2)

    assert generated_contents[0] == ""
    assert deleted_list or (errors_list and "Not Found: " in errors_list[0])


def test_generate_list_content_threading(mock_gui):
    with patch("file_list_handler.start_content_generation") as mock_start:
        from lru_cache import ThreadSafeLRUCache

        generate_list_content(
            mock_gui,
            set(),
            "",
            threading.Lock(),
            lambda *a: None,
            ThreadSafeLRUCache(100, 10),
        )

        mock_start.assert_called_once()
