import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox
import os
import logging
from widgets import Tooltip
from security import validate_template_file, validate_content_security, sanitize_content
from constants import SECURITY_ENABLED

class BasePromptTab(tk.Frame):
    def __init__(self, parent, gui, template_dir):
        super().__init__(parent)
        self.gui = gui
        self.template_dir = template_dir
        self.colors = gui.colors
        self.setup_ui()

    def setup_ui(self):
        self.base_prompt_text = scrolledtext.ScrolledText(self, wrap=tk.WORD,
                                                          bg=self.colors['bg_accent'], fg=self.colors['fg'],
                                                          font=("Arial", 10), relief=tk.FLAT, borderwidth=0)
        self.base_prompt_text.pack(fill="both", expand=True, padx=5, pady=5)

        self.base_prompt_button_frame = tk.Frame(self, bg=self.colors['bg'])
        self.base_prompt_button_frame.pack(side=tk.BOTTOM, fill='x', pady=10)

        self.save_template_button = self.gui.create_button(self.base_prompt_button_frame, "Save Template (Ctrl+T)", self.save_template, "Save current prompt text as a template")
        self.save_template_button.pack(side=tk.LEFT, padx=(10, 5))
        self.load_template_button = self.gui.create_button(self.base_prompt_button_frame, "Load Template (Ctrl+L)", self.load_template, "Load a saved prompt template")
        self.load_template_button.pack(side=tk.LEFT, padx=5)
        self.delete_template_button = self.gui.create_button(self.base_prompt_button_frame, "Delete Template", self.delete_template, "Delete a saved prompt template")
        self.delete_template_button.pack(side=tk.LEFT, padx=5)
        default_prompt = self.gui.settings.get('app', 'default_base_prompt', '')
        if default_prompt:
             self.base_prompt_text.insert('1.0', default_prompt)

    def reconfigure_colors(self, colors):
        self.colors = colors
        self.base_prompt_text.config(bg=colors['bg_accent'], fg=colors['fg'])
        self.base_prompt_button_frame.config(bg=colors['bg'])
        for btn in [self.save_template_button, self.load_template_button, self.delete_template_button]:
             btn.config(bg=colors['btn_bg'], fg=colors['btn_fg'])

    def perform_search(self, query, case_sensitive, whole_word):
        matches = []
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

    def highlight_all_matches(self, matches):
        for match_data in matches:
            pos, end_pos = match_data
            self.base_prompt_text.tag_add("highlight", pos, end_pos)

    def highlight_match(self, match_data, is_focused=True):
        highlight_tag = "focused_highlight" if is_focused else "highlight"
        other_highlight_tag = "highlight" if is_focused else "focused_highlight"
        pos, end_pos = match_data
        self.base_prompt_text.tag_remove(other_highlight_tag, pos, end_pos)
        self.base_prompt_text.tag_add(highlight_tag, pos, end_pos)

    def center_match(self, match_data):
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

    def clear_highlights(self):
        self.base_prompt_text.tag_remove("highlight", "1.0", tk.END)
        self.base_prompt_text.tag_remove("focused_highlight", "1.0", tk.END)

    def save_template(self):
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
                messagebox.showerror("Save Error", f"Could not save template:\n{e}")

    def load_template(self):
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
                        messagebox.showerror("Security Warning", f"Template validation failed:\n{error}")
                        return
                
                with open(template_file, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                # Additional content security validation
                if SECURITY_ENABLED:
                    is_valid, error = validate_content_security(content, "template")
                    if not is_valid:
                        messagebox.showerror("Security Warning", f"Template content validation failed:\n{error}")
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
                messagebox.showerror("Load Error", f"Could not load template:\n{e}")

    def delete_template(self):
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
                    messagebox.showerror("Delete Error", f"Could not delete template:\n{e}")

    def clear(self):
        self.base_prompt_text.delete(1.0, tk.END)