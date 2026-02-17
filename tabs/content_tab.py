from __future__ import annotations

import logging
import os
import tkinter as tk
from typing import Any

import ttkbootstrap as ttk
from ttkbootstrap.widgets.scrolled import ScrolledText
import pygments  # type: ignore[import-untyped]
from pygments.lexers import get_lexer_for_filename, TextLexer  # type: ignore[import-untyped]
from pygments.styles import get_style_by_name  # type: ignore[import-untyped]
from pygments.token import Token  # type: ignore[import-untyped]

from constants import ERROR_MESSAGE_DURATION, STATUS_MESSAGE_DURATION
from path_utils import get_relative_path
from widgets import Tooltip


class ContentTab(ttk.Frame):
    def __init__(self, parent: ttk.Frame, gui: Any, file_handler: Any) -> None:
        super().__init__(parent)
        self.gui = gui
        self.file_handler = file_handler
        # Colors now managed by ttkbootstrap theme
        self.file_states = {}
        self.content_expand_collapse_var = ttk.BooleanVar(value=True)
        self.setup_ui()

    def setup_ui(self):
        self.content_button_frame = ttk.Frame(self)
        self.content_button_frame.pack(side=tk.TOP, fill='x', pady=(10, 5))
        self.content_expand_collapse_button = self.gui.create_button(self.content_button_frame, "Expand All", self.toggle_content_all, "Expand/collapse all file content sections")
        self.content_expand_collapse_button.pack(pady=8, padx=10)

        self.content_text = ScrolledText(self, wrap=tk.WORD,
                                                      font=("Arial", 10),
                                                      bootstyle="dark")
        self.content_text.pack(fill="both", expand=True, padx=5, pady=(0, 10))

        # Get theme colors from ttkbootstrap
        style = ttk.Style()
        colors = style.colors
        
        self.content_text.tag_configure("filename", foreground=colors.danger, font=('Arial', 10, 'bold'))
        self.content_text.tag_configure("toggle", foreground=colors.success, underline=True)
        self.content_text.tag_configure("deleted", foreground=colors.danger, overstrike=True, font=('Arial', 10, 'bold'))
        self.content_text.tag_configure("highlight", background=colors.warning, foreground=colors.bg)
        self.content_text.tag_configure("focused_highlight", background=colors.primary, foreground=colors.bg)

        self.content_text.tag_bind("toggle", "<Enter>", lambda e: self.content_text.config(cursor="hand2"))
        self.content_text.tag_bind("toggle", "<Leave>", lambda e: self.content_text.config(cursor=""))


    def perform_search(self, query, case_sensitive, whole_word):
        matches = []
        # ttkbootstrap ScrolledText is always editable
        start_pos = "1.0"
        while True:
            pos = self.content_text.search(query, start_pos, stopindex=tk.END,
                                           nocase=not case_sensitive,
                                           regexp=whole_word)
            if not pos: break
            end_pos = f"{pos}+{len(query)}c"
            matches.append((pos, end_pos))
            start_pos = end_pos
        return matches

    def highlight_all_matches(self, matches):
        # ttkbootstrap ScrolledText is always editable
        for match_data in matches:
            pos, end_pos = match_data
            self.content_text.tag_add("highlight", pos, end_pos)

    def highlight_match(self, match_data, is_focused=True):
        highlight_tag = "focused_highlight" if is_focused else "highlight"
        other_highlight_tag = "highlight" if is_focused else "focused_highlight"
        pos, end_pos = match_data
        # ttkbootstrap ScrolledText is always editable
        self.content_text.tag_remove(other_highlight_tag, pos, end_pos)
        self.content_text.tag_add(highlight_tag, pos, end_pos)

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
        # ttkbootstrap ScrolledText is always editable
        self.content_text.tag_remove("highlight", "1.0", tk.END)
        self.content_text.tag_remove("focused_highlight", "1.0", tk.END)

    def _get_syntax_tags(self):
        """Map Pygments tokens to ttkbootstrap theme colors."""
        style = ttk.Style()
        colors = style.colors
        
        # Basic mapping - can be refined
        return {
            Token.Keyword: colors.primary,
            Token.Name: colors.info,
            Token.String: colors.success,
            Token.Number: colors.warning,
            Token.Comment: colors.secondary,
            Token.Operator: colors.danger,
            Token.Punctuation: colors.fg,
            Token.Text: colors.fg,
            Token.Error: colors.danger
        }

    def _highlight_code(self, content, filename):
        """Highlight code using Pygments."""
        try:
            lexer = get_lexer_for_filename(filename)
        except pygments.util.ClassNotFound:
            lexer = TextLexer()
            
        tokens = pygments.lex(content, lexer)
        return tokens

    def _insert_content_chunked(self, text, tags):
        """Insert large text in chunks to avoid UI freeze."""
        chunk_size = 2000
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        for i, chunk in enumerate(chunks):
            self.content_text.insert(tk.END, chunk, tags)
            if i > 0 and i % 5 == 0:
                self.update_idletasks()

    def _handle_preview_completion(self, generated_content, token_count, errors, deleted_files=None):
        deleted_files = deleted_files or []
        self.gui.is_generating_preview = False

        logging.info(f"[PREVIEW COMPLETE] Callback received. Content length: {len(generated_content or ''):,} chars, Errors: {len(errors or [])}, Deleted: {len(deleted_files)}")

        self.gui.hide_loading_state()

        if errors:
            error_msg = "Errors generating preview content."
            error_msg += f" Files: {'; '.join(errors[:3])}"
            self.gui.show_status_message(error_msg, error=True, duration=ERROR_MESSAGE_DURATION)
        elif deleted_files and not errors:
            self.gui.show_status_message("Preview ready. Deleted files listed below.", duration=STATUS_MESSAGE_DURATION)
        else:
            self.gui.show_status_message("Preview ready.", duration=STATUS_MESSAGE_DURATION)

        # ttkbootstrap ScrolledText is always editable
        self.content_text.delete(1.0, tk.END)
        self.file_states.clear()
        
        # Setup syntax tags
        syntax_colors = self._get_syntax_tags()
        for token_type, color in syntax_colors.items():
            self.content_text.tag_configure(str(token_type), foreground=color)

        if generated_content:
            sections = generated_content.split(self.file_handler.FILE_SEPARATOR)
            for section in sections:
                section = section.strip()
                if not section: continue

                rel_path = None
                content = None
                
                # --- Parsing Logic ---
                
                # Case 1: Standard Markdown (Grok/Default)
                if section.startswith("File: "):
                    try:
                        header_end = section.find("\nContent:\n")
                        if header_end != -1:
                            rel_path = section[6:header_end].strip()
                            content_block = section[header_end + 10:]
                            
                            # Clean up markdown code blocks if present
                            if content_block.startswith("```"):
                                first_newline = content_block.find("\n")
                                if first_newline != -1:
                                    content_block = content_block[first_newline+1:]
                            if content_block.endswith("```"):
                                content_block = content_block[:-3]
                            
                            content = content_block.strip()
                    except Exception as e:
                         logging.error(f"Error parsing Markdown section: {e}")

                # Case 2: XML Format (Gemini)
                elif section.startswith("<file"):
                    try:
                        # Simple string parsing to extract path and content
                        # Expected format: <file path="...">\n<![CDATA[\n CONTENT \n]]>\n</file>
                        
                        # Extract Path
                        path_start = section.find('path="')
                        if path_start != -1:
                            path_start += 6
                            path_end = section.find('"', path_start)
                            if path_end != -1:
                                rel_path = section[path_start:path_end]
                        
                        # Extract Content (CDATA)
                        cdata_start = section.find('<![CDATA[')
                        if cdata_start != -1:
                            cdata_start += 9
                            cdata_end = section.rfind(']]>')
                            if cdata_end != -1:
                                content = section[cdata_start:cdata_end].strip()
                    except Exception as e:
                         logging.error(f"Error parsing XML section: {e}")

                # --- Rendering Logic ---
                if rel_path and content is not None:
                    file_id = rel_path
                    self.file_states[file_id] = True
                    toggle_tag = f"toggle_{file_id}"
                    content_tag = f"content_{file_id}"

                    self.content_text.insert(tk.END, " [-] ", ("toggle", toggle_tag))
                    self.content_text.insert(tk.END, f"File: {rel_path}\n", "filename")
                    
                    # Syntax Highlighting Logic
                    # Cap at 500KB for highlighting to prevent freeze
                    if len(content) < 500 * 1024:
                        tokens = self._highlight_code(content, rel_path)
                        for token_type, token_text in tokens:
                            # Map specific token types to generic ones if needed
                            tag = str(token_type)
                            while tag not in syntax_colors and token_type.parent:
                                token_type = token_type.parent
                                tag = str(token_type)
                            
                            if tag not in syntax_colors:
                                tag = str(Token.Text)
                                
                            self.content_text.insert(tk.END, token_text, (content_tag, tag))
                            
                            # Periodic update for responsiveness
                            if len(token_text) > 1000:
                                self.update_idletasks()
                    else:
                        # Fallback for large files
                        self._insert_content_chunked(content, content_tag)
                        
                    self.content_text.insert(tk.END, "\n\n", content_tag)

                    self.content_text.tag_bind(toggle_tag, "<Button-1>",
                                                lambda event, fid=file_id: self.toggle_content(fid))
                else:
                    if len(section) > 5:
                         self.content_text.insert(tk.END, f"{section}\n\n")

        if deleted_files:
            repo_path = getattr(self.gui, 'current_repo_path', None) or ''
            self.content_text.insert(tk.END, "\n", "deleted")
            for path in sorted(deleted_files):
                rel = get_relative_path(path, repo_path) or path
                self.content_text.insert(tk.END, f"[DELETED] {rel}\n", "deleted")
            self.content_text.insert(tk.END, "\n", "deleted")
            summary = "Deleted files (not copied): " + ", ".join(
                (get_relative_path(p, repo_path) or os.path.basename(p) for p in sorted(deleted_files)[:10])
            )
            if len(deleted_files) > 10:
                summary += f" … +{len(deleted_files) - 10} more"
            self.content_text.insert(tk.END, summary + "\n", "deleted")

        self.gui.current_token_count = token_count
        self.gui.info_label.config(text=f"Tokens (Selected): {self.gui.current_token_count:,}".replace(",", " "))
        if self.gui.current_repo_path:
             self.gui.copy_button.config(state=tk.NORMAL)
             self.gui.copy_all_button.config(state=tk.NORMAL)
        
        # Update cache information
        self.gui.update_cache_info()

        self.update_content_expand_collapse_button()

    def toggle_content_all(self):
        if not self.file_states: return

        new_state_expanded = not self.content_expand_collapse_var.get()

        # ttkbootstrap ScrolledText is always editable
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

        # ttkbootstrap ScrolledText is always editable
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

        # ttkbootstrap ScrolledText is always editable
        ranges = self.content_text.tag_ranges(toggle_tag)
        if ranges:
            start, end = ranges
            self.content_text.delete(start, end)
            self.content_text.insert(start, f" {toggle_symbol} ", ("toggle", toggle_tag))
        self.content_text.tag_configure(content_tag, elide=not new_state_expanded)
        # ttkbootstrap ScrolledText is always editable

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
        # ttkbootstrap ScrolledText is always editable
        self.content_text.delete(1.0, tk.END)
        self.file_states.clear()
        self.update_content_expand_collapse_button()

    def update_tag_colors(self):
        """Updates text tag colors to match the current theme."""
        style = ttk.Style()
        colors = style.colors

        self.content_text.tag_configure("filename", foreground=colors.danger, font=('Arial', 10, 'bold'))
        self.content_text.tag_configure("toggle", foreground=colors.success, underline=True)
        self.content_text.tag_configure("deleted", foreground=colors.danger, overstrike=True, font=('Arial', 10, 'bold'))
        self.content_text.tag_configure("highlight", background=colors.warning, foreground=colors.bg)
        self.content_text.tag_configure("focused_highlight", background=colors.primary, foreground=colors.bg)