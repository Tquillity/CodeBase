import os
import pyperclip
import fnmatch
import mimetypes
import tkinter as tk
from tkinter import messagebox
from threading import Thread

class FileHandler:
    def __init__(self, gui):
        self.gui = gui
        self.repo_path = None
        self.file_contents = ""
        self.token_count = 0
        self.loaded_files = set()
        self.ignore_patterns = []
        self.recent_folders = gui.file_handler.recent_folders if hasattr(gui, 'file_handler') else gui.load_recent_folders()
        
        self.text_extensions_default = {'.txt', '.py', '.cpp', '.c', '.h', '.java', '.js', '.ts', '.tsx',
                                        '.jsx', '.css', '.scss', '.html', '.json', '.md', '.xml', '.svg',
                                        '.gitignore', '.yml', '.yaml', '.toml', '.ini', '.properties',
                                        '.csv', '.tsv', '.log', '.sql', '.sh', '.bash', '.zsh', '.fish',
                                        '.awk', '.sed', '.bat', '.cmd', '.ps1', '.php', '.rb', '.erb',
                                        '.haml', '.slim', '.pl', '.lua', '.r', '.m', '.mm', '.asm', '.v',
                                        '.vhdl', '.verilog', '.s', '.swift', '.kt', '.kts', '.go', '.rs',
                                        '.dart', '.vue', '.pug', '.coffee', '.proto', '.dockerfile',
                                        '.make', '.tf', '.hcl', '.sol', '.gradle', '.groovy', '.scala',
                                        '.clj', '.cljs', '.cljc', '.edn', '.rkt', '.jl', '.purs', '.elm',
                                        '.hs', '.lhs', '.agda', '.idr', '.nix', '.dhall', '.tex', '.bib',
                                        '.sty', '.cls', '.cs', '.fs', '.fsx'}
        self.text_extensions_enabled = {ext: tk.IntVar(value=1) for ext in self.text_extensions_default}
        self.exclude_files_default = {
            'package-lock.json': tk.IntVar(value=0),
            'yarn.lock': tk.IntVar(value=0),
            'composer.lock': tk.IntVar(value=0),
            'Gemfile.lock': tk.IntVar(value=0),
            'poetry.lock': tk.IntVar(value=0)
        }
        self.exclude_files = self.exclude_files_default.copy()

    def load_repo(self, folder):
        self.repo_path = os.path.abspath(folder)
        self.gui.update_recent_folders(self.repo_path)
        self.ignore_patterns = self.parse_gitignore(os.path.join(self.repo_path, '.gitignore'))
        
        # Populate loaded_files by scanning the repository
        self.loaded_files.clear()
        for dirpath, dirnames, filenames in os.walk(self.repo_path):
            dirnames[:] = [d for d in dirnames if not self.is_ignored(os.path.join(dirpath, d))]
            for filename in filenames:
                file_path = os.path.normcase(os.path.join(dirpath, filename))
                if not self.is_ignored(file_path) and self.is_text_file(file_path):
                    self.loaded_files.add(file_path)
        
        # Generate file contents after populating loaded_files
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
        return False

    def is_text_file(self, file_path):
        mime_type, _ = mimetypes.guess_type(file_path)
        ext = os.path.splitext(file_path)[1].lower()
        filename = os.path.basename(file_path)
        excluded = filename in self.exclude_files and self.exclude_files[filename].get() == 1
        return (
            (mime_type and mime_type.startswith('text')) or
            (ext in self.text_extensions_default and self.text_extensions_enabled[ext].get() == 1)
        ) and not excluded

    def generate_file_contents(self):
        file_contents = []
        for file_path in sorted(self.loaded_files):
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    file_contents.append(f"File: {file_path}\nContent:\n{content}\n===FILE_SEPARATOR===\n")
            except Exception as e:
                print(f"Error reading {file_path}: {str(e)}")
        return ''.join(file_contents)

    def populate_tree(self, root_dir):
        self.gui.tree.delete(*self.gui.tree.get_children())
        root_id = self.gui.tree.insert("", "end", text=f"📁 {os.path.basename(root_dir)}", 
                                      values=(root_dir, "☑"), open=True, 
                                      tags=('folder', 'selected'))
        self.build_tree(root_dir, root_id, selected=True)
        expansion = self.gui.settings.get('app', 'expansion', 'Collapsed')
        if expansion == 'Expanded':
            self.expand_all()
        elif expansion == 'Levels':
            try:
                levels = int(self.gui.settings.get('app', 'levels', '1'))
                self.expand_levels(root_id, levels)
            except ValueError:
                self.collapse_all()
        else:
            self.collapse_all()
        self.update_expand_collapse_button()

    def build_tree(self, path, parent_id, selected=True):
        if self.is_ignored(path):
            return
        for item in sorted(os.listdir(path)):
            item_path = os.path.join(path, item)
            if not self.is_ignored(item_path):
                icon = "📁" if os.path.isdir(item_path) else "📄"
                tag = 'folder' if os.path.isdir(item_path) else 'file'
                checkbox_state = "☑" if selected else "☐"
                tags = [tag]
                if selected:
                    tags.append('selected')
                item_id = self.gui.tree.insert(parent_id, "end", text=f"{icon} {item}", 
                                              values=(item_path, checkbox_state), open=False, 
                                              tags=tags)
                if os.path.isdir(item_path):
                    self.gui.tree.insert(item_id, "end", text="Loading...", tags=('dummy',))
                elif selected and self.is_text_file(item_path):
                    self.loaded_files.add(item_path)

    def on_double_click(self, event):
        item_id = self.gui.tree.identify_row(event.y)
        if 'folder' in self.gui.tree.item(item_id, "tags"):
            self.expand_folder(item_id)

    def on_treeview_open(self, event):
        item_id = self.gui.tree.focus()
        if 'folder' in self.gui.tree.item(item_id, "tags"):
            self.expand_folder(item_id)

    def expand_folder(self, item_id_or_path):
        if isinstance(item_id_or_path, str):
            item_id = self.find_tree_item(item_id_or_path)
            if not item_id:
                return
        else:
            item_id = item_id_or_path
        item_path = self.gui.tree.item(item_id, "values")[0]
        selected = 'selected' in self.gui.tree.item(item_id, "tags")
        for child in self.gui.tree.get_children(item_id):
            self.gui.tree.delete(child)
        self.build_tree(item_path, item_id, selected)
        self.update_tree_strikethrough()
        self.file_contents = self.generate_file_contents()
        self.token_count = len(self.file_contents.split())
        self.gui.update_content_preview()
        self.gui.info_label.config(text=f"Token Count: {self.token_count:,}".replace(",", " "))

    def toggle_selection(self, event):
        region = self.gui.tree.identify_region(event.x, event.y)
        if region == "cell":
            column = self.gui.tree.identify_column(event.x)
            if column == "#2":  # Checkbox column
                item_id = self.gui.tree.identify_row(event.y)
                values = self.gui.tree.item(item_id, "values")
                current_state = values[1]
                new_state = "☐" if current_state == "☑" else "☑"
                tags = list(self.gui.tree.item(item_id, "tags"))
                if 'selected' in tags:
                    tags.remove('selected')
                else:
                    tags.append('selected')
                self.gui.tree.item(item_id, values=(values[0], new_state), tags=tags)
                item_path = values[0]
                if os.path.isfile(item_path):
                    if new_state == "☑" and self.is_text_file(item_path):
                        self.loaded_files.add(item_path)
                    else:
                        self.loaded_files.discard(item_path)
                elif os.path.isdir(item_path):
                    self.update_folder_selection(item_id, new_state == "☑")
                self.file_contents = self.generate_file_contents()
                self.token_count = len(self.file_contents.split())
                self.gui.update_content_preview()
                self.gui.info_label.config(text=f"Token Count: {self.token_count:,}".replace(",", " "))

    def update_folder_selection(self, item_id, selected):
        for child in self.gui.tree.get_children(item_id):
            child_path = self.gui.tree.item(child, "values")[0]
            tags = list(self.gui.tree.item(child, "tags"))
            if selected:
                if 'selected' not in tags:
                    tags.append('selected')
            else:
                if 'selected' in tags:
                    tags.remove('selected')
            self.gui.tree.item(child, values=(child_path, "☑" if selected else "☐"), tags=tags)
            if os.path.isfile(child_path):
                if selected and self.is_text_file(child_path):
                    self.loaded_files.add(child_path)
                else:
                    self.loaded_files.discard(child_path)
            elif os.path.isdir(child_path):
                self.update_folder_selection(child, selected)

    def find_tree_item(self, path):
        def search(item):
            if self.gui.tree.item(item, "values") and self.gui.tree.item(item, "values")[0] == path:
                return item
            for child in self.gui.tree.get_children(item):
                result = search(child)
                if result:
                    return result
            return None
        return search(self.gui.tree.get_children()[0]) if self.gui.tree.get_children() else None

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
            if self.gui.include_icons_var.get() == 0:
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

    def update_tree_strikethrough(self):
        def update_item(item):
            values = self.gui.tree.item(item, "values")
            if values and len(values) > 0:
                item_path = os.path.normcase(values[0])
                tags = list(self.gui.tree.item(item, "tags"))
                if 'file' in tags and self.gui.show_unloaded_var.get() and item_path not in self.loaded_files:
                    if 'unloaded' not in tags:
                        tags.append('unloaded')
                elif 'unloaded' in tags:
                    tags.remove('unloaded')
                self.gui.tree.item(item, tags=tags)
            for child in self.gui.tree.get_children(item):
                update_item(child)
        if self.gui.tree.get_children():
            update_item(self.gui.tree.get_children()[0])

    def expand_all(self, item=""):
        for child in self.gui.tree.get_children(item):
            if 'folder' in self.gui.tree.item(child, "tags"):
                self.gui.tree.item(child, open=True)
                if self.gui.tree.item(child, "text") == "Loading...":
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
            if 'folder' in self.gui.tree.item(child, "tags"):
                if not self.gui.tree.item(child, "open"):
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
                pos = text_widget.search(query, start_pos, stopindex=tk.END, nocase=0)
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