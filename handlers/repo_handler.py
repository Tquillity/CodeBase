from __future__ import annotations

import logging
import os
import threading
import time
from typing import TYPE_CHECKING, Any, Callable, Optional, Set

import tkinter as tk

from constants import (
    CACHE_MAX_MEMORY_MB,
    CACHE_MAX_SIZE,
    ERROR_HANDLING_ENABLED,
    ERROR_MESSAGE_DURATION,
    FILE_SEPARATOR,
    STATUS_MESSAGE_DURATION,
    TEXT_EXTENSIONS_DEFAULT,
)
from error_handler import handle_error
from exceptions import FileOperationError, RepositoryError, SecurityError
from file_scanner import is_text_file, parse_gitignore, yield_repo_files
from lru_cache import ThreadSafeLRUCache
from path_utils import normalize_for_cache
from widgets import FolderDialog

if TYPE_CHECKING:
    from gui import RepoPromptGUI


class RepoHandler:
    text_extensions_default: set[str] = TEXT_EXTENSIONS_DEFAULT
    FILE_SEPARATOR: str = FILE_SEPARATOR

    gui: RepoPromptGUI
    repo_path: Optional[str]
    loaded_files: set[str]
    scanned_text_files: set[str]
    ignore_patterns: list[str]
    recent_folders: list[str]
    content_cache: Any  # ThreadSafeLRUCache
    lock: threading.Lock
    read_errors: list[str]

    def __init__(self, gui: RepoPromptGUI) -> None:
        self.gui = gui
        self.repo_path = None
        self.loaded_files = set()
        self.scanned_text_files = set()
        self.ignore_patterns = []
        self.recent_folders = gui.load_recent_folders()
        self.content_cache = ThreadSafeLRUCache(CACHE_MAX_SIZE, CACHE_MAX_MEMORY_MB)
        self.lock = threading.Lock()
        self.read_errors = []

    def select_repo(self) -> None:
        """Opens a dialog to select a repository and loads it."""
        if self.gui.is_loading:
            self.gui.show_status_message("Loading...", error=True)
            return
        default_start_folder = self.gui.settings.get('app', 'default_start_folder', os.path.expanduser("~"))
        dialog = FolderDialog(self.gui.root, self.gui.recent_folders, on_delete_callback=self.gui.delete_recent_folder, default_start_folder=default_start_folder, gui=self.gui)
        folder = dialog.show()
        if folder:
            self.gui.update_recent_folders(folder)
            self._clear_internal_state(clear_ui=True)
            self.gui.show_loading_state("Scanning repository...", show_cancel=True)
            self.load_repo(folder, self.gui._queue_loading_progress, self._handle_load_completion)

    def refresh_repo(self) -> None:
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
        self.gui.show_loading_state("Refreshing repository...", show_cancel=True)
        
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
       
        # The completion callback will handle restoring the state
        completion_callback = lambda repo_path, ignore_patterns, scanned, loaded, errors: \
            self._handle_refresh_completion(repo_path, ignore_patterns, scanned, errors, previous_selections, expansion_state)
        
        logging.info(f"Calling load_repo with path: {self.repo_path}")
        self.load_repo(self.repo_path, self.gui._queue_loading_progress, completion_callback)

    def get_tree_expansion_state(self) -> set[str]:
        """Traverses the tree and returns a set of paths for all open folders."""
        open_folders: set[str] = set()
        tree = self.gui.structure_tab.tree

        def _traverse(item_id: str) -> None:
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

    def apply_tree_expansion_state(self, expansion_state: set[str]) -> None:
        """Traverses the tree and re-opens folders based on the saved state."""
        tree = self.gui.structure_tab.tree

        def _traverse_and_apply(item_id: str) -> None:
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

    def _clear_internal_state(self, clear_ui: bool = False, clear_recent: bool = False) -> None:
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
        if hasattr(self.gui, '_git_monitor_id') and self.gui._git_monitor_id:
            self.gui.root.after_cancel(self.gui._git_monitor_id)
            self.gui._git_monitor_id = None

    def _update_ui_for_no_repo(self) -> None:
        """Resets the UI to its initial state when no repo is loaded."""
        self.gui.header_frame.repo_name_label.config(text="None", foreground=self.gui.header_frame.LEGENDARY_GOLD)
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
    def get_extension_groups(cls) -> dict[str, list[str]]:
        groups: dict[str, list[str]] = {
            "Programming Languages": [ '.py', '.java', '.cpp', '.c', '.h', '.js', '.ts', '.tsx', '.jsx', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.kts', '.dart', '.groovy', '.scala', '.cs', '.fs', '.fsx', '.lua', '.pl', '.r', '.m', '.mm', '.asm', '.v', '.vhdl', '.verilog', '.s', '.clj', '.cljs', '.cljc', '.edn', '.rkt', '.jl', '.purs', '.elm', '.hs', '.lhs', '.agda', '.idr' ],
            "Markup": [ '.html', '.xml', '.md', '.mdx', '.rst', '.adoc', '.org', '.texinfo', '.astro' ],
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

    def _scan_repo_worker(
        self,
        folder: str,
        progress_callback: Callable[..., None],
        completion_callback: Callable[..., None],
    ) -> None:
        """Worker function to run in a separate thread with detailed progress and cancel support."""
        try:
            logging.info(f"Starting repository scan for {folder}")
            if getattr(self.gui, '_shutdown_requested', False):
                logging.info("Shutdown requested, aborting repository scan")
                return
            progress_callback("Scanning files...", None, None)

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
            errors: list[str] = []

            # --- Collect all non-ignored file paths (with cancel check) ---
            file_paths = []
            for file_path_abs in yield_repo_files(repo_path, ignore_patterns, self.gui):
                if getattr(self.gui, '_scan_cancel_requested', False):
                    logging.info("Scan cancelled by user during file collection")
                    self.gui.task_queue.put((completion_callback, (None, None, set(), set(), ["Scan cancelled by user."])))
                    return
                file_paths.append(file_path_abs)

            total_files = len(file_paths)
            if total_files == 0:
                progress_callback("Building file list...", 100, "0/0 files")
            else:
                progress_callback("Building file list...", 0, f"0/{total_files} files")

            # --- Process files with progress and cancel checks ---
            processed_count = 0
            scanned_files_temp = set()
            loaded_files_temp = set()
            progress_interval = max(1, min(100, total_files // 20)) if total_files else 1
            for file_path_abs in file_paths:
                if getattr(self.gui, '_scan_cancel_requested', False):
                    logging.info("Scan cancelled by user during processing")
                    self.gui.task_queue.put((completion_callback, (None, None, set(), set(), ["Scan cancelled by user."])))
                    return

                processed_count += 1
                if is_text_file(file_path_abs, self.gui):
                    normalized_path = normalize_for_cache(file_path_abs)
                    scanned_files_temp.add(normalized_path)
                    loaded_files_temp.add(normalized_path)

                if processed_count % progress_interval == 0 or processed_count == total_files:
                    pct = int((processed_count / total_files) * 100) if total_files else 100
                    progress_callback("Scanning...", pct, f"{processed_count}/{total_files} files")

            end_time = time.time()
            logging.info(f"Scan complete for {repo_path}. Found {len(scanned_files_temp)} text files out of {total_files} total files in {end_time - start_time:.2f} seconds.")
            self.gui.task_queue.put((completion_callback, (repo_path, ignore_patterns, scanned_files_temp, loaded_files_temp, errors)))
        except Exception as e:
            logging.error(f"Error during repo scan worker: {e}", exc_info=True)
            self.gui.task_queue.put((completion_callback, (None, None, set(), set(), [f"Unexpected scan error: {e}"])))


    def load_repo(
        self,
        folder: str,
        progress_callback: Callable[..., None],
        completion_callback: Callable[..., None],
    ) -> None:
        """Starts the repository scan in a background thread."""
        thread = threading.Thread(target=self._scan_repo_worker, args=(folder, progress_callback, completion_callback), daemon=True)
        thread.name = f"RepoScan-{os.path.basename(folder)}"
        self.gui.register_background_thread(thread)
        thread.start()


    def _handle_load_completion(
        self,
        repo_path: Optional[str],
        ignore_patterns: Optional[list[str]],
        scanned_files: Set[str],
        loaded_files: Set[str],
        errors: list[str],
    ) -> None:
        """Callback for the *initial* repo load. Keeps progress visible through tree build and preview."""
        logging.info(f"Handling initial load completion for {repo_path}")
        if errors or repo_path is None:
            self.gui.hide_loading_state()
            logging.error(f"Load errors: {errors}")
            error_message = "Error loading repository."
            if errors: error_message += f" Details: {'; '.join(errors[:3])}"
            self.gui.show_status_message(error_message, error=True, duration=ERROR_MESSAGE_DURATION)
            self.gui.show_toast(f"Failed to load repository. {error_message}", toast_type="error")
            self._clear_internal_state(clear_ui=True)
            return
        # --- Success: keep progress bar visible for tree + preview phases ---
        self.gui.show_loading_phase("Building tree...")
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

        repo_name = os.path.basename(repo_path)
        repo_settings = self.gui.settings.get('repo', repo_path, {})
        saved_color = repo_settings.get('color', self.gui.header_frame.LEGENDARY_GOLD)
        self.gui.header_frame.repo_name_label.config(text=repo_name, foreground=saved_color)
        self.gui.refresh_button.config(state=tk.NORMAL)

        self.gui.structure_tab.populate_tree(repo_path)
        self.gui.structure_tab.apply_initial_expansion()
        if self.gui.structure_tab.tree.get_children():
            self.gui.copy_structure_button.config(state=tk.NORMAL)
        else:
            self.gui.copy_structure_button.config(state=tk.DISABLED)
        self.gui.show_loading_phase("Generating preview...")
        self.gui.trigger_preview_update()
        self.gui.show_status_message(f"Loaded {repo_name} successfully.", duration=STATUS_MESSAGE_DURATION)
        self.gui.start_git_status_monitor()

    def _handle_refresh_completion(
        self,
        repo_path: Optional[str],
        ignore_patterns: Optional[list[str]],
        scanned_files: Set[str],
        errors: list[str],
        previous_selections: Set[str],
        expansion_state: set[str],
    ) -> None:
        """Callback for repository refresh. Keeps progress visible through tree build and preview."""
        logging.info(f"Handling refresh completion for {repo_path}")
        if errors or repo_path is None:
            self.gui.hide_loading_state()
            logging.error(f"Refresh errors: {errors}")
            error_message = "Error refreshing repository."
            if errors: error_message += f" Details: {'; '.join(errors[:3])}"
            self.gui.show_status_message(error_message, error=True, duration=ERROR_MESSAGE_DURATION)
            self.gui.show_toast(f"Failed to refresh repository. {error_message}", toast_type="error")
            return
        self.gui.show_loading_phase("Building tree...")
        file_handler = self.gui.file_handler
        file_handler.ignore_patterns = ignore_patterns or []
        file_handler.scanned_text_files = scanned_files or set()

        with file_handler.lock:
            normalized_scanned = {normalize_for_cache(p) for p in scanned_files}
            file_handler.loaded_files = normalized_scanned
            logging.debug(f"Aligned {len(normalized_scanned)} files after refresh.")

        self.gui.structure_tab.populate_tree(repo_path)
        self.apply_tree_expansion_state(expansion_state)

        repo_settings = self.gui.settings.get('repo', repo_path, {})
        saved_color = repo_settings.get('color', self.gui.header_frame.LEGENDARY_GOLD)
        self.gui.header_frame.repo_name_label.config(foreground=saved_color)

        self.gui.show_loading_phase("Generating preview...")
        self.gui.trigger_preview_update()
        self.gui.show_status_message(f"Refreshed {os.path.basename(repo_path)} successfully.", duration=STATUS_MESSAGE_DURATION)
        self.gui.start_git_status_monitor()