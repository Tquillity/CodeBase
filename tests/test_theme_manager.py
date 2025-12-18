import tkinter as tk
import pytest
from unittest.mock import MagicMock, patch, ANY
from handlers.theme_manager import ThemeManager
from colors import COLOR_BG, COLOR_FG, COLOR_HC_BG, COLOR_HC_FG

@pytest.fixture
def mock_gui():
    gui = MagicMock()
    gui.root = MagicMock()  # Fully mock root

    # Mock IntVar behavior
    class MockIntVar:
        def __init__(self, value=0):
            self.value = value

        def get(self):
            return self.value

        def set(self, value):
            self.value = value

    gui.high_contrast_mode = MockIntVar()  # Use custom mock class for get/set

    gui.settings = MagicMock()
    # Assign mock objects to all widget attributes (unchanged)
    gui.header_frame = MagicMock()
    gui.title_label = MagicMock()
    gui.version_label = MagicMock()
    gui.repo_prefix_label = MagicMock()
    gui.repo_name_label = MagicMock()
    gui.header_separator = MagicMock()
    gui.left_separator = MagicMock()
    gui.left_frame = MagicMock()
    gui.right_frame = MagicMock()
    gui.info_label = MagicMock()
    gui.prepend_checkbox = MagicMock()
    gui.clear_button_frame = MagicMock()
    gui.select_button = MagicMock()
    gui.refresh_button = MagicMock()
    gui.copy_button = MagicMock()
    gui.copy_all_button = MagicMock()
    gui.copy_structure_button = MagicMock()
    gui.clear_button = MagicMock()
    gui.clear_all_button = MagicMock()
    gui.search_frame = MagicMock()
    gui.search_entry = MagicMock()
    gui.search_button = MagicMock()
    gui.next_button = MagicMock()
    gui.prev_button = MagicMock()
    gui.find_all_button = MagicMock()
    gui.case_sensitive_checkbox = MagicMock()
    gui.whole_word_checkbox = MagicMock()
    gui.content_tab = MagicMock()
    gui.structure_tab = MagicMock()
    gui.base_prompt_tab = MagicMock()
    gui.settings_tab = MagicMock()
    gui.file_list_tab = MagicMock()
    gui.status_bar = MagicMock()
    return gui

@pytest.fixture
def theme_manager(mock_gui):
    tm = ThemeManager(mock_gui)
    tm.apply_theme()  # FIX: Call apply_theme in fixture to ensure colors dict is created
    return tm

def test_apply_theme_normal(theme_manager, mock_gui):
    mock_gui.high_contrast_mode.set(0)
    theme_manager.apply_theme()
    assert mock_gui.colors['bg'] == COLOR_BG
    assert mock_gui.colors['fg'] == COLOR_FG

def test_apply_theme_high_contrast(theme_manager, mock_gui):
    mock_gui.high_contrast_mode.set(1)
    theme_manager.apply_theme()
    assert mock_gui.colors['bg'] == COLOR_HC_BG
    assert mock_gui.colors['fg'] == COLOR_HC_FG

def test_reconfigure_ui_colors(theme_manager, mock_gui):
    mock_gui.high_contrast_mode.set(0)
    theme_manager.apply_theme()  # Ensure colors are set before reconfigure
    with patch('tkinter.ttk.Style') as mock_style_cls:
        mock_style = mock_style_cls.return_value
        theme_manager.reconfigure_ui_colors()
        mock_gui.root.configure.assert_called_with(bg=COLOR_BG)
        mock_gui.header_frame.config.assert_called_with(bg=COLOR_BG)
        mock_gui.status_bar.config.assert_called_with(bg=COLOR_BG, fg=ANY)
        mock_gui.content_tab.reconfigure_colors.assert_called_with(mock_gui.colors)
        mock_style.configure.assert_any_call("Custom.TNotebook", background=COLOR_BG)