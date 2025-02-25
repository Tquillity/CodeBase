import os
import tkinter as tk
from tkinter import filedialog, messagebox
import pyperclip
import fnmatch
import mimetypes

class RepoPromptGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Repo Prompt")
        
        self.repo_path = None
        self.file_contents = ""
        self.token_count = 0
        self.ignore_patterns = []
        
        # Create GUI elements
        self.select_button = tk.Button(root, text="Select Repo Folder", command=self.select_repo)
        self.select_button.pack(pady=10)
        
        self.info_label = tk.Label(root, text="Token Count: 0")
        self.info_label.pack(pady=5)
        
        self.copy_button = tk.Button(root, text="Copy Contents", command=self.copy_to_clipboard, state=tk.DISABLED)
        self.copy_button.pack(pady=10)
        
    def select_repo(self):
        self.repo_path = filedialog.askdirectory()
        if self.repo_path:
            # Parse .gitignore if it exists
            gitignore_path = os.path.join(self.repo_path, '.gitignore')
            self.ignore_patterns = self.parse_gitignore(gitignore_path)
            
            # Read files, skipping ignored and binary files
            self.file_contents = self.read_repo_files(self.repo_path)
            self.token_count = len(self.file_contents.split())  # Count words as tokens
            self.info_label.config(text=f"Token Count: {self.token_count}")
            self.copy_button.config(state=tk.NORMAL)
    
    def parse_gitignore(self, gitignore_path):
        """Read .gitignore and return a list of patterns to ignore."""
        ignore_patterns = []
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r') as file:
                for line in file:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        ignore_patterns.append(line)
        return ignore_patterns
    
    def is_ignored(self, path):
        """Check if a file or directory should be ignored based on .gitignore patterns."""
        rel_path = os.path.relpath(path, self.repo_path)
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(os.path.basename(path), pattern):
                return True
        return False
    
    def is_text_file(self, file_path):
        """Check if a file is a text file based on its MIME type."""
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type and mime_type.startswith('text')
    
    def read_repo_files(self, root_dir):
        """Read files from the repository, skipping ignored and binary files."""
        file_contents = []
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Skip ignored directories
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
    
    def copy_to_clipboard(self):
        pyperclip.copy(self.file_contents)
        messagebox.showinfo("Copied", "Contents copied to clipboard.")

if __name__ == "__main__":
    root = tk.Tk()
    app = RepoPromptGUI(root)
    root.mainloop()