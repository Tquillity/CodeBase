# gui.py
import os
import ttkbootstrap as ttk
import tkinter as tk
from tkinter import messagebox, filedialog, Toplevel, BooleanVar, IntVar, StringVar, colorchooser
from typing import Dict, List, Set, Optional, Any, Callable
from tabs.content_tab import ContentTab
from tabs.structure_tab import StructureTab
from tabs.base_prompt_tab import BasePromptTab
from tabs.settings_tab import SettingsTab
from tabs.file_list_tab import FileListTab
from widgets import Tooltip, FolderDialog
from file_handler import FileHandler
from settings import SettingsManager
import appdirs
import logging
import pyperclip
from content_manager import generate_content
from file_scanner import is_text_file
from file_list_handler import generate_list_content
from handlers.search_handler import SearchHandler
from handlers.copy_handler import CopyHandler
from handlers.repo_handler import RepoHandler
from handlers.git_handler import GitHandler
# ThemeManager removed - using ttkbootstrap instead
from panels.panels import HeaderFrame, LeftPanel, RightPanel
import queue  # FIX: Added for thread-safe Tkinter callbacks
from tkinterdnd2 import DND_FILES
from constants import VERSION, DEFAULT_WINDOW_SIZE, DEFAULT_WINDOW_POSITION, STATUS_MESSAGE_DURATION, ERROR_MESSAGE_DURATION, WINDOW_TOP_DURATION, ERROR_HANDLING_ENABLED, DEFAULT_LOG_LEVEL, LOG_TO_FILE, LOG_TO_CONSOLE, LOG_FILE_PATH, LOG_FORMAT
from exceptions import UIError, ConfigurationError, ThreadingError
from error_handler import handle_error, safe_execute, get_error_handler
from logging_config import setup_logging, get_logger

# Setup centralized logging configuration (moved to main.py)
# setup_logging(...) removed to prevent double initialization

class RepoPromptGUI:
    def __init__(self, root: ttk.Window) -> None:
        self.root = root
        self.version = VERSION
        self.settings = SettingsManager()
        self.logger = get_logger(__name__)
        self.high_contrast_mode = BooleanVar(value=self.settings.get('app', 'high_contrast', 0))
        
        # --- FIX: FORCE ROOT BACKGROUND COLOR ---
        # Get the theme's background color and force the root window to use it
        # This covers the gray gaps caused by padding
        style = ttk.Style()
        self.root.configure(background=style.colors.bg)
        # ----------------------------------------
        
        # Theme management now handled by ttkbootstrap
        self.root.title(f"CodeBase v{self.version}")
        self.root.geometry(self.settings.get('app', 'window_geometry', DEFAULT_WINDOW_SIZE))
        # Background color now managed by ttkbootstrap theme
        
        # Quick window visibility check and fix
        current_geometry = self.root.geometry()
        if 'x1' in current_geometry or current_geometry == '1x1+0+0':
            self.root.geometry(f"{DEFAULT_WINDOW_SIZE}{DEFAULT_WINDOW_POSITION}")
        
        # Ensure window is visible (minimal operations)
        self.root.deiconify()
        self.root.lift()
        self.prepend_var = IntVar(value=self.settings.get('app', 'prepend_prompt', 1))
        self.show_unloaded_var = IntVar(value=self.settings.get('app', 'show_unloaded', 0))
        self.user_data_dir = appdirs.user_data_dir("CodeBase")
        self.template_dir = os.path.join(self.user_data_dir, "templates")
        self.recent_folders_file = os.path.join(self.user_data_dir, "recent_folders.txt")
        os.makedirs(self.template_dir, exist_ok=True)
        self.match_positions = {}
        self.current_match_index = {}
        self.recent_folders = self.load_recent_folders()
        self.current_repo_path = None
        self.is_loading = False
        self.current_token_count = 0
        self.file_handler = FileHandler(self)
        self.search_handler = SearchHandler(self)
        self.copy_handler = CopyHandler(self)
        self.repo_handler = RepoHandler(self)
        self.git_handler = GitHandler(self)
        self.setup_ui()
        self.bind_keys()
        
        # Register drag and drop
        try:
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind('<<Drop>>', self._on_drop)
        except Exception as e:
            self.logger.warning(f"Drag and drop registration failed: {e}")
            
        self.apply_default_tab()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Update test toggle button after UI is fully initialized
        if hasattr(self, 'test_toggle_button'):
            self.update_test_toggle_button()
        self.list_selected_files = set()
        self.list_read_errors = []
        
        # Resource cleanup tracking (must be before _poll_queue)
        self._shutdown_requested = False
        self._background_threads = []
        
        # FIX: Added queue for thread-safe Tkinter callbacks from background threads
        self.task_queue = queue.Queue()
        
        # Update logging configuration based on settings
        self._update_logging_config()
        
        self._poll_queue()

    def _on_drop(self, event):
        """Handle file/folder drop events."""
        try:
            path = event.data
            if not path: return
            
            # Clean up path (Tcl/Tk wraps paths with spaces in curly braces)
            if path.startswith('{') and path.endswith('}'):
                path = path[1:-1]
            
            # Handle multiple files drop - take the first one if space separated
            # This is a simplified approach; robust regex parsing is better for complex cases
            # but tkinterdnd2 usually handles single file drops well.
            # If multiple paths are wrapped in {}, we might need regex.
            # For now, let's assume single folder drop for simplicity or take first.
            
            # Verify path exists
            if not os.path.exists(path):
                self.show_status_message(f"Invalid path dropped: {path}", error=True)
                return
                
            if os.path.isdir(path):
                self.show_status_message(f"Loading dropped repository: {path}")
                self.update_recent_folders(path)
                self.repo_handler._clear_internal_state(clear_ui=True)
                self.show_loading_state(f"Scanning {os.path.basename(path)}...", show_cancel=True)
                self.repo_handler.load_repo(path, self.show_status_message, self.repo_handler._handle_load_completion)
            else:
                self.show_status_message("Please drop a folder, not a file.", error=True)
                
        except Exception as e:
            self.logger.error(f"Error handling drop event: {e}")
            self.show_status_message("Error processing dropped item.", error=True)

    def _update_logging_config(self):
        """Update logging configuration based on user settings."""
        try:
            from logging_config import LoggingConfig
            
            # Get logging settings from user preferences
            log_level = self.settings.get('app', 'log_level', DEFAULT_LOG_LEVEL)
            log_to_file = self.settings.get('app', 'log_to_file', 1) == 1
            log_to_console = self.settings.get('app', 'log_to_console', 1) == 1
            
            # Update logging configuration
            LoggingConfig.setup_logging(
                level=log_level,
                log_file=LOG_FILE_PATH if log_to_file else None,
                console_output=log_to_console,
                format_string=LOG_FORMAT,
                force=True
            )
            
            self.logger.info(f"Logging configured: level={log_level}, file={log_to_file}, console={log_to_console}")
            
        except Exception as e:
            self.logger.error(f"Failed to update logging configuration: {e}")

    # FIX: Polling method to process queued tasks in the main thread
    def _poll_queue(self):
        # Stop polling if shutdown requested
        if self._shutdown_requested:
            return
            
        try:
            # Process all available tasks in the queue
            while True:
                task = self.task_queue.get_nowait()
                if isinstance(task, tuple) and len(task) == 2:
                    func, args = task
                    try:
                        func(*args)
                    except Exception as e:
                        logging.error(f"Error executing queued task: {e}")
        except queue.Empty:
            pass
        except Exception as e:
            logging.error(f"Error in queue polling: {e}")
        finally:
            # Schedule next poll only if not shutting down
            if not self._shutdown_requested:
                self.root.after(50, self._poll_queue)  # Poll every 50ms for better responsiveness

    def trigger_preview_update(self):
        """Triggers the generation of the content preview tab."""
        # NEW_LOG
        logging.info("Triggering preview update")
        if self.is_loading:
            return
        if self.current_repo_path:
            self.show_status_message("Updating content preview...")
            # Disable copy buttons while updating
            self.copy_button.config(state=tk.DISABLED)
            self.copy_all_button.config(state=tk.DISABLED)
            self.file_handler.generate_and_update_preview(None, self.content_tab._handle_preview_completion)

    def load_recent_folders(self):
        if os.path.exists(self.recent_folders_file):
            try:
                with open(self.recent_folders_file, 'r', encoding='utf-8') as file:
                    folders = [line.strip() for line in file if line.strip()]
                    return folders
            except Exception as e:
                logging.error(f"Error loading recent folders from {self.recent_folders_file}: {e}")
        return []

    def save_recent_folders(self):
        try:
            with open(self.recent_folders_file, 'w', encoding='utf-8') as file:
                for folder in self.recent_folders:
                    file.write(f"{folder}\n")
        except Exception as e:
            logging.error(f"Error saving recent folders to {self.recent_folders_file}: {e}")

    def update_recent_folders(self, new_folder):
        if not new_folder: return
        abs_path = os.path.abspath(new_folder)
        
        # Validate folder exists and is not a dummy folder
        if not os.path.exists(abs_path) or not os.path.isdir(abs_path):
            return
        if abs_path.startswith('/folder') and abs_path[7:].isdigit():
            return  # Skip dummy folders like /folder1, /folder2, etc.
            
        if abs_path in self.recent_folders:
            self.recent_folders.remove(abs_path)
        self.recent_folders.insert(0, abs_path)
        max_recent = 20
        self.recent_folders = self.recent_folders[:max_recent]
        self.save_recent_folders()

    def delete_recent_folder(self, folder_to_delete):
        """Removes a specific folder from the recent list and saves the change."""
        if folder_to_delete in self.recent_folders:
            self.recent_folders.remove(folder_to_delete)
            self.save_recent_folders()
            logging.info(f"Removed recent folder: {folder_to_delete}")

    def setup_ui(self):
        self.menu = tk.Menu(self.root, tearoff=0)
        self.root.config(menu=self.menu)
        file_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Select Repo", accelerator="Ctrl+R", command=self.repo_handler.select_repo)
        file_menu.add_command(label="Refresh Repo", accelerator="Ctrl+F5", command=self.repo_handler.refresh_repo)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        edit_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Copy Contents", accelerator="Ctrl+C", command=self.copy_handler.copy_contents)
        edit_menu.add_command(label="Copy Structure", accelerator="Ctrl+S", command=self.copy_handler.copy_structure)
        edit_menu.add_command(label="Copy All", accelerator="Ctrl+A", command=self.copy_handler.copy_all)
        help_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        self.root.grid_rowconfigure(2, weight=1)
        self.root.grid_columnconfigure(2, weight=1)
        self.header_frame = HeaderFrame(self.root, title="CodeBase", version=self.version)
        self.header_frame.repo_name_label.bind("<Button-1>", self.change_repo_color)
        self.left_frame = LeftPanel(self.root, self)
        self.left_separator = ttk.Frame(self.root, width=2)
        self.left_separator.grid(row=2, column=1, padx=8, pady=15, sticky="ns")
        self.right_frame = RightPanel(self.root, self)
        self.setup_status_bar()
        # Create large file counter display instead of progress bar
        self.file_counter = ttk.Label(self.root, text="", font=("Arial", 36, "bold"))
        self._style_file_counter()

    def create_button(self, parent, text, command, tooltip_text=None, state=tk.NORMAL, bootstyle="primary"):
        btn = ttk.Button(parent, text=text, command=command, state=state, bootstyle=bootstyle)
        if tooltip_text:
            Tooltip(btn, tooltip_text)
        return btn

    def setup_status_bar(self):
        self.status_bar = ttk.Label(self.root, text="Ready", anchor="w")
        self.status_bar.grid(row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=(5, 10))
        self.status_timer_id = None
        
        # Add right-click context menu to status bar
        self.status_bar.bind("<Button-3>", self._show_status_context_menu)
        self.status_bar.bind("<Button-2>", self._show_status_context_menu)  # Middle click for Linux

        # Create status bar context menu once
        self.status_context_menu = tk.Menu(self.root, tearoff=0)
        self.status_context_menu.add_command(label="Copy", command=self._copy_status_bar)
        self.status_context_menu.add_command(label="Paste", command=self._paste_to_status_bar)
        self.status_context_menu.add_separator()
        self.status_context_menu.add_command(label="Clear", command=self._clear_status_bar)

    def show_loading_state(self, message: str, show_cancel: bool = False) -> None:
        print(f"DEBUG: show_loading_state called with message: {message}")
        
        # Show file counter in center of screen
        print("DEBUG: Showing file counter")
        self.file_counter.grid(row=2, column=0, columnspan=3, padx=30, pady=30)
        
        # Initialize file counter (don't show "0" initially)
        print("DEBUG: Initializing file counter")
        self.file_counter.config(text="")
        print(f"DEBUG: File counter initialized - text: {self.file_counter.cget('text')}")
        
        self.show_status_message(message, duration=ERROR_MESSAGE_DURATION)
        self.is_loading = True
        self.root.config(cursor="watch")
        
        # Add cancel button if requested
        if show_cancel and not hasattr(self, 'cancel_button'):
            self.cancel_button = self.create_button(
                self.root, 
                "Cancel", 
                self.cancel_operation,
                "Cancel the current operation"
            )
            self.cancel_button.grid(row=3, column=2, padx=10, pady=5, sticky="e")
        elif not show_cancel and hasattr(self, 'cancel_button'):
            self.cancel_button.grid_remove()
            
        self.root.update_idletasks()

    def hide_loading_state(self) -> None:
        self.file_counter.grid_remove()
        self.is_loading = False
        self.root.config(cursor="")
        
        # Remove cancel button if it exists
        if hasattr(self, 'cancel_button'):
            self.cancel_button.grid_remove()
            
        self.root.update_idletasks()

    def cancel_operation(self) -> None:
        """Cancel the current operation."""
        if hasattr(self, '_shutdown_requested'):
            self._shutdown_requested = True
            self.show_status_message("Operation cancelled by user", error=True)
            self.hide_loading_state()
        else:
            self.show_status_message("No operation to cancel", error=True)

    def show_status_message(self, message: str, duration: int = STATUS_MESSAGE_DURATION, error: bool = False) -> None:
        if self.status_timer_id:
            self.root.after_cancel(self.status_timer_id)
            self.status_timer_id = None
        # Status bar color now managed by ttkbootstrap theme
        if error:
            self.status_bar.config(text=f" {message}", bootstyle="danger")
        else:
            self.status_bar.config(text=f" {message}")
        self.status_timer_id = self.root.after(duration, self.reset_status_bar)

    def reset_status_bar(self):
        self.status_bar.config(text=" Ready")
        self.status_timer_id = None

    def _show_status_context_menu(self, event):
        """Show right-click context menu for status bar."""
        try:
            # Show context menu at cursor position
            self.status_context_menu.tk_popup(event.x_root, event.y_root)
        except Exception as e:
            logging.error(f"Error showing status context menu: {e}")
        finally:
             self.status_context_menu.grab_release()

    def _paste_to_status_bar(self):
        """Paste clipboard content to status bar."""
        try:
            import pyperclip
            clipboard_content = pyperclip.paste()
            if clipboard_content:
                # Clear any existing timer
                if self.status_timer_id:
                    self.root.after_cancel(self.status_timer_id)
                    self.status_timer_id = None
                
                # Show pasted content in status bar
                self.status_bar.config(text=f" {clipboard_content}")
                logging.info(f"Pasted to status bar: {clipboard_content[:50]}...")
            else:
                self.show_status_message("Clipboard is empty", error=True)
        except Exception as e:
            logging.error(f"Error pasting to status bar: {e}")
            self.show_status_message("Error pasting from clipboard", error=True)

    def _copy_status_bar(self):
        """Copy status bar content to clipboard."""
        try:
            import pyperclip
            # Get the current status bar text (remove leading space if present)
            status_text = self.status_bar.cget("text").strip()
            if status_text and status_text != "Ready":
                pyperclip.copy(status_text)
                self.show_status_message(f"Copied: {status_text[:30]}...", duration=2000)
                logging.info(f"Copied status bar content: {status_text}")
            else:
                self.show_status_message("Nothing to copy", error=True)
        except Exception as e:
            logging.error(f"Error copying status bar: {e}")
            self.show_status_message("Error copying to clipboard", error=True)

    def _clear_status_bar(self):
        """Clear the status bar."""
        self.reset_status_bar()

    def _style_file_counter(self):
        """Style the file counter display to match the application theme."""
        self.file_counter.config(
            font=("Arial", 36, "bold")
        )

    def reconfigure_file_counter(self):
        """Reconfigure file counter styling when theme changes."""
        self._style_file_counter()

    def update_progress(self, percentage: int, message: str = None, file_count: str = None):
        """Update the file counter display."""
        try:
            percentage = max(0, min(100, percentage))  # Clamp between 0-100
            print(f"DEBUG: update_progress called with percentage={percentage}, message={message}, file_count={file_count}")
            
            # Check if file counter exists
            if not hasattr(self, 'file_counter'):
                print("DEBUG: File counter not found!")
                return
                
            # Show file count if available, otherwise percentage
            if file_count:
                # Show the full "X/Y files" format
                self.file_counter.config(text=file_count)
                print(f"DEBUG: File counter set to: {file_count}")
            else:
                self.file_counter.config(text=f"{percentage}%")
                print(f"DEBUG: File counter set to percentage: {percentage}%")
                
            print(f"DEBUG: File counter text set to {self.file_counter.cget('text')}")
            
            if message:
                print(f"DEBUG: Showing status message: {message}")
                self.show_status_message(message, duration=1000)
            
            # Force immediate UI update
            print("DEBUG: Forcing UI update")
            self.root.update_idletasks()
            self.root.update()
            print("DEBUG: UI update completed")
        except Exception as e:
            print(f"DEBUG: Error updating progress: {e}")
            logging.warning(f"Error updating progress: {e}")

    def set_progress_max(self, max_value: int):
        """Set the maximum value for the progress bar."""
        try:
            self.progress['maximum'] = max_value
        except Exception as e:
            logging.warning(f"Error setting progress max: {e}")

    def update_cache_info(self):
        """Update the cache information display."""
        try:
            stats = self.file_handler.content_cache.stats()
            cache_text = f"Cache: {stats['size']} items ({stats['memory_mb']:.1f} MB)"
            self.cache_info_label.config(text=cache_text)
        except Exception as e:
            logging.warning(f"Error updating cache info: {e}")
            self.cache_info_label.config(text="Cache: Error")

    def toggle_test_files_and_refresh(self):
        """Toggle test files exclusion and refresh the current repository."""
        try:
            if not self.current_repo_path:
                self.show_status_message("No repository loaded", error=True)
                return
                
            # Toggle the setting
            current_setting = self.settings.get('app', 'exclude_test_files', 0)
            new_setting = 1 if current_setting == 0 else 0
            self.settings.set('app', 'exclude_test_files', new_setting)
            self.settings.save()
            
            # Debug logging
            logging.info(f"Test files exclusion toggled: {current_setting} -> {new_setting}")
            logging.info(f"Settings file saved. Reading back: {self.settings.get('app', 'exclude_test_files', 0)}")
            
            # Force reload settings to ensure we have the latest value
            self.settings.settings = self.settings.load_settings()
            logging.info(f"After reload, setting is: {self.settings.get('app', 'exclude_test_files', 0)}")
            
            # Update button appearance
            self.update_test_toggle_button()
            
            # Show status message
            if new_setting:
                self.show_status_message("Refreshing repository without test files...")
            else:
                self.show_status_message("Refreshing repository with test files...")
            
            # Force a complete reload of the repository with the new setting
            repo_path = self.current_repo_path  # Preserve the path before clearing
            self.repo_handler._clear_internal_state(clear_ui=False, clear_recent=False)
            self.repo_handler.load_repo(repo_path, self.show_status_message, self.repo_handler._handle_load_completion)
                
        except Exception as e:
            logging.error(f"Error toggling test files exclusion: {e}")
            self.show_status_message("Error updating test files setting", error=True)

    def update_test_toggle_button(self):
        """Update the test toggle button appearance based on current setting."""
        try:
            exclude_tests = self.settings.get('app', 'exclude_test_files', 0)
            
            if exclude_tests:
                # Red button - excluding tests
                self.test_toggle_button.config(text="No Tests")
                self.test_toggle_button.configure(bootstyle="danger")
            else:
                # Green button - including tests
                self.test_toggle_button.config(text="With Tests")
                self.test_toggle_button.configure(bootstyle="success")
                
        except Exception as e:
            logging.error(f"Error updating test toggle button: {e}")

    def clear_current(self):
        if self.is_loading: self.show_status_message("Loading...", error=True); return
        current_index = self.notebook.index('current')
        cleared = False
        if current_index == 0:
            self.content_tab.clear()
            cleared = True
        elif current_index == 1:
             if messagebox.askyesno("Confirm Clear", "Clearing the structure requires reloading the repository. Proceed?"):
                 self.clear_all()
                 cleared = True
             else:
                 return
        elif current_index == 2:
            self.base_prompt_tab.clear()
            cleared = True
        elif current_index == 3:
             self.show_status_message("Settings tab cannot be cleared this way.")
             return
        elif current_index == 4:
            self.file_list_tab.clear()
            cleared = True
        if cleared:
             self.show_status_message("Current tab content cleared.")

    def clear_all(self):
        if self.is_loading: self.show_status_message("Loading...", error=True); return
        if messagebox.askyesno("Confirm Clear All", "This will clear all loaded data, selections, and the current repository view. Are you sure?"):
            self.repo_handler._clear_internal_state(clear_recent=False)
            self.content_tab.clear()
            self.structure_tab.clear()
            self.base_prompt_tab.clear()
            self.file_list_tab.clear()
            self.repo_handler._update_ui_for_no_repo()
            self.show_status_message("All data cleared.")

    def save_app_settings(self):
        try:
            self.settings.set('app', 'default_tab', self.settings_tab.default_tab_var.get())
            self.settings.set('app', 'prepend_prompt', self.prepend_var.get())
            self.settings.set('app', 'show_unloaded', self.show_unloaded_var.get())
            self.settings.set('app', 'expansion', self.settings_tab.expansion_var.get())
            levels = self.settings_tab.levels_entry.get()
            if levels.isdigit():
                 self.settings.set('app', 'levels', int(levels))
            else:
                 self.settings.set('app', 'levels', 1)
            self.settings.set('app', 'exclude_node_modules', self.settings_tab.exclude_node_modules_var.get())
            self.settings.set('app', 'exclude_dist', self.settings_tab.exclude_dist_var.get())
            self.settings.set('app', 'exclude_coverage', self.settings_tab.exclude_coverage_var.get())
            self.settings.set('app', 'exclude_files', {file: var.get() for file, var in self.settings_tab.exclude_file_vars.items()})
            self.settings.set('app', 'search_case_sensitive', self.case_sensitive_var.get())
            self.settings.set('app', 'search_whole_word', self.whole_word_var.get())
            self.settings.set('app', 'include_icons', self.settings_tab.include_icons_var.get())
            self.settings.set('app', 'high_contrast', self.high_contrast_mode.get())
            ext_settings = {ext: var.get() for ext, (cb, var, *_) in self.settings_tab.extension_checkboxes.items()}
            self.settings.set('app', 'text_extensions', ext_settings)
            
            # Save new configurable settings
            # Performance settings
            try:
                cache_max_size = int(self.settings_tab.cache_max_size_var.get())
                self.settings.set('app', 'cache_max_size', cache_max_size)
            except ValueError:
                pass
            
            try:
                cache_max_memory = int(self.settings_tab.cache_max_memory_var.get())
                self.settings.set('app', 'cache_max_memory_mb', cache_max_memory)
            except ValueError:
                pass
            
            try:
                tree_max_items = int(self.settings_tab.tree_max_items_var.get())
                self.settings.set('app', 'tree_max_items', tree_max_items)
            except ValueError:
                pass
            
            # Security settings
            self.settings.set('app', 'security_enabled', self.settings_tab.security_enabled_var.get())
            try:
                max_file_size = int(self.settings_tab.max_file_size_var.get())
                self.settings.set('app', 'max_file_size_mb', max_file_size)
            except ValueError:
                pass
            
            # Logging settings
            self.settings.set('app', 'log_level', self.settings_tab.log_level_var.get())
            self.settings.set('app', 'log_to_file', self.settings_tab.log_to_file_var.get())
            self.settings.set('app', 'log_to_console', self.settings_tab.log_to_console_var.get())
            
            # Folder selection settings
            self.settings.set('app', 'default_start_folder', self.settings_tab.default_start_folder_var.get())
            
            self.settings.save()
            self.show_status_message("Settings saved successfully.")
            # Theme is now managed by ttkbootstrap automatically
            self.apply_default_tab()
            if self.current_repo_path:
                 self.show_status_message("Settings saved. Refreshing repository view...")
                 self.root.after(WINDOW_TOP_DURATION, self.repo_handler.refresh_repo)
        except Exception as e:
            logging.error(f"Error saving settings: {e}", exc_info=True)
            messagebox.showerror("Settings Error", f"Could not save settings:\n{e}")

    def apply_default_tab(self):
        default_tab_name = self.settings.get('app', 'default_tab', 'Content Preview')
        try:
            for i in range(self.notebook.index('end')):
                if self.notebook.tab(i, "text") == default_tab_name:
                    self.notebook.select(i)
                    break
        except tk.TclError:
             logging.warning("Could not select default tab, notebook might not be ready.")

    def show_about(self):
        messagebox.showinfo("About CodeBase",
                            f"CodeBase v{self.version}\n\n"
                            "A tool to scan local code repositories, preview text files, "
                            "and copy contents or structure to the clipboard.\n\n"
                            "Developed by Mikael Sundh.\n"
                            "License: MIT (To be finalized)\n"
                            "© 2024-2025")

    def change_repo_color(self, event=None):
        if not self.current_repo_path:
            return
        current_color = self.header_frame.repo_name_label.cget("foreground")
        _, color_code = colorchooser.askcolor(title="Choose Repo Color", initialcolor=current_color)
        if color_code:
            self.header_frame.repo_name_label.config(foreground=color_code)
            repo_data = self.settings.get('repo', self.current_repo_path, {})
            repo_data['color'] = color_code
            self.settings.set('repo', self.current_repo_path, repo_data)
            self.settings.save()
            self.show_status_message(f"Repository color updated to {color_code}")

    def on_close(self):
        """Handle application shutdown with proper resource cleanup."""
        logging.info("Starting application shutdown...")
        
        # Set shutdown flag to stop background operations
        self._shutdown_requested = True
        
        # Save settings
        try:
            self.settings.set('app', 'window_geometry', self.root.geometry())
            self.settings.save()
            logging.info("Settings saved successfully.")
        except Exception as e:
            logging.error(f"Error saving settings: {e}")
        
        # Clean up resources
        self._cleanup_resources()
        
        # Destroy the window
        try:
            self.root.destroy()
            logging.info("Application closed successfully.")
        except Exception as e:
            logging.error(f"Error during window destruction: {e}")
    
    def _cleanup_resources(self):
        """Clean up all application resources."""
        logging.info("Cleaning up resources...")
        
        # Clear content cache
        try:
            if hasattr(self.file_handler, 'content_cache'):
                self.file_handler.content_cache.clear()
                logging.info("Content cache cleared.")
        except Exception as e:
            logging.error(f"Error clearing content cache: {e}")
        
        # Clear repo handler cache
        try:
            if hasattr(self.repo_handler, 'content_cache'):
                self.repo_handler.content_cache.clear()
                logging.info("Repo handler cache cleared.")
        except Exception as e:
            logging.error(f"Error clearing repo handler cache: {e}")
        
        # Wait for background threads to finish (with timeout)
        self._wait_for_threads(timeout=5.0)
        
        # Clear task queue
        try:
            while not self.task_queue.empty():
                try:
                    self.task_queue.get_nowait()
                except queue.Empty:
                    break
            logging.info("Task queue cleared.")
        except Exception as e:
            logging.error(f"Error clearing task queue: {e}")
        
        # Clear file lists
        try:
            self.list_selected_files.clear()
            self.list_read_errors.clear()
            logging.info("File lists cleared.")
        except Exception as e:
            logging.error(f"Error clearing file lists: {e}")
    
    def _wait_for_threads(self, timeout=5.0):
        """Wait for background threads to complete with timeout."""
        import time
        
        start_time = time.time()
        while self._background_threads and (time.time() - start_time) < timeout:
            # Remove completed threads
            self._background_threads = [t for t in self._background_threads if t.is_alive()]
            if self._background_threads:
                time.sleep(0.1)  # Short sleep to avoid busy waiting
        
        if self._background_threads:
            logging.warning(f"Some background threads did not complete within {timeout}s timeout")
        else:
            logging.info("All background threads completed successfully.")
    
    def register_background_thread(self, thread):
        """Register a background thread for cleanup tracking."""
        self._background_threads.append(thread)
        logging.debug(f"Registered background thread: {thread.name}")

    def bind_keys(self):
        self.root.bind('<Control-r>', lambda e: self.repo_handler.select_repo())
        self.root.bind('<Control-F5>', lambda e: self.repo_handler.refresh_repo())
        self.root.bind('<Control-c>', lambda e: self.copy_handler.copy_contents())
        self.root.bind('<Control-s>', lambda e: self.copy_handler.copy_structure())
        self.root.bind('<Control-a>', lambda e: self.copy_handler.copy_all())
        self.root.bind('<Control-t>', lambda e: self.base_prompt_tab.save_template())
        self.root.bind('<Control-l>', lambda e: self.base_prompt_tab.load_template())
if __name__ == "__main__":
    root = ttk.Window(themename="darkly")
    app = RepoPromptGUI(root)
    root.mainloop()