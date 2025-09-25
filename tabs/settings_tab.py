import tkinter as tk
from tkinter import ttk
from file_handler import FileHandler

class SettingsTab(tk.Frame):
    def __init__(self, parent, gui, settings, high_contrast_mode):
        super().__init__(parent)
        self.gui = gui
        self.settings = settings
        self.high_contrast_mode = high_contrast_mode
        self.colors = gui.colors
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
        scroll_frame.pack(side=tk.RIGHT, fill=tk.Y)

        canvas = tk.Canvas(self, bg=self.colors['bg'], yscrollcommand=scroll_frame.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_frame.config(command=canvas.yview)

        inner_frame = tk.Frame(canvas, bg=self.colors['bg'])
        inner_frame_id = canvas.create_window((0, 0), window=inner_frame, anchor="nw")

        def _on_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        inner_frame.bind("<Configure>", _on_configure)

        default_tab_label = tk.Label(inner_frame, text="Default Tab:", bg=self.colors['bg'], fg=self.colors['fg'])
        default_tab_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        default_tab_options = ["Content Preview", "Folder Structure", "Base Prompt", "Settings", "File List Selection"]
        default_tab_menu = ttk.Combobox(inner_frame, textvariable=self.default_tab_var, values=default_tab_options, state="readonly")
        default_tab_menu.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        expansion_label = tk.Label(inner_frame, text="Initial Expansion:", bg=self.colors['bg'], fg=self.colors['fg'])
        expansion_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        expansion_options = ["Collapsed", "Expanded", "Levels"]
        expansion_menu = ttk.Combobox(inner_frame, textvariable=self.expansion_var, values=expansion_options, state="readonly")
        expansion_menu.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        levels_label = tk.Label(inner_frame, text="Expansion Levels:", bg=self.colors['bg'], fg=self.colors['fg'])
        levels_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.levels_entry = tk.Entry(inner_frame, textvariable=self.levels_var, width=5, bg=self.colors['bg_accent'], fg=self.colors['fg'])
        self.levels_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        exclude_node_modules_checkbox = tk.Checkbutton(inner_frame, text="Exclude node_modules", variable=self.exclude_node_modules_var,
                                                       bg=self.colors['bg'], fg=self.colors['fg'], selectcolor=self.colors['bg_accent'])
        exclude_node_modules_checkbox.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        exclude_dist_checkbox = tk.Checkbutton(inner_frame, text="Exclude dist/build folders", variable=self.exclude_dist_var,
                                               bg=self.colors['bg'], fg=self.colors['fg'], selectcolor=self.colors['bg_accent'])
        exclude_dist_checkbox.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        exclude_files_label = tk.Label(inner_frame, text="Exclude Specific Files:", bg=self.colors['bg'], fg=self.colors['fg'])
        exclude_files_label.grid(row=5, column=0, padx=10, pady=5, sticky="w")

        exclude_files = self.settings.get('app', 'exclude_files', {})
        row = 6
        for file, value in exclude_files.items():
            var = tk.IntVar(value=value)
            checkbox = tk.Checkbutton(inner_frame, text=file, variable=var,
                                      bg=self.colors['bg'], fg=self.colors['fg'], selectcolor=self.colors['bg_accent'])
            checkbox.grid(row=row, column=0, columnspan=2, padx=20, pady=2, sticky="w")
            self.exclude_file_vars[file] = var
            row += 1

        include_icons_checkbox = tk.Checkbutton(inner_frame, text="Include Icons in Structure", variable=self.include_icons_var,
                                                bg=self.colors['bg'], fg=self.colors['fg'], selectcolor=self.colors['bg_accent'])
        include_icons_checkbox.grid(row=row, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        row += 1

        # Performance Settings Section
        performance_label = tk.Label(inner_frame, text="Performance Settings", bg=self.colors['bg'], fg=self.colors['header'], font=("Arial", 12, "bold"))
        performance_label.grid(row=row, column=0, columnspan=2, padx=10, pady=(20, 5), sticky="w")
        row += 1

        # Cache settings
        self.cache_max_size_var = tk.StringVar(value=str(self.settings.get('app', 'cache_max_size', 1000)))
        cache_size_label = tk.Label(inner_frame, text="Cache Max Size:", bg=self.colors['bg'], fg=self.colors['fg'])
        cache_size_label.grid(row=row, column=0, padx=10, pady=5, sticky="w")
        cache_size_entry = tk.Entry(inner_frame, textvariable=self.cache_max_size_var, width=10, bg=self.colors['bg_accent'], fg=self.colors['fg'])
        cache_size_entry.grid(row=row, column=1, padx=10, pady=5, sticky="w")
        row += 1

        self.cache_max_memory_var = tk.StringVar(value=str(self.settings.get('app', 'cache_max_memory_mb', 100)))
        cache_memory_label = tk.Label(inner_frame, text="Cache Max Memory (MB):", bg=self.colors['bg'], fg=self.colors['fg'])
        cache_memory_label.grid(row=row, column=0, padx=10, pady=5, sticky="w")
        cache_memory_entry = tk.Entry(inner_frame, textvariable=self.cache_max_memory_var, width=10, bg=self.colors['bg_accent'], fg=self.colors['fg'])
        cache_memory_entry.grid(row=row, column=1, padx=10, pady=5, sticky="w")
        row += 1

        # Tree operation settings
        self.tree_max_items_var = tk.StringVar(value=str(self.settings.get('app', 'tree_max_items', 10000)))
        tree_items_label = tk.Label(inner_frame, text="Tree Max Items:", bg=self.colors['bg'], fg=self.colors['fg'])
        tree_items_label.grid(row=row, column=0, padx=10, pady=5, sticky="w")
        tree_items_entry = tk.Entry(inner_frame, textvariable=self.tree_max_items_var, width=10, bg=self.colors['bg_accent'], fg=self.colors['fg'])
        tree_items_entry.grid(row=row, column=1, padx=10, pady=5, sticky="w")
        row += 1

        # Security Settings Section
        security_label = tk.Label(inner_frame, text="Security Settings", bg=self.colors['bg'], fg=self.colors['header'], font=("Arial", 12, "bold"))
        security_label.grid(row=row, column=0, columnspan=2, padx=10, pady=(20, 5), sticky="w")
        row += 1

        self.security_enabled_var = tk.IntVar(value=self.settings.get('app', 'security_enabled', 1))
        security_enabled_checkbox = tk.Checkbutton(inner_frame, text="Enable Security Validation", variable=self.security_enabled_var,
                                                   bg=self.colors['bg'], fg=self.colors['fg'], selectcolor=self.colors['bg_accent'])
        security_enabled_checkbox.grid(row=row, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        row += 1

        self.max_file_size_var = tk.StringVar(value=str(self.settings.get('app', 'max_file_size_mb', 10)))
        max_file_size_label = tk.Label(inner_frame, text="Max File Size (MB):", bg=self.colors['bg'], fg=self.colors['fg'])
        max_file_size_label.grid(row=row, column=0, padx=10, pady=5, sticky="w")
        max_file_size_entry = tk.Entry(inner_frame, textvariable=self.max_file_size_var, width=10, bg=self.colors['bg_accent'], fg=self.colors['fg'])
        max_file_size_entry.grid(row=row, column=1, padx=10, pady=5, sticky="w")
        row += 1

        # Logging Settings Section
        logging_label = tk.Label(inner_frame, text="Logging Settings", bg=self.colors['bg'], fg=self.colors['header'], font=("Arial", 12, "bold"))
        logging_label.grid(row=row, column=0, columnspan=2, padx=10, pady=(20, 5), sticky="w")
        row += 1

        # Log level
        self.log_level_var = tk.StringVar(value=self.settings.get('app', 'log_level', 'INFO'))
        log_level_label = tk.Label(inner_frame, text="Log Level:", bg=self.colors['bg'], fg=self.colors['fg'])
        log_level_label.grid(row=row, column=0, padx=10, pady=5, sticky="w")
        log_level_options = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        log_level_menu = ttk.Combobox(inner_frame, textvariable=self.log_level_var, values=log_level_options, state="readonly", width=15)
        log_level_menu.grid(row=row, column=1, padx=10, pady=5, sticky="w")
        row += 1

        # Log to file
        self.log_to_file_var = tk.IntVar(value=self.settings.get('app', 'log_to_file', 1))
        log_to_file_checkbox = tk.Checkbutton(inner_frame, text="Log to File", variable=self.log_to_file_var,
                                             bg=self.colors['bg'], fg=self.colors['fg'], selectcolor=self.colors['bg_accent'])
        log_to_file_checkbox.grid(row=row, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        row += 1

        # Log to console
        self.log_to_console_var = tk.IntVar(value=self.settings.get('app', 'log_to_console', 1))
        log_to_console_checkbox = tk.Checkbutton(inner_frame, text="Log to Console", variable=self.log_to_console_var,
                                                  bg=self.colors['bg'], fg=self.colors['fg'], selectcolor=self.colors['bg_accent'])
        log_to_console_checkbox.grid(row=row, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        row += 1

        extensions_label = tk.Label(inner_frame, text="Text File Extensions:", bg=self.colors['bg'], fg=self.colors['fg'])
        extensions_label.grid(row=row, column=0, padx=10, pady=10, sticky="w")
        row += 1

        extension_groups = FileHandler.get_extension_groups()
        for group, extensions in extension_groups.items():
            group_label = tk.Label(inner_frame, text=group, bg=self.colors['bg'], fg=self.colors['header'], font=("Arial", 10, "bold"))
            group_label.grid(row=row, column=0, columnspan=2, padx=10, pady=5, sticky="w")
            row += 1

            ext_row = row
            col = 0
            for ext in sorted(extensions):
                var = tk.IntVar(value=self.settings.get('app', 'text_extensions', {}).get(ext, 1))
                cb = tk.Checkbutton(inner_frame, text=ext, variable=var,
                                    bg=self.colors['bg'], fg=self.colors['fg'], selectcolor=self.colors['bg_accent'])
                cb.grid(row=ext_row, column=col, padx=20, pady=2, sticky="w")
                self.extension_checkboxes[ext] = (cb, var)
                col += 1
                if col > 5:
                    col = 0
                    ext_row += 1
            row = ext_row + 1

        save_button = self.gui.create_button(inner_frame, "Save Settings", self.gui.save_app_settings, "Save changes to settings")
        save_button.grid(row=row, column=0, columnspan=2, pady=20)

        high_contrast_checkbox = tk.Checkbutton(inner_frame, text="High Contrast Mode", variable=self.high_contrast_mode,
                                                command=self.gui.theme_manager.toggle_high_contrast,
                                                bg=self.colors['bg'], fg=self.colors['fg'], selectcolor=self.colors['bg_accent'])
        high_contrast_checkbox.grid(row=row + 1, column=0, columnspan=2, padx=10, pady=5, sticky="w")

    def reconfigure_colors(self, colors):
        self.colors = colors
        # Reconfigure all labels, checkboxes, etc., here if needed
        # For simplicity, since this tab is rebuilt on refresh, we can skip detailed reconfiguration

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