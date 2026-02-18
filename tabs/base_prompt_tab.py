from __future__ import annotations

import logging
import os
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING, Any, List, Tuple

import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.widgets.scrolled import ScrolledText

from constants import SECURITY_ENABLED
from security import sanitize_content, validate_content_security, validate_template_file
from widgets import Tooltip

if TYPE_CHECKING:
    from gui import RepoPromptGUI


class BasePromptTab(ttk.Frame):
    gui: RepoPromptGUI
    template_dir: str
    base_prompt_text: Any  # ttkbootstrap ScrolledText
    base_prompt_button_frame: ttk.Frame
    save_template_button: ttk.Button
    load_template_button: ttk.Button
    delete_template_button: ttk.Button

    def __init__(
        self,
        parent: tk.Misc,
        gui: RepoPromptGUI,
        template_dir: str,
    ) -> None:
        super().__init__(parent)
        self.gui = gui
        self.template_dir = template_dir
        self.setup_ui()

    def setup_ui(self) -> None:
        self.base_prompt_text = ScrolledText(self, wrap=tk.WORD,
                                                          font=("Arial", 10), bootstyle="dark")
        self.base_prompt_text.pack(fill="both", expand=True, padx=5, pady=(5, 10))

        self.base_prompt_button_frame = ttk.Frame(self)
        self.base_prompt_button_frame.pack(side=tk.BOTTOM, fill='x', pady=(0, 10))

        self.save_template_button = self.gui.create_button(self.base_prompt_button_frame, "Save Template (Ctrl+T)", self.save_template, "Save current prompt text as a template")
        self.save_template_button.pack(side=tk.LEFT, padx=(10, 5), pady=8)
        self.load_template_button = self.gui.create_button(self.base_prompt_button_frame, "Load Template (Ctrl+L)", self.load_template, "Load a saved prompt template")
        self.load_template_button.pack(side=tk.LEFT, padx=5, pady=8)
        self.delete_template_button = self.gui.create_button(self.base_prompt_button_frame, "Delete Template", self.delete_template, "Delete a saved prompt template")
        self.delete_template_button.pack(side=tk.LEFT, padx=5, pady=8)
        default_prompt = self.gui.settings.get('app', 'default_base_prompt', '')
        if default_prompt:
             self.base_prompt_text.insert('1.0', default_prompt)


    def perform_search(self, query: str, case_sensitive: bool, whole_word: bool) -> List[Tuple[str, str]]:
        matches: List[Tuple[str, str]] = []
        start_pos = "1.0"
        while True:
            pos = self.base_prompt_text.search(query, start_pos, stopindex=tk.END,
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
            self.base_prompt_text.tag_add("highlight", pos, end_pos)

    def highlight_match(self, match_data: Tuple[str, str], is_focused: bool = True) -> None:
        highlight_tag = "focused_highlight" if is_focused else "highlight"
        other_highlight_tag = "highlight" if is_focused else "focused_highlight"
        pos, end_pos = match_data
        self.base_prompt_text.tag_remove(other_highlight_tag, pos, end_pos)
        self.base_prompt_text.tag_add(highlight_tag, pos, end_pos)

    def center_match(self, match_data: Tuple[str, str]) -> None:
        pos, _ = match_data
        try:
            self.base_prompt_text.see(pos)
            if self.base_prompt_text.winfo_height() <= 0: return

            dlineinfo = self.base_prompt_text.dlineinfo(pos)
            if dlineinfo is None: return
            x, y, width, height, baseline = dlineinfo
            
            total_lines_str = self.base_prompt_text.index("end-1c").split('.')[0]
            if not total_lines_str: return
            total_lines = int(total_lines_str)
            
            lines_per_screen = max(1, self.base_prompt_text.winfo_height() // height if height > 0 else 20) 
            
            target_line = max(1, int(self.base_prompt_text.index(pos).split('.')[0]) - (lines_per_screen // 2))
            
            self.base_prompt_text.yview_moveto( (target_line -1) / total_lines if total_lines > 0 else 0)

        except tk.TclError as e:
             logging.warning(f"TclError centering match (widget might be updating): {e}")
        except Exception as e:
             logging.error(f"Error centering match: {e}")

    def clear_highlights(self) -> None:
        self.base_prompt_text.tag_remove("highlight", "1.0", tk.END)
        self.base_prompt_text.tag_remove("focused_highlight", "1.0", tk.END)

    def save_template(self) -> None:
        template_content = self.base_prompt_text.get(1.0, tk.END).strip()
        if not template_content:
             self.gui.show_status_message("Base Prompt is empty, nothing to save.", error=True)
             return

        template_name = filedialog.asksaveasfilename(
            initialdir=self.template_dir,
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            title="Save Base Prompt Template"
        )
        if template_name:
            try:
                with open(template_name, 'w', encoding='utf-8') as file:
                    file.write(template_content)
                self.gui.show_status_message(f"Template '{os.path.basename(template_name)}' saved.")
            except Exception as e:
                logging.error(f"Error saving template {template_name}: {e}")
                self.gui.show_toast(f"Could not save template: {e}", toast_type="error")

    def load_template(self) -> None:
        template_file = filedialog.askopenfilename(
            initialdir=self.template_dir,
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Load Base Prompt Template"
        )
        if template_file:
            try:
                # Enhanced security validation
                if SECURITY_ENABLED:
                    is_valid, error = validate_template_file(template_file)
                    if not is_valid:
                        self.gui.show_toast(f"Template validation failed: {error}", toast_type="warning")
                        return
                
                with open(template_file, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                # Additional content security validation
                if SECURITY_ENABLED:
                    is_valid, error = validate_content_security(content, "template")
                    if not is_valid:
                        self.gui.show_toast(f"Template content validation failed: {error}", toast_type="warning")
                        return
                    
                    # Sanitize content if needed
                    sanitized_content = sanitize_content(content)
                    if sanitized_content != content:
                        if messagebox.askyesno("Security Notice", 
                            "Potentially unsafe content detected and sanitized. Continue with sanitized version?"):
                            content = sanitized_content
                        else:
                            return
                
                self.base_prompt_text.delete(1.0, tk.END)
                self.base_prompt_text.insert(tk.END, content)
                self.gui.show_status_message(f"Template '{os.path.basename(template_file)}' loaded.")
            except Exception as e:
                logging.error(f"Error loading template {template_file}: {e}")
                self.gui.show_toast(f"Could not load template: {e}", toast_type="error")

    def delete_template(self) -> None:
        template_file = filedialog.askopenfilename(
            initialdir=self.template_dir,
            filetypes=[("Text files", "*.txt")],
            title="Select Template to Delete"
        )
        if template_file:
            if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to permanently delete the template:\n{os.path.basename(template_file)}?"):
                try:
                    os.remove(template_file)
                    self.gui.show_status_message(f"Template '{os.path.basename(template_file)}' deleted.")
                except Exception as e:
                    logging.error(f"Error deleting template {template_file}: {e}")
                    self.gui.show_toast(f"Could not delete template: {e}", toast_type="error")

    def clear(self) -> None:
        self.base_prompt_text.delete(1.0, tk.END)