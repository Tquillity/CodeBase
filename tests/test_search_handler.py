# tests/test_search_handler.py
import tkinter as tk
import pytest
from unittest.mock import MagicMock, patch
from handlers.search_handler import SearchHandler

@pytest.fixture
def mock_gui():
    gui = MagicMock()
    gui.search_var = MagicMock(get=MagicMock(return_value="query"))
    gui.case_sensitive_var = MagicMock(get=MagicMock(return_value=0))
    gui.whole_word_var = MagicMock(get=MagicMock(return_value=0))
    gui.notebook = MagicMock(index=MagicMock(return_value=0), select=MagicMock(return_value="tab0"))
    gui.content_tab = MagicMock(perform_search=MagicMock(return_value=[("1.0", "1.5")]))
    gui.structure_tab = MagicMock()
    gui.base_prompt_tab = MagicMock()
    gui.settings_tab = MagicMock()
    gui.file_list_tab = MagicMock()
    gui.match_positions = {}
    gui.current_match_index = {}
    gui.show_status_message = MagicMock()
    return gui

@pytest.fixture
def search_handler(mock_gui):
    return SearchHandler(mock_gui)

def test_search_tab_success(search_handler, mock_gui):
    search_handler.search_tab()
    assert mock_gui.match_positions[0] == [("1.0", "1.5")]
    assert mock_gui.current_match_index[0] == 0
    mock_gui.show_status_message.assert_called_with("Found 1 match(es).")

def test_search_tab_no_matches(search_handler, mock_gui):
    mock_gui.content_tab.perform_search.return_value = []
    search_handler.search_tab()
    mock_gui.show_status_message.assert_called_with("Search found nothing.")

def test_next_match(search_handler, mock_gui):
    mock_gui.match_positions[0] = [("1.0", "1.5"), ("2.0", "2.5")]
    mock_gui.current_match_index[0] = 0
    search_handler.next_match()
    assert mock_gui.current_match_index[0] == 1

def test_prev_match(search_handler, mock_gui):
    mock_gui.match_positions[0] = [("1.0", "1.5"), ("2.0", "2.5")]
    mock_gui.current_match_index[0] = 1
    search_handler.prev_match()
    assert mock_gui.current_match_index[0] == 0

def test_find_all_success(search_handler, mock_gui):
    mock_gui.content_tab.perform_search.return_value = [("1.0", "1.5")]
    search_handler.find_all()
    mock_gui.show_status_message.assert_called_with("Highlighted 1 match(es).")
    mock_gui.content_tab.highlight_all_matches.assert_called_with([("1.0", "1.5")])

def test_clear_search_highlights(search_handler, mock_gui):
    search_handler._clear_search_highlights(0)
    mock_gui.content_tab.clear_highlights.assert_called_once()

def test_highlight_match(search_handler, mock_gui):
    mock_gui.match_positions[0] = [("1.0", "1.5")]
    search_handler._highlight_match(0, 0, is_focused=True)
    mock_gui.content_tab.highlight_match.assert_called_with(("1.0", "1.5"), True)