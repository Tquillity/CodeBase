# tests/test_widgets.py
import tkinter as tk
from tkinter import ttk
from unittest.mock import MagicMock, patch, ANY
import pytest
from widgets import Tooltip, FolderDialog

@pytest.fixture
def mock_root():
    root = tk.Tk()
    root.withdraw()
    yield root
    root.quit()
    root.destroy()

def test_tooltip_show_hide(mock_root):
    widget = tk.Button(mock_root, text="Hover me")
    tooltip = Tooltip(widget, "Tip text", delay=100)
    tooltip.schedule_show()  # Trigger enter (schedules after)
    # Manually trigger the scheduled show (bypasses delay in test env)
    tooltip.show_tip()
    assert tooltip.tip_window is not None  # Shown
    assert tooltip.tip_window.winfo_exists() == 1  # Verify it's created
    tooltip.hide_tip()  # Trigger leave
    assert tooltip.tip_window is None  # Hidden

def test_folder_dialog_recent_list(mock_root):
    recent = ["/folder1", "/folder2"]
    dialog = FolderDialog(mock_root, recent)
    # Check list_frame has children (one frame per recent folder + labels/buttons inside)
    assert len(dialog.list_frame.winfo_children()) == 2  # Two item frames
    # Verify a path label exists in the first item
    first_item = dialog.list_frame.winfo_children()[0]
    path_label = [child for child in first_item.winfo_children() if isinstance(child, ttk.Label)][0]
    assert path_label.cget('text') == "/folder1"

def test_folder_dialog_delete_item(mock_root):
    recent = ["/folder1"]
    on_delete = MagicMock()
    dialog = FolderDialog(mock_root, recent, on_delete_callback=on_delete)
    # Get the delete button from the first (only) item frame
    first_item = dialog.list_frame.winfo_children()[0]
    delete_btn = [child for child in first_item.winfo_children() if isinstance(child, ttk.Button)][0]
    # Simulate click (invoke command)
    delete_btn.invoke()
    on_delete.assert_called_with("/folder1")
    assert len(dialog.recent_folders) == 0  # Removed locally
    assert len(dialog.list_frame.winfo_children()) == 0  # Frame destroyed

def test_folder_dialog_confirm_invalid(mock_root):
    dialog = FolderDialog(mock_root, [])
    dialog.folder_var.set("/nonexistent")
    with patch('tkinter.messagebox.showerror') as mock_error:
        dialog.confirm()
        mock_error.assert_called_with("Invalid Path", ANY, parent=dialog.dialog)  # Invalid path error
    assert dialog.selected_folder is None  # Not set