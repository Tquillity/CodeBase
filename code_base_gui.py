import os
import tkinter as tk
from tkinter import filedialog, scrolledtext, IntVar, messagebox, ttk
import pyperclip
import fnmatch
import mimetypes
import appdirs

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        self.id = None
        self.widget.bind("<Enter>", self.schedule_show)
        self.widget.bind("<Leave>", self.hide_tip)

    def schedule_show(self, event):
        if self.id:
            self.widget.after_cancel(self.id)
        self.id = self.widget.after(500, lambda: self.show_tip(event))

    def show_tip(self, event):
        if self.tip:
            return
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tip, text=self.text, bg="#ffffe0", relief="solid", borderwidth=1)
        label.pack()
        self.tip.update_idletasks()
        tip_width = self.tip.winfo_width()
        tip_height = self.tip.winfo_height()
        screen_width = self.tip.winfo_screenwidth()
        screen_height = self.tip.winfo_screenheight()
        if x + tip_width > screen_width:
            x = screen_width - tip_width
        if y + tip_height > screen_height:
            y = screen_height - tip_height
        self.tip.wm_geometry(f"+{x}+{y}")

    def hide_tip(self, event):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None
        if self.tip:
            self.tip.destroy()
            self.tip = None

class RepoPromptGUI:
    def add_button_hover(self, button):
        button.bind("<Enter>", lambda e: button.config(bg="#5a5a5a"))
        button.bind("<Leave>", lambda e: button.config(bg=self.button_bg))

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

    def copy_to_clipboard(self):
        if self.prepend_var.get() == 1:
            base_prompt = self.base_prompt_text.get(1.0, tk.END).strip()
            content_to_copy = base_prompt + "\n\n" + self.file_contents
        else:
            content_to_copy = self.file_contents
        pyperclip.copy(content_to_copy)
        self.show_status_message("Copy Successful!")

    def copy_structure_to_clipboard(self):
        structure_content = self.generate_folder_structure_text()
        pyperclip.copy(structure_content)
        self.show_status_message("Copy Successful!")

    def save_template(self):
        template_name = filedialog.asksaveasfilename(initialdir=self.template_dir, defaultextension=".txt",
                                                     filetypes=[("Text files", "*.txt")], title="Save Template")
        if template_name:
            with open(template_name, 'w', encoding='utf-8') as file:
                file.write(self.base_prompt_text.get(1.0, tk.END).strip())
            messagebox.showinfo("Saved", "Template saved successfully!")

    def load_template(self):
        template_file = filedialog.askopenfilename(initialdir=self.template_dir, filetypes=[("Text files", "*.txt")],
                                                   title="Load Template")
        if template_file:
            with open(template_file, 'r', encoding='utf-8') as file:
                template_content = file.read()
            self.base_prompt_text.delete(1.0, tk.END)
            self.base_prompt_text.insert(tk.END, template_content)

    def delete_template(self):
        template_file = filedialog.askopenfilename(initialdir=self.template_dir, filetypes=[("Text files", "*.txt")],
                                                   title="Delete Template")
        if template_file and messagebox.askyesno("Confirm", "Are you sure you want to delete this template?"):
            os.remove(template_file)
            messagebox.showinfo("Deleted", "Template deleted successfully!")

    def __init__(self, root):
        self.root = root
        self.root.title("CodeBase")
        self.root.geometry("1200x800")
        self.root.configure(bg='#2b2b2b')
        self.text_color = '#ffffff'
        self.button_bg = '#4a4a4a'
        self.button_fg = '#ffffff'
        self.header_color = '#add8e6'
        self.status_color = '#FF4500'
        self.folder_color = '#FFD700'

        self.repo_path = None
        self.file_contents = ""
        self.token_count = 0
        self.ignore_patterns = []
        self.loaded_files = set()

        self.text_extensions_default = {'.txt', '.py', '.cpp', '.c', '.h', '.java', '.js', '.ts', '.tsx',
                                        '.jsx', '.css', '.scss', '.html', '.json', '.md', '.xml', '.svg',
                                        '.gitignore', '.yml', '.yaml', '.toml', '.ini', '.properties',
                                        '.csv', '.tsv', '.log', '.sql', '.sh', '.bash', '.zsh', '.fish',
                                        '.awk', '.sed', '.bat', '.cmd', '.ps1', '.php', '.rb', '.erb',
                                        '.haml', '.slim', '.pl', '.lua', '.r', '.m', '.mm', '.asm', '.v',
                                        '.vhdl', '.verilog', '.s', '.swift', '.kt', '.kts', '.go', '.rs',
                                        '.dart', '.vue', '.pug', '.coffee', '.proto', '.dockerfile',
                                        '.make', '.tf', '.hcl', '.sol', '.gradle', '.groovy', '.scala',
                                        '.clj', '.cljs', '.cljc', '.edn', '.rkt', '.jl', '.purs', '.elm',
                                        '.hs', '.lhs', '.agda', '.idr', '.nix', '.dhall', '.tex', '.bib',
                                        '.sty', '.cls', '.cs', '.fs', '.fsx'}
        self.text_extensions_enabled = {ext: IntVar(value=1) for ext in self.text_extensions_default}
        self.exclude_files_default = {
            'package-lock.json': IntVar(value=0),
            'yarn.lock': IntVar(value=0),
            'composer.lock': IntVar(value=0),
            'Gemfile.lock': IntVar(value=0),
            'poetry.lock': IntVar(value=0)
        }
        self.exclude_files = self.exclude_files_default.copy()

        self.user_data_dir = appdirs.user_data_dir("CodeBase")
        self.template_dir = os.path.join(self.user_data_dir, "templates")
        self.recent_folders_file = os.path.join(self.user_data_dir, "recent_folders.txt")
        self.cache_file = os.path.join(self.user_data_dir, "cache.txt")
        os.makedirs(self.template_dir, exist_ok=True)

        self.recent_folders = self.load_recent_folders()

        self.header_label = tk.Label(root, text="CodeBase", font=("Arial", 16), bg='#2b2b2b', fg=self.text_color)
        self.header_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.version_label = tk.Label(root, text="v1.5", font=("Arial", 10), bg='#2b2b2b', fg=self.header_color)
        self.version_label.grid(row=0, column=1, padx=5, pady=10, sticky="w")

        self.repo_label = tk.Label(root, text="Current Repo Loaded: None", font=("Arial", 14), bg='#2b2b2b', fg='#FF4500')
        self.repo_label.grid(row=0, column=2, padx=50, pady=10, sticky="w")

        tk.Frame(root, bg='#4a4a4a', height=1).grid(row=1, column=0, columnspan=3, sticky="ew")

        self.left_frame = tk.Frame(root, bg='#2b2b2b')
        self.left_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ns")

        tk.Frame(root, bg='#4a4a4a', width=1).grid(row=2, column=1, sticky="ns", padx=5)

        self.right_frame = tk.Frame(root, bg='#2b2b2b')
        self.right_frame.grid(row=2, column=2, padx=10, pady=10, sticky="nsew")

        root.grid_columnconfigure(2, weight=1)
        root.grid_rowconfigure(2, weight=1)

        self.select_button = tk.Button(self.left_frame, text="Select Repo Folder (Ctrl+R)", command=self.select_repo,
                                       bg=self.button_bg, fg=self.button_fg)
        self.select_button.pack(pady=10)
        self.add_button_hover(self.select_button)
        Tooltip(self.select_button, "Choose a repository folder to scan")

        self.settings_button = tk.Button(self.left_frame, text="Repo Settings", command=self.open_settings_dialog,
                                         bg=self.button_bg, fg=self.button_fg)
        self.settings_button.pack(pady=5)
        self.add_button_hover(self.settings_button)
        Tooltip(self.settings_button, "Customize file reading settings")

        self.info_label = tk.Label(self.left_frame, text="Token Count: 0", bg='#2b2b2b', fg=self.text_color)
        self.info_label.pack(pady=5)

        self.copy_button = tk.Button(self.left_frame, text="Copy Contents (Ctrl+C)", command=self.copy_to_clipboard,
                                     state=tk.DISABLED, bg=self.button_bg, fg=self.button_fg)
        self.copy_button.pack(pady=0)
        self.add_button_hover(self.copy_button)
        Tooltip(self.copy_button, "Copy file contents to clipboard")

        self.prepend_var = IntVar()
        self.prepend_checkbox = tk.Checkbutton(self.left_frame, text="Prepend Base Prompt", variable=self.prepend_var,
                                               bg='#2b2b2b', fg=self.text_color, selectcolor='#4a4a4a')
        self.prepend_checkbox.pack(pady=5)
        Tooltip(self.prepend_checkbox, "Include Base Prompt text in copied content")

        self.copy_structure_button = tk.Button(self.left_frame, text="Copy Structure (Ctrl+S)", command=self.copy_structure_to_clipboard,
                                               state=tk.DISABLED, bg=self.button_bg, fg=self.button_fg)
        self.copy_structure_button.pack(pady=10)
        self.add_button_hover(self.copy_structure_button)
        Tooltip(self.copy_structure_button, "Copy folder structure to clipboard")

        self.include_icons_var = IntVar(value=1)
        self.include_icons_checkbox = tk.Checkbutton(self.left_frame, text="Include Icons in Structure",
                                                     variable=self.include_icons_var, bg='#2b2b2b', fg=self.text_color,
                                                     selectcolor='#4a4a4a')
        self.include_icons_checkbox.pack(pady=5)
        Tooltip(self.include_icons_checkbox, "Toggle icons in the copied folder structure")

        self.notebook = ttk.Notebook(self.right_frame)
        self.notebook.pack(fill="both", expand=True)
        style = ttk.Style()
        style.configure("Custom.TNotebook", background='#2b2b2b')
        style.configure("Custom.TNotebook.Tab", background='#3c3c3c', foreground=self.text_color)
        style.map("Custom.TNotebook.Tab", background=[('selected', self.header_color)], foreground=[('selected', '#2b2b2b')])
        self.notebook.configure(style="Custom.TNotebook")

        search_frame = tk.Frame(self.right_frame, bg='#2b2b2b')
        search_frame.pack(side=tk.TOP, anchor="ne", pady=5, padx=10)
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var, bg='#3c3c3c', fg=self.text_color, 
                                     insertbackground=self.text_color, width=60, font=("Arial", 12))
        self.search_entry.pack(side=tk.LEFT, padx=5, pady=2, ipady=5)
        self.search_button = tk.Button(search_frame, text="Search", command=self.search_tab, bg=self.button_bg, fg=self.button_fg, 
                                       font=("Arial", 16))
        self.search_button.pack(side=tk.LEFT, pady=2, ipadx=5, ipady=5)
        self.add_button_hover(self.search_button)
        Tooltip(self.search_entry, "Enter text to search in the current tab")
        Tooltip(self.search_button, "Search the current tab")

        self.next_button = tk.Button(search_frame, text="Next", command=self.next_match,
                                     bg=self.button_bg, fg=self.button_fg, font=("Arial", 16))
        self.next_button.pack(side=tk.LEFT, pady=2, ipadx=5, ipady=5)
        self.add_button_hover(self.next_button)
        Tooltip(self.next_button, "Go to the next search match")

        self.prev_button = tk.Button(search_frame, text="Prev", command=self.prev_match,
                                     bg=self.button_bg, fg=self.button_fg, font=("Arial", 16))
        self.prev_button.pack(side=tk.LEFT, pady=2, ipadx=5, ipady=5)
        self.add_button_hover(self.prev_button)
        Tooltip(self.prev_button, "Go to the previous search match")

        self.search_entry.bind("<Down>", lambda e: self.next_match())
        self.search_entry.bind("<Up>", lambda e: self.prev_match())

        self.match_positions = {}
        self.current_match_index = {}

        self.content_frame = tk.Frame(self.notebook, bg='#2b2b2b')
        self.notebook.add(self.content_frame, text="Content Preview")
        self.content_text = scrolledtext.ScrolledText(self.content_frame, wrap=tk.WORD, bg='#3c3c3c', fg=self.text_color,
                                                      font=("Arial", 10), state=tk.DISABLED)
        self.content_text.pack(fill="both", expand=True)

        self.structure_frame = tk.Frame(self.notebook, bg='#2b2b2b')
        self.notebook.add(self.structure_frame, text="Folder Structure")
        
        structure_button_frame = tk.Frame(self.structure_frame, bg='#2b2b2b')
        structure_button_frame.pack(side=tk.TOP, fill='x', pady=5)

        self.expand_collapse_var = tk.BooleanVar(value=True)
        self.expand_collapse_button = tk.Button(structure_button_frame, text="Expand All",
                                              command=self.toggle_expand_collapse,
                                              bg=self.button_bg, fg=self.button_fg)
        self.expand_collapse_button.pack(side=tk.LEFT, padx=5)
        self.add_button_hover(self.expand_collapse_button)
        Tooltip(self.expand_collapse_button, "Expand or collapse all folders")

        self.show_unloaded_var = IntVar(value=0)
        self.show_unloaded_checkbox = tk.Checkbutton(structure_button_frame, 
                                                    text="Show Unloaded Files", 
                                                    variable=self.show_unloaded_var,
                                                    command=self.update_tree_strikethrough,
                                                    bg='#2b2b2b', fg=self.text_color,
                                                    selectcolor='#4a4a4a')
        self.show_unloaded_checkbox.pack(side=tk.LEFT, padx=5)
        Tooltip(self.show_unloaded_checkbox, "Toggle strikethrough on files not loaded in content")

        self.tree = ttk.Treeview(self.structure_frame, show="tree", style="Custom.Treeview")
        self.tree.pack(fill="both", expand=True)
        style.configure("Custom.Treeview", background="#3c3c3c", foreground=self.text_color, fieldbackground="#3c3c3c")
        style.map("Custom.Treeview", background=[('selected', '#4a4a4a')], foreground=[('selected', self.text_color)])
        scrollbar = ttk.Scrollbar(self.structure_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.tag_bind('folder', '<Double-1>', self.on_double_click)
        self.tree.bind('<<TreeviewOpen>>', self.on_treeview_open)
        self.tree.tag_configure('unloaded', font=(None, -10, 'overstrike'))

        self.base_prompt_frame = tk.Frame(self.notebook, bg='#2b2b2b')
        self.notebook.add(self.base_prompt_frame, text="Base Prompt")
        self.base_prompt_text = scrolledtext.ScrolledText(self.base_prompt_frame, wrap=tk.WORD, bg='#3c3c3c', fg=self.text_color,
                                                          font=("Arial", 10))
        self.base_prompt_text.pack(fill="both", expand=True)

        button_frame = tk.Frame(self.base_prompt_frame, bg='#2b2b2b')
        button_frame.pack(pady=10)
        self.save_template_button = tk.Button(button_frame, text="Save Template (Ctrl+S)", command=self.save_template,
                                              bg=self.button_bg, fg=self.button_fg)
        self.save_template_button.grid(row=0, column=0, padx=5)
        self.add_button_hover(self.save_template_button)
        Tooltip(self.save_template_button, "Save the current Base Prompt as a template")

        self.load_template_button = tk.Button(button_frame, text="Load Template (Ctrl+L)", command=self.load_template,
                                              bg=self.button_bg, fg=self.button_fg)
        self.load_template_button.grid(row=0, column=1, padx=5)
        self.add_button_hover(self.load_template_button)
        Tooltip(self.load_template_button, "Load a saved template into the Base Prompt")

        self.delete_template_button = tk.Button(button_frame, text="Delete Template", command=self.delete_template,
                                                bg=self.button_bg, fg=self.button_fg)
        self.delete_template_button.grid(row=0, column=3, padx=5)
        self.add_button_hover(self.delete_template_button)
        Tooltip(self.delete_template_button, "Delete a saved template")

        self.menu = tk.Menu(self.root, bg=self.button_bg, fg=self.button_fg)
        self.root.config(menu=self.menu)
        help_menu = tk.Menu(self.menu, bg=self.button_bg, fg=self.button_fg)
        self.menu.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

        self.root.bind('<Control-c>', lambda e: self.copy_to_clipboard())
        self.root.bind('<Control-s>', lambda e: self.save_template())
        self.root.bind('<Control-l>', lambda e: self.load_template())
        self.root.bind('<Control-r>', lambda e: self.select_repo())

        clear_button_frame = tk.Frame(self.left_frame, bg='#2b2b2b')
        clear_button_frame.pack(side='bottom', fill='x')
        self.clear_button = tk.Button(clear_button_frame, text="Clear", command=self.clear_current,
                                      bg=self.button_bg, fg=self.button_fg)
        self.add_button_hover(self.clear_button)
        Tooltip(self.clear_button, "Clear data in the current tab")
        self.clear_button.pack(side='left', padx=5, pady=5)

        self.clear_all_button = tk.Button(clear_button_frame, text="Clear All", command=self.clear_all,
                                          bg=self.button_bg, fg=self.button_fg)
        self.add_button_hover(self.clear_all_button)
        Tooltip(self.clear_all_button, "Clear data in all tabs")
        self.clear_all_button.pack(side='left', padx=5, pady=5)

        self.status_bar = tk.Label(root, text="Ready", bg='#2b2b2b', fg=self.status_color, bd=1, relief="sunken", anchor="w")
        self.status_bar.grid(row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=5)

    def open_folder_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Repository Folder")
        dialog.geometry("400x300")
        dialog.configure(bg=self.header_color)

        border_frame = tk.Frame(dialog, bg=self.header_color)
        border_frame.pack(fill="both", expand=True, padx=2, pady=2)
        inner_frame = tk.Frame(border_frame, bg='#3c3c3c')
        inner_frame.pack(fill="both", expand=True)

        tk.Label(inner_frame, text="Select Repository Folder", font=("Arial", 12, "bold"), bg='#3c3c3c', fg=self.text_color).pack(pady=10)

        def truncate_path(path, max_length=45):
            if len(path) > max_length:
                return "…/" + path[-(max_length - 3):]
            return path

        tk.Label(inner_frame, text="Recent Folders:", bg='#3c3c3c', fg=self.text_color).pack(pady=5)
        list_frame = tk.Frame(inner_frame, bg='#2b2b2b', relief="groove", borderwidth=2)
        list_frame.pack(pady=5, padx=20, fill="x")

        folder_var = tk.StringVar()
        selected_label = None

        def select_folder(event, label, folder):
            nonlocal selected_label
            folder_var.set(folder)
            if selected_label and selected_label != label:
                selected_label.config(bg=selected_label.default_bg, fg=self.text_color)
            label.config(bg=self.header_color, fg='#2b2b2b')
            selected_label = label

        def double_click_select(event, folder):
            folder_var.set(folder)
            confirm_selection()

        def refresh_folder_list():
            for widget in list_frame.winfo_children():
                widget.destroy()
            for i, folder in enumerate(self.recent_folders[:5]):
                truncated = truncate_path(folder)
                bg_color = '#3c3c3c' if i % 2 == 0 else '#4a4a4a'
                item_frame = tk.Frame(list_frame, bg=bg_color)
                item_frame.pack(fill="x", padx=5, pady=2)

                folder_label = tk.Label(item_frame, text=truncated, bg=bg_color, fg=self.text_color, cursor="hand2", anchor="w")
                folder_label.default_bg = bg_color
                folder_label.pack(side="left", fill="x", expand=True)
                folder_label.bind("<Button-1>", lambda e, l=folder_label, f=folder: select_folder(e, l, f))
                folder_label.bind("<Double-1>", lambda e, f=folder: double_click_select(e, f))

                remove_btn = tk.Label(item_frame, text="✕", bg=bg_color, fg='#FF4500', font=("Arial", 10), cursor="hand2")
                remove_btn.pack(side="right", padx=(5, 0))
                remove_btn.bind("<Button-1>", lambda e, f=folder: remove_folder(f))
                remove_btn.bind("<Enter>", lambda e, b=remove_btn: b.config(fg="#FF6347"))
                remove_btn.bind("<Leave>", lambda e, b=remove_btn: b.config(fg="#FF4500"))
                Tooltip(remove_btn, f"Remove {truncated} from recent folders")
            if len(self.recent_folders) > 5 and hasattr(dropdown_frame, 'dropdown'):
                dropdown_frame.dropdown['values'] = [truncate_path(f) for f in self.recent_folders[5:20]]

        def remove_folder(folder):
            if folder in self.recent_folders:
                self.recent_folders.remove(folder)
                self.save_recent_folders()
                refresh_folder_list()

        refresh_folder_list()

        dropdown_frame = tk.Frame(inner_frame, bg='#3c3c3c')
        dropdown_frame.pack(pady=5, fill="x", padx=20)
        if len(self.recent_folders) > 5:
            tk.Label(dropdown_frame, text="More Recent Folders:", bg='#3c3c3c', fg=self.text_color).pack(pady=5)
            dropdown_frame.dropdown = ttk.Combobox(dropdown_frame, textvariable=folder_var, 
                                                  values=[truncate_path(f) for f in self.recent_folders[5:20]], 
                                                  state="readonly")
            dropdown_frame.dropdown.pack(pady=5, fill="x")

        def browse_folder():
            folder = filedialog.askdirectory()
            if folder:
                folder_var.set(folder)

        tk.Button(inner_frame, text="Browse", command=browse_folder, bg=self.button_bg, fg=self.button_fg).pack(pady=10)

        def confirm_selection():
            selected = folder_var.get()
            if selected:
                for folder in self.recent_folders:
                    if truncate_path(folder) == selected:
                        selected = folder
                        break
                dialog.selected_folder = selected
                dialog.destroy()
            else:
                messagebox.showwarning("No Selection", "Please select a folder.")

        tk.Button(inner_frame, text="OK", command=confirm_selection, bg=self.button_bg, fg=self.button_fg).pack(pady=10)
        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)
        return getattr(dialog, 'selected_folder', None)

    def open_settings_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Repo Folder Settings")
        dialog.geometry("860x645")
        dialog.configure(bg='#2b2b2b')

        notebook = ttk.Notebook(dialog)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        style = ttk.Style()
        style.configure("Settings.TNotebook", background='#2b2b2b')
        style.configure("Settings.TNotebook.Tab", background='#3c3c3c', foreground=self.text_color)
        style.map("Settings.TNotebook.Tab", background=[('selected', self.header_color)], foreground=[('selected', '#2b2b2b')])
        notebook.configure(style="Settings.TNotebook")

        ext_frame = tk.Frame(notebook, bg='#2b2b2b')
        notebook.add(ext_frame, text="File Extensions")
        ext_canvas = tk.Canvas(ext_frame, bg='#2b2b2b')
        ext_scrollbar = ttk.Scrollbar(ext_frame, orient="vertical", command=ext_canvas.yview)
        ext_scrollable_frame = tk.Frame(ext_canvas, bg='#2b2b2b')

        ext_scrollable_frame.bind(
            "<Configure>",
            lambda e: ext_canvas.configure(scrollregion=ext_canvas.bbox("all"))
        )

        ext_canvas.create_window((0, 0), window=ext_scrollable_frame, anchor="nw")
        ext_canvas.configure(yscrollcommand=ext_scrollbar.set)

        ext_canvas.pack(side="left", fill="both", expand=True)
        ext_scrollbar.pack(side="right", fill="y")

        tk.Label(ext_scrollable_frame, text="Select file extensions to include:", bg='#2b2b2b', fg=self.text_color).grid(row=0, column=0, columnspan=3, pady=5)
        for i, ext in enumerate(sorted(self.text_extensions_default)):
            row = (i // 9) + 1
            col = i % 9
            cb = tk.Checkbutton(ext_scrollable_frame, text=ext, variable=self.text_extensions_enabled[ext],
                                bg='#2b2b2b', fg=self.text_color, selectcolor='#4a4a4a')
            cb.grid(row=row, column=col, sticky="w", padx=5, pady=2)

        exclude_frame = tk.Frame(notebook, bg='#2b2b2b')
        notebook.add(exclude_frame, text="Exclude Files")
        tk.Label(exclude_frame, text="Select files to exclude:", bg='#2b2b2b', fg=self.text_color).grid(row=0, column=0, pady=5)
        for i, file in enumerate(sorted(self.exclude_files_default.keys())):
            cb = tk.Checkbutton(exclude_frame, text=file, variable=self.exclude_files[file],
                                bg='#2b2b2b', fg=self.text_color, selectcolor='#4a4a4a')
            cb.grid(row=i+1, column=0, sticky="w", padx=10, pady=2)

        def apply_and_refresh():
            if self.repo_path and os.path.isdir(self.repo_path):
                self.file_contents = self.read_repo_files(self.repo_path)
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    f.write(self.repo_path + '\n')
                    f.write(self.file_contents)

                self.token_count = len(self.file_contents.split())
                formatted_count = f"{self.token_count:,}".replace(",", " ")
                self.info_label.config(text=f"Token Count: {formatted_count}")
                self.copy_button.config(state=tk.NORMAL)
                self.copy_structure_button.config(state=tk.NORMAL)

                self.content_text.config(state=tk.NORMAL)
                self.content_text.delete(1.0, tk.END)
                self.content_text.tag_configure("filename", foreground="red")
                if self.file_contents.startswith("File: "):
                    sections = self.file_contents[len("File: "):].split("\nFile: ")
                    sections = ["File: " + s for s in sections]
                else:
                    sections = []
                for section in sections:
                    filename_end = section.find("\nContent:\n")
                    if filename_end != -1:
                        filename = section[6:filename_end].strip()
                        content = section[filename_end + 11:]
                        self.content_text.insert(tk.END, f"File: {filename}\n", "filename")
                        self.content_text.insert(tk.END, f"Content:\n{content}\n\n")
                    else:
                        self.content_text.insert(tk.END, section + "\n\n")
                self.content_text.config(state=tk.DISABLED)

                self.populate_tree(self.repo_path)
                self.show_status_message("Settings Applied and Refreshed!")
            else:
                messagebox.showwarning("No Repo Loaded", "No repository loaded to refresh. Settings will apply on next load.")
            dialog.destroy()

        tk.Button(dialog, text="Apply & Refresh with new Settings", command=apply_and_refresh, 
                  bg=self.button_bg, fg=self.button_fg).pack(pady=10)
        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)

    def select_repo(self):
        selected_folder = self.open_folder_dialog()
        if selected_folder and os.path.isdir(selected_folder):
            self.repo_path = os.path.abspath(selected_folder)
            self.update_recent_folders(self.repo_path)

            repo_name = os.path.basename(self.repo_path)
            self.repo_label.config(text=f"Current Repo Loaded: {repo_name}")

            gitignore_path = os.path.join(self.repo_path, '.gitignore')
            self.ignore_patterns = self.parse_gitignore(gitignore_path)

            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cached_repo_path = f.readline().strip()
                self.file_contents = self.read_repo_files(self.repo_path)
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    f.write(self.repo_path + '\n')
                    f.write(self.file_contents)
            else:
                self.file_contents = self.read_repo_files(self.repo_path)
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    f.write(self.repo_path + '\n')
                    f.write(self.file_contents)

            self.token_count = len(self.file_contents.split())
            formatted_count = f"{self.token_count:,}".replace(",", " ")
            self.info_label.config(text=f"Token Count: {formatted_count}")
            self.copy_button.config(state=tk.NORMAL)
            self.copy_structure_button.config(state=tk.NORMAL)

            self.content_text.config(state=tk.NORMAL)
            self.content_text.delete(1.0, tk.END)
            self.content_text.tag_configure("filename", foreground="red")
            if self.file_contents.startswith("File: "):
                sections = self.file_contents[len("File: "):].split("\nFile: ")
                sections = ["File: " + s for s in sections]
            else:
                sections = []
            for section in sections:
                filename_end = section.find("\nContent:\n")
                if filename_end != -1:
                    filename = section[6:filename_end].strip()
                    content = section[filename_end + 11:]
                    self.content_text.insert(tk.END, f"File: {filename}\n", "filename")
                    self.content_text.insert(tk.END, f"Content:\n{content}\n\n")
                else:
                    self.content_text.insert(tk.END, section + "\n\n")
            self.content_text.config(state=tk.DISABLED)

            self.populate_tree(self.repo_path)
        else:
            messagebox.showerror("Invalid Folder", "Please select a valid directory.")

    def populate_tree(self, root_dir):
        self.tree.delete(*self.tree.get_children())
        root_basename = os.path.basename(root_dir)
        root_icon = "📁" if os.path.isdir(root_dir) else "📄"
        root_id = self.tree.insert("", "end", text=f"{root_icon} {root_basename}", open=True, tags=('folder',), values=(root_dir,))
        self.build_tree(root_dir, root_id)
        self.tree.tag_configure('folder', foreground=self.folder_color)
        self.tree.tag_configure('file', foreground=self.text_color)
        self.update_tree_strikethrough()

    def build_tree(self, path, parent_id):
        if self.is_ignored(path):
            return
        try:
            items = [item for item in sorted(os.listdir(path)) if not self.is_ignored(os.path.join(path, item))]
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

    def on_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if 'folder' in self.tree.item(item_id, "tags"):
            item_path = self.tree.item(item_id, "values")[0]
            self.expand_folder(item_path, item_id)

    def on_treeview_open(self, event):
        item_id = self.tree.focus()
        if 'folder' in self.tree.item(item_id, "tags"):
            children = self.tree.get_children(item_id)
            if children and all(self.tree.item(child, "text") == "Loading..." for child in children):
                item_path = self.tree.item(item_id, "values")[0]
                self.expand_folder(item_path, item_id)

    def expand_folder(self, path, item_id):
        try:
            original_text = self.tree.item(item_id, "text")
            self.tree.item(item_id, text=f"{original_text} (Loading...)")
            self.root.update_idletasks()
            for child in self.tree.get_children(item_id):
                self.tree.delete(child)
            self.build_tree(path, item_id)
            self.tree.item(item_id, text=original_text)
            self.update_tree_strikethrough()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to expand folder {path}: {str(e)}")
            self.tree.item(item_id, text=original_text)

    def parse_gitignore(self, gitignore_path):
        ignore_patterns = []
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r') as file:
                for line in file:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        ignore_patterns.append(line)
        return ignore_patterns

    def is_ignored(self, path):
        rel_path = os.path.relpath(path, self.repo_path)
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(os.path.basename(path), pattern):
                return True
        if '.git' in rel_path.split(os.sep):
            return True
        return False

    def is_text_file(self, file_path):
        mime_type, _ = mimetypes.guess_type(file_path)
        ext = os.path.splitext(file_path)[1].lower()
        filename = os.path.basename(file_path)
        excluded = filename in self.exclude_files and self.exclude_files[filename].get() == 1
        return (
            (mime_type and mime_type.startswith('text')) or
            (ext in self.text_extensions_default and self.text_extensions_enabled[ext].get() == 1)
        ) and not excluded

    def read_repo_files(self, root_dir):
        self.loaded_files.clear()
        file_contents = []
        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [d for d in dirnames if not self.is_ignored(os.path.join(dirpath, d))]
            for filename in filenames:
                file_path = os.path.normcase(os.path.join(dirpath, filename))
                if not self.is_ignored(file_path) and self.is_text_file(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as file:
                            content = file.read()
                            file_contents.append(f"File: {file_path}\nContent:\n{content}\n")
                            self.loaded_files.add(file_path)
                    except UnicodeDecodeError:
                        messagebox.showwarning("File Skipped", f"Skipping {filename}: Not a UTF-8 text file")
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to read {filename}: {str(e)}")
        return "\n".join(file_contents)

    def update_tree_strikethrough(self):
        def update_item(item):
            values = self.tree.item(item, "values")
            if values and len(values) > 0:
                item_path = os.path.normcase(values[0])
                tags = list(self.tree.item(item, "tags"))
                if 'file' in tags:
                    if self.show_unloaded_var.get() and item_path not in self.loaded_files:
                        if 'unloaded' not in tags:
                            tags.append('unloaded')
                    else:
                        if 'unloaded' in tags:
                            tags.remove('unloaded')
                    self.tree.item(item, tags=tags)
            for child in self.tree.get_children(item):
                update_item(child)

        children = self.tree.get_children()
        if children:
            update_item(children[0])
            self.show_status_message("Unloaded files visibility updated")
        else:
            self.show_status_message("No tree items to update")

    def generate_folder_structure_text(self):
        def traverse_tree(item_id, prefix="", indent=""):
            lines = []
            item_text = self.tree.item(item_id, "text")
            if self.include_icons_var.get() == 0:
                item_text = item_text[2:]
            lines.append(f"{indent}{prefix}{item_text}")
            children = self.tree.get_children(item_id)
            for i, child_id in enumerate(children):
                if i == len(children) - 1:
                    sub_prefix = "└── "
                    sub_indent = indent + "    "
                else:
                    sub_prefix = "├── "
                    sub_indent = indent + "│   "
                lines.extend(traverse_tree(child_id, sub_prefix, sub_indent))
            return lines

        root_items = self.tree.get_children()
        if not root_items:
            return ""
        return "\n".join(traverse_tree(root_items[0]))

    def show_status_message(self, message):
        self.status_bar.config(text=message)
        def fade_out(opacity=1.0):
            if opacity > 0:
                self.status_bar.config(fg=f'#{int(255 * opacity):02x}{int(255 * opacity):02x}{int(0):02x}')
                self.root.after(100, fade_out, opacity - 0.1)
            else:
                self.status_bar.config(text="Ready", fg=self.status_color)
        self.root.after(5000, fade_out)

    def clear_current(self):
        current_index = self.notebook.index('current')
        if current_index == 0:
            self.content_text.config(state=tk.NORMAL)
            self.content_text.delete(1.0, tk.END)
            self.content_text.config(state=tk.DISABLED)
            self.file_contents = ""
            self.token_count = 0
            self.loaded_files.clear()
            self.info_label.config(text="Token Count: 0")
            self.copy_button.config(state=tk.DISABLED)
            self.update_tree_strikethrough()
        elif current_index == 1:
            self.tree.delete(*self.tree.get_children())
            self.copy_structure_button.config(state=tk.DISABLED)
        elif current_index == 2:
            self.base_prompt_text.delete(1.0, tk.END)

    def clear_all(self):
        self.content_text.config(state=tk.NORMAL)
        self.content_text.delete(1.0, tk.END)
        self.content_text.config(state=tk.DISABLED)
        self.file_contents = ""
        self.token_count = 0
        self.loaded_files.clear()
        self.info_label.config(text="Token Count: 0")
        self.copy_button.config(state=tk.DISABLED)
        self.tree.delete(*self.tree.get_children())
        self.copy_structure_button.config(state=tk.DISABLED)
        self.base_prompt_text.delete(1.0, tk.END)
        self.repo_label.config(text="Current Repo Loaded: None")
        self.update_tree_strikethrough()

    def show_about(self):
        messagebox.showinfo("About", "CodeBase v1.5\nA tool to scan repositories and copy contents.\n\nTo be released under\nMIT License Soon\n©2025 Mikael Sundh")

    def expand_all(self, item=""):
        for child in self.tree.get_children(item):
            if 'folder' in self.tree.item(child, "tags"):
                self.tree.item(child, open=True)
                children = self.tree.get_children(child)
                if children and self.tree.item(children[0], "text") == "Loading...":
                    item_path = self.tree.item(child, "values")[0]
                    self.expand_folder(item_path, child)
                self.expand_all(child)

    def collapse_all(self, item=""):
        for child in self.tree.get_children(item):
            if 'folder' in self.tree.item(child, "tags"):
                self.tree.item(child, open=False)
                self.collapse_all(child)

    def toggle_expand_collapse(self):
        if self.expand_collapse_var.get():
            self.expand_all()
            self.expand_collapse_button.config(text="Collapse All")
            self.expand_collapse_var.set(False)
        else:
            self.collapse_all()
            self.expand_collapse_button.config(text="Expand All")
            self.expand_collapse_var.set(True)
        self.show_status_message("Folder structure updated")

    def search_tab(self):
        query = self.search_var.get()
        if not query:
            return

        current_tab = self.notebook.index(self.notebook.select())
        match_found = False

        if current_tab == 0:
            self.content_text.tag_remove("highlight", "1.0", tk.END)
            self.content_text.tag_remove("focused_highlight", "1.0", tk.END)
        elif current_tab == 1:
            for item in self.tree.get_children():
                self.tree.item(item, tags=self.tree.item(item, "tags")[0])
        elif current_tab == 2:
            self.base_prompt_text.tag_remove("highlight", "1.0", tk.END)
            self.base_prompt_text.tag_remove("focused_highlight", "1.0", tk.END)

        if current_tab in [0, 2]:
            text_widget = self.content_text if current_tab == 0 else self.base_prompt_text
            if current_tab == 0:
                text_widget.config(state=tk.NORMAL)
            matches = []
            start_pos = "1.0"
            while True:
                pos = text_widget.search(query, start_pos, stopindex=tk.END, nocase=0)
                if not pos:
                    break
                end_pos = f"{pos}+{len(query)}c"
                matches.append((pos, end_pos))
                start_pos = end_pos
            self.match_positions[current_tab] = matches
            self.current_match_index[current_tab] = 0 if matches else -1
            for i, match in enumerate(matches):
                if i == self.current_match_index.get(current_tab, -1):
                    text_widget.tag_add("focused_highlight", match[0], match[1])
                else:
                    text_widget.tag_add("highlight", match[0], match[1])
            text_widget.tag_config("highlight", background="#FFFF00", foreground="#000000")
            text_widget.tag_config("focused_highlight", background=self.header_color, foreground="#000000")
            if matches:
                self.center_match(text_widget, matches[0][0])
                match_found = True
            if current_tab == 0:
                text_widget.config(state=tk.DISABLED)
        elif current_tab == 1:
            matches = []
            def collect_matches(item):
                nonlocal match_found
                item_text = self.tree.item(item, "text")
                if query in item_text:
                    matches.append(item)
                    match_found = True
                for child in self.tree.get_children(item):
                    collect_matches(child)
            collect_matches("")
            self.match_positions[current_tab] = matches
            self.current_match_index[current_tab] = 0 if matches else -1
            for i, item in enumerate(matches):
                if i == self.current_match_index.get(current_tab, -1):
                    self.tree.item(item, tags=("focused_highlight",))
                else:
                    self.tree.item(item, tags=("highlight",))
            self.tree.tag_configure("highlight", background="#FFFF00", foreground="#000000")
            self.tree.tag_configure("focused_highlight", background=self.header_color, foreground="#000000")
            if matches:
                self.tree.see(matches[0])
                self.tree.selection_set(matches[0])
                match_found = True

        if match_found:
            self.show_status_message("Search Successful")
        else:
            self.show_status_message("Search Found Nothing")

    def center_match(self, text_widget, pos):
        text_widget.see(pos)
        top, bottom = text_widget.yview()
        delta = bottom - top
        line = int(text_widget.index(pos).split('.')[0])
        total_lines = int(text_widget.index("end").split('.')[0])
        if total_lines > 0:
            f = (line - 1) / total_lines
            new_top = max(0, min(1 - delta, f - delta / 2))
            text_widget.yview_moveto(new_top)

    def next_match(self):
        current_tab = self.notebook.index(self.notebook.select())
        matches = self.match_positions.get(current_tab, [])
        if not matches:
            return
        index = self.current_match_index.get(current_tab, -1)
        if index < len(matches) - 1:
            if current_tab in [0, 2]:
                text_widget = self.content_text if current_tab == 0 else self.base_prompt_text
                if current_tab == 0:
                    text_widget.config(state=tk.NORMAL)
                old_pos, old_end = matches[index]
                text_widget.tag_remove("focused_highlight", old_pos, old_end)
                text_widget.tag_add("highlight", old_pos, old_end)
            elif current_tab == 1:
                old_item = matches[index]
                self.tree.item(old_item, tags=("highlight",))

            index += 1
            self.current_match_index[current_tab] = index
            if current_tab in [0, 2]:
                text_widget = self.content_text if current_tab == 0 else self.base_prompt_text
                pos, end = matches[index]
                text_widget.tag_remove("highlight", pos, end)
                text_widget.tag_add("focused_highlight", pos, end)
                self.center_match(text_widget, pos)
                if current_tab == 0:
                    text_widget.config(state=tk.DISABLED)
            elif current_tab == 1:
                item = matches[index]
                self.tree.item(item, tags=("focused_highlight",))
                self.tree.see(item)
                self.tree.selection_set(item)

    def prev_match(self):
        current_tab = self.notebook.index(self.notebook.select())
        matches = self.match_positions.get(current_tab, [])
        if not matches:
            return
        index = self.current_match_index.get(current_tab, -1)
        if index > 0:
            if current_tab in [0, 2]:
                text_widget = self.content_text if current_tab == 0 else self.base_prompt_text
                if current_tab == 0:
                    text_widget.config(state=tk.NORMAL)
                old_pos, old_end = matches[index]
                text_widget.tag_remove("focused_highlight", old_pos, old_end)
                text_widget.tag_add("highlight", old_pos, old_end)
            elif current_tab == 1:
                old_item = matches[index]
                self.tree.item(old_item, tags=("highlight",))

            index -= 1
            self.current_match_index[current_tab] = index
            if current_tab in [0, 2]:
                text_widget = self.content_text if current_tab == 0 else self.base_prompt_text
                pos, end = matches[index]
                text_widget.tag_remove("highlight", pos, end)
                text_widget.tag_add("focused_highlight", pos, end)
                self.center_match(text_widget, pos)
                if current_tab == 0:
                    text_widget.config(state=tk.DISABLED)
            elif current_tab == 1:
                item = matches[index]
                self.tree.item(item, tags=("focused_highlight",))
                self.tree.see(item)
                self.tree.selection_set(item)

if __name__ == "__main__":
    root = tk.Tk()
    app = RepoPromptGUI(root)
    root.mainloop()