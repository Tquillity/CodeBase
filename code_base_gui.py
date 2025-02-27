import os
import tkinter as tk
from tkinter import filedialog, scrolledtext, IntVar, messagebox
import pyperclip
import fnmatch
import mimetypes
import tkinter.ttk as ttk
import appdirs  # For cross-platform user data directory

class Tooltip:
    """Simple tooltip class for Tkinter widgets with improved positioning and delay."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        self.id = None
        self.widget.bind("<Enter>", self.schedule_show)
        self.widget.bind("<Leave>", self.hide_tip)

    def schedule_show(self, event):
        # Cancel any pending tooltip if the mouse moves quickly
        if self.id:
            self.widget.after_cancel(self.id)
        # Schedule tooltip to show after a 500ms delay
        self.id = self.widget.after(500, lambda: self.show_tip(event))

    def show_tip(self, event):
        if self.tip:  # Avoid creating multiple tooltips
            return
        # Position tooltip 25 pixels below and to the right of the widget
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)  # Remove window decorations
        self.tip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tip, text=self.text, bg="#ffffe0", relief="solid", borderwidth=1)
        label.pack()
        # Adjust position to stay within screen boundaries
        self.tip.update_idletasks()  # Update geometry info
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
        # Cancel scheduled tooltip if mouse leaves before delay
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None
        # Destroy tooltip if it exists
        if self.tip:
            self.tip.destroy()
            self.tip = None

class RepoPromptGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Code Base")
        self.root.geometry("1024x600")

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
        self.cache_file = os.path.join(self.user_data_dir, "cache.txt")
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
        self.select_button = tk.Button(self.left_frame, text="Select Repo Folder (Ctrl+R)", command=self.select_repo,
                                       bg=self.button_bg, fg=self.button_fg)
        self.select_button.pack(pady=10)
        Tooltip(self.select_button, "Choose a repository folder to scan")

        self.info_label = tk.Label(self.left_frame, text="Token Count: 0", bg='#2b2b2b', fg=self.text_color)
        self.info_label.pack(pady=5)

        self.copy_button = tk.Button(self.left_frame, text="Copy Contents (Ctrl+C)", command=self.copy_to_clipboard,
                                     state=tk.DISABLED, bg=self.button_bg, fg=self.button_fg)
        self.copy_button.pack(pady=0)
        Tooltip(self.copy_button, "Copy file contents to clipboard")
        self.copy_status_label = tk.Label(self.left_frame, text="", font=("Arial", 8), bg='#2b2b2b', fg=self.status_color)
        self.copy_status_label.pack()

        self.prepend_var = IntVar()
        self.prepend_checkbox = tk.Checkbutton(self.left_frame, text="Prepend Base Prompt", variable=self.prepend_var,
                                               bg='#2b2b2b', fg=self.text_color, selectcolor='#4a4a4a')
        self.prepend_checkbox.pack(pady=5)
        Tooltip(self.prepend_checkbox, "Include Base Prompt text in copied content")

        self.copy_structure_button = tk.Button(self.left_frame, text="Copy Structure (Ctrl+S)", command=self.copy_structure_to_clipboard,
                                               state=tk.DISABLED, bg=self.button_bg, fg=self.button_fg)
        self.copy_structure_button.pack(pady=10)
        Tooltip(self.copy_structure_button, "Copy folder structure to clipboard")
        self.copy_structure_status_label = tk.Label(self.left_frame, text="", font=("Arial", 8), bg='#2b2b2b', fg=self.status_color)
        self.copy_structure_status_label.pack()

        self.include_icons_var = IntVar(value=1)
        self.include_icons_checkbox = tk.Checkbutton(self.left_frame, text="Include Icons in Structure",
                                                     variable=self.include_icons_var, bg='#2b2b2b', fg=self.text_color,
                                                     selectcolor='#4a4a4a')
        self.include_icons_checkbox.pack(pady=5)
        Tooltip(self.include_icons_checkbox, "Toggle icons in the copied folder structure")

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
        button_frame.pack(pady=10)  # Increased padding for better spacing
        self.save_template_button = tk.Button(button_frame, text="Save Template (Ctrl+S)", command=self.save_template,
                                              bg=self.button_bg, fg=self.button_fg)
        self.save_template_button.grid(row=0, column=0, padx=5)
        Tooltip(self.save_template_button, "Save the current Base Prompt as a template")
        self.load_template_button = tk.Button(button_frame, text="Load Template (Ctrl+L)", command=self.load_template,
                                              bg=self.button_bg, fg=self.button_fg)
        self.load_template_button.grid(row=0, column=1, padx=5)
        Tooltip(self.load_template_button, "Load a saved template into the Base Prompt")

        self.delete_template_button = tk.Button(button_frame, text="Delete Template", command=self.delete_template,
                                                bg=self.button_bg, fg=self.button_fg)
        self.delete_template_button.grid(row=0, column=3, padx=5)
        Tooltip(self.delete_template_button, "Delete a saved template")

        # Menu bar for help
        self.menu = tk.Menu(self.root, bg=self.button_bg, fg=self.button_fg)
        self.root.config(menu=self.menu)
        help_menu = tk.Menu(self.menu, bg=self.button_bg, fg=self.button_fg)
        self.menu.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

        # Keyboard shortcuts
        self.root.bind('<Control-c>', lambda e: self.copy_to_clipboard())
        self.root.bind('<Control-s>', lambda e: self.save_template())
        self.root.bind('<Control-l>', lambda e: self.load_template())
        self.root.bind('<Control-r>', lambda e: self.select_repo())

        # Add clear buttons at the bottom
        clear_button_frame = tk.Frame(self.left_frame, bg='#2b2b2b')
        clear_button_frame.pack(side='bottom', fill='x')

        self.clear_button = tk.Button(clear_button_frame, text="Clear", command=self.clear_current,
                                    bg=self.button_bg, fg=self.button_fg)
        Tooltip(self.clear_button, "Clear data in the current tab")
        self.clear_button.pack(side='left', padx=5, pady=5)

        self.clear_all_button = tk.Button(clear_button_frame, text="Clear All", command=self.clear_all,
                                        bg=self.button_bg, fg=self.button_fg)
        Tooltip(self.clear_all_button, "Clear data in all tabs")
        self.clear_all_button.pack(side='left', padx=5, pady=5)

    ### New Methods for Added Features ###


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
        dialog.configure(bg=self.header_color)

        # Outer frame for border
        border_frame = tk.Frame(dialog, bg=self.header_color)
        border_frame.pack(fill="both", expand=True, padx=2, pady=2)

        # Inner frame for content
        inner_frame = tk.Frame(border_frame, bg='#3c3c3c')
        inner_frame.pack(fill="both", expand=True)

        # Title label
        title_label = tk.Label(inner_frame, text="Select Repository Folder",
                               font=("Arial", 12, "bold"), bg='#3c3c3c', fg=self.text_color)
        title_label.pack(pady=5)

        # Truncate long paths
        def truncate_path(path, max_length=50):
            if len(path) > max_length:
                return "…/" + path[-(max_length - 3):]
            return path

        recent_folders_truncated = [truncate_path(folder) for folder in self.recent_folders]

        tk.Label(inner_frame, text="Recent Folders:", bg='#3c3c3c', fg=self.text_color).pack(pady=5)
        folder_var = tk.StringVar()
        folder_dropdown = ttk.Combobox(inner_frame, textvariable=folder_var, values=recent_folders_truncated, state="readonly")
        folder_dropdown.pack(pady=5, fill="x")

        def browse_folder():
            folder = filedialog.askdirectory()
            if folder:
                folder_var.set(folder)

        browse_button = tk.Button(inner_frame, text="Browse", command=browse_folder,
                                  bg=self.button_bg, fg=self.button_fg)
        browse_button.pack(pady=5)

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
        if selected_folder and os.path.isdir(selected_folder):
            self.repo_path = os.path.realpath(selected_folder)
            self.update_recent_folders(self.repo_path)

            gitignore_path = os.path.join(self.repo_path, '.gitignore')
            self.ignore_patterns = self.parse_gitignore(gitignore_path)

            # Check for cached contents
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cached_repo_path = f.readline().strip()  # Read the first line (repo path)
                    if cached_repo_path == self.repo_path and os.path.getmtime(self.cache_file) > os.path.getmtime(self.repo_path):
                        self.file_contents = f.read()  # Read the remaining contents
                    else:
                        self.file_contents = self.read_repo_files(self.repo_path)
                        with open(self.cache_file, 'w', encoding='utf-8') as f:
                            f.write(self.repo_path + '\n')  # Write repo path as first line
                            f.write(self.file_contents)     # Write file contents
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

            # Update Content Preview
            words = self.file_contents.split()
            preview_text = " ".join(words[:500])
            self.content_text.config(state=tk.NORMAL)
            self.content_text.delete(1.0, tk.END)
            self.content_text.insert(tk.END, preview_text)
            self.content_text.config(state=tk.DISABLED)

            # Update Folder Structure
            self.populate_tree(self.repo_path)
        else:
            messagebox.showerror("Invalid Folder", "Please select a valid directory.")

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
                # Add dummy child for lazy loading
                self.tree.insert(item_id, "end", text="Loading...", tags=('dummy',))
                self.tree.tag_bind(tag, '<Double-1>', lambda e, p=item_path, i=item_id: self.expand_folder(p, i))

    def expand_folder(self, path, item_id):
        # Remove dummy node
        for child in self.tree.get_children(item_id):
            self.tree.delete(child)
        self.build_tree(path, item_id)

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
                        messagebox.showwarning("File Skipped", f"Skipping {filename}: Not a UTF-8 text file")
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to read {filename}: {str(e)}")
        return "\n".join(file_contents)

    def generate_folder_structure_text(self):
        def traverse_tree(item_id, prefix="", indent=""):
            lines = []
            item_text = self.tree.item(item_id, "text")
            if self.include_icons_var.get() == 0:
                item_text = item_text[2:]  # Remove icon and space
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
        """Display a temporary status message with fade-out effect."""
        label.config(text=message)
        def fade_out(opacity=1.0):
            if opacity > 0:
                label.config(fg=f'#{int(255 * opacity):02x}{int(255 * opacity):02x}{int(0):02x}')
                self.root.after(100, fade_out, opacity - 0.1)
            else:
                label.config(text="", fg=self.status_color)
        self.root.after(5000, fade_out)

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

    def delete_template(self):
        """Delete a selected template file."""
        template_file = filedialog.askopenfilename(initialdir=self.template_dir, filetypes=[("Text files", "*.txt")],
                                                   title="Delete Template")
        if template_file and messagebox.askyesno("Confirm", "Are you sure you want to delete this template?"):
            os.remove(template_file)
            messagebox.showinfo("Deleted", "Template deleted successfully!")

    def clear_current(self):
        current_index = self.notebook.index('current')
        if current_index == 0:  # Content Preview tab
            self.content_text.config(state=tk.NORMAL)
            self.content_text.delete(1.0, tk.END)
            self.content_text.config(state=tk.DISABLED)
            self.file_contents = ""
            self.token_count = 0
            self.info_label.config(text="Token Count: 0")
            self.copy_button.config(state=tk.DISABLED)
        elif current_index == 1:  # Folder Structure tab
            self.tree.delete(*self.tree.get_children())
            self.copy_structure_button.config(state=tk.DISABLED)
        elif current_index == 2:  # Base Prompt tab
            self.base_prompt_text.delete(1.0, tk.END)

    def clear_all(self):
        # Clear Content Preview
        self.content_text.config(state=tk.NORMAL)
        self.content_text.delete(1.0, tk.END)
        self.content_text.config(state=tk.DISABLED)
        self.file_contents = ""
        self.token_count = 0
        self.info_label.config(text="Token Count: 0")
        self.copy_button.config(state=tk.DISABLED)
        
        # Clear Folder Structure
        self.tree.delete(*self.tree.get_children())
        self.copy_structure_button.config(state=tk.DISABLED)
        
        # Clear Base Prompt
        self.base_prompt_text.delete(1.0, tk.END)

    def show_about(self):
        """Show about information."""
        messagebox.showinfo("About", "CodeBase v1.0\nA tool to scan repositories and copy contents.\n© 2023 Your Name")

if __name__ == "__main__":
    root = tk.Tk()
    app = RepoPromptGUI(root)
    root.mainloop()