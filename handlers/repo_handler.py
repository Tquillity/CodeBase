import os
import pyperclip
import fnmatch
import mimetypes
import tkinter as tk
from tkinter import messagebox
import threading
import logging
import time # For timing tasks
from widgets import FolderDialog
from constants import TEXT_EXTENSIONS_DEFAULT, FILE_SEPARATOR, CACHE_MAX_SIZE, CACHE_MAX_MEMORY_MB, ERROR_MESSAGE_DURATION, STATUS_MESSAGE_DURATION, ERROR_HANDLING_ENABLED
from lru_cache import ThreadSafeLRUCache
from file_scanner import parse_gitignore, is_ignored_path, yield_repo_files
from exceptions import RepositoryError, FileOperationError, SecurityError
from error_handler import handle_error, safe_execute
class RepoHandler:
    # Default text extensions (remains class variable for access in settings)
    text_extensions_default = TEXT_EXTENSIONS_DEFAULT
    FILE_SEPARATOR = FILE_SEPARATOR
    def __init__(self, gui):
        self.gui = gui
        self.repo_path = None
        self.loaded_files = set() # Files *selected* for inclusion
        self.scanned_text_files = set() # All text files found during scan
        self.ignore_patterns = []
        # Ensure recent folders are loaded correctly via gui method
        self.recent_folders = gui.load_recent_folders()
        self.content_cache = ThreadSafeLRUCache(CACHE_MAX_SIZE, CACHE_MAX_MEMORY_MB)
        self.lock = threading.Lock() # Lock for accessing shared resources like loaded_files, cache
        self.read_errors = [] # Collect errors during read operations

    def select_repo(self):
        """Opens a dialog to select a repository and loads it."""
        if self.gui.is_loading:
            self.gui.show_status_message("Loading...", error=True)
            return
        default_start_folder = self.gui.settings.get('app', 'default_start_folder', os.path.expanduser("~"))
        dialog = FolderDialog(self.gui.root, self.gui.recent_folders, on_delete_callback=self.gui.delete_recent_folder, default_start_folder=default_start_folder)
        folder = dialog.show()
        if folder:
            self.gui.update_recent_folders(folder)
            self._clear_internal_state(clear_ui=True)
            self.gui.show_loading_state(f"Scanning {os.path.basename(folder)}...", show_cancel=True)
            self.load_repo(folder, self.gui.show_status_message, self._handle_load_completion)

    def refresh_repo(self):
        """
        Refreshes the current repository, preserving selections and expansion state.
        """
        if self.gui.is_loading:
            self.gui.show_status_message("Loading...", error=True)
            return
        if not self.repo_path:
            self.gui.show_status_message("No repository loaded to refresh.", error=True)
            return
        logging.info("Starting repository refresh...")
        logging.info(f"Repository path: {self.repo_path}")
        self.gui.show_loading_state(f"Refreshing {os.path.basename(self.repo_path)}...", show_cancel=True)
        # --- PRESERVE STATE ---
        # 1. Save the set of currently selected files
        with self.gui.file_handler.lock:
            previous_selections = self.gui.file_handler.loaded_files.copy()
        logging.debug(f"Preserving {len(previous_selections)} selected files.")
        # 2. Save the expansion state of the TreeView
        expansion_state = self.get_tree_expansion_state()
        logging.debug(f"Preserving {len(expansion_state)} expanded folders.")
       
        # 3. Clear content cache to pick up file modifications
        with self.gui.file_handler.lock:
            self.gui.file_handler.content_cache.clear()
       
        # --- RESCAN ---
        # The completion callback will handle restoring the state
        completion_callback = lambda repo_path, ignore_patterns, scanned, loaded, errors: \
            self._handle_refresh_completion(repo_path, ignore_patterns, scanned, errors, previous_selections, expansion_state)
        
        logging.info(f"Calling load_repo with path: {self.repo_path}")
        self.load_repo(self.repo_path, self.gui.show_status_message, completion_callback)

    def get_tree_expansion_state(self):
        """Traverses the tree and returns a set of paths for all open folders."""
        open_folders = set()
        tree = self.gui.structure_tab.tree
       
        def _traverse(item_id):
            if not tree.exists(item_id):
                return
            if tree.item(item_id, 'open'):
                values = tree.item(item_id, 'values')
                if values and 'folder' in tree.item(item_id, 'tags'):
                    open_folders.add(values[0])
               
                for child_id in tree.get_children(item_id):
                    _traverse(child_id)
       
        for root_item in tree.get_children(""):
            _traverse(root_item)
           
        return open_folders

    def apply_tree_expansion_state(self, expansion_state):
        """Traverses the tree and re-opens folders based on the saved state."""
        tree = self.gui.structure_tab.tree
       
        def _traverse_and_apply(item_id):
            if not tree.exists(item_id):
                return
               
            values = tree.item(item_id, 'values')
            if values and 'folder' in tree.item(item_id, 'tags'):
                folder_path = values[0]
                if folder_path in expansion_state:
                    # Expanding the folder will trigger the population of its children
                    self.gui.file_handler.expand_folder(item_id)
                    tree.item(item_id, open=True)
                    # Recurse into children only if the parent was expanded
                    for child_id in tree.get_children(item_id):
                        _traverse_and_apply(child_id)
        for root_item in tree.get_children(""):
            _traverse_and_apply(root_item)
       
        logging.info("Finished applying tree expansion state.")
        self.gui.structure_tab.update_expand_collapse_button()

    def _clear_internal_state(self, clear_ui=False, clear_recent=False):
        """Clears the internal state of the handler."""
        self.repo_path = None
        with self.lock:
            self.loaded_files.clear()
            self.scanned_text_files.clear()
            self.ignore_patterns = []
            self.content_cache.clear()
            self.read_errors.clear()
        self.gui.current_repo_path = None
        if clear_recent:
            self.recent_folders.clear()
            self.gui.recent_folders.clear()
            self.gui.save_recent_folders()
        if clear_ui:
            self._update_ui_for_no_repo()

    def _update_ui_for_no_repo(self):
        """Resets the UI to its initial state when no repo is loaded."""
        self.gui.header_frame.repo_label.config(text="Current Repo: None")
        self.gui.info_label.config(text="Token Count: 0")
        self.gui.cache_info_label.config(text="Cache: 0 items (0 MB)")
        self.gui.structure_tab.clear()
        self.gui.content_tab.clear()
        self.gui.file_list_tab.clear()
        self.gui.refresh_button.config(state=tk.DISABLED)
        self.gui.copy_button.config(state=tk.DISABLED)
        self.gui.copy_structure_button.config(state=tk.DISABLED)
        self.gui.copy_all_button.config(state=tk.DISABLED)
        self.gui.current_token_count = 0

    @classmethod
    def get_extension_groups(cls):
        # (Content Unchanged - assuming it's correct)
        groups = {
            "Programming Languages": [ '.py', '.java', '.cpp', '.c', '.h', '.js', '.ts', '.tsx', '.jsx', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.kts', '.dart', '.groovy', '.scala', '.cs', '.fs', '.fsx', '.lua', '.pl', '.r', '.m', '.mm', '.asm', '.v', '.vhdl', '.verilog', '.s', '.clj', '.cljs', '.cljc', '.edn', '.rkt', '.jl', '.purs', '.elm', '.hs', '.lhs', '.agda', '.idr' ],
            "Markup": [ '.html', '.xml', '.md', '.mdx', '.rst', '.adoc', '.org', '.texinfo' ],
            "Configuration": [ '.json', '.yml', '.yaml', '.toml', '.ini', '.properties', '.gitignore', '.dockerfile', '.make', '.conf', '.cfg', '.env', '.hcl', '.tf', '.nix', '.dhall' ],
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

    def _scan_repo_worker(self, folder, progress_callback, completion_callback):
        """Worker function to run in a separate thread with detailed progress."""
        try:
            logging.info(f"Starting repository scan for {folder}")
            # Check if shutdown was requested
            if self.gui._shutdown_requested:
                logging.info("Shutdown requested, aborting repository scan")
                return
                
            start_time = time.time()
            abs_path = os.path.abspath(folder)
            if not os.path.commonpath([abs_path, os.path.expanduser("~")]).startswith(os.path.expanduser("~")):
                error = SecurityError(
                    "Access outside user directory is not allowed",
                    attempted_path=abs_path,
                    details={"user_home": os.path.expanduser("~"), "attempted_path": abs_path}
                )
                if ERROR_HANDLING_ENABLED:
                    handle_error(error, "_scan_repo_worker", show_ui=True)
                self.gui.task_queue.put((completion_callback, (None, None, set(), set(), ["Security Error: Access outside user directory is not allowed."])))
                return
            repo_path = abs_path
            ignore_patterns = parse_gitignore(os.path.join(repo_path, '.gitignore'))
            errors = []
        
            # --- Collect all non-ignored file paths ---
            file_paths = []
            for file_path_abs in yield_repo_files(repo_path, ignore_patterns, self.gui):
                file_paths.append(file_path_abs)
        
            total_files = len(file_paths)
            # Skip progress bar for first pass since it's too fast to be useful
            print(f"DEBUG: Found {total_files} files, skipping progress bar for fast scan")
        
            # --- Process files ---
            processed_count = 0
            scanned_files_temp = set()
            loaded_files_temp = set()
            scan_start_time = time.time()
            for file_path_abs in file_paths:
                processed_count += 1
            
                if self.is_text_file(file_path_abs):
                    scanned_files_temp.add(file_path_abs)
                    loaded_files_temp.add(file_path_abs)
            
                # Skip progress updates for first pass since it's too fast to be useful
                # Just log occasionally for debugging
                if processed_count % 50 == 0 or processed_count == total_files:
                    elapsed = time.time() - scan_start_time
                    print(f"DEBUG: Processed {processed_count}/{total_files} files in {elapsed:.1f}s")
        
            end_time = time.time()
            logging.info(f"Scan complete for {repo_path}. Found {len(scanned_files_temp)} text files out of {total_files} total files in {end_time - start_time:.2f} seconds.")
            logging.info(f"Putting completion callback in queue with {len(scanned_files_temp)} scanned files")
            self.gui.task_queue.put((completion_callback, (repo_path, ignore_patterns, scanned_files_temp, loaded_files_temp, errors)))
        except Exception as e:
            logging.error(f"Error during repo scan worker: {e}", exc_info=True)
            self.gui.task_queue.put((completion_callback, (None, None, set(), set(), [f"Unexpected scan error: {e}"])))


    def load_repo(self, folder, progress_callback, completion_callback):
        """Starts the repository scan in a background thread."""
        thread = threading.Thread(target=self._scan_repo_worker, args=(folder, progress_callback, completion_callback), daemon=True)
        thread.name = f"RepoScan-{os.path.basename(folder)}"
        self.gui.register_background_thread(thread)
        thread.start()


    def is_text_file(self, file_path):
        try:
            ext = os.path.splitext(file_path)[1].lower()
            text_extensions_settings = self.gui.settings.get('app', 'text_extensions', {ext: 1 for ext in self.text_extensions_default})
            if ext in text_extensions_settings and text_extensions_settings[ext] == 1:
                 filename = os.path.basename(file_path)
                 exclude_files_settings = self.gui.settings.get('app', 'exclude_files', {})
                 if filename in exclude_files_settings and exclude_files_settings[filename] == 1:
                     return False
                 return True
            if ext in text_extensions_settings and text_extensions_settings[ext] == 0:
                 return False
            mime_type, encoding = mimetypes.guess_type(file_path)
            if mime_type and mime_type.startswith('text/'):
                 filename = os.path.basename(file_path)
                 exclude_files_settings = self.gui.settings.get('app', 'exclude_files', {})
                 if filename in exclude_files_settings and exclude_files_settings[filename] == 1:
                     return False
                 return True
        except Exception as e:
            logging.warning(f"Could not determine if {file_path} is text: {e}")
        return False

    def _handle_load_completion(self, repo_path, ignore_patterns, scanned_files, loaded_files, errors):
        """Callback for the *initial* repo load."""
        logging.info(f"Handling initial load completion for {repo_path}")
        self.gui.hide_loading_state()
        if errors or repo_path is None:
            logging.error(f"Load errors: {errors}")
            error_message = "Error loading repository."
            if errors: error_message += f" Details: {'; '.join(errors[:3])}"
            self.gui.show_status_message(error_message, error=True, duration=ERROR_MESSAGE_DURATION)
            messagebox.showerror("Load Error", f"Failed to load repository.\n{error_message}")
            self._clear_internal_state(clear_ui=True)
            return
        # --- Success ---
        self.repo_path = repo_path
        self.gui.current_repo_path = repo_path
       
        file_handler = self.gui.file_handler
        file_handler.repo_path = repo_path
        file_handler.ignore_patterns = ignore_patterns or []
        file_handler.scanned_text_files = scanned_files or set()
       
        with file_handler.lock:
            file_handler.loaded_files = loaded_files or set()
            file_handler.content_cache.clear()
            file_handler.read_errors.clear()
        # Update GUI elements
        repo_name = os.path.basename(repo_path)
        self.gui.header_frame.repo_label.config(text=f"Current Repo: {repo_name}")
        self.gui.refresh_button.config(state=tk.NORMAL)
       
        self.gui.structure_tab.populate_tree(repo_path)
        self.gui.structure_tab.apply_initial_expansion()
        if self.gui.structure_tab.tree.get_children():
            self.gui.copy_structure_button.config(state=tk.NORMAL)
        else:
            self.gui.copy_structure_button.config(state=tk.DISABLED)
        self.gui.trigger_preview_update()
        self.gui.show_status_message(f"Loaded {repo_name} successfully.", duration=STATUS_MESSAGE_DURATION)

    def _handle_refresh_completion(self, repo_path, ignore_patterns, scanned_files, errors, previous_selections, expansion_state):
        """Callback specifically for handling a repository refresh."""
        logging.info(f"Handling refresh completion for {repo_path}")
        self.gui.hide_loading_state()
        if errors or repo_path is None:
            logging.error(f"Refresh errors: {errors}")
            error_message = "Error refreshing repository."
            if errors: error_message += f" Details: {'; '.join(errors[:3])}"
            self.gui.show_status_message(error_message, error=True, duration=ERROR_MESSAGE_DURATION)
            messagebox.showerror("Refresh Error", f"Failed to refresh repository.\n{error_message}")
            # Don't clear state on failed refresh, just report error
            return
        file_handler = self.gui.file_handler
        file_handler.ignore_patterns = ignore_patterns or []
        file_handler.scanned_text_files = scanned_files or set()
        # --- RESTORE STATE ---
        # 1. Restore selections by intersecting old selections with newly scanned files
        with file_handler.lock:
            newly_selected_files = previous_selections.intersection(scanned_files)
            file_handler.loaded_files = newly_selected_files
            logging.debug(f"Restored {len(newly_selected_files)} selections.")
        # 2. Repopulate the tree, which is necessary to show new/deleted files
        self.gui.structure_tab.populate_tree(repo_path)
       
        # 3. Restore the expansion state of the tree
        self.apply_tree_expansion_state(expansion_state)
       
        # --- FINALIZE ---
        self.gui.trigger_preview_update()
        self.gui.show_status_message(f"Refreshed {os.path.basename(repo_path)} successfully.", duration=STATUS_MESSAGE_DURATION)