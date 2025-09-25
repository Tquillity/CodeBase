# tests/test_file_list_tab.py
import tkinter as tk
from tkinter import scrolledtext
import pytest
from unittest.mock import MagicMock, patch, ANY
from tabs.file_list_tab import FileListTab
from file_list_handler import generate_list_content
from file_scanner import is_text_file

@pytest.fixture
def mock_gui():
    gui = MagicMock()
    gui.colors = {'bg': '#fff', 'fg': '#000', 'bg_accent': '#eee', 'btn_bg': '#ddd', 'btn_fg': '#000', 'status': '#f00', 'btn_hover': '#ccc'}
    gui.create_button = MagicMock(side_effect=[MagicMock() for _ in range(3)])  # For load, copy, and clear buttons
    gui.is_loading = False
    gui.current_repo_path = "/repo"
    gui.list_selected_files = set()
    gui.list_read_errors = []
    gui.show_status_message = MagicMock()
    gui.show_loading_state = MagicMock()
    gui.prepend_var = MagicMock(get=MagicMock(return_value=1))
    gui.base_prompt_tab = MagicMock(base_prompt_text=MagicMock(get=MagicMock(return_value="Prompt")))
    gui.copy_handler = MagicMock()
    gui.file_handler = MagicMock(lock=MagicMock(), content_cache={}, read_errors=[])
    return gui

@pytest.fixture
def file_list_tab(mock_gui):
    parent = MagicMock()
    # Patch ScrolledText at the class level
    with patch('tkinter.scrolledtext.ScrolledText') as mock_scrolled_text_cls:
        tab = FileListTab(parent, mock_gui)
        tab.file_list_text = mock_scrolled_text_cls.return_value
        tab.error_label = MagicMock()
        yield tab

def test_setup_ui(mock_gui):
    parent = MagicMock()
    with patch('tkinter.scrolledtext.ScrolledText'):
        tab = FileListTab(parent, mock_gui)
        assert tab.file_list_text is not None
        assert tab.load_list_button is not None

def test_reconfigure_colors(file_list_tab, mock_gui):
    new_colors = {'bg': '#aaa', 'bg_accent': '#ccc', 'fg': '#111', 'btn_bg': '#bbb', 'btn_fg': '#222', 'status': '#e00'}
    file_list_tab.reconfigure_colors(new_colors)
    file_list_tab.file_list_text.config.assert_called_with(bg='#ccc', fg='#111')
    file_list_tab.error_label.config.assert_called_with(bg='#aaa', fg='#e00')

def test_perform_search(file_list_tab):
    file_list_tab.file_list_text.search.side_effect = ["1.0", "2.0", ""]
    matches = file_list_tab.perform_search("query", case_sensitive=False, whole_word=False)
    assert matches == [("1.0", "1.0+5c"), ("2.0", "2.0+5c")]

def test_highlight_all_matches(file_list_tab):
    matches = [("1.0", "1.5")]
    file_list_tab.highlight_all_matches(matches)
    file_list_tab.file_list_text.tag_add.assert_called_with("highlight", "1.0", "1.5")

def test_highlight_match(file_list_tab):
    match_data = ("1.0", "1.5")
    file_list_tab.highlight_match(match_data, is_focused=True)
    file_list_tab.file_list_text.tag_add.assert_called_with("focused_highlight", "1.0", "1.5")

def test_center_match(file_list_tab):
    match_data = ("5.0", "5.5")
    file_list_tab.file_list_text.see = MagicMock()
    file_list_tab.file_list_text.dlineinfo = MagicMock(return_value=(0, 100, 0, 20, 0))
    file_list_tab.file_list_text.winfo_height = MagicMock(return_value=400)
    file_list_tab.file_list_text.index = MagicMock(side_effect=["100.0", "5.0"])
    file_list_tab.file_list_text.yview_moveto = MagicMock()
    file_list_tab.center_match(match_data)
    file_list_tab.file_list_text.yview_moveto.assert_called_with(ANY)

def test_clear_highlights(file_list_tab):
    file_list_tab.clear_highlights()
    file_list_tab.file_list_text.tag_remove.assert_any_call("highlight", "1.0", tk.END)
    file_list_tab.file_list_text.tag_remove.assert_any_call("focused_highlight", "1.0", tk.END)

def test_clear(file_list_tab, mock_gui):
    file_list_tab.clear()
    file_list_tab.file_list_text.delete.assert_called_with("1.0", tk.END)
    assert len(mock_gui.list_selected_files) == 0
    file_list_tab.error_label.config.assert_called_with(text="")

def test_load_file_list_success(file_list_tab, mock_gui, monkeypatch):
    file_list_tab.file_list_text.get.return_value = "file1.txt\nfile2.txt"
    monkeypatch.setattr('os.path.isfile', lambda p: True)
    monkeypatch.setattr('tabs.file_list_tab.is_text_file', lambda p, g: True)
    file_list_tab.load_file_list()
    assert len(mock_gui.list_selected_files) == 2
    mock_gui.show_status_message.assert_called_with("Loaded 2 files from list.")