import os
import tkinter as tk
from tkinter import filedialog, scrolledtext, IntVar, messagebox, ttk
import pyperclip
import fnmatch
import mimetypes
import appdirs

class Tooltip:
    # Handles tooltip popups on hover with delay and screen boundary checks
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        self.id = None
        self.widget.bind("<Enter>", self.schedule_show)
        self.widget.bind("<Leave>", self.hide_tip)

    # Schedules tooltip display after 500ms delay, cancels if mouse moves fast
    def schedule_show(self, event):
        if self.id:
            self.widget.after_cancel(self.id)
        self.id = self.widget.after(500, lambda: self.show_tip(event))

    # Shows tooltip 25px below/right of widget, adjusts for screen edges
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

    # Hides tooltip when mouse leaves, cancels scheduled show if not yet visible
    def hide_tip(self, event):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None
        if self.tip:
            self.tip.destroy()
            self.tip = None

class RepoPromptGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CodeBase")
        self.root.geometry("1024x600")

        # Set up dark mode colors
        self.root.configure(bg='#2b2b2b')
        self.text_color = '#ffffff'
        self.button_bg = '#4a4a4a'
        self.button_fg = '#ffffff'
        self.header_color = '#add8e6'
        self.status_color = '#ffff00'
        self.folder_color = '#FFD700'

        # Initialize repo-related vars
        self.repo_path = None
        self.file_contents = ""
        self.token_count = 0
        self.ignore_patterns = []

        # Set up user data dirs
        self.user_data_dir = appdirs.user_data_dir("CodeBase")
        self.template_dir = os.path.join(self.user_data_dir, "templates")
        self.recent_folders_file = os.path.join(self.user_data_dir, "recent_folders.txt")
        self.cache_file = os.path.join(self.user_data_dir, "cache.txt")
        os.makedirs(self.template_dir, exist_ok=True)

        # Load recent folders from file
        self.recent_folders = self.load_recent_folders()

        # Header setup
        self.header_label = tk.Label(root, text="CodeBase", font=("Arial", 16), bg='#2b2b2b', fg=self.text_color)
        self.header_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.version_label = tk.Label(root, text="v1.0", font=("Arial", 10), bg='#2b2b2b', fg=self.header_color)
        self.version_label.grid(row=0, column=1, padx=5, pady=10, sticky="w")

        # Add horizontal separator below header
        tk.Frame(root, bg='#4a4a4a', height=1).grid(row=1, column=0, columnspan=2, sticky="ew")

        # Left frame for controls
        self.left_frame = tk.Frame(root, bg='#2b2b2b')
        self.left_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ns")

        # Vertical separator between frames
        tk.Frame(root, bg='#4a4a4a', width=1).grid(row=2, column=1, sticky="ns", padx=5)

        # Right frame for tabs
        self.right_frame = tk.Frame(root, bg='#2b2b2b')
        self.right_frame.grid(row=2, column=2, padx=10, pady=10, sticky="nsew")

        # Make right frame expandable
        root.grid_columnconfigure(2, weight=1)
        root.grid_rowconfigure(2, weight=1)

        # Left frame widgets
        self.select_button = tk.Button(self.left_frame, text="Select Repo Folder (Ctrl+R)", command=self.select_repo,
                                       bg=self.button_bg, fg=self.button_fg)
        self.select_button.pack(pady=10)
        self.add_button_hover(self.select_button)
        Tooltip(self.select_button, "Choose a repository folder to scan")

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

        # Notebook setup
        self.notebook = ttk.Notebook(self.right_frame)
        self.notebook.pack(fill="both", expand=True)
        style = ttk.Style()
        style.configure("Custom.TNotebook", background='#2b2b2b')
        style.configure("Custom.TNotebook.Tab", background='#3c3c3c', foreground=self.text_color)
        style.map("Custom.TNotebook.Tab", background=[('selected', self.header_color)], foreground=[('selected', '#2b2b2b')])
        self.notebook.configure(style="Custom.TNotebook")

        # Content Preview tab
        self.content_frame = tk.Frame(self.notebook, bg='#2b2b2b')
        self.notebook.add(self.content_frame, text="Content Preview")
        self.content_text = scrolledtext.ScrolledText(self.content_frame, wrap=tk.WORD, bg='#3c3c3c', fg=self.text_color,
                                                      font=("Arial", 10), state=tk.DISABLED)
        self.content_text.pack(fill="both", expand=True)

        # Folder Structure tab
        self.structure_frame = tk.Frame(self.notebook, bg='#2b2b2b')
        self.notebook.add(self.structure_frame, text="Folder Structure")
        self.tree = ttk.Treeview(self.structure_frame, show="tree", style="Custom.Treeview")
        self.tree.pack(fill="both", expand=True)
        style.configure("Custom.Treeview", background="#3c3c3c", foreground=self.text_color, fieldbackground="#3c3c3c")
        style.map("Custom.Treeview", background=[('selected', '#4a4a4a')], foreground=[('selected', self.text_color)])
        scrollbar = ttk.Scrollbar(self.structure_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.tag_bind('folder', '<Double-1>', self.on_double_click)
        self.tree.bind('<<TreeviewOpen>>', self.on_treeview_open)

        # Base Prompt tab
        self.base_prompt_frame = tk.Frame(self.notebook, bg='#2b2b2b')
        self.notebook.add(self.base_prompt_frame, text="Base Prompt")
        self.base_prompt_text = scrolledtext.ScrolledText(self.base_prompt_frame, wrap=tk.WORD, bg='#3c3c3c', fg=self.text_color,
                                                          font=("Arial", 10))
        self.base_prompt_text.pack(fill="both", expand=True)

        # Base Prompt buttons
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

        # Menu setup
        self.menu = tk.Menu(self.root, bg=self.button_bg, fg=self.button_fg)
        self.root.config(menu=self.menu)
        help_menu = tk.Menu(self.menu, bg=self.button_bg, fg=self.button_fg)
        self.menu.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

        # Bind keyboard shortcuts
        self.root.bind('<Control-c>', lambda e: self.copy_to_clipboard())
        self.root.bind('<Control-s>', lambda e: self.save_template())
        self.root.bind('<Control-l>', lambda e: self.load_template())
        self.root.bind('<Control-r>', lambda e: self.select_repo())

        # Clear buttons setup
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

        # Status bar at bottom
        self.status_bar = tk.Label(root, text="Ready", bg='#2b2b2b', fg=self.status_color, bd=1, relief="sunken", anchor="w")
        self.status_bar.grid(row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=5)

    # Add hover effect to buttons, changes bg color on mouse enter/leave
    def add_button_hover(self, button):
        button.bind("<Enter>", lambda e: button.config(bg="#5a5a5a"))
        button.bind("<Leave>", lambda e: button.config(bg=self.button_bg))

    # Load recent folders from file, return empty list if file doesn’t exist
    def load_recent_folders(self):
        if os.path.exists(self.recent_folders_file):
            with open(self.recent_folders_file, 'r') as file:
                return [line.strip() for line in file.readlines() if line.strip()]
        return []

    # Save recent folders to file
    def save_recent_folders(self):
        with open(self.recent_folders_file, 'w') as file:
            for folder in self.recent_folders:
                file.write(f"{folder}\n")

    # Update recent folders list, keep max 20 entries
    def update_recent_folders(self, new_folder):
        if new_folder in self.recent_folders:
            self.recent_folders.remove(new_folder)
        self.recent_folders.insert(0, new_folder)
        if len(self.recent_folders) > 20:
            self.recent_folders = self.recent_folders[:20]
        self.save_recent_folders()

    # Dialog for selecting repo folder with recent folders list
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

        # Shorten paths longer than 50 chars
        def truncate_path(path, max_length=50):
            if len(path) > max_length:
                return "…/" + path[-(max_length - 3):]
            return path

        tk.Label(inner_frame, text="Recent Folders:", bg='#3c3c3c', fg=self.text_color).pack(pady=5)
        list_frame = tk.Frame(inner_frame, bg='#2b2b2b', relief="groove", borderwidth=2)
        list_frame.pack(pady=5, padx=20, fill="x")

        folder_var = tk.StringVar()
        selected_label = None

        # Highlight selected folder in blue with dark text
        def select_folder(event, label, folder):
            nonlocal selected_label
            folder_var.set(folder)
            if selected_label and selected_label != label:
                selected_label.config(bg=selected_label.default_bg, fg=self.text_color)
            label.config(bg=self.header_color, fg='#2b2b2b')
            selected_label = label

        # Confirm selection on double-click
        def double_click_select(event, folder):
            folder_var.set(folder)
            confirm_selection()

        # Populate recent folders list (top 5)
        for i, folder in enumerate(self.recent_folders[:5]):
            truncated = truncate_path(folder)
            bg_color = '#3c3c3c' if i % 2 == 0 else '#4a4a4a'
            folder_label = tk.Label(list_frame, text=truncated, bg=bg_color, fg=self.text_color, cursor="hand2", anchor="w")
            folder_label.default_bg = bg_color
            folder_label.pack(fill="x", padx=5, pady=2)
            folder_label.bind("<Button-1>", lambda e, l=folder_label, f=truncated: select_folder(e, l, f))
            folder_label.bind("<Double-1>", lambda e, f=truncated: double_click_select(e, f))

        # Add dropdown for additional folders if >5
        if len(self.recent_folders) > 5:
            tk.Label(inner_frame, text="More Recent Folders:", bg='#3c3c3c', fg=self.text_color).pack(pady=5)
            additional_folders = [truncate_path(folder) for folder in self.recent_folders[5:20]]
            ttk.Combobox(inner_frame, textvariable=folder_var, values=additional_folders, state="readonly").pack(pady=5, fill="x", padx=20)

        # Open file explorer for manual folder selection
        def browse_folder():
            folder = filedialog.askdirectory()
            if folder:
                folder_var.set(folder)

        tk.Button(inner_frame, text="Browse", command=browse_folder, bg=self.button_bg, fg=self.button_fg).pack(pady=10)

        # Confirm selection and close dialog
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

    # Load and process selected repository
    def select_repo(self):
        selected_folder = self.open_folder_dialog()
        if selected_folder and os.path.isdir(selected_folder):
            self.repo_path = os.path.realpath(selected_folder)
            self.update_recent_folders(self.repo_path)

            gitignore_path = os.path.join(self.repo_path, '.gitignore')
            self.ignore_patterns = self.parse_gitignore(gitignore_path)

            # Load from cache if valid, otherwise read files
            print(f"Cache file exists: {os.path.exists(self.cache_file)}")
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cached_repo_path = f.readline().strip()
                    if cached_repo_path == self.repo_path and os.path.getmtime(self.cache_file) > os.path.getmtime(self.repo_path):
                        self.file_contents = f.read()
                    else:
                        print("Reading files from repository...")
                        self.file_contents = self.read_repo_files(self.repo_path)
                        with open(self.cache_file, 'w', encoding='utf-8') as f:
                            f.write(self.repo_path + '\n')
                            f.write(self.file_contents)     
            else:
                print("Reading files from repository...")
                self.file_contents = self.read_repo_files(self.repo_path)
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    f.write(self.repo_path + '\n')
                    f.write(self.file_contents)

            # Update token count and enable copy buttons
            self.token_count = len(self.file_contents.split())
            formatted_count = f"{self.token_count:,}".replace(",", " ")
            self.info_label.config(text=f"Token Count: {formatted_count}")
            self.copy_button.config(state=tk.NORMAL)
            self.copy_structure_button.config(state=tk.NORMAL)

            # Populate content preview with red filenames
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

    # Initialize folder structure tree with root dir
    def populate_tree(self, root_dir):
        self.tree.delete(*self.tree.get_children())
        root_basename = os.path.basename(root_dir)
        root_icon = "📁" if os.path.isdir(root_dir) else "📄"
        root_id = self.tree.insert("", "end", text=f"{root_icon} {root_basename}", open=True, tags=('folder',))
        self.build_tree(root_dir, root_id)
        self.tree.tag_configure('folder', foreground=self.folder_color)
        self.tree.tag_configure('file', foreground=self.text_color)

    # Build tree nodes for given path, add dummy "Loading..." for folders
    def build_tree(self, path, parent_id):
        if self.is_ignored(path):
            return
        try:
            items = [item for item in sorted(os.listdir(path)) if not self.is_ignored(os.path.join(path, item))]
            for item in items:
                item_path = os.path.join(path, item)
                icon = "📁" if os.path.isdir(item_path) else "📄"
                tag = 'folder' if os.path.isdir(item_path) else 'file'
                item_id = self.tree.insert(parent_id, "end", text=f"{icon} {item}", values=(item_path,), open=False, tags=(tag,))
                if os.path.isdir(item_path):
                    self.tree.insert(item_id, "end", text="Loading...", tags=('dummy',))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to list directory {path}: {str(e)}")

    # Expand folder on double-click
    def on_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if 'folder' in self.tree.item(item_id, "tags"):
            item_path = self.tree.item(item_id, "values")[0]
            self.expand_folder(item_path, item_id)

    # Expand folder when arrow clicked, if not already loaded
    def on_treeview_open(self, event):
        item_id = self.tree.focus()
        if 'folder' in self.tree.item(item_id, "tags"):
            children = self.tree.get_children(item_id)
            if children and all(self.tree.item(child, "text") == "Loading..." for child in children):
                item_path = self.tree.item(item_id, "values")[0]
                self.expand_folder(item_path, item_id)

    # Load folder contents, replace "Loading..." with actual items
    def expand_folder(self, path, item_id):
        try:
            original_text = self.tree.item(item_id, "text")
            self.tree.item(item_id, text=f"{original_text} (Loading...)")
            self.root.update_idletasks()
            for child in self.tree.get_children(item_id):
                self.tree.delete(child)
            self.build_tree(path, item_id)
            self.tree.item(item_id, text=original_text)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to expand folder {path}: {str(e)}")
            self.tree.item(item_id, text=original_text)

    # Parse .gitignore file for ignore patterns
    def parse_gitignore(self, gitignore_path):
        ignore_patterns = []
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r') as file:
                for line in file:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        ignore_patterns.append(line)
        return ignore_patterns

    # Check if path matches ignore patterns or is .git
    def is_ignored(self, path):
        rel_path = os.path.relpath(path, self.repo_path)
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(os.path.basename(path), pattern):
                return True
        if '.git' in rel_path.split(os.sep):
            return True
        return False

    # Detect if file is text-based using MIME type
    def is_text_file(self, file_path):
        mime_type, _ = mimetypes.guess_type(file_path)
        ext = os.path.splitext(file_path)[1].lower()
        text_extensions = {'.txt', '.py', '.cpp', '.c', '.h', '.java', '.js', '.ts', '.tsx', 
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
        return (mime_type and mime_type.startswith('text')) or ext in text_extensions

    # Read all text files in repo, format with "File:" and "Content:"
    def read_repo_files(self, root_dir):
        file_contents = []
        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [d for d in dirnames if not self.is_ignored(os.path.join(dirpath, d))]
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if not self.is_ignored(file_path) and self.is_text_file(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as file:
                            content = file.read()
                            file_contents.append(f"File: {file_path}\nContent:\n{content}\n")
                    except UnicodeDecodeError:
                        messagebox.showwarning("File Skipped", f"Skipping {filename}: Not a UTF-8 text file")
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to read {filename}: {str(e)}")
        return "\n".join(file_contents)

    # Generate ASCII tree structure text, optional icons
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

    # Show status message with fade-out effect
    def show_status_message(self, message):
        self.status_bar.config(text=message)
        def fade_out(opacity=1.0):
            if opacity > 0:
                self.status_bar.config(fg=f'#{int(255 * opacity):02x}{int(255 * opacity):02x}{int(0):02x}')
                self.root.after(100, fade_out, opacity - 0.1)
            else:
                self.status_bar.config(text="Ready", fg=self.status_color)
        self.root.after(5000, fade_out)

    # Copy content to clipboard, optionally prepend base prompt
    def copy_to_clipboard(self):
        if self.prepend_var.get() == 1:
            base_prompt = self.base_prompt_text.get(1.0, tk.END).strip()
            content_to_copy = base_prompt + "\n\n" + self.file_contents
        else:
            content_to_copy = self.file_contents
        pyperclip.copy(content_to_copy)
        self.show_status_message("Copy Successful!")

    # Copy folder structure to clipboard
    def copy_structure_to_clipboard(self):
        structure_content = self.generate_folder_structure_text()
        pyperclip.copy(structure_content)
        self.show_status_message("Copy Successful!")

    # Save base prompt as template file
    def save_template(self):
        template_name = filedialog.asksaveasfilename(initialdir=self.template_dir, defaultextension=".txt",
                                                     filetypes=[("Text files", "*.txt")], title="Save Template")
        if template_name:
            with open(template_name, 'w', encoding='utf-8') as file:
                file.write(self.base_prompt_text.get(1.0, tk.END).strip())
            messagebox.showinfo("Saved", "Template saved successfully!")

    # Load template into base prompt
    def load_template(self):
        template_file = filedialog.askopenfilename(initialdir=self.template_dir, filetypes=[("Text files", "*.txt")],
                                                   title="Load Template")
        if template_file:
            with open(template_file, 'r', encoding='utf-8') as file:
                template_content = file.read()
            self.base_prompt_text.delete(1.0, tk.END)
            self.base_prompt_text.insert(tk.END, template_content)

    # Delete selected template file after confirmation
    def delete_template(self):
        template_file = filedialog.askopenfilename(initialdir=self.template_dir, filetypes=[("Text files", "*.txt")],
                                                   title="Delete Template")
        if template_file and messagebox.askyesno("Confirm", "Are you sure you want to delete this template?"):
            os.remove(template_file)
            messagebox.showinfo("Deleted", "Template deleted successfully!")

    # Clear current tab’s content
    def clear_current(self):
        current_index = self.notebook.index('current')
        if current_index == 0:
            self.content_text.config(state=tk.NORMAL)
            self.content_text.delete(1.0, tk.END)
            self.content_text.config(state=tk.DISABLED)
            self.file_contents = ""
            self.token_count = 0
            self.info_label.config(text="Token Count: 0")
            self.copy_button.config(state=tk.DISABLED)
        elif current_index == 1:
            self.tree.delete(*self.tree.get_children())
            self.copy_structure_button.config(state=tk.DISABLED)
        elif current_index == 2:
            self.base_prompt_text.delete(1.0, tk.END)

    # Clear all tabs’ content
    def clear_all(self):
        self.content_text.config(state=tk.NORMAL)
        self.content_text.delete(1.0, tk.END)
        self.content_text.config(state=tk.DISABLED)
        self.file_contents = ""
        self.token_count = 0
        self.info_label.config(text="Token Count: 0")
        self.copy_button.config(state=tk.DISABLED)
        self.tree.delete(*self.tree.get_children())
        self.copy_structure_button.config(state=tk.DISABLED)
        self.base_prompt_text.delete(1.0, tk.END)

    # Show about dialog
    def show_about(self):
        messagebox.showinfo("About", "CodeBase v1.0\nA tool to scan repositories and copy contents.\n© 2023 Your Name")

if __name__ == "__main__":
    root = tk.Tk()
    app = RepoPromptGUI(root)
    root.mainloop()