import os
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from widgets import Tooltip, FolderDialog, SettingsDialog
from file_handler import FileHandler
from settings import SettingsManager
import appdirs

class RepoPromptGUI:
    def __init__(self, root):
        self.root = root
        self.version = "2.0"
        self.root.title(f"CodeBase v{self.version}")
        self.root.geometry("1200x800")
        self.root.configure(bg='#2b2b2b')
        self.settings = SettingsManager()
        
        # Colors
        self.text_color = '#ffffff'
        self.button_bg = '#4a4a4a'
        self.button_fg = '#ffffff'
        self.header_color = '#add8e6'
        self.status_color = '#FF4500'
        self.folder_color = '#FFD700'

        # Variables
        self.prepend_var = tk.IntVar()
        self.include_icons_var = tk.IntVar(value=1)
        self.show_unloaded_var = tk.IntVar(value=0)
        self.expand_collapse_var = tk.BooleanVar(value=True)
        self.user_data_dir = appdirs.user_data_dir("CodeBase")
        self.template_dir = os.path.join(self.user_data_dir, "templates")
        self.recent_folders_file = os.path.join(self.user_data_dir, "recent_folders.txt")
        os.makedirs(self.template_dir, exist_ok=True)
        self.match_positions = {}
        self.current_match_index = {}
        self.file_states = {}
        self.recent_folders = self.load_recent_folders()

        # Progress bar
        self.progress = ttk.Progressbar(self.root, mode='indeterminate')

        self.file_handler = FileHandler(self)
        
        self.setup_ui()
        self.bind_keys()
        self.apply_default_tab()

    def load_recent_folders(self):
        if os.path.exists(self.recent_folders_file):
            with open(self.recent_folders_file, 'r') as file:
                return [line.strip() for line in file.readlines() if line.strip()]
        return []

    def save_recent_folders(self):
        with open(self.recent_folders_file, 'w') as file:
            for folder in self.recent_folders:
                file.write(f"{folder}\n")

    def update_recent_folders(self, new_folder):
        if new_folder in self.recent_folders:
            self.recent_folders.remove(new_folder)
        self.recent_folders.insert(0, new_folder)
        if len(self.recent_folders) > 20:
            self.recent_folders = self.recent_folders[:20]
        self.save_recent_folders()

    def setup_header(self):
        tk.Label(self.root, text="CodeBase", font=("Arial", 16), bg='#2b2b2b', fg=self.text_color).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        tk.Label(self.root, text=f"v{self.version}", font=("Arial", 10), bg='#2b2b2b', fg=self.header_color).grid(row=0, column=1, padx=5, pady=10, sticky="w")
        self.repo_label = tk.Label(self.root, text="Current Repo Loaded: None", font=("Arial", 14), bg='#2b2b2b', fg=self.status_color)
        self.repo_label.grid(row=0, column=2, padx=50, pady=10, sticky="w")
        tk.Frame(self.root, bg='#4a4a4a', height=1).grid(row=1, column=0, columnspan=3, sticky="ew")

    def setup_left_frame(self):
        self.left_frame = tk.Frame(self.root, bg='#2b2b2b')
        self.left_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ns")
        tk.Frame(self.root, bg='#4a4a4a', width=1).grid(row=2, column=1, sticky="ns", padx=5)
        self.select_button = self.add_button(self.left_frame, "Select Repo (Ctrl+R)", self.select_repo, "Choose a repository folder")
        self.refresh_button = self.add_button(self.left_frame, "Refresh (Ctrl+F5)", self.refresh_repo, "Refresh current repository", state=tk.DISABLED)
        self.settings_button = self.add_button(self.left_frame, "Repo Settings", self.open_repo_settings, "Customize file reading settings")
        self.info_label = tk.Label(self.left_frame, text="Token Count: 0", bg='#2b2b2b', fg=self.text_color)
        self.info_label.pack(pady=5)
        self.copy_button = self.add_button(self.left_frame, "Copy Contents (Ctrl+C)", self.file_handler.copy_contents, "Copy selected contents", state=tk.DISABLED)
        self.copy_all_button = self.add_button(self.left_frame, "Copy All (Ctrl+A)", self.file_handler.copy_all, "Copy prompt, contents, structure", state=tk.DISABLED)
        self.prepend_checkbox = tk.Checkbutton(self.left_frame, text="Prepend Base Prompt", variable=self.prepend_var, bg='#2b2b2b', fg=self.text_color, selectcolor='#4a4a4a')
        self.prepend_checkbox.pack(pady=5)
        Tooltip(self.prepend_checkbox, "Include Base Prompt in copied content")
        self.copy_structure_button = self.add_button(self.left_frame, "Copy Structure (Ctrl+S)", self.file_handler.copy_structure, "Copy folder structure", state=tk.DISABLED)
        self.include_icons_checkbox = tk.Checkbutton(self.left_frame, text="Include Icons in Structure", variable=self.include_icons_var, bg='#2b2b2b', fg=self.text_color, selectcolor='#4a4a4a')
        self.include_icons_checkbox.pack(pady=5)
        Tooltip(self.include_icons_checkbox, "Toggle icons in structure")
        
        clear_button_frame = tk.Frame(self.left_frame, bg='#2b2b2b')
        clear_button_frame.pack(side='bottom', fill='x')
        self.clear_button = self.add_button(clear_button_frame, "Clear", self.clear_current, "Clear data in current tab")
        self.clear_all_button = self.add_button(clear_button_frame, "Clear All", self.clear_all, "Clear data in all tabs")

    def setup_right_frame(self):
        self.right_frame = tk.Frame(self.root, bg='#2b2b2b')
        self.right_frame.grid(row=2, column=2, padx=10, pady=10, sticky="nsew")
        self.root.grid_columnconfigure(2, weight=1)
        self.root.grid_rowconfigure(2, weight=1)

        self.notebook = ttk.Notebook(self.right_frame)
        self.notebook.pack(fill="both", expand=True)
        style = ttk.Style()
        style.configure("Custom.TNotebook", background='#2b2b2b')
        style.configure("Custom.TNotebook.Tab", background='#3c3c3c', foreground=self.text_color)
        style.map("Custom.TNotebook.Tab", background=[('selected', self.header_color)], foreground=[('selected', '#2b2b2b')])
        self.notebook.configure(style="Custom.TNotebook")
        self.notebook.bind('<Tab>', self.cycle_tabs)

        search_frame = tk.Frame(self.right_frame, bg='#2b2b2b')
        search_frame.pack(side=tk.TOP, anchor="ne", pady=5, padx=10)
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var, bg='#3c3c3c', fg=self.text_color, insertbackground=self.text_color, width=60, font=("Arial", 12))
        self.search_entry.pack(side=tk.LEFT, padx=5, pady=2, ipady=5)
        Tooltip(self.search_entry, "Enter text to search in current tab")
        self.search_button = self.add_button(search_frame, "Search", self.file_handler.search_tab, "Search current tab")
        self.next_button = self.add_button(search_frame, "Next", self.file_handler.next_match, "Next match")
        self.prev_button = self.add_button(search_frame, "Prev", self.file_handler.prev_match, "Previous match")
        self.search_entry.bind("<Return>", lambda e: self.file_handler.search_tab())
        self.search_entry.bind("<KP_Enter>", lambda e: self.file_handler.search_tab())
        self.search_entry.bind("<Down>", lambda e: self.file_handler.next_match())
        self.search_entry.bind("<Up>", lambda e: self.file_handler.prev_match())

        self.content_text = scrolledtext.ScrolledText(self.notebook, wrap=tk.WORD, bg='#3c3c3c', fg=self.text_color, font=("Arial", 10), state=tk.NORMAL)
        self.content_text.pack(fill="both", expand=True)
        self.content_text.tag_configure("filename", foreground="red")
        self.content_text.tag_configure("toggle", foreground="#00FF00", underline=True)
        self.content_text.bind("<Motion>", self.on_mouse_move)
        self.content_text.bind("<Leave>", lambda event: self.content_text.config(cursor=""))
        self.notebook.add(self.content_text, text="Content Preview")

        self.structure_frame = tk.Frame(self.notebook, bg='#2b2b2b')
        self.notebook.add(self.structure_frame, text="Folder Structure")
        structure_button_frame = tk.Frame(self.structure_frame, bg='#2b2b2b')
        structure_button_frame.pack(side=tk.TOP, fill='x', pady=5)
        self.expand_collapse_button = self.add_button(structure_button_frame, "Expand All", self.file_handler.toggle_expand_collapse, "Expand/collapse folders")
        self.show_unloaded_checkbox = tk.Checkbutton(structure_button_frame, text="Show Unloaded Files", variable=self.show_unloaded_var, command=self.file_handler.update_tree_strikethrough, bg='#2b2b2b', fg=self.text_color, selectcolor='#4a4a4a')
        self.show_unloaded_checkbox.pack(side=tk.LEFT, padx=5)
        Tooltip(self.show_unloaded_checkbox, "Toggle strikethrough on unloaded files")
        self.tree = ttk.Treeview(self.structure_frame, columns=("path", "checkbox"), show=["tree", "headings"], style="Custom.Treeview")
        self.tree.column("#0", width=300)
        self.tree.column("path", width=0, stretch=tk.NO)
        self.tree.column("checkbox", width=30, anchor="center")
        self.tree.heading("#0", text="Name")
        self.tree.heading("checkbox", text="Select/Deselect")
        self.tree.pack(fill="both", expand=True)
        style.configure("Custom.Treeview", background="#3c3c3c", foreground=self.text_color, fieldbackground="#3c3c3c")
        style.map("Custom.Treeview", background=[('selected', '#4a4a4a')], foreground=[('selected', self.text_color)])
        scrollbar = ttk.Scrollbar(self.structure_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.tag_bind('folder', '<Double-1>', self.file_handler.on_double_click)
        self.tree.tag_bind('file', '<Double-1>', self.jump_to_file_content)
        self.tree.bind('<<TreeviewOpen>>', self.file_handler.on_treeview_open)
        self.tree.bind('<Button-1>', self.file_handler.toggle_selection)
        self.tree.tag_configure('unloaded', font=(None, -10, 'overstrike'))
        self.tree.tag_configure('selected', foreground='#00FF00')

        self.base_prompt_text = scrolledtext.ScrolledText(self.notebook, wrap=tk.WORD, bg='#3c3c3c', fg=self.text_color, font=("Arial", 10))
        self.notebook.add(self.base_prompt_text, text="Base Prompt")
        button_frame = tk.Frame(self.base_prompt_text.master, bg='#2b2b2b')
        button_frame.pack(pady=10)
        self.save_template_button = self.add_button(button_frame, "Save Template (Ctrl+T)", self.save_template, "Save current prompt as template")
        self.load_template_button = self.add_button(button_frame, "Load Template (Ctrl+L)", self.load_template, "Load a saved template")
        self.delete_template_button = self.add_button(button_frame, "Delete Template", self.delete_template, "Delete a saved template")

        self.settings_frame = tk.Frame(self.notebook, bg='#2b2b2b')
        self.notebook.add(self.settings_frame, text="Settings")
        self.setup_settings_tab()

    def setup_status_bar(self):
        self.status_bar = tk.Label(self.root, text="Ready", bg='#2b2b2b', fg=self.status_color, bd=1, relief="sunken", anchor="w")
        self.status_bar.grid(row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=5)

    def setup_settings_tab(self):
        tk.Label(self.settings_frame, text="Application Settings", font=("Arial", 14), bg='#2b2b2b', fg=self.text_color).pack(pady=10)
        default_label = tk.Label(self.settings_frame, text="Default Tab:", bg='#2b2b2b', fg=self.text_color)
        default_label.pack()
        Tooltip(default_label, "Set the default tab on startup")
        self.default_tab_var = tk.StringVar(value=self.settings.get('app', 'default_tab', 'Content Preview'))
        for tab in ["Content Preview", "Folder Structure", "Base Prompt", "Settings"]:
            tk.Radiobutton(self.settings_frame, text=tab, variable=self.default_tab_var, value=tab, bg='#2b2b2b', fg=self.text_color, selectcolor='#4a4a4a').pack(anchor='w')
        expansion_label = tk.Label(self.settings_frame, text="Folder Expansion:", bg='#2b2b2b', fg=self.text_color)
        expansion_label.pack(pady=5)
        Tooltip(expansion_label, "Control folder expansion on load")
        self.expansion_var = tk.StringVar(value=self.settings.get('app', 'expansion', 'Collapsed'))
        tk.Radiobutton(self.settings_frame, text="Fully Expanded", variable=self.expansion_var, value="Expanded", bg='#2b2b2b', fg=self.text_color, selectcolor='#4a4a4a').pack(anchor='w')
        tk.Radiobutton(self.settings_frame, text="Collapsed", variable=self.expansion_var, value="Collapsed", bg='#2b2b2b', fg=self.text_color, selectcolor='#4a4a4a').pack(anchor='w')
        tk.Radiobutton(self.settings_frame, text="Load X levels", variable=self.expansion_var, value="Levels", bg='#2b2b2b', fg=self.text_color, selectcolor='#4a4a4a').pack(anchor='w')
        self.levels_entry = tk.Entry(self.settings_frame, bg='#3c3c3c', fg=self.text_color)
        self.levels_entry.insert(0, self.settings.get('app', 'levels', '1'))
        self.levels_entry.pack(pady=5)
        Tooltip(self.levels_entry, "Number of folder levels to expand")
        self.add_button(self.settings_frame, "Save Settings", self.save_app_settings, "Save application settings")

    def setup_ui(self):
        self.menu = tk.Menu(self.root, bg=self.button_bg, fg=self.button_fg)
        self.root.config(menu=self.menu)
        help_menu = tk.Menu(self.menu, bg=self.button_bg, fg=self.button_fg)
        self.menu.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        self.setup_header()
        self.setup_left_frame()
        self.setup_right_frame()
        self.setup_status_bar()

    def add_button(self, parent, text, command, tooltip, state=tk.NORMAL):
        btn = tk.Button(parent, text=text, command=command, bg=self.button_bg, fg=self.button_fg, state=state)
        btn.pack(pady=5)
        btn.bind("<Enter>", lambda e: btn.config(bg="#5a5a5a"))
        btn.bind("<Leave>", lambda e: btn.config(bg=self.button_bg))
        Tooltip(btn, tooltip)
        return btn

    def bind_keys(self):
        self.root.bind('<Control-c>', lambda e: self.file_handler.copy_contents())
        self.root.bind('<Control-s>', lambda e: self.file_handler.copy_structure())
        self.root.bind('<Control-a>', lambda e: self.file_handler.copy_all())
        self.root.bind('<Control-r>', lambda e: self.select_repo())
        self.root.bind('<Control-F5>', lambda e: self.refresh_repo())
        self.root.bind('<Control-t>', lambda e: self.save_template())
        self.root.bind('<Control-l>', lambda e: self.load_template())

    def cycle_tabs(self, event):
        current_index = self.notebook.index('current')
        next_index = (current_index + 1) % self.notebook.index('end')
        self.notebook.select(next_index)
        return 'break'

    def on_mouse_move(self, event):
        index = self.content_text.index(f"@{event.x},{event.y}")
        tags = self.content_text.tag_names(index)
        if "toggle" in tags:
            self.content_text.config(cursor="hand2")
        else:
            self.content_text.config(cursor="")

    def select_repo(self):
        self.progress.grid(row=3, column=0, columnspan=3, sticky="ew")
        self.progress.start()
        folder = FolderDialog(self.root, self.file_handler.recent_folders).show()
        if folder:
            self.file_handler.load_repo(folder)
            self.repo_label.config(text=f"Current Repo Loaded: {os.path.basename(folder)}")
            self.refresh_ui()
        self.progress.stop()
        self.progress.grid_forget()

    def refresh_ui(self):
        self.info_label.config(text=f"Token Count: {self.file_handler.token_count:,}".replace(",", " "))
        self.refresh_button.config(state=tk.NORMAL)
        self.copy_button.config(state=tk.NORMAL)
        self.copy_all_button.config(state=tk.NORMAL)
        self.copy_structure_button.config(state=tk.NORMAL)
        self.update_content_preview()

    def populate_tree(self, root_dir):
        self.tree.delete(*self.tree.get_children())
        root_basename = os.path.basename(root_dir)
        root_icon = "📁" if os.path.isdir(root_dir) else "📄"
        root_id = self.tree.insert("", "end", text=f"{root_icon} {root_basename}", open=True, tags=('folder',), values=(root_dir,))
        self.build_tree(root_dir, root_id)
        self.tree.tag_configure('folder', foreground=self.folder_color)
        self.tree.tag_configure('file', foreground=self.text_color)
        self.file_handler.update_tree_strikethrough()

    def build_tree(self, path, parent_id):
        if self.file_handler.is_ignored(path):
            return
        try:
            items = [item for item in sorted(os.listdir(path)) if not self.file_handler.is_ignored(os.path.join(path, item))]
            for item in items:
                item_path = os.path.join(path, item)
                icon = "📁" if os.path.isdir(item_path) else "📄"
                tag = 'folder' if os.path.isdir(item_path) else 'file'
                tags = [tag]
                item_id = self.tree.insert(parent_id, "end", text=f"{icon} {item}", values=(item_path,), open=False, tags=tags)
                if os.path.isdir(item_path):
                    self.tree.insert(item_id, "end", text="Loading...", tags=('dummy',))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to list directory {path}: {str(e)}")

    def update_content_preview(self):
        self.content_text.config(state=tk.NORMAL)
        self.content_text.delete(1.0, tk.END)
        self.file_states.clear()

        if self.file_handler.file_contents:
            sections = self.file_handler.file_contents.split("===FILE_SEPARATOR===\n")
            for section in sections:
                if section.strip() and section.startswith("File: "):
                    filename_end = section.find("\nContent:\n")
                    if filename_end != -1:
                        file_path = section[6:filename_end].strip()
                        content = section[filename_end + 11:]
                        file_id = file_path
                        self.file_states[file_id] = True
                        toggle_tag = f"toggle_{file_id}"
                        content_tag = f"content_{file_id}"

                        self.content_text.insert(tk.END, "[-]", ("toggle", toggle_tag))
                        self.content_text.insert(tk.END, f" File: {file_path}\n", "filename")
                        self.content_text.insert(tk.END, f"Content:\n{content}\n\n", content_tag)
                        self.content_text.tag_bind(toggle_tag, "<Button-1>", lambda event, fid=file_id: self.toggle_content(fid))
        self.content_text.config(state=tk.DISABLED)

    def toggle_content(self, file_id):
        self.content_text.config(state=tk.NORMAL)
        current_state = self.file_states.get(file_id, True)
        new_state = not current_state
        self.file_states[file_id] = new_state

        toggle_tag = f"toggle_{file_id}"
        content_tag = f"content_{file_id}"

        ranges = self.content_text.tag_ranges(toggle_tag)
        if ranges and len(ranges) == 2:
            start, end = ranges[0], ranges[1]
            self.content_text.delete(start, end)
            new_text = "[-]" if new_state else "[+]"
            self.content_text.insert(start, new_text, ("toggle", toggle_tag))

        self.content_text.tag_configure(content_tag, elide=not new_state)
        self.content_text.config(state=tk.DISABLED)

    def search_tab(self):
        query = self.search_var.get()
        if not query:
            return
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 3:
            return
        matches = []
        if current_tab in [0, 2]:
            text_widget = self.content_text if current_tab == 0 else self.base_prompt_text
            text_widget.tag_remove("highlight", "1.0", tk.END)
            text_widget.tag_remove("focused_highlight", "1.0", tk.END)
            start_pos = "1.0"
            while True:
                pos = text_widget.search(query, start_pos, stopindex=tk.END, nocase=0)
                if not pos:
                    break
                end_pos = f"{pos}+{len(query)}c"
                matches.append((pos, end_pos))
                start_pos = end_pos
            text_widget.tag_config("highlight", background="#FFFF00", foreground="#000000")
            text_widget.tag_config("focused_highlight", background="#add8e6", foreground="#000000")
        elif current_tab == 1:
            self.tree.tag_configure("highlight", background="#FFFF00", foreground="#000000")
            self.tree.tag_configure("focused_highlight", background="#add8e6", foreground="#000000")
            def collect_matches(item):
                item_text = self.tree.item(item, "text")
                if query in item_text:
                    matches.append(item)
                for child in self.tree.get_children(item):
                    collect_matches(child)
            if self.tree.get_children():
                collect_matches(self.tree.get_children()[0])

        self.match_positions[current_tab] = matches
        self.current_match_index[current_tab] = 0 if matches else -1
        for i, match in enumerate(matches):
            if current_tab in [0, 2]:
                text_widget.tag_add("focused_highlight" if i == 0 else "highlight", match[0], match[1])
            elif current_tab == 1:
                tags = [t for t in self.tree.item(match, "tags") if t not in ("highlight", "focused_highlight")]
                tags.append("focused_highlight" if i == 0 else "highlight")
                self.tree.item(match, tags=tags)
                if i == 0:
                    self.tree.see(match)
                    self.tree.selection_set(match)
        if matches:
            if current_tab in [0, 2]:
                self.file_handler.center_match(text_widget, matches[0][0])
            self.show_status_message("Search Successful")
        else:
            self.show_status_message("Search Found Nothing")

    def refresh_repo(self):
        if self.file_handler.repo_path:
            self.progress.grid(row=3, column=0, columnspan=3, sticky="ew")
            self.progress.start()
            self.file_handler.load_repo(self.file_handler.repo_path)
            self.refresh_ui()
            self.progress.stop()
            self.progress.grid_forget()

    def open_repo_settings(self):
        SettingsDialog(self.root, self.file_handler, self.settings).show()

    def jump_to_file_content(self, event):
        item_id = self.tree.identify_row(event.y)
        if 'file' in self.tree.item(item_id, "tags"):
            file_path = self.tree.item(item_id, "values")[0]
            self.notebook.select(0)
            pos = self.content_text.search(f"File: {file_path}", "1.0", tk.END)
            if pos:
                self.content_text.see(pos)
                self.file_handler.center_match(self.content_text, pos)

    def save_app_settings(self):
        self.settings.set('app', 'default_tab', self.default_tab_var.get())
        self.settings.set('app', 'expansion', self.expansion_var.get())
        self.settings.set('app', 'levels', self.levels_entry.get())
        self.settings.save()
        self.show_status_message("Settings saved")
        self.apply_default_tab()

    def apply_default_tab(self):
        default_tab = self.settings.get('app', 'default_tab', 'Content Preview')
        for i, tab in enumerate(self.notebook.tabs()):
            if self.notebook.tab(tab, "text") == default_tab:
                self.notebook.select(i)
                break

    def show_status_message(self, message):
        self.status_bar.config(text=message)
        def fade_out(opacity=1.0):
            if opacity > 0:
                self.status_bar.config(fg=f'#{int(255 * opacity):02x}{int(69 * opacity):02x}{int(0):02x}')
                self.root.after(100, fade_out, opacity - 0.1)
            else:
                self.status_bar.config(text="Ready", fg=self.status_color)
        self.root.after(5000, fade_out)

    def save_template(self):
        template_name = tk.filedialog.asksaveasfilename(initialdir=self.template_dir, defaultextension=".txt", filetypes=[("Text files", "*.txt")], title="Save Template")
        if template_name:
            with open(template_name, 'w', encoding='utf-8') as file:
                file.write(self.base_prompt_text.get(1.0, tk.END).strip())
            self.show_status_message("Template saved successfully!")

    def load_template(self):
        template_file = tk.filedialog.askopenfilename(initialdir=self.template_dir, filetypes=[("Text files", "*.txt")], title="Load Template")
        if template_file:
            with open(template_file, 'r', encoding='utf-8') as file:
                self.base_prompt_text.delete(1.0, tk.END)
                self.base_prompt_text.insert(tk.END, file.read())
            self.show_status_message("Template loaded successfully!")

    def delete_template(self):
        template_file = tk.filedialog.askopenfilename(initialdir=self.template_dir, filetypes=[("Text files", "*.txt")], title="Delete Template")
        if template_file and messagebox.askyesno("Confirm", "Are you sure you want to delete this template?"):
            os.remove(template_file)
            self.show_status_message("Template deleted successfully!")

    def clear_current(self):
        current_index = self.notebook.index('current')
        if current_index == 0:
            self.content_text.delete(1.0, tk.END)
            self.file_handler.file_contents = ""
            self.file_handler.token_count = 0
            self.file_handler.loaded_files.clear()
            self.info_label.config(text="Token Count: 0")
            self.copy_button.config(state=tk.DISABLED)
            self.file_handler.update_tree_strikethrough()
        elif current_index == 1:
            self.tree.delete(*self.tree.get_children())
            self.copy_structure_button.config(state=tk.DISABLED)
        elif current_index == 2:
            self.base_prompt_text.delete(1.0, tk.END)
        self.show_status_message("Current tab cleared")

    def clear_all(self):
        self.content_text.delete(1.0, tk.END)
        self.file_handler.file_contents = ""
        self.file_handler.token_count = 0
        self.file_handler.loaded_files.clear()
        self.info_label.config(text="Token Count: 0")
        self.copy_button.config(state=tk.DISABLED)
        self.copy_all_button.config(state=tk.DISABLED)
        self.copy_structure_button.config(state=tk.DISABLED)
        self.tree.delete(*self.tree.get_children())
        self.base_prompt_text.delete(1.0, tk.END)
        self.repo_label.config(text="Current Repo Loaded: None")
        self.file_handler.update_tree_strikethrough()
        self.show_status_message("All tabs cleared")

    def show_about(self):
        messagebox.showinfo("About", f"CodeBase v{self.version}\nA tool to scan repositories and copy contents.\n\nTo be released under\nMIT License Soon\n©2025 Mikael Sundh")

if __name__ == "__main__":
    root = tk.Tk()
    app = RepoPromptGUI(root)
    root.mainloop()