# tests/test_panels.py
import tkinter as tk
import pytest
from unittest.mock import MagicMock, patch
from panels.panels import HeaderFrame, LeftPanel, RightPanel
from constants import VERSION
import tkinter.ttk as ttk

@pytest.fixture
def mock_root():
    import ttkbootstrap as ttk
    root = ttk.Window()
    root.withdraw()
    yield root
    root.destroy()

@pytest.fixture
def mock_parent(mock_root):
    return tk.Frame(mock_root)

@pytest.fixture
def mock_gui(mock_root):
    gui = MagicMock()
    gui.colors = {
        'bg': '#fff', 'fg': '#000', 'bg_accent': '#eee', 'btn_bg': '#ddd', 'btn_fg': '#000', 
        'btn_hover': '#ccc', 'header': '#add8e6', 'status': '#f00',
        'folder': '#FFD700', 'file_selected': '#00FF00', 'file_unloaded': '#FF0000',
        'file_default': '#000', 'file_nontext': '#808080',
        'highlight_bg': '#FFFF00', 'highlight_fg': '#000000',
        'focused_highlight_bg': '#add8e6', 'focused_highlight_fg': '#000000'
    }
    
    def create_mock_button(parent, text, command, tooltip_text=None, state=tk.NORMAL):
        btn = MagicMock()
        config_dict = {'state': state}  # Store initial state and potentially other configs
        
        def config_side_effect(**kwargs):
            config_dict.update(kwargs)
        
        btn.config.side_effect = config_side_effect
        
        def cget_side_effect(key):
            return config_dict.get(key)
        
        btn.cget.side_effect = cget_side_effect
        
        # Mock bind to do nothing
        btn.bind.side_effect = lambda event, func, add=None: None
        
        return btn
    
    gui.create_button.side_effect = create_mock_button
    
    gui.repo_handler = MagicMock()
    gui.copy_handler = MagicMock()
    gui.search_handler = MagicMock()
    gui.prepend_var = tk.IntVar()
    gui.settings = MagicMock()
    gui.high_contrast_mode = tk.IntVar()
    gui.template_dir = "/templates"
    gui.show_unloaded_var = tk.IntVar()
    gui.file_handler = MagicMock()
    return gui

def test_header_frame_init(mock_parent, mock_gui):
    frame = HeaderFrame(mock_parent, title="CodeBase")
    assert frame.title_label.cget('text') == "CodeBase"
    assert frame.version_label.cget('text') == f"v{VERSION}"
    assert frame.repo_prefix_label.cget('text') == "Current Repo: "
    assert frame.repo_name_label.cget('text') == "None"

def test_left_panel_init(mock_parent, mock_gui):
    with patch('ttkbootstrap.Combobox'), \
         patch('ttkbootstrap.Checkbutton'):
        panel = LeftPanel(mock_parent, mock_gui)
        assert panel.gui.select_button is not None
        assert panel.gui.refresh_button.cget('state') == tk.DISABLED
        assert panel.gui.copy_button.cget('state') == tk.DISABLED

def test_right_panel_init(mock_parent, mock_gui):
    with patch('ttkbootstrap.Notebook'), \
         patch('ttkbootstrap.Checkbutton'), \
         patch('panels.panels.ContentTab'), \
         patch('panels.panels.StructureTab'), \
         patch('panels.panels.BasePromptTab'), \
         patch('panels.panels.SettingsTab'), \
         patch('panels.panels.FileListTab'):
        panel = RightPanel(mock_parent, mock_gui)
        assert panel.gui.search_entry is not None
        assert panel.gui.notebook is not None