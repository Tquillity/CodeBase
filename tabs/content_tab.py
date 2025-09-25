import tkinter as tk
from tkinter import scrolledtext
from widgets import Tooltip
import logging

class ContentTab(tk.Frame):
    def __init__(self, parent, gui, file_handler):
        super().__init__(parent)
        self.gui = gui
        self.file_handler = file_handler
        self.colors = gui.colors
        self.file_states = {}
        self.content_expand_collapse_var = tk.BooleanVar(value=True)
        self.setup_ui()

    def setup_ui(self):
        self.content_button_frame = tk.Frame(self, bg=self.colors['bg'])
        self.content_button_frame.pack(side=tk.TOP, fill='x', pady=5)
        self.content_expand_collapse_button = self.gui.create_button(self.content_button_frame, "Expand All", self.toggle_content_all, "Expand/collapse all file content sections")
        self.content_expand_collapse_button.pack(pady=0, padx=10)

        self.content_text = scrolledtext.ScrolledText(self, wrap=tk.WORD,
                                                      bg=self.colors['bg_accent'], fg=self.colors['fg'],
                                                      font=("Arial", 10), state=tk.DISABLED,
                                                      relief=tk.FLAT, borderwidth=0)
        self.content_text.pack(fill="both", expand=True, padx=5, pady=(0,5))

        self.content_text.tag_configure("filename", foreground=self.colors['status'], font=('Arial', 10, 'bold'))
        self.content_text.tag_configure("toggle", foreground=self.colors['file_selected'], underline=True)
        self.content_text.tag_configure("highlight", background=self.colors['highlight_bg'], foreground=self.colors['highlight_fg'])
        self.content_text.tag_configure("focused_highlight", background=self.colors['focused_highlight_bg'], foreground=self.colors['focused_highlight_fg'])

        self.content_text.tag_bind("toggle", "<Enter>", lambda e: self.content_text.config(cursor="hand2"))
        self.content_text.tag_bind("toggle", "<Leave>", lambda e: self.content_text.config(cursor=""))

    def reconfigure_colors(self, colors):
        self.colors = colors
        self.content_button_frame.config(bg=colors['bg'])
        self.content_expand_collapse_button.config(bg=colors['btn_bg'], fg=colors['btn_fg'])
        self.content_text.config(bg=colors['bg_accent'], fg=colors['fg'])
        self.content_text.tag_configure("filename", foreground=colors['status'])
        self.content_text.tag_configure("toggle", foreground=colors['file_selected'])
        self.content_text.tag_configure("highlight", background=colors['highlight_bg'], foreground=colors['highlight_fg'])
        self.content_text.tag_configure("focused_highlight", background=colors['focused_highlight_bg'], foreground=colors['focused_highlight_fg'])

    def perform_search(self, query, case_sensitive, whole_word):
        matches = []
        initial_state = self.content_text.cget('state')
        self.content_text.config(state=tk.NORMAL)
        start_pos = "1.0"
        while True:
            pos = self.content_text.search(query, start_pos, stopindex=tk.END,
                                           nocase=not case_sensitive,
                                           regexp=whole_word)
            if not pos: break
            end_pos = f"{pos}+{len(query)}c"
            matches.append((pos, end_pos))
            start_pos = end_pos
        self.content_text.config(state=initial_state)
        return matches

    def highlight_all_matches(self, matches):
        initial_state = self.content_text.cget('state')
        self.content_text.config(state=tk.NORMAL)
        for match_data in matches:
            pos, end_pos = match_data
            self.content_text.tag_add("highlight", pos, end_pos)
        self.content_text.config(state=initial_state)

    def highlight_match(self, match_data, is_focused=True):
        highlight_tag = "focused_highlight" if is_focused else "highlight"
        other_highlight_tag = "highlight" if is_focused else "focused_highlight"
        pos, end_pos = match_data
        initial_state = self.content_text.cget('state')
        self.content_text.config(state=tk.NORMAL)
        self.content_text.tag_remove(other_highlight_tag, pos, end_pos)
        self.content_text.tag_add(highlight_tag, pos, end_pos)
        self.content_text.config(state=initial_state)

    def center_match(self, match_data):
        pos, _ = match_data
        try:
            self.content_text.see(pos)
            if self.content_text.winfo_height() <= 0: return

            dlineinfo = self.content_text.dlineinfo(pos)
            if dlineinfo is None: return
            x, y, width, height, baseline = dlineinfo
            
            total_lines_str = self.content_text.index("end-1c").split('.')[0]
            if not total_lines_str: return
            total_lines = int(total_lines_str)
            
            lines_per_screen = max(1, self.content_text.winfo_height() // height if height > 0 else 20) 
            
            target_line = max(1, int(self.content_text.index(pos).split('.')[0]) - (lines_per_screen // 2))
            
            self.content_text.yview_moveto( (target_line -1) / total_lines if total_lines > 0 else 0)

        except tk.TclError as e:
             logging.warning(f"TclError centering match (widget might be updating): {e}")
        except Exception as e:
             logging.error(f"Error centering match: {e}")

    def clear_highlights(self):
        initial_state = self.content_text.cget('state')
        self.content_text.config(state=tk.NORMAL)
        self.content_text.tag_remove("highlight", "1.0", tk.END)
        self.content_text.tag_remove("focused_highlight", "1.0", tk.END)
        self.content_text.config(state=initial_state)

    def _handle_preview_completion(self, generated_content, token_count, errors):
        if errors:
             error_msg = "Errors generating preview content."
             if errors: error_msg += f" Files: {'; '.join(errors[:3])}"
             self.gui.show_status_message(error_msg, error=True, duration=10000)

        self.content_text.config(state=tk.NORMAL)
        self.content_text.delete(1.0, tk.END)
        self.file_states.clear()

        if generated_content:
            sections = generated_content.split(self.file_handler.FILE_SEPARATOR)
            for section in sections:
                section = section.strip()
                if section.startswith("File: "):
                    try:
                        header_end = section.find("\nContent:\n")
                        if header_end != -1:
                            rel_path = section[6:header_end].strip()
                            content = section[header_end + 10:]
                            file_id = rel_path

                            self.file_states[file_id] = True
                            toggle_tag = f"toggle_{file_id}"
                            content_tag = f"content_{file_id}"

                            self.content_text.insert(tk.END, " [-] ", ("toggle", toggle_tag))
                            self.content_text.insert(tk.END, f"File: {rel_path}\n", "filename")
                            self.content_text.insert(tk.END, f"{content}\n\n", content_tag)

                            self.content_text.tag_bind(toggle_tag, "<Button-1>",
                                                       lambda event, fid=file_id: self.toggle_content(fid))
                    except Exception as e:
                         logging.error(f"Error parsing generated content section: {e}")
                         self.content_text.insert(tk.END, f"\n--- Error displaying section: {e} ---\n", "error")

        self.content_text.config(state=tk.DISABLED)

        self.gui.current_token_count = token_count
        self.gui.info_label.config(text=f"Tokens (Selected): {self.gui.current_token_count:,}".replace(",", " "))
        if self.gui.current_repo_path:
             self.gui.copy_button.config(state=tk.NORMAL)
             self.gui.copy_all_button.config(state=tk.NORMAL)
        
        # Update cache information
        self.gui.update_cache_info()

        self.update_content_expand_collapse_button()

        if not errors:
             self.gui.show_status_message("Content preview updated.", duration=3000)

    def toggle_content_all(self):
        if not self.file_states: return

        new_state_expanded = not self.content_expand_collapse_var.get()

        self.content_text.config(state=tk.NORMAL)
        toggle_symbol = "[-]" if new_state_expanded else "[+]"
        new_button_text = "Collapse All" if new_state_expanded else "Expand All"

        for file_id in self.file_states.keys():
            self.file_states[file_id] = new_state_expanded
            toggle_tag = f"toggle_{file_id}"
            content_tag = f"content_{file_id}"

            ranges = self.content_text.tag_ranges(toggle_tag)
            if ranges:
                 start, end = ranges
                 self.content_text.delete(start, end)
                 self.content_text.insert(start, f" {toggle_symbol} ", ("toggle", toggle_tag))

            self.content_text.tag_configure(content_tag, elide=not new_state_expanded)

        self.content_text.config(state=tk.DISABLED)
        self.content_expand_collapse_var.set(new_state_expanded)
        self.content_expand_collapse_button.config(text=new_button_text)
        status = "expanded" if new_state_expanded else "collapsed"
        self.gui.show_status_message(f"Content sections {status}.")

    def toggle_content(self, file_id):
        if file_id not in self.file_states: return

        current_state = self.file_states[file_id]
        new_state_expanded = not current_state
        self.file_states[file_id] = new_state_expanded

        toggle_tag = f"toggle_{file_id}"
        content_tag = f"content_{file_id}"
        toggle_symbol = "[-]" if new_state_expanded else "[+]"

        self.content_text.config(state=tk.NORMAL)
        ranges = self.content_text.tag_ranges(toggle_tag)
        if ranges:
            start, end = ranges
            self.content_text.delete(start, end)
            self.content_text.insert(start, f" {toggle_symbol} ", ("toggle", toggle_tag))
        self.content_text.tag_configure(content_tag, elide=not new_state_expanded)
        self.content_text.config(state=tk.DISABLED)

        self.update_content_expand_collapse_button()

    def update_content_expand_collapse_button(self):
        if not self.file_states:
            is_expanded = True
            self.content_expand_collapse_button.config(state=tk.DISABLED)
        else:
            self.content_expand_collapse_button.config(state=tk.NORMAL)
            is_expanded = all(self.file_states.values())

        self.content_expand_collapse_var.set(is_expanded)
        self.content_expand_collapse_button.config(text="Collapse All" if is_expanded else "Expand All")

    def clear(self):
        self.content_text.config(state=tk.NORMAL)
        self.content_text.delete(1.0, tk.END)
        self.content_text.config(state=tk.DISABLED)
        self.file_states.clear()
        self.update_content_expand_collapse_button()