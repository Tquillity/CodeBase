from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any, List, Optional, Tuple

import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.widgets.scrolled import ScrolledText

from constants import SECURITY_ENABLED
from file_list_handler import generate_list_content
from file_scanner import is_text_file
from path_utils import ensure_absolute_path, is_path_within_base, normalize_path
from security import validate_file_size
from widgets import Tooltip

if TYPE_CHECKING:
    from gui import RepoPromptGUI


class FileListTab(ttk.Frame):
    gui: RepoPromptGUI
    file_list_text: Any  # ttkbootstrap ScrolledText
    context_menu: tk.Menu
    load_list_button: ttk.Button
    copy_list_button: ttk.Button
    clear_list_button: ttk.Button
    error_label: ttk.Label

    def __init__(self, parent: tk.Misc, gui: RepoPromptGUI) -> None:
        super().__init__(parent)
        self.gui = gui
        self.setup_ui()

    def setup_ui(self) -> None:
        self.file_list_text = ScrolledText(self, wrap=tk.NONE,
                                                      font=("Arial", 10), bootstyle="dark", height=10)
        self.file_list_text.pack(fill="both", expand=True, padx=5, pady=(5, 10))
        
        # Ensure the text widget is always editable for pasting
        # Note: ttkbootstrap ScrolledText is always editable by default
        
        # Enable keyboard shortcuts for text editing
        self.file_list_text.bind("<Control-v>", self._paste_text)
        self.file_list_text.bind("<Control-V>", self._paste_text)
        self.file_list_text.bind("<Control-c>", self._copy_text)
        self.file_list_text.bind("<Control-C>", self._copy_text)
        self.file_list_text.bind("<Control-x>", self._cut_text)
        self.file_list_text.bind("<Control-X>", self._cut_text)
        self.file_list_text.bind("<Control-a>", self._select_all)
        self.file_list_text.bind("<Control-A>", self._select_all)
        self.file_list_text.bind("<Button-3>", self._show_context_menu)  # Right-click context menu
        
        # Create context menu once and reuse
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Cut", command=self._cut_text)
        self.context_menu.add_command(label="Copy", command=self._copy_text)
        self.context_menu.add_command(label="Paste", command=self._paste_text)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Select All", command=self._select_all)
        self.context_menu.add_command(label="Clear", command=self._clear_text)
        
        # Button frame for better organization
        button_frame = ttk.Frame(self)
        button_frame.pack(side=tk.BOTTOM, fill='x', pady=(0, 5))
        
        self.load_list_button = self.gui.create_button(button_frame, "Load List", self.load_file_list, "Load pasted file list for selection")
        self.load_list_button.pack(side=tk.LEFT, padx=(10, 5), pady=8)
        self.copy_list_button = self.gui.create_button(button_frame, "Copy from List", self.copy_from_list, "Copy content from listed files", state=tk.DISABLED)
        self.copy_list_button.pack(side=tk.LEFT, padx=5, pady=8)
        self.clear_list_button = self.gui.create_button(button_frame, "Clear List", self.clear_file_list, "Clear the file list text area")
        self.clear_list_button.pack(side=tk.LEFT, padx=5, pady=8)
        self.error_label = ttk.Label(self, text="", anchor="w", font=("Arial", 10))
        self.error_label.pack(fill="x", pady=(0, 10))


    def perform_search(self, query: str, case_sensitive: bool, whole_word: bool) -> List[Tuple[str, str]]:
        matches: List[Tuple[str, str]] = []
        start_pos = "1.0"
        while True:
            pos = self.file_list_text.search(query, start_pos, stopindex=tk.END,
                                             nocase=not case_sensitive,
                                             regexp=whole_word)
            if not pos: break
            end_pos = f"{pos}+{len(query)}c"
            matches.append((pos, end_pos))
            start_pos = end_pos
        return matches

    def highlight_all_matches(self, matches: List[Tuple[str, str]]) -> None:
        for match_data in matches:
            pos, end_pos = match_data
            self.file_list_text.tag_add("highlight", pos, end_pos)

    def highlight_match(self, match_data: Tuple[str, str], is_focused: bool = True) -> None:
        highlight_tag = "focused_highlight" if is_focused else "highlight"
        other_highlight_tag = "highlight" if is_focused else "focused_highlight"
        pos, end_pos = match_data
        self.file_list_text.tag_remove(other_highlight_tag, pos, end_pos)
        self.file_list_text.tag_add(highlight_tag, pos, end_pos)

    def center_match(self, match_data: Tuple[str, str]) -> None:
        pos, _ = match_data
        try:
            self.file_list_text.see(pos)
            if self.file_list_text.winfo_height() <= 0: return
            dlineinfo = self.file_list_text.dlineinfo(pos)
            if dlineinfo is None: return
            x, y, width, height, baseline = dlineinfo
           
            total_lines_str = self.file_list_text.index("end-1c").split('.')[0]
            if not total_lines_str: return
            total_lines = int(total_lines_str)
           
            lines_per_screen = max(1, self.file_list_text.winfo_height() // height if height > 0 else 20)
           
            target_line = max(1, int(self.file_list_text.index(pos).split('.')[0]) - (lines_per_screen // 2))
           
            self.file_list_text.yview_moveto( (target_line -1) / total_lines if total_lines > 0 else 0)
        except tk.TclError as e:
             logging.warning(f"TclError centering match (widget might be updating): {e}")
        except Exception as e:
             logging.error(f"Error centering match: {e}")

    def clear_highlights(self) -> None:
        self.file_list_text.tag_remove("highlight", "1.0", tk.END)
        self.file_list_text.tag_remove("focused_highlight", "1.0", tk.END)

    def clear(self) -> None:
        self.file_list_text.delete("1.0", tk.END)
        self.gui.list_selected_files.clear()
        self.copy_list_button.config(state=tk.DISABLED)
        self.error_label.config(text="")

    def clear_file_list(self) -> None:
        """Clear the file list text area and reset state."""
        self.file_list_text.delete("1.0", tk.END)
        with self.gui.file_handler.lock:
            self.gui.list_selected_files.clear()
            self.gui.list_read_errors.clear()
        self.copy_list_button.config(state=tk.DISABLED)
        self.error_label.config(text="")
        self.gui.show_status_message("File list cleared.")

    def load_file_list(self) -> None:
        if self.gui.is_loading:
            self.gui.show_status_message("Loading...", error=True)
            return
        
        # Ensure text area remains editable
        # ttkbootstrap ScrolledText is always editable
        text_content = self.file_list_text.get("1.0", tk.END).strip()
        if not text_content:
            self.gui.show_status_message("No file list provided.", error=True)
            self.copy_list_button.config(state=tk.DISABLED)
            return
        with self.gui.file_handler.lock:
            self.gui.list_selected_files.clear()
            self.gui.list_read_errors.clear()
        seen_paths = set() # To avoid duplicates
        lines = text_content.splitlines()
        for line in lines:
            line = line.strip()
            if not line or line in seen_paths:
                continue
            if os.path.isabs(line):
                full_path = normalize_path(line) # Normalize absolute path
                # Security: Ensure it's within the current repo (or home dir)
                if self.gui.current_repo_path and not is_path_within_base(full_path, self.gui.current_repo_path):
                    with self.gui.file_handler.lock:
                        self.gui.list_read_errors.append(f"Invalid (outside repo): {line}")
                    continue
            else:
                # Relative: Join with repo path
                if not self.gui.current_repo_path:
                    with self.gui.file_handler.lock:
                        self.gui.list_read_errors.append(f"No repo loaded for relative: {line}")
                    continue
                full_path = ensure_absolute_path(line, self.gui.current_repo_path)
            if os.path.isfile(full_path):
                # Enhanced security validation (only for suspicious files)
                if SECURITY_ENABLED:
                    # Only validate file size for normal repository files
                    is_valid, error = validate_file_size(full_path)
                    if not is_valid:
                        with self.gui.file_handler.lock:
                            self.gui.list_read_errors.append(f"Size: {line} - {error}")
                        continue
                
                # Optional: Check if it's a text file
                if is_text_file(full_path, self.gui):
                    with self.gui.file_handler.lock:
                        self.gui.list_selected_files.add(full_path)
                    seen_paths.add(line) # Track original line to dedup
                else:
                    with self.gui.file_handler.lock:
                        self.gui.list_read_errors.append(f"Non-text file: {line}")
            else:
                with self.gui.file_handler.lock:
                    self.gui.list_read_errors.append(f"Not Found: {line}")
        if self.gui.list_selected_files:
            self.copy_list_button.config(state=tk.NORMAL)
            self.gui.show_status_message(f"Loaded {len(self.gui.list_selected_files)} files from list.")
        else:
            self.copy_list_button.config(state=tk.DISABLED)
            self.gui.show_status_message("No valid files in list.", error=True)
        if self.gui.list_read_errors:
            self.error_label.config(text=f"Errors: {'; '.join(self.gui.list_read_errors[:3])}")
        
        # Ensure text area remains editable after loading
        # ttkbootstrap ScrolledText is always editable

    def _paste_text(self, event: Optional[tk.Event[Any]] = None) -> Optional[str]:
        """Handle paste operation for the text widget."""
        try:
            clipboard_content = self.file_list_text.clipboard_get()
            self.file_list_text.insert(tk.INSERT, clipboard_content)
        except tk.TclError:
            pass
        except Exception as e:
            logging.warning(f"Error pasting text: {e}")
        return "break"

    def _show_context_menu(self, event: tk.Event[Any]) -> None:
        """Show right-click context menu for text editing."""
        try:
            # Show context menu at cursor position
            self.context_menu.tk_popup(event.x_root, event.y_root)
        except Exception as e:
            logging.warning(f"Error showing context menu: {e}")
        finally:
             self.context_menu.grab_release()

    def _cut_text(self, event: Optional[tk.Event[Any]] = None) -> Optional[str]:
        """Cut selected text to clipboard."""
        try:
            if self.file_list_text.selection_get():
                self._copy_text()
                self.file_list_text.delete(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            pass
        return "break"

    def _copy_text(self, event: Optional[tk.Event[Any]] = None) -> Optional[str]:
        """Copy selected text to clipboard."""
        try:
            if self.file_list_text.selection_get():
                self.file_list_text.clipboard_clear()
                self.file_list_text.clipboard_append(self.file_list_text.selection_get())
        except tk.TclError:
            pass
        return "break"

    def _select_all(self, event: Optional[tk.Event[Any]] = None) -> Optional[str]:
        """Select all text in the widget."""
        self.file_list_text.tag_add(tk.SEL, "1.0", tk.END)
        self.file_list_text.mark_set(tk.INSERT, "1.0")
        self.file_list_text.see(tk.INSERT)
        return "break"

    def _clear_text(self) -> None:
        """Clear all text in the widget."""
        self.file_list_text.delete("1.0", tk.END)

    def copy_from_list(self) -> None:
        if self.gui.is_loading:
            self.gui.show_status_message("Loading...", error=True)
            return
        if not self.gui.list_selected_files:
            self.gui.show_status_message("No files selected from list.", error=True)
            return
        self.gui.show_loading_state("Preparing list content for clipboard...")
        prompt = self.gui.base_prompt_tab.base_prompt_text.get("1.0", tk.END).strip() if self.gui.prepend_var.get() else ""
        def completion_callback(content: str, token_count: int, errors: List[str], deleted_files: List[str] | None = None) -> None:
            self.gui.copy_handler._handle_copy_completion_final(prompt=prompt, content=content, structure=None, errors=errors,
                                                status_message="Copied from file list" if not errors else "Copy failed with errors")
        # FIX: Pass self.gui to generate_list_content for queue access
        generate_list_content(self.gui, self.gui.list_selected_files, self.gui.current_repo_path, self.gui.file_handler.lock,
                            completion_callback, self.gui.file_handler.content_cache, self.gui.list_read_errors)