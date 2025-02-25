import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import pyperclip
import fnmatch
import mimetypes

class RepoPromptGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Repo Prompt")
        self.root.geometry("800x600")  # Resize window to 800x600 pixels
        
        # Set dark mode colors
        self.root.configure(bg='#2b2b2b')  # Dark grey background
        self.text_color = '#ffffff'  # White text
        self.button_bg = '#4a4a4a'  # Medium grey for buttons
        self.button_fg = '#ffffff'  # White text for buttons
        self.header_color = '#add8e6'  # Light dark blue for version
        
        self.repo_path = None
        self.file_contents = ""
        self.token_count = 0
        self.ignore_patterns = []
        
        # Header: "CodeBase v1.0"
        self.header_label = tk.Label(root, text="CodeBase", font=("Arial", 16), bg='#2b2b2b', fg=self.text_color)
        self.header_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.version_label = tk.Label(root, text="v1.0", font=("Arial", 10), bg='#2b2b2b', fg=self.header_color)
        self.version_label.grid(row=0, column=1, padx=5, pady=10, sticky="w")
        
        # Left frame for buttons and token count
        self.left_frame = tk.Frame(root, bg='#2b2b2b')
        self.left_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ns")
        
        # Right frame for text area
        self.right_frame = tk.Frame(root, bg='#2b2b2b')
        self.right_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        
        # Configure grid to make right frame expandable
        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(1, weight=1)
        
        # Left frame contents (buttons and token count)
        self.select_button = tk.Button(self.left_frame, text="Select Repo Folder", command=self.select_repo,
                                       bg=self.button_bg, fg=self.button_fg)
        self.select_button.pack(pady=10)  # Added padding for better margins
        
        self.info_label = tk.Label(self.left_frame, text="Token Count: 0", bg='#2b2b2b', fg=self.text_color)
        self.info_label.pack(pady=5)
        
        self.copy_button = tk.Button(self.left_frame, text="Copy Contents", command=self.copy_to_clipboard,
                                     state=tk.DISABLED, bg=self.button_bg, fg=self.button_fg)
        self.copy_button.pack(pady=10)  # Added padding for better margins
        
        # Right frame: Text area for first 500 tokens
        self.text_area = scrolledtext.ScrolledText(self.right_frame, wrap=tk.WORD, bg='#3c3c3c', fg=self.text_color,
                                                   font=("Arial", 10), state=tk.DISABLED)
        self.text_area.pack(fill="both", expand=True)
        
    def select_repo(self):
        self.repo_path = filedialog.askdirectory()
        if self.repo_path:
            # Parse .gitignore if it exists
            gitignore_path = os.path.join(self.repo_path, '.gitignore')
            self.ignore_patterns = self.parse_gitignore(gitignore_path)
            
            # Read files, skipping ignored and binary files
            self.file_contents = self.read_repo_files(self.repo_path)
            self.token_count = len(self.file_contents.split())  # Count words as tokens
            formatted_count = f"{self.token_count:,}".replace(",", " ")
            self.info_label.config(text=f"Token Count: {formatted_count}")
            self.copy_button.config(state=tk.NORMAL)
            
            # Display first 500 tokens in text area
            words = self.file_contents.split()
            preview_text = " ".join(words[:500])
            self.text_area.config(state=tk.NORMAL)
            self.text_area.delete(1.0, tk.END)
            self.text_area.insert(tk.END, preview_text)
            self.text_area.config(state=tk.DISABLED)
    
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