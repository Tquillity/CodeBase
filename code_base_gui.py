import os
import tkinter as tk
from tkinter import filedialog, scrolledtext, IntVar, messagebox
import pyperclip
import fnmatch
import mimetypes
import tkinter.ttk as ttk
import appdirs  # For cross-platform user data directory

class RepoPromptGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Code Base")
        self.root.geometry("800x600")

        # Dark mode color scheme
        self.root.configure(bg='#2b2b2b')
        self.text_color = '#ffffff'
        self.button_bg = '#4a4a4a'
        self.button_fg = '#ffffff'
        self.header_color = '#add8e6'
        self.status_color = '#ffff00'
        self.folder_color = '#FFD700'  # Orange-yellowish for folders

        self.repo_path = None
        self.file_contents = ""
        self.token_count = 0
        self.ignore_patterns = []

        # User data directory for templates and recent folders
        self.user_data_dir = appdirs.user_data_dir("CodeBase")
        self.template_dir = os.path.join(self.user_data_dir, "templates")
        self.recent_folders_file = os.path.join(self.user_data_dir, "recent_folders.txt")
        os.makedirs(self.template_dir, exist_ok=True)

        # Load recent folders
        self.recent_folders = self.load_recent_folders()

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

        self.copy_button = tk.Button(self.left_frame, text="Copy Contents", command=self.copy_to_clipboard,
                                     state=tk.DISABLED, bg=self.button_bg, fg=self.button_fg)
        self.copy_button.pack(pady=10)
        self.copy_status_label = tk.Label(self.left_frame, text="", font=("Arial", 8), bg='#2b2b2b', fg=self.status_color)
        self.copy_status_label.pack()

        self.prepend_var = IntVar()
        self.prepend_checkbox = tk.Checkbutton(self.left_frame, text="Prepend Base Prompt", variable=self.prepend_var,
                                               bg='#2b2b2b', fg=self.text_color, selectcolor='#4a4a4a')
        self.prepend_checkbox.pack(pady=5)

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
        self.tree = ttk.Treeview(self.structure_frame, show="tree", style="Custom.Treeview")
        self.tree.pack(fill="both", expand=True)
        style = ttk.Style()
        style.configure("Custom.Treeview", background="#3c3c3c", foreground=self.text_color, fieldbackground="#3c3c3c")
        style.map("Custom.Treeview", background=[('selected', '#4a4a4a')], foreground=[('selected', self.text_color)])
        scrollbar = ttk.Scrollbar(self.structure_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Tab 3: Base Prompt
        self.base_prompt_frame = tk.Frame(self.notebook, bg='#2b2b2b')
        self.notebook.add(self.base_prompt_frame, text="Base Prompt")
        self.base_prompt_text = scrolledtext.ScrolledText(self.base_prompt_frame, wrap=tk.WORD, bg='#3c3c3c', fg=self.text_color,
                                                          font=("Arial", 10))
        self.base_prompt_text.pack(fill="both", expand=True)

        # Buttons for Base Prompt in a horizontal frame
        button_frame = tk.Frame(self.base_prompt_frame, bg='#2b2b2b')
        button_frame.pack(pady=5)
        self.save_template_button = tk.Button(button_frame, text="Save Template", command=self.save_template,
                                              bg=self.button_bg, fg=self.button_fg)
        self.save_template_button.grid(row=0, column=0, padx=5)
        self.load_template_button = tk.Button(button_frame, text="Load Template", command=self.load_template,
                                              bg=self.button_bg, fg=self.button_fg)
        self.load_template_button.grid(row=0, column=1, padx=5)
        self.clear_text_button = tk.Button(button_frame, text="Clear Text", command=self.clear_base_prompt,
                                           bg=self.button_bg, fg=self.button_fg)
        self.clear_text_button.grid(row=0, column=2, padx=5)

    ### New Methods for Added Features ###

    def clear_base_prompt(self):
        """Clear all text in the Base Prompt text area."""
        self.base_prompt_text.delete(1.0, tk.END)

    def load_recent_folders(self):
        """Load recent folders from the history file."""
        if os.path.exists(self.recent_folders_file):
            with open(self.recent_folders_file, 'r') as file:
                return [line.strip() for line in file.readlines() if line.strip()]
        return []

    def save_recent_folders(self):
        """Save recent folders to the history file."""
        with open(self.recent_folders_file, 'w') as file:
            for folder in self.recent_folders:
                file.write(f"{folder}\n")

    def update_recent_folders(self, new_folder):
        """Update the recent folders list with a new selection, limiting to 10 entries."""
        if new_folder in self.recent_folders:
            self.recent_folders.remove(new_folder)
        self.recent_folders.insert(0, new_folder)
        if len(self.recent_folders) > 10:
            self.recent_folders = self.recent_folders[:10]
        self.save_recent_folders()

    def open_folder_dialog(self):
        """Custom dialog for selecting a folder with a recent folders dropdown."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Repository Folder")
        dialog.geometry("400x200")
        dialog.configure(bg=self.header_color)  # Set dialog background to border color

        # Outer frame to act as the border
        border_frame = tk.Frame(dialog, bg=self.header_color)
        border_frame.pack(fill="both", expand=True, padx=2, pady=2)  # 2px border thickness

        # Inner frame for dialog content
        inner_frame = tk.Frame(border_frame, bg='#3c3c3c')
        inner_frame.pack(fill="both", expand=True)

        # Title label inside inner frame
        title_label = tk.Label(inner_frame, text="Select Repository Folder", 
                            font=("Arial", 12, "bold"), bg='#3c3c3c', fg=self.text_color)
        title_label.pack(pady=5)

        # Truncate long paths for dropdown
        def truncate_path(path, max_length=50):
            if len(path) > max_length:
                return "…/" + path[-(max_length - 3):]
            return path

        recent_folders_truncated = [truncate_path(folder) for folder in self.recent_folders]

        # Dropdown label and combobox
        tk.Label(inner_frame, text="Recent Folders:", bg='#3c3c3c', fg=self.text_color).pack(pady=5)
        folder_var = tk.StringVar()
        folder_dropdown = ttk.Combobox(inner_frame, textvariable=folder_var, 
                                    values=recent_folders_truncated, state="readonly")
        folder_dropdown.pack(pady=5, fill="x")

        # Browse button
        def browse_folder():
            folder = filedialog.askdirectory()
            if folder:
                folder_var.set(folder)

        browse_button = tk.Button(inner_frame, text="Browse", command=browse_folder,
                                bg=self.button_bg, fg=self.button_fg)
        browse_button.pack(pady=5)

        # OK button
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

        ok_button = tk.Button(inner_frame, text="OK", command=confirm_selection,
                            bg=self.button_bg, fg=self.button_fg)
        ok_button.pack(pady=10)

        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)
        return getattr(dialog, 'selected_folder', None)

    ### Updated Method ###

    def select_repo(self):
        """Open custom dialog to select repo folder with recent folders dropdown."""
        selected_folder = self.open_folder_dialog()
        if selected_folder:
            self.repo_path = selected_folder
            self.update_recent_folders(selected_folder)

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
            self.populate_tree(self.repo_path)

    ### Original Methods (Unchanged) ###

    def populate_tree(self, root_dir):
        self.tree.delete(*self.tree.get_children())
        root_basename = os.path.basename(root_dir)
        root_icon = "📁" if os.path.isdir(root_dir) else "📄"
        root_id = self.tree.insert("", "end", text=f"{root_icon} {root_basename}", open=True, tags=('folder',))
        self.build_tree(root_dir, root_id)

        # Configure folder and file colors
        self.tree.tag_configure('folder', foreground=self.folder_color)
        self.tree.tag_configure('file', foreground=self.text_color)

    def build_tree(self, path, parent_id):
        if self.is_ignored(path):
            return
        items = [item for item in sorted(os.listdir(path)) if not self.is_ignored(os.path.join(path, item))]
        for item in items:
            item_path = os.path.join(path, item)
            icon = "📁" if os.path.isdir(item_path) else "📄"
            tag = 'folder' if os.path.isdir(item_path) else 'file'
            item_id = self.tree.insert(parent_id, "end", text=f"{icon} {item}", open=False, tags=(tag,))
            if os.path.isdir(item_path):
                self.build_tree(item_path, item_id)

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

    def generate_folder_structure_text(self):
        def traverse_tree(item_id, prefix="", indent=""):
            lines = []
            item_text = self.tree.item(item_id, "text")
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

    def show_status_message(self, label, message):
        label.config(text=message)
        self.root.after(10000, lambda: label.config(text=""))

    def copy_to_clipboard(self):
        if self.prepend_var.get() == 1:
            base_prompt = self.base_prompt_text.get(1.0, tk.END).strip()
            content_to_copy = base_prompt + "\n\n" + self.file_contents
        else:
            content_to_copy = self.file_contents
        pyperclip.copy(content_to_copy)
        self.show_status_message(self.copy_status_label, "Copy Successful!")

    def copy_structure_to_clipboard(self):
        structure_content = self.generate_folder_structure_text()
        pyperclip.copy(structure_content)
        self.show_status_message(self.copy_structure_status_label, "Copy Successful!")

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

if __name__ == "__main__":
    root = tk.Tk()
    app = RepoPromptGUI(root)
    root.mainloop()