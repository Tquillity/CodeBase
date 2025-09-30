import ttkbootstrap as ttk
from widgets import Tooltip
from tabs.content_tab import ContentTab
from tabs.structure_tab import StructureTab
from tabs.base_prompt_tab import BasePromptTab
from tabs.settings_tab import SettingsTab
from tabs.file_list_tab import FileListTab
from constants import VERSION, LEFT_PANEL_WIDTH

class HeaderFrame(ttk.Frame):
    def __init__(self, parent, title="CodeBase", version=VERSION):
        super().__init__(parent)
        self.grid(row=0, column=0, columnspan=3, padx=10, pady=(10,0), sticky="ew")

        self.title_label = ttk.Label(self, text=title, font=("Arial", 16))
        self.title_label.pack(side=ttk.LEFT, padx=(0, 5))

        self.version_label = ttk.Label(self, text=f"v{version}", font=("Arial", 10))
        self.version_label.pack(side=ttk.LEFT, anchor='s')

        self.repo_label = ttk.Label(self, text="Current Repo: None", font=("Arial", 12))
        self.repo_label.pack(side=ttk.LEFT, padx=50)

        self.header_separator = ttk.Frame(parent, height=1)
        self.header_separator.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=(0,5))

class LeftPanel(ttk.Frame):
    def __init__(self, parent, gui):
        super().__init__(parent, width=LEFT_PANEL_WIDTH)
        self.gui = gui
        self.grid(row=2, column=0, padx=(10, 0), pady=10, sticky="nsw")
        self.grid_propagate(False)
        self.setup_ui()

    def setup_ui(self):
        button_pady = 8
        self.gui.select_button = self.gui.create_button(self, "Select Repo (Ctrl+R)", self.gui.repo_handler.select_repo, "Choose a repository folder")
        self.gui.select_button.pack(pady=button_pady, padx=10, fill='x')

        self.gui.refresh_button = self.gui.create_button(self, "Refresh (Ctrl+F5)", self.gui.repo_handler.refresh_repo, "Refresh current repository", state=ttk.DISABLED)
        self.gui.refresh_button.pack(pady=button_pady, padx=10, fill='x')

        self.gui.info_label = ttk.Label(self, text="Token Count: 0", font=("Arial", 10))
        self.gui.info_label.pack(pady=8)
        
        self.gui.cache_info_label = ttk.Label(self, text="Cache: 0 items (0 MB)", font=("Arial", 9))
        self.gui.cache_info_label.pack(pady=5)

        self.gui.copy_button = self.gui.create_button(self, "Copy Contents (Ctrl+C)", self.gui.copy_handler.copy_contents, "Copy selected file contents", state=ttk.DISABLED)
        self.gui.copy_button.pack(pady=button_pady, padx=10, fill='x')

        self.gui.copy_structure_button = self.gui.create_button(self, "Copy Structure (Ctrl+S)", self.gui.copy_handler.copy_structure, "Copy folder structure", state=ttk.DISABLED)
        self.gui.copy_structure_button.pack(pady=button_pady, padx=10, fill='x')

        self.gui.copy_all_button = self.gui.create_button(self, "Copy All (Ctrl+A)", self.gui.copy_handler.copy_all, "Copy prompt, contents, & structure", state=ttk.DISABLED)
        self.gui.copy_all_button.pack(pady=button_pady, padx=10, fill='x')

        self.gui.prepend_checkbox = ttk.Checkbutton(self, text="Prepend Base Prompt", variable=self.gui.prepend_var)
        self.gui.prepend_checkbox.pack(pady=10, padx=15, fill='x')
        Tooltip(self.gui.prepend_checkbox, "Include Base Prompt text when copying content or 'Copy All'")

        self.gui.clear_button_frame = ttk.Frame(self)
        self.gui.clear_button_frame.pack(side='bottom', fill='x', pady=(20, 10))

        self.gui.clear_button = self.gui.create_button(self.gui.clear_button_frame, "Clear Current Tab", self.gui.clear_current, "Clear data in the currently active tab")
        self.gui.clear_button.pack(pady=5, padx=10, fill='x')

        self.gui.clear_all_button = self.gui.create_button(self.gui.clear_button_frame, "Clear All", self.gui.clear_all, "Clear all loaded data and selections")
        self.gui.clear_all_button.pack(pady=5, padx=10, fill='x')

class RightPanel(ttk.Frame):
    def __init__(self, parent, gui):
        super().__init__(parent)
        self.gui = gui
        self.grid(row=2, column=2, padx=(0, 10), pady=10, sticky="nsew")
        self.setup_ui()

    def setup_ui(self):
        self.gui.search_frame = ttk.Frame(self)
        self.gui.search_frame.pack(side=ttk.TOP, fill='x', pady=(0, 10), padx=5)

        self.gui.search_var = ttk.StringVar()
        self.gui.search_entry = ttk.Entry(self.gui.search_frame, textvariable=self.gui.search_var, width=40,
                                     font=("Arial", 10))
        self.gui.search_entry.pack(side=ttk.LEFT, padx=(0, 5), ipady=3)
        Tooltip(self.gui.search_entry, "Enter text to search (Press Enter to search)")

        self.gui.search_button = self.gui.create_button(self.gui.search_frame, "Search", self.gui.search_handler.search_tab, "Search current tab for text")
        self.gui.search_button.pack(side=ttk.LEFT, padx=2)
        self.gui.next_button = self.gui.create_button(self.gui.search_frame, "Next", self.gui.search_handler.next_match, "Go to next search match")
        self.gui.next_button.pack(side=ttk.LEFT, padx=2)
        self.gui.prev_button = self.gui.create_button(self.gui.search_frame, "Prev", self.gui.search_handler.prev_match, "Go to previous search match")
        self.gui.prev_button.pack(side=ttk.LEFT, padx=2)
        self.gui.find_all_button = self.gui.create_button(self.gui.search_frame, "All", self.gui.search_handler.find_all, "Highlight all matches in current tab")
        self.gui.find_all_button.pack(side=ttk.LEFT, padx=2)

        self.gui.case_sensitive_var = ttk.IntVar(value=self.gui.settings.get('app', 'search_case_sensitive', 0))
        self.gui.case_sensitive_checkbox = ttk.Checkbutton(self.gui.search_frame, text="Case", variable=self.gui.case_sensitive_var)
        self.gui.case_sensitive_checkbox.pack(side=ttk.LEFT, padx=2)
        Tooltip(self.gui.case_sensitive_checkbox, "Case Sensitive Search")

        self.gui.whole_word_var = ttk.IntVar(value=self.gui.settings.get('app', 'search_whole_word', 0))
        self.gui.whole_word_checkbox = ttk.Checkbutton(self.gui.search_frame, text="Word", variable=self.gui.whole_word_var)
        self.gui.whole_word_checkbox.pack(side=ttk.LEFT, padx=2)
        Tooltip(self.gui.whole_word_checkbox, "Match Whole Word Only (Note: Uses basic regex matching)")

        self.gui.search_entry.bind("<Return>", lambda e: self.gui.search_handler.search_tab())
        self.gui.search_entry.bind("<KP_Enter>", lambda e: self.gui.search_handler.search_tab())

        # Notebook styling now handled by ttkbootstrap theme
        self.gui.notebook = ttk.Notebook(self)
        self.gui.notebook.pack(fill="both", expand=True, pady=(0,5))

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