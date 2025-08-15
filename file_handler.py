import os
import pyperclip
import fnmatch
import mimetypes
import tkinter as tk
from tkinter import messagebox
import threading
import logging
import time

from file_scanner import scan_repo, parse_gitignore, is_ignored_path, is_text_file
from content_manager import get_file_content, generate_content

class FileHandler:
    text_extensions_default = {'.txt', '.py', '.cpp', '.c', '.h', '.java', '.js', '.ts', '.tsx', '.jsx', '.css', '.scss', '.html', '.json', '.md', '.xml', '.svg', '.gitignore', '.yml', '.yaml', '.toml', '.ini', '.properties', '.csv', '.tsv', '.log', '.sql', '.sh', '.bash', '.zsh', '.fish', '.awk', '.sed', '.bat', '.cmd', '.ps1', '.php', '.rb', '.erb', '.haml', '.slim', '.pl', '.lua', '.r', '.m', '.mm', '.asm', '.v', '.vhdl', '.verilog', '.s', '.swift', '.kt', '.kts', '.go', '.rs', '.dart', '.vue', '.pug', '.coffee', '.proto', '.dockerfile', '.make', '.tf', '.hcl', '.sol', '.gradle', '.groovy', '.scala', '.clj', '.cljs', '.cljc', '.edn', '.rkt', '.jl', '.purs', '.elm', '.hs', '.lhs', '.agda', '.idr', '.nix', '.dhall', '.tex', '.bib', '.sty', '.cls', '.cs', '.fs', '.fsx', '.mdx', '.rst', '.adoc', '.org', '.texinfo', '.w', '.man', '.conf', '.cfg', '.env', '.ipynb', '.rmd', '.qmd', '.lock', '.srt', '.vtt', '.po', '.pot', '.mts'}
    FILE_SEPARATOR = "===FILE_SEPARATOR===\n"

    def __init__(self, gui):
        self.gui = gui
        self.repo_path = None
        self.loaded_files = set()
        self.scanned_text_files = set()
        self.ignore_patterns = []
        self.recent_folders = gui.load_recent_folders()
        self.content_cache = {}
        self.lock = threading.Lock()
        self.read_errors = []

    @classmethod
    def get_extension_groups(cls):
        groups = {
            "Programming Languages": [ '.py', '.java', '.cpp', '.c', '.h', '.js', '.ts', '.tsx', '.jsx', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.kts', '.dart', '.groovy', '.scala', '.cs', '.fs', '.fsx', '.lua', '.pl', '.r', '.m', '.mm', '.asm', '.v', '.vhdl', '.verilog', '.s', '.clj', '.cljs', '.cljc', '.edn', '.rkt', '.jl', '.purs', '.elm', '.hs', '.lhs', '.agda', '.idr' ],
            "Markup": [ '.html', '.xml', '.md', '.mdx', '.rst', '.adoc', '.org', '.texinfo' ],
            "Configuration": [ '.json', '.yml', '.yaml', '.toml', '.ini', '.properties', '.gitignore', '.dockerfile', '.make', '.conf', '.cfg', '.env', '.hcl', '.tf', '.nix', '.dhall', '.mts' ],
            "Scripts": [ '.sh', '.bash', '.zsh', '.fish', '.awk', '.sed', '.bat', '.cmd', '.ps1' ],
            "Data": [ '.csv', '.tsv', '.log', '.sql', '.ipynb', '.rmd', '.qmd' ],
            "Styles": [ '.css', '.scss' ],
            "Other": [ '.txt', '.svg', '.proto', '.sol', '.gradle', '.coffee', '.pug', '.vue', '.erb', '.haml', '.slim', '.tex', '.bib', '.sty', '.cls', '.w', '.man', '.lock', '.srt', '.vtt', '.po', '.pot' ]
        }
        all_grouped = set(sum(groups.values(), []))
        other_extensions = cls.text_extensions_default - all_grouped
        if other_extensions:
            groups["Other"].extend(sorted(other_extensions))
        return groups

    def populate_tree(self, root_dir):
        tree = self.gui.structure_tab.tree
        logging.info(f"Populating tree for root: {root_dir}")
        tree.delete(*tree.get_children())
        if not root_dir or not os.path.exists(root_dir):
            logging.warning("populate_tree called with invalid root_dir")
            return
        root_basename = os.path.basename(root_dir)
        initial_state = "☑"
        root_id = tree.insert("", "end", text=f"📁 {root_basename}",
                                      values=(root_dir, initial_state), open=False, tags=('folder',))
        logging.debug(f"Inserted root ID: {root_id}")
        tree.insert(root_id, "end", text="Loading...", tags=('dummy',))

    def build_tree_level(self, path, parent_id, selected=True):
        tree = self.gui.structure_tab.tree
        logging.info(f"Building level for path: {path}, parent: {parent_id}, selected: {selected}")
        for child in tree.get_children(parent_id):
            tree.delete(child)

        try:
            items = sorted(os.listdir(path))
            logging.debug(f"Found items: {items}")
        except OSError as e:
            logging.error(f"Dir list error: {path} - {e}")
            tree.insert(parent_id, "end", text=f"Error: {e.strerror}", tags=('error',))
            return

        added_items = 0
        for item in items:
            item_path = os.path.join(path, item)
            item_path_norm = os.path.normcase(item_path)

            if is_ignored_path(item_path, self.repo_path, self.ignore_patterns, self.gui):
                logging.debug(f"Ignored: {item_path}")
                continue

            is_dir = os.path.isdir(item_path)
            is_text = False
            if not is_dir:
                is_text = is_text_file(item_path, self.gui)

            logging.debug(f"Processing item: {item}, dir: {is_dir}, text: {is_text}")

            icon = "📁" if is_dir else ("📄" if is_text else "❓")
            checkbox_state = "☑" if selected else "☐"
            tags = []

            if is_dir:
                tags.append('folder')
            elif is_text:
                if selected:
                    tags.append('file_selected')
                    with self.lock:
                        self.loaded_files.add(item_path_norm)
                else:
                    tags.append('file_default')
                    with self.lock:
                        self.loaded_files.discard(item_path_norm)
            else:
                tags.append('file_nontext')

            try:
                item_id = tree.insert(parent_id, "end", text=f"{icon} {item}",
                                              values=(item_path, checkbox_state),
                                              open=False, tags=tuple(tags))
                logging.debug(f"Inserted item ID: {item_id}, tags: {tags}")
                if is_dir:
                    tree.insert(item_id, "end", text="Loading...", tags=('dummy',))
                added_items += 1
            except Exception as e:
                logging.error(f"Error inserting item {item} into tree: {e}")

        if added_items == 0 and not tree.get_children(parent_id):
             logging.debug(f"No items added to {path}")
             tree.insert(parent_id, "end", text="(empty)", tags=('empty',))

    def expand_folder(self, item_id):
        tree = self.gui.structure_tab.tree
        if not tree.exists(item_id):
            return

        logging.info(f"Received expand request for item_id: '{item_id}'")
        children = tree.get_children(item_id)

        # *** THE FIX IS HERE ***
        # Only build the level if the children list is not empty AND the first child has the 'dummy' tag.
        # This is the only state where we need to populate the folder.
        if children and 'dummy' in tree.item(children[0])['tags']:
            logging.debug(f"Item '{item_id}' has a dummy child. Proceeding to build level.")
            
            values = tree.item(item_id)['values']
            if not values or len(values) < 2:
                logging.error(f"Cannot expand folder: Item {item_id} has invalid values '{values}'")
                for child in children:
                    tree.delete(child)
                tree.insert(item_id, "end", text="Error: Invalid data", tags=('error',))
                return

            item_path = values[0]
            logging.info(f"Extracted path for expansion: '{item_path}'")
            parent_selected = values[1] == "☑"
            
            self.build_tree_level(item_path, item_id, parent_selected)
            logging.debug(f"Finished building level for {item_id}. It now has {len(tree.get_children(item_id))} children.")
        else:
            logging.debug(f"Item '{item_id}' is either empty or already populated. No action needed.")

        # This can be called regardless, as it's a lightweight UI update
        self.gui.root.after(0, self.gui.structure_tab.update_tree_strikethrough)


    def toggle_selection(self, event):
        tree = self.gui.structure_tab.tree
        region = tree.identify_region(event.x, event.y)
        if region != "cell": return

        column = tree.identify_column(event.x)
        logging.debug(f"Toggling selection for item: {tree.identify_row(event.y)}, column: {column}")
        if column != "#2": return

        item_id = tree.identify_row(event.y)
        if not item_id: return

        item_data = tree.item(item_id)
        values = item_data['values']
        if not values or len(values) < 2: return

        current_state = values[1]
        new_state_symbol = "☐" if current_state == "☑" else "☑"
        new_state_bool = new_state_symbol == "☑"
        
        item_path = values[0]
        item_path_norm = os.path.normcase(item_path)
        
        tags = list(item_data['tags'])
        content_changed = False
        new_tags = []

        with self.lock:
            if 'folder' in tags:
                tree.item(item_id, values=(item_path, new_state_symbol))
                content_changed = self._update_folder_selection_recursive(item_id, new_state_bool)
            elif 'file_selected' in tags or 'file_default' in tags:
                if new_state_bool:
                    self.loaded_files.add(item_path_norm)
                    new_tags = ['file_selected']
                else:
                    self.loaded_files.discard(item_path_norm)
                    new_tags = ['file_default']
                tree.item(item_id, values=(item_path, new_state_symbol), tags=tuple(new_tags))
                content_changed = True
        
        logging.debug(f"New state: {new_state_symbol}, tags: {new_tags}")

        self.gui.structure_tab.update_tree_strikethrough()

        if content_changed:
             self.gui.trigger_preview_update()

    def _update_folder_selection_recursive(self, item_id, selected):
        tree = self.gui.structure_tab.tree
        content_changed_flag = False
        children = tree.get_children(item_id)
        
        logging.debug(f"Recursive update for {item_id}, selected: {selected}")

        if children and tree.item(children[0])['tags'] == ('dummy',):
             self.expand_folder(item_id)
             children = tree.get_children(item_id)

        for child_id in children:
            child_data = tree.item(child_id)
            values = child_data['values']
            if not values or len(values) < 2: continue

            child_path = values[0]
            child_path_norm = os.path.normcase(child_path)
            tags = list(child_data['tags'])
            new_state_symbol = "☑" if selected else "☐"
            
            logging.debug(f"Updating child: {child_id}, new_state: {new_state_symbol}")

            if 'folder' in tags:
                tree.item(child_id, values=(child_path, new_state_symbol))
                if self._update_folder_selection_recursive(child_id, selected):
                    content_changed_flag = True
            elif 'file_selected' in tags or 'file_default' in tags:
                if selected:
                    if child_path_norm not in self.loaded_files: content_changed_flag = True
                    self.loaded_files.add(child_path_norm)
                    new_tags = ['file_selected']
                else:
                    if child_path_norm in self.loaded_files: content_changed_flag = True
                    self.loaded_files.discard(child_path_norm)
                    new_tags = ['file_default']
                tree.item(child_id, values=(child_path, new_state_symbol), tags=tuple(new_tags))

        return content_changed_flag

    def generate_and_update_preview(self, _, completion_callback):
        with self.lock:
            files_to_include = set(self.loaded_files)
        logging.info(f"Generating preview for {len(files_to_include)} files")
        generate_content(files_to_include, self.repo_path, self.lock, completion_callback, self.content_cache, self.read_errors)

    def expand_all(self, item=""):
        tree = self.gui.structure_tab.tree
        children = tree.get_children(item)
        for child_id in children:
            tags = tree.item(child_id)['tags']
            if 'folder' in tags:
                # Ensure it's populated before opening and recursing
                self.expand_folder(child_id)
                if tree.exists(child_id):
                     tree.item(child_id, open=True)
                     self.expand_all(child_id)

    def collapse_all(self, item=""):
        tree = self.gui.structure_tab.tree
        children = tree.get_children(item)
        for child_id in children:
            tags = tree.item(child_id)['tags']
            if 'folder' in tags:
                tree.item(child_id, open=False)
                # We also recurse on collapse to ensure all sub-folders are closed
                self.collapse_all(child_id)

    def generate_folder_structure_text(self):
        tree = self.gui.structure_tab.tree
        root_items = tree.get_children("")
        if not root_items:
            return ""
        include_icons = self.gui.settings.get('app', 'include_icons', 1) == 1
        structure_lines = []
        def traverse(item_id, indent="", prefix=""):
            item_info = tree.item(item_id)
            item_text_raw = item_info["text"]
            item_tags = item_info["tags"]
            if 'dummy' in item_tags or 'error' in item_tags or 'empty' in item_tags:
                if 'empty' in item_tags:
                     display_text = "(empty)"
                else:
                    return
            elif not include_icons and len(item_text_raw) > 2 and item_text_raw[1] == ' ':
                 display_text = item_text_raw[2:]
            else:
                 display_text = item_text_raw
            structure_lines.append(f"{indent}{prefix}{display_text}")
            children = tree.get_children(item_id)
            if 'folder' in item_tags and children:
                # Only traverse if the folder is actually populated (not a dummy)
                if not (len(children) == 1 and 'dummy' in tree.item(children[0])['tags']):
                    for i, child_id in enumerate(children):
                        sub_prefix = "└── " if i == len(children) - 1 else "├── "
                        sub_indent = indent + ("    " if i == len(children) - 1 else "│   ")
                        traverse(child_id, sub_indent, sub_prefix)
        if root_items:
             traverse(root_items[0])
        return "\n".join(structure_lines)

    def are_all_folders_expanded(self, item=""):
        tree = self.gui.structure_tab.tree
        children = tree.get_children(item)
        for child_id in children:
            tags = tree.item(child_id)['tags']
            if 'folder' in tags:
                if not tree.item(child_id)['open']:
                    return False
                # If it's open, we need to check its children too
                if not self.are_all_folders_expanded(child_id):
                    return False
        return True

    def expand_levels(self, levels, item="", current_level=0):
        tree = self.gui.structure_tab.tree
        if current_level >= levels:
             return
        children = tree.get_children(item)
        for child_id in children:
            tags = tree.item(child_id)['tags']
            if 'folder' in tags:
                # Ensure it's populated before opening
                self.expand_folder(child_id)
                if tree.exists(child_id):
                    tree.item(child_id, open=True)
                    # Recurse for the next level
                    self.expand_levels(levels, child_id, current_level + 1)