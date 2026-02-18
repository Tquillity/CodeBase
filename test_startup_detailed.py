#!/usr/bin/env python3
from __future__ import annotations

import time
import tkinter as tk
from typing import cast

import ttkbootstrap as ttk


def test_imports() -> None:
    start = time.time()
    from gui import RepoPromptGUI  # noqa: F401
    end = time.time()
    print(f"Import time: {end - start:.3f} seconds")


def test_gui_creation() -> None:
    from gui import RepoPromptGUI

    start = time.time()
    root = tk.Tk()
    end = time.time()
    print(f"Tkinter root creation: {end - start:.3f} seconds")
    start = time.time()
    app = RepoPromptGUI(cast(ttk.Window, root))
    end = time.time()
    print(f"RepoPromptGUI creation: {end - start:.3f} seconds")
    root.destroy()


if __name__ == "__main__":
    test_imports()
    test_gui_creation()
