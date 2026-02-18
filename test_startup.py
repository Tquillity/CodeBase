#!/usr/bin/env python3
from __future__ import annotations

import time
import tkinter as tk
from typing import cast

import ttkbootstrap as ttk
from gui import RepoPromptGUI


def test_startup_time() -> None:
    start_time = time.time()
    root = tk.Tk()
    app = RepoPromptGUI(cast(ttk.Window, root))
    end_time = time.time()
    startup_time = end_time - start_time
    print(f"Startup time: {startup_time:.3f} seconds")
    root.destroy()


if __name__ == "__main__":
    test_startup_time()
