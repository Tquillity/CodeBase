import tkinter as tk
from tkinter import scrolledtext
from widgets import Tooltip
import logging
import os
from file_list_handler import generate_list_content
from file_scanner import is_text_file
class FileListTab(tk.Frame):
    def __init__(self, parent, gui):
        super().__init__(parent)
        self.gui = gui
        self.colors = gui.colors
        self.setup_ui()

    def setup_ui(self):
        self.file_list_text = scrolledtext.ScrolledText(self, wrap=tk.NONE,
                                                      bg=self.colors['bg_accent'], fg=self.colors['fg'],
                                                      font=("Arial", 10), relief=tk.FLAT, borderwidth=0, height=10)
        self.file_list_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.load_list_button = self.gui.create_button(self, "Load List", self.load_file_list, "Load pasted file list for selection")
        self.load_list_button.pack(side=tk.LEFT, padx=10, pady=5)
        self.copy_list_button = self.gui.create_button(self, "Copy from List", self.copy_from_list, "Copy content from listed files", state=tk.DISABLED)
        self.copy_list_button.pack(side=tk.LEFT, padx=10, pady=5)
        self.error_label = tk.Label(self, text="", bg=self.colors['bg'], fg=self.colors['status'], anchor="w")
        self.error_label.pack(fill="x", pady=5)

    def reconfigure_colors(self, colors):
        self.colors = colors
        self.file_list_text.config(bg=colors['bg_accent'], fg=colors['fg'])
        self.load_list_button.config(bg=colors['btn_bg'], fg=colors['btn_fg'])
        self.copy_list_button.config(bg=colors['btn_bg'], fg=colors['btn_fg'])
        self.error_label.config(bg=colors['bg'], fg=colors['status'])

    def perform_search(self, query, case_sensitive, whole_word):
        matches = []
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

    def highlight_all_matches(self, matches):
        for match_data in matches:
            pos, end_pos = match_data
            self.file_list_text.tag_add("highlight", pos, end_pos)

    def highlight_match(self, match_data, is_focused=True):
        highlight_tag = "focused_highlight" if is_focused else "highlight"
        other_highlight_tag = "highlight" if is_focused else "focused_highlight"
        pos, end_pos = match_data
        self.file_list_text.tag_remove(other_highlight_tag, pos, end_pos)
        self.file_list_text.tag_add(highlight_tag, pos, end_pos)

    def center_match(self, match_data):
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

    def clear_highlights(self):
        self.file_list_text.tag_remove("highlight", "1.0", tk.END)
        self.file_list_text.tag_remove("focused_highlight", "1.0", tk.END)

    def clear(self):
        self.file_list_text.delete("1.0", tk.END)
        self.gui.list_selected_files.clear()
        self.copy_list_button.config(state=tk.DISABLED)
        self.error_label.config(text="")

    def load_file_list(self):
        if self.gui.is_loading:
            self.gui.show_status_message("Loading...", error=True)
            return
        text_content = self.file_list_text.get("1.0", tk.END).strip()
        if not text_content:
            self.gui.show_status_message("No file list provided.", error=True)
            self.copy_list_button.config(state=tk.DISABLED)
            return
        self.gui.list_selected_files.clear()
        self.gui.list_read_errors.clear()
        seen_paths = set() # To avoid duplicates
        lines = text_content.splitlines()
        for line in lines:
            line = line.strip()
            if not line or line in seen_paths:
                continue
            if os.path.isabs(line):
                full_path = os.path.normpath(line) # Normalize absolute path
                # Security: Ensure it's within the current repo (or home dir)
                if self.gui.current_repo_path and not full_path.startswith(self.gui.current_repo_path):
                    self.gui.list_read_errors.append(f"Invalid (outside repo): {line}")
                    continue
            else:
                # Relative: Join with repo path
                if not self.gui.current_repo_path:
                    self.gui.list_read_errors.append(f"No repo loaded for relative: {line}")
                    continue
                full_path = os.path.normpath(os.path.join(self.gui.current_repo_path, line))
            if os.path.isfile(full_path):
                # Optional: Check if it's a text file
                if is_text_file(full_path, self.gui):
                    self.gui.list_selected_files.add(full_path)
                    seen_paths.add(line) # Track original line to dedup
                else:
                    self.gui.list_read_errors.append(f"Non-text file: {line}")
            else:
                self.gui.list_read_errors.append(f"Not Found: {line}")
        if self.gui.list_selected_files:
            self.copy_list_button.config(state=tk.NORMAL)
            self.gui.show_status_message(f"Loaded {len(self.gui.list_selected_files)} files from list.")
        else:
            self.copy_list_button.config(state=tk.DISABLED)
            self.gui.show_status_message("No valid files in list.", error=True)
        if self.gui.list_read_errors:
            self.error_label.config(text=f"Errors: {'; '.join(self.gui.list_read_errors[:3])}")

    def copy_from_list(self):
        if self.gui.is_loading:
            self.gui.show_status_message("Loading...", error=True)
            return
        if not self.gui.list_selected_files:
            self.gui.show_status_message("No files selected from list.", error=True)
            return
        self.gui.show_loading_state("Preparing list content for clipboard...")
        prompt = self.gui.base_prompt_tab.base_prompt_text.get("1.0", tk.END).strip() if self.gui.prepend_var.get() else ""
        def completion_callback(content, token_count, errors):
            self.gui.copy_handler._handle_copy_completion_final(prompt=prompt, content=content, structure=None, errors=errors,
                                                status_message="Copied from file list" if not errors else "Copy failed with errors")
        # FIX: Pass self.gui to generate_list_content for queue access
        generate_list_content(self.gui, self.gui.list_selected_files, self.gui.current_repo_path, self.gui.file_handler.lock,
                            completion_callback, self.gui.file_handler.content_cache, self.gui.list_read_errors)