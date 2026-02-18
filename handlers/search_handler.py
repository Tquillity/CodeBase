from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from gui import RepoPromptGUI


class SearchHandler:
    gui: RepoPromptGUI

    def __init__(self, gui: RepoPromptGUI) -> None:
        self.gui = gui

    def search_tab(self) -> None:
        query = self.gui.search_var.get()
        if not query:
            return
        current_index = self.gui.notebook.index(self.gui.notebook.select())  # type: ignore[no-untyped-call]
        if current_index == 2:
            return
        if current_index == 4:
            return

        self._clear_search_highlights(current_index)

        tab_instances = [self.gui.content_tab, self.gui.structure_tab, self.gui.module_analysis_tab, self.gui.base_prompt_tab, self.gui.settings_tab, self.gui.file_list_tab]
        tab = tab_instances[current_index]
        matches = tab.perform_search(query, self.gui.case_sensitive_var.get(), self.gui.whole_word_var.get())

        self.gui.match_positions[current_index] = matches
        self.gui.current_match_index[current_index] = 0 if matches else -1

        if matches:
            self._highlight_match(current_index, 0, is_focused=True)
            tab.center_match(matches[0])
            self.gui.show_status_message(f"Found {len(matches)} match(es).")
            self.gui.search_count_label.config(text=f"1/{len(matches)}")
        else:
            self.gui.show_status_message("Search found nothing.")
            self.gui.search_count_label.config(text="0 matches")

    def next_match(self) -> None:
        current_index = self.gui.notebook.index(self.gui.notebook.select())  # type: ignore[no-untyped-call]
        matches = cast(Any, self.gui.match_positions).get(current_index, [])
        if not matches:
            return
        current_match = cast(Any, self.gui.current_match_index).get(current_index, -1)

        if current_match < len(matches) - 1:
            self._highlight_match(current_index, current_match, is_focused=False)
            new_index = current_match + 1
            self._highlight_match(current_index, new_index, is_focused=True)
            self.gui.current_match_index[current_index] = new_index

            tab_instances = [self.gui.content_tab, self.gui.structure_tab, self.gui.module_analysis_tab, self.gui.base_prompt_tab, self.gui.settings_tab, self.gui.file_list_tab]
            tab = cast(Any, tab_instances[current_index])
            tab.center_match(matches[new_index])
            self.gui.search_count_label.config(text=f"{new_index + 1}/{len(matches)}")

    def prev_match(self) -> None:
        current_index = self.gui.notebook.index(self.gui.notebook.select())  # type: ignore[no-untyped-call]
        matches = cast(Any, self.gui.match_positions).get(current_index, [])
        if not matches:
            return
        current_match = cast(Any, self.gui.current_match_index).get(current_index, -1)

        if current_match > 0:
            self._highlight_match(current_index, current_match, is_focused=False)
            new_index = current_match - 1
            self._highlight_match(current_index, new_index, is_focused=True)
            self.gui.current_match_index[current_index] = new_index

            tab_instances = [self.gui.content_tab, self.gui.structure_tab, self.gui.module_analysis_tab, self.gui.base_prompt_tab, self.gui.settings_tab, self.gui.file_list_tab]
            tab = cast(Any, tab_instances[current_index])
            tab.center_match(matches[new_index])
            self.gui.search_count_label.config(text=f"{new_index + 1}/{len(matches)}")

    def find_all(self) -> None:
        query = self.gui.search_var.get()
        if not query:
            return
        current_index = self.gui.notebook.index(self.gui.notebook.select())  # type: ignore[no-untyped-call]
        if current_index == 2:
            return
        if current_index == 4:
            return

        self._clear_search_highlights(current_index)

        tab_instances = [self.gui.content_tab, self.gui.structure_tab, self.gui.module_analysis_tab, self.gui.base_prompt_tab, self.gui.settings_tab, self.gui.file_list_tab]
        tab = cast(Any, tab_instances[current_index])
        matches = tab.perform_search(query, self.gui.case_sensitive_var.get(), self.gui.whole_word_var.get())

        tab.highlight_all_matches(matches)

        self.gui.match_positions[current_index] = matches
        self.gui.current_match_index[current_index] = -1
        if matches:
            self.gui.show_status_message(f"Highlighted {len(matches)} match(es).")
            self.gui.search_count_label.config(text=f"{len(matches)} matches")
        else:
            self.gui.show_status_message("No matches found.")
            self.gui.search_count_label.config(text="0 matches")

    def _clear_search_highlights(self, tab_index: int) -> None:
        tab_instances = [self.gui.content_tab, self.gui.structure_tab, self.gui.module_analysis_tab, self.gui.base_prompt_tab, self.gui.settings_tab, self.gui.file_list_tab]
        tab = cast(Any, tab_instances[tab_index])
        tab.clear_highlights()
        if hasattr(self.gui, 'search_count_label'):
            self.gui.search_count_label.config(text="")

    def _highlight_match(self, tab_index: int, match_index: int, is_focused: bool = True) -> None:
        matches = cast(Any, self.gui.match_positions).get(tab_index, [])
        if not matches or match_index < 0 or match_index >= len(matches):
            return

        tab_instances = [self.gui.content_tab, self.gui.structure_tab, self.gui.module_analysis_tab, self.gui.base_prompt_tab, self.gui.settings_tab, self.gui.file_list_tab]
        tab = cast(Any, tab_instances[tab_index])
        tab.highlight_match(matches[match_index], is_focused)
