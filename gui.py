# gui.py
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, Toplevel, BooleanVar, IntVar, StringVar
from colors import *
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
from handlers.theme_manager import ThemeManager
from panels.panels import HeaderFrame, LeftPanel, RightPanel
import queue  # FIX: Added for thread-safe Tkinter callbacks
from constants import VERSION, DEFAULT_WINDOW_SIZE, DEFAULT_WINDOW_POSITION, STATUS_MESSAGE_DURATION, ERROR_MESSAGE_DURATION, WINDOW_TOP_DURATION

# NEW_LOG: Set level to DEBUG to see all messages
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', filename='codebase_debug.log', filemode='w')
class RepoPromptGUI:
    def __init__(self, root):
        self.root = root
        self.version = VERSION
        self.settings = SettingsManager()
        self.high_contrast_mode = BooleanVar(value=self.settings.get('app', 'high_contrast', 0))
        self.theme_manager = ThemeManager(self)
        self.theme_manager.apply_theme()
        self.root.title(f"CodeBase v{self.version}")
        self.root.geometry(self.settings.get('app', 'window_geometry', DEFAULT_WINDOW_SIZE))
        self.root.configure(bg=self.colors['bg'])
        
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
        self.setup_ui()
        self.bind_keys()
        self.apply_default_tab()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.list_selected_files = set()
        self.list_read_errors = []
        
        # Resource cleanup tracking (must be before _poll_queue)
        self._shutdown_requested = False
        self._background_threads = []
        
        # FIX: Added queue for thread-safe Tkinter callbacks from background threads
        self.task_queue = queue.Queue()
        self._poll_queue()

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
        self.menu = tk.Menu(self.root, bg=self.colors['btn_bg'], fg=self.colors['btn_fg'], tearoff=0)
        self.root.config(menu=self.menu)
        file_menu = tk.Menu(self.menu, bg=self.colors['btn_bg'], fg=self.colors['btn_fg'], tearoff=0)
        self.menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Select Repo", accelerator="Ctrl+R", command=self.repo_handler.select_repo)
        file_menu.add_command(label="Refresh Repo", accelerator="Ctrl+F5", command=self.repo_handler.refresh_repo)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        edit_menu = tk.Menu(self.menu, bg=self.colors['btn_bg'], fg=self.colors['btn_fg'], tearoff=0)
        self.menu.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Copy Contents", accelerator="Ctrl+C", command=self.copy_handler.copy_contents)
        edit_menu.add_command(label="Copy Structure", accelerator="Ctrl+S", command=self.copy_handler.copy_structure)
        edit_menu.add_command(label="Copy All", accelerator="Ctrl+A", command=self.copy_handler.copy_all)
        help_menu = tk.Menu(self.menu, bg=self.colors['btn_bg'], fg=self.colors['btn_fg'], tearoff=0)
        self.menu.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        self.root.grid_rowconfigure(2, weight=1)
        self.root.grid_columnconfigure(2, weight=1)
        self.header_frame = HeaderFrame(self.root, self.colors, title="CodeBase", version=self.version)
        self.left_frame = LeftPanel(self.root, self.colors, self)
        self.left_separator = tk.Frame(self.root, bg=self.colors['btn_bg'], width=2)
        self.left_separator.grid(row=2, column=1, padx=5, pady=10, sticky="ns")
        self.right_frame = RightPanel(self.root, self.colors, self)
        self.setup_status_bar()
        self.progress = ttk.Progressbar(self.root, mode='indeterminate')

    def create_button(self, parent, text, command, tooltip_text=None, state=tk.NORMAL):
        btn = tk.Button(parent, text=text, command=command, bg=self.colors['btn_bg'], fg=self.colors['btn_fg'], state=state)
        btn.bind("<Enter>", lambda e: btn.config(bg=self.colors['btn_hover']))
        btn.bind("<Leave>", lambda e: btn.config(bg=self.colors['btn_bg']))
        if tooltip_text:
            Tooltip(btn, tooltip_text)
        return btn

    def setup_status_bar(self):
        self.status_bar = tk.Label(self.root, text="Ready", bd=1, relief="sunken", anchor="w",
                                   bg=self.colors['bg'], fg=self.colors['status'], padx=5)
        self.status_bar.grid(row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=(5, 10))
        self.status_timer_id = None

    def show_loading_state(self, message):
        self.progress.grid(row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=5)
        self.progress.start()
        self.show_status_message(message, duration=ERROR_MESSAGE_DURATION)
        self.is_loading = True
        self.root.config(cursor="watch")
        self.root.update_idletasks()

    def hide_loading_state(self):
        self.progress.stop()
        self.progress.grid_remove()
        self.is_loading = False
        self.root.config(cursor="")
        self.root.update_idletasks()

    def show_status_message(self, message, duration=STATUS_MESSAGE_DURATION, error=False):
        if self.status_timer_id:
            self.root.after_cancel(self.status_timer_id)
            self.status_timer_id = None
        status_color = self.colors['status']
        if error:
             status_color = '#FF0000'
        self.status_bar.config(text=f" {message}", fg=status_color)
        self.status_timer_id = self.root.after(duration, self.reset_status_bar)

    def reset_status_bar(self):
        self.status_bar.config(text=" Ready", fg=self.colors['status'])
        self.status_timer_id = None

    def update_cache_info(self):
        """Update the cache information display."""
        try:
            stats = self.file_handler.content_cache.stats()
            cache_text = f"Cache: {stats['size']} items ({stats['memory_mb']:.1f} MB)"
            self.cache_info_label.config(text=cache_text)
        except Exception as e:
            logging.warning(f"Error updating cache info: {e}")
            self.cache_info_label.config(text="Cache: Error")

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
            self.settings.set('app', 'exclude_files', {file: var.get() for file, var in self.settings_tab.exclude_file_vars.items()})
            self.settings.set('app', 'search_case_sensitive', self.case_sensitive_var.get())
            self.settings.set('app', 'search_whole_word', self.whole_word_var.get())
            self.settings.set('app', 'include_icons', self.settings_tab.include_icons_var.get())
            self.settings.set('app', 'high_contrast', self.high_contrast_mode.get())
            ext_settings = {ext: var.get() for ext, (cb, var, *_) in self.settings_tab.extension_checkboxes.items()}
            self.settings.set('app', 'text_extensions', ext_settings)
            self.settings.save()
            self.show_status_message("Settings saved successfully.")
            self.theme_manager.apply_theme()
            self.theme_manager.reconfigure_ui_colors()
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
    root = tk.Tk()
    app = RepoPromptGUI(root)
    root.mainloop()