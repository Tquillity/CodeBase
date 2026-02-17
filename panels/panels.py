import ttkbootstrap as ttk
import tkinter as tk
from widgets import Tooltip
from tabs.content_tab import ContentTab
from tabs.structure_tab import StructureTab
from tabs.base_prompt_tab import BasePromptTab
from tabs.settings_tab import SettingsTab
from tabs.file_list_tab import FileListTab
from constants import VERSION, LEFT_PANEL_WIDTH, TEMPLATE_MARKDOWN, TEMPLATE_XML, LEGENDARY_GOLD

class HeaderFrame(ttk.Frame):
    def __init__(self, parent, title="CodeBase", version=VERSION, row_offset=0):
        super().__init__(parent)
        self.grid(row=0 + row_offset, column=0, columnspan=5, padx=12, pady=(12, 0), sticky="ew")

        # Title and version section
        title_frame = ttk.Frame(self)
        title_frame.pack(side=tk.LEFT, fill='y')
        
        self.title_label = ttk.Label(title_frame, text=title, font=("Arial", 16, "bold"))
        self.title_label.pack(side=tk.LEFT, padx=(0, 8))

        self.version_label = ttk.Label(title_frame, text=f"v{version}", font=("Arial", 10))
        self.version_label.pack(side=tk.LEFT, anchor='s')

        # Repository info section
        repo_frame = ttk.Frame(self)
        repo_frame.pack(side=tk.LEFT, fill='both', expand=True, padx=(40, 0))
        
        self.LEGENDARY_GOLD = LEGENDARY_GOLD
        
        self.repo_prefix_label = ttk.Label(
            repo_frame, 
            text="Current Repo: ", 
            font=("Arial", 16, "italic"),
            foreground=self.LEGENDARY_GOLD
        )
        self.repo_prefix_label.pack(side=tk.LEFT, anchor='w')
        
        self.repo_name_label = ttk.Label(
            repo_frame, 
            text="None", 
            font=("Arial", 16, "italic"),
            foreground=self.LEGENDARY_GOLD,
            cursor="hand2"
        )
        self.repo_name_label.pack(side=tk.LEFT, anchor='w')
        
        Tooltip(self.repo_name_label, "Click to change this repository's color")

        # Separator line
        self.header_separator = ttk.Frame(parent, height=1)
        self.header_separator.grid(row=1 + row_offset, column=0, columnspan=5, sticky="ew", padx=12, pady=(8, 8))

class LeftPanel(ttk.Frame):
    def __init__(self, parent, gui, row_offset=0):
        super().__init__(parent, width=LEFT_PANEL_WIDTH)
        self.gui = gui
        self.grid(row=2 + row_offset, column=0, padx=(10, 0), pady=10, sticky="nsw")
        self.grid_propagate(False)
        self.setup_ui()

    def setup_ui(self):
        button_pady = 6
        button_padx = 12
        
        # Main action buttons
        self.gui.select_button = self.gui.create_button(self, "Select Repo (Ctrl+R)", self.gui.repo_handler.select_repo, "Choose a repository folder")
        self.gui.select_button.pack(pady=(button_pady, button_pady), padx=button_padx, fill='x')

        self.gui.refresh_button = self.gui.create_button(self, "Refresh (Ctrl+F5)", self.gui.repo_handler.refresh_repo, "Refresh current repository", state=tk.DISABLED)
        self.gui.refresh_button.pack(pady=(0, button_pady), padx=button_padx, fill='x')

        # Info section with better spacing
        info_frame = ttk.Frame(self)
        info_frame.pack(pady=(10, 15), padx=button_padx, fill='x')
        
        self.gui.info_label = ttk.Label(info_frame, text="Token Count: 0", font=("Arial", 10))
        self.gui.info_label.pack(pady=(0, 3))
        
        self.gui.cache_info_label = ttk.Label(info_frame, text="Cache: 0 items (0 MB)", font=("Arial", 9))
        self.gui.cache_info_label.pack()

        # Copy buttons section
        copy_section_frame = ttk.Frame(self)
        copy_section_frame.pack(pady=(5, 10), padx=button_padx, fill='x')
        
        copy_label = ttk.Label(copy_section_frame, text="Copy Actions", font=("Arial", 9, "bold"))
        copy_label.pack(pady=(0, 5))
        
        self.gui.copy_button = self.gui.create_button(copy_section_frame, "Copy Contents (Ctrl+C)", self.gui.copy_handler.copy_contents, "Copy selected file contents", state=tk.DISABLED)
        self.gui.copy_button.pack(pady=(0, button_pady), padx=0, fill='x')

        self.gui.copy_structure_button = self.gui.create_button(copy_section_frame, "Copy Structure (Ctrl+S)", self.gui.copy_handler.copy_structure, "Copy folder structure", state=tk.DISABLED)
        self.gui.copy_structure_button.pack(pady=(0, button_pady), padx=0, fill='x')

        self.gui.copy_all_button = self.gui.create_button(copy_section_frame, "Copy All (Ctrl+A)", self.gui.copy_handler.copy_all, "Copy prompt, contents, & structure", state=tk.DISABLED)
        self.gui.copy_all_button.pack(pady=(0, button_pady), padx=0, fill='x')

        # Git Actions
        self.gui.copy_diff_button = self.gui.create_button(copy_section_frame, "Copy Git Diff", self.gui.git_handler.copy_diff, "Copy changes (git diff HEAD)")
        self.gui.copy_diff_button.pack(pady=(0, 0), padx=0, fill='x')

        # === GIT STATUS PANEL MOVED TO RIGHT SIDE ===
        # (Git Status is now in GitStatusPanel on the right)

        # Options section
        options_frame = ttk.Frame(self)
        options_frame.pack(pady=(10, 10), padx=button_padx, fill='x')
        
        options_label = ttk.Label(options_frame, text="Options", font=("Arial", 9, "bold"))
        options_label.pack(pady=(0, 5))
        
        # Format Selection Combobox
        format_frame = ttk.Frame(options_frame)
        format_frame.pack(fill='x', pady=(0, 8))
        
        format_label = ttk.Label(format_frame, text="Format:")
        format_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.gui.format_var = tk.StringVar(value=self.gui.settings.get('app', 'copy_format', TEMPLATE_MARKDOWN))
        self.gui.format_combo = ttk.Combobox(format_frame, textvariable=self.gui.format_var, values=[TEMPLATE_MARKDOWN, TEMPLATE_XML], state="readonly")
        self.gui.format_combo.pack(side=tk.LEFT, fill='x', expand=True)
        self.gui.format_combo.bind("<<ComboboxSelected>>", self.on_format_change)
        Tooltip(self.gui.format_combo, "Select output format for copied content")

        self.gui.prepend_checkbox = ttk.Checkbutton(options_frame, text="Prepend Base Prompt", variable=self.gui.prepend_var)
        self.gui.prepend_checkbox.pack(pady=(0, 8), padx=0, fill='x')
        Tooltip(self.gui.prepend_checkbox, "Include Base Prompt text when copying content or 'Copy All'")

        # Neutralize URLs checkbox
        self.gui.sanitize_urls_var = tk.IntVar(value=self.gui.settings.get('app', 'sanitize_urls', 0))
        self.gui.sanitize_urls_checkbox = ttk.Checkbutton(
            options_frame, 
            text="Neutralize URLs", 
            variable=self.gui.sanitize_urls_var,
            command=self.on_sanitize_urls_toggle
        )
        self.gui.sanitize_urls_checkbox.pack(pady=(0, 8), padx=0, fill='x')
        Tooltip(self.gui.sanitize_urls_checkbox, "Replace links with [URL_REDACTED] to fix Google AI Studio preview errors")

        # Test files toggle button
        self.gui.test_toggle_button = self.gui.create_button(options_frame, "With Tests", self.gui.toggle_test_files_and_refresh, "Toggle test files inclusion and refresh repository")
        self.gui.test_toggle_button.pack(pady=(0, 0), padx=0, fill='x')

        # Lock files toggle button
        self.gui.lock_toggle_button = self.gui.create_button(options_frame, "No Locks", self.gui.toggle_lock_files_and_refresh, "Toggle lock files inclusion and refresh repository")
        self.gui.lock_toggle_button.pack(pady=(0, 0), padx=0, fill='x')

        # Clear buttons section at bottom
        self.gui.clear_button_frame = ttk.Frame(self)
        self.gui.clear_button_frame.pack(side='bottom', fill='x', pady=(15, 10), padx=button_padx)
        
        clear_label = ttk.Label(self.gui.clear_button_frame, text="Clear Actions", font=("Arial", 9, "bold"))
        clear_label.pack(pady=(0, 5))

        self.gui.clear_button = self.gui.create_button(self.gui.clear_button_frame, "Clear Current Tab", self.gui.clear_current, "Clear data in the currently active tab")
        self.gui.clear_button.pack(pady=(0, 5), padx=0, fill='x')

        self.gui.clear_all_button = self.gui.create_button(self.gui.clear_button_frame, "Clear All", self.gui.clear_all, "Clear all loaded data and selections")
        self.gui.clear_all_button.pack(pady=(0, 0), padx=0, fill='x')

    def on_format_change(self, event):
        """Handle format selection change."""
        new_format = self.gui.format_var.get()
        self.gui.settings.set('app', 'copy_format', new_format)
        self.gui.settings.save()
        self.gui.trigger_preview_update()

    def on_sanitize_urls_toggle(self):
        """Handle Neutralize URLs checkbox toggle."""
        self.gui.settings.set('app', 'sanitize_urls', self.gui.sanitize_urls_var.get())
        self.gui.settings.save()
        self.gui.trigger_preview_update()

class RightPanel(ttk.Frame):
    def __init__(self, parent, gui, row_offset=0):
        super().__init__(parent)
        self.gui = gui
        self.grid(row=2 + row_offset, column=2, padx=(0, 10), pady=10, sticky="nsew")
        self.setup_ui()

    def on_tab_changed(self, event):
        """Handle tab change event."""
        if hasattr(self.gui, 'search_count_label'):
            self.gui.search_count_label.config(text="")

    def setup_ui(self):
        # Search section with better organization
        search_container = ttk.Frame(self)
        search_container.pack(side=tk.TOP, fill='x', pady=(0, 10), padx=8)
        
        # Search input row
        search_input_frame = ttk.Frame(search_container)
        search_input_frame.pack(fill='x', pady=(0, 5))
        
        self.gui.search_var = ttk.StringVar()
        self.gui.search_entry = ttk.Entry(search_input_frame, textvariable=self.gui.search_var, width=35,
                                     font=("Arial", 10))
        self.gui.search_entry.pack(side=tk.LEFT, padx=(0, 8), ipady=2, fill='x', expand=True)
        Tooltip(self.gui.search_entry, "Enter text to search (Press Enter to search)")

        self.gui.search_button = self.gui.create_button(search_input_frame, "Search", self.gui.search_handler.search_tab, "Search current tab for text")
        self.gui.search_button.pack(side=tk.LEFT, padx=(0, 3))
        
        # Search navigation row
        nav_frame = ttk.Frame(search_container)
        nav_frame.pack(fill='x', pady=(0, 5))
        
        self.gui.next_button = self.gui.create_button(nav_frame, "Next", self.gui.search_handler.next_match, "Go to next search match")
        self.gui.next_button.pack(side=tk.LEFT, padx=(0, 3))
        
        self.gui.prev_button = self.gui.create_button(nav_frame, "Prev", self.gui.search_handler.prev_match, "Go to previous search match")
        self.gui.prev_button.pack(side=tk.LEFT, padx=(0, 3))
        
        self.gui.find_all_button = self.gui.create_button(nav_frame, "All", self.gui.search_handler.find_all, "Highlight all matches in current tab")
        self.gui.find_all_button.pack(side=tk.LEFT, padx=(0, 0))

        self.gui.search_count_label = ttk.Label(nav_frame, text="")
        self.gui.search_count_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Search options row
        options_frame = ttk.Frame(search_container)
        options_frame.pack(fill='x')

        self.gui.case_sensitive_var = ttk.IntVar(value=self.gui.settings.get('app', 'search_case_sensitive', 0))
        self.gui.case_sensitive_checkbox = ttk.Checkbutton(options_frame, text="Case Sensitive", variable=self.gui.case_sensitive_var)
        self.gui.case_sensitive_checkbox.pack(side=tk.LEFT, padx=(0, 8))
        Tooltip(self.gui.case_sensitive_checkbox, "Case Sensitive Search")

        self.gui.whole_word_var = ttk.IntVar(value=self.gui.settings.get('app', 'search_whole_word', 0))
        self.gui.whole_word_checkbox = ttk.Checkbutton(options_frame, text="Whole Word", variable=self.gui.whole_word_var)
        self.gui.whole_word_checkbox.pack(side=tk.LEFT, padx=(0, 0))
        Tooltip(self.gui.whole_word_checkbox, "Match Whole Word Only (Note: Uses basic regex matching)")

        self.gui.search_entry.bind("<Return>", lambda e: self.gui.search_handler.search_tab())
        self.gui.search_entry.bind("<KP_Enter>", lambda e: self.gui.search_handler.search_tab())

        # Notebook styling now handled by ttkbootstrap theme
        self.gui.notebook = ttk.Notebook(self)
        self.gui.notebook.pack(fill="both", expand=True, pady=(0,5))
        self.gui.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        self.gui.content_tab = ContentTab(self.gui.notebook, self.gui, self.gui.file_handler)
        self.gui.notebook.add(self.gui.content_tab, text="Content Preview")

        self.gui.structure_tab = StructureTab(self.gui.notebook, self.gui, self.gui.file_handler, self.gui.settings, self.gui.show_unloaded_var)
        self.gui.notebook.add(self.gui.structure_tab, text="Folder Structure")

        self.gui.base_prompt_tab = BasePromptTab(self.gui.notebook, self.gui, self.gui.template_dir)
        self.gui.notebook.add(self.gui.base_prompt_tab, text="Base Prompt")

        self.gui.settings_tab = SettingsTab(self.gui.notebook, self.gui, self.gui.settings, self.gui.high_contrast_mode)
        self.gui.notebook.add(self.gui.settings_tab, text="Settings")

        # Create the FileListTab instance
        self.gui.file_list_tab = FileListTab(self.gui.notebook, self.gui)
        # Configure its buttons to use its own methods as callbacks
        self.gui.file_list_tab.load_list_button.config(command=self.gui.file_list_tab.load_file_list)
        self.gui.file_list_tab.copy_list_button.config(command=self.gui.file_list_tab.copy_from_list)
        # Add the fully configured tab to the notebook
        self.gui.notebook.add(self.gui.file_list_tab, text="File List Selection")


class GitStatusPanel(ttk.Frame):
    """Dedicated right sidebar for Git Status (VSCode-style)"""
    def __init__(self, parent, gui):
        super().__init__(parent)
        self.gui = gui
        self.pack_propagate(False)
        self.config(width=240)
        self.setup_ui()

    def setup_ui(self):
        ttk.Label(self, text="Git Status", font=("Arial", 11, "bold")).pack(anchor="w", padx=12, pady=(12, 8))

        # Branch
        self.git_branch_label = ttk.Label(self, text="Branch: —", font=("Arial", 9, "italic"))
        self.git_branch_label.pack(anchor="w", padx=12, pady=2)

        ttk.Separator(self).pack(fill='x', padx=12, pady=8)

        # --- Staged Changes ---
        self.staged_label = ttk.Label(self, text="Staged Changes (0)", font=("Arial", 10, "bold"), bootstyle="success")
        self.staged_label.pack(anchor="w", padx=12, pady=(4, 2))

        # Container for List + Scrollbar
        staged_container = ttk.Frame(self)
        staged_container.pack(fill='x', padx=12, pady=4)

        staged_sb = ttk.Scrollbar(staged_container, orient=tk.VERTICAL)
        self.staged_list = tk.Listbox(
            staged_container, height=6, font=("Arial", 9), selectmode=tk.SINGLE,
            bg="#1e1e1e", fg="#9cdcfe", borderwidth=0, highlightthickness=0,
            yscrollcommand=staged_sb.set
        )
        staged_sb.config(command=self.staged_list.yview)

        self.staged_list.pack(side=tk.LEFT, fill='x', expand=True)
        staged_sb.pack(side=tk.RIGHT, fill='y')

        ttk.Button(self, text="Copy All Staged", bootstyle="success-outline",
                   command=self.gui.copy_staged_changes).pack(pady=(2, 10), padx=12, fill='x')

        # --- Unstaged Changes ---
        self.changes_label = ttk.Label(self, text="Changes (0)", font=("Arial", 10, "bold"), bootstyle="warning")
        self.changes_label.pack(anchor="w", padx=12, pady=(8, 2))

        # Container for List + Scrollbar
        changes_container = ttk.Frame(self)
        changes_container.pack(fill='x', padx=12, pady=4)

        changes_sb = ttk.Scrollbar(changes_container, orient=tk.VERTICAL)
        self.changes_list = tk.Listbox(
            changes_container, height=6, font=("Arial", 9), selectmode=tk.SINGLE,
            bg="#1e1e1e", fg="#9cdcfe", borderwidth=0, highlightthickness=0,
            yscrollcommand=changes_sb.set
        )
        changes_sb.config(command=self.changes_list.yview)

        self.changes_list.pack(side=tk.LEFT, fill='x', expand=True)
        changes_sb.pack(side=tk.RIGHT, fill='y')

        ttk.Button(self, text="Copy All Changes", bootstyle="warning-outline",
                   command=self.gui.copy_unstaged_changes).pack(pady=(2, 10), padx=12, fill='x')

        # Refresh
        ttk.Button(self, text="↻ Refresh Git Status", bootstyle="outline",
                   command=self.gui.update_git_status).pack(pady=6, padx=12, fill='x')