# tests/test_search_utils.py
import tkinter as tk

from widgets.search_utils import label_matches_query, search_text_widget


def test_label_matches_query_whole_word():
    assert label_matches_query("hello world", "world", case_sensitive=False, whole_word=True)
    assert not label_matches_query("helloworld", "world", case_sensitive=False, whole_word=True)


def test_label_matches_query_substring():
    assert label_matches_query("MyModule.py", "mod", case_sensitive=False, whole_word=False)


def test_search_text_widget_whole_word():
    root = tk.Tk()
    root.withdraw()
    text = tk.Text(root)
    text.insert("1.0", "func( hello world func(x)")
    matches = search_text_widget(text, "func", "1.0", case_sensitive=True, whole_word=True)
    assert len(matches) >= 1
    root.destroy()


def test_search_text_widget_literal_metacharacters():
    root = tk.Tk()
    root.withdraw()
    text = tk.Text(root)
    text.insert("1.0", "func( test")
    matches = search_text_widget(text, "func(", "1.0", case_sensitive=True, whole_word=False)
    assert len(matches) == 1
    root.destroy()
