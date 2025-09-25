#!/usr/bin/env python3
import time
import tkinter as tk

def test_imports():
    start = time.time()
    from gui import RepoPromptGUI
    end = time.time()
    print(f"Import time: {end - start:.3f} seconds")

def test_gui_creation():
    from gui import RepoPromptGUI
    
    start = time.time()
    root = tk.Tk()
    end = time.time()
    print(f"Tkinter root creation: {end - start:.3f} seconds")
    
    start = time.time()
    app = RepoPromptGUI(root)
    end = time.time()
    print(f"RepoPromptGUI creation: {end - start:.3f} seconds")
    
    root.destroy()

if __name__ == "__main__":
    test_imports()
    test_gui_creation()
