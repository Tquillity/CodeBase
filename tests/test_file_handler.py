# tests/test_file_handler.py
import os
import tempfile
import tkinter as tk
import threading
import pytest
from unittest.mock import MagicMock, patch, ANY
from file_handler import FileHandler
from file_scanner import is_text_file, is_ignored_path

# Mock GUI class for FileHandler
class MockGUI:
    def __init__(self):
        # Create a mock for structure_tab that itself has a mock for tree
        self.structure_tab = MagicMock()
        self.structure_tab.tree = MagicMock()
        self.structure_tab.update_tree_strikethrough = MagicMock()

        self.settings = MagicMock()
        self.settings.get.side_effect = lambda sec, key, default=None: default if key != 'text_extensions' else {}
        self.root = MagicMock()
        self.trigger_preview_update = MagicMock()
        self.load_recent_folders = MagicMock(return_value=[])

@pytest.fixture
def mock_gui():
    return MockGUI()

@pytest.fixture
def file_handler(mock_gui):
    # Initialize FileHandler with the more detailed MockGUI
    fh = FileHandler(mock_gui)
    # Since the mock tree is on a nested mock, we can alias it for easier access in tests
    fh.gui.tree = fh.gui.structure_tab.tree
    return fh


@pytest.fixture
def temp_repo():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create directory structure
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

def test_get_extension_groups():
    groups = FileHandler.get_extension_groups()
    assert isinstance(groups, dict)
    assert "Programming Languages" in groups
    assert ".py" in groups["Programming Languages"]
    assert len(groups["Other"]) >= 0  # May vary

def test_populate_tree(file_handler, temp_repo):
    temp_dir, *_ = temp_repo
    file_handler.repo_path = temp_dir
    file_handler.populate_tree(temp_dir)
    # Check that the tree's insert method was called, indicating population started
    file_handler.gui.tree.insert.assert_called()

def test_build_tree_level(file_handler, temp_repo, monkeypatch):
    temp_dir, sub_dir, file1_path, file2_path, nontext_path = temp_repo
    file_handler.repo_path = temp_dir
    file_handler.ignore_patterns = []
    parent_id = "parent"

    # Mock is_ignored_path and is_text_file
    monkeypatch.setattr("file_handler.is_ignored_path", lambda *args, **kwargs: False)
    monkeypatch.setattr("file_handler.is_text_file", lambda p, g: p.endswith(".txt") or p.endswith(".py"))

    file_handler.build_tree_level(temp_dir, parent_id, selected=True)

    # Check inserts
    calls = file_handler.gui.tree.insert.call_args_list
    assert any("📁 sub" in call.kwargs['text'] for call in calls)
    assert any("📄 file1.txt" in call.kwargs['text'] for call in calls)
    # file2.py is in a subdirectory, so it should not be inserted at the top level
    assert not any("file2.py" in call.kwargs['text'] for call in calls)
    assert any("❓ image.png" in call.kwargs['text'] for call in calls)


def test_expand_folder(file_handler, temp_repo):
    temp_dir, sub_dir, _, file2_path, _ = temp_repo
    file_handler.repo_path = temp_dir
    item_id = "item"

    # Set up the mock tree's item method to return different values based on input
    def item_side_effect(target_id, option=None, **kwargs):
        if target_id == "dummy_child":
            return {'tags': ('dummy',)}
        if target_id == item_id:
            if option == 'values':
                return [temp_dir, "☑"]
            return {'values': [temp_dir, "☑"], 'tags': ('folder',), 'text': "📁 root"}
        return {} # Default return for other calls

    file_handler.gui.tree.item.side_effect = item_side_effect
    file_handler.gui.tree.get_children.return_value = ["dummy_child"]
    file_handler.gui.tree.exists.return_value = True

    # Since expand_folder calls build_tree_level, we mock it to avoid its own complex dependencies
    with patch.object(file_handler, 'build_tree_level') as mock_build:
        file_handler.expand_folder(item_id)
        mock_build.assert_called_once_with(temp_dir, item_id, True)


def test_toggle_selection_folder(file_handler):
    event = MagicMock(x=10, y=10)
    file_handler.gui.tree.identify_region.return_value = "cell"
    file_handler.gui.tree.identify_column.return_value = "#2"
    item_id = "folder_item"
    file_handler.gui.tree.identify_row.return_value = item_id

    file_handler.gui.tree.item.return_value = {'values': ["path", "☑"], 'tags': ('folder',)}

    # Mock _update_folder_selection_recursive to return True to indicate a change
    with patch.object(file_handler, '_update_folder_selection_recursive', return_value=True):
        file_handler.toggle_selection(event)

    # Check that the item's state was toggled in the Treeview
    file_handler.gui.tree.item.assert_any_call(item_id, values=("path", "☐"))
    # Check that the preview update was triggered
    file_handler.gui.trigger_preview_update.assert_called_once()

def test_generate_folder_structure_text(file_handler, temp_repo):
    temp_dir, sub_dir, file1_path, file2_path, _ = temp_repo
    file_handler.repo_path = temp_dir
    root_id = "root"
    file_handler.gui.settings.get.return_value = 1  # include_icons

    # Mock the tree structure
    def mock_get_children(iid=""):
        if iid == "": return [root_id]
        if iid == root_id: return ["file1", "sub_id"]
        if iid == "sub_id": return ["file2"]
        return []

    file_handler.gui.tree.get_children.side_effect = mock_get_children

    def mock_item(iid, **kwargs):
        items = {
            root_id: {'text': "📁 root", 'tags': ('folder',), 'values': ['path/root', '☑']},
            "file1": {'text': "📄 file1.txt", 'tags': ('file_selected',), 'values': ['path/file1.txt', '☑']},
            "sub_id": {'text': "📁 sub", 'tags': ('folder',), 'values': ['path/sub', '☑']},
            "file2": {'text': "📄 file2.py", 'tags': ('file_selected',), 'values': ['path/sub/file2.py', '☑']},
        }
        return items.get(iid)

    file_handler.gui.tree.item.side_effect = mock_item

    structure = file_handler.generate_folder_structure_text()
    lines = structure.splitlines()
    assert "📁 root" in lines[0]
    assert "├── 📄 file1.txt" in structure
    assert "└── 📁 sub" in structure
    assert "    └── 📄 file2.py" in structure