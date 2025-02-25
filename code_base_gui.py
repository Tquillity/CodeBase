import os
import tkinter as tk
from tkinter import filedialog, scrolledtext
import pyperclip
import fnmatch
import mimetypes
import tkinter.ttk as ttk

class RepoPromptGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Repo Prompt")
        self.root.geometry("800x600")

        # Dark mode color scheme
        self.root.configure(bg='#2b2b2b')
        self.text_color = '#ffffff'
        self.button_bg = '#4a4a4a'
        self.button_fg = '#ffffff'
        self.header_color = '#add8e6'
        self.status_color = '#ffff00'  # Yellow for status message

        self.repo_path = None
        self.file_contents = ""
        self.token_count = 0
        self.ignore_patterns = []

        # Header
        self.header_label = tk.Label(root, text="CodeBase", font=("Arial", 16), bg='#2b2b2b', fg=self.text_color)
        self.header_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.version_label = tk.Label(root, text="v1.0", font=("Arial", 10), bg='#2b2b2b', fg=self.header_color)
        self.version_label.grid(row=0, column=1, padx=5, pady=10, sticky="w")

        # Left frame (buttons and token count)
        self.left_frame = tk.Frame(root, bg='#2b2b2b')
        self.left_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ns")

        # Right frame (tabbed interface)
        self.right_frame = tk.Frame(root, bg='#2b2b2b')
        self.right_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

        # Make right frame expandable
        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(1, weight=1)

        # Left frame contents
        self.select_button = tk.Button(self.left_frame, text="Select Repo Folder", command=self.select_repo,
                                       bg=self.button_bg, fg=self.button_fg)
        self.select_button.pack(pady=10)

        self.info_label = tk.Label(self.left_frame, text="Token Count: 0", bg='#2b2b2b', fg=self.text_color)
        self.info_label.pack(pady=5)

        # Copy Contents button and its status label
        self.copy_button = tk.Button(self.left_frame, text="Copy Contents", command=self.copy_to_clipboard,
                                     state=tk.DISABLED, bg=self.button_bg, fg=self.button_fg)
        self.copy_button.pack(pady=10)
        self.copy_status_label = tk.Label(self.left_frame, text="", font=("Arial", 8), bg='#2b2b2b', fg=self.status_color)
        self.copy_status_label.pack()

        # Copy Structure button and its status label
        self.copy_structure_button = tk.Button(self.left_frame, text="Copy Structure", command=self.copy_structure_to_clipboard,
                                               state=tk.DISABLED, bg=self.button_bg, fg=self.button_fg)
        self.copy_structure_button.pack(pady=10)
        self.copy_structure_status_label = tk.Label(self.left_frame, text="", font=("Arial", 8), bg='#2b2b2b', fg=self.status_color)
        self.copy_structure_status_label.pack()

        # Right frame: Notebook with tabs
        self.notebook = ttk.Notebook(self.right_frame)
        self.notebook.pack(fill="both", expand=True)

        # Tab 1: Content Preview
        self.content_frame = tk.Frame(self.notebook, bg='#2b2b2b')
        self.notebook.add(self.content_frame, text="Content Preview")
        self.content_text = scrolledtext.ScrolledText(self.content_frame, wrap=tk.WORD, bg='#3c3c3c', fg=self.text_color,
                                                      font=("Arial", 10), state=tk.DISABLED)
        self.content_text.pack(fill="both", expand=True)

        # Tab 2: Folder Structure
        self.structure_frame = tk.Frame(self.notebook, bg='#2b2b2b')
        self.notebook.add(self.structure_frame, text="Folder Structure")
        self.structure_text = scrolledtext.ScrolledText(self.structure_frame, wrap=tk.WORD, bg='#3c3c3c', fg=self.text_color,
                                                        font=("Arial", 10), state=tk.DISABLED)
        self.structure_text.pack(fill="both", expand=True)

    def select_repo(self):
        self.repo_path = filedialog.askdirectory()
        if self.repo_path:
            gitignore_path = os.path.join(self.repo_path, '.gitignore')
            self.ignore_patterns = self.parse_gitignore(gitignore_path)

            self.file_contents = self.read_repo_files(self.repo_path)
            self.token_count = len(self.file_contents.split())
            formatted_count = f"{self.token_count:,}".replace(",", " ")
            self.info_label.config(text=f"Token Count: {formatted_count}")
            self.copy_button.config(state=tk.NORMAL)
            self.copy_structure_button.config(state=tk.NORMAL)

            # Update Content Preview
            words = self.file_contents.split()
            preview_text = " ".join(words[:500])
            self.content_text.config(state=tk.NORMAL)
            self.content_text.delete(1.0, tk.END)
            self.content_text.insert(tk.END, preview_text)
            self.content_text.config(state=tk.DISABLED)

            # Update Folder Structure
            folder_structure = self.generate_folder_structure(self.repo_path)
            self.structure_text.config(state=tk.NORMAL)
            self.structure_text.delete(1.0, tk.END)
            self.structure_text.insert(tk.END, folder_structure)
            self.structure_text.config(state=tk.DISABLED)

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
        return mime_type and mime_type.startswith('text')

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
                        print(f"Skipping {file_path}: Not a UTF-8 text file")
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")
        return "\n".join(file_contents)

    def generate_folder_structure(self, root_dir):
        def build_tree(path, prefix, indent):
            if self.is_ignored(path):
                return []
            basename = os.path.basename(path)
            icon = "📁" if os.path.isdir(path) else "📄"
            lines = [indent + prefix + icon + basename]
            if os.path.isdir(path):
                items = [item for item in sorted(os.listdir(path)) if not self.is_ignored(os.path.join(path, item))]
                for i, item in enumerate(items):
                    item_path = os.path.join(path, item)
                    if i < len(items) - 1:
                        sub_prefix = "├── "
                        sub_indent = indent + "│   "
                    else:
                        sub_prefix = "└── "
                        sub_indent = indent + "    "
                    lines.extend(build_tree(item_path, sub_prefix, sub_indent))
            return lines

        root_basename = os.path.basename(root_dir)
        structure = ["── 📁" + root_basename]
        items = [item for item in sorted(os.listdir(root_dir)) if not self.is_ignored(os.path.join(root_dir, item))]
        for i, item in enumerate(items):
            item_path = os.path.join(root_dir, item)
            if i < len(items) - 1:
                sub_prefix = "├── "
                sub_indent = "│   "
            else:
                sub_prefix = "└── "
                sub_indent = "    "
            sub_tree = build_tree(item_path, sub_prefix, sub_indent)
            structure.extend(sub_tree)
        return "\n".join(structure)

    def show_status_message(self, label, message):
        """Display a temporary status message under the specified label."""
        label.config(text=message)
        self.root.after(10000, lambda: label.config(text=""))  # Clear after 10 seconds

    def copy_to_clipboard(self):
        pyperclip.copy(self.file_contents)
        self.show_status_message(self.copy_status_label, "Copy Successful!")

    def copy_structure_to_clipboard(self):
        structure_content = self.structure_text.get(1.0, tk.END).strip()
        pyperclip.copy(structure_content)
        self.show_status_message(self.copy_structure_status_label, "Copy Successful!")

if __name__ == "__main__":
    root = tk.Tk()
    app = RepoPromptGUI(root)
    root.mainloop()