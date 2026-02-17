import os
import tkinter as tk
import threading
import logging
from collections import deque
from typing import Set, List, Optional, Any, Dict

from file_scanner import parse_gitignore, is_ignored_path, is_text_file
from content_manager import get_file_content, generate_content
from constants import TEXT_EXTENSIONS_DEFAULT, FILE_SEPARATOR, CACHE_MAX_SIZE, CACHE_MAX_MEMORY_MB, ERROR_HANDLING_ENABLED, TREE_MAX_ITEMS, TREE_UI_UPDATE_INTERVAL, TREE_SAFETY_LIMIT
from lru_cache import ThreadSafeLRUCache
from path_utils import normalize_for_cache, is_same_path
from exceptions import FileOperationError, UIError, ThreadingError
from error_handler import handle_error, safe_execute

class FileHandler:
    text_extensions_default = TEXT_EXTENSIONS_DEFAULT
    FILE_SEPARATOR = FILE_SEPARATOR

    def __init__(self, gui: Any) -> None:
        self.gui = gui
        self.repo_path: Optional[str] = None
        self.loaded_files: Set[str] = set()
        self.scanned_text_files: Set[str] = set()
        self.ignore_patterns: List[str] = []
        self.recent_folders: List[str] = gui.load_recent_folders()
        self.content_cache: ThreadSafeLRUCache = ThreadSafeLRUCache(CACHE_MAX_SIZE, CACHE_MAX_MEMORY_MB)
        self.lock: threading.Lock = threading.Lock()
        self.read_errors: List[str] = []

    @classmethod
    def get_extension_groups(cls):
        groups = {
            "Programming Languages": [ '.py', '.java', '.cpp', '.c', '.h', '.js', '.ts', '.tsx', '.jsx', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.kts', '.dart', '.groovy', '.scala', '.cs', '.fs', '.fsx', '.lua', '.pl', '.r', '.m', '.mm', '.asm', '.v', '.vhdl', '.verilog', '.s', '.clj', '.cljs', '.cljc', '.edn', '.rkt', '.jl', '.purs', '.elm', '.hs', '.lhs', '.agda', '.idr' ],
            "Markup": [ '.html', '.xml', '.md', '.mdx', '.rst', '.adoc', '.org', '.texinfo', '.astro' ],
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

    def apply_filter(self, query):
        """
        Filters the file tree based on the query.
        If query is empty, restores the normal tree.
        If query exists, builds a filtered tree showing only matches and their parents.
        """
        if not self.repo_path: return
        
        if not query:
            # Restore normal view
            self.populate_tree(self.repo_path)
            return
            
        tree = self.gui.structure_tab.tree
        tree.delete(*tree.get_children())
        
        query = query.lower()
        matches = []
        
        # Find matching files in scanned list
        search_pool = self.scanned_text_files.union(self.loaded_files)
        
        for file_path in search_pool:
            if query in os.path.basename(file_path).lower():
                matches.append(file_path)
                
        if not matches:
            tree.insert("", "end", text="No matches found", tags=('empty',))
            return
            
        # 2. Build the tree with matches
        # We need to create folders as we go.
        created_items = {} # path -> item_id
        
        root_basename = os.path.basename(self.repo_path)
        root_id = tree.insert("", "end", text=f"📁 {root_basename} (Filtered)", 
                             values=(self.repo_path, "☑"), open=True, tags=('folder',))
        created_items[self.repo_path] = root_id
        
        for file_path in sorted(matches):
            # Ensure parents exist
            parent_path = os.path.dirname(file_path)
            
            # We need to build the chain from repo_path down to parent_path
            # Get relative path parts
            try:
                rel_path = os.path.relpath(file_path, self.repo_path)
            except ValueError:
                continue # Should not happen if file is in repo
                
            parts = rel_path.split(os.sep)
            current_path = self.repo_path
            parent_id = root_id
            
            # Create directory structure in tree
            for part in parts[:-1]:
                current_path = os.path.join(current_path, part)
                if current_path not in created_items:
                    folder_id = tree.insert(parent_id, "end", text=f"📁 {part}",
                                           values=(current_path, "☐"), open=True, tags=('folder',))
                    created_items[current_path] = folder_id
                    parent_id = folder_id
                else:
                    parent_id = created_items[current_path]
            
            # Insert file
            filename = parts[-1]
            item_path_norm = normalize_for_cache(file_path)
            is_selected = item_path_norm in self.loaded_files
            checkbox_state = "☑" if is_selected else "☐"
            tags = ['file_selected'] if is_selected else ['file_default']
            
            tree.insert(parent_id, "end", text=f"📄 {filename}",
                       values=(file_path, checkbox_state), tags=tuple(tags))

    def populate_tree(self, root_dir):
        tree = self.gui.structure_tab.tree
        logging.info(f"Populating tree for root: {root_dir}")
        tree.delete(*tree.get_children())
        
        # Clear expanding items set to prevent conflicts with new repository
        if hasattr(self, '_expanding_items'):
            self._expanding_items.clear()
        
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
            item_path_norm = normalize_for_cache(item_path)

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

        # Add a simple check to prevent infinite loops
        if not hasattr(self, '_expanding_items'):
            self._expanding_items = set()
        
        if item_id in self._expanding_items:
            logging.debug(f"Item '{item_id}' is already being expanded, skipping")
            return
            
        self._expanding_items.add(item_id)
        
        try:
            logging.info(f"Received expand request for item_id: '{item_id}'")
            children = tree.get_children(item_id)

            # Only build the level if the children list is not empty AND the first child has the 'dummy' tag.
            # This ensures we only populate folders that have not been loaded yet.
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
        finally:
            # Remove from expanding set when done
            self._expanding_items.discard(item_id)


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
        item_path_norm = normalize_for_cache(item_path)
        
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
            child_path_norm = normalize_for_cache(child_path)
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

    def generate_and_update_preview(self, _, completion_callback=None):
        """
        Generates the combined content preview and updates the UI.
        """
        # If no completion callback is provided, default to updating the content tab
        if completion_callback is None:
            completion_callback = self.gui.content_tab._handle_preview_completion
            
        with self.lock:
            files_to_include = set(self.loaded_files)

        logging.info(f"[PREVIEW] Starting generation for {len(files_to_include)} files")
        # Loading phase already set by repo_handler (e.g. "Generating preview..."); do not call show_loading_state here (avoids reset loop)

        # Get the currently selected template format from the settings/UI
        current_format = self.gui.settings.get('app', 'copy_format', "Markdown (Grok)")
        
        def update_progress(processed, total, elapsed):
            if processed > 5:
                avg = elapsed / processed
                remaining = avg * (total - processed)
                message = f"Reading {processed} of {total} files ({elapsed:.1f}s, est. {remaining:.1f}s left)"
            else:
                message = f"Reading {processed} of {total} files ({elapsed:.1f}s)"
            
            # Update both status bar and progress bar
            self.gui.status_bar.config(text=f" {message}")
            percentage = int((processed / total) * 100) if total > 0 else 0
            file_count_text = f"{processed}/{total} files"
            self.gui.update_progress(percentage, message, file_count_text)
        def queued_progress(processed, total, elapsed):
            self.gui.task_queue.put((update_progress, (processed, total, elapsed)))
        def wrapped_completion(content, token_count, errors, deleted_files=None):
            self.gui.task_queue.put((completion_callback, (content, token_count, errors, deleted_files or [])))
            self.gui.task_queue.put((self.gui.hide_loading_state, ()))
        thread = threading.Thread(target=generate_content, args=(files_to_include, self.repo_path, self.lock, wrapped_completion, self.content_cache, self.read_errors, queued_progress, self.gui, current_format), daemon=True)
        thread.start()

    def expand_all(self, item: str = "", max_depth: int = None) -> None:
        """Iterative expand_all implementation with smart depth limiting to prevent infinite loops."""
        tree = self.gui.structure_tab.tree
        
        # Smart depth calculation: analyze repository structure first
        if max_depth is None:
            max_depth = self._calculate_smart_depth_limit()
        
        logging.info(f"Expanding tree with depth limit: {max_depth}")
        
        # Use a queue for iterative processing instead of recursion
        # Each item in queue is (item_id, depth)
        items_to_process = deque([(item, 0)])
        processed_count = 0
        
        while items_to_process and processed_count < TREE_SAFETY_LIMIT:
            current_item, depth = items_to_process.popleft()
            processed_count += 1
            
            # Skip if we've reached max depth
            if depth >= max_depth:
                logging.debug(f"Skipping expansion at depth {depth} (max: {max_depth})")
                continue
            
            # Additional safety: Skip if we've processed too many items at this depth
            # This prevents infinite loops in pathological directory structures
            if processed_count > 1000 and depth > 5:
                logging.warning(f"Stopping expansion at depth {depth} due to high item count ({processed_count})")
                break
            
            # Get children of current item
            children = tree.get_children(current_item)
            
            # Process each child
            for child_id in children:
                tags = tree.item(child_id)['tags']
                if 'folder' in tags:
                    # Ensure it's populated before opening
                    self.expand_folder(child_id)
                    if tree.exists(child_id):
                        tree.item(child_id, open=True)
                        # Add to queue for processing with incremented depth
                        items_to_process.append((child_id, depth + 1))
            
            # Allow UI updates to prevent blocking
            if processed_count % TREE_UI_UPDATE_INTERVAL == 0:
                tree.update_idletasks()
        
        if processed_count >= TREE_SAFETY_LIMIT:
            logging.warning(f"expand_all: Processed {processed_count} items, stopped at safety limit")
        else:
            logging.info(f"expand_all: Processed {processed_count} items, completed successfully")

    def _calculate_smart_depth_limit(self) -> int:
        """Calculate an appropriate depth limit based on repository structure."""
        if not self.repo_path or not os.path.exists(self.repo_path):
            return 5  # Default fallback
        
        try:
            # Sample the repository structure to determine appropriate depth
            max_depth_found = 0
            sample_count = 0
            max_samples = 100  # Limit sampling for performance
            
            for root, dirs, files in os.walk(self.repo_path):
                if sample_count >= max_samples:
                    break
                    
                # Skip hidden directories and common build/cache directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', 'env', '__pycache__', 'build', 'dist', 'target']]
                
                depth = root.count(os.sep) - self.repo_path.count(os.sep)
                max_depth_found = max(max_depth_found, depth)
                sample_count += 1
            
            # Smart depth calculation:
            # - Use actual max depth found (100% coverage)
            # - Add safety buffer of 2 levels to handle edge cases
            # - Maximum: 15 levels (to prevent infinite loops in extreme cases)
            smart_depth = min(15, max_depth_found + 2)
            
            logging.info(f"Repository max depth: {max_depth_found}, using smart limit: {smart_depth}")
            return smart_depth
            
        except Exception as e:
            logging.warning(f"Error calculating smart depth limit: {e}, using default")
            return 10  # Generous default for unknown repositories

    def expand_all_unlimited(self, item: str = "") -> None:
        """Expand all folders with no depth limit - use with caution on very large repositories."""
        logging.warning("Using unlimited expansion - this may be slow on large repositories")
        self.expand_all(item, max_depth=999)  # Effectively unlimited

    def collapse_all(self, item: str = "") -> None:
        """Iterative collapse_all implementation to prevent stack overflow and improve performance."""
        tree = self.gui.structure_tab.tree
        
        # Use a queue for iterative processing instead of recursion
        items_to_process = deque([item])
        processed_count = 0
        
        while items_to_process and processed_count < TREE_SAFETY_LIMIT:
            current_item = items_to_process.popleft()
            processed_count += 1
            
            # Get children of current item
            children = tree.get_children(current_item)
            
            # Process each child
            for child_id in children:
                tags = tree.item(child_id)['tags']
                if 'folder' in tags:
                    tree.item(child_id, open=False)
                    # Add to queue for processing (instead of recursion)
                    items_to_process.append(child_id)
            
            # Allow UI updates to prevent blocking
            if processed_count % TREE_UI_UPDATE_INTERVAL == 0:
                tree.update_idletasks()
        
        if processed_count >= TREE_SAFETY_LIMIT:
            logging.warning(f"collapse_all: Processed {processed_count} items, stopped at safety limit")

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
        """Iterative are_all_folders_expanded implementation to prevent stack overflow and improve performance."""
        tree = self.gui.structure_tab.tree
        
        # Use a queue for iterative processing instead of recursion
        items_to_check = deque([item])
        processed_count = 0
        
        while items_to_check and processed_count < TREE_SAFETY_LIMIT:
            current_item = items_to_check.popleft()
            processed_count += 1
            
            # Get children of current item
            children = tree.get_children(current_item)
            
            # Check each child
            for child_id in children:
                tags = tree.item(child_id)['tags']
                if 'folder' in tags:
                    if not tree.item(child_id)['open']:
                        return False
                    # Add to queue for checking (instead of recursion)
                    items_to_check.append(child_id)
        
        if processed_count >= TREE_SAFETY_LIMIT:
            logging.warning(f"are_all_folders_expanded: Processed {processed_count} items, stopped at safety limit")
        
        return True

    def expand_levels(self, levels: int, item: str = "", current_level: int = 0) -> None:
        """Iterative expand_levels implementation to prevent stack overflow and improve performance."""
        tree = self.gui.structure_tab.tree
        
        # Use a queue for iterative processing with level tracking
        items_to_process = deque([(item, current_level)])
        processed_count = 0
        
        while items_to_process and processed_count < TREE_SAFETY_LIMIT:
            current_item, level = items_to_process.popleft()
            processed_count += 1
            
            # Stop if we've reached the desired level
            if level >= levels:
                continue
            
            # Get children of current item
            children = tree.get_children(current_item)
            
            # Process each child
            for child_id in children:
                tags = tree.item(child_id)['tags']
                if 'folder' in tags:
                    # Ensure it's populated before opening
                    self.expand_folder(child_id)
                    if tree.exists(child_id):
                        tree.item(child_id, open=True)
                        # Add to queue for next level processing (instead of recursion)
                        items_to_process.append((child_id, level + 1))
            
            # Allow UI updates to prevent blocking
            if processed_count % TREE_UI_UPDATE_INTERVAL == 0:
                tree.update_idletasks()
        
        if processed_count >= TREE_SAFETY_LIMIT:
            logging.warning(f"expand_levels: Processed {processed_count} items, stopped at safety limit")