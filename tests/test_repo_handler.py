# tests/test_repo_handler.py
import os
import pytest
from unittest.mock import MagicMock, patch, ANY
import tkinter as tk
from tkinter import messagebox
from handlers.repo_handler import RepoHandler
from widgets import FolderDialog
from constants import LEGENDARY_GOLD

@pytest.fixture
def mock_gui():
    gui = MagicMock()
    gui.is_loading = False
    gui.current_repo_path = None
    gui.header_frame = MagicMock(
        repo_prefix_label=MagicMock(),
        repo_name_label=MagicMock(),
        LEGENDARY_GOLD=LEGENDARY_GOLD
    )
    gui.structure_tab = MagicMock()
    gui.structure_tab.tree = MagicMock(get_children=MagicMock(return_value=["root"]))
    gui.structure_tab.populate_tree = MagicMock()
    gui.structure_tab.apply_initial_expansion = MagicMock()
    gui.show_status_message = MagicMock()
    gui.show_loading_state = MagicMock()
    gui.hide_loading_state = MagicMock()
    gui.trigger_preview_update = MagicMock()
    gui.refresh_button = MagicMock()
    gui.copy_structure_button = MagicMock()
    gui.copy_button = MagicMock()
    gui.copy_all_button = MagicMock()
    gui.root = MagicMock(after=MagicMock(side_effect=lambda delay, func, *args: func(*args)))
    
    def settings_get_side_effect(section, key, default=None):
        if section == 'repo':
            return {}
        return 1
    gui.settings.get = MagicMock(side_effect=settings_get_side_effect)
    
    gui.update_recent_folders = MagicMock()
    gui.content_tab = MagicMock(clear=MagicMock())
    gui.file_list_tab = MagicMock(clear=MagicMock())
    gui.info_label = MagicMock()
    return gui

@pytest.fixture
def repo_handler(mock_gui):
    return RepoHandler(mock_gui)

def test_select_repo_loading(repo_handler, mock_gui):
    mock_gui.is_loading = True
    repo_handler.select_repo()
    mock_gui.show_status_message.assert_called_with("Loading...", error=True)

def test_select_repo_cancelled(repo_handler, mock_gui):
    mock_gui.is_loading = False
    with patch('handlers.repo_handler.FolderDialog') as mock_dialog:
        mock_dialog.return_value.show.return_value = None
        repo_handler.select_repo()
        mock_gui.show_status_message.assert_not_called()  # No message for cancel

def test_select_repo_success(repo_handler, mock_gui):
    mock_gui.is_loading = False
    with patch('handlers.repo_handler.FolderDialog') as mock_dialog:
        mock_dialog.return_value.show.return_value = "/selected"
        with patch.object(repo_handler, '_clear_internal_state') as mock_clear, \
             patch.object(repo_handler, 'load_repo') as mock_load:
            repo_handler.select_repo()
            mock_gui.update_recent_folders.assert_called_with("/selected")
            mock_clear.assert_called_with(clear_ui=True)
            mock_gui.show_loading_state.assert_called_with("Scanning selected...", show_cancel=True)
            mock_load.assert_called_with("/selected", mock_gui.show_status_message, repo_handler._handle_load_completion)

def test_refresh_repo_no_path(repo_handler, mock_gui):
    mock_gui.current_repo_path = None
    repo_handler.refresh_repo()
    mock_gui.show_status_message.assert_called_with("No repository loaded to refresh.", error=True)

def test_refresh_repo_success(repo_handler, mock_gui):
    mock_gui.current_repo_path = "/repo"
    repo_handler.repo_path = "/repo"  # Set for basename
    with patch.object(repo_handler, 'get_tree_expansion_state', return_value=set()), \
         patch.object(mock_gui.file_handler.content_cache, 'clear'), \
         patch.object(repo_handler, 'load_repo') as mock_load:
        repo_handler.refresh_repo()
        mock_gui.show_loading_state.assert_called_with("Refreshing repo...", show_cancel=True)
        mock_load.assert_called_with("/repo", mock_gui.show_status_message, ANY)  # The lambda for refresh_completion

def test_handle_load_completion_success(repo_handler, mock_gui):
    scanned = set(["file1", "file2"])
    loaded = set(["file1"])
    ignore_patterns = [".git"]
    repo_handler._handle_load_completion("/repo", ignore_patterns, scanned, loaded, [])
    mock_gui.hide_loading_state.assert_called_once()
    assert repo_handler.repo_path == "/repo"
    assert mock_gui.current_repo_path == "/repo"
    assert mock_gui.file_handler.repo_path == "/repo"
    assert mock_gui.file_handler.ignore_patterns == ignore_patterns
    assert mock_gui.file_handler.scanned_text_files == scanned
    assert mock_gui.file_handler.loaded_files == loaded
    mock_gui.file_handler.content_cache.clear.assert_called_once()
    mock_gui.file_handler.read_errors.clear.assert_called_once()
    mock_gui.header_frame.repo_name_label.config.assert_called_with(text="repo", foreground=LEGENDARY_GOLD)
    mock_gui.refresh_button.config.assert_called_with(state=tk.NORMAL)
    mock_gui.structure_tab.populate_tree.assert_called_with("/repo")
    mock_gui.structure_tab.apply_initial_expansion.assert_called_once()
    mock_gui.copy_structure_button.config.assert_called_with(state=tk.NORMAL)
    mock_gui.trigger_preview_update.assert_called_once()
    mock_gui.show_status_message.assert_called_with("Loaded repo successfully.", duration=5000)

def test_handle_refresh_completion_success(repo_handler, mock_gui):
    from path_utils import normalize_for_cache
    scanned = set(["/repo/file1", "/repo/file2", "/repo/new_file"])
    previous = set(["/repo/file1"])
    expansion = set(["/repo/dir"])
    
    repo_handler._handle_refresh_completion("/repo", [".git"], scanned, [], previous, expansion)
    
    mock_gui.hide_loading_state.assert_called_once()
    # Should now select ALL scanned files, normalized
    expected_loaded = {normalize_for_cache(f) for f in scanned}
    assert mock_gui.file_handler.loaded_files == expected_loaded
    mock_gui.structure_tab.populate_tree.assert_called_with("/repo")
    mock_gui.trigger_preview_update.assert_called_once()
    mock_gui.header_frame.repo_name_label.config.assert_called_with(foreground=LEGENDARY_GOLD)

def test_handle_load_completion_errors(repo_handler, mock_gui):
    with patch('tkinter.messagebox.showerror') as mock_error:
        repo_handler._handle_load_completion(None, None, set(), set(), ["error1"])
        mock_gui.hide_loading_state.assert_called_once()
        mock_gui.show_status_message.assert_called_with(ANY, error=True, duration=10000)
        mock_error.assert_called_with("Load Error", ANY)
        assert repo_handler.repo_path is None  # Cleared

def test_clear_internal_state(repo_handler, mock_gui):
    with patch.object(repo_handler, '_update_ui_for_no_repo') as mock_update_ui:
        repo_handler._clear_internal_state(clear_ui=True, clear_recent=False)
        assert repo_handler.repo_path is None
        assert len(repo_handler.loaded_files) == 0
        assert len(repo_handler.scanned_text_files) == 0
        assert repo_handler.ignore_patterns == []
        assert repo_handler.content_cache.size() == 0
        assert len(repo_handler.read_errors) == 0
        assert mock_gui.current_repo_path is None
        mock_update_ui.assert_called_once()

def test_update_ui_for_no_repo(repo_handler, mock_gui):
    repo_handler._update_ui_for_no_repo()
    mock_gui.header_frame.repo_name_label.config.assert_called_with(text="None", foreground=LEGENDARY_GOLD)
    mock_gui.info_label.config.assert_called_with(text="Token Count: 0")
    mock_gui.structure_tab.clear.assert_called_once()
    mock_gui.content_tab.clear.assert_called_once()
    mock_gui.file_list_tab.clear.assert_called_once()
    mock_gui.refresh_button.config.assert_called_with(state=tk.DISABLED)
    mock_gui.copy_structure_button.config.assert_called_with(state=tk.DISABLED)
    mock_gui.copy_button.config.assert_called_with(state=tk.DISABLED)
    mock_gui.copy_all_button.config.assert_called_with(state=tk.DISABLED)
    assert mock_gui.current_token_count == 0