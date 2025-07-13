import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch, ANY
from tkinter import messagebox
import pyperclip
from handlers.copy_handler import CopyHandler
from content_manager import generate_content

@pytest.fixture
def mock_gui():
    gui = MagicMock()
    gui.is_loading = False
    gui.file_handler = MagicMock()
    gui.file_handler.loaded_files = {"file1"}
    gui.file_handler.lock = MagicMock()
    gui.base_prompt_tab = MagicMock()
    gui.base_prompt_tab.base_prompt_text = MagicMock()
    gui.base_prompt_tab.base_prompt_text.get.return_value = "Prompt text\n"
    gui.prepend_var = MagicMock(get=MagicMock(return_value=1))
    gui.structure_tab = MagicMock()
    gui.structure_tab.tree = MagicMock(get_children=MagicMock(return_value=["item"]))
    gui.structure_tab.generate_folder_structure_text = MagicMock(return_value="Structure\n")
    gui.show_loading_state = MagicMock()
    gui.hide_loading_state = MagicMock()
    gui.show_status_message = MagicMock()
    gui.current_repo_path = "/repo"
    gui.file_handler.content_cache = {}
    gui.file_handler.read_errors = []
    return gui

@pytest.fixture
def copy_handler(mock_gui):
    return CopyHandler(mock_gui)

def test_copy_contents_success(copy_handler, mock_gui):
    with patch('handlers.copy_handler.generate_content') as mock_gen:
        copy_handler.copy_contents()
        mock_gen.assert_called_with(set(["file1"]), "/repo", ANY, ANY, {}, [])

def test_copy_contents_no_files(copy_handler, mock_gui):
    mock_gui.file_handler.loaded_files = set()
    copy_handler.copy_contents()
    mock_gui.show_status_message.assert_called_with("No files selected to copy.", error=True)

def test_copy_structure_success(copy_handler, mock_gui):
    with patch('pyperclip.copy') as mock_copy:
        copy_handler.copy_structure()
        mock_copy.assert_called_with("Structure\n")
        mock_gui.show_status_message.assert_called_with("Folder structure copied to clipboard.")

def test_copy_structure_empty(copy_handler, mock_gui):
    mock_gui.structure_tab.generate_folder_structure_text.return_value = ""
    copy_handler.copy_structure()
    mock_gui.show_status_message.assert_called_with("Generated structure is empty.", error=True)

def test_copy_all_success(copy_handler, mock_gui):
    with patch('handlers.copy_handler.generate_content') as mock_gen:
        copy_handler.copy_all()
        mock_gen.assert_called_with(set(["file1"]), "/repo", ANY, ANY, {}, [])

def test_copy_all_no_content(copy_handler, mock_gui):
    mock_gui.file_handler.loaded_files = set()
    mock_gui.structure_tab.tree.get_children.return_value = []
    mock_gui.base_prompt_tab.base_prompt_text.get.return_value = ""
    copy_handler.copy_all()
    mock_gui.show_status_message.assert_called_with("Nothing to copy.", error=True)

def test_handle_copy_completion_final_success(copy_handler, mock_gui):
    with patch('pyperclip.copy') as mock_copy:
        copy_handler._handle_copy_completion_final("Prompt", "Content\n", "Structure\n", [], "Copied")
        mock_copy.assert_called_with("Prompt\n\n---\n\nContent\n\n---\n\nFolder Structure:\nStructure\n")
        mock_gui.show_status_message.assert_called_with("Copied")

def test_handle_copy_completion_final_errors(copy_handler, mock_gui):
    # FIX: Patch the qualified name as imported in copy_handler.py
    with patch('tkinter.messagebox.showwarning') as mock_warn:  # FIX: Patch tkinter.messagebox directly
        copy_handler._handle_copy_completion_final("Prompt", "Content", "", ["error1", "error2"], "Failed")
        mock_gui.show_status_message.assert_any_call(ANY, error=True, duration=10000)
        mock_warn.assert_called()