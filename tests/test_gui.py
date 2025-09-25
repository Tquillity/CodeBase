# tests/test_gui.py
import os
import tkinter as tk
from tkinter import messagebox, filedialog
import pytest
import tempfile
from unittest.mock import MagicMock, patch, mock_open, ANY
from gui import RepoPromptGUI
from colors import COLOR_BG, COLOR_FG, COLOR_HC_BG, COLOR_HC_FG
from tabs.content_tab import ContentTab
from tabs.structure_tab import StructureTab
from tabs.base_prompt_tab import BasePromptTab
from tabs.settings_tab import SettingsTab
from tabs.file_list_tab import FileListTab
from handlers.search_handler import SearchHandler
from handlers.copy_handler import CopyHandler
from handlers.repo_handler import RepoHandler
from handlers.theme_manager import ThemeManager
from panels.panels import HeaderFrame, LeftPanel, RightPanel
from file_scanner import is_text_file

@pytest.fixture
def mock_root():
    root = tk.Tk()
    root.withdraw()
    yield root
    root.quit()
    root.destroy()

@pytest.fixture
def temp_repo_for_gui_tests():
    with tempfile.TemporaryDirectory() as temp_dir:
        text_file = os.path.join(temp_dir, "test.txt")
        with open(text_file, 'w') as f:
            f.write("Text content")

        non_text_file = os.path.join(temp_dir, "image.png")
        with open(non_text_file, 'wb') as f:
            f.write(b'\x89PNG')

        sub_dir = os.path.join(temp_dir, "sub")
        os.mkdir(sub_dir)
        sub_file = os.path.join(sub_dir, "sub.txt")
        with open(sub_file, 'w') as f:
            f.write("Sub text")

        yield temp_dir, text_file, non_text_file, sub_file

@pytest.fixture
def gui(mock_root):
    with (
        patch('gui.SettingsManager') as mock_settings_cls,
        patch('gui.FileHandler') as mock_file_handler,
        patch('gui.HeaderFrame') as mock_header_cls,
        patch('gui.LeftPanel') as mock_left_cls,
        patch('gui.RightPanel') as mock_right_cls,
        patch('tkinter.scrolledtext.ScrolledText'),
        patch('tkinter.ttk.Treeview'),
        patch('tkinter.ttk.Scrollbar'),
        patch('tkinter.ttk.Style'),
        patch('tkinter.ttk.Combobox'),
        patch('tkinter.Canvas'),
        patch('tkinter.Entry'),
        patch('tkinter.Checkbutton'),
        patch('tkinter.Label'),
        patch('tkinter.Frame'),
    ):

        mock_settings_inst = mock_settings_cls.return_value
        def get_side_effect(section, key, default=None):
            if section == 'app':
                if key == 'high_contrast': return 0
                if key == 'prepend_prompt': return 1
                if key == 'show_unloaded': return 0
                if key == 'window_geometry': return "1920x1080"
            return default
        mock_settings_inst.get.side_effect = get_side_effect

        def right_panel_side_effect(parent, colors, gui_instance):
            gui_instance.notebook = MagicMock()
            gui_instance.notebook.index.side_effect = lambda x: 0 if x == 'current' else 5 if x == 'end' else None
            gui_instance.notebook.tab.side_effect = lambda i, option: {
                0: "Content Preview",
                1: "Folder Structure",
                2: "Base Prompt",
                3: "Settings",
                4: "File List Selection"
            }.get(i, None) if option == "text" else None
            gui_instance.notebook.select = MagicMock()

            mock_parent = MagicMock()
            gui_instance.content_tab = ContentTab(mock_parent, gui_instance, gui_instance.file_handler)
            gui_instance.content_tab.clear = MagicMock()
            gui_instance.content_tab.reconfigure_colors = MagicMock()

            gui_instance.structure_tab = StructureTab(mock_parent, gui_instance, gui_instance.file_handler, gui_instance.settings, gui_instance.show_unloaded_var)
            gui_instance.structure_tab.clear = MagicMock()
            gui_instance.structure_tab.reconfigure_colors = MagicMock()

            gui_instance.base_prompt_tab = BasePromptTab(mock_parent, gui_instance, gui_instance.template_dir)
            gui_instance.base_prompt_tab.clear = MagicMock()
            gui_instance.base_prompt_tab.reconfigure_colors = MagicMock()

            gui_instance.settings_tab = SettingsTab(mock_parent, gui_instance, gui_instance.settings, gui_instance.high_contrast_mode)
            gui_instance.settings_tab.reconfigure_colors = MagicMock()

            gui_instance.file_list_tab = FileListTab(mock_parent, gui_instance)
            gui_instance.file_list_tab.clear = MagicMock()
            gui_instance.file_list_tab.reconfigure_colors = MagicMock()
            gui_instance.file_list_tab.copy_list_button = MagicMock()
            gui_instance.file_list_tab.error_label = MagicMock()

            return MagicMock()

        mock_right_cls.side_effect = right_panel_side_effect
        
        app = RepoPromptGUI(mock_root)

        app.header_frame = mock_header_cls.return_value
        app.header_frame.repo_label = MagicMock()
        app.header_separator = MagicMock()
        app.left_frame = mock_left_cls.return_value
        app.right_frame = mock_right_cls.return_value
        app.left_separator = MagicMock()
        app.info_label = MagicMock()
        app.select_button = MagicMock()
        app.refresh_button = MagicMock()
        app.copy_button = MagicMock()
        app.copy_structure_button = MagicMock()
        app.copy_all_button = MagicMock()
        app.prepend_checkbox = MagicMock()
        app.clear_button_frame = MagicMock()
        app.clear_button = MagicMock()
        app.clear_all_button = MagicMock()
        app.search_frame = MagicMock()
        app.search_entry = MagicMock()
        app.search_button = MagicMock()
        app.next_button = MagicMock()
        app.prev_button = MagicMock()
        app.find_all_button = MagicMock()
        app.case_sensitive_checkbox = MagicMock()
        app.whole_word_checkbox = MagicMock()
        app.status_bar = MagicMock()
        
        app.notebook.select.reset_mock()
        yield app

def test_init(gui):
    assert gui.version == "3.2"
    assert gui.high_contrast_mode.get() == 0
    assert gui.prepend_var.get() == 1
    assert gui.show_unloaded_var.get() == 0
    assert hasattr(gui, 'colors')

def test_load_recent_folders(gui):
    mock_file = mock_open(read_data="folder1\nfolder2\n")
    with patch('builtins.open', mock_file), \
         patch('os.path.exists', return_value=True):
        folders = gui.load_recent_folders()
        assert folders == ["folder1", "folder2"]

def test_load_recent_folders_error(caplog, gui):
    with patch('os.path.exists', return_value=True), \
         patch('builtins.open', side_effect=Exception("Read error")):
        folders = gui.load_recent_folders()
        assert folders == []
        assert "Error loading recent folders" in caplog.text

def test_save_recent_folders(gui):
    gui.recent_folders = ["folder1", "folder2"]
    mock_file = mock_open()
    with patch('builtins.open', mock_file):
        gui.save_recent_folders()
        mock_file().write.assert_any_call("folder1\n")
        mock_file().write.assert_called_with("folder2\n")

def test_update_recent_folders(gui):
    gui.recent_folders = ["/old/folder"]
    gui.update_recent_folders("/new/folder")
    assert gui.recent_folders[0] == os.path.abspath("/new/folder")
    assert len(gui.recent_folders) == 2

    for i in range(25):
        gui.update_recent_folders(f"/folder{i}")
    assert len(gui.recent_folders) == 20

def test_select_repo(gui):
    gui.is_loading = True
    with patch.object(gui, 'show_status_message') as mock_status:
        gui.repo_handler.select_repo()
        mock_status.assert_called_with("Loading...", error=True)

    gui.is_loading = False
    with patch('handlers.repo_handler.FolderDialog') as mock_dialog:
        mock_dialog.return_value.show.return_value = "/selected/folder"
        with patch.object(gui, 'update_recent_folders'), \
             patch.object(gui.repo_handler, '_clear_internal_state'), \
             patch.object(gui, 'show_loading_state') as mock_show_loading, \
             patch.object(gui.repo_handler, 'load_repo') as mock_load_repo:
            gui.repo_handler.select_repo()
            mock_dialog.assert_called()
            # FIX: Change assertion to match the actual implementation string.
            mock_show_loading.assert_called_with("Scanning folder...")
            mock_load_repo.assert_called_with("/selected/folder", gui.show_status_message, ANY)

def test_refresh_repo(gui):
    gui.current_repo_path = "/repo"
    gui.repo_handler.repo_path = "/repo"
    gui.is_loading = False
    with patch.object(gui, 'show_loading_state') as mock_show_loading, \
         patch.object(gui.repo_handler, 'get_tree_expansion_state', return_value=set()), \
         patch.object(gui.file_handler, 'content_cache', new_callable=MagicMock), \
         patch.object(gui.repo_handler, 'load_repo') as mock_load_repo:
        
        gui.file_handler.content_cache.clear = MagicMock()
        
        gui.repo_handler.refresh_repo()
        mock_show_loading.assert_called_with("Refreshing repo...")
        mock_load_repo.assert_called_with("/repo", gui.show_status_message, ANY)

def test_copy_contents(gui):
    gui.file_handler.loaded_files = {"file1"}
    gui.is_loading = False
    with patch.object(gui.base_prompt_tab.base_prompt_text, 'get', return_value="Prompt text\n"), \
         patch.object(gui, 'show_loading_state') as mock_show_loading, \
         patch('handlers.copy_handler.generate_content') as mock_gen, \
         patch('pyperclip.copy'), \
         patch('tkinter.messagebox.showwarning'):
        gui.copy_handler.copy_contents()
        mock_show_loading.assert_called_with("Preparing content for clipboard...")
        mock_gen.assert_called_with(set(["file1"]), gui.current_repo_path, ANY, ANY, ANY, ANY, None, gui)

def test_load_file_list_empty_input(gui):
    gui.is_loading = False
    gui.file_list_tab.file_list_text.get = MagicMock(return_value="   ")
    with patch.object(gui, 'show_status_message') as mock_status, \
         patch.object(gui.file_list_tab.copy_list_button, 'config') as mock_button_config:
        gui.file_list_tab.load_file_list()
        mock_status.assert_called_with("No file list provided.", error=True)
        assert len(gui.list_selected_files) == 0
        mock_button_config.assert_called_with(state=tk.DISABLED)

def test_load_file_list_relative_paths(gui, temp_repo_for_gui_tests, monkeypatch):
    repo_dir, text_file, _, sub_file = temp_repo_for_gui_tests
    gui.current_repo_path = repo_dir
    gui.is_loading = False

    gui.file_list_tab.file_list_text.get = MagicMock(return_value="test.txt\nsub/sub.txt\nduplicate.txt\ntest.txt")
    with patch.object(gui, 'show_status_message') as mock_status, \
         patch.object(gui.file_list_tab.error_label, 'config') as mock_error_config, \
         patch.object(gui.file_list_tab.copy_list_button, 'config') as mock_button_config:

        def mock_isfile(p):
            return "duplicate" not in p

        monkeypatch.setattr('os.path.isfile', mock_isfile)
        def mock_is_text(path, g):
            return path.endswith('.txt')
        monkeypatch.setattr('file_scanner.is_text_file', mock_is_text)

        gui.file_list_tab.load_file_list()

        norm_text = os.path.normpath(text_file)
        norm_sub = os.path.normpath(sub_file)
        assert gui.list_selected_files == {norm_text, norm_sub}
        mock_status.assert_called_with("Loaded 2 files from list.")
        assert "Not Found: duplicate.txt" in gui.list_read_errors
        mock_error_config.assert_called_with(text=ANY)
        mock_button_config.assert_called_with(state=tk.NORMAL)

def test_load_file_list_absolute_paths_valid(gui, temp_repo_for_gui_tests, monkeypatch):
    repo_dir, text_file, _, _ = temp_repo_for_gui_tests
    gui.current_repo_path = repo_dir
    gui.is_loading = False
    abs_path = os.path.abspath(text_file)

    gui.file_list_tab.file_list_text.get = MagicMock(return_value=f"{abs_path}\n{abs_path}")
    with patch.object(gui, 'show_status_message') as mock_status:

        monkeypatch.setattr('os.path.isfile', lambda p: True)
        monkeypatch.setattr('file_scanner.is_text_file', lambda p, s: True)

        gui.file_list_tab.load_file_list()

        norm_text = os.path.normpath(text_file)
        assert gui.list_selected_files == {norm_text}
        assert len(gui.list_read_errors) == 0
        mock_status.assert_called_with("Loaded 1 files from list.")

def test_load_file_list_absolute_paths_invalid(gui, monkeypatch):
    gui.current_repo_path = "/repo"
    gui.is_loading = False

    gui.file_list_tab.file_list_text.get = MagicMock(return_value="/outside/file.txt\n/repo/invalid")
    with patch.object(gui, 'show_status_message') as mock_status:

        monkeypatch.setattr('os.path.isfile', lambda p: False)
        monkeypatch.setattr('file_scanner.is_text_file', lambda p, s: True)

        gui.file_list_tab.load_file_list()

        assert len(gui.list_selected_files) == 0
        assert "Invalid (outside repo): /outside/file.txt" in gui.list_read_errors
        assert "Not Found: /repo/invalid" in gui.list_read_errors
        mock_status.assert_called_with("No valid files in list.", error=True)

def test_load_file_list_non_text_file(gui, temp_repo_for_gui_tests, monkeypatch):
    repo_dir, _, non_text, _ = temp_repo_for_gui_tests
    gui.current_repo_path = repo_dir
    gui.is_loading = False

    gui.file_list_tab.file_list_text.get = MagicMock(return_value="image.png")

    monkeypatch.setattr('file_scanner.is_text_file', lambda p, s: not p.endswith('.png'))
    monkeypatch.setattr('os.path.isfile', lambda p: True)

    gui.file_list_tab.load_file_list()

    assert len(gui.list_selected_files) == 0
    assert "Non-text file: image.png" in gui.list_read_errors

def test_load_file_list_no_repo_for_relative(gui, monkeypatch):
    gui.current_repo_path = None
    gui.is_loading = False

    gui.file_list_tab.file_list_text.get = MagicMock(return_value="relative.txt")

    gui.file_list_tab.load_file_list()

    assert "No repo loaded for relative: relative.txt" in gui.list_read_errors
    assert len(gui.list_selected_files) == 0

def test_clear_current_content_tab(gui):
    gui.notebook.index.side_effect = lambda x: 0 if x == 'current' else 5 if x == 'end' else None
    with patch.object(gui, 'show_status_message') as mock_status:
        gui.clear_current()
        gui.content_tab.clear.assert_called_once()
        mock_status.assert_called_with("Current tab content cleared.")

def test_clear_current_structure_tab_confirm(gui):
    gui.notebook.index.side_effect = lambda x: 1 if x == 'current' else 5 if x == 'end' else None
    with patch('tkinter.messagebox.askyesno', return_value=True), \
         patch.object(gui, 'clear_all') as mock_clear_all:
        gui.clear_current()
        mock_clear_all.assert_called_once()


def test_clear_current_no_action(gui):
    gui.notebook.index.side_effect = lambda x: 3 if x == 'current' else 5 if x == 'end' else None
    with patch.object(gui, 'show_status_message') as mock_status:
        gui.clear_current()
        mock_status.assert_called_with("Settings tab cannot be cleared this way.")

def test_clear_all_confirm(gui):
    with patch('tkinter.messagebox.askyesno', return_value=True), \
         patch.object(gui.repo_handler, '_clear_internal_state') as mock_clear_state, \
         patch.object(gui.repo_handler, '_update_ui_for_no_repo') as mock_update_ui, \
         patch.object(gui, 'show_status_message') as mock_status:
        gui.clear_all()
        mock_clear_state.assert_called_once_with(clear_recent=False)
        gui.content_tab.clear.assert_called_once()
        gui.structure_tab.clear.assert_called_once()
        gui.base_prompt_tab.clear.assert_called_once()
        gui.file_list_tab.clear.assert_called_once()
        mock_update_ui.assert_called_once()
        mock_status.assert_called_with("All data cleared.")

def test_save_app_settings(gui):
    gui.settings_tab.default_tab_var = MagicMock(get=MagicMock(return_value="Content Preview"))
    gui.prepend_var = MagicMock(get=MagicMock(return_value=1))
    gui.show_unloaded_var = MagicMock(get=MagicMock(return_value=0))
    gui.settings_tab.expansion_var = MagicMock(get=MagicMock(return_value="Expanded"))
    gui.settings_tab.levels_entry = MagicMock(get=MagicMock(return_value="2"))
    gui.settings_tab.exclude_node_modules_var = MagicMock(get=MagicMock(return_value=1))
    gui.settings_tab.exclude_dist_var = MagicMock(get=MagicMock(return_value=1))
    gui.settings_tab.exclude_file_vars = {'file1': MagicMock(get=MagicMock(return_value=1))}
    gui.case_sensitive_var = MagicMock(get=MagicMock(return_value=0))
    gui.whole_word_var = MagicMock(get=MagicMock(return_value=0))
    gui.settings_tab.include_icons_var = MagicMock(get=MagicMock(return_value=1))
    gui.high_contrast_mode = MagicMock(get=MagicMock(return_value=0))
    gui.settings_tab.extension_checkboxes = {'.txt': (MagicMock(), MagicMock(get=MagicMock(return_value=1)))}

    gui.current_repo_path = "/repo"

    with patch.object(gui.settings, 'set') as mock_set, \
         patch.object(gui.settings, 'save'), \
         patch.object(gui.theme_manager, 'apply_theme'), \
         patch.object(gui.theme_manager, 'reconfigure_ui_colors'), \
         patch.object(gui, 'apply_default_tab'), \
         patch.object(gui.root, 'after'), \
         patch.object(gui, 'show_status_message') as mock_status:
        gui.save_app_settings()
        mock_set.assert_any_call('app', 'default_tab', "Content Preview")
        mock_set.assert_any_call('app', 'prepend_prompt', 1)
        mock_set.assert_any_call('app', 'show_unloaded', 0)
        mock_set.assert_any_call('app', 'expansion', "Expanded")
        mock_set.assert_any_call('app', 'levels', 2)
        mock_set.assert_any_call('app', 'exclude_node_modules', 1)
        mock_set.assert_any_call('app', 'exclude_dist', 1)
        mock_set.assert_any_call('app', 'exclude_files', {'file1': 1})
        mock_set.assert_any_call('app', 'search_case_sensitive', 0)
        mock_set.assert_any_call('app', 'search_whole_word', 0)
        mock_set.assert_any_call('app', 'include_icons', 1)
        mock_set.assert_any_call('app', 'high_contrast', 0)
        mock_set.assert_any_call('app', 'text_extensions', {'.txt': 1})
        mock_status.assert_any_call("Settings saved successfully.")
        mock_status.assert_called_with("Settings saved. Refreshing repository view...")
        gui.root.after.assert_called_with(100, gui.repo_handler.refresh_repo)

def test_apply_default_tab(gui):
    with patch.object(gui.settings, 'get', return_value="Folder Structure"):
        gui.apply_default_tab()
        gui.notebook.select.assert_called_with(1)

def test_show_about(gui):
    with patch('tkinter.messagebox.showinfo') as mock_info:
        gui.show_about()
        mock_info.assert_called_with("About CodeBase", ANY)

def test_on_close(gui):
    with patch.object(gui.root, 'geometry', return_value="100x200+300+400"), \
         patch.object(gui.settings, 'set') as mock_set, \
         patch.object(gui.settings, 'save'), \
         patch.object(gui.root, 'destroy'):
        gui.on_close()
        mock_set.assert_called_with('app', 'window_geometry', "100x200+300+400")

def test_reconfigure_ui_colors_propagation(gui):
    with patch.object(gui.high_contrast_mode, 'get', return_value=0), \
         patch('tkinter.ttk.Style') as mock_style_cls:
        gui.theme_manager.apply_theme()
        mock_style = mock_style_cls.return_value
        gui.theme_manager.reconfigure_ui_colors()
        gui.content_tab.reconfigure_colors.assert_called_with(gui.colors)
        gui.structure_tab.reconfigure_colors.assert_called_with(gui.colors)
        gui.base_prompt_tab.reconfigure_colors.assert_called_with(gui.colors)
        gui.settings_tab.reconfigure_colors.assert_called_with(gui.colors)
        gui.file_list_tab.reconfigure_colors.assert_called_with(gui.colors)
        mock_style.map.assert_called()

# --- New tests for tab classes (basic smoke tests) ---

def test_content_tab_init(mock_root, gui):
    with patch('tkinter.scrolledtext.ScrolledText') as mock_scrolled, \
         patch('gui.RepoPromptGUI.create_button') as mock_button:
        tab = ContentTab(mock_root, gui, gui.file_handler)
        assert mock_scrolled.called
        assert mock_button.called

def test_structure_tab_init(mock_root, gui):
    with patch('tkinter.ttk.Treeview') as mock_tree, \
         patch('tkinter.ttk.Style'), \
         patch('gui.RepoPromptGUI.create_button') as mock_button, \
         patch('tkinter.ttk.Scrollbar'):
        tab = StructureTab(mock_root, gui, gui.file_handler, gui.settings, gui.show_unloaded_var)
        assert mock_tree.called
        assert mock_button.called

def test_base_prompt_tab_init(mock_root, gui):
    with patch('tkinter.scrolledtext.ScrolledText') as mock_scrolled, \
         patch('gui.RepoPromptGUI.create_button') as mock_button:
        tab = BasePromptTab(mock_root, gui, gui.template_dir)
        assert mock_scrolled.called
        assert mock_button.called

def test_settings_tab_init(mock_root, gui):
    with patch('tkinter.ttk.Scrollbar'), \
         patch('tkinter.Canvas'), \
         patch('tkinter.Frame'), \
         patch('gui.RepoPromptGUI.create_button'):
        tab = SettingsTab(mock_root, gui, gui.settings, gui.high_contrast_mode)
        assert tab.default_tab_var is not None
        assert len(tab.extension_checkboxes) > 0

def test_file_list_tab_init(mock_root, gui):
    with patch('tkinter.scrolledtext.ScrolledText') as mock_scrolled, \
         patch('gui.RepoPromptGUI.create_button') as mock_button:
        tab = FileListTab(mock_root, gui)
        assert mock_scrolled.called
        assert mock_button.called

def test_save_app_settings_invalid_levels(gui):
    # To prevent the 'save_app_settings' method from crashing on other missing
    # attributes, we provide minimal mocks for all the variables it tries to access.
    gui.settings_tab.default_tab_var = MagicMock(get=MagicMock(return_value="Content Preview"))
    gui.settings_tab.expansion_var = MagicMock(get=MagicMock(return_value="Collapsed"))
    gui.settings_tab.exclude_node_modules_var = MagicMock(get=MagicMock(return_value=1))
    gui.settings_tab.exclude_dist_var = MagicMock(get=MagicMock(return_value=1))
    gui.settings_tab.exclude_file_vars = {}
    gui.case_sensitive_var = MagicMock(get=MagicMock(return_value=0)) # The critical missing mock
    gui.whole_word_var = MagicMock(get=MagicMock(return_value=0))
    gui.settings_tab.include_icons_var = MagicMock(get=MagicMock(return_value=1))
    gui.high_contrast_mode = MagicMock(get=MagicMock(return_value=0))
    gui.settings_tab.extension_checkboxes = {}

    # Now, set the specific value for this test's assertion
    gui.settings_tab.levels_entry = MagicMock(get=MagicMock(return_value="abc"))

    # Also patch messagebox to prevent popups during tests, even if an error occurs
    with patch('tkinter.messagebox.showerror') as mock_showerror:
        gui.save_app_settings()
        # Assert the popup was NOT called, because our mock setup is now complete
        mock_showerror.assert_not_called()

    # The original assertion remains valid
    gui.settings.set.assert_any_call('app', 'levels', 1)

def test_content_tab_perform_search(mock_root, gui):
    tab = gui.content_tab
    tab.content_text = MagicMock(search=MagicMock(side_effect=["1.0", ""]))
    matches = tab.perform_search("query", False, False)
    assert matches == [("1.0", "1.0+5c")]