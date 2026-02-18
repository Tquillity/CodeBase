# tests/test_file_scanner.py
from __future__ import annotations

import logging
import os
import tempfile
import threading
import time
from typing import cast

import pytest
from unittest.mock import MagicMock, patch, ANY

from file_scanner import scan_repo, parse_gitignore, is_ignored_path, is_text_file

@pytest.fixture
def temp_repo():
    """Fixture to create a temporary repository with sample files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        sub_dir = os.path.join(temp_dir, "sub")
        os.mkdir(sub_dir)

        file1_path = os.path.join(temp_dir, "file1.txt")
        with open(file1_path, 'w') as f:
            f.write("Text")

        file2_path = os.path.join(sub_dir, "file2.py")
        with open(file2_path, 'w') as f:
            f.write("Code")

        nontext_path = os.path.join(temp_dir, "image.png")
        with open(nontext_path, 'wb') as f:
            f.write(b'\x89PNG')

        yield temp_dir, sub_dir, file1_path, file2_path, nontext_path

def test_parse_gitignore_with_comments_and_empty_lines():
    with tempfile.TemporaryDirectory() as temp_dir:
        gitignore_path = os.path.join(temp_dir, ".gitignore")
        gitignore_content = """
# This is a comment and should be ignored
*.log
node_modules/

# Another comment
build/
"""
        with open(gitignore_path, "w") as f:
            f.write(gitignore_content)

        patterns = parse_gitignore(gitignore_path)

    expected = ['.git', '*.log', 'node_modules/', 'build/']
    assert sorted(patterns) == sorted(expected)

def test_parse_gitignore_non_existent_file():
    non_existent_path = "/path/that/definitely/does/not/exist/.gitignore"
    patterns = parse_gitignore(non_existent_path)
    assert patterns == ['.git']

def test_parse_gitignore_empty_file():
    with tempfile.TemporaryDirectory() as temp_dir:
        gitignore_path = os.path.join(temp_dir, ".gitignore")
        with open(gitignore_path, "w") as f:
            f.write("")

        patterns = parse_gitignore(gitignore_path)
        assert patterns == ['.git']

def test_parse_gitignore_with_only_comments():
    with tempfile.TemporaryDirectory() as temp_dir:
        gitignore_path = os.path.join(temp_dir, ".gitignore")
        with open(gitignore_path, "w") as f:
            f.write("# Comment\n# Another")

        patterns = parse_gitignore(gitignore_path)
        assert patterns == ['.git']

def test_is_ignored_path_gitignore_patterns(monkeypatch):
    repo_root = "/repo"
    ignore_list = ['.git', '*.log', 'node_modules/']
    gui = MagicMock()  # Mock gui for settings
    gui.settings.get.side_effect = lambda sec, key, default: 0 if key in ['exclude_node_modules', 'exclude_dist'] else default

    def mock_isdir(p):
        return 'node_modules' in p  # True for dir
    monkeypatch.setattr('os.path.isdir', mock_isdir)

    assert is_ignored_path(os.path.join(repo_root, ".git"), repo_root, ignore_list, gui) == True
    assert is_ignored_path(os.path.join(repo_root, "file.log"), repo_root, ignore_list, gui) == True
    assert is_ignored_path(os.path.join(repo_root, "node_modules"), repo_root, ignore_list, gui) == True
    assert is_ignored_path(os.path.join(repo_root, "src", "code.py"), repo_root, ignore_list, gui) == False

def test_is_ignored_path_directory_patterns_match_nested_files(monkeypatch):
    """Test that directory patterns like .next/ or node_modules/ match files inside those directories."""
    repo_root = "/repo"
    ignore_list = ['.next/', 'node_modules/', 'build/', 'dist/']
    gui = MagicMock()
    gui.settings.get.side_effect = lambda sec, key, default: 0 if key in ['exclude_node_modules', 'exclude_dist'] else default

    # Files inside ignored directories should be ignored
    assert is_ignored_path(os.path.join(repo_root, "apps", "web", ".next", "dev", "static", "chunks", "file.js"), repo_root, ignore_list, gui) == True
    assert is_ignored_path(os.path.join(repo_root, "node_modules", "some-package", "index.js"), repo_root, ignore_list, gui) == True
    assert is_ignored_path(os.path.join(repo_root, "build", "output", "app.js"), repo_root, ignore_list, gui) == True
    assert is_ignored_path(os.path.join(repo_root, "dist", "bundle.js"), repo_root, ignore_list, gui) == True
    
    # Files outside ignored directories should not be ignored
    assert is_ignored_path(os.path.join(repo_root, "src", "code.js"), repo_root, ignore_list, gui) == False
    assert is_ignored_path(os.path.join(repo_root, "apps", "web", "src", "page.tsx"), repo_root, ignore_list, gui) == False

def test_is_ignored_path_settings_excludes(monkeypatch):
    repo_root = "/repo"
    ignore_list: list[str] = []
    gui = MagicMock()
    gui.settings.get.side_effect = lambda sec, key, default: 1 if key in ['exclude_node_modules', 'exclude_dist'] else default

    assert is_ignored_path("/repo/node_modules/pkg", repo_root, ignore_list, gui) == True
    assert is_ignored_path("/repo/dist/build.js", repo_root, ignore_list, gui) == True
    assert is_ignored_path("/repo/src/code.py", repo_root, ignore_list, gui) == False

def test_is_text_file_extensions():
    gui = MagicMock()
    gui.settings.get.side_effect = lambda sec, key, default: cast("dict[str, int]", {}) if key == 'exclude_files' else {'.txt': 1, '.py': 1, '.bin': 0}

    with patch('os.path.getsize', return_value=100):
        assert is_text_file("file.txt", gui) == True
        assert is_text_file("code.py", gui) == True
        assert is_text_file("data.bin", gui) == False  # Explicitly disabled
        assert is_text_file("image.png", gui) == False  # Not in text extensions

def test_is_text_file_mime_type(monkeypatch):
    gui = MagicMock()
    gui.settings.get.side_effect = lambda sec, key, default: cast("dict[str, int]", {}) if key == 'exclude_files' else cast("dict[str, int]", {})
    
    def mock_guess_type(path):
        if path.endswith(".md"):
            return "text/markdown", None
        return None, None

    monkeypatch.setattr("mimetypes.guess_type", mock_guess_type)

    with patch('os.path.getsize', return_value=100):
        assert is_text_file("readme.md", gui) == True
        assert is_text_file("image.jpg", gui) == False

def test_is_text_file_exclude_files():
    gui = MagicMock()
    gui.settings.get.side_effect = lambda sec, key, default: {'.txt': 1} if key == 'text_extensions' else {'package-lock.json': 1} if key == 'exclude_files' else default

    with patch('os.path.getsize', return_value=100):
        assert is_text_file("package-lock.json", gui) == False  # Excluded by name
        assert is_text_file("notes.txt", gui) == True

def test_is_text_file_binary_extensions():
    gui = MagicMock()
    # Mock settings.get to return an empty dict for text_extensions so it falls through to ext check
    gui.settings.get.side_effect = lambda sec, key, default: cast("dict[str, int]", {}) if key == 'text_extensions' else cast("dict[str, int]", {})
    
    with patch('os.path.getsize', return_value=100):
        # These should be rejected even if text_extensions says they are text, or if they bypass MIME check
        assert is_text_file("binary.so", gui) == False
        assert is_text_file("data.bin", gui) == False
        assert is_text_file("lib.dylib", gui) == False

def test_is_text_file_size_limit():
    from constants import MAX_FILE_SIZE
    gui = MagicMock()
    gui.settings.get.side_effect = lambda sec, key, default: {'.txt': 1} if key == 'text_extensions' else cast("dict[str, int]", {})
    
    with patch('os.path.getsize', return_value=MAX_FILE_SIZE + 1):
        assert is_text_file("large.txt", gui) == False
    
    with patch('os.path.getsize', return_value=MAX_FILE_SIZE - 1):
        assert is_text_file("small.txt", gui) == True

def test_is_ignored_path_venv(monkeypatch):
    repo_root = "/repo"
    ignore_list: list[str] = []
    gui = MagicMock()
    gui.settings.get.side_effect = lambda sec, key, default: 0 # Disable other ignores
    
    assert is_ignored_path("/repo/venv/lib/python.py", repo_root, ignore_list, gui) == True
    assert is_ignored_path("/repo/env/bin/activate", repo_root, ignore_list, gui) == True
    assert is_ignored_path("/repo/ENV/settings.ini", repo_root, ignore_list, gui) == True
    assert is_ignored_path("/repo/src/main.py", repo_root, ignore_list, gui) == False

def test_scan_repo_success(caplog, temp_repo, monkeypatch):
    caplog.set_level(logging.INFO)
    temp_dir, sub_dir, file1_path, file2_path, nontext_path = temp_repo
    gui = MagicMock()
    progress_callback = MagicMock()
    completion_callback = MagicMock()

    # Mock root.after to execute immediately
    def mock_after(delay, func, *args):
        func(*args)

    gui.root.after.side_effect = mock_after

    # Mock is_ignored_path and is_text_file
    def mock_ignored(p, *args):
        return '.git' in p

    def mock_text(p, g):
        return p.endswith(".txt") or p.endswith(".py")

    def mock_commonpath(paths):
        return '/home/user/tmp'  # Starts with home
    monkeypatch.setattr('os.path.commonpath', mock_commonpath)
    monkeypatch.setattr('os.path.expanduser', lambda x: '/home/user')

    with patch('file_scanner.is_ignored_path', mock_ignored), \
         patch('file_scanner.is_text_file', mock_text), \
         patch('file_scanner.parse_gitignore', return_value=['.git']):

        scan_repo(temp_dir, gui, progress_callback, completion_callback, threading.Lock())

    # Check callback called with expected
    completion_callback.assert_called_once_with(os.path.abspath(temp_dir), ANY, ANY, ANY, [])
    args = completion_callback.call_args[0]
    assert args[0] == os.path.abspath(temp_dir)  # repo_path
    assert '.git' in args[1]  # ignore_patterns
    scanned = args[2]
    assert os.path.normpath(file1_path) in scanned
    assert os.path.normpath(file2_path) in scanned
    assert os.path.normpath(nontext_path) not in scanned
    loaded = args[3]
    assert scanned == loaded  # All text files loaded initially
    assert args[4] == []  # No errors

    assert "Scan complete" in caplog.text

def test_scan_repo_security_error():
    gui = MagicMock()
    completion_callback = MagicMock()
    forbidden_path = "/system/root"  # Outside user home

    # Mock root.after to execute immediately
    def mock_after(delay, func, *args):
        func(*args)

    gui.root.after.side_effect = mock_after

    with patch('os.path.expanduser', return_value="/home/user"), \
         patch('os.path.commonpath', return_value="/system"):

        scan_repo(forbidden_path, gui, MagicMock(), completion_callback, threading.Lock())

    completion_callback.assert_called_with(None, None, set(), set(), ["Security Error: Access outside user directory is not allowed."])

def test_scan_repo_exception(caplog):
    gui = MagicMock()
    completion_callback = MagicMock()

    # Mock root.after to execute immediately
    def mock_after(delay, func, *args):
        func(*args)

    gui.root.after.side_effect = mock_after

    with patch('os.path.expanduser', return_value="/home/user"), \
         patch('os.path.commonpath', return_value="/home/user"), \
         patch('os.walk', side_effect=Exception("Walk error")):

        scan_repo("/fake", gui, MagicMock(), completion_callback, threading.Lock())

    completion_callback.assert_called_with(None, None, set(), set(), [ANY])  # Unexpected error
    assert "Unexpected error during repository scan" in caplog.text