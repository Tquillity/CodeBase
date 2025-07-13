import tkinter as tk
from gui import RepoPromptGUI

if __name__ == "__main__":
    root = tk.Tk()
    app = RepoPromptGUI(root)
    root.mainloop()