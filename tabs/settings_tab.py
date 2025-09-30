import ttkbootstrap as ttk
import tkinter as tk
from tkinter import filedialog
import os
from file_handler import FileHandler

class SettingsTab(ttk.Frame):
    def __init__(self, parent, gui, settings, high_contrast_mode):
        super().__init__(parent)
        self.gui = gui
        self.settings = settings
        self.high_contrast_mode = high_contrast_mode
        # Colors now managed by ttkbootstrap theme
        self.exclude_file_vars = {}
        self.extension_checkboxes = {}
        self.default_tab_var = tk.StringVar(value=self.settings.get('app', 'default_tab', 'Content Preview'))
        self.expansion_var = tk.StringVar(value=self.settings.get('app', 'expansion', 'Collapsed'))
        self.levels_var = tk.StringVar(value=str(self.settings.get('app', 'levels', 1)))
        self.exclude_node_modules_var = tk.IntVar(value=self.settings.get('app', 'exclude_node_modules', 1))
        self.exclude_dist_var = tk.IntVar(value=self.settings.get('app', 'exclude_dist', 1))
        self.include_icons_var = tk.IntVar(value=self.settings.get('app', 'include_icons', 1))
        self.setup_ui()

    def setup_ui(self):
        scroll_frame = ttk.Scrollbar(self, orient="vertical")
        scroll_frame.pack(side=ttk.RIGHT, fill=ttk.Y)

        canvas = tk.Canvas(self, yscrollcommand=scroll_frame.set)
        canvas.pack(side=ttk.LEFT, fill=ttk.BOTH, expand=True)

        scroll_frame.config(command=canvas.yview)

        inner_frame = tk.Frame(canvas)
        inner_frame_id = canvas.create_window((0, 0), window=inner_frame, anchor="nw")

        def _on_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        inner_frame.bind("<Configure>", _on_configure)
        canvas.bind("<MouseWheel>", _on_mousewheel)
        inner_frame.bind("<MouseWheel>", _on_mousewheel)

        # Default Tab Selection
        default_tab_label = ttk.Label(inner_frame, text="Default Tab:", font=("Arial", 10, "bold"))
        default_tab_label.grid(row=0, column=0, padx=15, pady=8, sticky="w")
        default_tab_options = ["Content Preview", "Folder Structure", "Base Prompt", "Settings", "File List Selection"]
        default_tab_menu = ttk.Combobox(inner_frame, textvariable=self.default_tab_var, values=default_tab_options, state="readonly")
        default_tab_menu.grid(row=0, column=1, padx=15, pady=8, sticky="w")

        # Expansion Settings
        expansion_label = ttk.Label(inner_frame, text="Initial Expansion:", font=("Arial", 10, "bold"))
        expansion_label.grid(row=1, column=0, padx=15, pady=8, sticky="w")
        expansion_options = ["Collapsed", "Expanded", "Levels"]
        expansion_menu = ttk.Combobox(inner_frame, textvariable=self.expansion_var, values=expansion_options, state="readonly")
        expansion_menu.grid(row=1, column=1, padx=15, pady=8, sticky="w")

        # Expansion Levels
        levels_label = ttk.Label(inner_frame, text="Expansion Levels:", font=("Arial", 10, "bold"))
        levels_label.grid(row=2, column=0, padx=15, pady=8, sticky="w")
        self.levels_entry = ttk.Entry(inner_frame, textvariable=self.levels_var, width=5)
        self.levels_entry.grid(row=2, column=1, padx=15, pady=8, sticky="w")

        # Exclude node_modules
        exclude_node_modules_checkbox = ttk.Checkbutton(inner_frame, text="Exclude node_modules", variable=self.exclude_node_modules_var)
        exclude_node_modules_checkbox.grid(row=3, column=0, columnspan=2, padx=15, pady=8, sticky="w")

        # Exclude dist/build folders
        exclude_dist_checkbox = ttk.Checkbutton(inner_frame, text="Exclude dist/build folders", variable=self.exclude_dist_var)
        exclude_dist_checkbox.grid(row=4, column=0, columnspan=2, padx=15, pady=8, sticky="w")

        # Exclude Specific Files
        exclude_files_label = ttk.Label(inner_frame, text="Exclude Specific Files:", font=("Arial", 10, "bold"))
        exclude_files_label.grid(row=5, column=0, padx=15, pady=8, sticky="w")

        exclude_files = self.settings.get('app', 'exclude_files', {})
        row = 6
        for file, value in exclude_files.items():
            var = tk.IntVar(value=value)
            checkbox = ttk.Checkbutton(inner_frame, text=file, variable=var)
            checkbox.grid(row=row, column=0, columnspan=2, padx=15, pady=8, sticky="w")
            self.exclude_file_vars[file] = var
            row += 1

        # Include Icons
        include_icons_checkbox = ttk.Checkbutton(inner_frame, text="Include Icons in Structure", variable=self.include_icons_var)
        include_icons_checkbox.grid(row=row, column=0, columnspan=2, padx=15, pady=8, sticky="w")
        row += 1

        # Performance Settings Section
        performance_label = ttk.Label(inner_frame, text="Performance Settings", font=("Arial", 12, "bold"))
        performance_label.grid(row=row, column=0, columnspan=2, padx=15, pady=(20, 10), sticky="w")
        row += 1

        # Cache settings
        self.cache_max_size_var = tk.StringVar(value=str(self.settings.get('app', 'cache_max_size', 1000)))
        cache_size_label = ttk.Label(inner_frame, text="Cache Max Size:", font=("Arial", 10, "bold"))
        cache_size_label.grid(row=row, column=0, padx=15, pady=8, sticky="w")
        cache_size_entry = ttk.Entry(inner_frame, textvariable=self.cache_max_size_var, width=10)
        cache_size_entry.grid(row=row, column=1, padx=15, pady=8, sticky="w")
        row += 1

        self.cache_max_memory_var = tk.StringVar(value=str(self.settings.get('app', 'cache_max_memory_mb', 100)))
        cache_memory_label = ttk.Label(inner_frame, text="Cache Max Memory (MB):", font=("Arial", 10, "bold"))
        cache_memory_label.grid(row=row, column=0, padx=15, pady=8, sticky="w")
        cache_memory_entry = ttk.Entry(inner_frame, textvariable=self.cache_max_memory_var, width=10)
        cache_memory_entry.grid(row=row, column=1, padx=15, pady=8, sticky="w")
        row += 1

        # Tree operation settings
        self.tree_max_items_var = tk.StringVar(value=str(self.settings.get('app', 'tree_max_items', 10000)))
        tree_items_label = ttk.Label(inner_frame, text="Tree Max Items:", font=("Arial", 10, "bold"))
        tree_items_label.grid(row=row, column=0, padx=15, pady=8, sticky="w")
        tree_items_entry = ttk.Entry(inner_frame, textvariable=self.tree_max_items_var, width=10)
        tree_items_entry.grid(row=row, column=1, padx=15, pady=8, sticky="w")
        row += 1

        # Security Settings Section
        security_label = ttk.Label(inner_frame, text="Security Settings", font=("Arial", 12, "bold"))
        security_label.grid(row=row, column=0, columnspan=2, padx=15, pady=(20, 10), sticky="w")
        row += 1

        self.security_enabled_var = tk.IntVar(value=self.settings.get('app', 'security_enabled', 1))
        security_enabled_checkbox = ttk.Checkbutton(inner_frame, text="Enable Security Validation", variable=self.security_enabled_var)
        security_enabled_checkbox.grid(row=row, column=0, columnspan=2, padx=15, pady=8, sticky="w")
        row += 1

        self.max_file_size_var = tk.StringVar(value=str(self.settings.get('app', 'max_file_size_mb', 10)))
        max_file_size_label = ttk.Label(inner_frame, text="Max File Size (MB):", font=("Arial", 10, "bold"))
        max_file_size_label.grid(row=row, column=0, padx=15, pady=8, sticky="w")
        max_file_size_entry = ttk.Entry(inner_frame, textvariable=self.max_file_size_var, width=10)
        max_file_size_entry.grid(row=row, column=1, padx=15, pady=8, sticky="w")
        row += 1

        # Logging Settings Section
        logging_label = ttk.Label(inner_frame, text="Logging Settings", font=("Arial", 12, "bold"))
        logging_label.grid(row=row, column=0, columnspan=2, padx=15, pady=(20, 10), sticky="w")
        row += 1

        # Log level
        self.log_level_var = tk.StringVar(value=self.settings.get('app', 'log_level', 'INFO'))
        log_level_label = ttk.Label(inner_frame, text="Log Level:", font=("Arial", 10, "bold"))
        log_level_label.grid(row=row, column=0, padx=15, pady=8, sticky="w")
        log_level_options = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        log_level_menu = ttk.Combobox(inner_frame, textvariable=self.log_level_var, values=log_level_options, state="readonly", width=15)
        log_level_menu.grid(row=row, column=1, padx=15, pady=8, sticky="w")
        row += 1

        # Log to file
        self.log_to_file_var = tk.IntVar(value=self.settings.get('app', 'log_to_file', 1))
        log_to_file_checkbox = ttk.Checkbutton(inner_frame, text="Log to File", variable=self.log_to_file_var)
        log_to_file_checkbox.grid(row=row, column=0, columnspan=2, padx=15, pady=8, sticky="w")
        row += 1

        # Log to console
        self.log_to_console_var = tk.IntVar(value=self.settings.get('app', 'log_to_console', 1))
        log_to_console_checkbox = ttk.Checkbutton(inner_frame, text="Log to Console", variable=self.log_to_console_var)
        log_to_console_checkbox.grid(row=row, column=0, columnspan=2, padx=15, pady=8, sticky="w")
        row += 1

        # Folder Selection Settings Section
        folder_selection_label = ttk.Label(inner_frame, text="Folder Selection Settings", font=("Arial", 12, "bold"))
        folder_selection_label.grid(row=row, column=0, columnspan=2, padx=15, pady=(20, 10), sticky="w")
        row += 1

        # Default start folder
        self.default_start_folder_var = tk.StringVar(value=self.settings.get('app', 'default_start_folder', os.path.expanduser("~")))
        default_folder_label = ttk.Label(inner_frame, text="Default Start Folder:", font=("Arial", 10, "bold"))
        default_folder_label.grid(row=row, column=0, padx=15, pady=8, sticky="w")
        
        default_folder_frame = ttk.Frame(inner_frame)
        default_folder_frame.grid(row=row, column=1, padx=15, pady=8, sticky="ew")
        
        self.default_folder_entry = ttk.Entry(default_folder_frame, textvariable=self.default_start_folder_var, width=40)
        self.default_folder_entry.pack(side=ttk.LEFT, fill="x", expand=True)
        
        browse_folder_button = ttk.Button(default_folder_frame, text="Browse...", command=self._browse_default_folder, width=10)
        browse_folder_button.pack(side=ttk.RIGHT, padx=(5, 0))
        row += 1

        # Text File Extensions
        extensions_label = ttk.Label(inner_frame, text="Text File Extensions:", font=("Arial", 10, "bold"))
        extensions_label.grid(row=row, column=0, padx=15, pady=8, sticky="w")
        row += 1

        extension_groups = FileHandler.get_extension_groups()
        for group, extensions in extension_groups.items():
            group_label = ttk.Label(inner_frame, text=group, font=("Arial", 10, "bold"))
            group_label.grid(row=row, column=0, columnspan=2, padx=25, pady=8, sticky="w")
            row += 1

            ext_row = row
            col = 0
            for ext in sorted(extensions):
                var = tk.IntVar(value=self.settings.get('app', 'text_extensions', {}).get(ext, 1))
                cb = ttk.Checkbutton(inner_frame, text=ext, variable=var)
                cb.grid(row=ext_row, column=col, padx=25, pady=5, sticky="w")
                self.extension_checkboxes[ext] = (cb, var)
                col += 1
                if col > 5:
                    col = 0
                    ext_row += 1
            row = ext_row + 1

        # Save button
        save_button = self.gui.create_button(inner_frame, "Save Settings", self.gui.save_app_settings, "Save changes to settings")
        save_button.grid(row=row, column=0, columnspan=2, pady=20)

        # High contrast mode (now theme switching)
        high_contrast_checkbox = ttk.Checkbutton(inner_frame, text="High Contrast Mode", variable=self.high_contrast_mode, command=self._toggle_theme)
        high_contrast_checkbox.grid(row=row + 1, column=0, columnspan=2, padx=10, pady=5, sticky="w")

    def _toggle_theme(self):
        """Toggle between dark and light themes and update styles."""
        current_theme = self.gui.root.style.theme_name()
        if current_theme == 'darkly':
            self.gui.root.style.theme_use('litera')  # Light theme
        else:
            self.gui.root.style.theme_use('darkly')  # Dark theme
        
        # Update tag colors in structure and content tabs
        self.gui.structure_tab.update_tag_colors()
        self.gui.content_tab.update_tag_colors()

    def _browse_default_folder(self):
        """Open folder selection dialog for default start folder."""
        current_folder = self.default_start_folder_var.get()
        if not os.path.exists(current_folder):
            current_folder = os.path.expanduser("~")
        
        folder = filedialog.askdirectory(
            title="Select Default Start Folder",
            initialdir=current_folder
        )
        
        if folder:
            self.default_start_folder_var.set(folder)


    def perform_search(self, query, case_sensitive, whole_word):
        return []  # No searchable content in settings tab

    def highlight_all_matches(self, matches):
        pass

    def highlight_match(self, match_data, is_focused=True):
        pass

    def center_match(self, match_data):
        pass

    def clear_highlights(self):
        pass

    def clear(self):
        pass  # Settings tab doesn't need clearing