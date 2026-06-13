# gui_bindings.py
"""Global keyboard shortcuts for RepoPromptGUI."""
from __future__ import annotations

from typing import Any

import tkinter as tk
import ttkbootstrap as ttk


def widget_is_text_entry(widget: Any) -> bool:
    """True when focus is in a text-editing widget (native or ttk)."""
    return isinstance(widget, (tk.Text, tk.Entry, ttk.Entry))


def bind_app_shortcuts(gui: Any) -> None:
    def _on_copy_contents(e: Any) -> None:
        if widget_is_text_entry(e.widget):
            return
        gui.copy_handler.copy_contents()

    def _on_copy_structure(e: Any) -> None:
        if widget_is_text_entry(e.widget):
            return
        gui.copy_handler.copy_structure()

    def _on_copy_all(e: Any) -> None:
        if widget_is_text_entry(e.widget):
            return
        gui.copy_handler.copy_all()

    gui.root.bind("<Control-r>", lambda e: gui.repo_handler.select_repo())
    gui.root.bind("<Control-F5>", lambda e: gui.repo_handler.refresh_repo())
    gui.root.bind("<Control-c>", _on_copy_contents)
    gui.root.bind("<Control-s>", _on_copy_structure)
    gui.root.bind("<Control-a>", _on_copy_all)
    gui.root.bind("<Control-t>", lambda e: gui.base_prompt_tab.save_template())
    gui.root.bind("<Control-l>", lambda e: gui.base_prompt_tab.load_template())
