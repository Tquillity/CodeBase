# widgets/search_utils.py
"""Shared text-widget search helpers for tab search bars."""
from __future__ import annotations

import re
import tkinter as tk
from typing import Any


def label_matches_query(
    label: str,
    query: str,
    *,
    case_sensitive: bool,
    whole_word: bool,
) -> bool:
    """Match a tree/list label against a search query (Python-side, not Tk text)."""
    if not query:
        return False
    if whole_word:
        flags = 0 if case_sensitive else re.IGNORECASE
        return re.search(rf"\b{re.escape(query)}\b", label, flags) is not None
    search_in = label if case_sensitive else label.lower()
    query_term = query if case_sensitive else query.lower()
    return query_term in search_in


def search_text_widget(
    text_widget: Any,
    query: str,
    start_pos: str,
    *,
    case_sensitive: bool,
    whole_word: bool,
    stopindex: str = tk.END,
) -> list[tuple[str, str]]:
    """
    Search a Tk text widget for matches.

    whole_word=False: literal search (regexp=False).
    whole_word=True: Tcl word boundaries via regexp=True, re.escape(query) wrapped in \\m...\\M.
    Uses count=tk.IntVar() for actual match length (not len(query)).
    Catches tk.TclError on invalid patterns; returns matches found so far.
    """
    if not query:
        return []

    matches: list[tuple[str, str]] = []
    pos = start_pos
    search_query = query
    use_regexp = False

    if whole_word:
        search_query = rf"\m{re.escape(query)}\M"
        use_regexp = True

    count_var = tk.IntVar(value=0)
    while True:
        try:
            found = text_widget.search(
                search_query,
                pos,
                stopindex=stopindex,
                nocase=not case_sensitive,
                regexp=use_regexp,
                count=count_var,
            )
        except tk.TclError:
            break
        if not found:
            break
        match_len = count_var.get() if use_regexp else len(query)
        end_pos = f"{found}+{match_len}c"
        matches.append((found, end_pos))
        pos = end_pos
    return matches
