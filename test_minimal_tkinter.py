#!/usr/bin/env python3
import time
import tkinter as tk

def test_minimal_tkinter():
    start = time.time()
    root = tk.Tk()
    end = time.time()
    print(f"Minimal Tkinter root creation: {end - start:.3f} seconds")
    root.destroy()

if __name__ == "__main__":
    test_minimal_tkinter()
