# tests/test_gui_bindings.py
import tkinter as tk
import ttkbootstrap as ttk

from gui_bindings import widget_is_text_entry


def test_widget_is_text_entry_includes_ttk_entry():
    root = tk.Tk()
    root.withdraw()
    try:
        assert widget_is_text_entry(ttk.Entry(root))
        assert widget_is_text_entry(tk.Entry(root))
        assert widget_is_text_entry(tk.Text(root))
        assert not widget_is_text_entry(ttk.Button(root, text="x"))
    finally:
        root.destroy()
