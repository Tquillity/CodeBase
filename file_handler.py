import os
import pyperclip
import fnmatch
import mimetypes
import tkinter as tk
from tkinter import messagebox
import threading
import logging

class FileHandler:
    text_extensions_default = {
        '.txt', '.py', '.cpp', '.c', '.h', '.java', '.js', '.ts', '.tsx', '.jsx',
        '.css', '.scss', '.html', '.json', '.md', '.xml', '.svg', '.gitignore',
        '.yml', '.yaml', '.toml', '.ini', '.properties', '.csv', '.tsv', '.log',
        '.sql', '.sh', '.bash', '.zsh', '.fish', '.awk', '.sed', '.bat', '.cmd',
        '.ps1', '.php', '.rb', '.erb', '.haml', '.slim', '.pl', '.lua', '.r',
        '.m', '.mm', '.asm', '.v', '.vhdl', '.verilog', '.s', '.swift', '.kt',
        '.kts', '.go', '.rs', '.dart', '.vue', '.pug', '.coffee', '.proto',
        '.dockerfile', '.make', '.tf', '.hcl', '.sol', '.gradle', '.groovy',
        '.scala', '.clj', '.cljs', '.cljc', '.edn', '.rkt', '.jl', '.purs',
        '.elm', '.hs', '.lhs', '.agda', '.idr', '.nix', '.dhall', '.tex', '.bib',
        '.sty', '.cls', '.cs', '.fs', '.fsx',
        '.mdx', '.rst', '.adoc', '.org', '.texinfo', '.w', '.man', '.conf', '.cfg',
        '.env', '.ipynb', '.rmd', '.qmd', '.lock', '.srt', '.vtt', '.po', '.pot'
    }

    def __init__(self, gui):
        self.gui = gui
        self.repo_path = None
        self.file_contents = ""
        self.token_count = 0
        self.loaded_files = set()
        self.ignore_patterns = []
        self.recent_folders = gui.file_handler.recent_folders if hasattr(gui, 'file_handler') else gui.load_recent_folders()
        self.content_cache = {}
        self.lock = threading.Lock()

    @classmethod
    def get_extension_groups(cls):
        groups = {
            "Programming Languages": [
                '.py', '.java', '.cpp', '.c', '.h', '.js', '.ts', '.tsx', '.jsx',
                '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.kts', '.dart',
                '.groovy', '.scala', '.cs', '.fs', '.fsx', '.lua', '.pl', '.r',
                '.m', '.mm', '.asm', '.v', '.vhdl', '.verilog', '.s', '.clj',
                '.cljs', '.cljc', '.edn', '.rkt', '.jl', '.purs', '.elm', '.hs',
                '.lhs', '.agda', '.idr'
            ],
            "Markup": [
                '.html', '.xml', '.md', '.mdx', '.rst', '.adoc', '.org', '.texinfo'
            ],
            "Configuration": [
                '.json', '.yml', '.yaml', '.toml', '.ini', '.properties', '.gitignore',
                '.dockerfile', '.make', '.conf', '.cfg', '.env', '.hcl', '.tf', '.nix',
                '.dhall'
            ],
            "Scripts": [
                '.sh', '.bash', '.zsh', '.fish', '.awk', '.sed', '.bat', '.cmd', '.ps1'
            ],
            "Data": [
                '.csv', '.tsv', '.log', '.sql', '.ipynb', '.rmd', '.qmd'
            ],
            "Styles": [
                '.css', '.scss'
            ],
            "Other": [
                '.txt', '.svg', '.proto', '.sol', '.gradle', '.coffee', '.pug', '.vue',
                '.erb', '.haml', '.slim', '.tex', '.bib', '.sty', '.cls', '.w', '.man',
                '.lock', '.srt', '.vtt', '.po', '.pot'
            ]
        }
        all_grouped = set(sum(groups.values(), []))
        other_extensions = cls.text_extensions_default - all_grouped
        if other_extensions:
            groups["Other"].extend(sorted(other_extensions))
        return groups

    def load_repo(self, folder):
        abs_path = os.path.abspath(folder)
        if not os.path.commonpath([abs_path, os.path.expanduser("~")]).startswith(os.path.expanduser("~")):
            messagebox.showerror("Security Error", "Access outside user directory is not allowed.")
            return
        self.repo_path = abs_path
        self.gui.update_recent_folders(self.repo_path)
        self.ignore_patterns = self.parse_gitignore(os.path.join(self.repo_path, '.gitignore'))
        
        self.loaded_files.clear()
        for dirpath, dirnames, filenames in os.walk(self.repo_path):
            dirnames[:] = [d for d in dirnames if not self.is_ignored(os.path.join(dirpath, d))]
            for filename in filenames:
                file_path = os.path.normcase(os.path.join(dirpath, filename))
                if not self.is_ignored(file_path) and self.is_text_file(file_path):
                    self.loaded_files.add(file_path)
        
        self.file_contents = self.generate_file_contents()
        self.token_count = len(self.file_contents.split())
        self.gui.populate_tree(self.repo_path)

    def save_recent_folders(self):
        with open(self.gui.recent_folders_file, 'w') as file:
            for folder in self.recent_folders:
                file.write(f"{folder}\n")

    def parse_gitignore(self, gitignore_path):
        ignore_patterns = []
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r') as file:
                for line in file:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        ignore_patterns.append(line)
        return ignore_patterns

    def is_ignored(self, path):
        rel_path = os.path.relpath(path, self.repo_path)
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(os.path.basename(path), pattern):
                return True
        if '.git' in rel_path.split(os.sep):
            return True
        if self.gui.settings.get('app', 'exclude_node_modules', 1) and 'node_modules' in rel_path.split(os.sep):
            return True
        if self.gui.settings.get('app', 'exclude_dist', 1) and 'dist' in rel_path.split(os.sep):
            return True
        return False

    def is_text_file(self, file_path):
        mime_type, _ = mimetypes.guess_type(file_path)
        ext = os.path.splitext(file_path)[1].lower()
        filename = os.path.basename(file_path)
        exclude_files = self.gui.settings.get('app', 'exclude_files', {})
        text_extensions = self.gui.settings.get('app', 'text_extensions', {ext: 1 for ext in self.text_extensions_default})
        excluded = filename in exclude_files and exclude_files[filename] == 1
        return (
            (mime_type and mime_type.startswith('text')) or
            (ext in self.text_extensions_default and text_extensions.get(ext, 1) == 1)
        ) and not excluded

    def generate_file_contents(self):
        def content_generator():
            for file_path in sorted(self.loaded_files):
                if file_path not in self.content_cache:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as file:
                            self.content_cache[file_path] = file.read()
                    except FileNotFoundError:
                        logging.error(f"File not found: {file_path}")
                        messagebox.showerror("Error", f"File not found: {file_path}")
                        continue
                    except PermissionError:
                        logging.error(f"Permission denied: {file_path}")
                        messagebox.showerror("Error", f"Permission denied: {file_path}")
                        continue
                    except UnicodeDecodeError:
                        logging.error(f"Cannot decode file: {file_path}")
                        messagebox.showerror("Error", f"Cannot decode {file_path}: Not a text file")
                        continue
                    except Exception as e:
                        logging.error(f"Error reading {file_path}: {str(e)}")
                        messagebox.showerror("Error", f"Error reading {file_path}: {str(e)}")
                        continue
                yield f"File: {file_path}\nContent:\n{self.content_cache[file_path]}\n===FILE_SEPARATOR===\n"
        return ''.join(content_generator())

    def populate_tree(self, root_dir):
        self.gui.tree.delete(*self.gui.tree.get_children())
        root_id = self.gui.tree.insert("", "end", text=f"📁 {os.path.basename(root_dir)}", 
                                      values=(root_dir, "☑"), open=False, tags=('folder'))
        # Lazy loading: only expand when user opens the folder

    def build_tree(self, path, parent_id, selected=True):
        if self.is_ignored(path):
            return
        try:
            items = sorted(os.listdir(path))
            for item in items:
                item_path = os.path.join(path, item)
                if not self.is_ignored(item_path):
                    icon = "📁" if os.path.isdir(item_path) else "📄"
                    checkbox_state = "☑" if selected else "☐"
                    if os.path.isdir(item_path):
                        tags = ['folder']
                    else:
                        if self.is_text_file(item_path) and selected:
                            tags = ['file_selected']
                            self.loaded_files.add(item_path)
                        elif self.is_text_file(item_path):
                            tags = ['file_default']
                        else:
                            tags = ['file_nontext']
                    item_id = self.gui.tree.insert(parent_id, "end", text=f"{icon} {item}", 
                                                  values=(item_path, checkbox_state), open=False, 
                                                  tags=tags)
                    if os.path.isdir(item_path):
                        self.gui.tree.insert(item_id, "end", text="Loading...", tags=('dummy',))
        except Exception as e:
            print(f"Error building tree for {path}: {e}")

    def on_double_click(self, event):
        item_id = self.gui.tree.identify_row(event.y)
        if 'folder' in self.gui.tree.item(item_id, "tags"):
            self.expand_folder(item_id)

    def on_treeview_open(self, event):
        item_id = self.gui.tree.focus()
        if 'folder' in self.gui.tree.item(item_id, "tags"):
            self.expand_folder(item_id)

    def expand_folder(self, item_id):
        values = self.gui.tree.item(item_id, "values")
        if not values or len(values) < 1:
            print(f"Error: Item {item_id} has no path value")
            return

        item_path = values[0]
        original_text = self.gui.tree.item(item_id, "text")
        selected = values[1] == "☑"

        self.gui.tree.item(item_id, text=f"{original_text} (Loading...)")
        self.gui.root.update_idletasks()

        for child in self.gui.tree.get_children(item_id):
            self.gui.tree.delete(child)

        try:
            items = sorted(os.listdir(item_path))
            for item in items:
                item_full_path = os.path.join(item_path, item)
                if not self.is_ignored(item_full_path):
                    icon = "📁" if os.path.isdir(item_full_path) else "📄"
                    checkbox_state = "☑" if selected else "☐"
                    if os.path.isdir(item_full_path):
                        tags = ['folder']
                    else:
                        if self.is_text_file(item_full_path) and selected:
                            tags = ['file_selected']
                            self.loaded_files.add(item_full_path)
                        elif self.is_text_file(item_full_path):
                            tags = ['file_default']
                        else:
                            tags = ['file_nontext']
                    child_id = self.gui.tree.insert(item_id, "end", text=f"{icon} {item}", 
                                                   values=(item_full_path, checkbox_state), 
                                                   open=False, tags=tags)
                    if os.path.isdir(item_full_path):
                        self.gui.tree.insert(child_id, "end", text="Loading...", tags=('dummy',))
        except Exception as e:
            print(f"Error expanding folder {item_path}: {e}")

        self.gui.tree.item(item_id, text=original_text)
        self.update_tree_strikethrough()
        self.file_contents = self.generate_file_contents()
        self.token_count = len(self.file_contents.split())
        self.gui.update_content_preview()
        self.gui.info_label.config(text=f"Token Count: {self.token_count:,}".replace(",", " "))

    def toggle_selection(self, event):
        with self.lock:
            region = self.gui.tree.identify_region(event.x, event.y)
            if region == "cell":
                column = self.gui.tree.identify_column(event.x)
                if column == "#2":
                    item_id = self.gui.tree.identify_row(event.y)
                    values = self.gui.tree.item(item_id, "values")
                    current_state = values[1]
                    new_state = "☐" if current_state == "☑" else "☑"
                    item_path = values[0]
                    content_changed = False

                    if os.path.isfile(item_path) and self.is_text_file(item_path):
                        if new_state == "☑":
                            self.loaded_files.add(item_path)
                            tags = ['file_selected']
                        else:
                            self.loaded_files.discard(item_path)
                            tags = ['file_default']
                        self.gui.tree.item(item_id, values=(values[0], new_state), tags=tags)
                        content_changed = True
                    elif os.path.isdir(item_path):
                        self.gui.tree.item(item_id, values=(values[0], new_state))
                        content_changed = self.update_folder_selection(item_id, new_state == "☑")
                    else:
                        messagebox.showinfo("Info", "Only text files can be selected.")
                        return

                    self.update_tree_strikethrough()

                    if content_changed:
                        self.file_contents = self.generate_file_contents()
                        self.token_count = len(self.file_contents.split())
                        self.gui.root.after(0, self.gui.update_content_preview)
                        self.gui.root.after(0, lambda: self.gui.info_label.config(text=f"Token Count: {self.token_count:,}".replace(",", " ")))

    def update_folder_selection(self, item_id, selected):
        content_changed = False
        item_path = self.gui.tree.item(item_id, "values")[0]

        def update_loaded_files(path, select):
            nonlocal content_changed
            for root, dirs, files in os.walk(path):
                if hasattr(self, 'is_ignored') and self.is_ignored(root):
                    continue
                for file in files:
                    file_path = os.path.normcase(os.path.join(root, file))
                    if self.is_text_file(file_path):
                        if select:
                            if file_path not in self.loaded_files:
                                self.loaded_files.add(file_path)
                                content_changed = True
                        else:
                            if file_path in self.loaded_files:
                                self.loaded_files.discard(file_path)
                                content_changed = True

        update_loaded_files(item_path, selected)

        for child in self.gui.tree.get_children(item_id):
            values = self.gui.tree.item(child, "values") or ()
            if not values:
                continue
            child_path = values[0]
            
            if os.path.isfile(child_path):
                if self.is_text_file(child_path):
                    tags = ['file_selected'] if selected else ['file_default']
                else:
                    tags = ['file_nontext']
                self.gui.tree.item(child, values=(child_path, "☑" if selected else "☐"), tags=tags)
            elif os.path.isdir(child_path):
                self.gui.tree.item(child, values=(child_path, "☑" if selected else "☐"))
                if self.gui.tree.get_children(child):
                    self.update_folder_selection(child, selected)

        self.update_tree_strikethrough()
        return content_changed

    def update_tree_strikethrough(self):
        def update_item(item):
            values = self.gui.tree.item(item, "values")
            if values and len(values) > 0:
                item_path = os.path.normcase(values[0])
                if os.path.isfile(item_path):
                    if item_path in self.loaded_files:
                        tags = ['file_selected']
                    elif self.gui.show_unloaded_var.get():
                        tags = ['file_unloaded']
                    else:
                        if self.is_text_file(item_path):
                            tags = ['file_default']
                        else:
                            tags = ['file_nontext']
                    self.gui.tree.item(item, tags=tags)
            for child in self.gui.tree.get_children(item):
                update_item(child)
        if self.gui.tree.get_children():
            update_item(self.gui.tree.get_children()[0])

    def copy_contents(self):
        content = self.gui.base_prompt_text.get(1.0, tk.END).strip() + "\n\n" + self.file_contents if self.gui.prepend_var.get() else self.file_contents
        pyperclip.copy(content)
        self.gui.show_status_message("Copy Successful!")

    def copy_structure(self):
        pyperclip.copy(self.generate_folder_structure_text())
        self.gui.show_status_message("Copy Successful!")

    def copy_all(self):
        content = f"{self.gui.base_prompt_text.get(1.0, tk.END).strip()}\n\n{self.file_contents}\n\n{self.generate_folder_structure_text()}"
        pyperclip.copy(content)
        self.gui.show_status_message("Copied all content")

    def generate_folder_structure_text(self):
        def traverse(item_id, prefix="", indent=""):
            lines = []
            item_text = self.gui.tree.item(item_id, "text")
            if self.gui.settings.get('app', 'include_icons', 1) == 0:
                item_text = item_text[2:]
            lines.append(f"{indent}{prefix}{item_text}")
            children = self.gui.tree.get_children(item_id)
            for i, child_id in enumerate(children):
                sub_prefix = "└── " if i == len(children) - 1 else "├── "
                sub_indent = indent + ("    " if i == len(children) - 1 else "│   ")
                lines.extend(traverse(child_id, sub_prefix, sub_indent))
            return lines
        root_items = self.gui.tree.get_children()
        return "\n".join(traverse(root_items[0])) if root_items else ""

    def expand_all(self, item=""):
        children = self.gui.tree.get_children(item)
        for child in children:
            child_tags = self.gui.tree.item(child, "tags")
            child_text = self.gui.tree.item(child, "text")
            
            if 'folder' in child_tags:
                self.gui.tree.item(child, open=True)
                
                if "Loading..." in child_text:
                    self.expand_folder(child)
                else:
                    child_children = self.gui.tree.get_children(child)
                    if len(child_children) == 1 and self.gui.tree.item(child_children[0], "text") == "Loading...":
                        self.expand_folder(child)
                
                self.expand_all(child)

    def collapse_all(self, item=""):
        for child in self.gui.tree.get_children(item):
            if 'folder' in self.gui.tree.item(child, "tags"):
                self.gui.tree.item(child, open=False)
                self.collapse_all(child)

    def expand_levels(self, item_id, levels, current_level=0):
        if current_level < levels:
            self.gui.tree.item(item_id, open=True)
            self.expand_folder(item_id)
            for child in self.gui.tree.get_children(item_id):
                if 'folder' in self.gui.tree.item(child, "tags"):
                    self.expand_levels(child, levels, current_level + 1)

    def are_all_folders_expanded(self, item=""):
        for child in self.gui.tree.get_children(item):
            child_tags = self.gui.tree.item(child, "tags")
            child_open = self.gui.tree.item(child, "open")
            
            if 'folder' in child_tags:
                if not child_open:
                    return False
                if not self.are_all_folders_expanded(child):
                    return False
        return True

    def update_expand_collapse_button(self):
        if self.are_all_folders_expanded():
            self.gui.expand_collapse_button.config(text="Collapse All")
            self.gui.expand_collapse_var.set(False)
        else:
            self.gui.expand_collapse_button.config(text="Expand All")
            self.gui.expand_collapse_var.set(True)

    def toggle_expand_collapse(self):
        if self.are_all_folders_expanded():
            self.collapse_all()
            self.gui.expand_collapse_button.config(text="Expand All")
            self.gui.expand_collapse_var.set(True)
        else:
            self.expand_all()
            self.gui.expand_collapse_button.config(text="Collapse All")
            self.gui.expand_collapse_var.set(False)
        self.gui.show_status_message("Folder structure updated")

    def search_tab(self):
        query = self.gui.search_var.get()
        if not query:
            return
        current_tab = self.gui.notebook.index(self.gui.notebook.select())
        if current_tab == 3:
            return
        matches = []
        if current_tab in [0, 2]:
            text_widget = self.gui.content_text if current_tab == 0 else self.gui.base_prompt_text
            if current_tab == 0:
                text_widget.config(state=tk.NORMAL)
            text_widget.tag_remove("highlight", "1.0", tk.END)
            text_widget.tag_remove("focused_highlight", "1.0", tk.END)
            start_pos = "1.0"
            while True:
                pos = text_widget.search(query, start_pos, stopindex=tk.END, 
                                        nocase=not self.gui.case_sensitive_var.get(), 
                                        regexp=self.gui.whole_word_var.get())
                if not pos:
                    break
                end_pos = f"{pos}+{len(query)}c"
                matches.append((pos, end_pos))
                start_pos = end_pos
            text_widget.tag_config("highlight", background="#FFFF00", foreground="#000000")
            text_widget.tag_config("focused_highlight", background="#add8e6", foreground="#000000")
            if current_tab == 0:
                text_widget.config(state=tk.DISABLED)
        elif current_tab == 1:
            self.gui.tree.tag_configure("highlight", background="#FFFF00", foreground="#000000")
            self.gui.tree.tag_configure("focused_highlight", background="#add8e6", foreground="#000000")
            def collect_matches(item):
                item_text = self.gui.tree.item(item, "text")
                if query in item_text:
                    matches.append(item)
                for child in self.gui.tree.get_children(item):
                    collect_matches(child)
            if self.gui.tree.get_children():
                collect_matches(self.gui.tree.get_children()[0])

        self.gui.match_positions[current_tab] = matches
        self.gui.current_match_index[current_tab] = 0 if matches else -1
        for i, match in enumerate(matches):
            if current_tab in [0, 2]:
                text_widget.tag_add("focused_highlight" if i == 0 else "highlight", match[0], match[1])
            elif current_tab == 1:
                tags = [t for t in self.gui.tree.item(match, "tags") if t not in ("highlight", "focused_highlight")]
                tags.append("focused_highlight" if i == 0 else "highlight")
                self.gui.tree.item(match, tags=tags)
                if i == 0:
                    self.gui.tree.see(match)
                    self.gui.tree.selection_set(match)
        if matches:
            if current_tab in [0, 2]:
                self.center_match(text_widget, matches[0][0])
            self.gui.show_status_message("Search Successful")
        else:
            self.gui.show_status_message("Search Found Nothing")

    def center_match(self, text_widget, pos):
        text_widget.see(pos)
        top, bottom = text_widget.yview()
        delta = bottom - top
        line = int(text_widget.index(pos).split('.')[0])
        total_lines = int(text_widget.index("end").split('.')[0])
        if total_lines > 0:
            f = (line - 1) / total_lines
            new_top = max(0, min(1 - delta, f - delta / 2))
            text_widget.yview_moveto(new_top)

    def next_match(self):
        current_tab = self.gui.notebook.index(self.gui.notebook.select())
        matches = self.gui.match_positions.get(current_tab, [])
        if not matches or current_tab == 3:
            return
        index = self.gui.current_match_index.get(current_tab, -1)
        if index < len(matches) - 1:
            if current_tab in [0, 2]:
                text_widget = self.gui.content_text if current_tab == 0 else self.gui.base_prompt_text
                if current_tab == 0:
                    text_widget.config(state=tk.NORMAL)
                old_pos, old_end = matches[index]
                text_widget.tag_remove("focused_highlight", old_pos, old_end)
                text_widget.tag_add("highlight", old_pos, old_end)
                index += 1
                pos, end = matches[index]
                text_widget.tag_remove("highlight", pos, end)
                text_widget.tag_add("focused_highlight", pos, end)
                self.center_match(text_widget, pos)
                if current_tab == 0:
                    text_widget.config(state=tk.DISABLED)
            elif current_tab == 1:
                old_item = matches[index]
                tags = [t for t in self.gui.tree.item(old_item, "tags") if t != "focused_highlight"]
                tags.append("highlight")
                self.gui.tree.item(old_item, tags=tags)
                index += 1
                item = matches[index]
                tags = [t for t in self.gui.tree.item(item, "tags") if t != "highlight"]
                tags.append("focused_highlight")
                self.gui.tree.item(item, tags=tags)
                self.gui.tree.see(item)
                self.gui.tree.selection_set(item)
            self.gui.current_match_index[current_tab] = index

    def prev_match(self):
        current_tab = self.gui.notebook.index(self.gui.notebook.select())
        matches = self.gui.match_positions.get(current_tab, [])
        if not matches or current_tab == 3:
            return
        index = self.gui.current_match_index.get(current_tab, -1)
        if index > 0:
            if current_tab in [0, 2]:
                text_widget = self.gui.content_text if current_tab == 0 else self.gui.base_prompt_text
                if current_tab == 0:
                    text_widget.config(state=tk.NORMAL)
                old_pos, old_end = matches[index]
                text_widget.tag_remove("focused_highlight", old_pos, old_end)
                text_widget.tag_add("highlight", old_pos, old_end)
                index -= 1
                pos, end = matches[index]
                text_widget.tag_remove("highlight", pos, end)
                text_widget.tag_add("focused_highlight", pos, end)
                self.center_match(text_widget, pos)
                if current_tab == 0:
                    text_widget.config(state=tk.DISABLED)
            elif current_tab == 1:
                old_item = matches[index]
                tags = [t for t in self.gui.tree.item(old_item, "tags") if t != "focused_highlight"]
                tags.append("highlight")
                self.gui.tree.item(old_item, tags=tags)
                index -= 1
                item = matches[index]
                tags = [t for t in self.gui.tree.item(item, "tags") if t != "highlight"]
                tags.append("focused_highlight")
                self.gui.tree.item(item, tags=tags)
                self.gui.tree.see(item)
                self.gui.tree.selection_set(item)
            self.gui.current_match_index[current_tab] = index

    def find_all(self):
        query = self.gui.search_var.get()
        if not query:
            return
        current_tab = self.gui.notebook.index(self.gui.notebook.select())
        if current_tab == 3:
            return
        matches = []
        if current_tab in [0, 2]:
            text_widget = self.gui.content_text if current_tab == 0 else self.gui.base_prompt_text
            if current_tab == 0:
                text_widget.config(state=tk.NORMAL)
            text_widget.tag_remove("highlight", "1.0", tk.END)
            text_widget.tag_remove("focused_highlight", "1.0", tk.END)
            start_pos = "1.0"
            while True:
                pos = text_widget.search(query, start_pos, stopindex=tk.END, nocase=not self.gui.case_sensitive_var.get())
                if not pos:
                    break
                end_pos = f"{pos}+{len(query)}c"
                matches.append((pos, end_pos))
                start_pos = end_pos
            text_widget.tag_config("highlight", background="#FFFF00", foreground="#000000")
            for match in matches:
                text_widget.tag_add("highlight", match[0], match[1])
            if current_tab == 0:
                text_widget.config(state=tk.DISABLED)
        elif current_tab == 1:
            self.gui.tree.tag_configure("highlight", background="#FFFF00", foreground="#000000")
            def collect_matches(item):
                item_text = self.gui.tree.item(item, "text")
                if query.lower() in item_text.lower() if not self.gui.case_sensitive_var.get() else query in item_text:
                    matches.append(item)
                for child in self.gui.tree.get_children(item):
                    collect_matches(child)
            if self.gui.tree.get_children():
                collect_matches(self.gui.tree.get_children()[0])
            for match in matches:
                tags = [t for t in self.gui.tree.item(match, "tags") if t not in ("highlight", "focused_highlight")]
                tags.append("highlight")
                self.gui.tree.item(match, tags=tags)
        self.gui.match_positions[current_tab] = matches
        self.gui.current_match_index[current_tab] = -1
        if matches:
            self.gui.show_status_message("All matches highlighted")
        else:
            self.gui.show_status_message("No matches found")